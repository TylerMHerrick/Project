"""S3 client wrapper for email storage operations."""
import boto3
from typing import Optional, BinaryIO
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)


class S3Client:
    """Wrapper for S3 operations."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.client = boto3.client('s3', **Config.get_boto3_config())
        self.bucket = Config.EMAIL_BUCKET
    
    def get_email(self, object_key: str) -> bytes:
        """Retrieve email from S3.
        
        Args:
            object_key: S3 object key
            
        Returns:
            Raw email bytes
            
        Raises:
            Exception: If email cannot be retrieved
        """
        try:
            logger.info(f"Retrieving email from S3: {object_key}")
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to retrieve email from S3: {str(e)}")
            raise
    
    def store_attachment(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> str:
        """Store email attachment in S3.
        
        Args:
            key: S3 object key
            data: Attachment data
            content_type: MIME type of attachment
            
        Returns:
            S3 object key
        """
        try:
            logger.info(f"Storing attachment to S3: {key}")
            self.client.put_object(
                Bucket=self.bucket,
                Key=f"attachments/{key}",
                Body=data,
                ContentType=content_type,
                ServerSideEncryption='AES256'
            )
            return f"attachments/{key}"
        except Exception as e:
            logger.error(f"Failed to store attachment: {str(e)}")
            raise
    
    def get_attachment(self, key: str) -> bytes:
        """Retrieve attachment from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            Attachment bytes
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to retrieve attachment: {str(e)}")
            raise
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for attachment download.
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise

