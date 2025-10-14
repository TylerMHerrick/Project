"""
Test email processing by directly invoking the Lambda handler.
This simulates the complete flow including the Lambda processing.
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

Action items:
- Order materials by Friday (Sarah)
- Schedule inspection by Oct 20 (Mike)

Please let me know if you need any additional information.

Thanks,
Test Contractor
ABC Electrical Co.
"""
    
    msg.attach(MIMEText(body, 'plain'))
    return msg.as_string()


def test_complete_flow():
    """Test the complete email processing flow."""
    print("\n" + "=" * 60)
    print("  EMAIL PROCESSING TEST")
    print("=" * 60)
    print(f"Environment: {Config.ENVIRONMENT}")
    print(f"Using LocalStack: {Config.USE_LOCALSTACK}")
    print("")
    
    s3 = boto3.client('s3', **Config.get_boto3_config())
    sns = boto3.client('sns', **Config.get_boto3_config())
    dynamodb = boto3.resource('dynamodb', **Config.get_boto3_config())
    
    # Step 1: Create test email
    print("Step 1: Creating test email...")
    email_content = create_test_email()
    print("  ✓ Test email created")
    
    # Step 2: Upload to S3
    print("\nStep 2: Uploading email to S3...")
    s3_key = f'test-emails/test-{int(time.time())}.eml'
    
    try:
        s3.put_object(
            Bucket=Config.EMAIL_BUCKET,
            Key=s3_key,
            Body=email_content.encode('utf-8')
        )
        print(f"  ✓ Uploaded to S3: {s3_key}")
    except Exception as e:
        print(f"  ✗ Failed to upload to S3: {str(e)}")
        return False
    
    # Step 3: Create SES notification (what SNS would publish)
    print("\nStep 3: Creating SES notification...")
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
    
    print("  ✓ SES notification created")
    
    # Step 4: Create SQS event (what Lambda would receive)
    print("\nStep 4: Creating Lambda event...")
    lambda_event = {
        'Records': [
            {
                'messageId': '12345',
                'receiptHandle': 'test-receipt',
                'body': json.dumps({
                    'Type': 'Notification',
                    'MessageId': '67890',
                    'TopicArn': Config.EMAIL_TOPIC_ARN,
                    'Message': json.dumps(ses_notification),
                    'Timestamp': datetime.now().isoformat(),
                    'SignatureVersion': '1',
                }),
                'attributes': {},
                'messageAttributes': {},
                'md5OfBody': '',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-east-1:000000000000:email-processing-queue',
                'awsRegion': 'us-east-1'
            }
        ]
    }
    
    print("  ✓ Lambda event created")
    
    # Step 5: Invoke the Lambda handler directly
    print("\nStep 5: Processing email with Lambda handler...")
    print("  (This calls OpenAI API - may take 5-10 seconds)")
    
    try:
        # Import the Lambda handler
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src/lambdas/email_processor'))
        from handler import lambda_handler
        
        # Invoke the handler
        result = lambda_handler(lambda_event, None)
        
        if result.get('statusCode') == 200:
            print("  ✓ Email processed successfully!")
            body = json.loads(result.get('body', '{}'))
            print(f"  ✓ Processed: {body.get('processed', 0)} email(s)")
        else:
            print(f"  ⚠ Processing returned status: {result.get('statusCode')}")
            print(f"  Response: {result.get('body', 'No details')}")
            
    except Exception as e:
        print(f"  ✗ Failed to process email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Check results in DynamoDB
    print("\nStep 6: Checking DynamoDB for results...")
    time.sleep(1)
    
    try:
        events_table = dynamodb.Table(Config.EVENTS_TABLE)
        response = events_table.scan(Limit=10)
        
        if response['Items']:
            print(f"  ✓ Found {len(response['Items'])} event(s) in database\n")
            print("-" * 60)
            
            for i, item in enumerate(response['Items'], 1):
                print(f"\nEvent #{i}:")
                print(f"  Project ID:  {item.get('project_id')}")
                print(f"  Event Type:  {item.get('event_type')}")
                print(f"  From:        {item.get('sender')}")
                print(f"  Subject:     {item.get('subject')}")
                
                if item.get('ai_extracted_data'):
                    ai_data = item['ai_extracted_data']
                    print(f"\n  AI Extraction Results:")
                    print(f"    Project Name:  {ai_data.get('project_name', 'Not extracted')}")
                    print(f"    Address:       {ai_data.get('project_address', 'Not extracted')}")
                    
                    decisions = ai_data.get('decisions', [])
                    print(f"\n    Decisions ({len(decisions)}):")
                    if decisions:
                        for d in decisions[:3]:  # Show first 3
                            print(f"      • {d.get('decision', 'Unknown')}")
                            if d.get('made_by'):
                                print(f"        By: {d['made_by']}")
                    else:
                        print("      (none found)")
                    
                    action_items = ai_data.get('action_items', [])
                    print(f"\n    Action Items ({len(action_items)}):")
                    if action_items:
                        for a in action_items[:3]:  # Show first 3
                            print(f"      • {a.get('task', 'Unknown')}")
                            if a.get('owner'):
                                print(f"        Owner: {a['owner']}")
                            if a.get('deadline'):
                                print(f"        Due: {a['deadline']}")
                    else:
                        print("      (none found)")
                    
                    key_points = ai_data.get('key_points', [])
                    if key_points:
                        print(f"\n    Key Points:")
                        for kp in key_points[:3]:  # Show first 3
                            print(f"      • {kp}")
            
            print("\n" + "-" * 60)
            print("\n✓✓✓ EMAIL PROCESSING TEST PASSED ✓✓✓")
            return True
        else:
            print("  ⚠ No events found in database")
            print("\n  Possible issues:")
            print("    - OpenAI API key not set in .env")
            print("    - Lambda handler encountered an error")
            print("    - DynamoDB not properly initialized")
            return False
            
    except Exception as e:
        print(f"  ✗ Failed to check DynamoDB: {str(e)}")
        return False


if __name__ == '__main__':
    success = test_complete_flow()
    
    if not success:
        print("\n" + "=" * 60)
        print("✗✗✗ TEST FAILED ✗✗✗")
        print("=" * 60)
        print("\nCheck the error messages above for details.")
    
    print("")  # Extra newline at end
    sys.exit(0 if success else 1)

