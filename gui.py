import threading
import webview
from app import create_app

def run_flask():
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    window = webview.create_window(
        title="Lexium",
        url="http://127.0.0.1:5000",
        width=1200,
        height=800,
        resizable=True
    )

    webview.start()