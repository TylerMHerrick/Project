"""
Script to create DynamoDB tables locally or in AWS.
Run this after deploying infrastructure or to set up LocalStack.
"""
import boto3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.config import Config
from shared.logger import setup_logger

logger = setup_logger(__name__)


def create_tables():
    """Create all DynamoDB tables."""
    dynamodb = boto3.client('dynamodb', **Config.get_boto3_config())
    
    tables_to_create = [
        {
            'name': Config.ORGANIZATIONS_TABLE,
            'config': get_organizations_table_config()
        },
        {
            'name': Config.PROJECTS_TABLE,
            'config': get_projects_table_config()
        },
        {
            'name': Config.EVENTS_TABLE,
            'config': get_events_table_config()
        },
        {
            'name': Config.USERS_TABLE,
            'config': get_users_table_config()
        },
        {
            'name': Config.API_USAGE_TABLE,
            'config': get_api_usage_table_config()
        }
    ]
    
    for table_def in tables_to_create:
        try:
            # Check if table exists
            existing_tables = dynamodb.list_tables()['TableNames']
            if table_def['name'] in existing_tables:
                logger.info(f"Table {table_def['name']} already exists")
                continue
            
            # Create table
            logger.info(f"Creating table: {table_def['name']}")
            dynamodb.create_table(**table_def['config'])
            logger.info(f"Successfully created table: {table_def['name']}")
            
        except Exception as e:
            logger.error(f"Failed to create table {table_def['name']}: {str(e)}")
            raise


def get_organizations_table_config():
    """Get Organizations table configuration."""
    return {
        'TableName': Config.ORGANIZATIONS_TABLE,
        'KeySchema': [
            {'AttributeName': 'organization_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'organization_id', 'AttributeType': 'S'},
            {'AttributeName': 'email_address', 'AttributeType': 'S'},
            {'AttributeName': 'subdomain', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'email_address-index',
                'KeySchema': [
                    {'AttributeName': 'email_address', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'subdomain-index',
                'KeySchema': [
                    {'AttributeName': 'subdomain', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'SSESpecification': {'Enabled': True}
    }


def get_projects_table_config():
    """Get Projects table configuration - Multi-tenant."""
    return {
        'TableName': Config.PROJECTS_TABLE,
        'KeySchema': [
            {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
            {'AttributeName': 'project_id_created_at', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'organization_id', 'AttributeType': 'S'},
            {'AttributeName': 'project_id_created_at', 'AttributeType': 'S'},
            {'AttributeName': 'client_email', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'client_email-index',
                'KeySchema': [
                    {'AttributeName': 'client_email', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'organization_id-status-index',
                'KeySchema': [
                    {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'status', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        'SSESpecification': {'Enabled': True}
    }


def get_events_table_config():
    """Get Events table configuration - Multi-tenant."""
    return {
        'TableName': Config.EVENTS_TABLE,
        'KeySchema': [
            {'AttributeName': 'organization_id_project_id', 'KeyType': 'HASH'},
            {'AttributeName': 'event_timestamp', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'organization_id_project_id', 'AttributeType': 'S'},
            {'AttributeName': 'event_timestamp', 'AttributeType': 'N'},
            {'AttributeName': 'organization_id', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'GlobalSecondaryIndexes': [{
            'IndexName': 'organization_id-index',
            'KeySchema': [
                {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
                {'AttributeName': 'event_timestamp', 'KeyType': 'RANGE'}
            ],
            'Projection': {'ProjectionType': 'ALL'}
        }],
        'SSESpecification': {'Enabled': True}
    }


def get_users_table_config():
    """Get Users table configuration - Multi-tenant."""
    return {
        'TableName': Config.USERS_TABLE,
        'KeySchema': [
            {'AttributeName': 'user_email', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'user_email', 'AttributeType': 'S'},
            {'AttributeName': 'organization_id', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'GlobalSecondaryIndexes': [{
            'IndexName': 'organization_id-index',
            'KeySchema': [
                {'AttributeName': 'organization_id', 'KeyType': 'HASH'}
            ],
            'Projection': {'ProjectionType': 'ALL'}
        }],
        'SSESpecification': {'Enabled': True}
    }


def get_api_usage_table_config():
    """Get API Usage table configuration."""
    return {
        'TableName': Config.API_USAGE_TABLE,
        'KeySchema': [
            {'AttributeName': 'organization_id_date', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'organization_id_date', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'},
            {'AttributeName': 'organization_id', 'AttributeType': 'S'}
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'GlobalSecondaryIndexes': [{
            'IndexName': 'organization_id-index',
            'KeySchema': [
                {'AttributeName': 'organization_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            'Projection': {'ProjectionType': 'ALL'}
        }],
        'SSESpecification': {'Enabled': True}
    }


if __name__ == '__main__':
    logger.info("Starting DynamoDB table creation...")
    logger.info(f"Environment: {Config.ENVIRONMENT}")
    logger.info(f"Using LocalStack: {Config.USE_LOCALSTACK}")
    
    create_tables()
    
    logger.info("Table creation complete!")

