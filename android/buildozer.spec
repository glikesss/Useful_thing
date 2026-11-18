[app]
title = MathLab
package.name = mathlab
package.domain = org.glikesss
source.dir = ..
source.include_exts = py,png,jpg,kv,atlas,html,css,js,jar
source.exclude_dirs = .git,.venv,venv,tests,__pycache__,.pytest_cache,bin,dist,build
version = 0.1.0

requirements = python3,android,pyjnius,pywebview,bottle,proxy_tools,typing_extensions,sympy,numpy,scipy,pandas,matplotlib,openpyxl

orientation = portrait,landscape
fullscreen = 0
android.permissions = INTERNET
android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.add_jars = android/pywebview-android.jar
android.accept_sdk_license = True
android.allow_backup = True
android.enable_androidx = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
