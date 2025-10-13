"""
Script to test the email processing flow locally.
Simulates an email being received and processed through the system.
"""
import boto3
import json
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.config import Config
from shared.logger import setup_logger

logger = setup_logger(__name__)


def create_test_email():
    """Create a test email message."""
    msg = MIMEMultipart()
    msg['From'] = 'test.contractor@example.com'
    msg['To'] = f'project@{Config.PROJECT_DOMAIN}'
    msg['Subject'] = 'Test Project - Electrical Bid Request'
    msg['Message-ID'] = f'<test-{int(time.time())}@example.com>'
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    
    body = """Hi,

I'm sending this as a test for the Main Street Renovation project.

We need to get the electrical rough-in completed by March 15th. The general contractor,
John Smith, has approved the budget increase to $45,000.

Key decisions made:
- Use LED fixtures throughout
- Install additional outlets in conference room
- Upgrade panel to 200A service

Please let me know if you need any additional information.

Thanks,
Test Contractor
"""
    
    msg.attach(MIMEText(body, 'plain'))
    return msg.as_string()


def upload_email_to_s3(email_content):
    """Upload test email to S3."""
    s3 = boto3.client('s3', **Config.get_boto3_config())
    
    key = f'test-emails/test-{int(time.time())}.eml'
    
    try:
        s3.put_object(
            Bucket=Config.EMAIL_BUCKET,
            Key=key,
            Body=email_content.encode('utf-8')
        )
        logger.info(f"Uploaded test email to S3: {key}")
        return key
    except Exception as e:
        logger.error(f"Failed to upload email to S3: {str(e)}")
        raise


def publish_ses_notification(s3_key):
    """Publish SES notification to SNS topic."""
    sns = boto3.client('sns', **Config.get_boto3_config())
    
    # Create SES notification format
    ses_notification = {
        'receipt': {
            'timestamp': datetime.now().isoformat(),
            'processingTimeMillis': 100,
            'recipients': [f'project@{Config.PROJECT_DOMAIN}'],
            'spamVerdict': {'status': 'PASS'},
            'virusVerdict': {'status': 'PASS'},
            'spfVerdict': {'status': 'PASS'},
            'dkimVerdict': {'status': 'PASS'},
            'action': {
                'type': 'S3',
                'bucketName': Config.EMAIL_BUCKET,
                'objectKey': s3_key
            }
        },
        'mail': {
            'timestamp': datetime.now().isoformat(),
            'source': 'test.contractor@example.com',
            'messageId': f'test-{int(time.time())}',
            'destination': [f'project@{Config.PROJECT_DOMAIN}'],
            'commonHeaders': {
                'from': ['test.contractor@example.com'],
                'to': [f'project@{Config.PROJECT_DOMAIN}'],
                'subject': 'Test Project - Electrical Bid Request'
            }
        }
    }
    
    try:
        # Get topic ARN (assumes it exists)
        topics = sns.list_topics()
        email_topic = None
        for topic in topics['Topics']:
            if 'email-received' in topic['TopicArn']:
                email_topic = topic['TopicArn']
                break
        
        if not email_topic:
            logger.error("Email topic not found. Run setup_local_resources.py first.")
            return
        
        # Publish to SNS
        response = sns.publish(
            TopicArn=email_topic,
            Message=json.dumps(ses_notification),
            Subject='Amazon SES Email Receipt Notification'
        )
        
        logger.info(f"Published SES notification to SNS: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Failed to publish SNS notification: {str(e)}")
        raise


def check_processing_results():
    """Check if email was processed by querying DynamoDB."""
    dynamodb = boto3.resource('dynamodb', **Config.get_boto3_config())
    
    # Check events table
    events_table = dynamodb.Table(Config.EVENTS_TABLE)
    
    try:
        # Wait a bit for processing
        logger.info("Waiting for email processing...")
        time.sleep(5)
        
        # Scan for recent events (not efficient, but OK for testing)
        response = events_table.scan(Limit=10)
        
        if response['Items']:
            logger.info(f"Found {len(response['Items'])} event(s) in database:")
            for item in response['Items']:
                logger.info(f"  - Project: {item.get('project_id')}, Type: {item.get('event_type')}")
                if item.get('ai_extracted_data'):
                    logger.info(f"    AI Data: {json.dumps(item['ai_extracted_data'], indent=2)}")
        else:
            logger.warning("No events found in database. Email may still be processing.")
            
    except Exception as e:
        logger.error(f"Failed to check processing results: {str(e)}")


def test_email_flow():
    """Test the complete email processing flow."""
    logger.info("Starting email flow test...")
    logger.info(f"Environment: {Config.ENVIRONMENT}")
    logger.info(f"Using LocalStack: {Config.USE_LOCALSTACK}")
    
    # Step 1: Create test email
    logger.info("Step 1: Creating test email...")
    email_content = create_test_email()
    
    # Step 2: Upload to S3
    logger.info("Step 2: Uploading email to S3...")
    s3_key = upload_email_to_s3(email_content)
    
    # Step 3: Publish SES notification
    logger.info("Step 3: Publishing SES notification...")
    publish_ses_notification(s3_key)
    
    # Step 4: Check results
    logger.info("Step 4: Checking processing results...")
    check_processing_results()
    
    logger.info("Email flow test complete!")


if __name__ == '__main__':
    test_email_flow()

