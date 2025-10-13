"""
Email Processor Lambda
Receives SQS messages containing SES notifications, downloads and processes emails.
"""
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from shared.s3_client import S3Client
from shared.db_client import DynamoDBClient
from shared.ai_client import AIClient
from shared.email_parser import EmailParser
from shared.config import Config
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Initialize clients (reuse across Lambda invocations)
s3_client = S3Client()
db_client = DynamoDBClient()
ai_client = AIClient()
email_parser = EmailParser()


def lambda_handler(event, context):
    """Process incoming emails from SQS queue.
    
    Args:
        event: SQS event containing SES notification
        context: Lambda context
        
    Returns:
        Response with processing status
    """
    logger.info(f"Processing {len(event.get('Records', []))} email(s)")
    
    processed = 0
    failed = 0
    
    for record in event.get('Records', []):
        try:
            process_email_record(record)
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process record: {str(e)}", exc_info=True)
            failed += 1
            # Don't raise - let other messages process
    
    result = {
        'statusCode': 200 if failed == 0 else 207,  # 207 = Multi-Status (partial success)
        'body': json.dumps({
            'processed': processed,
            'failed': failed
        })
    }
    
    logger.info(f"Processing complete: {processed} succeeded, {failed} failed")
    return result


def process_email_record(record):
    """Process a single SQS record containing SES notification.
    
    Args:
        record: SQS record
    """
    # Parse SQS message
    message_body = json.loads(record['body'])
    
    # Parse SNS message (SES publishes to SNS, which triggers SQS)
    sns_message = json.loads(message_body['Message'])
    
    # Get SES receipt information
    receipt = sns_message.get('receipt', {})
    action = receipt.get('action', {})
    
    # Get S3 location
    bucket = action.get('bucketName')
    object_key = action.get('objectKey')
    
    if not bucket or not object_key:
        logger.error("Missing S3 bucket or object key in SES notification")
        return
    
    logger.info(f"Processing email from S3: s3://{bucket}/{object_key}")
    
    # Download email from S3
    raw_email = s3_client.get_email(object_key)
    
    # Parse email
    msg = email_parser.parse_raw_email(raw_email)
    metadata = email_parser.extract_metadata(msg)
    body = email_parser.extract_body(msg)
    attachments = email_parser.extract_attachments(msg)
    
    # Skip auto-replies
    if email_parser.is_auto_reply(msg):
        logger.info("Skipping auto-reply email")
        return
    
    # Validate sender if allowlist is enabled
    if Config.ENABLE_EMAIL_ALLOWLIST:
        allowed_domains = [d.strip() for d in Config.ALLOWED_SENDER_DOMAINS.split(',') if d.strip()]
        if not email_parser.validate_sender(metadata['sender_email'], allowed_domains):
            logger.warning(f"Rejected email from unauthorized sender: {metadata['sender_email']}")
            return
    
    # Store attachments in S3
    attachment_keys = []
    for attachment in attachments:
        # Check size limit
        max_size = Config.MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
        if attachment['size'] > max_size:
            logger.warning(f"Attachment {attachment['filename']} exceeds size limit: {attachment['size']} bytes")
            continue
        
        try:
            key = f"{metadata['message_id']}/{attachment['filename']}"
            stored_key = s3_client.store_attachment(key, attachment['data'], attachment['content_type'])
            attachment_keys.append({
                'filename': attachment['filename'],
                's3_key': stored_key,
                'content_type': attachment['content_type'],
                'size': attachment['size']
            })
        except Exception as e:
            logger.error(f"Failed to store attachment {attachment['filename']}: {str(e)}")
    
    # Prepare attachment summary for AI
    attachments_summary = None
    if attachment_keys:
        attachments_summary = ", ".join([
            f"{a['filename']} ({a['content_type']})" for a in attachment_keys
        ])
    
    # Extract project information using AI
    logger.info("Extracting project data with AI")
    sanitized_body = ai_client.sanitize_input(body)
    extracted_data = ai_client.extract_project_data(
        sender=metadata['sender_email'],
        subject=metadata['subject'],
        body=sanitized_body,
        attachments_summary=attachments_summary
    )
    
    # Determine or create project ID
    project_id = determine_project_id(metadata, extracted_data)
    
    # Store event in DynamoDB
    event_data = {
        'event_type': 'EMAIL_RECEIVED',
        'source_email_id': metadata['message_id'],
        'sender': metadata['sender_email'],
        'subject': metadata['subject'],
        'raw_s3_key': object_key,
        'attachments': attachment_keys,
        'ai_extracted_data': extracted_data,
    }
    
    event_id = db_client.create_event(project_id, event_data)
    logger.info(f"Created event {event_id} for project {project_id}")
    
    # Update project metadata if needed
    update_project_metadata(project_id, metadata, extracted_data)
    
    # Determine response type and generate reply
    if extracted_data.get('requires_response', False):
        send_response(metadata, extracted_data, attachment_keys)
    else:
        # Send acknowledgment
        send_acknowledgment(metadata, extracted_data, project_id)


