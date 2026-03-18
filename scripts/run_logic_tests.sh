#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVIDENCE_FILE="$REPO_ROOT/evidence_sources.yaml"

get_source_path() {
  local name="$1"
  awk -v source_name="$name" '
    $0 ~ "^[[:space:]]*-[[:space:]]*name:[[:space:]]*"source_name"[[:space:]]*$" { found=1; next }
    found && $0 ~ "^[[:space:]]*path:[[:space:]]*" {
      gsub(/^[[:space:]]*path:[[:space:]]*/, "", $0);
      print $0;
      exit;
    }
  ' "$EVIDENCE_FILE"
}

BACKEND_PATH="${BACKEND_PATH:-$(get_source_path backend)}"
FRONTEND_PATH="${FRONTEND_PATH:-$(get_source_path web_admin)}"
ARTIFACTS_ROOT="${ARTIFACTS_ROOT:-$REPO_ROOT/artifacts/test-results}"

BACKEND_RESULTS="$ARTIFACTS_ROOT/backend"
FRONTEND_RESULTS="$ARTIFACTS_ROOT/frontend"
mkdir -p "$BACKEND_RESULTS" "$FRONTEND_RESULTS"

echo "Repo root:      $REPO_ROOT"
echo "Backend path:   $BACKEND_PATH"
echo "Frontend path:  $FRONTEND_PATH"
echo "Artifacts root: $ARTIFACTS_ROOT"

if [[ ! -d "$BACKEND_PATH" ]]; then
  echo "ERROR: Backend path not found: $BACKEND_PATH" >&2
  exit 1
fi
if [[ ! -d "$FRONTEND_PATH" ]]; then
  echo "ERROR: Frontend path not found: $FRONTEND_PATH" >&2
  exit 1
fi

if ! command -v dotnet >/dev/null 2>&1; then
  echo "ERROR: dotnet SDK not found in PATH." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found in PATH." >&2
  exit 1
fi

echo ""
echo "=== Backend restore ==="
(
  cd "$BACKEND_PATH"
  dotnet restore CoreV2.sln
)

echo ""
echo "=== Backend tests (.trx + .junit.xml) ==="
(
  cd "$BACKEND_PATH"
  dotnet test CoreV2.sln \
    --configuration Release \
    --results-directory "$BACKEND_RESULTS" \
    --logger "trx;LogFileName=backend_tests.trx" \
    --logger "junit;LogFilePath=$BACKEND_RESULTS/backend_tests.junit.xml"
)

echo ""
echo "=== Frontend install ==="
(
  cd "$FRONTEND_PATH"
  if [[ ! -d node_modules ]]; then
    npm install
  fi
)

echo ""
echo "=== Frontend unit tests (.junit.xml) ==="
(
  cd "$FRONTEND_PATH"
  npm test -- --reporter=default --reporter=junit --outputFile="$FRONTEND_RESULTS/frontend_tests.junit.xml"
)

echo ""
echo "=== Summary ==="
echo "Logic test run succeeded."
echo "Reports location: $ARTIFACTS_ROOT"
