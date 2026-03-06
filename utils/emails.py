"""
NA Travels - Email Templates & Sending
"""
from flask import current_app, render_template_string
from flask_mail import Message
from app import mail
from utils.helpers import generate_email_token


# ── Email Templates ───────────────────────────────────────────────────────────

VERIFY_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }
    .container { max-width: 600px; margin: 40px auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .header { background: linear-gradient(135deg, #1a73e8, #0d47a1); padding: 30px; text-align: center; }
    .header h1 { color: #fff; margin: 0; font-size: 28px; }
    .header p { color: #cce4ff; margin: 5px 0 0; }
    .body { padding: 30px 40px; }
    .body h2 { color: #333; }
    .body p { color: #555; line-height: 1.6; }
    .btn { display: inline-block; background: #1a73e8; color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-size: 16px; font-weight: bold; margin: 20px 0; }
    .footer { background: #f9f9f9; padding: 20px 40px; text-align: center; color: #999; font-size: 13px; }
    .link-text { font-size: 12px; color: #888; word-break: break-all; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✈️ NA Travels</h1>
      <p>Explore the World with Us</p>
    </div>
    <div class="body">
      <h2>Verify Your Email Address</h2>
      <p>Hi <strong>{{ name }}</strong>,</p>
      <p>Thank you for registering with NA Travels! Please verify your email address to activate your account and start exploring amazing destinations.</p>
      <div style="text-align: center;">
        <a href="{{ verify_url }}" class="btn">✅ Verify Email</a>
      </div>
      <p>This link expires in <strong>24 hours</strong>.</p>
      <p class="link-text">If the button doesn't work, copy and paste this link:<br>{{ verify_url }}</p>
    </div>
    <div class="footer">
      <p>© 2024 NA Travels. If you didn't create an account, you can safely ignore this email.</p>
    </div>
  </div>
</body>
</html>
"""

RESET_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }
    .container { max-width: 600px; margin: 40px auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .header { background: linear-gradient(135deg, #e53935, #b71c1c); padding: 30px; text-align: center; }
    .header h1 { color: #fff; margin: 0; font-size: 28px; }
    .header p { color: #ffcdd2; margin: 5px 0 0; }
    .body { padding: 30px 40px; }
    .body h2 { color: #333; }
    .body p { color: #555; line-height: 1.6; }
    .btn { display: inline-block; background: #e53935; color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-size: 16px; font-weight: bold; margin: 20px 0; }
    .footer { background: #f9f9f9; padding: 20px 40px; text-align: center; color: #999; font-size: 13px; }
    .link-text { font-size: 12px; color: #888; word-break: break-all; }
    .warning { background: #fff3e0; border-left: 4px solid #ff9800; padding: 12px 16px; border-radius: 4px; color: #e65100; font-size: 14px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✈️ NA Travels</h1>
      <p>Password Reset Request</p>
    </div>
    <div class="body">
      <h2>Reset Your Password</h2>
      <p>Hi <strong>{{ name }}</strong>,</p>
      <p>We received a request to reset the password for your NA Travels account. Click the button below to choose a new password.</p>
      <div style="text-align: center;">
        <a href="{{ reset_url }}" class="btn">🔑 Reset Password</a>
      </div>
      <p>This link expires in <strong>1 hour</strong>.</p>
      <div class="warning">⚠️ If you didn't request a password reset, please ignore this email. Your account is safe.</div>
      <p class="link-text">If the button doesn't work, copy and paste this link:<br>{{ reset_url }}</p>
    </div>
    <div class="footer">
      <p>© 2024 NA Travels. For security, this link will expire in 1 hour.</p>
    </div>
  </div>
</body>
</html>
"""

WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }
    .container { max-width: 600px; margin: 40px auto; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .header { background: linear-gradient(135deg, #2e7d32, #1b5e20); padding: 30px; text-align: center; }
    .header h1 { color: #fff; margin: 0; font-size: 28px; }
    .header p { color: #c8e6c9; margin: 5px 0 0; }
    .body { padding: 30px 40px; }
    .body h2 { color: #333; }
    .body p { color: #555; line-height: 1.6; }
    .features { background: #f1f8e9; border-radius: 8px; padding: 20px; margin: 20px 0; }
    .feature-item { margin: 8px 0; color: #33691e; }
    .btn { display: inline-block; background: #2e7d32; color: #fff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-size: 16px; font-weight: bold; margin: 20px 0; }
    .footer { background: #f9f9f9; padding: 20px 40px; text-align: center; color: #999; font-size: 13px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✈️ NA Travels</h1>
      <p>Welcome Aboard!</p>
    </div>
    <div class="body">
      <h2>🎉 You're All Set, {{ name }}!</h2>
      <p>Your NA Travels account has been verified. Get ready to explore the world's most amazing destinations!</p>
      <div class="features">
        <div class="feature-item">🗺️ Discover thousands of travel destinations</div>
        <div class="feature-item">⭐ Read and write authentic travel reviews</div>
        <div class="feature-item">📸 Share your travel photos</div>
        <div class="feature-item">❤️ Save your favorite places</div>
      </div>
      <div style="text-align: center;">
        <a href="{{ frontend_url }}" class="btn">🌍 Start Exploring</a>
      </div>
    </div>
    <div class="footer">
      <p>© 2024 NA Travels. Happy travels!</p>
    </div>
  </div>
</body>
</html>
"""


# ── Send Functions ─────────────────────────────────────────────────────────────

def send_verification_email(user_email: str, user_name: str):
    """Send email verification link."""
    try:
        token = generate_email_token(user_email, salt="email-verify")
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
        verify_url = f"{frontend_url}/verify-email?token={token}"

        html = render_template_string(VERIFY_EMAIL_TEMPLATE, name=user_name, verify_url=verify_url)
        msg = Message(
            subject="✈️ NA Travels – Verify Your Email",
            recipients=[user_email],
            html=html,
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Verification email failed: {e}")
        return False


def send_password_reset_email(user_email: str, user_name: str):
    """Send password reset link."""
    try:
        token = generate_email_token(user_email, salt="password-reset")
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={token}"

        html = render_template_string(RESET_PASSWORD_TEMPLATE, name=user_name, reset_url=reset_url)
        msg = Message(
            subject="🔑 NA Travels – Password Reset Request",
            recipients=[user_email],
            html=html,
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Reset email failed: {e}")
        return False


def send_welcome_email(user_email: str, user_name: str):
    """Send welcome email after verification."""
    try:
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
        html = render_template_string(WELCOME_TEMPLATE, name=user_name, frontend_url=frontend_url)
        msg = Message(
            subject="🎉 Welcome to NA Travels!",
            recipients=[user_email],
            html=html,
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Welcome email failed: {e}")
        return False
