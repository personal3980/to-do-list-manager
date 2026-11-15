"""Local email preview by default; optional authenticated SMTP delivery."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

from .config import BACKEND_DIR, FRONTEND_ORIGIN


def send_reset_email(email, token):
    # Fragment avoids placing the token in static-server access logs.
    link = f'{FRONTEND_ORIGIN}/reset-password.html#token={token}'
    message = EmailMessage()
    message['Subject'] = 'Reset your Taskwell password'
    message['From'] = os.getenv('SMTP_FROM', 'taskwell@localhost')
    message['To'] = email
    message.set_content(f'Open this link to reset your password:\n\n{link}\n\n'
                        'This link expires in 30 minutes and can be used once.\n'
                        'If you did not request this, ignore this email.\n', cte='8bit')
    delivery = os.getenv('RESET_DELIVERY', 'local')
    if delivery == 'local':
        folder = BACKEND_DIR / 'reset-emails'
        folder.mkdir(mode=0o700, exist_ok=True)
        path = folder / f'{uuid4().hex}.eml'
        # This folder must never be served by the frontend or committed to Git.
        with path.open('x', encoding='utf-8') as output:
            output.write(message.as_string())
        Path(path).chmod(0o600)
    elif delivery == 'smtp':
        with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT', '587')), timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
    else:
        raise ValueError('RESET_DELIVERY must be local or smtp')
