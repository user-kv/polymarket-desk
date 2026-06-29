"""Put the repo root on sys.path so `import institute...` works from anywhere
(carries over the papertrader pytest-from-root fix)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
