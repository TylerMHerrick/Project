"""
Comprehensive tests for DynamoDB Client operations.
Tests: Projects table, Events table, Users table, all CRUD operations
"""
import pytest
import boto3
from moto import mock_dynamodb
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.db_client import DynamoDBClient
from shared.config import Config


@pytest.fixture
def dynamodb_setup():
    """Set up mock DynamoDB tables."""
    with mock_dynamodb():
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


class TestDynamoDBProjects:
    """Test cases for Projects table operations."""
    
    def test_create_project_minimal(self, dynamodb_setup):
        """✅ TEST: Create project with minimal data"""
        client = DynamoDBClient()
        
        project_data = {
            'client_email': 'contractor@example.com',
            'project_name': 'Main Street Renovation'
        }
        
        project_id = client.create_project(project_data)
        
        assert project_id.startswith('PROJ-'), "Project ID should have PROJ- prefix"
        assert len(project_id) > 10, "Project ID should be sufficiently long"
        print(f"   ✓ Project created: {project_id}")
    
    def test_create_project_complete(self, dynamodb_setup):
        """✅ TEST: Create project with complete data"""
        client = DynamoDBClient()
        
        project_data = {
            'client_email': 'contractor@example.com',
            'client_name': 'ABC Construction',
            'project_name': 'Downtown Office Building',
            'project_address': '123 Main St, Anytown, ST 12345',
            'estimated_budget': 500000,
            'estimated_timeline': '6 months',
            'trade': 'electrical'
        }
        
        project_id = client.create_project(project_data)
        
        # Retrieve and verify
        project = client.get_project(project_id)
        assert project['project_name'] == 'Downtown Office Building'
        assert project['estimated_budget'] == 500000
        assert project['status'] == 'active'
        print(f"   ✓ Complete project created: {project['project_name']}")
    
    def test_get_project(self, dynamodb_setup):
        """✅ TEST: Retrieve existing project"""
        client = DynamoDBClient()
        
        # Create project
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test Project'
        })
        
        # Retrieve project
        project = client.get_project(project_id)
        
        assert project is not None, "Project should exist"
        assert project['project_id'] == project_id
        assert project['project_name'] == 'Test Project'
        assert 'created_at' in project
        assert 'updated_at' in project
        print("   ✓ Project retrieved successfully")
    
    def test_get_project_not_found(self, dynamodb_setup):
        """✅ TEST: Handle non-existent project"""
        client = DynamoDBClient()
        
        project = client.get_project('PROJ-nonexistent-12345')
        
        assert project is None, "Should return None for non-existent project"
        print("   ✓ Non-existent project handled gracefully")
    
    def test_get_projects_by_client(self, dynamodb_setup):
        """✅ TEST: Retrieve all projects for a client"""
        client = DynamoDBClient()
        client_email = 'builder@example.com'
        
        # Create multiple projects
        project_names = ['Project Alpha', 'Project Beta', 'Project Gamma']
        for name in project_names:
            client.create_project({
                'client_email': client_email,
                'project_name': name
            })
        
        # Retrieve all projects
        projects = client.get_projects_by_client(client_email)
        
        assert len(projects) == 3, "Should retrieve all 3 projects"
        retrieved_names = {p['project_name'] for p in projects}
        assert retrieved_names == set(project_names)
        print(f"   ✓ Retrieved {len(projects)} projects for client")
    
    def test_get_projects_by_client_empty(self, dynamodb_setup):
        """✅ TEST: Handle client with no projects"""
        client = DynamoDBClient()
        
        projects = client.get_projects_by_client('newclient@example.com')
        
        assert len(projects) == 0, "Should return empty list"
        print("   ✓ Empty project list handled")
    
    def test_update_project(self, dynamodb_setup):
        """✅ TEST: Update project information"""
        client = DynamoDBClient()
        
        # Create project
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Original Name',
            'status': 'active'
        })
        
        # Update project
        time.sleep(0.1)  # Ensure different timestamp
        client.update_project(project_id, {
            'project_name': 'Updated Name',
            'status': 'in_progress',
            'estimated_budget': 100000
        })
        
        # Verify updates
        project = client.get_project(project_id)
        assert project['project_name'] == 'Updated Name'
        assert project['status'] == 'in_progress'
        assert project['estimated_budget'] == 100000
        assert project['updated_at'] > project['created_at'], "updated_at should be newer"
        print("   ✓ Project updated successfully")
    
    def test_update_nonexistent_project(self, dynamodb_setup):
        """✅ TEST: Handle updating non-existent project"""
        client = DynamoDBClient()
        
        with pytest.raises(ValueError):
            client.update_project('PROJ-nonexistent', {'status': 'completed'})
        
        print("   ✓ Update of non-existent project raises error")
    
    def test_multiple_clients_projects(self, dynamodb_setup):
        """✅ TEST: Multiple clients with separate projects"""
        client = DynamoDBClient()
        
        # Client A projects
        client_a = 'clienta@example.com'
        client.create_project({'client_email': client_a, 'project_name': 'A1'})
        client.create_project({'client_email': client_a, 'project_name': 'A2'})
        
        # Client B projects
        client_b = 'clientb@example.com'
        client.create_project({'client_email': client_b, 'project_name': 'B1'})
        
        # Verify separation
        projects_a = client.get_projects_by_client(client_a)
        projects_b = client.get_projects_by_client(client_b)
        
        assert len(projects_a) == 2
        assert len(projects_b) == 1
        print("   ✓ Multiple clients' projects properly isolated")


