# MathLab для Android

Сборка рассчитана на Linux/WSL и устройства ARM64 (в том числе Android 14).

## Подготовка

Нужны Python 3, Java JDK 17, Buildozer, Android SDK/NDK и системные зависимости Buildozer.
На Arch Linux установите зависимости Buildozer из актуальной документации проекта; на Ubuntu/WSL — пакеты build-essential, git, zip, unzip, openjdk-17-jdk, python3-dev, libffi-dev, libssl-dev, zlib1g-dev и libncurses-dev.

## Сборка debug APK

Из корня репозитория:

```bash
bash android/build.sh
```

Скрипт устанавливает Python-зависимости, извлекает Android JAR из установленного pywebview и запускает Buildozer.

APK появится в `android/bin/`.

## Ограничения текущего этапа

- Сборка APK ещё не означает, что импорт/экспорт файлов адаптирован к Android: desktop file dialogs pywebview на Android не поддерживаются.
- Совместимость SciPy, Pandas и Matplotlib проверяется фактической сборкой на Android toolchain.
- После первой сборки необходимо проверить запуск, MathLive, вычисления, построение графиков и память на реальном устройстве.
