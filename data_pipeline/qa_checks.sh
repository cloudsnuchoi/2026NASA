#!/usr/bin/env bash
# Run data_pipeline/qa_checks.sql against fieldshift in a READ ONLY session and summarise.
# Usage: PGHOST=127.0.0.1 PGPORT=5433 PGUSER=hk PGDATABASE=fieldshift data_pipeline/qa_checks.sh [out.txt]
# Exit code: 1 if any FAIL, else 0. Password comes from ~/.pgpass or PGPASSWORD.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${1:-/dev/stdout}"
export PGOPTIONS="-c default_transaction_read_only=on -c client_min_messages=warning"
res="$(psql -X -q -v ON_ERROR_STOP=1 -f "$here/qa_checks.sql")"
printf '%s\n' "$res" > "$out"
fails=$(grep -c ' | FAIL$' <<<"$res" || true)
warns=$(grep -c ' | WARN$' <<<"$res" || true)
passes=$(grep -c ' | PASS$' <<<"$res" || true)
echo "qa_checks: PASS=$passes WARN=$warns FAIL=$fails" >&2
grep -E ' \| (FAIL|WARN)$' <<<"$res" >&2 || true
[ "$fails" -eq 0 ]
