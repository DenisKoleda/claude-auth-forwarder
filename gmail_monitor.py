import base64
import html as html_module
import http.server
import logging
import os
import re
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import settings
from admin_state import AdminState
from i18n import t
from secure_files import write_private_text

logger = logging.getLogger(__name__)


def extract_oauth_code(callback_url: str, expected_state: str) -> str | None:
    """Return the OAuth code only when the callback state matches."""
    query = parse_qs(urlparse(callback_url).query)
    code = query.get("code", [None])[0]
    state = query.get("state", [None])[0]
    return code if code and state == expected_state else None


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
    def __init__(self, admin_state: AdminState | None = None) -> None:
        self.service: Any = None
        self.creds: Credentials | None = None
        self.admin_state = admin_state

    def _enabled_providers(self) -> list[dict[str, str]]:
        """Return enabled provider Gmail queries."""
        providers: list[dict[str, str]] = []

        source_enabled = (
            self.admin_state.is_source_enabled
            if self.admin_state
            else lambda source: {
                "claude_auth": settings.ENABLE_CLAUDE_EMAILS,
                "openai_auth": settings.ENABLE_OPENAI_EMAILS,
                "billing": settings.ENABLE_BILLING_EMAILS,
            }.get(source, False)
        )

        if source_enabled("claude_auth"):
            providers.append(
                {
                    "id": "claude",
                    "name": "Claude",
                    "kind": "auth",
                    "query": settings.CLAUDE_AUTH_GMAIL_QUERY,
                }
            )
        if source_enabled("openai_auth"):
            providers.append(
                {
                    "id": "openai",
                    "name": "OpenAI",
                    "kind": "auth",
                    "query": settings.OPENAI_AUTH_GMAIL_QUERY,
                }
            )
        if source_enabled("billing"):
            providers.extend(
                [
                    {
                        "id": "claude",
                        "name": "Claude",
                        "kind": "billing",
                        "query": settings.CLAUDE_BILLING_GMAIL_QUERY,
                    },
                    {
                        "id": "openai",
                        "name": "OpenAI",
                        "kind": "billing",
                        "query": settings.OPENAI_BILLING_GMAIL_QUERY,
                    },
                ]
            )

        return providers

    def authenticate(self) -> None:
        """Authenticate with Gmail API."""
        if os.path.exists(settings.GMAIL_TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(
                settings.GMAIL_TOKEN_FILE, settings.GMAIL_SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except RefreshError as e:
                    # Token revoked or expired - need full re-auth
                    logger.warning(t("token_refresh_failed", error=e))
                    if os.path.exists(settings.GMAIL_TOKEN_FILE):
                        os.remove(settings.GMAIL_TOKEN_FILE)
                        logger.info(t("token_removed"))
                    self.creds = None

            if not self.creds or not self.creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GMAIL_CREDENTIALS_FILE, settings.GMAIL_SCOPES
                )
                auth_port = settings.OAUTH_PORT

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

            write_private_text(settings.GMAIL_TOKEN_FILE, self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)
        logger.info(t("gmail_auth_success"))

    def _run_manual_auth_flow(self, flow: InstalledAppFlow, port: int) -> Credentials:
        """Run OAuth flow via web page for headless environments (Docker/SSH/VPS).

        Starts a temporary HTTP server on the configured bind host that:
        - Shows auth link and a form to paste the redirect URL at GET /
        - Handles direct OAuth callback if redirect reaches the server (port forwarding)
        - Handles form submission with pasted redirect URL at POST /
        """
        flow.redirect_uri = f"http://localhost:{port}/"
        auth_url, expected_state = flow.authorization_url(access_type="offline", prompt="consent")

        auth_code_result: list[str | None] = [None]
        server_ready = threading.Event()

        class OAuthHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                code = extract_oauth_code(self.path, expected_state)

                if code:
                    auth_code_result[0] = code
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
                code = extract_oauth_code(pasted_url, expected_state)

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

        server = http.server.HTTPServer((settings.OAUTH_BIND_HOST, port), OAuthHandler)
        server.timeout = 1

        hint_url = f"http://localhost:{port}"

        logger.info(t("auth_server_started", port=port))
        print(f"\n{'=' * 60}")
        print(t("auth_server_hint", url=hint_url))
        print(f"{'=' * 60}\n")

        server_ready.set()
        while auth_code_result[0] is None:
            server.handle_request()
        server.server_close()

        flow.fetch_token(code=auth_code_result[0])
        creds: Credentials = flow.credentials
        return creds

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
                    write_private_text(settings.GMAIL_TOKEN_FILE, self.creds.to_json())
                    logger.info(t("gmail_auth_success"))
                    return True
                except RefreshError:
                    pass
            if os.path.exists(settings.GMAIL_TOKEN_FILE):
                os.remove(settings.GMAIL_TOKEN_FILE)
            self.creds = None
            raise TokenExpiredError(t("token_fully_expired"))
        return False

    def get_unread_emails(self, _retry: bool = True) -> list[dict[str, Any]]:
        """Get unread auth/billing emails from enabled providers.

        Returns:
            list: List of emails (empty if no new ones)

        Raises:
            GmailAPIError: On API error
        """
        try:
            emails = []
            seen_message_ids: set[str] = set()

            for provider in self._enabled_providers():
                results = (
                    self.service.users()
                    .messages()
                    .list(userId="me", q=provider["query"], maxResults=10)
                    .execute()
                )

                messages = results.get("messages", [])

                for msg in messages:
                    msg_id = msg["id"]
                    if msg_id in seen_message_ids:
                        continue
                    seen_message_ids.add(msg_id)

                    email_data = self._get_email_content(
                        msg_id,
                        provider_id=provider["id"],
                        provider_name=provider["name"],
                        kind=provider["kind"],
                    )
                    if email_data:
                        emails.append(email_data)

            return emails
        except Exception as e:
            # If token expired during API call, re-auth and retry once
            if _retry and self._reauth_if_token_error(e):
                return self.get_unread_emails(_retry=False)
            raise GmailAPIError(t("gmail_fetch_error", error=e)) from e

    def get_unread_claude_emails(self, _retry: bool = True) -> list[dict[str, Any]]:
        """Backward-compatible alias for the old main loop."""
        return self.get_unread_emails(_retry=_retry)

    def _get_email_content(
        self,
        msg_id: str,
        provider_id: str = "claude",
        provider_name: str = "Claude",
        kind: str = "auth",
    ) -> dict[str, Any] | None:
        """Get email content."""
        try:
            message = (
                self.service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            )

            headers = message["payload"]["headers"]
            subject = self._get_header(headers, "subject", t("no_subject"))
            sender = self._get_header(headers, "from", t("unknown_sender"))
            received_at = int(message.get("internalDate", "0")) / 1000

            body = self._extract_body(message["payload"])
            auth_data = (
                self._extract_auth_data(body, provider_id, provider_name)
                if kind == "auth"
                else None
            )
            payment_data = None

            if kind == "billing":
                payment_data = self._classify_payment_email(body, subject, provider_id)
                if payment_data:
                    payment_data["provider"] = provider_id
                    payment_data["provider_name"] = provider_name

            return {
                "id": msg_id,
                "provider": provider_id,
                "provider_name": provider_name,
                "kind": kind,
                "subject": subject,
                "from": sender,
                "received_at": received_at,
                "stale": self._is_stale(kind, received_at),
                "body": body,
                "auth_data": auth_data,
                "payment_data": payment_data,
            }
        except Exception as e:
            logger.error(t("email_read_error", msg_id=msg_id, error=e))
            return None

    def _is_stale(self, kind: str, received_at: float, now: float | None = None) -> bool:
        if received_at <= 0:
            return True
        max_age = (
            settings.AUTH_EMAIL_MAX_AGE_SECONDS
            if kind == "auth"
            else settings.BILLING_EMAIL_MAX_AGE_SECONDS
        )
        return (now or time.time()) - received_at > max_age

    def _get_header(self, headers: list[dict], name: str, default: str = "") -> str:
        """Extract header value by name."""
        return next((h["value"] for h in headers if h["name"].lower() == name.lower()), default)

    def _decode_body_data(self, data: str) -> str:
        """Decode base64 email body data."""
        return base64.urlsafe_b64decode(data).decode("utf-8")

    def _extract_body(self, payload: dict) -> str:
        """Extract email text. Walks nested multipart parts (mixed/alternative)."""
        if payload.get("body", {}).get("data"):
            return self._decode_body_data(payload["body"]["data"])

        if "parts" not in payload:
            return ""

        html_body = ""
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if mime == "text/plain" and data:
                return self._decode_body_data(data)
            if mime == "text/html" and data and not html_body:
                html_body = self._decode_body_data(data)
            if mime.startswith("multipart/"):
                nested = self._extract_body(part)
                if nested:
                    if "<" not in nested:
                        return nested
                    if not html_body:
                        html_body = nested

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

    def _extract_auth_data(
        self, body: str, provider_id: str, provider_name: str
    ) -> dict[str, str] | None:
        """Extract auth link or code from email body."""
        if provider_id == "claude":
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
                    return {
                        "type": auth_type,
                        "value": match.group(group),
                        "provider": provider_id,
                        "provider_name": provider_name,
                    }

        # Codes are extracted from stripped text to avoid CSS color false positives
        clean_text = self._strip_html(body)
        if provider_id == "openai":
            code_patterns = [
                ("code", r"following code to help verify your identity:\s*(\d{4,8})", 1),
                ("code", r"(?:authentication|verification)\s+code[:\s]+(\d{4,8})", 1),
                ("code", r"(?<!\#)\b(\d{6})\b", 1),
            ]
        else:
            code_patterns = [
                ("code", r"(?:code|код|verification|pin)[:\s]+(\d{4,8})", 1),
                ("code", r"(?<!\#)\b(\d{6})\b", 1),
            ]

        for auth_type, pattern, group in code_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return {
                    "type": auth_type,
                    "value": match.group(group),
                    "provider": provider_id,
                    "provider_name": provider_name,
                }

        return None

    def _classify_payment_email(
        self, body: str, subject: str, provider_id: str
    ) -> dict[str, str] | None:
        """Detect payment-related emails and extract relevant fields."""
        if provider_id == "openai":
            return self._classify_openai_email(body, subject)

        subject_lower = subject.lower()
        if "receipt" in subject_lower or "invoice" in subject_lower:
            return self._extract_payment_success(body, subject)
        if "paused" in subject_lower:
            return {"type": "subscription_paused"}
        if "payment" in subject_lower or "unsuccessful" in subject_lower:
            return self._extract_payment_failed(body, subject)
        return None

    def _clean_email_text(self, body: str) -> str:
        return self._strip_html(body) if "<" in body else body

    def _extract_amount(self, text: str) -> str:
        amount_match = re.search(r"(?:[$€£]\s?[\d,.]+|[\d,.]+\s?(?:USD|EUR|GBP))", text)
        return amount_match.group(0).strip() if amount_match else ""

    def _extract_card_last4(self, text: str) -> str:
        card_match = re.search(
            r"(?:ending in|оканчивающ\S*|Visa[-\s]|Mastercard[-\s]|card[-\s])\s*(\d{4})",
            text,
            re.IGNORECASE,
        )
        return card_match.group(1) if card_match else "****"

    def _extract_openai_plan(self, text: str) -> str:
        plan_match = re.search(r"\b(ChatGPT\s+(?:Plus|Pro|Team|Enterprise))\b", text, re.I)
        return plan_match.group(1) if plan_match else "ChatGPT"

    def _classify_openai_email(self, body: str, subject: str) -> dict[str, str] | None:
        """Detect OpenAI auth-adjacent billing/subscription emails."""
        clean_text = self._clean_email_text(body)
        subject_lower = subject.lower()
        clean_lower = clean_text.lower()

        if "account has been funded" in subject_lower:
            amount = self._extract_amount(clean_text)
            return {
                "type": "openai_api_funded",
                "amount": amount or t("unknown_amount"),
                "card_last4": self._extract_card_last4(clean_text),
            }

        if "usage limits have increased" in subject_lower:
            return {"type": "openai_usage_limits_increased"}

        if "не будет продлен" in subject_lower or "not be renewed" in subject_lower:
            period_match = re.search(
                r"периода\s+([^.\n]+)", clean_text, re.IGNORECASE
            ) or re.search(
                r"(?:до конца расчетного периода|until)\s+([^.\n]+)",
                clean_text,
                re.IGNORECASE,
            )
            return {
                "type": "subscription_cancel_pending",
                "plan": self._extract_openai_plan(clean_text),
                "period": period_match.group(1).strip() if period_match else "",
            }

        if "новый план" in subject_lower or "new plan" in subject_lower:
            return {
                "type": "subscription_started",
                "plan": self._extract_openai_plan(clean_text),
                "amount": self._extract_amount(clean_text),
                "card_last4": self._extract_card_last4(clean_text),
            }

        if (
            "не потеряйте доступ" in subject_lower
            or "не был проведен" in clean_lower
            or "failed" in clean_lower
        ):
            amount = self._extract_amount(clean_text)
            return {
                "type": "payment_failed",
                "amount": amount or t("unknown_amount"),
                "card_last4": self._extract_card_last4(clean_text),
            }

        if any(word in subject_lower for word in ("payment", "billing", "receipt", "invoice")):
            amount = self._extract_amount(clean_text)
            if amount:
                return {
                    "type": "payment_success",
                    "amount": amount,
                    "plan": self._extract_openai_plan(clean_text),
                    "period": "",
                    "card_last4": self._extract_card_last4(clean_text),
                    "receipt_number": "",
                }

        return None

    def _extract_payment_failed(self, body: str, subject: str) -> dict[str, str] | None:
        """Extract failed payment info from email."""
        clean_text = self._clean_email_text(body)
        amount_match = re.search(r"\$[\d,.]+", subject) or re.search(r"\$[\d,.]+", clean_text)
        card_match = re.search(r"(?:ending in|оканчивающ\S*)\s+(\d{4})", clean_text, re.IGNORECASE)
        if amount_match:
            return {
                "type": "payment_failed",
                "amount": amount_match.group(0),
                "card_last4": card_match.group(1) if card_match else "****",
            }
        return None

    def _extract_payment_success(self, body: str, subject: str) -> dict[str, str] | None:
        """Extract successful payment (receipt) info from email."""
        clean_text = self._clean_email_text(body)
        amount_match = re.search(r"\$[\d,]+(?:\.\d{2})?", clean_text)
        # "Max plan - 20x", "Pro plan", "Team plan - 5x" etc.
        plan_match = re.search(r"\b([A-Z][A-Za-z]+\s+plan(?:\s*-\s*\d+x)?)", clean_text)
        # "May 5–Jun 5, 2026" or "May 5-Jun 5, 2026"
        period_match = re.search(
            r"[A-Z][a-z]{2,8}\s+\d{1,2}\s*[–—\-]\s*[A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4}",
            clean_text,
        )
        # "Payment method - 7220" or "ending in 4242"
        card_match = re.search(
            r"(?:Payment method\s*-\s*|ending in\s+|оканчивающ\S*\s+)(\d{4})",
            clean_text,
            re.IGNORECASE,
        )
        # "Receipt number 2035-4974-6213" — fallback to subject "#2035-4974-6213"
        receipt_match = re.search(
            r"Receipt number\s+([\w-]+)", clean_text, re.IGNORECASE
        ) or re.search(r"#([\w-]+)", subject)

        if not amount_match:
            return None
        return {
            "type": "payment_success",
            "amount": amount_match.group(0),
            "plan": plan_match.group(1) if plan_match else "",
            "period": period_match.group(0) if period_match else "",
            "card_last4": card_match.group(1) if card_match else "****",
            "receipt_number": receipt_match.group(1) if receipt_match else "",
        }

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