def determine_project_id(metadata, extracted_data):
    """Determine project ID from email or create new project.
    
    Args:
        metadata: Email metadata
        extracted_data: AI-extracted data
        
    Returns:
        Project ID
    """
    # Check if project ID hint in recipient (project+PROJ123@domain.com)
    if metadata.get('project_id_hint'):
        project_id = metadata['project_id_hint']
        logger.info(f"Using project ID from recipient: {project_id}")
        
        # Verify project exists
        project = db_client.get_project(project_id)
        if project:
            return project_id
        else:
            logger.warning(f"Project {project_id} not found, will create new project")
    
    # Check if AI extracted project ID
    if extracted_data.get('project_id'):
        project_id = extracted_data['project_id']
        project = db_client.get_project(project_id)
        if project:
            logger.info(f"Using AI-extracted project ID: {project_id}")
            return project_id
    
    # Try to find existing project for this client
    sender_email = metadata['sender_email']
    projects = db_client.get_projects_by_client(sender_email)
    
    # If only one active project, use it
    active_projects = [p for p in projects if p.get('status') == 'active']
    if len(active_projects) == 1:
        project_id = active_projects[0]['project_id']
        logger.info(f"Using existing active project: {project_id}")
        return project_id
    
    # Create new project
    project_data = {
        'client_email': sender_email,
        'client_name': metadata.get('from', sender_email),
        'project_name': extracted_data.get('project_name', 'Unnamed Project'),
        'project_address': extracted_data.get('project_address'),
        'status': 'active',
    }
    
    project_id = db_client.create_project(project_data)
    logger.info(f"Created new project: {project_id}")
    return project_id


def update_project_metadata(project_id, metadata, extracted_data):
    """Update project with new information from email.
    
    Args:
        project_id: Project ID
        metadata: Email metadata
        extracted_data: AI-extracted data
    """
    updates = {}
    
    # Update project name if extracted and not set
    if extracted_data.get('project_name'):
        project = db_client.get_project(project_id)
        if project and (not project.get('project_name') or project.get('project_name') == 'Unnamed Project'):
            updates['project_name'] = extracted_data['project_name']
    
    # Update address if extracted
    if extracted_data.get('project_address'):
        updates['project_address'] = extracted_data['project_address']
    
    # Add people mentioned
    if extracted_data.get('people_mentioned'):
        updates['people_mentioned'] = extracted_data['people_mentioned']
    
    if updates:
        db_client.update_project(project_id, updates)
        logger.info(f"Updated project {project_id} with new metadata")


def send_response(metadata, extracted_data, attachments):
    """Send AI-generated response to user.
    
    Args:
        metadata: Email metadata
        extracted_data: AI-extracted data
        attachments: Email attachments
    """
    # This will be handled by reply_sender Lambda (invoked asynchronously)
    # For now, just log
    logger.info(f"Response required for email from {metadata['sender_email']}")
    # TODO: Invoke reply_sender Lambda with response data


def send_acknowledgment(metadata, extracted_data, project_id):
    """Send acknowledgment email to user.
    
    Args:
        metadata: Email metadata
        extracted_data: AI-extracted data
        project_id: Project ID
    """
    logger.info(f"Sending acknowledgment to {metadata['sender_email']} for project {project_id}")
    # TODO: Invoke reply_sender Lambda with acknowledgment data

