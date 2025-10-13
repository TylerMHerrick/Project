"""DynamoDB client wrapper for project tracking operations."""
import boto3
from boto3.dynamodb.conditions import Key
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from decimal import Decimal
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)


class DynamoDBClient:
    """Wrapper for DynamoDB operations."""
    
    def __init__(self):
        """Initialize DynamoDB client."""
        self.dynamodb = boto3.resource('dynamodb', **Config.get_boto3_config())
        self.projects_table = self.dynamodb.Table(Config.PROJECTS_TABLE)
        self.events_table = self.dynamodb.Table(Config.EVENTS_TABLE)
        self.users_table = self.dynamodb.Table(Config.USERS_TABLE)
    
    def create_project(self, project_data: Dict[str, Any]) -> str:
        """Create a new project.
        
        Args:
            project_data: Project information
            
        Returns:
            Project ID
        """
        project_id = f"PROJ-{uuid.uuid4()}"
        timestamp = int(datetime.now().timestamp())
        
        item = {
            'project_id': project_id,
            'created_at': timestamp,
            'updated_at': timestamp,
            'status': 'active',
            **project_data
        }
        
        try:
            logger.info(f"Creating project: {project_id}")
            self.projects_table.put_item(Item=item)
            return project_id
        except Exception as e:
            logger.error(f"Failed to create project: {str(e)}")
            raise
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project data or None if not found
        """
        try:
            response = self.projects_table.query(
                KeyConditionExpression=Key('project_id').eq(project_id),
                Limit=1
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {str(e)}")
            raise
    
    def get_projects_by_client(self, client_email: str) -> List[Dict[str, Any]]:
        """Get all projects for a client.
        
        Args:
            client_email: Client email address
            
        Returns:
            List of projects
        """
        try:
            response = self.projects_table.query(
                IndexName='client_email-index',
                KeyConditionExpression=Key('client_email').eq(client_email)
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get projects for client {client_email}: {str(e)}")
            raise
    
    def update_project(self, project_id: str, updates: Dict[str, Any]) -> None:
        """Update project information.
        
        Args:
            project_id: Project ID
            updates: Fields to update
        """
        try:
            # Get the created_at timestamp first
            project = self.get_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            updates['updated_at'] = int(datetime.now().timestamp())
            
            # Build update expression
            update_expr = 'SET ' + ', '.join([f'#{k} = :{k}' for k in updates.keys()])
            expr_attr_names = {f'#{k}': k for k in updates.keys()}
            expr_attr_values = {f':{k}': v for k, v in updates.items()}
            
            logger.info(f"Updating project: {project_id}")
            self.projects_table.update_item(
                Key={
                    'project_id': project_id,
                    'created_at': project['created_at']
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {str(e)}")
            raise
    
    def create_event(self, project_id: str, event_data: Dict[str, Any]) -> str:
        """Create a project event (append-only audit log).
        
        Args:
            project_id: Project ID
            event_data: Event information
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())
        
        item = {
            'project_id': project_id,
            'event_timestamp': timestamp,
            'event_id': event_id,
            **event_data
        }
        
        try:
            logger.info(f"Creating event for project {project_id}: {event_id}")
            self.events_table.put_item(Item=item)
            return event_id
        except Exception as e:
            logger.error(f"Failed to create event: {str(e)}")
            raise
    
    def get_project_events(self, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events for a project in chronological order.
        
        Args:
            project_id: Project ID
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        try:
            response = self.events_table.query(
                KeyConditionExpression=Key('project_id').eq(project_id),
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get events for project {project_id}: {str(e)}")
            raise
    
    def create_user(self, user_data: Dict[str, Any]) -> None:
        """Create or update user account.
        
        Args:
            user_data: User information (must include 'user_email')
        """
        if 'user_email' not in user_data:
            raise ValueError("user_email is required")
        
        item = {
            'created_at': int(datetime.now().timestamp()),
            'subscription_tier': 'free',
            'api_quota': 1000,
            **user_data
        }
        
        try:
            logger.info(f"Creating/updating user: {user_data['user_email']}")
            self.users_table.put_item(Item=item)
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise
    
    def get_user(self, user_email: str) -> Optional[Dict[str, Any]]:
        """Get user by email.
        
        Args:
            user_email: User email address
            
        Returns:
            User data or None if not found
        """
        try:
            response = self.users_table.get_item(Key={'user_email': user_email})
            return response.get('Item')
        except Exception as e:
            logger.error(f"Failed to get user {user_email}: {str(e)}")
            raise

