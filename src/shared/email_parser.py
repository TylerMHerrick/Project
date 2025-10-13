"""Email parsing utilities."""
import email
from email import policy
from email.message import EmailMessage
from typing import Dict, List, Any, Optional, Tuple
import re
from .logger import setup_logger

logger = setup_logger(__name__)


class EmailParser:
    """Parse and extract information from emails."""
    
    @staticmethod
    def parse_raw_email(raw_email: bytes) -> EmailMessage:
        """Parse raw email bytes into EmailMessage object.
        
        Args:
            raw_email: Raw email in bytes
            
        Returns:
            Parsed EmailMessage object
        """
        return email.message_from_bytes(raw_email, policy=policy.default)
    
    @staticmethod
    def extract_metadata(msg: EmailMessage) -> Dict[str, Any]:
        """Extract metadata from email message.
        
        Args:
            msg: Parsed email message
            
        Returns:
            Dictionary containing email metadata
        """
        metadata = {
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'cc': msg.get('Cc', ''),
            'subject': msg.get('Subject', ''),
            'date': msg.get('Date', ''),
            'message_id': msg.get('Message-ID', ''),
            'in_reply_to': msg.get('In-Reply-To', ''),
            'references': msg.get('References', ''),
        }
        
        # Extract email address from 'From' field
        metadata['sender_email'] = EmailParser.extract_email_address(metadata['from'])
        
        # Extract project ID from recipient if using project+<id>@domain.com format
        metadata['project_id_hint'] = EmailParser.extract_project_id_from_recipient(metadata['to'])
        
        return metadata
    
    @staticmethod
    def extract_email_address(from_field: str) -> str:
        """Extract email address from From field.
        
        Args:
            from_field: Email 'From' header value
            
        Returns:
            Email address
        """
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1).strip()
        return from_field.strip()
    
    @staticmethod
    def extract_project_id_from_recipient(to_field: str) -> Optional[str]:
        """Extract project ID from recipient address (e.g., project+PROJ123@domain.com).
        
        Args:
            to_field: Email 'To' header value
            
        Returns:
            Project ID if found, None otherwise
        """
        match = re.search(r'project\+([^@]+)@', to_field)
        if match:
            return match.group(1).strip()
        return None
    
    @staticmethod
    def extract_body(msg: EmailMessage) -> str:
        """Extract text body from email message.
        
        Args:
            msg: Parsed email message
            
        Returns:
            Email body text
        """
        body = ""
        
        if msg.is_multipart():
            # Get plain text parts
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    try:
                        body += part.get_content()
                    except Exception as e:
                        logger.warning(f"Failed to extract text part: {str(e)}")
                elif content_type == 'text/html' and not body:
                    # Fallback to HTML if no plain text
                    try:
                        html_content = part.get_content()
                        body = EmailParser._html_to_text(html_content)
                    except Exception as e:
                        logger.warning(f"Failed to extract HTML part: {str(e)}")
        else:
            # Single part email
            try:
                body = msg.get_content()
            except Exception as e:
                logger.warning(f"Failed to extract body: {str(e)}")
                body = str(msg.get_payload())
        
        return body.strip()
    
    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to plain text (basic implementation).
        
        Args:
            html: HTML content
            
        Returns:
            Plain text
        """
        # Remove HTML tags (basic regex, consider using library like BeautifulSoup for production)
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def extract_attachments(msg: EmailMessage) -> List[Dict[str, Any]]:
        """Extract attachments from email message.
        
        Args:
            msg: Parsed email message
            
        Returns:
            List of attachment dictionaries
        """
        attachments = []
        
        for part in msg.walk():
            content_disposition = str(part.get('Content-Disposition', ''))
            
            if 'attachment' in content_disposition:
                filename = part.get_filename()
                if filename:
                    try:
                        attachments.append({
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True)),
                            'data': part.get_payload(decode=True)
                        })
                        logger.info(f"Extracted attachment: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to extract attachment {filename}: {str(e)}")
        
        return attachments
    
    @staticmethod
    def validate_sender(sender_email: str, allowed_domains: List[str]) -> bool:
        """Validate sender against allowed domains.
        
        Args:
            sender_email: Sender email address
            allowed_domains: List of allowed domain patterns
            
        Returns:
            True if sender is allowed, False otherwise
        """
        if not allowed_domains:
            return True  # No restrictions
        
        domain = sender_email.split('@')[-1].lower()
        
        for allowed_domain in allowed_domains:
            allowed_domain = allowed_domain.strip().lower()
            if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                return True
        
        return False
    
    @staticmethod
    def is_auto_reply(msg: EmailMessage) -> bool:
        """Check if email is an auto-reply (out of office, etc.).
        
        Args:
            msg: Parsed email message
            
        Returns:
            True if auto-reply, False otherwise
        """
        # Check common auto-reply headers
        auto_reply_headers = [
            'X-Autorespond',
            'X-Autoreply',
            'Auto-Submitted',
            'X-Auto-Response-Suppress',
        ]
        
        for header in auto_reply_headers:
            if msg.get(header):
                return True
        
        # Check subject for common auto-reply patterns
        subject = msg.get('Subject', '').lower()
        auto_reply_patterns = [
            'out of office',
            'automatic reply',
            'auto reply',
            'away from',
            'vacation',
        ]
        
        for pattern in auto_reply_patterns:
            if pattern in subject:
                return True
        
        return False

