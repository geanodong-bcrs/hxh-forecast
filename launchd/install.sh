#!/bin/bash
# Install (or reinstall) the two forecast LaunchAgents.
#
#   ./launchd/install.sh            install and load
#   ./launchd/install.sh uninstall  unload and remove
#
# Templates in this directory carry __REPO__/__PYTHON__/__HOME__ placeholders so
# they stay portable; this substitutes real paths into ~/Library/LaunchAgents.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents"
PYTHON="$(command -v python3)"
LABELS=(com.togashi.forecast.poll com.togashi.forecast.daily)

if [[ "${1:-}" == "uninstall" ]]; then
  for l in "${LABELS[@]}"; do
    launchctl bootout "gui/$UID/$l" 2>/dev/null || true
    rm -f "$DEST/$l.plist"
    echo "removed $l"
  done
  exit 0
fi

mkdir -p "$DEST" "$REPO/data/automation"
for l in "${LABELS[@]}"; do
  sed -e "s|__REPO__|$REPO|g" -e "s|__PYTHON__|$PYTHON|g" -e "s|__HOME__|$HOME|g" \
      "$REPO/launchd/$l.plist" > "$DEST/$l.plist"
  plutil -lint "$DEST/$l.plist" >/dev/null
  launchctl bootout "gui/$UID/$l" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$DEST/$l.plist"
  echo "installed $l"
done

echo
echo "python: $PYTHON"
echo "repo:   $REPO"
echo
launchctl list | grep -E 'PID|com.togashi' || true
echo

# The repo is under ~/Documents, which macOS protects with TCC. A LaunchAgent is
# not covered by the permission your Terminal holds, and the first launchd read
# can block on a consent decision instead of failing — a job that runs forever
# and prints nothing. Force that to happen now, at install time, rather than at
# 03:00 with nobody watching.
"$REPO/launchd/preflight.sh" || {
  echo
  echo "The agents are installed but will not work until the above is fixed."
  exit 1
}
echo
echo "poll  : hourly 02:00-09:00 local (8 runs/day, polls the X API)"
echo "daily : 09:30 local, right after the last poll. No API call."
echo
echo "Run one now:  python3 scripts/run_update.py --no-poll --force"
echo "Tail logs:    tail -f data/automation/launchd.poll.err.log"
