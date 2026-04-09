import io
import json
import boto3
from typing import List
from ix.common.settings import Settings
from ix.common import get_logger

logger = get_logger(__name__)


class Boto:
    def __init__(self):
        # Initialize the S3 client for Cloudflare R2
        self.s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{Settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=Settings.r2_access_id,
            aws_secret_access_key=Settings.r2_access_key,
            verify=True,
        )
        self.bucket_name = Settings.r2_bucket_name

    def save_json(self, data: dict, filename: str) -> bool:
        """Upload a JSON object to R2."""
        try:
            body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            self.s3.upload_fileobj(
                io.BytesIO(body),
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "application/json"},
            )
            logger.info("Uploaded JSON to object storage: %s (%d bytes)", filename, len(body))
            return True
        except Exception as e:
            logger.exception("Error uploading JSON %s: %s", filename, e)
            return False

    def get_json(self, filename: str) -> dict:
        """Download and parse a JSON object from R2."""
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=filename)
            return json.loads(response["Body"].read().decode("utf-8"))
        except Exception as e:
            logger.exception("Error reading JSON %s: %s", filename, e)
            return {}

    def list_prefix(self, prefix: str) -> list:
        """List all keys under a prefix."""
        try:
            keys = []
            resp = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            while True:
                if "Contents" in resp:
                    keys.extend(f["Key"] for f in resp["Contents"])
                if resp.get("IsTruncated"):
                    resp = self.s3.list_objects_v2(
                        Bucket=self.bucket_name, Prefix=prefix,
                        ContinuationToken=resp["NextContinuationToken"],
                    )
                else:
                    break
            return keys
        except Exception as e:
            logger.exception("Error listing prefix %s: %s", prefix, e)
            return []

    def save_pdf(self, pdf_content: bytes, filename: str) -> bool:
        try:
            # Upload the PDF to Cloudflare R2
            self.s3.upload_fileobj(
                io.BytesIO(pdf_content),
                self.bucket_name,
                filename,
                ExtraArgs={"ContentType": "application/pdf"},
            )
            logger.info("Uploaded file to object storage: %s", filename)
            return True
        except Exception as e:
            logger.exception("Error uploading file %s: %s", filename, e)
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
                logger.info("No files found in the object storage bucket.")
                return []
        except Exception as e:
            logger.exception("Error listing files in the object storage bucket: %s", e)
            return []

    def get_pdf(self, filename: str) -> bytes:
        try:
            # Get the PDF from Cloudflare R2
            response = self.s3.get_object(Bucket=self.bucket_name, Key=filename)

            # Read the content of the file
            pdf_content = response["Body"].read()
            logger.info("Retrieved file from object storage: %s", filename)
            return pdf_content
        except Exception as e:
            logger.exception("Error retrieving PDF %s: %s", filename, e)
            return b""

    def file_exists(self, filename: str) -> bool:
        try:
            # Check if the file exists in the bucket by fetching metadata
            self.s3.head_object(Bucket=self.bucket_name, Key=filename)
            logger.info("Confirmed file exists in object storage: %s", filename)
            return True
        except self.s3.exceptions.ClientError as e:
            # If a ClientError occurs, the file does not exist
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info("File does not exist in object storage: %s", filename)
                return False
            else:
                # If there is another error, re-raise it
                logger.exception("Error checking existence of %s: %s", filename, e)
                return False

    def rename_file(self, old_filename: str, new_filename: str) -> bool:
        try:
            # Check if the file exists
            if not self.file_exists(old_filename):
                logger.warning("Cannot rename missing file in object storage: %s", old_filename)
                return False

            # Copy the old file to the new file
            self.s3.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": old_filename},
                Key=new_filename,
            )
            logger.info("Copied object %s to %s", old_filename, new_filename)

            # Delete the old file after copying
            self.s3.delete_object(Bucket=self.bucket_name, Key=old_filename)
            logger.info("Deleted original object after rename: %s", old_filename)
            return True
        except Exception as e:
            logger.exception("Error renaming file %s to %s: %s", old_filename, new_filename, e)
            return False

    def delete_pdf(self, filename: str) -> bool:
        try:
            # Delete the PDF file from Cloudflare R2
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=filename,
            )
            logger.info("Deleted object from storage: %s", filename)
            return True
        except Exception as e:
            logger.exception("Error deleting file %s: %s", filename, e)
            return False
