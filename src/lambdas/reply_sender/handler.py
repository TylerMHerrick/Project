"""
Reply Sender Lambda
Sends email responses via SES.
"""
import json
import sys
import os
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from shared.config import Config
from shared.s3_client import S3Client
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Initialize clients
ses_client = boto3.client('ses', **Config.get_boto3_config())
s3_client = S3Client()


def lambda_handler(event, context):
    """Send email reply via SES.
    
    Args:
        event: Event containing email details
        context: Lambda context
        
    Returns:
        Response status
    """
    try:
        to_address = event.get('to_address')
        subject = event.get('subject')
        body_text = event.get('body_text')
        body_html = event.get('body_html')
        attachments = event.get('attachments', [])
        reply_to_message_id = event.get('reply_to_message_id')
        
        if not to_address or not subject or not body_text:
            raise ValueError("Missing required fields: to_address, subject, or body_text")
        
        logger.info(f"Sending email to {to_address}")
        
        message_id = send_email(
            to_address=to_address,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            reply_to_message_id=reply_to_message_id
        )
        
        logger.info(f"Email sent successfully: {message_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message_id': message_id,
                'status': 'sent'
            })
        }
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def send_email(to_address: str, subject: str, body_text: str,
               body_html: Optional[str] = None,
               attachments: Optional[List[Dict[str, str]]] = None,
               reply_to_message_id: Optional[str] = None) -> str:
    """Send email via SES.
    
    Args:
        to_address: Recipient email address
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body (optional)
        attachments: List of attachment dicts with 's3_key' and 'filename'
        reply_to_message_id: Message ID to reply to
        
    Returns:
        SES Message ID
    """
    # Create message
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = Config.EMAIL_FROM_ADDRESS
    msg['To'] = to_address
    
    # Add reply-to headers
    if reply_to_message_id:
        msg['In-Reply-To'] = reply_to_message_id
        msg['References'] = reply_to_message_id
    
    # Create body part
    body_part = MIMEMultipart('alternative')
    
    # Add plain text
    text_part = MIMEText(body_text, 'plain', 'utf-8')
    body_part.attach(text_part)
    
    # Add HTML if provided
    if body_html:
        html_part = MIMEText(body_html, 'html', 'utf-8')
        body_part.attach(html_part)
    
    msg.attach(body_part)
    
    # Add attachments if provided
    if attachments:
        for attachment in attachments:
            try:
                attach_part = create_attachment(
                    s3_key=attachment['s3_key'],
                    filename=attachment['filename']
                )
                msg.attach(attach_part)
            except Exception as e:
                logger.error(f"Failed to attach file {attachment['filename']}: {str(e)}")
    
    # Send email
    try:
        response = ses_client.send_raw_email(
            Source=Config.EMAIL_FROM_ADDRESS,
            Destinations=[to_address],
            RawMessage={'Data': msg.as_string()}
        )
        return response['MessageId']
    except Exception as e:
        logger.error(f"SES send_raw_email failed: {str(e)}")
        raise


def create_attachment(s3_key: str, filename: str) -> MIMEBase:
    """Create MIME attachment from S3 object.
    
    Args:
        s3_key: S3 object key
        filename: Attachment filename
        
    Returns:
        MIME attachment part
    """
    # Download from S3
    data = s3_client.get_attachment(s3_key)
    
    # Determine content type based on filename
    content_type = get_content_type(filename)
    maintype, subtype = content_type.split('/', 1)
    
    # Create MIME part
    part = MIMEBase(maintype, subtype)
    part.set_payload(data)
    encoders.encode_base64(part)
    
    # Add header
    part.add_header(
        'Content-Disposition',
        f'attachment; filename="{filename}"'
    )
    
    return part


def get_content_type(filename: str) -> str:
    """Get content type based on filename extension.
    
    Args:
        filename: Filename
        
    Returns:
        MIME content type
    """
    extension = filename.lower().split('.')[-1]
    
    content_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'txt': 'text/plain',
        'csv': 'text/csv',
    }
    
    return content_types.get(extension, 'application/octet-stream')


