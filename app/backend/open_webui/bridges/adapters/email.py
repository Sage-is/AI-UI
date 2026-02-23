import asyncio
import email as email_lib
import email.utils
import imaplib
import logging
import smtplib
import ssl
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from open_webui.bridges.base import MessageBridge
from open_webui.bridges.manager import register_adapter
from open_webui.bridges.types import (
    ConfigField,
    IncomingMessage,
    MediaAttachment,
    OutgoingMessage,
    PlatformInfo,
)

log = logging.getLogger(__name__)


@register_adapter("email")
class EmailBridge(MessageBridge):
    """Email adapter using stdlib smtplib/imaplib."""

    def __init__(self, connection_id: str, config: dict):
        super().__init__(connection_id, config)
        self._smtp_host: str = config.get("smtp_host", "")
        self._smtp_port: int = int(config.get("smtp_port", 587))
        self._smtp_tls: str = config.get("smtp_tls", "starttls")
        self._imap_host: str = config.get("imap_host", "")
        self._imap_port: int = int(config.get("imap_port", 993))
        self._imap_tls: str = config.get("imap_tls", "ssl")
        self._email_address: str = config.get("email_address", "")
        self._password: str = config.get("password", "")
        self._poll_interval: int = int(config.get("poll_interval", 30))
        self._subject_prefix: str = config.get("subject_prefix", "")
        self._default_subject: str = config.get("default_subject", "Message from Sage AI")

        self._poll_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        try:
            # Test SMTP
            await asyncio.to_thread(self._test_smtp)
            # Test IMAP
            await asyncio.to_thread(self._test_imap)

            self._connected = True
            self._stop_event.clear()
            self._poll_task = asyncio.create_task(self._imap_poll_loop())
            log.info(f"Email bridge connected: {self._email_address}")
            return True
        except Exception as e:
            log.error(f"Email bridge connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._stop_event.set()
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        log.info(f"Email bridge disconnected: {self._email_address}")

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._test_smtp)
            await asyncio.to_thread(self._test_imap)
            return True
        except Exception as e:
            log.warning(f"Email health check failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_message(self, message: OutgoingMessage) -> bool:
        """Send an email. message.thread_id is the recipient email address."""
        if not self._connected:
            return False

        try:
            await asyncio.to_thread(self._send_email, message)
            return True
        except Exception as e:
            log.error(f"Email send failed: {e}")
            return False

    def _send_email(self, message: OutgoingMessage) -> None:
        recipient = message.thread_id

        if message.media:
            msg = MIMEMultipart()
            msg.attach(MIMEText(message.content, "plain", "utf-8"))
            for attachment in message.media:
                if attachment.data:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.data)
                    email_lib.encoders.encode_base64(part)
                    filename = attachment.filename or "attachment"
                    part.add_header(
                        "Content-Disposition", "attachment", filename=filename
                    )
                    msg.attach(part)
        else:
            msg = MIMEText(message.content, "plain", "utf-8")

        msg["From"] = self._email_address
        msg["To"] = recipient
        msg["Subject"] = self._default_subject

        conn = self._open_smtp()
        try:
            conn.sendmail(self._email_address, [recipient], msg.as_string())
        finally:
            conn.quit()

    # ------------------------------------------------------------------
    # Webhook stubs (email doesn't use webhooks)
    # ------------------------------------------------------------------

    async def handle_webhook(self, body: bytes, headers: dict) -> Optional[IncomingMessage]:
        return None

    async def verify_webhook_signature(self, body: bytes, headers: dict) -> bool:
        return True

    # ------------------------------------------------------------------
    # IMAP polling
    # ------------------------------------------------------------------

    async def _imap_poll_loop(self) -> None:
        """Background task that polls IMAP for unseen emails."""
        log.info(f"Email IMAP poll loop started (interval={self._poll_interval}s)")
        while not self._stop_event.is_set():
            try:
                messages = await asyncio.to_thread(self._fetch_unseen_emails)
                for incoming in messages:
                    if self._incoming_handler:
                        try:
                            await self._incoming_handler(incoming)
                        except Exception as e:
                            log.error(f"Error in incoming handler for email: {e}")
            except Exception as e:
                log.error(f"IMAP poll error: {e}")

            # Wait for poll_interval or stop event
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self._poll_interval
                )
                # If we reach here, stop_event was set
                break
            except asyncio.TimeoutError:
                # Normal timeout — loop again
                continue

    def _fetch_unseen_emails(self) -> list[IncomingMessage]:
        """Connect to IMAP, fetch UNSEEN emails, mark them SEEN, return parsed messages."""
        results: list[IncomingMessage] = []

        conn = self._open_imap()
        try:
            conn.select("INBOX")

            # Build IMAP search criteria
            criteria = "(UNSEEN)"
            if self._subject_prefix:
                criteria = f'(UNSEEN SUBJECT "{self._subject_prefix}")'

            status, data = conn.search(None, criteria)
            if status != "OK":
                return results

            msg_nums = data[0].split()
            if not msg_nums:
                return results

            for num in msg_nums:
                try:
                    status, msg_data = conn.fetch(num, "(RFC822)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        continue

                    raw_bytes = msg_data[0][1]
                    if not isinstance(raw_bytes, bytes):
                        continue

                    incoming = self._parse_email(raw_bytes)
                    if incoming:
                        results.append(incoming)

                    # Mark as seen
                    conn.store(num, "+FLAGS", "\\Seen")
                except Exception as e:
                    log.error(f"Error processing email #{num}: {e}")
                    # Still mark as seen to avoid infinite retry
                    try:
                        conn.store(num, "+FLAGS", "\\Seen")
                    except Exception:
                        pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
            try:
                conn.logout()
            except Exception:
                pass

        return results

    def _parse_email(self, raw_bytes: bytes) -> Optional[IncomingMessage]:
        """Parse a raw email into an IncomingMessage."""
        msg = email_lib.message_from_bytes(raw_bytes)

        # Extract sender
        from_header = msg.get("From", "")
        sender_name, sender_address = email.utils.parseaddr(from_header)
        if not sender_address:
            return None

        # Self-loop prevention
        if sender_address.lower() == self._email_address.lower():
            return None

        # Subject prefix filtering (client-side double check)
        subject = msg.get("Subject", "")
        if self._subject_prefix and not subject.startswith(self._subject_prefix):
            return None

        # Parse body and attachments
        body = ""
        media: list[MediaAttachment] = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        media.append(
                            MediaAttachment(
                                url="",
                                mime_type=content_type,
                                filename=part.get_filename() or "attachment",
                                size=len(payload),
                                data=payload,
                            )
                        )
                elif content_type == "text/plain" and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        body = body.strip()
        if not body and not media:
            return None

        message_id = msg.get("Message-ID", "")
        date_str = msg.get("Date", "")

        return IncomingMessage(
            connection_id=self.connection_id,
            platform="email",
            external_thread_id=sender_address,
            external_user_id=sender_address,
            external_user_name=sender_name or None,
            content=body,
            media=media,
            raw_event={
                "message_id": message_id,
                "subject": subject,
                "date": date_str,
                "from": from_header,
            },
        )

    # ------------------------------------------------------------------
    # SMTP / IMAP helpers
    # ------------------------------------------------------------------

    def _open_smtp(self) -> smtplib.SMTP:
        """Open a fresh SMTP connection."""
        if self._smtp_tls == "ssl":
            ctx = ssl.create_default_context()
            conn = smtplib.SMTP_SSL(self._smtp_host, self._smtp_port, context=ctx)
        else:
            conn = smtplib.SMTP(self._smtp_host, self._smtp_port)
            if self._smtp_tls == "starttls":
                ctx = ssl.create_default_context()
                conn.starttls(context=ctx)

        conn.login(self._email_address, self._password)
        return conn

    def _open_imap(self) -> imaplib.IMAP4:
        """Open a fresh IMAP connection."""
        if self._imap_tls == "ssl":
            ctx = ssl.create_default_context()
            conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port, ssl_context=ctx)
        elif self._imap_tls == "starttls":
            conn = imaplib.IMAP4(self._imap_host, self._imap_port)
            ctx = ssl.create_default_context()
            conn.starttls(ssl_context=ctx)
        else:
            conn = imaplib.IMAP4(self._imap_host, self._imap_port)

        conn.login(self._email_address, self._password)
        return conn

    def _test_smtp(self) -> None:
        """Test SMTP connectivity (raises on failure)."""
        conn = self._open_smtp()
        conn.quit()

    def _test_imap(self) -> None:
        """Test IMAP connectivity (raises on failure)."""
        conn = self._open_imap()
        conn.select("INBOX")
        conn.close()
        conn.logout()

    # ------------------------------------------------------------------
    # Platform info
    # ------------------------------------------------------------------

    @classmethod
    def get_platform_info(cls) -> PlatformInfo:
        return PlatformInfo(
            platform="email",
            display_name="Email (SMTP/IMAP)",
            description="Send and receive messages via email using SMTP and IMAP",
            supports_media=True,
            supports_groups=False,
            config_schema=[
                ConfigField(
                    name="smtp_host",
                    label="SMTP Host",
                    type="text",
                    required=True,
                    placeholder="smtp.gmail.com",
                ),
                ConfigField(
                    name="smtp_port",
                    label="SMTP Port",
                    type="number",
                    required=True,
                    default="587",
                ),
                ConfigField(
                    name="smtp_tls",
                    label="SMTP Security",
                    type="select",
                    required=True,
                    default="starttls",
                    options=[
                        {"value": "starttls", "label": "STARTTLS"},
                        {"value": "ssl", "label": "SSL/TLS"},
                        {"value": "none", "label": "None"},
                    ],
                ),
                ConfigField(
                    name="imap_host",
                    label="IMAP Host",
                    type="text",
                    required=True,
                    placeholder="imap.gmail.com",
                ),
                ConfigField(
                    name="imap_port",
                    label="IMAP Port",
                    type="number",
                    required=True,
                    default="993",
                ),
                ConfigField(
                    name="imap_tls",
                    label="IMAP Security",
                    type="select",
                    required=True,
                    default="ssl",
                    options=[
                        {"value": "ssl", "label": "SSL/TLS"},
                        {"value": "starttls", "label": "STARTTLS"},
                        {"value": "none", "label": "None"},
                    ],
                ),
                ConfigField(
                    name="email_address",
                    label="Email Address",
                    type="text",
                    required=True,
                    placeholder="sage@example.com",
                ),
                ConfigField(
                    name="password",
                    label="Password",
                    type="password",
                    required=True,
                    placeholder="App password recommended",
                ),
                ConfigField(
                    name="poll_interval",
                    label="Poll Interval (seconds)",
                    type="number",
                    required=False,
                    default="30",
                    placeholder="30",
                ),
                ConfigField(
                    name="subject_prefix",
                    label="Subject Prefix Filter",
                    type="text",
                    required=False,
                    placeholder="Only process emails matching this prefix",
                ),
                ConfigField(
                    name="default_subject",
                    label="Default Outgoing Subject",
                    type="text",
                    required=False,
                    default="Message from Sage AI",
                    placeholder="Message from Sage AI",
                ),
            ],
        )
