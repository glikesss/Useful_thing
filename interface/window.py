from pathlib import Path


class MathLabWindow:
    """Desktop application window."""

    def __init__(self, *, debug=False):
        self.debug = debug

        from .bridge import MathLabBridge
        self.bridge = MathLabBridge()

        self.window = None

    def run(self):
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError(
                "pywebview не установлен. Выполните: "
                "python -m pip install -r requirements.txt"
            ) from exc

        html_path = (
            Path(__file__).resolve().parent
            / "html"
            / "index.html"
        )

        if not html_path.is_file():
            raise FileNotFoundError(
                f"GUI файл не найден: {html_path}"
            )

        self.window = webview.create_window(
            title="MathLab",
            url="interface/html/index.html",
            js_api=self.bridge,
            width=1440,
            height=900,
            min_size=(1000, 650),
            background_color="#111827",
            text_select=True,
        )

        self.bridge._set_window(self.window)
        webview.start(debug=self.debug)

