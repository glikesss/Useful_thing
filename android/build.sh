#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv-android"
if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install buildozer cython
python -m pip install -r android/requirements-android.txt

PYWEBVIEW_DIR="$(python -c 'import pathlib, webview; print(pathlib.Path(webview.__file__).resolve().parent)')"
JAR="$PYWEBVIEW_DIR/lib/pywebview-android.jar"
if [[ ! -f "$JAR" ]]; then
    echo "Не найден pywebview-android.jar: $JAR" >&2
    exit 1
fi
cp "$JAR" android/pywebview-android.jar

cd android
buildozer -v android debug
