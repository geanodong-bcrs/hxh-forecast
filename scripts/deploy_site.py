#!/usr/bin/env python3
"""Publish the site and the reproducible parts of the project to a PUBLIC repo.

    python3 scripts/deploy_site.py            # stage + show exactly what would go
    python3 scripts/deploy_site.py --push     # stage, commit, push

The working vault stays private. It holds 776 of Togashi's manuscript photos
(data/raw/tweet_media, review/thumbs) — archiving those locally for transcription
is research; republishing them from a public repo is redistribution at scale. It
also holds an Obsidian vault and 202 MB of history. None of that goes out.

Two independent guards, because a git history is permanent and a mistake here
cannot be taken back:

  ALLOW   an explicit list of what is copied. Nothing is included by wildcard
          from the repo root, so a new directory is never published by accident.
  DENY    a pattern scan of the STAGED TREE, run after copying and before any
          commit. If anything matching it survived the allowlist, the deploy
          aborts. This is meant to be redundant — if it ever fires, the allowlist
          was wrong.

The deploy tree lives OUTSIDE the vault so obsidian-git never sees it, and it
has its own git history containing only these files — the vault's 51 commits of
image data are never pushed anywhere.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
DEPLOY = os.path.abspath(os.path.join(REPO, "..", "hxh-forecast-deploy"))
REMOTE = "https://github.com/geanodong-bcrs/hxh-forecast.git"
BRANCH = "main"
GIT_NAME = "geanodong-bcrs"
GIT_EMAIL = "geanodong-bcrs@users.noreply.github.com"   # never a real inbox

# (source in the vault, destination in the public repo). The two pages go to the
# ROOT so Pages serves them at /hxh-forecast/ rather than /hxh-forecast/site/.
ALLOW = [
    ("site/index.html", "index.html"),
    ("site/method.html", "method.html"),
    ("scripts", "scripts"),
    ("data/processed", "data/processed"),
    ("data/forecasts", "data/forecasts"),
    ("data/annotations", "data/annotations"),
    ("data/taxonomy", "data/taxonomy"),
    ("data/corrections", "data/corrections"),
    ("data/automation/poll_log.csv", "data/automation/poll_log.csv"),
    ("docs", "docs"),
    ("launchd", "launchd"),
    ("Agents.md", "Agents.md"),
]

# Anything matching these must never reach the public tree.
DENY = [
    (r"(^|/)\.env$", "the X API bearer token"),
    (r"(^|/)\.obsidian(/|$)", "Obsidian vault config"),
    (r"(^|/)tweet_media(/|$)", "Togashi's manuscript photos"),
    (r"(^|/)thumbs(/|$)", "review thumbnails of his photos"),
    (r"(^|/)resources(/|$)", "third-party chart image (@togashiactu)"),
    (r"(^|/)raw(/|$)", "the raw layer"),
    (r"\.(jpe?g|png|gif|webp|heic)$", "an image file"),
    (r"(^|/)__pycache__(/|$)", "python bytecode"),
    (r"(^|/)\.DS_Store$", "macOS metadata"),
    (r"(^|/)main(/|$)", "the stray bare-git directory"),
    (r"(^|/)review(/|$)", "the reviewer UI and its thumbnails"),
]

README = """# Hunter x Hunter — publication forecast

