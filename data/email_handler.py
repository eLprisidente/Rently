from flask import current_app
from flask_mail import Mail, Message

mail = None

def init_mail(app):
    global mail
    mail = Mail(app)

def send_email(name, from_email, message_text):
    if not mail:
        return

    subject = "New Contact Form Submission"

    sender = current_app.config['MAIL_USERNAME']
    recipients = ["your-target-email@example.com"]

    msg = Message(subject=subject, sender=sender, recipients=recipients)

    msg.body = (
        f"Name: {name}\n"
        f"Email: {from_email}\n"
        f"Message:\n{message_text}"
    )

    mail.send(msg)
