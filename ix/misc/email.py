from smtplib import SMTP_SSL
from email.message import EmailMessage
from ix.misc import Settings
import io

class EmailSender:
    """A class to send emails with optional attachments using Gmail's SMTP server."""

    def __init__(
        self,
        to: str,
        subject: str,
        content: str,
    ):
        """Initialize the EmailSender with login credentials from Settings."""
        self.login = Settings.email_login
        self.password = Settings.email_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465
        self.msg = EmailMessage()
        self.msg["From"] = self.login
        self.msg["To"] = to
        self.msg["Subject"] = subject
        self.msg.set_content(content)

    def attach(self, file_buffer: io.BytesIO, filename: str) -> None:
        """Attach an Excel file (as io.BytesIO) to the email.

        Args:
            file_buffer (io.BytesIO): The file buffer containing the Excel file.
            filename (str): The name of the attached file.
        """
        file_content = file_buffer.getvalue()
        self.msg.add_attachment(file_content, maintype="application", subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)


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
