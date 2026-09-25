#!/usr/bin/env python3
"""Local-only panel transcription and annotation app.

The server binds to 127.0.0.1, stores its working database under private/story,
and never serves manga images. Page images selected in the browser remain in the
browser session only.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "story_annotator"
DEFAULT_DB = ROOT / "private" / "story" / "story_annotations.sqlite"
DEFAULT_IMPORT = ROOT / "private" / "story" / "chapter_407_panel_transcription.csv"
EXPORT_DIR = ROOT / "private" / "story" / "exports"
CHARACTERS_CSV = ROOT / "data" / "story" / "characters.csv"
CHARACTER_APPEARANCES_CSV = ROOT / "data" / "story" / "chapter_character_appearances.csv"

PANEL_FIELDS = (
    "panel_id", "chapter", "page_start", "page_end", "panel_order",
    "panel_types", "characters_on_panel", "characters_mentioned", "location",
    "tags", "visual_description", "notes", "review_status", "silent_panel",
)


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS chapters (
            chapter INTEGER PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            page_count INTEGER NOT NULL DEFAULT 0,
            edition TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS panels (
            panel_id TEXT PRIMARY KEY,
            chapter INTEGER NOT NULL REFERENCES chapters(chapter),
            page_start INTEGER NOT NULL,
            page_end INTEGER NOT NULL,
            panel_order INTEGER NOT NULL,
            panel_types TEXT NOT NULL DEFAULT 'standard',
            characters_on_panel TEXT NOT NULL DEFAULT '',
            characters_mentioned TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            visual_description TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            review_status TEXT NOT NULL DEFAULT 'needs_review',
            silent_panel INTEGER NOT NULL DEFAULT 0,
            UNIQUE(chapter, page_start, page_end, panel_order)
        );
        CREATE TABLE IF NOT EXISTS text_segments (
            segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_id TEXT NOT NULL REFERENCES panels(panel_id) ON DELETE CASCADE ON UPDATE CASCADE,
            segment_order INTEGER NOT NULL,
            speaker TEXT NOT NULL DEFAULT '',
            mode TEXT NOT NULL DEFAULT 'dialogue',
            text TEXT NOT NULL DEFAULT '',
            UNIQUE(panel_id, segment_order)
        );
        CREATE TABLE IF NOT EXISTS characters (
            character_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            hunterpedia_title TEXT NOT NULL DEFAULT '',
            identity_status TEXT NOT NULL DEFAULT 'community_wiki_seed',
            first_listed_chapter INTEGER,
            source_type TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            retrieved_utc TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS chapter_character_appearances (
            chapter INTEGER NOT NULL,
            appearance_order INTEGER NOT NULL,
            character_id TEXT NOT NULL REFERENCES characters(character_id),
            appearance_type TEXT NOT NULL DEFAULT 'appears',
            source_note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(chapter, appearance_order, character_id)
        );
        """
    )
    seed_characters(db)
    return db


def seed_characters(db: sqlite3.Connection) -> None:
    if not CHARACTERS_CSV.exists() or not CHARACTER_APPEARANCES_CSV.exists():
        return
    if not db.execute("SELECT COUNT(*) FROM characters").fetchone()[0]:
        with CHARACTERS_CSV.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                db.execute(
                    "INSERT OR IGNORE INTO characters VALUES(?,?,?,?,?,?,?,?,?)",
                    (row["character_id"], row["display_name"], row["hunterpedia_title"],
                     row["identity_status"], int(row["first_listed_chapter"]),
                     row["source_type"], row["source_url"], row["retrieved_utc"], row["notes"]),
                )
        with CHARACTER_APPEARANCES_CSV.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                db.execute(
                    "INSERT OR IGNORE INTO chapter_character_appearances VALUES(?,?,?,?,?)",
                    (int(row["chapter"]), int(row["appearance_order"]), row["character_id"],
                     row["appearance_type"], row["source_note"]),
                )
        db.commit()


def characters_payload(db: sqlite3.Connection, chapter: int | None = None) -> dict:
    rows = db.execute(
        """SELECT c.*, a.appearance_order, a.appearance_type, a.source_note,
        CASE WHEN a.chapter IS NULL THEN 0 ELSE 1 END AS chapter_candidate
        FROM characters c
        LEFT JOIN chapter_character_appearances a
          ON a.character_id=c.character_id AND a.chapter=?
        ORDER BY chapter_candidate DESC, COALESCE(a.appearance_order, 9999), c.display_name""",
        (chapter,),
    ).fetchall()
    return {"chapter": chapter, "characters": [dict(row) for row in rows]}


def make_panel_id(chapter: int, page_start: int, page_end: int, order: int) -> str:
    page_part = f"p{page_start:02d}"
    if page_end != page_start:
        page_part += f"-{page_end:02d}"
    return f"ch{chapter}-{page_part}-{order:02d}"


