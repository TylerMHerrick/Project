"""Configuration management for the application."""
import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""
    
    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'dev')
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    
    # LocalStack
    USE_LOCALSTACK: bool = os.getenv('USE_LOCALSTACK', 'false').lower() == 'true'
    AWS_ENDPOINT_URL: Optional[str] = os.getenv('AWS_ENDPOINT_URL')
    
    # Domain
    PROJECT_DOMAIN: str = os.getenv('PROJECT_DOMAIN', 'yourdomain.com')
    EMAIL_FROM_ADDRESS: str = os.getenv('EMAIL_FROM_ADDRESS', f'project@{PROJECT_DOMAIN}')
    
    # S3
    EMAIL_BUCKET: str = os.getenv('EMAIL_BUCKET', 'project-emails-dev')
    
    # DynamoDB
    PROJECTS_TABLE: str = os.getenv('PROJECTS_TABLE', 'ProjectTracking-Projects-dev')
    EVENTS_TABLE: str = os.getenv('EVENTS_TABLE', 'ProjectTracking-Events-dev')
    USERS_TABLE: str = os.getenv('USERS_TABLE', 'ProjectTracking-Users-dev')
    ORGANIZATIONS_TABLE: str = os.getenv('ORGANIZATIONS_TABLE', 'ProjectTracking-Organizations-dev')
    API_USAGE_TABLE: str = os.getenv('API_USAGE_TABLE', 'ProjectTracking-APIUsage-dev')
    
    # SQS
    EMAIL_QUEUE_URL: str = os.getenv('EMAIL_QUEUE_URL', '')
    EMAIL_DLQ_URL: str = os.getenv('EMAIL_DLQ_URL', '')
    
    # SNS
    EMAIL_TOPIC_ARN: str = os.getenv('EMAIL_TOPIC_ARN', '')
    
    # Secrets Manager
    OPENAI_API_KEY_SECRET: str = os.getenv('OPENAI_API_KEY_SECRET', 'openai-api-key')
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')  # Only for local dev
    OPENAI_MODEL_EXTRACTION: str = os.getenv('OPENAI_MODEL_EXTRACTION', 'gpt-4o-mini')
    OPENAI_MODEL_ESTIMATION: str = os.getenv('OPENAI_MODEL_ESTIMATION', 'gpt-4o')
    
    # Processing
    MAX_ATTACHMENT_SIZE_MB: int = int(os.getenv('MAX_ATTACHMENT_SIZE_MB', '25'))
    EMAIL_RETENTION_DAYS: int = int(os.getenv('EMAIL_RETENTION_DAYS', '90'))
    
    # Security
    ENABLE_EMAIL_ALLOWLIST: bool = os.getenv('ENABLE_EMAIL_ALLOWLIST', 'false').lower() == 'true'
    ALLOWED_SENDER_DOMAINS: str = os.getenv('ALLOWED_SENDER_DOMAINS', '')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def get_boto3_config(cls) -> dict:
        """Get boto3 client configuration."""
        config = {'region_name': cls.AWS_REGION}
        if cls.USE_LOCALSTACK and cls.AWS_ENDPOINT_URL:
            config['endpoint_url'] = cls.AWS_ENDPOINT_URL
        return config

