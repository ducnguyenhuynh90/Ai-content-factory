#!/usr/bin/env bash
# Set up the video editor on YOUR computer (macOS or Linux). Safe to re-run.
#
# It never uses sudo, never asks for a password and never uploads media. When something needs an
# administrator or an account, it stops and tells you the exact command to run yourself.
set -uo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/.." && pwd)"
SKILLS="$HOME/.claude/skills"
ok() { printf "  [x] %s\n" "$*"; }
no() { printf "  [ ] %s\n" "$*"; MISSING=1; }
MISSING=0
OS="$(uname -s)"

echo "== 1. Tools"
if command -v ffmpeg >/dev/null; then ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"
else no "ffmpeg missing -> install it yourself: macOS 'brew install ffmpeg' · Ubuntu 'sudo apt install ffmpeg'"; fi
if command -v node >/dev/null; then
  NV=$(node --version | tr -d v | cut -d. -f1)
  if [ "$NV" -ge 22 ]; then ok "node $(node --version)"
  else no "node $(node --version) is older than 22 (HyperFrames needs 22+) -> macOS 'brew install node@22' · or nvm: 'nvm install 22'"; fi
else no "node missing -> macOS 'brew install node' · Linux: https://nodejs.org (or nvm)"; fi
command -v npx >/dev/null && ok "npx $(npx --version)" || no "npx missing (comes with Node.js)"
command -v git >/dev/null && ok "git $(git --version | awk '{print $3}')" || no "git missing -> macOS 'xcode-select --install' · Ubuntu 'sudo apt install git'"
command -v python3 >/dev/null && ok "python3 $(python3 --version | awk '{print $2}')" || no "python3 missing"
if [ "$MISSING" = 1 ]; then
  echo; echo "Install the missing tools above yourself (they need an administrator), then re-run this script."; exit 1
fi

echo "== 2. Python packages (user install, no sudo)"
PIP="python3 -m pip install --user --quiet"
python3 -c "import numpy, PIL" 2>/dev/null || $PIP numpy pillow
python3 -c "import faster_whisper" 2>/dev/null || $PIP faster-whisper
python3 -c "import cv2; assert cv2.__version__.startswith('4')" 2>/dev/null || $PIP "opencv-python-headless<5"
python3 -c "import faster_whisper, cv2, numpy, PIL; print('  [x] python deps ok')"

echo "== 3. Whisper model (one-time local download, ~480 MB for 'small'; audio never leaves this machine)"
python3 - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("small", device="cpu", compute_type="int8")
print("  [x] whisper 'small' model ready")
PY

echo "== 4. HyperFrames skills + browser"
npx --yes skills add heygen-com/hyperframes -g -a claude-code -y -s hyperframes -s hyperframes-cli -s hyperframes-registry -s media-use
npx --yes hyperframes telemetry disable >/dev/null 2>&1 || true
npx --yes hyperframes browser ensure
npx --yes hyperframes doctor || true

echo "== 5. video-editor skill"
mkdir -p "$SKILLS"
if [ -e "$SKILLS/video-editor" ] && [ "$(readlink "$SKILLS/video-editor")" != "$REPO/.claude/skills/video-editor" ]; then
  echo "  ! $SKILLS/video-editor already exists and is not a link to this repo; leaving it alone. Inspect it, then"
  echo "    remove it yourself if it should be replaced:  ls -la \"$SKILLS/video-editor\""
else
  ln -sfn "$REPO/.claude/skills/video-editor" "$SKILLS/video-editor" && ok "linked $SKILLS/video-editor"
fi
# Skills installed under ~/.agents/skills by other tools: link (don't copy) any that Claude can't see.
if [ -d "$HOME/.agents/skills" ]; then
  for d in "$HOME/.agents/skills"/*/; do
    n="$(basename "$d")"; [ -e "$SKILLS/$n" ] || { ln -s "$d" "$SKILLS/$n" && ok "linked agents skill $n"; }
  done
fi

echo "== 6. Verify"
"$SKILLS/video-editor/scripts/ve" doctor
