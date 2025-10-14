"""
Comprehensive tests for S3 Client operations.
Tests: email storage, attachment handling, presigned URLs
"""
import pytest
import boto3
from moto import mock_s3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.s3_client import S3Client
from shared.config import Config


@pytest.fixture
def s3_setup():
    """Set up mock S3 bucket."""
    with mock_s3():
        # Create mock bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket=Config.EMAIL_BUCKET)
        yield s3_client


class TestS3Client:
    """Comprehensive S3 client test cases."""
    
    def test_get_email_success(self, s3_setup):
        """✅ TEST: Retrieve email from S3"""
        # Setup
        test_email = b"From: test@example.com\nTo: project@domain.com\nSubject: Test\n\nBody content"
        s3_setup.put_object(
            Bucket=Config.EMAIL_BUCKET,
            Key='emails/test-email-123',
            Body=test_email
        )
        
        # Execute
        client = S3Client()
        result = client.get_email('emails/test-email-123')
        
        # Verify
        assert result == test_email, "Email content should match"
        print("   ✓ Email retrieved successfully")
    
    def test_get_email_not_found(self, s3_setup):
        """✅ TEST: Handle missing email gracefully"""
        client = S3Client()
        
        with pytest.raises(Exception):
            client.get_email('emails/nonexistent')
        
        print("   ✓ Properly handles missing email")
    
    def test_store_attachment_pdf(self, s3_setup):
        """✅ TEST: Store PDF attachment"""
        client = S3Client()
        pdf_data = b"%PDF-1.4 fake pdf content"
        
        # Execute
        key = client.store_attachment(
            'project-123/drawing.pdf',
            pdf_data,
            'application/pdf'
        )
        
        # Verify storage
        assert key.startswith('attachments/'), "Key should have attachments prefix"
        
        # Verify retrieval
        stored_data = s3_setup.get_object(Bucket=Config.EMAIL_BUCKET, Key=key)
        assert stored_data['Body'].read() == pdf_data, "PDF data should match"
        assert stored_data['ContentType'] == 'application/pdf', "Content type should be correct"
        assert stored_data['ServerSideEncryption'] == 'AES256', "Should be encrypted"
        
        print("   ✓ PDF attachment stored with encryption")
    
    def test_store_attachment_image(self, s3_setup):
        """✅ TEST: Store image attachment"""
        client = S3Client()
        image_data = b"\x89PNG\r\n\x1a\n fake png"
        
        key = client.store_attachment(
            'project-456/photo.png',
            image_data,
            'image/png'
        )
        
        assert 'attachments/' in key
        print("   ✓ Image attachment stored successfully")
    
    def test_store_attachment_docx(self, s3_setup):
        """✅ TEST: Store DOCX attachment"""
        client = S3Client()
        docx_data = b"PK\x03\x04 fake docx content"
        
        key = client.store_attachment(
            'project-789/specs.docx',
            docx_data,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        assert key is not None
        print("   ✓ DOCX attachment stored successfully")
    
    def test_get_attachment(self, s3_setup):
        """✅ TEST: Retrieve attachment from S3"""
        client = S3Client()
        
        # Store attachment
        test_data = b"Test attachment content"
        key = client.store_attachment('test.txt', test_data, 'text/plain')
        
        # Retrieve attachment
        retrieved = client.get_attachment(key)
        
        assert retrieved == test_data, "Retrieved data should match stored data"
        print("   ✓ Attachment retrieved correctly")
    
    def test_get_attachment_not_found(self, s3_setup):
        """✅ TEST: Handle missing attachment"""
        client = S3Client()
        
        with pytest.raises(Exception):
            client.get_attachment('attachments/missing.pdf')
        
        print("   ✓ Properly handles missing attachment")
    
    def test_generate_presigned_url(self, s3_setup):
        """✅ TEST: Generate presigned URL for download"""
        client = S3Client()
        
        # Store a file first
        test_data = b"Download me"
        key = client.store_attachment('download.pdf', test_data, 'application/pdf')
        
        # Generate presigned URL
        url = client.generate_presigned_url(key, expiration=3600)
        
        assert url is not None
        assert Config.EMAIL_BUCKET in url
        assert key in url
        print("   ✓ Presigned URL generated successfully")
    
    def test_generate_presigned_url_custom_expiration(self, s3_setup):
        """✅ TEST: Generate presigned URL with custom expiration"""
        client = S3Client()
        
        key = client.store_attachment('test.pdf', b"data", 'application/pdf')
        
        # Custom expiration (1 hour vs default)
        url = client.generate_presigned_url(key, expiration=7200)
        
        assert url is not None
        print("   ✓ Custom expiration URL generated")
    
    def test_large_file_storage(self, s3_setup):
        """✅ TEST: Store large file (simulated)"""
        client = S3Client()
        
        # Simulate 5MB file
        large_data = b"x" * (5 * 1024 * 1024)
        key = client.store_attachment('large-file.pdf', large_data, 'application/pdf')
        
        # Verify
        retrieved = client.get_attachment(key)
        assert len(retrieved) == len(large_data), "Large file should be stored completely"
        print("   ✓ Large file (5MB) stored successfully")
    
    def test_multiple_attachments_same_project(self, s3_setup):
        """✅ TEST: Store multiple attachments for same project"""
        client = S3Client()
        
        attachments = [
            ('project-123/drawing1.pdf', b'drawing 1', 'application/pdf'),
            ('project-123/drawing2.pdf', b'drawing 2', 'application/pdf'),
            ('project-123/specs.docx', b'specs', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        ]
        
        keys = []
        for filename, data, content_type in attachments:
            key = client.store_attachment(filename, data, content_type)
            keys.append(key)
        
        assert len(keys) == 3, "All attachments should be stored"
        assert all('project-123' in k for k in keys), "All keys should reference project"
        print("   ✓ Multiple attachments stored for same project")
    
    def test_special_characters_in_filename(self, s3_setup):
        """✅ TEST: Handle special characters in filenames"""
        client = S3Client()
        
        # Filenames with spaces, special chars
        key = client.store_attachment(
            'project-abc/Drawing #1 - Floor Plan (Rev A).pdf',
            b'drawing data',
            'application/pdf'
        )
        
        # Should be able to retrieve
        data = client.get_attachment(key)
        assert data == b'drawing data'
        print("   ✓ Special characters in filename handled")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

