#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-/tmp/postovni-poukazka-print-validation}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
RENDER_TIMEOUT_SECONDS="${RENDER_TIMEOUT_SECONDS:-20}"

if [ ! -x "$CHROME" ]; then
  echo "Chrome not found at: $CHROME" >&2
  echo "Set CHROME=/path/to/chrome and run again." >&2
  exit 1
fi

cd "$ROOT_DIR"
mkdir -p "$OUT_DIR"
HTML_URL="$(python3 -c 'from pathlib import Path; print(Path("postovni_poukazka_b.html").resolve().as_uri())')"

run_with_timeout() {
  local seconds="$1"
  shift
  "$@" &
  local pid="$!"
  local elapsed=0

  while kill -0 "$pid" 2>/dev/null; do
    if [ "$elapsed" -ge "$seconds" ]; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  wait "$pid"
}

render_pdf() {
  local name="$1"
  local query="$2"
  local pdf="$OUT_DIR/$name.pdf"
  local log="$OUT_DIR/$name.chrome.log"
  local profile="$OUT_DIR/chrome-profile-$name"
  rm -rf "$profile"
  if ! run_with_timeout "$RENDER_TIMEOUT_SECONDS" "$CHROME" \
    --headless=new \
    --disable-gpu \
    --disable-extensions \
    --disable-background-networking \
    --disable-sync \
    --disable-component-update \
    --no-first-run \
    --no-default-browser-check \
    --no-pdf-header-footer \
    --run-all-compositor-stages-before-draw \
    --virtual-time-budget=1000 \
    --user-data-dir="$profile" \
    --print-to-pdf="$pdf" \
    "$HTML_URL$query" >"$log" 2>&1; then
    if [ ! -s "$pdf" ]; then
      echo "Chrome failed while rendering $name. Log:" >&2
      sed -n '1,120p' "$log" >&2
      exit 1
    fi
  fi
  if [ ! -s "$pdf" ]; then
    echo "Chrome did not create PDF: $pdf. Log:" >&2
    sed -n '1,120p' "$log" >&2
    exit 1
  fi
  echo "$pdf"
}

render_png() {
  local pdf="$1"
  local png="${pdf%.pdf}.png"
  if ! sips -s format png "$pdf" --out "$png" >/dev/null; then
    echo "sips failed while converting PDF to PNG: $pdf" >&2
    exit 1
  fi
  if [ ! -s "$png" ]; then
    echo "sips did not create PNG: $png" >&2
    exit 1
  fi
  echo "$png"
}

FULL_PDF="$(render_pdf full '?validation=1')"
echo "Rendered full PDF: $FULL_PDF"
BACKGROUND_PDF="$(render_pdf background '?validation=1&hideText=1')"
echo "Rendered background-only PDF: $BACKGROUND_PDF"
BLANK_PDF="$(render_pdf blank '?validation=1&printBlank=1')"
echo "Rendered blank-form PDF: $BLANK_PDF"

FULL_PNG="$(render_png "$FULL_PDF")"
BACKGROUND_PNG="$(render_png "$BACKGROUND_PDF")"
BLANK_PNG="$(render_png "$BLANK_PDF")"

python3 "$ROOT_DIR/scripts/compare-print-layout.py" \
  --full "$FULL_PNG" \
  --background "$BACKGROUND_PNG" \
  --blank "$BLANK_PNG"

echo "Generated validation files in: $OUT_DIR"
