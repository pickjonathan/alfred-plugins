#!/bin/bash
#
# Run the workflow's test suite: Python unit/integration tests + bash script
# tests. Used locally and by CI.

set -uo pipefail

cd "$(dirname "$0")" || exit 1

PY="${PYTHON:-python3}"
rc=0

echo "== Python tests =="
"$PY" -m unittest discover -s tests -p 'test_*.py' -v || rc=1

echo
echo "== Bash script tests =="
bash tests/test_scripts.sh || rc=1

echo
if [ "$rc" -eq 0 ]; then
  echo "All tests passed."
else
  echo "Some tests FAILED."
fi
exit "$rc"
