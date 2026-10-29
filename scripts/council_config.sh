#!/usr/bin/env bash
# Council settings. Personal values live in ../council.conf (git-ignored; copy
# council.conf.example to create it). Anything unset falls back to the defaults below.
#   source council_config.sh   -> sets the variables (used by the other scripts)
#   bash council_config.sh     -> prints them, one KEY=value per line (used by the skill and integrity_check.py)
_council_conf="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/council.conf"
# shellcheck source=/dev/null
[ -f "$_council_conf" ] && . "$_council_conf"
COUNCIL_DIR="${COUNCIL_DIR:-$HOME/Documents/claude-council}"
REVIEW_LANGUAGE="${REVIEW_LANGUAGE:-English}"
EXPLAIN_LANGUAGE="${EXPLAIN_LANGUAGE:-English}"
RESEARCH_CONTEXT="${RESEARCH_CONTEXT:-}"
JOURNAL_DIR="$COUNCIL_DIR/journal"

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  printf 'COUNCIL_DIR=%s\nJOURNAL_DIR=%s\nREVIEW_LANGUAGE=%s\nEXPLAIN_LANGUAGE=%s\nRESEARCH_CONTEXT=%s\nCONFIG_FILE=%s\n' \
    "$COUNCIL_DIR" "$JOURNAL_DIR" "$REVIEW_LANGUAGE" "$EXPLAIN_LANGUAGE" "$RESEARCH_CONTEXT" \
    "$([ -f "$_council_conf" ] && echo "$_council_conf" || echo "none (defaults)")"
fi
