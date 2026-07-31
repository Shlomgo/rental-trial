"""Shared HTTP fetcher for all scrapers.

Builder sites here sit behind Cloudflare/Akamai bot-challenge pages that
fingerprint the TLS handshake. Python's `requests` (urllib3/OpenSSL) gets
served a JS challenge page; the system `curl` binary does not. So instead of
`requests`, we shell out to `curl` for every fetch. `new_session()` is kept
as a no-op factory so callers don't need to change if this ever moves back
to a `requests.Session`.
"""
import subprocess
import time

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 0.4
TIMEOUT_SECONDS = 30


def new_session():
    """No real session object needed for curl; kept for interface parity."""
    return None


def get_text(session, url):
    """GET a URL and return response text, or None on any failure (including
    non-200 status). Never raises: callers should treat None as 'could not
    fetch, leave blank'."""
    try:
        result = subprocess.run(
            [
                "curl", "-sS", "-L",
                "-A", USER_AGENT,
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: en-US,en;q=0.9",
                "--max-time", str(TIMEOUT_SECONDS),
                "-w", "\n__HTTP_STATUS__:%{http_code}",
                url,
            ],
            capture_output=True,
            timeout=TIMEOUT_SECONDS + 5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        time.sleep(REQUEST_DELAY_SECONDS)

    if result.returncode != 0:
        return None

    text = result.stdout.decode("utf-8", errors="replace")
    marker = "\n__HTTP_STATUS__:"
    idx = text.rfind(marker)
    if idx == -1:
        return None
    body, status = text[:idx], text[idx + len(marker):].strip()
    if status != "200":
        return None
    return body
