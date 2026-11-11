import os
import smtplib
import ssl
from collections.abc import Sequence
from email.message import EmailMessage

from dotenv import load_dotenv


class EmailSender:
    """Send email through an SMTP server configured in environment variables."""

    def __init__(
        self,
        *,
        server: str | None = None,
        login: str | None = None,
        password: str | None = None,
        from_address: str | None = None,
        port: int | None = None,
        timeout: float = 30.0,
    ) -> None:
        load_dotenv()
        self.server = server or os.getenv("SMTP_SERVER")
        self.login = login or os.getenv("SMTP_LOGIN")
        self.password = password or os.getenv("SMTP_PASS")
        self.from_address = from_address or os.getenv("MAIL_FROM")

        configured_port = port or os.getenv("SMTP_PORT")
        try:
            self.port = int(configured_port) if configured_port else 0
        except ValueError as error:
            raise RuntimeError("SMTP_PORT geçerli bir sayı olmalıdır.") from error

        if not self.server:
            raise RuntimeError("SMTP_SERVER .env içinde tanımlanmalıdır.")
        if not self.login:
            raise RuntimeError("SMTP_LOGIN .env içinde tanımlanmalıdır.")
        if not self.password:
            raise RuntimeError("SMTP_PASS .env içinde tanımlanmalıdır.")
        if not self.from_address:
            raise RuntimeError("MAIL_FROM .env içinde tanımlanmalıdır.")
        if not 1 <= self.port <= 65535:
            raise RuntimeError("SMTP_PORT 1 ile 65535 arasında olmalıdır.")
        if timeout <= 0:
            raise ValueError("SMTP timeout sıfırdan büyük olmalıdır.")

        self.timeout = timeout

    def send(
        self,
        *,
        recipients: str | Sequence[str],
        subject: str,
        body: str,
        html: bool = False,
        sender: str | None = None,
    ) -> None:
        """Send a plain-text or HTML email to one or more recipients."""
        recipient_list = [recipients] if isinstance(recipients, str) else list(recipients)
        recipient_list = [recipient.strip() for recipient in recipient_list if recipient.strip()]
        if not recipient_list:
            raise ValueError("En az bir alıcı belirtilmelidir.")
        if not subject.strip():
            raise ValueError("Mail konusu boş bırakılamaz.")
        if not body:
            raise ValueError("Mail içeriği boş bırakılamaz.")

        message = EmailMessage()
        message["From"] = sender or self.from_address
        message["To"] = ", ".join(recipient_list)
        message["Subject"] = subject.strip()
        message.set_content(body, subtype="html" if html else "plain")

        context = ssl.create_default_context()
        if self.port == 465:
            with smtplib.SMTP_SSL(
                self.server,
                self.port,
                timeout=self.timeout,
                context=context,
            ) as smtp:
                smtp.login(self.login, self.password)
                refused = smtp.send_message(message)
                if refused:
                    raise smtplib.SMTPRecipientsRefused(refused)
            return

        with smtplib.SMTP(self.server, self.port, timeout=self.timeout) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(self.login, self.password)
            refused = smtp.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
