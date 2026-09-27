
from flask import Flask
from threading import Thread

app = Flask(__name__)


@app.route("/")
def home():
    return "QTStudios is online."


def run() -> None:
    app.run(host="0.0.0.0", port=8080)


def keep_alive() -> None:
    t = Thread(target=run, daemon=True)
    t.start()
