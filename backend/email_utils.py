import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email: str, subject: str, html_body: str):
    """Simple SendGrid wrapper"""
    api_key = os.getenv("SENDGRID_API_KEY")
    sender = os.getenv("SENDER_EMAIL", "noreply@example.com")
    
    if not api_key:
        print("Warning: SENDGRID_API_KEY not set. Email not sent.")
        return

    message = Mail(
        from_email=sender,
        to_emails=to_email,
        subject=subject,
        html_content=html_body
    )
    
    try:
        sg = SendGridAPIClient(api_key)
        sg.send(message)
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

def send_lead_notifications(prospect_email: str, first_name: str, admin_email: str, lead_data: dict):
    # 1. Email Prospect
    send_email(
        to_email=prospect_email,
        subject="Application Received",
        html_body=f"<p>Hi {first_name}, thanks for applying!</p>"
    )

    # 2. Email Admin
    admin_body = f"""
    <h3>New Lead</h3>
    <p>Name: {first_name} {lead_data['last_name']}</p>
    <p>Email: {prospect_email}</p>
    <p>ID: {lead_data['id']}</p>
    """
    send_email(
        to_email=admin_email,
        subject=f"New Lead: {first_name}",
        html_body=admin_body
    )