"""Jembatan HTTP untuk Freefire-TCP-BOT.
Taruh file ini di folder yang sama dengan main.py, lalu jalankan di VPS/Railway/Render:
    pip install flask
    BOT_API_KEY=rahasia123 python bridge.py
"""
import os, re, sys, json, subprocess, threading, collections
from flask import Flask, request, jsonify

DIR = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ["BOT_API_KEY"]
EMOTES = os.path.join(DIR, "emotes.json")

BOOT = os.urandom(4).hex()          # berubah setiap bridge dijalankan ulang
logs = collections.deque(maxlen=1000)
count = 0                            # total baris yang pernah ditulis (tidak pernah mundur)
lock = threading.Lock()
proc = None
app = Flask(__name__)


@app.before_request
def auth():
    if request.headers.get("x-api-key") != KEY:
        return jsonify(error="API key salah"), 401


def add(line):
    global count
    with lock:
        logs.append(line)
        count += 1


def pump(p):
    for line in p.stdout:
        add(line.rstrip())
    add("[panel] proses berhenti")


def running():
    return proc is not None and proc.poll() is None


def start():
    global proc
    if running():
        return
    proc = subprocess.Popen([sys.executable, "-u", "main.py"], cwd=DIR,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            bufsize=1, errors="replace")
    threading.Thread(target=pump, args=(proc,), daemon=True).start()
    add("[panel] bot dijalankan")


def stop():
    if running():
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()


@app.get("/status")
def status():
    return jsonify(running=running(), pid=proc.pid if running() else None)


@app.get("/logs")
def get_logs():
    # first = nomor urut baris pertama yang dikirim; client memakainya agar "hapus log"
    # tetap benar walau buffer penuh atau halaman dimuat ulang.
    with lock:
        lines = list(logs)
        return jsonify(lines=lines, first=count - len(lines), count=count, boot=BOOT)


@app.post("/clear")
def r_clear():
    with lock:
        logs.clear()
        return jsonify(ok=True, count=count)


@app.post("/start")
def r_start():
    start(); return jsonify(running=running())


@app.post("/stop")
def r_stop():
    stop(); return jsonify(running=running())


@app.post("/restart")
def r_restart():
    stop(); start(); return jsonify(running=running())


@app.get("/emotes")
def get_emotes():
    with open(EMOTES, encoding="utf-8") as f:
        return jsonify(data=json.load(f))


@app.put("/emotes")
def put_emotes():
    data = (request.get_json(silent=True) or {}).get("data")
    if data is None:
        return jsonify(error="Data kosong"), 400
    with open(EMOTES, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify(ok=True)


@app.get("/commands")
def commands():
    """Pindai main.py dan kembalikan semua string perintah (/xxx atau !x) yang ada di kode."""
    try:
        with open(os.path.join(DIR, "main.py"), encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except OSError:
        return jsonify(commands=[])
    found = sorted(set(re.findall(r"""["']([/!][a-z][a-z0-9_]{0,19})(?=[\s"'])""", src)))
    return jsonify(commands=found)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
