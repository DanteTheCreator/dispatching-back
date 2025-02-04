from gmail_verifier import GmailVerifier

class TruckSmarterVerifier(GmailVerifier):
    def __init__(self, email, password):
        super().__init__(email, password)

    def get_otp(self):
        return self.get_otp_from_email("trucksmarter")