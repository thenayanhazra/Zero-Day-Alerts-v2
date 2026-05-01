from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from smtplib import SMTP

from .router import AlertEvent


@dataclass
class EmailSender:
    smtp_host: str
    from_addr: str
    to_addrs: tuple[str, ...]
    smtp_port: int = 25

    def send(self, event: AlertEvent) -> dict[str, object]:
        message = EmailMessage()
        message["From"] = self.from_addr
        message["To"] = ", ".join(self.to_addrs)
        message["Subject"] = f"[{event.severity.upper()}] {event.title or event.event_id}"
        message.set_content(
            f"Event: {event.event_id}\n"
            f"Source: {event.source}\n"
            f"Severity: {event.severity}\n"
            f"Tags: {', '.join(sorted(event.tags)) or '(none)'}\n\n"
            f"{event.body}"
        )

        with SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.send_message(message)

        return {"ok": True, "channel": "email", "recipients": list(self.to_addrs)}
