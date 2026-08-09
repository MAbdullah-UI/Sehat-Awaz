"""
Madad TTS Bridge — tiny local server that lets 1.html (a static HTML file,
which cannot run Python) get real Urdu speech from Microsoft's free
edge-tts service.

WHY THIS EXISTS
----------------
edge-tts is a Python library. Browsers can't call it directly. This
server exposes one HTTP endpoint (POST /tts) that 1.html calls with
fetch(); the server runs edge-tts and streams back an MP3.

SETUP (one time)
-----------------
    pip install flask flask-cors edge-tts

RUN (every time you want TTS to work)
--------------------------------------
    python tts_server.py

This starts a server at http://127.0.0.1:5050
Leave this terminal window open while you use 1.html (via Live Server,
as before). Two things need to be running at once: Live Server (for the
page) and this script (for the voice).
"""

import asyncio
import io

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import edge_tts

app = Flask(__name__)
CORS(app)  # allow 1.html (served from a different port) to call this server

DEFAULT_VOICE = "ur-PK-AsadNeural"  # ur-PK-UzmaNeural = female alternative


async def _synthesize(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = data.get("voice") or DEFAULT_VOICE

    if not text:
        return jsonify({"error": "no text provided"}), 400

    try:
        audio_bytes = asyncio.run(_synthesize(text, voice))
        if not audio_bytes:
            return jsonify({"error": "edge_tts returned empty audio"}), 502
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/mpeg",
            as_attachment=False,
        )
    except Exception as e:
        print(f"[Madad TTS Bridge] error: {e!r}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Madad TTS Bridge chal raha hai: http://127.0.0.1:5050")
    print("Isay khula chhor do jab tak app.html use kar rahe ho.")
    app.run(host="127.0.0.1", port=5050, debug=False)
