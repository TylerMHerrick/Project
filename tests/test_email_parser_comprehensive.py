"""
Comprehensive tests for Email Parser operations.
Tests: MIME parsing, header extraction, body parsing, attachment handling, special cases
"""
import pytest
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.email_parser import EmailParser


class TestEmailParserBasic:
    """Test cases for basic email parsing."""
    
    def test_parse_simple_text_email(self):
        """✅ TEST: Parse simple plain text email"""
        # Create simple email
        msg = MIMEText("This is a test email body.")
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Test Subject'
        msg['Message-ID'] = '<test123@example.com>'
        
        raw_email = msg.as_bytes()
        
        # Parse
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        attachments = EmailParser.extract_attachments(parsed_msg)
        
        assert metadata['from'] == 'sender@example.com'
        assert metadata['to'] == 'project@domain.com'
        assert metadata['subject'] == 'Test Subject'
        assert metadata['message_id'] == '<test123@example.com>'
        assert 'This is a test email body' in body
        assert len(attachments) == 0
        print("   ✓ Simple text email parsed")
    
    def test_parse_html_email(self):
        """✅ TEST: Parse HTML email"""
        msg = MIMEMultipart('alternative')
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'HTML Email'
        
        text_part = MIMEText("Plain text version", 'plain')
        html_part = MIMEText("<html><body><p>HTML version with <b>formatting</b></p></body></html>", 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        
        assert metadata['subject'] == 'HTML Email'
        assert 'Plain text version' in body or 'HTML version' in body
        print("   ✓ HTML email parsed")
    
    def test_parse_email_with_cc_bcc(self):
        """✅ TEST: Parse email with CC headers"""
        msg = MIMEText("Test body")
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Cc'] = 'manager@example.com, supervisor@example.com'
        msg['Subject'] = 'Test CC'
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        
        assert metadata['cc'] is not None
        assert 'manager@example.com' in metadata['cc']
        print("   ✓ CC headers parsed")
    
    def test_extract_sender_email(self):
        """✅ TEST: Extract email address from From field"""
        test_cases = [
            ('John Doe <john@example.com>', 'john@example.com'),
            ('john@example.com', 'john@example.com'),
            ('"John Doe" <john@example.com>', 'john@example.com'),
        ]
        
        for from_field, expected in test_cases:
            result = EmailParser.extract_email_address(from_field)
            assert result == expected, f"Failed for {from_field}"
        
        print("   ✓ Email address extraction works")


class TestEmailParserAttachments:
    """Test cases for attachment handling."""
    
    def test_parse_email_with_pdf_attachment(self):
        """✅ TEST: Parse email with PDF attachment"""
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Plans Attached'
        
        # Add body
        body = MIMEText("Please review the attached plans.")
        msg.attach(body)
        
        # Add PDF attachment
        attachment = MIMEBase('application', 'pdf')
        pdf_content = b"%PDF-1.4 fake pdf content for testing"
        attachment.set_payload(pdf_content)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename='floor-plan.pdf')
        msg.attach(attachment)
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        attachments = EmailParser.extract_attachments(parsed_msg)
        
        assert len(attachments) == 1
        assert attachments[0]['filename'] == 'floor-plan.pdf'
        assert attachments[0]['content_type'] == 'application/pdf'
        assert len(attachments[0]['data']) > 0
        print("   ✓ PDF attachment parsed")
    
    def test_parse_email_with_image_attachment(self):
        """✅ TEST: Parse email with image attachment"""
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Site Photos'
        
        body = MIMEText("Here are the site photos.")
        msg.attach(body)
        
        # Add image
        attachment = MIMEBase('image', 'jpeg')
        image_content = b"\xff\xd8\xff\xe0 fake jpeg data"
        attachment.set_payload(image_content)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename='site-photo.jpg')
        msg.attach(attachment)
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        attachments = EmailParser.extract_attachments(parsed_msg)
        
        assert len(attachments) == 1
        assert attachments[0]['filename'] == 'site-photo.jpg'
        assert attachments[0]['content_type'] == 'image/jpeg'
        print("   ✓ Image attachment parsed")
    
    def test_parse_email_with_multiple_attachments(self):
        """✅ TEST: Parse email with multiple attachments"""
        msg = MIMEMultipart()
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Project Documents'
        
        body = MIMEText("All project documents attached.")
        msg.attach(body)
        
        # Add multiple attachments
        attachments_data = [
            ('drawing1.pdf', b'PDF content 1', 'application/pdf'),
            ('drawing2.pdf', b'PDF content 2', 'application/pdf'),
            ('photo.jpg', b'JPEG content', 'image/jpeg'),
        ]
        
        for filename, content, content_type in attachments_data:
            maintype, subtype = content_type.split('/')
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(content)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(attachment)
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        attachments = EmailParser.extract_attachments(parsed_msg)
        
        assert len(attachments) == 3
        filenames = [att['filename'] for att in attachments]
        assert 'drawing1.pdf' in filenames
        assert 'drawing2.pdf' in filenames
        assert 'photo.jpg' in filenames
        print(f"   ✓ {len(attachments)} attachments parsed")


