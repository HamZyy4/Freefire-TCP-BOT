"""Jembatan HTTP untuk Freefire-TCP-BOT.
Taruh file ini di folder yang sama dengan main.py, lalu jalankan di VPS/Railway/Render:
    pip install flask
    BOT_API_KEY=rahasia123 python bridge.py
"""
import os, sys, json, subprocess, threading, collections
from flask import Flask, request, jsonify

DIR = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ["BOT_API_KEY"]
EMOTES = os.path.join(DIR, "emotes.json")
logs = collections.deque(maxlen=500)
proc = None
app = Flask(__name__)


@app.before_request
def auth():
    if request.headers.get("x-api-key") != KEY:
        return jsonify(error="API key salah"), 401


def pump(p):
    for line in p.stdout:
        logs.append(line.rstrip())
    logs.append("[panel] proses berhenti")


def running():
    return proc is not None and proc.poll() is None


def start():
    global proc
    if running():
        return
    proc = subprocess.Popen([sys.executable, "-u", "main.py"], cwd=DIR,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    threading.Thread(target=pump, args=(proc,), daemon=True).start()
    logs.append("[panel] bot dijalankan")


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
    return jsonify(lines=list(logs))


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
