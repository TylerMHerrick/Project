"""
Script to set up local AWS resources in LocalStack for development.
Run this after starting LocalStack with docker-compose.
"""
import boto3
import json
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


def setup_local_resources():
    """Set up all local AWS resources."""
    if not Config.USE_LOCALSTACK:
        logger.error("This script is only for LocalStack setup. Set USE_LOCALSTACK=true in .env")
        return
    
    logger.info("Setting up LocalStack resources...")
    
    # Create S3 bucket
    setup_s3_bucket()
    
    # Create SNS topic
    topic_arn = setup_sns_topic()
    
    # Create SQS queues
    queue_url, dlq_url = setup_sqs_queues()
    
    # Subscribe SQS to SNS
    subscribe_queue_to_topic(topic_arn, queue_url)
    
    # Create DynamoDB tables
    setup_dynamodb_tables()
    
    # Create Secrets Manager secret
    setup_secrets()
    
    logger.info("LocalStack setup complete!")
    logger.info(f"SNS Topic ARN: {topic_arn}")
    logger.info(f"SQS Queue URL: {queue_url}")
    logger.info(f"DLQ URL: {dlq_url}")


def setup_s3_bucket():
    """Create S3 bucket for email storage."""
    s3 = boto3.client('s3', **Config.get_boto3_config())
    
    try:
        s3.create_bucket(Bucket=Config.EMAIL_BUCKET)
        logger.info(f"Created S3 bucket: {Config.EMAIL_BUCKET}")
        
        # Enable versioning
        s3.put_bucket_versioning(
            Bucket=Config.EMAIL_BUCKET,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
    except s3.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"S3 bucket already exists: {Config.EMAIL_BUCKET}")
    except Exception as e:
        logger.error(f"Failed to create S3 bucket: {str(e)}")
        raise


def setup_sns_topic():
    """Create SNS topic for email notifications."""
    sns = boto3.client('sns', **Config.get_boto3_config())
    
    try:
        response = sns.create_topic(Name='email-received')
        topic_arn = response['TopicArn']
        logger.info(f"Created SNS topic: {topic_arn}")
        return topic_arn
    except Exception as e:
        logger.error(f"Failed to create SNS topic: {str(e)}")
        raise


def setup_sqs_queues():
    """Create SQS queues."""
    sqs = boto3.client('sqs', **Config.get_boto3_config())
    
    try:
        # Create DLQ
        dlq_response = sqs.create_queue(
            QueueName='email-processing-dlq',
            Attributes={
                'MessageRetentionPeriod': '1209600'  # 14 days
            }
        )
        dlq_url = dlq_response['QueueUrl']
        
        # Get DLQ ARN
        dlq_attrs = sqs.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['QueueArn']
        )
        dlq_arn = dlq_attrs['Attributes']['QueueArn']
        
        logger.info(f"Created DLQ: {dlq_url}")
        
        # Create main queue with DLQ
        queue_response = sqs.create_queue(
            QueueName='email-processing-queue',
            Attributes={
                'VisibilityTimeout': '300',
                'MessageRetentionPeriod': '1209600',
                'RedrivePolicy': json.dumps({
                    'deadLetterTargetArn': dlq_arn,
                    'maxReceiveCount': 3
                })
            }
        )
        queue_url = queue_response['QueueUrl']
        logger.info(f"Created SQS queue: {queue_url}")
        
        return queue_url, dlq_url
        
    except Exception as e:
        logger.error(f"Failed to create SQS queues: {str(e)}")
        raise


def subscribe_queue_to_topic(topic_arn, queue_url):
    """Subscribe SQS queue to SNS topic."""
    sns = boto3.client('sns', **Config.get_boto3_config())
    sqs = boto3.client('sqs', **Config.get_boto3_config())
    
    try:
        # Get queue ARN
        queue_attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['QueueArn']
        )
        queue_arn = queue_attrs['Attributes']['QueueArn']
        
        # Subscribe
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='sqs',
            Endpoint=queue_arn
        )
        
        logger.info(f"Subscribed queue to topic: {response['SubscriptionArn']}")
        
        # Set queue policy to allow SNS to send messages
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "sqs:SendMessage",
                "Resource": queue_arn,
                "Condition": {
                    "ArnEquals": {
                        "aws:SourceArn": topic_arn
                    }
                }
            }]
        }
        
        sqs.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={'Policy': json.dumps(policy)}
        )
        
    except Exception as e:
        logger.error(f"Failed to subscribe queue to topic: {str(e)}")
        raise


def setup_dynamodb_tables():
    """Create DynamoDB tables."""
    # Import and run the create_tables script
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../infrastructure'))
    from create_tables import create_tables
    
    create_tables()


def setup_secrets():
    """Create Secrets Manager secrets."""
    secrets = boto3.client('secretsmanager', **Config.get_boto3_config())
    
    try:
        # Create OpenAI API key secret (with placeholder)
        api_key = Config.OPENAI_API_KEY or 'sk-your-key-here'
        
        try:
            secrets.create_secret(
                Name=Config.OPENAI_API_KEY_SECRET,
                SecretString=json.dumps({'api_key': api_key})
            )
            logger.info(f"Created secret: {Config.OPENAI_API_KEY_SECRET}")
        except secrets.exceptions.ResourceExistsException:
            logger.info(f"Secret already exists: {Config.OPENAI_API_KEY_SECRET}")
            
    except Exception as e:
        logger.error(f"Failed to create secrets: {str(e)}")
        raise


if __name__ == '__main__':
    setup_local_resources()

