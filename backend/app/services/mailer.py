import smtplib
from email.message import EmailMessage

from flask import current_app

SUBJECTS = {
    "signup": "Verify your MindBridge email",
    "reset": "Reset your MindBridge password",
}


class MailError(Exception):
    """Raised when the code email cannot be sent. The message is safe to show to users."""


def send_code(to, purpose, code):
    """Send a verification code. Tests replace this with MAILER in the app config."""
    custom = current_app.config.get("MAILER")
    if custom is not None:
        custom(to, purpose, code)
        return

    host = current_app.config.get("SMTP_HOST")
    if not host:
        raise MailError("Email sending is not configured on this server")

    message = EmailMessage()
    message["Subject"] = SUBJECTS[purpose]
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = to
    message.set_content(
        f"Your MindBridge code is {code}. It expires in 10 minutes.\n\n"
        "If you did not ask for this, you can ignore this email."
    )
    try:
        with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=15) as smtp:
            smtp.starttls()
            if current_app.config.get("SMTP_USER"):
                smtp.login(current_app.config["SMTP_USER"], current_app.config["SMTP_PASSWORD"])
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        raise MailError("We could not send the email. Try again in a moment.") from error