class TestEmailParserEdgeCases:
    """Test cases for edge cases and special scenarios."""
    
    def test_parse_email_no_subject(self):
        """✅ TEST: Parse email without subject"""
        msg = MIMEText("Email body without subject")
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        
        assert metadata['subject'] == '' or metadata['subject'] is None
        assert body is not None
        print("   ✓ Email without subject handled")
    
    def test_parse_email_empty_body(self):
        """✅ TEST: Parse email with empty body"""
        msg = MIMEText("")
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Empty Body'
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        
        assert metadata['subject'] == 'Empty Body'
        assert body == '' or body is None
        print("   ✓ Empty body handled")
    
    def test_parse_email_very_long_body(self):
        """✅ TEST: Parse email with very long body"""
        long_body = "This is a test. " * 1000  # ~15KB
        msg = MIMEText(long_body)
        msg['From'] = 'sender@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Long Email'
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        
        assert len(body) > 10000
        assert metadata['subject'] == 'Long Email'
        print("   ✓ Long email body handled")
    
    def test_parse_forwarded_email(self):
        """✅ TEST: Parse forwarded email"""
        msg = MIMEText("""
---------- Forwarded message ---------
From: Original Sender <original@example.com>
Date: Mon, Oct 14, 2024 at 10:00 AM
Subject: Original Subject
To: someone@example.com

This is the original message content.
        """)
        msg['From'] = 'forwarder@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Fwd: Original Subject'
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        
        assert 'Fwd:' in metadata['subject']
        assert 'Forwarded message' in body
        print("   ✓ Forwarded email handled")
    
    def test_parse_reply_email(self):
        """✅ TEST: Parse reply email with quoted text"""
        msg = MIMEText("""
This is my reply.

On Mon, Oct 14, 2024 at 10:00 AM, Original Sender <original@example.com> wrote:
> This is the quoted original message.
> It has multiple lines.
        """)
        msg['From'] = 'replier@example.com'
        msg['To'] = 'project@domain.com'
        msg['Subject'] = 'Re: Original Subject'
        msg['In-Reply-To'] = '<original-message-id@example.com>'
        
        raw_email = msg.as_bytes()
        
        parsed_msg = EmailParser.parse_raw_email(raw_email)
        metadata = EmailParser.extract_metadata(parsed_msg)
        body = EmailParser.extract_body(parsed_msg)
        
        assert 'Re:' in metadata['subject']
        assert 'This is my reply' in body
        print("   ✓ Reply email with quoted text handled")


class TestEmailParserUtilities:
    """Test cases for utility functions."""
    
    def test_extract_project_id_from_recipient(self):
        """✅ TEST: Extract project ID from email address"""
        test_cases = [
            ('project+PROJ-123@domain.com', 'PROJ-123'),
            ('project+abc-456@domain.com', 'abc-456'),
            ('project@domain.com', None),  # No project ID
        ]
        
        for email, expected in test_cases:
            result = EmailParser.extract_project_id_from_recipient(email)
            assert result == expected, f"Failed for {email}"
        
        print("   ✓ Project ID extraction works")
    
    def test_is_auto_reply_detection(self):
        """✅ TEST: Detect auto-reply/out-of-office emails"""
        auto_reply_subjects = [
            'Out of Office',
            'Automatic reply',
            'Auto-reply: On vacation',
        ]
        
        for subject in auto_reply_subjects:
            msg = MIMEText("I'm out of office")
            msg['From'] = 'sender@example.com'
            msg['To'] = 'project@domain.com'
            msg['Subject'] = subject
            msg['Auto-Submitted'] = 'auto-replied'
            
            raw_email = msg.as_bytes()
            parsed_msg = EmailParser.parse_raw_email(raw_email)
            
            is_auto = EmailParser.is_auto_reply(parsed_msg)
            assert is_auto, f"Should detect auto-reply: {subject}"
        
        print("   ✓ Auto-reply detection works")
    
    def test_validate_sender_allowed(self):
        """✅ TEST: Validate sender against allowed domains"""
        allowed_domains = ['example.com', 'contractor.com']
        
        # Should pass
        assert EmailParser.validate_sender('user@example.com', allowed_domains) is True
        assert EmailParser.validate_sender('admin@contractor.com', allowed_domains) is True
        assert EmailParser.validate_sender('john@sub.example.com', allowed_domains) is True
        
        print("   ✓ Sender validation - allowed domains work")
    
    def test_validate_sender_blocked(self):
        """✅ TEST: Block sender not in allowed domains"""
        allowed_domains = ['example.com']
        
        # Should fail
        assert EmailParser.validate_sender('spam@notallowed.com', allowed_domains) is False
        assert EmailParser.validate_sender('bad@malicious.org', allowed_domains) is False
        
        print("   ✓ Sender validation - blocking works")
    
    def test_validate_sender_no_restrictions(self):
        """✅ TEST: No restrictions when allowed_domains is empty"""
        allowed_domains = []
        
        # Should allow all
        assert EmailParser.validate_sender('anyone@anywhere.com', allowed_domains) is True
        
        print("   ✓ Sender validation - no restrictions works")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
