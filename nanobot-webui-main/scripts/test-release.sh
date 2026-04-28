#!/usr/bin/env bash
# Pre-release smoke test: publish to TestPyPI → install in isolated venv → verify
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv-test-release"
PKG="nanobot-webui"

echo "==> 1/4  Building and publishing to TestPyPI..."
cd "$ROOT"
make publish-test

# Read current version from pyproject.toml
VERSION=$(python3 -c "
import re, pathlib
m = re.search(r'^version\s*=\s*\"(.+?)\"', pathlib.Path('pyproject.toml').read_text(), re.M)
print(m.group(1))
")
echo "    Version: $VERSION"

echo "==> 2/4  Creating isolated test venv at $VENV ..."
rm -rf "$VENV"
python3 -m venv "$VENV"
source "$VENV/bin/activate"

echo "==> 3/4  Installing $PKG==$VERSION from TestPyPI (retrying up to 3 min for index sync)..."
pip install --upgrade pip --quiet

# Step A: install all dependencies from real PyPI first
pip install --quiet \
  fastapi "uvicorn[standard]" PyJWT bcrypt python-multipart boto3 typer \
  "nanobot-ai" loguru rich

# Step B: install only our package (no-deps) from TestPyPI, retrying until the index syncs
INSTALLED=false
for i in $(seq 1 18); do
  if pip install \
    --index-url https://test.pypi.org/simple/ \
    --no-deps \
    "$PKG==$VERSION" --quiet 2>/dev/null; then
    INSTALLED=true
    break
  fi
  echo "    Not yet available, waiting 10s... ($i/18)"
  sleep 10
done

if [ "$INSTALLED" != "true" ]; then
  echo "    [FAIL] $PKG==$VERSION not found on TestPyPI after 3 minutes. Aborting."
  deactivate
  rm -rf "$VENV"
  exit 1
fi

echo "==> 4/4  Smoke tests..."

# CLI exists
nanobot --help | grep -q "webui" && echo "    [OK] nanobot --help"

# webui sub-command
nanobot webui --help | grep -q "port" && echo "    [OK] nanobot webui --help"

# Frontend assets are bundled
SITE=$(python3 -c "import site; print(site.getsitepackages()[0])")
DIST_INDEX="$SITE/webui/web/dist/index.html"
if [ -f "$DIST_INDEX" ]; then
  echo "    [OK] Frontend bundled: $DIST_INDEX"
else
  echo "    [FAIL] Frontend missing: $DIST_INDEX"
  deactivate
  rm -rf "$VENV"
  exit 1
fi

deactivate
rm -rf "$VENV"
echo ""
echo "All checks passed for $PKG==$VERSION. Ready to publish to PyPI."
echo "    make publish"