def split_pages(value: str) -> tuple[int, int]:
    numbers = [int(n) for n in re.findall(r"\d+", value)]
    if not numbers:
        raise ValueError(f"No page number in {value!r}")
    return numbers[0], numbers[-1]


def infer_mode(text: str) -> str:
    lowered = text.lower()
    if " os:" in f" {lowered}" or "[thought]" in lowered:
        return "mixed" if ":" in text.replace("OS:", "", 1) else "thought"
    return "dialogue"


def import_legacy_csv(db: sqlite3.Connection, path: Path) -> int:
    if not path.exists():
        return 0
    if db.execute("SELECT COUNT(*) FROM panels").fetchone()[0]:
        return 0

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return 0

    chapter = int(rows[0]["chapter"])
    page_count = max(split_pages(row["page"])[1] for row in rows)
    db.execute(
        "INSERT OR IGNORE INTO chapters(chapter,title,page_count,edition,language) "
        "VALUES(?,?,?,?,?)",
        (chapter, "Negotiation", page_count, "", "en"),
    )
    for row in rows:
        page_start, page_end = split_pages(row["page"])
        order = int(row["panel_order"])
        panel_id = make_panel_id(chapter, page_start, page_end, order)
        visual = (row.get("characters_on_panel") or "").strip()
        db.execute(
            """INSERT INTO panels(
                panel_id,chapter,page_start,page_end,panel_order,panel_types,
                characters_on_panel,characters_mentioned,location,tags,
                visual_description,notes,review_status,silent_panel
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                panel_id, chapter, page_start, page_end, order,
                (row.get("panel_type") or "standard").strip().replace(", ", ";"),
                visual, (row.get("characters_mentioned") or "").strip(),
                (row.get("location") or "").strip(),
                (row.get("keywords") or "").strip().replace(", ", ";"),
                "", (row.get("notes") or "").strip(), "needs_review",
                1 if not (row.get("script_text") or "").strip() else 0,
            ),
        )
        text = (row.get("script_text") or "").strip()
        if text:
            db.execute(
                "INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) "
                "VALUES(?,?,?,?,?)",
                (panel_id, 1, (row.get("speakers") or "").strip(), infer_mode(text), text),
            )
    db.commit()
    return len(rows)


def panel_payload(db: sqlite3.Connection, panel_id: str) -> dict:
    row = db.execute("SELECT * FROM panels WHERE panel_id=?", (panel_id,)).fetchone()
    if row is None:
        raise KeyError(panel_id)
    data = dict(row)
    data["silent_panel"] = bool(data["silent_panel"])
    data["segments"] = [
        dict(segment)
        for segment in db.execute(
            "SELECT segment_id,segment_order,speaker,mode,text FROM text_segments "
            "WHERE panel_id=? ORDER BY segment_order", (panel_id,)
        )
    ]
    return data


def chapter_payload(db: sqlite3.Connection, chapter: int) -> dict:
    meta = db.execute("SELECT * FROM chapters WHERE chapter=?", (chapter,)).fetchone()
    if meta is None:
        raise KeyError(chapter)
    panel_rows = db.execute(
        "SELECT panel_id,page_start,page_end,panel_order,review_status,silent_panel,location "
        "FROM panels WHERE chapter=? ORDER BY page_start,page_end,panel_order",
        (chapter,),
    ).fetchall()
    panels = [dict(row) for row in panel_rows]
    for panel in panels:
        panel["silent_panel"] = bool(panel["silent_panel"])
    complete = sum(1 for row in panel_rows if row["review_status"] == "reviewed")
    return {"chapter": dict(meta), "panels": panels, "reviewed": complete}


def update_panel(db: sqlite3.Connection, panel_id: str, payload: dict) -> dict:
    existing = db.execute("SELECT * FROM panels WHERE panel_id=?", (panel_id,)).fetchone()
    if existing is None:
        raise KeyError(panel_id)
    values = {field: payload.get(field, existing[field]) for field in PANEL_FIELDS if field != "panel_id"}
    values["silent_panel"] = 1 if values["silent_panel"] else 0
    db.execute(
        """UPDATE panels SET panel_types=?,characters_on_panel=?,characters_mentioned=?,
        location=?,tags=?,visual_description=?,notes=?,review_status=?,silent_panel=?
        WHERE panel_id=?""",
        (
            values["panel_types"], values["characters_on_panel"],
            values["characters_mentioned"], values["location"], values["tags"],
            values["visual_description"], values["notes"], values["review_status"],
            values["silent_panel"], panel_id,
        ),
    )
    db.execute("DELETE FROM text_segments WHERE panel_id=?", (panel_id,))
    for index, segment in enumerate(payload.get("segments", []), start=1):
        db.execute(
            "INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) "
            "VALUES(?,?,?,?,?)",
            (
                panel_id, index, (segment.get("speaker") or "").strip(),
                segment.get("mode") or "dialogue", segment.get("text") or "",
            ),
        )
    db.commit()
    return panel_payload(db, panel_id)


def add_panel(db: sqlite3.Connection, payload: dict) -> dict:
    chapter = int(payload["chapter"])
    page_start = int(payload["page_start"])
    page_end = int(payload.get("page_end", page_start))
    after = int(payload.get("after_order", 0))
    rows = db.execute(
        "SELECT panel_id,panel_order FROM panels WHERE chapter=? AND page_start=? AND page_end=? "
        "ORDER BY panel_order DESC", (chapter, page_start, page_end)
    ).fetchall()
    for row in rows:
        if row["panel_order"] > after:
            temporary = f"__moving__{row['panel_id']}"
            db.execute(
                "UPDATE panels SET panel_id=?,panel_order=? WHERE panel_id=?",
                (temporary, -row["panel_order"], row["panel_id"]),
            )
    for row in rows:
        if row["panel_order"] > after:
            old_id = f"__moving__{row['panel_id']}"
            new_order = row["panel_order"] + 1
            new_id = make_panel_id(chapter, page_start, page_end, new_order)
            db.execute(
                "UPDATE panels SET panel_id=?,panel_order=? WHERE panel_id=?",
                (new_id, new_order, old_id),
            )
    order = after + 1
    panel_id = make_panel_id(chapter, page_start, page_end, order)
    inherit = payload.get("inherit", {})
    db.execute(
        """INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,
        panel_types,characters_on_panel,characters_mentioned,location,tags,
        visual_description,notes,review_status,silent_panel)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            panel_id, chapter, page_start, page_end, order, "standard", "", "",
            inherit.get("location", ""), inherit.get("tags", ""), "", "",
            "needs_review", 0,
        ),
    )
    db.commit()
    return panel_payload(db, panel_id)