class TestDynamoDBEvents:
    """Test cases for Events table operations (audit log)."""
    
    def test_create_event(self, dynamodb_setup):
        """✅ TEST: Create event for project"""
        client = DynamoDBClient()
        
        # Create project first
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test Project'
        })
        
        # Create event
        event_data = {
            'event_type': 'EMAIL_RECEIVED',
            'sender': 'contractor@example.com',
            'subject': 'Project Update',
            'body_preview': 'We need to discuss...'
        }
        event_id = client.create_event(project_id, event_data)
        
        assert event_id is not None
        assert len(event_id) > 0
        print(f"   ✓ Event created: {event_id}")
    
    def test_get_project_events(self, dynamodb_setup):
        """✅ TEST: Retrieve all events for project"""
        client = DynamoDBClient()
        
        # Create project
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test Project'
        })
        
        # Create multiple events
        event_types = ['EMAIL_RECEIVED', 'DECISION_MADE', 'SCOPE_CHANGE']
        for event_type in event_types:
            client.create_event(project_id, {'event_type': event_type})
            time.sleep(0.01)  # Ensure different timestamps
        
        # Retrieve events
        events = client.get_project_events(project_id)
        
        assert len(events) == 3, "Should retrieve all 3 events"
        # Events should be in descending order (newest first)
        assert events[0]['event_type'] == 'SCOPE_CHANGE'
        assert events[2]['event_type'] == 'EMAIL_RECEIVED'
        print(f"   ✓ Retrieved {len(events)} events in chronological order")
    
    def test_events_chronological_order(self, dynamodb_setup):
        """✅ TEST: Events are returned in chronological order"""
        client = DynamoDBClient()
        
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test'
        })
        
        # Create events with delays
        timestamps = []
        for i in range(5):
            event_data = {'event_type': f'EVENT_{i}', 'sequence': i}
            client.create_event(project_id, event_data)
            time.sleep(0.01)
        
        # Retrieve events
        events = client.get_project_events(project_id)
        
        # Verify descending order (newest first)
        for i in range(len(events) - 1):
            assert events[i]['event_timestamp'] >= events[i+1]['event_timestamp']
        
        print("   ✓ Events in proper chronological order (newest first)")
    
    def test_events_limit(self, dynamodb_setup):
        """✅ TEST: Limit number of events returned"""
        client = DynamoDBClient()
        
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test'
        })
        
        # Create many events
        for i in range(15):
            client.create_event(project_id, {'event_type': f'EVENT_{i}'})
        
        # Retrieve with limit
        events = client.get_project_events(project_id, limit=5)
        
        assert len(events) == 5, "Should respect limit parameter"
        print("   ✓ Event limit respected")
    
    def test_event_with_complex_data(self, dynamodb_setup):
        """✅ TEST: Store event with complex AI-extracted data"""
        client = DynamoDBClient()
        
        project_id = client.create_project({
            'client_email': 'test@example.com',
            'project_name': 'Test'
        })
        
        # Complex event data (simulating AI extraction)
        event_data = {
            'event_type': 'EMAIL_RECEIVED',
            'sender': 'pm@construction.com',
            'subject': 'Budget Approved',
            'ai_extracted_data': {
                'decisions': [
                    {'decision': 'Budget approved', 'made_by': 'John Smith', 'amount': 50000}
                ],
                'action_items': [
                    {'task': 'Order materials', 'owner': 'Bob', 'deadline': '2025-03-15'}
                ],
                'risks': ['Weather delay possible'],
                'key_points': ['Budget approved', 'Materials needed soon']
            },
            'attachments': ['drawing1.pdf', 'specs.docx']
        }
        
        event_id = client.create_event(project_id, event_data)
        
        # Retrieve and verify
        events = client.get_project_events(project_id)
        assert len(events) == 1
        event = events[0]
        assert event['ai_extracted_data']['decisions'][0]['amount'] == 50000
        assert len(event['attachments']) == 2
        print("   ✓ Complex event data stored correctly")
    
    def test_events_for_nonexistent_project(self, dynamodb_setup):
        """✅ TEST: Handle events query for non-existent project"""
        client = DynamoDBClient()
        
        events = client.get_project_events('PROJ-nonexistent')
        
        assert len(events) == 0, "Should return empty list for non-existent project"
        print("   ✓ Non-existent project events handled gracefully")


