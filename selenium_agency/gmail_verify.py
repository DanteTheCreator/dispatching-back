import imaplib
import email
from email.header import decode_header
import re
from dotenv import load_dotenv
import os

load_dotenv()

# Your Gmail credentials
EMAIL = os.getenv("EMAIL")
SUPEREMAIL = os.getenv("SUPEREMAIL")
PASSWORD = os.getenv("GMAILAPPPASSWORD")

def get_otp_from_gmail_central(subject):
    try:
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        if EMAIL is not None and PASSWORD is not None:
            mail.login(EMAIL, PASSWORD)
        
        # Select the mailbox to search in
        mail.select("inbox")

        # Search for emails with specific subject
        _, messages = mail.search(None, f'(SUBJECT "{subject}")')

        # If no messages found, return
        if not messages[0]:
            print("No new OTP emails found.")
            return None

        # Process the most recent email
        email_ids = messages[0].split()
        latest_email_id = email_ids[-1]  # Get the latest email ID
        _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        if not msg_data:
            return None
            
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                # Parse the email
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
               
                print(subject)
                if isinstance(subject, bytes):
                    # Decode byte subject to string
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # If the email has multiple parts
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode() #type: ignore
                            otp_match = re.search(r'\b[0-9]{6}\b', body)
                            if otp_match:
                                otp = otp_match.group(0)
                                print(f"OTP found: {otp}")
                                return otp
                            # Look for a 6-digit number within a p tag with class "security-code"
                            pattern = r'<p[^>]*class="security-code"[^>]*>(\d{6})</p>'
                            match = re.search(pattern, body)
                            
                            if match:
                                print(f"OTP found: {match.group(1)}")
                                return match.group(1)
                            
                            # Fallback: look for any 6-digit number within any p tag
                            pattern = r'<p[^>]*>(\d{6})</p>'
                            match = re.search(pattern, body)
                            
                            if match:
                                print(f"OTP found: {match.group(1)}")
                                return match.group(1)
                    
                
        print("No OTP found in the email.")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        mail.logout()


def get_otp_from_gmail_super(subject):
    try:
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        if EMAIL is not None and PASSWORD is not None:
            mail.login(EMAIL, PASSWORD)
        
        # Select the mailbox to search in
        mail.select("inbox")

        # Search for emails with specific subject
        _, messages = mail.search(None, f'(SUBJECT "{subject}")')

        # If no messages found, return
        if not messages[0]:
            print("No new OTP emails found.")
            return None

        # Process the most recent email
        email_ids = messages[0].split()
        latest_email_id = email_ids[-1]  # Get the latest email ID
        _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        if not msg_data:
            return None
            
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                # Parse the email
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
               
                print(subject)
                if isinstance(subject, bytes):
                    # Decode byte subject to string
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # If the email has multiple parts
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode() #type: ignore

                            # Look for a 6-digit number within a p tag with class "security-code"
                            pattern = r'<p[^>]*class="security-code"[^>]*>(\d{6})</p>'
                            match = re.search(pattern, body)
                            
                            if match:
                                print(f"OTP found: {match.group(1)}")
                                return match.group(1)
                            
                            # Fallback: look for any 6-digit number within any p tag
                            pattern = r'<p[^>]*>(\d{6})</p>'
                            match = re.search(pattern, body)
                            
                            if match:
                                print(f"OTP found: {match.group(1)}")
                                return match.group(1)
                            
                else:
                    # Process plain text emails
                    body = msg.get_payload(decode=True).decode() #type: ignore
                    otp_match = re.search(r'\b[0-9]{6}\b', body)
                    if otp_match:
                        otp = otp_match.group(0)
                        print(f"OTP found: {otp}")
                        return otp
        
        print("No OTP found in the email.")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        mail.logout()


#get_otp_from_gmail("Super Dispatch Verification Code")