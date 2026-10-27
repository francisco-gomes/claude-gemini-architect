#!/usr/bin/env bash
# Fails if something that would be published contains private data.
#   bash scripts/check-private.sh            files tracked by git
#   bash scripts/check-private.sh --pack     files inside the npm tarball
#   bash scripts/check-private.sh --history  every commit (git log -p --all)
# Private terms: one extended regex per line (case-insensitive) in $PRIVATE_TERMS_FILE, default
# _privado/private-terms.txt. That file is never committed; without it only the generic patterns run (CI).
set -euo pipefail
cd "$(dirname "$0")/.."

GENERIC='/home/[a-z0-9_-]+/|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|npm_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9._%+-]+@(gmail|outlook|hotmail|yahoo|icloud)\.com'
TERMS_FILE="${PRIVATE_TERMS_FILE:-_privado/private-terms.txt}"
PATTERN="$GENERIC"
if [ -f "$TERMS_FILE" ]; then
  COUNT=0
  while IFS= read -r line; do
    case "$line" in ''|'#'*) continue ;; esac
    PATTERN="$PATTERN|$line"
    COUNT=$((COUNT + 1))
  done < "$TERMS_FILE"
  echo "private terms: $COUNT from $TERMS_FILE"
else
  echo "private terms: none ($TERMS_FILE not found; generic patterns only)"
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
case "${1:-}" in
  --pack)
    npm pack --silent --pack-destination "$WORK" > /dev/null
    tar -xzf "$WORK"/*.tgz -C "$WORK"
    ROOT="$WORK/package"
    FILES=$(cd "$ROOT" && find . -type f | sed 's|^\./||' | sort)
    ;;
  --history)
    git log -p --all -- . ':(exclude)scripts/check-private.sh' > "$WORK/history.txt"
    ROOT="$WORK"
    FILES="history.txt"
    ;;
  '')
    ROOT="."
    FILES=$(git ls-files | grep -vxF 'scripts/check-private.sh' || true)
    ;;
  *)
    echo "usage: bash scripts/check-private.sh [--pack|--history]" >&2
    exit 2
    ;;
esac

HITS=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if grep -nIiE "$PATTERN" "$ROOT/$f" > "$WORK/hit.txt" 2>/dev/null; then
    sed "s|^|$f:|" "$WORK/hit.txt"
    HITS=$((HITS + 1))
  fi
done <<< "$FILES"
echo "files with private data: $HITS"
if [ "$HITS" = 0 ]; then echo OK; else echo FAILED; exit 1; fi