def export_chapter(db: sqlite3.Connection, chapter: int) -> tuple[Path, str]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"chapter_{chapter}_panels.csv"
    fields = [
        "panel_id", "chapter", "page_start", "page_end", "panel_order",
        "panel_types", "characters_on_panel", "characters_mentioned", "location",
        "tags", "visual_description", "notes", "review_status", "silent_panel",
        "text_segments_json",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    ids = db.execute(
        "SELECT panel_id FROM panels WHERE chapter=? ORDER BY page_start,page_end,panel_order",
        (chapter,),
    )
    for item in ids:
        panel = panel_payload(db, item["panel_id"])
        row = {field: panel.get(field, "") for field in fields}
        row["silent_panel"] = int(panel["silent_panel"])
        row["text_segments_json"] = json.dumps(panel["segments"], ensure_ascii=False)
        writer.writerow(row)
    text = output.getvalue()
    path.write_text(text, encoding="utf-8")
    return path, text


class AppHandler(BaseHTTPRequestHandler):
    db_path = DEFAULT_DB

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("story-annotator: " + fmt % args + "\n")

    def send_json(self, value, status=HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/chapter/"):
                chapter = int(parsed.path.rsplit("/", 1)[1])
                with connect(self.db_path) as db:
                    self.send_json(chapter_payload(db, chapter))
                return
            if parsed.path.startswith("/api/panel/"):
                panel_id = parsed.path.rsplit("/", 1)[1]
                with connect(self.db_path) as db:
                    self.send_json(panel_payload(db, panel_id))
                return
            if parsed.path == "/api/characters":
                query = __import__("urllib.parse").parse.parse_qs(parsed.query)
                chapter = int(query["chapter"][0]) if query.get("chapter") else None
                with connect(self.db_path) as db:
                    self.send_json(characters_payload(db, chapter))
                return
            self.serve_static(parsed.path)
        except KeyError as exc:
            self.send_json({"error": f"Not found: {exc.args[0]}"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/panel/"):
                panel_id = parsed.path.rsplit("/", 1)[1]
                with connect(self.db_path) as db:
                    self.send_json(update_panel(db, panel_id, self.read_json()))
                return
            self.send_json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/panels":
                with connect(self.db_path) as db:
                    self.send_json(add_panel(db, self.read_json()), HTTPStatus.CREATED)
                return
            if parsed.path.startswith("/api/export/"):
                chapter = int(parsed.path.rsplit("/", 1)[1])
                with connect(self.db_path) as db:
                    path, _ = export_chapter(db, chapter)
                self.send_json({"saved": str(path.relative_to(ROOT))})
                return
            self.send_json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def serve_static(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (APP_DIR / relative).resolve()
        if APP_DIR.resolve() not in target.parents and target != APP_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    with connect(args.db) as db:
        imported = import_legacy_csv(db, DEFAULT_IMPORT)
    AppHandler.db_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Story annotator: {url}")
    print(f"Database: {args.db}")
    if imported:
        print(f"Imported {imported} panels from {DEFAULT_IMPORT.relative_to(ROOT)}")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