**[View the forecast](https://geanodong-bcrs.github.io/hxh-forecast/)** ·
[How it works](https://geanodong-bcrs.github.io/hxh-forecast/method.html)

A Bayesian forecast of when the next Hunter x Hunter chapters will be published,
built from the historical publication record and from Togashi's own production
posts on X. It updates itself: once a day, and again whenever he posts.

This repository is the published output and the code that produces it. Every
forecast the model has ever made is in `data/forecasts/`, append-only — including
the wrong ones.

## What is here

```
index.html          the forecast page
method.html         how it works, and where it is weakest
scripts/            the whole pipeline: fetch -> build -> forecast -> render
docs/               data dictionary, model, backtest, event taxonomy, automation
data/processed/     chapters, WSJ issue calendar, tweets, production events
data/forecasts/     every forecast snapshot, never overwritten
data/annotations/   image transcriptions and the announcement record
Agents.md           the project specification the whole thing follows
```

## What is deliberately not here

Togashi's manuscript photos. The project downloads them to transcribe production
milestones, which is why `data/raw/` is missing from this repository — archiving
them for research is one thing, republishing several hundred of them is another.
`data/processed/production_events.csv` carries the verbatim Japanese read from
each image, with the tweet ID it came from, so the evidence is auditable without
the images being rehosted.

## Reproducing a forecast

Every snapshot records the sha256 of each input file it was built from, plus the
run that produced it and the evidence timestamp it was allowed to see.

```bash
python3 scripts/run_update.py --no-poll --force
```

## Caveats

The model's headline number rests on very little, and the method page says so
plainly rather than burying it. No calibration figures are published yet, because
scoring honestly requires an announcement record that does not exist yet — see
`docs/model.md` and `docs/backtest.md`.

An independent fan project. Not affiliated with Shueisha or with Togashi.
"""


def run(cmd, cwd=DEPLOY, check=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit("FAILED: %s\n%s%s" % (" ".join(cmd), p.stdout, p.stderr))
    return p


def stage():
    """Rebuild the deploy tree from scratch, keeping its .git."""
    keep_git = os.path.join(DEPLOY, ".git")
    had_git = os.path.exists(keep_git)
    if os.path.exists(DEPLOY):
        for name in os.listdir(DEPLOY):
            if name == ".git":
                continue
            p = os.path.join(DEPLOY, name)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    else:
        os.makedirs(DEPLOY)

    def ignore(_d, names):
        return [n for n in names
                if n in ("__pycache__", ".DS_Store", "resources") or n.endswith(".pyc")]

    for src, dst in ALLOW:
        s, d = os.path.join(REPO, src), os.path.join(DEPLOY, dst)
        if not os.path.exists(s):
            print("  skip (missing): %s" % src)
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    with open(os.path.join(DEPLOY, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(README)
    # tell Pages not to run Jekyll over the tree
    open(os.path.join(DEPLOY, ".nojekyll"), "w").close()
    return had_git


def inventory():
    out = []
    for root, dirs, files in os.walk(DEPLOY):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), DEPLOY)
            out.append((rel, os.path.getsize(os.path.join(root, f))))
    return sorted(out)


def check_deny(files):
    bad = []
    for rel, _ in files:
        for pat, why in DENY:
            if re.search(pat, rel):
                bad.append((rel, why))
                break
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="commit and push (default: stage only)")
    ap.add_argument("--message", default=None)
    args = ap.parse_args()

    print("vault:  %s" % REPO)
    print("deploy: %s" % DEPLOY)
    print("remote: %s\n" % REMOTE)

    had_git = stage()
    files = inventory()

    bad = check_deny(files)
    if bad:
        print("\nDENYLIST TRIPPED — nothing was committed or pushed:")
        for rel, why in bad[:20]:
            print("  %-60s %s" % (rel, why))
        sys.exit("\n%d file(s) matched the denylist. Fix ALLOW before retrying." % len(bad))

    total = sum(sz for _, sz in files)
    by_dir = {}
    for rel, sz in files:
        top = rel.split(os.sep)[0] if os.sep in rel else "(root)"
        by_dir.setdefault(top, [0, 0])
        by_dir[top][0] += 1
        by_dir[top][1] += sz
    print("staged %d files, %.1f MB — denylist clean\n" % (len(files), total / 1e6))
    print("  %-22s %6s  %9s" % ("", "files", "size"))
    for k in sorted(by_dir):
        print("  %-22s %6d  %8.1f KB" % (k, by_dir[k][0], by_dir[k][1] / 1024.0))

    if not args.push:
        print("\nStaged only. Review the list above, then re-run with --push.")
        return 0

    if not had_git:
        run(["git", "init"])
        # `git init -b` needs git 2.28+; this machine is older. Point HEAD at the
        # branch directly, which works on every version and avoids an initial
        # commit landing on master and then needing a rename.
        run(["git", "symbolic-ref", "HEAD", "refs/heads/%s" % BRANCH])
        run(["git", "remote", "add", "origin", REMOTE])
        # Set the identity LOCALLY, on the deploy repo only — the machine has no
        # git identity configured, so commits would otherwise be authored as
        # <user>@<hostname>.local and bake the machine name into public commit
        # metadata forever. The GitHub noreply address is the privacy-preserving
        # standard and never exposes a real inbox.
        run(["git", "config", "user.name", GIT_NAME])
        run(["git", "config", "user.email", GIT_EMAIL])
    run(["git", "add", "-A"])
    if not run(["git", "status", "--porcelain"], check=False).stdout.strip():
        print("\nnothing changed since the last deploy")
        return 0
    msg = args.message or ("publish forecast %s"
                           % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    run(["git", "commit", "-m", msg])
    p = run(["git", "push", "-u", "origin", BRANCH], check=False)
    if p.returncode != 0:
        print(p.stdout + p.stderr)
        sys.exit("push failed — if this is the first push you may need to "
                 "authenticate (a GitHub PAT or `git credential` helper).")
    print("\npushed to %s (%s)" % (REMOTE, BRANCH))
    print("Pages: enable in Settings > Pages > Deploy from branch: main / (root)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
