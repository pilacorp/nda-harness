"""Choose a Hindsight bank through the control-plane page."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
import secrets
import threading
from urllib.parse import parse_qs, urlencode, urlsplit
import webbrowser

BANK_PAGE = 'https://hindsight.pila.vn/harness/bank'
_BANK_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,190}')


def valid_bank_id(bank_id):
    """A Hindsight bank id safe to store in the local profile."""
    return isinstance(bank_id, str) and len(bank_id.encode()) <= 192 and _BANK_ID.fullmatch(bank_id) is not None


def loopback_redirect(value):
    """Return a parsed http loopback URL, or None when the redirect is not local."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme != 'http' or parsed.username or parsed.password or parsed.hostname not in ('127.0.0.1', 'localhost'):
        return None
    if parsed.port is None:
        return None
    return parsed


def await_bank_choice(*, opener=None, timeout=120, page=BANK_PAGE):
    """Open the bank page and accept one matching loopback choice."""
    state = secrets.token_urlsafe(24)
    chosen = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlsplit(self.path).query)
            got_state = (query.get('state') or [''])[0]
            got_bank = (query.get('bank_id') or [''])[0]
            matched = len(got_state) == len(state) and secrets.compare_digest(got_state, state)
            if not matched or not valid_bank_id(got_bank):
                body = b'Bank selection was rejected.'
                self.send_response(400)
            else:
                chosen['bank_id'] = got_bank
                body = b'Bank selected. You can close this tab.'
                self.send_response(200)
                done.set()
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            return

    server = HTTPServer(('127.0.0.1', 0), Handler)
    port = server.server_address[1]
    redirect = f'http://127.0.0.1:{port}/callback'
    url = page + '?' + urlencode({'redirect_uri': redirect, 'state': state})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        (opener or webbrowser.open)(url)
        if not done.wait(timeout):
            return {'status': 'needs_bank', 'bank_id': 'pending', 'url': url}
        return {'status': 'ready', 'bank_id': chosen['bank_id']}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
