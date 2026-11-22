"""The action gate for mail. send_mail is the only code that opens an SMTP connection, and it
refuses any address that is not on the teammate allowlist (rulebook: never contact real people)."""
import smtplib
from email.message import EmailMessage

from ..core import config

# Hard-coded on purpose: teammates only. Lower case.
ALLOWLIST = ("devsatish08@gmail.com", "ananyashankar0836@gmail.com")
TEAM_MEMBERS = ("dev", "ananya")  # only these may approve or reject
SENDER = "Synex <outreach@synex.local>"


class MailBlocked(RuntimeError):
    pass


def is_allowed(address: str) -> bool:
    return address.strip().lower() in ALLOWLIST


def send_mail(to_address: str, subject: str, body: str, headers: dict[str, str] | None = None) -> None:
    if not is_allowed(to_address):
        raise MailBlocked(f"{to_address!r} is not on the teammate allowlist")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SENDER, to_address, subject
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(body)
    with smtplib.SMTP(config.smtp_host(), config.smtp_port(), timeout=15) as smtp:
        smtp.send_message(msg)
