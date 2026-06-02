# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"



ENABLE_EMAIL = False   # ⬅ turn ON later when needed

def send_email(to_email: str, subject: str, body: str):
    if not ENABLE_EMAIL:
        print(f"📧 Email skipped: {subject}")
        return

    try:
        # existing SMTP logic here
        ...
    except Exception as e:
        print(f"❌ Email failed: {e}")