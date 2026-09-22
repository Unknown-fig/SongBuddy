"""
Vercel Serverless Function entry point for SongBuddy.
Adapts the SongBuddy HTTP handler for Vercel's Serverless Python runtime.
"""
import os
import sys
import urllib.parse
from pathlib import Path

# Mark environment as running in serverless Vercel
os.environ["VERCEL"] = "1"

# Add project root directory to Python path
ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import SongBuddyHandler

class handler(SongBuddyHandler):
    """
    Vercel Serverless Function entry handler.
    Vercel looks for a class named `handler` inheriting from BaseHTTPRequestHandler.
    """
    def _normalize_vercel_path(self):
        """
        Recovers the real original requested path from Vercel rewrites or headers.
        """
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # 1. Check for explicit __path__ parameter injected via vercel.json rewrites
        real_path = None
        if "__path__" in params and params["__path__"]:
            real_path = params["__path__"][0]
        else:
            # 2. Check for Vercel edge proxy routing headers
            forwarded = (
                self.headers.get("x-forwarded-uri")
                or self.headers.get("x-matched-path")
                or self.headers.get("x-vercel-forwarded-for")
            )
            if forwarded and forwarded.startswith("/api"):
                real_path = urllib.parse.urlparse(forwarded).path

        if real_path:
            clean_params = {k: v for k, v in params.items() if k != "__path__"}
            query_str = urllib.parse.urlencode(clean_params, doseq=True)
            self.path = f"{real_path}?{query_str}" if query_str else real_path

    def do_GET(self):
        self._normalize_vercel_path()
        super().do_GET()

    def do_POST(self):
        self._normalize_vercel_path()
        super().do_POST()

    def do_OPTIONS(self):
        self._normalize_vercel_path()
        super().do_OPTIONS()
