import json
import os
import smtplib
import ssl
from contextlib import closing
from email.errors import HeaderParseError
from email.headerregistry import Address
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
SENDER = "welcome@scherger.cloud"
SMTP_HOST = "smtp.mx.cloudflare.net"
SMTP_PORT = 465
FORM_PATH = Path(__file__).with_name("index.html")


def send_email(recipient, token):
    message = EmailMessage()
    message["From"] = SENDER
    message["To"] = recipient
    message["Subject"] = "Welcome to Acme"
    message.set_content("Thanks for signing up.")

    smtp = smtplib.SMTP_SSL(
        SMTP_HOST, SMTP_PORT, timeout=10, context=ssl.create_default_context()
    )
    with closing(smtp):
        smtp.login("api_token", token)
        smtp.send_message(message, to_addrs=[recipient])


class Handler(BaseHTTPRequestHandler):
    timeout = 10

    def respond(self, status, payload):
        self.respond_bytes(status, json.dumps(payload).encode("utf-8"), "application/json")

    def respond_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            self.respond(404, {"error": "Route not found."})
            return
        self.respond_bytes(200, FORM_PATH.read_bytes(), "text/html")

    def do_POST(self):
        if self.path != "/send":
            self.respond(404, {"error": "Route not found."})
            return
        if self.headers.get("Host") not in {f"{HOST}:{PORT}", f"localhost:{PORT}"}:
            self.respond(403, {"error": "Use the local service address."})
            return
        if self.headers.get_content_type() != "application/json":
            self.respond(415, {"error": "Use Content-Type: application/json."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.respond(400, {"error": "Invalid Content-Length."})
            return
        if length > 4096:
            self.respond(413, {"error": "Request body is too large."})
            return
        if length <= 0:
            self.respond(400, {"error": "Provide a JSON request body."})
            return

        try:
            payload = json.loads(self.rfile.read(length))
            recipient = payload.get("to") if isinstance(payload, dict) else None
            if not isinstance(recipient, str) or not recipient.isascii():
                raise ValueError
            address = Address(addr_spec=recipient)
            if not address.username or not address.domain or address.addr_spec != recipient:
                raise ValueError
        except TimeoutError:
            self.respond(408, {"error": "Timed out reading the request body."})
            return
        except (ValueError, HeaderParseError, IndexError, RecursionError):
            self.respond(400, {"error": "Provide one email address in the to field."})
            return

        try:
            send_email(address.addr_spec, self.server.token)
        except smtplib.SMTPAuthenticationError as exc:
            self.respond(502, {"error": "Cloudflare rejected SMTP authentication.", "smtp_code": exc.smtp_code})
            return
        except smtplib.SMTPRecipientsRefused as exc:
            code, _ = exc.recipients[address.addr_spec]
            self.respond(502, {"error": "Cloudflare rejected the recipient.", "smtp_code": code})
            return
        except smtplib.SMTPResponseException as exc:
            self.respond(502, {"error": "Cloudflare rejected the SMTP request.", "smtp_code": exc.smtp_code})
            return
        except OSError:
            self.respond(502, {"error": "SMTP connection to Cloudflare failed."})
            return

        self.respond(200, {"status": "accepted", "from": SENDER, "to": address.addr_spec})


def main():
    token = os.environ.get("TOKEN")
    if not token:
        raise SystemExit("Set TOKEN in .env.secret and run with uv run --env-file .env.secret app.py.")
    with ThreadingHTTPServer((HOST, PORT), Handler) as server:
        server.token = token
        print(f"Listening on http://{HOST}:{PORT}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
