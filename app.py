from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import os
import threading
import logging
from logging.handlers import WatchedFileHandler


def create_app():
    app = Flask(__name__)
    auth = HTTPBasicAuth()

    log_dir = "/var/log/tts"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "tts.log")
    handler = WatchedFileHandler(log_path)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s"
    ))
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    @app.before_request
    def log_request_info():
        request._start_time = None
        app.logger.info(f"{request.remote_addr} {request.method} {request.path}")

    @app.after_request
    def log_response_info(response):
        status = response.status_code
        app.logger.info(f"{request.remote_addr} {request.method} {request.path} -> {status}")
        return response

    user_string = os.getenv("USERS", "")
    users = {}
    for entry in user_string.split(","):
        parts = entry.strip().split(":", 1)
        if len(parts) == 2:
            username, password = parts
            users[username] = generate_password_hash(password)

    SAVE = "/app/generated_files"
    VOICE = "/app/voices"
    AUDIO = "audio.wav"
    MODEL = os.path.join(VOICE, "de_DE-thorsten-high.onnx")
    CONFIG = os.path.join(VOICE, "de_DE-thorsten-high.onnx.json")
    os.makedirs(SAVE, exist_ok=True)
    status = {"running": False}

    @auth.verify_password
    def verify(u, p):
        if u in users and check_password_hash(users[u], p):
            return u

    @app.route('/')
    @auth.login_required
    def index():
        exists = os.path.exists(os.path.join(SAVE, AUDIO))
        return render_template("index.html",
                               filename=AUDIO if exists else None,
                               processing=status["running"])

    @app.route('/generate', methods=['POST'])
    @auth.login_required
    def generate():
        text = request.form.get("text", "").strip()
        out = os.path.join(SAVE, AUDIO)
        if os.path.exists(out):
            os.remove(out)
        status["running"] = True

        def task():
            try:
                subprocess.run([
                    "piper", "-m", MODEL,
                    "-c", CONFIG,
                    "-f", out
                ], input=text.encode("utf-8"), check=True)
                app.logger.info("TTS completed")
            except Exception as e:
                app.logger.error(f"TTS error: {e}")
            finally:
                status["running"] = False

        threading.Thread(target=task, daemon=True).start()
        return "", 204

    @app.route('/delete', methods=['POST'])
    @auth.login_required
    def delete():
        f = os.path.join(SAVE, AUDIO)
        if os.path.exists(f):
            os.remove(f)
            app.logger.info("Deleted audio.wav")
        status["running"] = False
        return "", 204

    @app.route('/audio/<fn>')
    @auth.login_required
    def audio(fn):
        return send_from_directory(SAVE, fn)

    @app.route('/status')
    @auth.login_required
    def st():
        return jsonify(processing=status["running"])

    return app


if __name__ == "__main__":
    from waitress import serve
    application = create_app()
    serve(application, host="0.0.0.0", port=5000)
