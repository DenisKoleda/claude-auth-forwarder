import base64
import html as html_module
import http.server
import logging
import os
import re
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from i18n import t

logger = logging.getLogger(__name__)


def _can_open_browser() -> bool:
    """Check if browser can be opened."""
    try:
        # Check for DISPLAY (Linux) or if not in SSH
        if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
            return False
        if (
            os.name == "posix"
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            # macOS can always open browser, Linux without DISPLAY cannot
            import platform

            if platform.system() != "Darwin":
                return False
        return True
    except Exception:
        return False


class GmailAPIError(Exception):
    """Error when working with Gmail API."""

    pass


class TokenExpiredError(Exception):
    """Error when Gmail token is expired/revoked and re-auth is needed."""

    pass


class GmailMonitor:
    def __init__(self) -> None:
        self.service: Any = None
        self.creds: Credentials | None = None

    def authenticate(self) -> None:
        """Authenticate with Gmail API."""
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(
                config.GMAIL_TOKEN_FILE, config.GMAIL_SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except RefreshError as e:
                    # Token revoked or expired - need full re-auth
                    logger.warning(t("token_refresh_failed", error=e))
                    if os.path.exists(config.GMAIL_TOKEN_FILE):
                        os.remove(config.GMAIL_TOKEN_FILE)
                        logger.info(t("token_removed"))
                    self.creds = None

            if not self.creds or not self.creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDENTIALS_FILE, config.GMAIL_SCOPES
                )
                auth_port = int(os.environ.get("OAUTH_PORT", 8080))

                if _can_open_browser():
                    print(f"\n{'=' * 60}")
                    print(t("open_auth_url"))
                    print(f"{'=' * 60}\n")
                    self.creds = flow.run_local_server(
                        port=auth_port,
                        open_browser=True,
                        success_message=t("auth_success_browser"),
                    )
                else:
                    self.creds = self._run_manual_auth_flow(flow, auth_port)

            with open(config.GMAIL_TOKEN_FILE, "w") as token:
                token.write(self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)
        logger.info(t("gmail_auth_success"))

    def _run_manual_auth_flow(self, flow: InstalledAppFlow, port: int) -> Credentials:
        """Run OAuth flow via web page for headless environments (Docker/SSH/VPS).

        Starts an HTTP server on 0.0.0.0:{port} that:
        - Shows auth link and a form to paste the redirect URL at GET /
        - Handles direct OAuth callback if redirect reaches the server (port forwarding)
        - Handles form submission with pasted redirect URL at POST /
        """
        flow.redirect_uri = f"http://localhost:{port}/"
        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

        auth_code_result: list[str | None] = [None]
        server_ready = threading.Event()

        class OAuthHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                if "code" in params:
                    auth_code_result[0] = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        f"<h2>{html_module.escape(t('auth_success_browser'))}</h2>".encode()
                    )
                    return

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                escaped_url = html_module.escape(auth_url)
                page = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                    "<title>Gmail OAuth</title></head><body>"
                    f"<h2>{html_module.escape(t('auth_page_title'))}</h2>"
                    f"<p>{html_module.escape(t('auth_page_step1'))}</p>"
                    f"<p><a href='{escaped_url}' target='_blank'>"
                    f"{html_module.escape(t('auth_page_link'))}</a></p>"
                    f"<p>{html_module.escape(t('auth_page_step2'))}</p>"
                    f"<p>{html_module.escape(t('auth_page_step3'))}</p>"
                    "<form method='POST'>"
                    "<input type='text' name='url' style='width:80%;padding:8px' "
                    f"placeholder='{html_module.escape(t('auth_page_placeholder'))}'>"
                    "<br><br>"
                    f"<button type='submit' style='padding:8px 24px'>"
                    f"{html_module.escape(t('auth_page_submit'))}</button>"
                    "</form></body></html>"
                )
                self.wfile.write(page.encode())

            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode()
                form_data = parse_qs(body)
                pasted_url = form_data.get("url", [""])[0]
                parsed = urlparse(pasted_url)
                code = parse_qs(parsed.query).get("code", [None])[0]

                if code:
                    auth_code_result[0] = code
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        f"<h2>{html_module.escape(t('auth_success_browser'))}</h2>".encode()
                    )
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        f"<h2>{html_module.escape(t('auth_code_not_found'))}</h2>".encode()
                    )

            def log_message(self, format: str, *args: Any) -> None:
                logger.debug("OAuth HTTP: %s", format % args)

        server = http.server.HTTPServer(("0.0.0.0", port), OAuthHandler)
        server.timeout = 1

        external_host = os.environ.get("OAUTH_EXTERNAL_HOST", "")
        if external_host:
            hint_url = f"http://{external_host}"
        else:
            hint_url = f"http://YOUR_SERVER_IP:{port}"

        logger.info(t("auth_server_started", port=port))
        print(f"\n{'=' * 60}")
        print(t("auth_server_hint", url=hint_url))
        print(f"{'=' * 60}\n")

        server_ready.set()
        while auth_code_result[0] is None:
            server.handle_request()
        server.server_close()

        flow.fetch_token(code=auth_code_result[0])
        return flow.credentials

    def _is_token_error(self, error: Exception) -> bool:
        """Check if error is related to expired/revoked token."""
        error_str = str(error).lower()
        return (
            "invalid_grant" in error_str
            or "token" in error_str
            and ("expired" in error_str or "revoked" in error_str)
        )

    def _reauth_if_token_error(self, error: Exception) -> bool:
        """Try to refresh token if error is token-related. Returns True if refresh succeeded.

        Raises:
            TokenExpiredError: If token cannot be refreshed (revoked/expired refresh token).
        """
        if self._is_token_error(error):
            logger.warning(t("token_expired_reauth"))
            if self.creds and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    self.service = build(
                        "gmail", "v1", credentials=self.creds, cache_discovery=False
                    )
                    with open(config.GMAIL_TOKEN_FILE, "w") as f:
                        f.write(self.creds.to_json())
                    logger.info(t("gmail_auth_success"))
                    return True
                except RefreshError:
                    pass
            if os.path.exists(config.GMAIL_TOKEN_FILE):
                os.remove(config.GMAIL_TOKEN_FILE)
            self.creds = None
            raise TokenExpiredError(t("token_fully_expired"))
        return False

    def get_unread_claude_emails(self, _retry: bool = True) -> list[dict[str, Any]]:
        """Get unread emails from Claude/Anthropic.

        Returns:
            list: List of emails (empty if no new ones)

        Raises:
            GmailAPIError: On API error
        """
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=config.GMAIL_QUERY, maxResults=10)
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for msg in messages:
                email_data = self._get_email_content(msg["id"])
                if email_data:
                    emails.append(email_data)

            return emails
        except Exception as e:
            # If token expired during API call, re-auth and retry once
            if _retry and self._reauth_if_token_error(e):
                return self.get_unread_claude_emails(_retry=False)
            raise GmailAPIError(t("gmail_fetch_error", error=e)) from e

    def _get_email_content(self, msg_id: str) -> dict[str, Any] | None:
        """Get email content."""
        try:
            message = (
                self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            )

            headers = message["payload"]["headers"]
            subject = self._get_header(headers, "subject", t("no_subject"))
            sender = self._get_header(headers, "from", t("unknown_sender"))

            body = self._extract_body(message["payload"])
            auth_data = self._extract_auth_data(body)
            payment_data = None

            subject_lower = subject.lower()
            if not auth_data and ("payment" in subject_lower or "unsuccessful" in subject_lower):
                payment_data = self._extract_payment_data(body, subject)

            return {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "body": body,
                "auth_data": auth_data,
                "payment_data": payment_data,
            }
        except Exception as e:
            logger.error(t("email_read_error", msg_id=msg_id, error=e))
            return None

    def _get_header(self, headers: list[dict], name: str, default: str = "") -> str:
        """Extract header value by name."""
        return next((h["value"] for h in headers if h["name"].lower() == name.lower()), default)

    def _decode_body_data(self, data: str) -> str:
        """Decode base64 email body data."""
        return base64.urlsafe_b64decode(data).decode("utf-8")

    def _extract_body(self, payload: dict) -> str:
        """Extract email text."""
        if payload.get("body", {}).get("data"):
            return self._decode_body_data(payload["body"]["data"])

        if "parts" not in payload:
            return ""

        html_body = ""
        for part in payload["parts"]:
            data = part.get("body", {}).get("data")
            if not data:
                continue
            if part["mimeType"] == "text/plain":
                return self._decode_body_data(data)
            if part["mimeType"] == "text/html":
                html_body = self._decode_body_data(data)

        return html_body

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags and decode entities to get plain text."""
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"</?(p|div|tr|td|table|h[1-6])[^>]*>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&#\d+;", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_auth_data(self, body: str) -> dict[str, str] | None:
        """Extract auth link or code from email body."""
        # Links are extracted from raw HTML (they're in href attributes)
        link_patterns = [
            # Mobile link first (more specific: has ?client= before #)
            ("mobile_link", r'https://claude\.ai/magic-link\?client=[^#]+#[^\s"<>]+', 0),
            # Desktop link: magic-link#token
            ("link", r'https://claude\.ai/magic-link#[^\s"<>]+', 0),
        ]

        for auth_type, pattern, group in link_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return {"type": auth_type, "value": match.group(group)}

        # Codes are extracted from stripped text to avoid CSS color false positives
        clean_text = self._strip_html(body)
        code_patterns = [
            ("code", r"(?:code|код|verification|pin)[:\s]+(\d{4,8})", 1),
            ("code", r"(?<!\#)\b(\d{6})\b", 1),
        ]

        for auth_type, pattern, group in code_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return {"type": auth_type, "value": match.group(group)}

        return None

    def _extract_payment_data(self, body: str, subject: str) -> dict[str, str] | None:
        """Extract payment failure info from email."""
        clean_text = self._strip_html(body) if "<" in body else body
        amount_match = re.search(r"\$[\d,.]+", subject) or re.search(r"\$[\d,.]+", clean_text)
        card_match = re.search(r"(?:ending in|оканчивающ\S*)\s+(\d{4})", clean_text, re.IGNORECASE)
        if amount_match:
            return {
                "type": "payment_failed",
                "amount": amount_match.group(0),
                "card_last4": card_match.group(1) if card_match else "****",
            }
        return None

    def mark_as_read(self, msg_id: str, _retry: bool = True) -> None:
        """Mark email as read."""
        try:
            self.service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(t("email_marked_read", msg_id=msg_id))
        except Exception as e:
            # If token expired during API call, re-auth and retry once
            if _retry and self._reauth_if_token_error(e):
                return self.mark_as_read(msg_id, _retry=False)
            logger.error(t("email_mark_error", error=e))
