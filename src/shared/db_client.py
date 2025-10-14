"""DynamoDB client wrapper for multi-tenant project tracking operations."""
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
    """Wrapper for DynamoDB operations with multi-tenant support."""
    
    def __init__(self):
        """Initialize DynamoDB client."""
        self.dynamodb = boto3.resource('dynamodb', **Config.get_boto3_config())
        self.organizations_table = self.dynamodb.Table(Config.ORGANIZATIONS_TABLE)
        self.projects_table = self.dynamodb.Table(Config.PROJECTS_TABLE)
        self.events_table = self.dynamodb.Table(Config.EVENTS_TABLE)
        self.users_table = self.dynamodb.Table(Config.USERS_TABLE)
        self.api_usage_table = self.dynamodb.Table(Config.API_USAGE_TABLE)
    
    # ==================== Organization Methods ====================
    
    def create_organization(self, org_data: Dict[str, Any]) -> str:
        """Create a new organization.
        
        Args:
            org_data: Organization information (organization_name, email_address, subdomain, etc.)
            
        Returns:
            Organization ID
        """
        organization_id = f"ORG-{uuid.uuid4().hex[:12]}"
        timestamp = int(datetime.now().timestamp() * 1000)
        
        item = {
            'organization_id': organization_id,
            'created_at': timestamp,
            'updated_at': timestamp,
            'subscription_tier': 'starter',
            'billing_status': 'active',
            'monthly_api_budget': 20.0,
            'current_month_spend': 0.0,
            **org_data
        }
        
        try:
            logger.info(f"Creating organization: {organization_id}")
            self.organizations_table.put_item(Item=item)
            return organization_id
        except Exception as e:
            logger.error(f"Failed to create organization: {str(e)}")
            raise
    
    def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve organization by ID.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Organization data or None if not found
        """
        try:
            response = self.organizations_table.get_item(Key={'organization_id': organization_id})
            return response.get('Item')
        except Exception as e:
            logger.error(f"Failed to get organization {organization_id}: {str(e)}")
            raise
    
    def get_organization_by_email(self, email_address: str) -> Optional[Dict[str, Any]]:
        """Retrieve organization by email address.
        
        Args:
            email_address: Organization email address (e.g., acme@myprojectr.com)
            
        Returns:
            Organization data or None if not found
        """
        try:
            response = self.organizations_table.query(
                IndexName='email_address-index',
                KeyConditionExpression=Key('email_address').eq(email_address),
                Limit=1
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Failed to get organization by email {email_address}: {str(e)}")
            raise
    
    def get_organization_by_subdomain(self, subdomain: str) -> Optional[Dict[str, Any]]:
        """Retrieve organization by subdomain.
        
        Args:
            subdomain: Organization subdomain (e.g., 'acme')
            
        Returns:
            Organization data or None if not found
        """
        try:
            response = self.organizations_table.query(
                IndexName='subdomain-index',
                KeyConditionExpression=Key('subdomain').eq(subdomain),
                Limit=1
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Failed to get organization by subdomain {subdomain}: {str(e)}")
            raise
    
    def update_organization(self, organization_id: str, updates: Dict[str, Any]) -> None:
        """Update organization information.
        
        Args:
            organization_id: Organization ID
            updates: Fields to update
        """
        try:
            updates['updated_at'] = int(datetime.now().timestamp() * 1000)
            
            # Build update expression
            update_expr = 'SET ' + ', '.join([f'#{k} = :{k}' for k in updates.keys()])
            expr_attr_names = {f'#{k}': k for k in updates.keys()}
            expr_attr_values = {f':{k}': v for k, v in updates.items()}
            
            logger.info(f"Updating organization: {organization_id}")
            self.organizations_table.update_item(
                Key={'organization_id': organization_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
        except Exception as e:
            logger.error(f"Failed to update organization {organization_id}: {str(e)}")
            raise
    
    # ==================== Project Methods ====================
    
    def create_project(self, organization_id: str, project_data: Dict[str, Any]) -> str:
        """Create a new project within an organization.
        
        Args:
            organization_id: Organization ID
            project_data: Project information
            
        Returns:
            Project ID
        """
        project_id = f"PROJ-{uuid.uuid4().hex[:8]}"
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # Composite sort key: project_id#timestamp
        project_id_created_at = f"{project_id}#{timestamp}"
        
        item = {
            'organization_id': organization_id,
            'project_id': project_id,
            'project_id_created_at': project_id_created_at,
            'created_at': timestamp,
            'updated_at': timestamp,
            'status': 'active',
            **project_data
        }
        
        try:
            logger.info(f"Creating project: {project_id} for org: {organization_id}")
            self.projects_table.put_item(Item=item)
            return project_id
        except Exception as e:
            logger.error(f"Failed to create project: {str(e)}")
            raise
    
    def get_project(self, organization_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve project by ID within an organization.
        
        Args:
            organization_id: Organization ID
            project_id: Project ID
            
        Returns:
            Project data or None if not found
        """
        try:
            # Query using begins_with since we don't know the exact timestamp
            response = self.projects_table.query(
                KeyConditionExpression=Key('organization_id').eq(organization_id) & 
                                     Key('project_id_created_at').begins_with(f"{project_id}#"),
                Limit=1
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {str(e)}")
            raise
    
    def get_projects_by_organization(self, organization_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all projects for an organization.
        
        Args:
            organization_id: Organization ID
            status: Optional status filter ('active', 'completed', 'on-hold')
            
        Returns:
            List of projects
        """
        try:
            if status:
                # Use the organization_id-status-index
                response = self.projects_table.query(
                    IndexName='organization_id-status-index',
                    KeyConditionExpression=Key('organization_id').eq(organization_id) & Key('status').eq(status)
                )
            else:
                # Query all projects for organization
                response = self.projects_table.query(
                    KeyConditionExpression=Key('organization_id').eq(organization_id)
                )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get projects for organization {organization_id}: {str(e)}")
            raise
    
    def get_projects_by_client(self, client_email: str) -> List[Dict[str, Any]]:
        """Get all projects for a client email address (cross-organization for migration).
        
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
    
    def update_project(self, organization_id: str, project_id: str, updates: Dict[str, Any]) -> None:
        """Update project information.
        
        Args:
            organization_id: Organization ID
            project_id: Project ID
            updates: Fields to update
        """
        try:
            # Get the project first to find the exact sort key
            project = self.get_project(organization_id, project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found in organization {organization_id}")
            
            updates['updated_at'] = int(datetime.now().timestamp() * 1000)
            
            # Build update expression
            update_expr = 'SET ' + ', '.join([f'#{k} = :{k}' for k in updates.keys()])
            expr_attr_names = {f'#{k}': k for k in updates.keys()}
            expr_attr_values = {f':{k}': v for k, v in updates.items()}
            
            logger.info(f"Updating project: {project_id}")
            self.projects_table.update_item(
                Key={
                    'organization_id': organization_id,
                    'project_id_created_at': project['project_id_created_at']
                },
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {str(e)}")
            raise
    
    # ==================== Event Methods ====================
    
    def create_event(self, organization_id: str, project_id: str, event_data: Dict[str, Any]) -> str:
        """Create a project event (append-only audit log).
        
        Args:
            organization_id: Organization ID
            project_id: Project ID
            event_data: Event information
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # Composite partition key: organization_id#project_id
        organization_id_project_id = f"{organization_id}#{project_id}"
        
        item = {
            'organization_id': organization_id,
            'project_id': project_id,
            'organization_id_project_id': organization_id_project_id,
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
    
    def get_project_events(self, organization_id: str, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events for a project in chronological order.
        
        Args:
            organization_id: Organization ID
            project_id: Project ID
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        try:
            organization_id_project_id = f"{organization_id}#{project_id}"
            response = self.events_table.query(
                KeyConditionExpression=Key('organization_id_project_id').eq(organization_id_project_id),
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get events for project {project_id}: {str(e)}")
            raise
    
    def get_organization_events(self, organization_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all events for an organization.
        
        Args:
            organization_id: Organization ID
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        try:
            response = self.events_table.query(
                IndexName='organization_id-index',
                KeyConditionExpression=Key('organization_id').eq(organization_id),
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get events for organization {organization_id}: {str(e)}")
            raise
    
    # ==================== User Methods ====================
    
    def create_user(self, user_data: Dict[str, Any]) -> None:
        """Create or update user account.
        
        Args:
            user_data: User information (must include 'user_email' and 'organization_id')
        """
        if 'user_email' not in user_data:
            raise ValueError("user_email is required")
        if 'organization_id' not in user_data:
            raise ValueError("organization_id is required")
        
        item = {
            'created_at': int(datetime.now().timestamp() * 1000),
            'role': 'viewer',  # Default role
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
    
    def get_organization_users(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all users in an organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            List of users
        """
        try:
            response = self.users_table.query(
                IndexName='organization_id-index',
                KeyConditionExpression=Key('organization_id').eq(organization_id)
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get users for organization {organization_id}: {str(e)}")
            raise
    
    def update_user(self, user_email: str, updates: Dict[str, Any]) -> None:
        """Update user information.
        
        Args:
            user_email: User email
            updates: Fields to update
        """
        try:
            updates['updated_at'] = int(datetime.now().timestamp() * 1000)
            
            # Build update expression
            update_expr = 'SET ' + ', '.join([f'#{k} = :{k}' for k in updates.keys()])
            expr_attr_names = {f'#{k}': k for k in updates.keys()}
            expr_attr_values = {f':{k}': v for k, v in updates.items()}
            
            logger.info(f"Updating user: {user_email}")
            self.users_table.update_item(
                Key={'user_email': user_email},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
        except Exception as e:
            logger.error(f"Failed to update user {user_email}: {str(e)}")
            raise
    
    # ==================== API Usage Tracking Methods ====================
    
    def track_api_usage(self, organization_id: str, usage_data: Dict[str, Any]) -> None:
        """Track API usage for cost monitoring.
        
        Args:
            organization_id: Organization ID
            usage_data: Usage information (api_provider, model, tokens_used, cost_usd)
        """
        timestamp = int(datetime.now().timestamp() * 1000)
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Composite partition key: organization_id#date
        organization_id_date = f"{organization_id}#{date}"
        
        # TTL: 90 days from now
        ttl = int((datetime.now().timestamp() + (90 * 24 * 60 * 60)))
        
        item = {
            'organization_id': organization_id,
            'organization_id_date': organization_id_date,
            'timestamp': timestamp,
            'date': date,
            'ttl': ttl,
            **usage_data
        }
        
        try:
            self.api_usage_table.put_item(Item=item)
        except Exception as e:
            logger.error(f"Failed to track API usage: {str(e)}")
            raise
    
    def get_api_usage_by_date(self, organization_id: str, date: str) -> List[Dict[str, Any]]:
        """Get API usage for a specific date.
        
        Args:
            organization_id: Organization ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of usage records
        """
        try:
            organization_id_date = f"{organization_id}#{date}"
            response = self.api_usage_table.query(
                KeyConditionExpression=Key('organization_id_date').eq(organization_id_date)
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get API usage for date {date}: {str(e)}")
            raise
    
    def get_api_usage_summary(self, organization_id: str, days: int = 30) -> Dict[str, Any]:
        """Get API usage summary for the last N days.
        
        Args:
            organization_id: Organization ID
            days: Number of days to look back
            
        Returns:
            Summary with total_cost, total_tokens, breakdown by model
        """
        try:
            # Query using organization_id-index for last N days
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)
            start_timestamp = int(start_date.timestamp() * 1000)
            
            response = self.api_usage_table.query(
                IndexName='organization_id-index',
                KeyConditionExpression=Key('organization_id').eq(organization_id) & 
                                     Key('timestamp').gte(start_timestamp)
            )
            
            items = response.get('Items', [])
            
            # Calculate summary
            total_cost = sum(float(item.get('cost_usd', 0)) for item in items)
            total_tokens = sum(int(item.get('tokens_used', 0)) for item in items)
            
            # Breakdown by model
            model_breakdown = {}
            for item in items:
                model = item.get('model', 'unknown')
                if model not in model_breakdown:
                    model_breakdown[model] = {'cost': 0.0, 'tokens': 0, 'calls': 0}
                model_breakdown[model]['cost'] += float(item.get('cost_usd', 0))
                model_breakdown[model]['tokens'] += int(item.get('tokens_used', 0))
                model_breakdown[model]['calls'] += 1
            
            return {
                'organization_id': organization_id,
                'period_days': days,
                'total_cost_usd': round(total_cost, 2),
                'total_tokens': total_tokens,
                'total_calls': len(items),
                'model_breakdown': model_breakdown
            }
        except Exception as e:
            logger.error(f"Failed to get API usage summary: {str(e)}")
            raise
