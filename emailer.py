# ============================================================
#  emailer.py — Email alerts for new items
#  Edit EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER below
# ============================================================

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
def find_new_items(old_data, new_data, key=None):
    if not old_data:
        return new_data  # First time = all are new
    # Auto pick key if not given
    if not key and new_data:
        key = list(new_data[0].keys())[0]
    old_vals = {str(item.get(key,"")).lower() for item in old_data}
    return [item for item in new_data
            if str(item.get(key,"")).lower() not in old_vals]


def send_alert(new_items, site_name="Website"):
    if not new_items:
        print("  [Email] No new items — skipping.")
        return

    rows = ""
    for item in new_items:
        cells = "".join(
            f"<tr><td style='color:#888;padding:3px 10px'>{k}</td>"
            f"<td style='padding:3px 10px'><b>{v}</b></td></tr>"
            for k, v in item.items()
        )
        rows += f"<div style='background:#f5f5f5;border-radius:6px;" \
                f"padding:10px;margin-bottom:10px'><table>{cells}</table></div>"

    html = f"""
    <html><body style='font-family:sans-serif;max-width:580px;margin:auto'>
      <h2 style='color:#2d6a4f'>🆕 {len(new_items)} New Items on {site_name}</h2>
      <p style='color:#666'>Your scraper found these new listings:</p>
      {rows}
      <p style='color:#bbb;font-size:11px'>Sent by Smart Scraper v2 🕷️</p>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🆕 {len(new_items)} New Items — {site_name}"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(f"  ✅ Email sent! {len(new_items)} new items.")
    except smtplib.SMTPAuthenticationError:
        print("  ❌ Wrong email/password. Check App Password in emailer.py")
    except Exception as e:
        print(f"  ❌ Email error: {e}")