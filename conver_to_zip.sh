#!/usr/bin/env bash

SRC="${1:?Usage: $(basename "$0") <source_dir> <output_dir>}"
OUT="${2:?Usage: $(basename "$0") <source_dir> <output_dir>}"

mkdir -p "$OUT"

for dir in "$SRC"/*/; do
    [[ -d "$dir" ]] || continue
    name=$(basename "$dir")
    (cd "$dir" && zip -qr "$OUT/$name.zip" .)
    echo "Archived $name"
done
