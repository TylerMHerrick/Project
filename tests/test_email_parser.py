"""
Unit tests for email parser.
"""
import pytest
from email import policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.email_parser import EmailParser


class TestEmailParser:
    """Test cases for EmailParser."""
    
    def test_extract_email_address(self):
        """Test email address extraction from From field."""
        # Test with name and email
        assert EmailParser.extract_email_address('John Doe <john@example.com>') == 'john@example.com'
        
        # Test with just email
        assert EmailParser.extract_email_address('john@example.com') == 'john@example.com'
        
        # Test with extra whitespace
        assert EmailParser.extract_email_address('  john@example.com  ') == 'john@example.com'
    
    def test_extract_project_id_from_recipient(self):
        """Test project ID extraction from recipient."""
        # Test with project ID
        assert EmailParser.extract_project_id_from_recipient('project+PROJ123@example.com') == 'PROJ123'
        
        # Test without project ID
        assert EmailParser.extract_project_id_from_recipient('project@example.com') is None
        
        # Test with UUID format
        assert EmailParser.extract_project_id_from_recipient(
            'project+PROJ-abc123-def456@example.com'
        ) == 'PROJ-abc123-def456'
    
    def test_parse_simple_email(self):
        """Test parsing simple text email."""
        # Create test email
        msg = MIMEText('This is a test email body.')
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@example.com'
        msg['Subject'] = 'Test Subject'
        
        # Parse
        raw_email = msg.as_bytes()
        parsed = EmailParser.parse_raw_email(raw_email)
        
        # Verify
        assert parsed['From'] == 'sender@example.com'
        assert parsed['Subject'] == 'Test Subject'
        
        body = EmailParser.extract_body(parsed)
        assert 'test email body' in body
    
    def test_extract_attachments(self):
        """Test attachment extraction."""
        # Create email with attachment
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@example.com'
        msg['Subject'] = 'Email with attachment'
        
        # Add text part
        msg.attach(MIMEText('Email body'))
        
        # Add attachment
        attachment = MIMEText('Attachment content')
        attachment.add_header('Content-Disposition', 'attachment', filename='test.txt')
        msg.attach(attachment)
        
        # Parse
        raw_email = msg.as_bytes()
        parsed = EmailParser.parse_raw_email(raw_email)
        attachments = EmailParser.extract_attachments(parsed)
        
        # Verify
        assert len(attachments) == 1
        assert attachments[0]['filename'] == 'test.txt'
        assert b'Attachment content' in attachments[0]['data']
    
    def test_validate_sender(self):
        """Test sender validation."""
        # Test allowed domain
        assert EmailParser.validate_sender('user@example.com', ['example.com']) is True
        
        # Test subdomain
        assert EmailParser.validate_sender('user@sub.example.com', ['example.com']) is True
        
        # Test not allowed
        assert EmailParser.validate_sender('user@other.com', ['example.com']) is False
        
        # Test empty allowlist (all allowed)
        assert EmailParser.validate_sender('user@any.com', []) is True
    
    def test_is_auto_reply(self):
        """Test auto-reply detection."""
        # Test out of office subject
        msg = MIMEText('Body')
        msg['Subject'] = 'Out of Office: Re: Project'
        assert EmailParser.is_auto_reply(msg) is True
        
        # Test auto-reply header
        msg2 = MIMEText('Body')
        msg2['Subject'] = 'Normal subject'
        msg2['Auto-Submitted'] = 'auto-replied'
        assert EmailParser.is_auto_reply(msg2) is True
        
        # Test normal email
        msg3 = MIMEText('Body')
        msg3['Subject'] = 'Normal subject'
        assert EmailParser.is_auto_reply(msg3) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

