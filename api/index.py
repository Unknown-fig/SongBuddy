"""
Vercel Serverless Function entry point for SongBuddy.
Adapts the SongBuddy HTTP handler for Vercel's Serverless Python runtime.
"""
import os
import sys
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
    pass
