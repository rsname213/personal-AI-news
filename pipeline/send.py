"""
Gmail SMTP delivery via App Password.

Uses port 465 (SMTP_SSL) — simpler than port 587 STARTTLS, no explicit starttls() call needed.
Credentials come from GMAIL_USER and GMAIL_APP_PASSWORD environment variables.
Self-send: From and To are the same address.

On any SMTP failure: logs [ERROR] and raises SystemExit(1) so GitHub Actions marks the run red.
"""
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def send_email(subject: str, html_body: str, text_body: str) -> None:
    """
    Send the newsletter email via Gmail SMTP.

    Args:
        subject: Email subject line (should include date).
        html_body: Premailer-processed HTML body.
        text_body: Plain-text fallback body.

    Raises:
        SystemExit(1) on any SMTP failure.
    """
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_user   # Self-send per DEL-02
    msg["X-Mailer"] = "Personal AI Newsletter"

    # Attach plain text first, HTML second (email clients prefer last part)
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, gmail_user, msg.as_string())
            print(f"[OK] Email sent: '{subject}' -> {gmail_user}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR] Gmail authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD. Error: {e}")
        raise SystemExit(1)
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error during send: {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error sending email: {e}")
        raise SystemExit(1)


def build_subject() -> str:
    """Build the email subject line with today's date (DEL-03)."""
    today = datetime.now().strftime("%B %-d, %Y")
    return f"Neel's AI Briefing \u2014 {today}"
