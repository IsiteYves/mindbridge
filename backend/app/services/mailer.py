import smtplib
from email.message import EmailMessage

from flask import current_app

from app.services.email_templates import code_email, message_email

class MailError(Exception):
    """Raised when an email cannot be sent. The message is safe to show to users."""


# Always upgrades to TLS; login runs only when an SMTP user is configured.
def _deliver(to, subject, text, html_body, reply_to=None):
    host = current_app.config.get("SMTP_HOST")
    if not host:
        raise MailError("Email sending is not configured on this server")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = to
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(text)
    message.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=15) as smtp:
            smtp.starttls()
            if current_app.config.get("SMTP_USER"):
                smtp.login(current_app.config["SMTP_USER"], current_app.config["SMTP_PASSWORD"])
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        raise MailError("We could not send the email. Try again in a moment.") from error


def send_code(to, purpose, code):
    
    # A MAILER config hook replaces real delivery, used by tests and local development.
    custom = current_app.config.get("MAILER")
    if custom is not None:
        custom(to, purpose, code)
        return
    subject, text, html_body = code_email(purpose, code)
    _deliver(to, subject, text, html_body)


def send_reminder_email(to, subject, body):
   
    custom = current_app.config.get("REMINDER_MAILER")
    if custom is not None:
        custom(to, subject, body)
        return
    text, html_body = message_email(subject, body)
    _deliver(to, subject, text, html_body)


def send_contact_message(to, name, sender_email, subject, body):
    custom = current_app.config.get("CONTACT_MAILER")
    if custom is not None:
        custom(to, name, sender_email, subject, body)
        return
    heading = f"Contact: {subject}"
    text, html_body = message_email(heading, f"From {name} <{sender_email}>\n\n{body}")
    _deliver(to, heading, text, html_body, reply_to=sender_email)
