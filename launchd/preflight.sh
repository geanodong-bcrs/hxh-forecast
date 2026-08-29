#!/bin/bash
# Does a launchd job have permission to read this repo?
#
# The repo lives under ~/Documents, which macOS protects with TCC. A LaunchAgent
# is NOT covered by the permission your Terminal has, and the failure is nasty:
#   /bin/bash          -> fast, clear "Operation not permitted"
#   anaconda python3   -> HANGS forever in open(), no error, no output
# so a broken install looks like a job that runs and never finishes.
#
# This bootstraps a throwaway job that tries to read one file the way launchd
# will, and reports what happened.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$(command -v python3)"
LABEL="com.togashi.preflight"
OUT="/tmp/togashi_preflight.$$"

cat > "$OUT.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$LABEL</string>
<key>ProgramArguments</key><array>
  <string>$PYTHON</string><string>-c</string>
  <string>open("$REPO/README.md").read(16); print("READABLE")</string>
</array>
<key>StandardOutPath</key><string>$OUT.out</string>
<key>StandardErrorPath</key><string>$OUT.err</string>
<key>RunAtLoad</key><false/>
</dict></plist>
PLIST

: > "$OUT.out"; : > "$OUT.err"
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null
launchctl bootstrap "gui/$UID" "$OUT.plist" 2>/dev/null
launchctl kickstart "gui/$UID/$LABEL" >/dev/null 2>&1

verdict="hang"
for _ in $(seq 1 15); do
  sleep 1
  if grep -q READABLE "$OUT.out" 2>/dev/null; then verdict="ok"; break; fi
  if [[ -s "$OUT.err" ]]; then verdict="denied"; break; fi
done

launchctl kill 9 "gui/$UID/$LABEL" 2>/dev/null
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null
err="$(cat "$OUT.err" 2>/dev/null | tail -3)"
rm -f "$OUT.plist" "$OUT.out" "$OUT.err"

if [[ "$verdict" == "ok" ]]; then
  echo "preflight OK — launchd can read the repo."
  exit 0
fi

REAL="$(python3 -c 'import sys,os; print(os.path.realpath(sys.executable))')"
cat <<MSG

  ================================================================
  PREFLIGHT FAILED — launchd cannot read this repo.
  ================================================================
MSG
[[ "$verdict" == "hang" ]] \
  && echo "  The probe HUNG in open() — the signature of a TCC block that" \
  && echo "  never returns. The scheduled jobs would hang the same way:" \
  && echo "  running forever, producing no output and no error." \
  || echo "  The probe was denied: ${err:-Operation not permitted}"
cat <<MSG

  The repo is under ~/Documents, which macOS protects. The permission
  your Terminal has does NOT extend to a LaunchAgent.

  Fix — grant Full Disk Access to the interpreter launchd runs:

    1. System Settings > Privacy & Security > Full Disk Access
    2. Click +  (authenticate)
    3. Press Cmd-Shift-G and paste this exact path:

         $REAL

    4. Make sure its toggle is ON
    5. Re-run:  ./launchd/preflight.sh

  Adding Terminal to Full Disk Access does not help — TCC attributes
  the access to the binary launchd executes, which is the one above.

MSG
exit 1
