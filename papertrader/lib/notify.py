"""
lib/notify.py — desktop notifications for meaningful events only.

Uses the BurntToast PowerShell module (installed 2026-06-16, confirmed working)
to pop a real Windows notification. Deliberately NOT wired into every routine
scan — only fires for events worth interrupting the user for:
  - a paper bet was actually placed
  - bets were settled (won/lost)
  - the weekly digest is ready

If BurntToast or PowerShell is unavailable for any reason, this fails silently
(logs a warning) rather than crashing the scan/settle/calibrate job — a missed
notification should never block the underlying paper-trading logic.
"""

import subprocess
import logging

logger = logging.getLogger("notify")


def send_toast(title, message):
    """Fire a Windows toast notification. Best-effort — never raises."""
    # Escape single quotes for embedding in a PowerShell single-quoted string.
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")
    ps_cmd = (
        "Import-Module BurntToast -ErrorAction Stop; "
        f"New-BurntToastNotification -Text '{safe_title}', '{safe_message}'"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            timeout=20, capture_output=True, check=True,
        )
    except Exception as e:
        logger.warning(f"Toast notification failed (non-fatal): {e}")
