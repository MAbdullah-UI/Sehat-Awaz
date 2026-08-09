"""
Vercel Serverless Function: /api/tts

Runs on Vercel's Python runtime, same domain as the rest of the site
(madad-med.vercel.app) — so app.html can call it with a plain relative
fetch('/api/tts') and there is no CORS or separate-server config needed.

Uses Microsoft's free edge-tts service for a real Urdu voice
(ur-PK-AsadNeural). No API key required.
"""

from http.server import BaseHTTPRequestHandler
import json
import asyncio
import io
import edge_tts

DEFAULT_VOICE = "ur-PK-AsadNeural"  # ur-PK-UzmaNeural = female alternative


async def _synthesize(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


class handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body or b"{}")
            text = (data.get("text") or "").strip()
            voice = data.get("voice") or DEFAULT_VOICE

            if not text:
                self.send_response(400)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "no text provided"}).encode())
                return

            audio_bytes = asyncio.run(_synthesize(text, voice))
            if not audio_bytes:
                raise RuntimeError("edge_tts returned empty audio")

            self.send_response(200)
            self._cors_headers()
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            self.wfile.write(audio_bytes)
        except Exception as e:
            print(f"[Madad /api/tts] error: {e!r}")
            self.send_response(500)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())