"""
A paste-in page that runs on your own computer only.

    python -m scam_triage.web           # then open http://127.0.0.1:8765

It listens on 127.0.0.1, so nothing else on your network can reach it.
Messages are masked (see mask.py) before anything is sent to Jev.
"""

import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .cli import LABELS
from .engine import BE_CAREFUL, LIKELY_SCAM, check

HOST, PORT = "127.0.0.1", 8765
MAX_BODY = 20_000

_COLOURS = {LIKELY_SCAM: "#b3261e", BE_CAREFUL: "#8a5a00", "looks_ordinary": "#1e6b3a"}

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scam Check</title>
<style>
 body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; color: #1b1b1b; }}
 textarea {{ width: 100%; min-height: 9rem; font: inherit; padding: .6rem; box-sizing: border-box; }}
 button {{ font: inherit; padding: .5rem 1.2rem; margin-top: .5rem; }}
 .verdict {{ font-weight: 700; font-size: 1.3rem; margin-top: 1.5rem; }}
 .note {{ color: #555; font-size: .9rem; }}
</style></head><body>
<h1>Scam Check</h1>
<p class="note">Paste a text message or email. Codes, numbers, email addresses and links are masked before the
message is sent to the checker; link checks run here on your computer.</p>
<form method="post" action="/">
<textarea name="message" required placeholder="Paste the message here">{message}</textarea>
<button type="submit">Check</button>
</form>
{result}
</body></html>"""


def render_result(result) -> str:
    items = "".join(f"<li>{html.escape(r)}</li>" for r in result.reasons)
    mock = ('<p class="note">Mock mode: no TYPESAFE_API_KEY, so keyword rules stood in for Jev.</p>'
            if result.mode == "mock" else "")
    return (f'<p class="verdict" style="color:{_COLOURS[result.verdict]}">{LABELS[result.verdict]}</p>'
            f"<p><strong>Why:</strong></p><ul>{items}</ul>"
            f"<p><strong>What to do:</strong> {html.escape(result.advice)}</p>{mock}")


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, status: int = 200, content_type: str = "text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(PAGE.format(message="", result=""))

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send("Message too long.", status=413, content_type="text/plain; charset=utf-8")
            return
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        if self.headers.get("Content-Type", "").startswith("application/json"):
            message = json.loads(raw or "{}").get("message", "")
            result = check(message)
            self._send(json.dumps({"verdict": result.verdict, "reasons": result.reasons, "advice": result.advice,
                                   "mode": result.mode}), content_type="application/json")
            return
        message = parse_qs(raw).get("message", [""])[0]
        result = render_result(check(message)) if message.strip() else ""
        self._send(PAGE.format(message=html.escape(message), result=result))

    def log_message(self, fmt, *args):  # don't write pasted messages to the terminal log
        pass


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Scam Check running at http://{HOST}:{PORT}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
