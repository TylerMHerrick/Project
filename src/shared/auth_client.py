"""Authentication client for Cognito integration."""
import boto3
import jwt
from jwt import PyJWKClient
from typing import Dict, Optional, Any, List
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)


class AuthClient:
    """Wrapper for AWS Cognito authentication operations."""
    
    def __init__(self, user_pool_id: Optional[str] = None, region: Optional[str] = None):
        """Initialize Cognito client.
        
        Args:
            user_pool_id: Cognito User Pool ID (defaults to env var)
            region: AWS region (defaults to Config.AWS_REGION)
        """
        self.region = region or Config.AWS_REGION
        self.user_pool_id = user_pool_id or self._get_user_pool_id()
        self.cognito_client = boto3.client('cognito-idp', **Config.get_boto3_config())
        
        # Set up JWKS client for token verification
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self.jwks_client = PyJWKClient(self.jwks_url)
    
    def _get_user_pool_id(self) -> str:
        """Get User Pool ID from environment or CloudFormation outputs."""
        import os
        return os.getenv('USER_POOL_ID', '')
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token from Cognito.
        
        Args:
            token: JWT access token or ID token
            
        Returns:
            Decoded token payload with user information
            
        Raises:
            jwt.InvalidTokenError: If token is invalid or expired
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Verify and decode token
            decoded_token = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True}
            )
            
            return decoded_token
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to verify token: {str(e)}")
            raise
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Cognito.
        
        Args:
            access_token: Cognito access token
            
        Returns:
            User attributes
        """
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            
            # Convert attribute list to dictionary
            attributes = {}
            for attr in response.get('UserAttributes', []):
                attributes[attr['Name']] = attr['Value']
            
            return {
                'username': response.get('Username'),
                'attributes': attributes
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise
    
    def extract_organization_id(self, token: str) -> Optional[str]:
        """Extract organization_id from a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Organization ID or None if not found
        """
        try:
            decoded = self.verify_token(token)
            # Check in custom attributes
            return decoded.get('custom:organization_id')
        except Exception as e:
            logger.error(f"Failed to extract organization_id: {str(e)}")
            return None
    
    def extract_user_role(self, token: str) -> str:
        """Extract user role from a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            User role (admin, viewer, etc.) or 'viewer' as default
        """
        try:
            decoded = self.verify_token(token)
            return decoded.get('custom:role', 'viewer')
        except Exception as e:
            logger.error(f"Failed to extract role: {str(e)}")
            return 'viewer'
    
    def create_user(self, email: str, organization_id: str, role: str = 'admin', 
                   temporary_password: Optional[str] = None) -> Dict[str, Any]:
        """Create a new user in Cognito.
        
        Args:
            email: User email
            organization_id: Organization ID
            role: User role (admin, viewer)
            temporary_password: Temporary password (auto-generated if not provided)
            
        Returns:
            User creation response
        """
        try:
            # Generate temporary password if not provided
            if not temporary_password:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits
                temporary_password = ''.join(secrets.choice(alphabet) for _ in range(12)) + 'Aa1!'
            
            # Create user with email as username
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'custom:organization_id', 'Value': organization_id},
                    {'Name': 'custom:role', 'Value': role}
                ],
                TemporaryPassword=temporary_password,
                DesiredDeliveryMediums=['EMAIL']
            )
            
            logger.info(f"Created user: {email} for organization: {organization_id}")
            
            return {
                'user': response.get('User'),
                'temporary_password': temporary_password
            }
        except self.cognito_client.exceptions.UsernameExistsException:
            logger.warning(f"User {email} already exists")
            raise ValueError(f"User with email {email} already exists")
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise
    
    def update_user_attributes(self, username: str, attributes: Dict[str, str]) -> None:
        """Update user attributes in Cognito.
        
        Args:
            username: Username (email)
            attributes: Dictionary of attributes to update
        """
        try:
            # Convert dict to attribute list
            user_attributes = [
                {'Name': key, 'Value': value}
                for key, value in attributes.items()
            ]
            
            self.cognito_client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=user_attributes
            )
            
            logger.info(f"Updated attributes for user: {username}")
        except Exception as e:
            logger.error(f"Failed to update user attributes: {str(e)}")
            raise
    
    def delete_user(self, username: str) -> None:
        """Delete a user from Cognito.
        
        Args:
            username: Username (email) to delete
        """
        try:
            self.cognito_client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            logger.info(f"Deleted user: {username}")
        except Exception as e:
            logger.error(f"Failed to delete user: {str(e)}")
            raise
    
    def disable_user(self, username: str) -> None:
        """Disable a user account.
        
        Args:
            username: Username (email) to disable
        """
        try:
            self.cognito_client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            logger.info(f"Disabled user: {username}")
        except Exception as e:
            logger.error(f"Failed to disable user: {str(e)}")
            raise
    
    def enable_user(self, username: str) -> None:
        """Enable a disabled user account.
        
        Args:
            username: Username (email) to enable
        """
        try:
            self.cognito_client.admin_enable_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            logger.info(f"Enabled user: {username}")
        except Exception as e:
            logger.error(f"Failed to enable user: {str(e)}")
            raise
    
    def list_users_in_group(self, group_name: str) -> List[Dict[str, Any]]:
        """List all users in a Cognito group.
        
        Args:
            group_name: Group name
            
        Returns:
            List of users
        """
        try:
            response = self.cognito_client.list_users_in_group(
                UserPoolId=self.user_pool_id,
                GroupName=group_name
            )
            return response.get('Users', [])
        except Exception as e:
            logger.error(f"Failed to list users in group: {str(e)}")
            raise
    
    def validate_organization_access(self, token: str, required_organization_id: str) -> bool:
        """Validate that a user has access to a specific organization.
        
        Args:
            token: JWT token
            required_organization_id: Organization ID to check access for
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            user_org_id = self.extract_organization_id(token)
            return user_org_id == required_organization_id
        except Exception as e:
            logger.error(f"Failed to validate organization access: {str(e)}")
            return False
    
    def check_admin_role(self, token: str) -> bool:
        """Check if user has admin role.
        
        Args:
            token: JWT token
            
        Returns:
            True if user is admin, False otherwise
        """
        try:
            role = self.extract_user_role(token)
            return role == 'admin'
        except Exception as e:
            logger.error(f"Failed to check admin role: {str(e)}")
            return False

