"""
Email Service for MarketPulse AI
Sends real email alerts via SMTP (Gmail / any SMTP provider).
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from datetime import datetime


def send_alert_email(to_email: str, symbol: str, alert_type: str, threshold: float, current_value: float) -> bool:
    """
    Sends a real email alert when a price/sentiment threshold is breached.
    
    Returns True if email was sent successfully, False otherwise.
    """
    smtp_email = current_app.config.get("SMTP_EMAIL")
    smtp_password = current_app.config.get("SMTP_PASSWORD")
    smtp_host = current_app.config.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(current_app.config.get("SMTP_PORT", 587))

    if not smtp_email or not smtp_password:
        print(f"[EMAIL SERVICE] SMTP not configured. Skipping email to {to_email}.")
        return False

    if not to_email:
        print("[EMAIL SERVICE] No recipient email provided. Skipping.")
        return False

    # Build the alert description
    if alert_type == "price_above":
        direction = "risen above"
        icon = "🚀"
        action_hint = "Consider taking profits or reviewing your position."
    elif alert_type == "price_below":
        direction = "fallen below"
        icon = "🔻"
        action_hint = "Consider buying the dip or setting a stop-loss."
    else:
        direction = "dropped below sentiment threshold of"
        icon = "📉"
        action_hint = "Market sentiment is bearish. Exercise caution."

    now = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    # Create the email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{icon} MarketPulse Alert: {symbol} has {direction} ${threshold:.2f}"
    msg["From"] = f"MarketPulse AI <{smtp_email}>"
    msg["To"] = to_email

    # Plain text version
    text_body = f"""
MarketPulse AI - Price Alert Triggered
=======================================

Symbol:         {symbol}
Alert Type:     {alert_type.replace('_', ' ').title()}
Threshold:      ${threshold:.2f}
Current Value:  ${current_value:.2f}
Triggered At:   {now}

{action_hint}

---
This alert was sent by MarketPulse AI.
Manage your alerts at your MarketPulse dashboard.
"""

    # HTML version (premium styled email)
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#0a0e17; font-family:'Segoe UI',Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0e17;">
        <tr>
            <td align="center" style="padding:40px 20px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#111827,#1a1f2e);border-radius:16px;border:1px solid #2a3040;overflow:hidden;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:30px 40px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;">
                                {icon} MarketPulse AI
                            </h1>
                            <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                                Price Alert Triggered
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding:40px;">
                            <h2 style="margin:0 0 24px;color:#ffffff;font-size:20px;font-weight:600;">
                                {symbol} has {direction} <span style="color:#6366f1;">${threshold:.2f}</span>
                            </h2>
                            
                            <!-- Stats Grid -->
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                                <tr>
                                    <td width="50%" style="padding:16px;background:#1e2433;border-radius:12px 0 0 12px;border-right:1px solid #2a3040;">
                                        <p style="margin:0;color:#9ca3af;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Threshold</p>
                                        <p style="margin:8px 0 0;color:#ffffff;font-size:24px;font-weight:700;">${threshold:.2f}</p>
                                    </td>
                                    <td width="50%" style="padding:16px;background:#1e2433;border-radius:0 12px 12px 0;">
                                        <p style="margin:0;color:#9ca3af;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Current Price</p>
                                        <p style="margin:8px 0 0;color:{'#22c55e' if alert_type == 'price_above' else '#ef4444'};font-size:24px;font-weight:700;">${current_value:.2f}</p>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Action Hint -->
                            <div style="background:#1e2433;border-radius:12px;padding:16px 20px;border-left:4px solid #6366f1;">
                                <p style="margin:0;color:#d1d5db;font-size:14px;line-height:1.6;">
                                    💡 <strong style="color:#ffffff;">Suggestion:</strong> {action_hint}
                                </p>
                            </div>
                            
                            <!-- Timestamp -->
                            <p style="margin:24px 0 0;color:#6b7280;font-size:12px;text-align:center;">
                                Triggered on {now}
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding:20px 40px;border-top:1px solid #2a3040;text-align:center;">
                            <p style="margin:0;color:#6b7280;font-size:12px;">
                                This alert was sent by MarketPulse AI &bull; 
                                Manage alerts in your dashboard
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Send the email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())
        
        print(f"[EMAIL SERVICE] ✅ Email sent successfully to {to_email} for {symbol} alert.")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"[EMAIL SERVICE] ❌ SMTP Authentication failed. Check SMTP_EMAIL and SMTP_PASSWORD in .env")
        print(f"[EMAIL SERVICE]    For Gmail, use an App Password: https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        print(f"[EMAIL SERVICE] ❌ Failed to send email to {to_email}: {e}")
        return False
