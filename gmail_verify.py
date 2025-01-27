import imaplib
import email
from email.header import decode_header
import re

# Your Gmail credentials
EMAIL = "test@gmail.com"
PASSWORD = "fdfdfdf"

def get_otp_from_gmail():
    try:
        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        
        # Select the mailbox to search in
        mail.select("inbox")

        # Search for all emails (change criteria as needed)
        status, messages = mail.search(None, '(SUBJECT "trucksmarter")')
        print(messages)

        # If no messages found, return
        if not messages[0]:
            print("No new OTP emails found.")
            return None

        # Process the most recent email
        email_ids = messages[0].split()
        latest_email_id = email_ids[-1]  # Get the latest email ID
        status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                # Parse the email
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    # Decode byte subject to string
                    subject = subject.decode(encoding if encoding else "utf-8")
                
                # If the email has multiple parts
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            # Search for OTP in the email body using regex
                            otp_match = re.search(r"\b\d{4,6}\b", body)
                            if otp_match:
                                otp = otp_match.group(0)
                                print(f"OTP found: {otp}")
                                return otp
                else:
                    # Process plain text emails
                    body = msg.get_payload(decode=True).decode()
                    otp_match = re.search(r"\b\d{4,6}\b", body)
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

# Call the function
get_otp_from_gmail()
