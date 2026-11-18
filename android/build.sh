#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install buildozer cython
python3 -m pip install -r android/requirements-android.txt

PYWEBVIEW_DIR="$(python3 -c 'import pathlib, webview; print(pathlib.Path(webview.__file__).resolve().parent)')"
JAR="$PYWEBVIEW_DIR/lib/pywebview-android.jar"
if [[ ! -f "$JAR" ]]; then
    echo "Не найден pywebview-android.jar: $JAR" >&2
    exit 1
fi
cp "$JAR" android/pywebview-android.jar

cd android
buildozer -v android debug
