#!/usr/bin/env bash
set -euo pipefail

DEST="samples"
mkdir -p "$DEST"

echo "Downloading short public-domain audio samples..."

# LibriVox sample (public domain). If links break, replace with valid ones.
curl -L -o "$DEST/example.wav" \
  https://www2.cs.uic.edu/~i101/SoundFiles/gettysburg.wav

cat > "$DEST/example_expected.txt" << 'EOF'
four score and seven years ago our fathers brought forth on this continent a new nation, conceived in liberty, and dedicated to the proposition that all men are created equal.
EOF

echo "Samples saved under $DEST/"

