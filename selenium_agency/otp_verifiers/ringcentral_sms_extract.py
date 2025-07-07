import imaplib
import email
from email.header import decode_header
import re
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

# Your Gmail credentials
EMAIL = os.getenv("EMAIL")
SUPEREMAIL = os.getenv("EMAIL_SUPER")
DANELAPASSWORD = os.getenv("DANELAGMAILPASSWORD")
CHYONOPASSWORD = os.getenv("CHYONOGMAILPASSWORD")

def get_central_dispatch_code():
    """
    Convenience function to get Central Dispatch confirmation code from RingCentral SMS
    """
    return ringcentral_sms_extract()

def get_recent_central_dispatch_code(minutes_back=10):
    """
    Get Central Dispatch code from emails received in the last N minutes
    """
    return ringcentral_sms_extract(time_filter_minutes=minutes_back)

def ringcentral_sms_extract(subject=None, time_filter_minutes=None):
    try:
        print("Logging in to Gmail with the following credentials:")
        print(EMAIL, DANELAPASSWORD)

        # Connect to Gmail's IMAP server
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        if EMAIL is not None and DANELAPASSWORD is not None:
            mail.login(EMAIL, DANELAPASSWORD)
        
        # Select the mailbox to search in
        mail.select("inbox")

        # Search for RingCentral SMS emails - look for "New Text Message from" in subject
        if subject:
            _, messages = mail.search(None, f'(SUBJECT "{subject}")')
        else:
            # Search for RingCentral SMS notifications
            search_criteria = '(FROM "service@ringcentral.com" SUBJECT "New Text Message")'
            
            # Add time filter if specified
            if time_filter_minutes:
                # Calculate date for IMAP search (format: DD-Mon-YYYY)
                since_date = (datetime.now() - timedelta(minutes=time_filter_minutes)).strftime("%d-%b-%Y")
                search_criteria = f'(FROM "service@ringcentral.com" SUBJECT "New Text Message" SINCE "{since_date}")'
            
            _, messages = mail.search(None, search_criteria)

        # If no messages found, return
        if not messages[0]:
            print("No RingCentral SMS emails found.")
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
                email_subject, encoding = decode_header(msg["Subject"])[0]
               
                print(f"Email subject: {email_subject}")
                if isinstance(email_subject, bytes):
                    # Decode byte subject to string
                    email_subject = email_subject.decode(encoding if encoding else "utf-8")
                
                # Function to extract code from email body
                def extract_code_from_body(body_text):
                    print(f"Email body: {body_text[:500]}...")  # Print first 500 chars for debugging
                    
                    # Look for Central Dispatch confirmation code pattern
                    central_dispatch_pattern = r'Central Dispatch confirmation code is (\d{6})'
                    match = re.search(central_dispatch_pattern, body_text, re.IGNORECASE)
                    if match:
                        code = match.group(1)
                        print(f"Central Dispatch code found: {code}")
                        return code
                    
                    # Look for any confirmation code pattern
                    confirmation_patterns = [
                        r'confirmation code is (\d{6})',
                        r'verification code is (\d{6})',
                        r'code is (\d{6})',
                        r'your code: (\d{6})',
                        r'\b(\d{6})\b'  # Any 6-digit number as fallback
                    ]
                    
                    for pattern in confirmation_patterns:
                        match = re.search(pattern, body_text, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            print(f"Code found with pattern '{pattern}': {code}")
                            return code
                    
                    return None
                
                # If the email has multiple parts
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type in ["text/plain", "text/html"]:
                            try:
                                body = part.get_payload(decode=True).decode('utf-8')
                                code = extract_code_from_body(body)
                                if code:
                                    # Mark email as read
                                    mail.store(latest_email_id, '+FLAGS', '\\Seen')
                                    return code
                            except Exception as e:
                                print(f"Error decoding part: {e}")
                                continue
                else:
                    # Single part email
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8')
                        code = extract_code_from_body(body)
                        if code:
                            # Mark email as read
                            mail.store(latest_email_id, '+FLAGS', '\\Seen')
                            return code
                    except Exception as e:
                        print(f"Error decoding email body: {e}")
                
        print("No verification code found in the email.")
        return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        try:
            mail.logout()
        except:
            pass  # Ignore logout errors

# Test function
if __name__ == "__main__":
    print("Testing RingCentral SMS extraction...")
    code = get_central_dispatch_code()
    if code:
        print(f"Successfully extracted code: {code}")
    else:
        print("No code found")

