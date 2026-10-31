import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st


def _setting(key):
    value = os.environ.get(key)
    if value:
        return value
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def send_reminder_email(to_email, student_name, book_title, due_date, is_overdue):
    """Send a single reminder email. Returns (True, msg) or (False, error_msg)."""
    
    sender_email = _setting("EMAIL_SENDER")
    sender_password = _setting("EMAIL_PASSWORD")
    if not sender_email or not sender_password:
        return False, "Email credentials are not configured."
    
    # 2. Build the email content
    subject = f"⚠️ OVERDUE BOOK: {book_title}" if is_overdue else f"⏰ Reminder: '{book_title}' is due soon"
    
    body = f"""
    Hello {student_name},
    
    This is a notification from the College Library (LibFind).
    
    Book: {book_title}
    Due Date: {str(due_date)[:10]}
    
    {"Your book is currently OVERDUE. Please return it immediately to avoid further fines." if is_overdue else "Please remember to return or renew this book by the due date to avoid fines."}
    
    Thank you,
    The Library Team
    """
    
    # 3. Connect to Gmail SMTP and send
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail's server
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True, f"Sent to {to_email}"
    except Exception as e:
        return False, f"Could not send reminder to {to_email}: {e}"