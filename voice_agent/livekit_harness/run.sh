#!/usr/bin/env bash
# Run the option 1/2 scenarios through livekit/agents' own AgentSession test harness.
# Usage (from voice_agent/, inside the venv that has livekit-agents==1.8.3):
#   ./livekit_harness/run.sh
set -euo pipefail

LK_TAG="${LK_TAG:-livekit-agents@1.8.3}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${LK_CHECKOUT:-$HERE/.livekit-agents}"

if [ ! -d "$WORK/.git" ]; then
  git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$LK_TAG" \
    https://github.com/livekit/agents "$WORK"
fi
cp "$HERE"/test_zz_local_*.py "$WORK/tests/"

cd "$WORK"
VOICE_AGENT_DIR="$(dirname "$HERE")" python -m pytest -q -p no:cacheprovider \
  tests/test_zz_local_filter.py tests/test_zz_local_bargein.py "$@"
