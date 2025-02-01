

class GmailVerifier:
    def __init__(self, email, password, imap_server="imap.gmail.com"):
        self.email = email
        self.password = password
        self.imap_server = imap_server

    def __connect_to_mailbox(self):
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.select("inbox")
            return mail
        except Exception as e:
            print(f"Failed to connect to mailbox: {e}")
            return None

    def __search_emails(self, mail, criteria):
        try:
            status, messages = mail.search(None, criteria)
            if status != "OK":
                print("No messages found.")
                return []
            return messages[0].split()
        except Exception as e:
            print(f"Failed to search emails: {e}")
            return []

    def __fetch_email(self, mail, email_id):
        try:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                print("Failed to fetch email.")
                return None
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    return email.message_from_bytes(response_part[1])
            return None
        except Exception as e:
            print(f"Failed to fetch email: {e}")
            return None

    def __extract_otp(self, body):
        otp_match = re.search(r"\b\d{4,6}\b", body)
        if otp_match:
            return otp_match.group(0)
        return None

    def get_otp_from_email(self, subject_criteria):
        mail = self.__connect_to_mailbox()
        if not mail:
            return None

        try:
            email_ids = self.__search_emails(mail, f'(SUBJECT "{subject_criteria}")')
            if not email_ids:
                print("No new OTP emails found.")
                return None

            latest_email_id = email_ids[-1]
            msg = self.__fetch_email(mail, latest_email_id)
            if not msg:
                return None

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        otp = self.extract_otp(body)
                        if otp:
                            print(f"OTP found: {otp}")
                            return otp
            else:
                body = msg.get_payload(decode=True).decode()
                otp = self.__extract_otp(body)
                if otp:
                    print(f"OTP found: {otp}")
                    return otp

            print("No OTP found in the email.")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            mail.logout()