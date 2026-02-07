#!/usr/bin/env bash
set -euo pipefail

OUT="/home/jch903/Desktop/overview.txt"
REPO="/media/jch903/fidelio/CLAUDOG/PortalRecruit"

cat > "$OUT" <<'HEADER'
==============================
PORTALRECRUIT PROJECT OVERVIEW
==============================

[1] Project Overview
- Repo: https://github.com/PortalRecruit/PortalRecruit
- Homepage: https://portalrecruit.github.io/PortalRecruit/
- App: https://buckets.streamlit.app
- Status: Active build. Focus: semantic player search + profile pages + AI scout breakdown + ingest pipeline.
- Goal: Natural-language, coach-speak search for players using Synergy/Sportradar data; results explain "why" and provide film/context.
- .env location: 
  - /media/jch903/fidelio/CLAUDOG/PortalRecruit/.env
  - backup: /home/jch903/.secrets/.env

HEADER

echo "" >> "$OUT"
echo "=========================" >> "$OUT"
echo "[2] Repository Tree" >> "$OUT"
echo "=========================" >> "$OUT"
(
  cd "$REPO"
  tree -a -L 3
) >> "$OUT"

echo "" >> "$OUT"
echo "===============================================" >> "$OUT"
echo "[3] Scripts / Config / HTML / Dictionary Files" >> "$OUT"
echo "===============================================" >> "$OUT"

# Helper to group by directory
grouped_cat() {
  local title="$1"; shift
  echo "" >> "$OUT"
  echo "----- ${title} -----" >> "$OUT"
  ( cd "$REPO" && find . -type f "$@" | sed 's|^\./||' | sort ) | \
  while read -r f; do
    echo "" >> "$OUT"
    echo "### FILE: $f" >> "$OUT"
    echo "----------------------------------------" >> "$OUT"
    cat "$REPO/$f" >> "$OUT"
  done
}

# Scripts (root/scripts + any scripts in repo)
grouped_cat "SCRIPTS (.py in scripts/)" -path './scripts/*' -name '*.py'

# Config files
grouped_cat "CONFIG (.toml/.yaml/.yml/.json/.ini)" \( -name '*.toml' -o -name '*.yaml' -o -name '*.yml' -o -name '*.json' -o -name '*.ini' \)

# HTML files
grouped_cat "HTML FILES" -name '*.html'

# Dictionary files (coach dictionary, etc.)
grouped_cat "DICTIONARY FILES (coach_dictionary, etc.)" \( -iname '*dictionary*.py' -o -iname '*dictionary*.json' \)

echo "" >> "$OUT"
echo "============================" >> "$OUT"
echo "[4] Database Deep Overview" >> "$OUT"
echo "============================"

DB="$REPO/data/skout.db"
VECTOR_DB="$REPO/data/vector_db/chroma.sqlite3"

if [ -f "$DB" ]; then
  echo "" >> "$OUT"
  echo "---- SQLite: skout.db ----" >> "$OUT"
  sqlite3 "$DB" ".tables" >> "$OUT"
  echo "" >> "$OUT"
  sqlite3 "$DB" ".schema" >> "$OUT"
  echo "" >> "$OUT"
  echo "Table row counts:" >> "$OUT"
  sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | while read -r t; do
    sqlite3 "$DB" "SELECT '$t' AS table_name, COUNT(*) AS rows FROM $t;" >> "$OUT"
  done
  echo "" >> "$OUT"
  echo "Sample rows (first 3):" >> "$OUT"
  sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | while read -r t; do
    echo "" >> "$OUT"
    echo "## $t (first 3)" >> "$OUT"
    sqlite3 -header -column "$DB" "SELECT * FROM $t LIMIT 3;" >> "$OUT"
  done
else
  echo "skout.db not found at $DB" >> "$OUT"
fi

if [ -f "$VECTOR_DB" ]; then
  echo "" >> "$OUT"
  echo "---- Chroma SQLite: chroma.sqlite3 ----" >> "$OUT"
  sqlite3 "$VECTOR_DB" ".tables" >> "$OUT"
  echo "" >> "$OUT"
  sqlite3 "$VECTOR_DB" ".schema" >> "$OUT"
  echo "" >> "$OUT"
  echo "Chroma table row counts:" >> "$OUT"
  sqlite3 "$VECTOR_DB" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" | while read -r t; do
    sqlite3 "$VECTOR_DB" "SELECT '$t' AS table_name, COUNT(*) AS rows FROM $t;" >> "$OUT"
  done
else
  echo "chroma.sqlite3 not found at $VECTOR_DB" >> "$OUT"
fi

echo "" >> "$OUT"
echo "==============================" >> "$OUT"
echo "[5] Special Notes for a New LLM" >> "$OUT"
echo "==============================" >> "$OUT"
cat >> "$OUT" <<'NOTES'
- Main repo path: /media/jch903/fidelio/CLAUDOG/PortalRecruit
- Streamlit app main file: src/dashboard/Home.py
- CSS/branding: www/streamlit.css, www/index.html, www/PORTALRECRUIT_LOGO.png
- Vector DB path: data/vector_db (Chroma)
- Core DB: data/skout.db (SQLite)
- Semantic search helper: src/search/semantic.py
- Ingestion helpers: src/processing/generate_embeddings.py, src/processing/enrich_plays.py
- Do NOT commit logs; do commit models via LFS if needed.
- .env contains API keys; never print or commit it.
NOTES

echo "✅ Overview written to $OUT"
