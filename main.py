import os
import threading
import webbrowser
from functools import wraps
from urllib.parse import urlparse, parse_qs
import time

import pyautogui
import psutil
from dotenv import load_dotenv
from flask import Flask, Response, request, render_template, jsonify

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

AUTH_USERNAME = os.environ.get('WEB_USERNAME')
AUTH_PASSWORD = os.environ.get('WEB_PASSWORD')

def check_auth(username, password):
    if not AUTH_USERNAME or not AUTH_PASSWORD:
        return False
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    return Response(
        'ログインが必要です', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

now_page = None

@app.route('/')
@requires_auth
def index():
    return render_template("index.html", username=AUTH_USERNAME)

def get_youtube_video_id(url: str):
    """YouTubeのURLから動画IDを抽出する"""
    if not url:
        return None
    parsed = urlparse(url)

    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith(("/shorts/", "/embed/")):
            return parsed.path.split("/")[2]

    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")

    return None

@app.route('/youtube')
@requires_auth
def youtube():
    video_id = request.args.get('p')
    if not video_id:
        return "動画IDが無効です。", 400
    return render_template("youtube.html", videoid=video_id)

@app.route('/page')
@requires_auth
def page():
    return render_template("page.html")

@app.route('/api/status')
@requires_auth
def api_pcstatus():
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory_info = psutil.virtual_memory()
    disk_path = 'C:' if os.name == 'nt' else '/'
    try:
        disk_info = psutil.disk_usage(disk_path)
        disk_data = {
            "percent": disk_info.percent,
            "used": round(disk_info.used / (1024 ** 3), 2),
            "total": round(disk_info.total / (1024 ** 3), 2)
        }
    except Exception:
        disk_data = {"percent": 0, "used": 0, "total": 0}

    return jsonify({
        "cpu": cpu_usage,
        "memory": {
            "percent": memory_info.percent,
            "used": round(memory_info.used / (1024 ** 3), 2),
            "total": round(memory_info.total / (1024 ** 3), 2)
        },
        "disk": disk_data
    })

@app.get('/api/page')
@requires_auth
def api_get_page():
    return jsonify({
        "status": "ok",
        "url": now_page
    })

@app.post('/api/youtube')
@requires_auth
def api_youtube_open():
    data = request.get_json()
    url = data.get('url') if data else None
    
    video_id = get_youtube_video_id(url)
    if not video_id:
        return jsonify({"status": "error", "error": "無効な動画URLです。"}), 400
    
    global now_page
    now_page = f"http://localhost:5000/youtube?p={video_id}"
    
    return jsonify({"status": "ok", "video_id": video_id})

def open_browser():
    time.sleep(1)
    webbrowser.open("http://localhost:5000/page")
    time.sleep(1)
    pyautogui.press('f11')

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)