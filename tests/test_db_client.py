"""
Unit tests for DynamoDB client.
These tests use moto to mock DynamoDB.
"""
import pytest
import boto3
from moto import mock_dynamodb
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.db_client import DynamoDBClient
from shared.config import Config


@pytest.fixture
def dynamodb_setup():
    """Set up mock DynamoDB tables."""
    with mock_dynamodb():
        # Create mock tables
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        
        # Projects table
        dynamodb.create_table(
            TableName=Config.PROJECTS_TABLE,
            KeySchema=[
                {'AttributeName': 'project_id', 'KeyType': 'HASH'},
                {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'project_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'N'},
                {'AttributeName': 'client_email', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[{
                'IndexName': 'client_email-index',
                'KeySchema': [{'AttributeName': 'client_email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'}
            }]
        )
        
        # Events table
        dynamodb.create_table(
            TableName=Config.EVENTS_TABLE,
            KeySchema=[
                {'AttributeName': 'project_id', 'KeyType': 'HASH'},
                {'AttributeName': 'event_timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'project_id', 'AttributeType': 'S'},
                {'AttributeName': 'event_timestamp', 'AttributeType': 'N'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Users table
        dynamodb.create_table(
            TableName=Config.USERS_TABLE,
            KeySchema=[
                {'AttributeName': 'user_email', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_email', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield


class TestDynamoDBClient:
    """Test cases for DynamoDBClient."""
    
    def test_create_project(self, dynamodb_setup):
        """Test project creation."""
        client = DynamoDBClient()
        
        project_data = {
            'client_email': 'test@example.com',
            'client_name': 'Test Client',
            'project_name': 'Test Project'
        }
        
        project_id = client.create_project(project_data)
        
        assert project_id.startswith('PROJ-')
    
    def test_get_project(self, dynamodb_setup):
        """Test project retrieval."""
        client = DynamoDBClient()
        
        # Create project
        project_data = {
            'client_email': 'test@example.com',
            'project_name': 'Test Project'
        }
        project_id = client.create_project(project_data)
        
        # Retrieve project
        project = client.get_project(project_id)
        
        assert project is not None
        assert project['project_id'] == project_id
        assert project['project_name'] == 'Test Project'
    
    def test_get_projects_by_client(self, dynamodb_setup):
        """Test retrieving projects by client email."""
        client = DynamoDBClient()
        
        # Create multiple projects
        for i in range(3):
            client.create_project({
                'client_email': 'test@example.com',
                'project_name': f'Project {i}'
            })
        
        # Retrieve projects
        projects = client.get_projects_by_client('test@example.com')
        
        assert len(projects) == 3
    
    def test_create_event(self, dynamodb_setup):
        """Test event creation."""
        client = DynamoDBClient()
        
        # Create project
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test Project'
        })
        
        # Create event
        event_data = {
            'event_type': 'EMAIL_RECEIVED',
            'sender': 'test@example.com',
            'subject': 'Test Email'
        }
        event_id = client.create_event(project_id, event_data)
        
        assert event_id is not None
    
    def test_get_project_events(self, dynamodb_setup):
        """Test retrieving project events."""
        client = DynamoDBClient()
        
        # Create project
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test Project'
        })
        
        # Create multiple events
        for i in range(3):
            client.create_event(project_id, {
                'event_type': 'TEST_EVENT',
                'data': f'Event {i}'
            })
        
        # Retrieve events
        events = client.get_project_events(project_id)
        
        assert len(events) == 3
    
    def test_create_user(self, dynamodb_setup):
        """Test user creation."""
        client = DynamoDBClient()
        
        user_data = {
            'user_email': 'user@example.com',
            'company_name': 'Test Company'
        }
        client.create_user(user_data)
        
        # Retrieve user
        user = client.get_user('user@example.com')
        
        assert user is not None
        assert user['user_email'] == 'user@example.com'
        assert user['company_name'] == 'Test Company'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