def format_acknowledgment_email(project_id: str, key_points: List[str]) -> Dict[str, str]:
    """Format acknowledgment email body.
    
    Args:
        project_id: Project ID
        key_points: List of key points extracted from email
        
    Returns:
        Dictionary with body_text and body_html
    """
    # Plain text version
    body_text = f"""Thank you for your email regarding project {project_id}.

I've received and processed your message. Here's what I extracted:

"""
    
    for i, point in enumerate(key_points, 1):
        body_text += f"{i}. {point}\n"
    
    body_text += """
If any of this information is incorrect, please reply to this email with corrections.

Best regards,
Your Project Tracking Assistant
"""
    
    # HTML version
    body_html = f"""<html>
<head></head>
<body>
    <p>Thank you for your email regarding project <strong>{project_id}</strong>.</p>
    
    <p>I've received and processed your message. Here's what I extracted:</p>
    
    <ol>
"""
    
    for point in key_points:
        body_html += f"        <li>{point}</li>\n"
    
    body_html += """    </ol>
    
    <p>If any of this information is incorrect, please reply to this email with corrections.</p>
    
    <p>Best regards,<br>
    <em>Your Project Tracking Assistant</em></p>
</body>
</html>"""
    
    return {
        'body_text': body_text,
        'body_html': body_html
    }


def format_estimate_email(estimate_data: Dict[str, Any]) -> Dict[str, str]:
    """Format estimate email body.
    
    Args:
        estimate_data: Estimate data from AI
        
    Returns:
        Dictionary with body_text and body_html
    """
    # Plain text version
    body_text = f"""Here is your preliminary estimate:

ESTIMATE #{estimate_data.get('estimate_id', 'N/A')}

"""
    
    for item in estimate_data.get('line_items', []):
        body_text += f"{item['description']}\n"
        body_text += f"  Quantity: {item['quantity']} {item['unit']}\n"
        body_text += f"  Unit Cost: ${item['unit_cost']:.2f}\n"
        body_text += f"  Total: ${item['total_cost']:.2f}\n\n"
    
    summary = estimate_data.get('summary', {})
    body_text += f"""
SUMMARY
-------
Subtotal: ${summary.get('subtotal', 0):.2f}
Contingency ({summary.get('contingency_percent', 10)}%): ${summary.get('contingency_amount', 0):.2f}
TOTAL: ${summary.get('total', 0):.2f}

IMPORTANT: This is a PRELIMINARY estimate only. Final pricing may vary based on site conditions,
material availability, and other factors.

Assumptions:
"""
    
    for assumption in estimate_data.get('assumptions', []):
        body_text += f"- {assumption}\n"
    
    body_text += """
Best regards,
Your Project Tracking Assistant
"""
    
    # HTML version (simplified for brevity)
    body_html = f"""<html>
<head>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .total {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h2>Preliminary Estimate</h2>
    <p><strong>Estimate #:</strong> {estimate_data.get('estimate_id', 'N/A')}</p>
    
    <table>
        <tr>
            <th>Description</th>
            <th>Quantity</th>
            <th>Unit</th>
            <th>Unit Cost</th>
            <th>Total</th>
        </tr>
"""
    
    for item in estimate_data.get('line_items', []):
        body_html += f"""        <tr>
            <td>{item['description']}</td>
            <td>{item['quantity']}</td>
            <td>{item['unit']}</td>
            <td>${item['unit_cost']:.2f}</td>
            <td>${item['total_cost']:.2f}</td>
        </tr>
"""
    
    summary = estimate_data.get('summary', {})
    body_html += f"""    </table>
    
    <h3>Summary</h3>
    <p>Subtotal: ${summary.get('subtotal', 0):.2f}<br>
    Contingency ({summary.get('contingency_percent', 10)}%): ${summary.get('contingency_amount', 0):.2f}<br>
    <span class="total">TOTAL: ${summary.get('total', 0):.2f}</span></p>
    
    <p><strong>IMPORTANT:</strong> This is a PRELIMINARY estimate only.</p>
    
    <p><em>Your Project Tracking Assistant</em></p>
</body>
</html>"""
    
    return {
        'body_text': body_text,
        'body_html': body_html
    }

