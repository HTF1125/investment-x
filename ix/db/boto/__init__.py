import io
import boto3
from typing import List
from ix.misc.settings import Settings


class Boto:
    def __init__(self):
        # Initialize the S3 client for Cloudflare R2
        self.s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{Settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=Settings.r2_access_id,
            aws_secret_access_key=Settings.r2_access_key,
            verify=True,  # Enable SSL verification
        )
        self.bucket_name = Settings.r2_bucket_name  # Cloudflare R2 bucket name

    def save_pdf(self, pdf_content: bytes, filename: str) -> bool:
        try:
            # Upload the PDF to Cloudflare R2
            self.s3.upload_fileobj(
                io.BytesIO(pdf_content),
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "application/pdf"},
            )
            print(f"File {filename} uploaded successfully.")
            return True
        except Exception as e:
            print(f"Error uploading file {filename}: {e}")
            return False

    def list_files(self) -> List[str]:
        try:
            # List files in the R2 bucket
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)

            # If the bucket contains files
            if "Contents" in response:
                files = [file["Key"] for file in response["Contents"]]
                return files
            else:
                print("No files found in the bucket.")
                return []
        except Exception as e:
            print(f"Error listing files in the bucket: {e}")
            return []

    def get_pdf(self, filename: str) -> bytes:
        try:
            # Get the PDF from Cloudflare R2
            response = self.s3.get_object(Bucket=self.bucket_name, Key=filename)

            # Read the content of the file
            pdf_content = response["Body"].read()
            print(f"Successfully retrieved {filename}.")
            return pdf_content
        except Exception as e:
            print(f"Error retrieving PDF {filename}: {e}")
            return b""

    def file_exists(self, filename: str) -> bool:
        try:
            # Check if the file exists in the bucket by fetching metadata
            self.s3.head_object(Bucket=self.bucket_name, Key=filename)
            print(f"File {filename} exists.")
            return True
        except self.s3.exceptions.ClientError as e:
            # If a ClientError occurs, the file does not exist
            if e.response["Error"]["Code"] == "NoSuchKey":
                print(f"File {filename} does not exist.")
                return False
            else:
                # If there is another error, re-raise it
                print(f"Error checking existence of {filename}: {e}")
                return False

    def rename_file(self, old_filename: str, new_filename: str) -> bool:
        try:
            # Check if the file exists
            if not self.file_exists(old_filename):
                print(f"Cannot rename {old_filename}, file does not exist.")
                return False

            # Copy the old file to the new file
            self.s3.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": old_filename},
                Key=new_filename,
            )
            print(f"File {old_filename} copied to {new_filename}.")

            # Delete the old file after copying
            self.s3.delete_object(Bucket=self.bucket_name, Key=old_filename)
            print(f"File {old_filename} deleted.")
            return True
        except Exception as e:
            print(f"Error renaming file {old_filename} to {new_filename}: {e}")
            return False

    def delete_pdf(self, filename: str) -> bool:
        try:
            # Delete the PDF file from Cloudflare R2
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=filename,
            )
            print(f"File {filename} deleted successfully.")
            return True
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
            return False
