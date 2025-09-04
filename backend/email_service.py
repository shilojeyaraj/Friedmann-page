"""
Email Service for Sending Passcodes
Supports Gmail, Outlook, and other SMTP providers
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        
    def is_configured(self):
        """Check if email service is properly configured"""
        return bool(self.smtp_username and self.smtp_password)
    
    def send_passcode_email(self, email: str, passcode: str) -> bool:
        """Send passcode email to client"""
        if not self.is_configured():
            print("⚠️ Email service not configured. Please set SMTP_USERNAME and SMTP_PASSWORD in .env file")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = "Your Financial Report Access Code"
            
            # Create HTML content
            html_content = self._create_email_html(passcode)
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.smtp_username, email, msg.as_string())
            server.quit()
            
            print(f"✅ Passcode sent to {email}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email to {email}: {e}")
            return False
    
    def _create_email_html(self, passcode: str) -> str:
        """Create HTML email template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Financial Report Access</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f8fafc;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 300;">
                        Financial Report Access
                    </h1>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 20px;">
                    <h2 style="color: #2d3748; margin: 0 0 20px 0; font-size: 24px;">
                        Your Access Code
                    </h2>
                    
                    <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                        You have requested access to your financial report. Use the following code to log in:
                    </p>
                    
                    <!-- Passcode Box -->
                    <div style="background-color: #f7fafc; border: 2px solid #e2e8f0; border-radius: 12px; padding: 30px; text-align: center; margin: 30px 0;">
                        <div style="font-size: 36px; font-weight: bold; color: #2d3748; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                            {passcode}
                        </div>
                    </div>
                    
                    <!-- Expiration Notice -->
                    <div style="background-color: #fff5f5; border-left: 4px solid #f56565; padding: 15px; margin: 20px 0;">
                        <p style="color: #c53030; margin: 0; font-weight: 500;">
                            ⏰ This code expires in 15 minutes
                        </p>
                    </div>
                    
                    <!-- Security Notice -->
                    <div style="background-color: #f0fff4; border-left: 4px solid #48bb78; padding: 15px; margin: 20px 0;">
                        <p style="color: #2f855a; margin: 0; font-size: 14px;">
                            🔒 If you didn't request this code, please ignore this email. Your account remains secure.
                        </p>
                    </div>
                    
                    <!-- Instructions -->
                    <div style="margin-top: 30px;">
                        <h3 style="color: #2d3748; font-size: 18px; margin: 0 0 15px 0;">What to do next:</h3>
                        <ol style="color: #4a5568; font-size: 14px; line-height: 1.6; margin: 0; padding-left: 20px;">
                            <li>Return to the financial report page</li>
                            <li>Enter the 6-digit code above</li>
                            <li>Click "Verify & Access Report"</li>
                        </ol>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; font-size: 12px; margin: 0;">
                        This is an automated message. Please do not reply to this email.
                    </p>
                    <p style="color: #718096; font-size: 12px; margin: 5px 0 0 0;">
                        © {datetime.now().year} Financial Advisory Services
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

# Create global instance
email_service = EmailService()