class TestDynamoDBUsers:
    """Test cases for Users table operations."""
    
    def test_create_user(self, dynamodb_setup):
        """✅ TEST: Create user account"""
        client = DynamoDBClient()
        
        user_data = {
            'user_email': 'contractor@example.com',
            'company_name': 'ABC Construction',
            'phone': '555-0100'
        }
        
        client.create_user(user_data)
        
        # Retrieve and verify
        user = client.get_user('contractor@example.com')
        assert user is not None
        assert user['user_email'] == 'contractor@example.com'
        assert user['company_name'] == 'ABC Construction'
        assert user['subscription_tier'] == 'free'  # Default
        assert user['api_quota'] == 1000  # Default
        print(f"   ✓ User created: {user['user_email']}")
    
    def test_create_user_minimal(self, dynamodb_setup):
        """✅ TEST: Create user with minimal data"""
        client = DynamoDBClient()
        
        user_data = {
            'user_email': 'simple@example.com'
        }
        
        client.create_user(user_data)
        user = client.get_user('simple@example.com')
        
        assert user is not None
        assert 'created_at' in user
        print("   ✓ Minimal user created with defaults")
    
    def test_create_user_no_email(self, dynamodb_setup):
        """✅ TEST: Handle user creation without email"""
        client = DynamoDBClient()
        
        with pytest.raises(ValueError):
            client.create_user({'company_name': 'No Email Company'})
        
        print("   ✓ User creation without email raises error")
    
    def test_get_user(self, dynamodb_setup):
        """✅ TEST: Retrieve existing user"""
        client = DynamoDBClient()
        
        # Create user
        client.create_user({
            'user_email': 'test@example.com',
            'company_name': 'Test Company'
        })
        
        # Retrieve user
        user = client.get_user('test@example.com')
        
        assert user is not None
        assert user['user_email'] == 'test@example.com'
        assert user['company_name'] == 'Test Company'
        print("   ✓ User retrieved successfully")
    
    def test_get_user_not_found(self, dynamodb_setup):
        """✅ TEST: Handle non-existent user"""
        client = DynamoDBClient()
        
        user = client.get_user('nonexistent@example.com')
        
        assert user is None, "Should return None for non-existent user"
        print("   ✓ Non-existent user handled gracefully")
    
    def test_update_user_via_put(self, dynamodb_setup):
        """✅ TEST: Update user by putting new data"""
        client = DynamoDBClient()
        
        # Create user
        client.create_user({
            'user_email': 'update@example.com',
            'company_name': 'Original Company'
        })
        
        # Update user (put_item overwrites)
        client.create_user({
            'user_email': 'update@example.com',
            'company_name': 'Updated Company',
            'subscription_tier': 'premium'
        })
        
        # Verify
        user = client.get_user('update@example.com')
        assert user['company_name'] == 'Updated Company'
        assert user['subscription_tier'] == 'premium'
        print("   ✓ User updated successfully")
    
    def test_multiple_users(self, dynamodb_setup):
        """✅ TEST: Create and manage multiple users"""
        client = DynamoDBClient()
        
        users = [
            {'user_email': 'user1@example.com', 'company_name': 'Company 1'},
            {'user_email': 'user2@example.com', 'company_name': 'Company 2'},
            {'user_email': 'user3@example.com', 'company_name': 'Company 3'},
        ]
        
        # Create all users
        for user_data in users:
            client.create_user(user_data)
        
        # Verify each exists
        for user_data in users:
            user = client.get_user(user_data['user_email'])
            assert user is not None
            assert user['company_name'] == user_data['company_name']
        
        print(f"   ✓ Created and verified {len(users)} users")
    
    def test_user_with_quota_tracking(self, dynamodb_setup):
        """✅ TEST: User with API quota tracking"""
        client = DynamoDBClient()
        
        client.create_user({
            'user_email': 'quota@example.com',
            'company_name': 'Quota Test',
            'subscription_tier': 'premium',
            'api_quota': 10000,
            'api_usage_current_month': 2500
        })
        
        user = client.get_user('quota@example.com')
        assert user['api_quota'] == 10000
        assert user['api_usage_current_month'] == 2500
        print("   ✓ User quota tracking works")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

