

from smtplib import SMTP_SSL
from email.message import EmailMessage
from ix.misc import Settings
import pandas as pd

class EmailSender:
    """A class to send emails with optional attachments using Gmail's SMTP server."""

    def __init__(
        self,
        to: str,
        subject: str,
        content: str,
    ):
        """Initialize the EmailSender with login credentials from Settings."""
        self.login = Settings.gmail_login
        self.password = Settings.gmail_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465
        self.msg = EmailMessage()
        self.msg["From"] = self.login
        self.msg["To"] = to
        self.msg["Subject"] = subject
        self.msg.set_content(content)

    def attach(self, df: pd.DataFrame, filename: str = "data.csv") -> None:
        """Attach a pandas DataFrame as a CSV file to the email.

        Args:
            df (pd.DataFrame): The DataFrame to attach as a CSV file.
            filename (str): The name of the attached CSV file. Defaults to "data.csv".
        """
        csv_data = df.to_csv(index=False)
        self.msg.add_attachment(csv_data, filename=filename, subtype="csv")

    def send(
        self,
    ) -> None:
        """Send the email with the specified content and any attachments.

        Args:
            to (str): Recipient's email address.
            subject (str): Subject of the email.
            content (str): Body content of the email.
        """
        # Send the email using SMTP_SSL
        with SMTP_SSL(self.smtp_server, self.smtp_port) as smtp:
            smtp.login(self.login, self.password)
            smtp.send_message(self.msg)

