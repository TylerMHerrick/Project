"""
Client Onboarding Script

This script automates the onboarding of new clients/organizations.

Usage:
    python scripts/onboard_client.py \
        --org-name "ACME Construction" \
        --email "acme@myprojectr.com" \
        --subdomain "acme" \
        --admin-email "john@acmeconstruction.com" \
        --admin-name "John Smith" \
        --tier "starter" \
        --create-stripe-customer

"""
import sys
import os
import argparse
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.db_client import DynamoDBClient
from shared.auth_client import AuthClient
from shared.billing_client import BillingClient
from shared.logger import setup_logger

logger = setup_logger(__name__)


def onboard_client(org_name: str, email: str, subdomain: str, 
                   admin_email: str, admin_name: str, 
                   tier: str = 'starter', create_stripe: bool = False,
                   trial_days: int = 14) -> dict:
    """Onboard a new client organization.
    
    Args:
        org_name: Organization name
        email: Organization email address (e.g., acme@myprojectr.com)
        subdomain: Subdomain identifier (e.g., 'acme')
        admin_email: Admin user email
        admin_name: Admin user name
        tier: Subscription tier (starter, professional, enterprise)
        create_stripe: Whether to create Stripe customer
        trial_days: Number of trial days
        
    Returns:
        Dictionary with onboarding results
    """
    logger.info(f"Starting onboarding for organization: {org_name}")
    
    # Initialize clients
    db_client = DynamoDBClient()
    auth_client = AuthClient()
    billing_client = BillingClient() if create_stripe else None
    
    results = {
        'organization_id': None,
        'stripe_customer_id': None,
        'admin_user_created': False,
        'temporary_password': None,
        'error': None
    }
    
    try:
        # Step 1: Check if organization already exists
        logger.info("Checking if organization already exists...")
        existing_org = db_client.get_organization_by_email(email)
        if existing_org:
            raise ValueError(f"Organization with email {email} already exists: {existing_org['organization_id']}")
        
        existing_subdomain = db_client.get_organization_by_subdomain(subdomain)
        if existing_subdomain:
            raise ValueError(f"Subdomain {subdomain} already taken by: {existing_subdomain['organization_id']}")
        
        # Step 2: Create organization in DynamoDB
        logger.info("Creating organization in DynamoDB...")
        tier_config = BillingClient.get_tier_config(tier)
        
        org_data = {
            'organization_name': org_name,
            'email_address': email,
            'subdomain': subdomain,
            'subscription_tier': tier,
            'billing_status': 'trial' if trial_days > 0 else 'active',
            'monthly_api_budget': tier_config['api_budget'] or 1000.0,
            'current_month_spend': 0.0,
            'email_limit': tier_config['email_limit'],
            'project_limit': tier_config['project_limit'],
            'user_limit': tier_config['user_limit'],
            'trial_ends_at': int((datetime.now() + timedelta(days=trial_days)).timestamp() * 1000) if trial_days > 0 else None
        }
        
        organization_id = db_client.create_organization(org_data)
        results['organization_id'] = organization_id
        logger.info(f"Created organization: {organization_id}")
        
        # Step 3: Create Stripe customer (if requested)
        if create_stripe and billing_client:
            logger.info("Creating Stripe customer...")
            try:
                stripe_customer = billing_client.create_customer(
                    email=admin_email,  # Use admin email for billing
                    organization_name=org_name,
                    organization_id=organization_id,
                    metadata={
                        'subdomain': subdomain,
                        'tier': tier
                    }
                )
                results['stripe_customer_id'] = stripe_customer['id']
                
                # Update organization with Stripe customer ID
                db_client.update_organization(organization_id, {
                    'stripe_customer_id': stripe_customer['id']
                })
                
                logger.info(f"Created Stripe customer: {stripe_customer['id']}")
            except Exception as e:
                logger.error(f"Failed to create Stripe customer: {str(e)}")
                # Continue with onboarding even if Stripe fails
                results['error'] = f"Stripe customer creation failed: {str(e)}"
        
        # Step 4: Create admin user in Cognito
        logger.info("Creating admin user in Cognito...")
        try:
            user_result = auth_client.create_user(
                email=admin_email,
                organization_id=organization_id,
                role='admin'
            )
            results['admin_user_created'] = True
            results['temporary_password'] = user_result['temporary_password']
            logger.info(f"Created Cognito user: {admin_email}")
        except ValueError as e:
            if "already exists" in str(e):
                logger.warning(f"User {admin_email} already exists in Cognito")
                results['admin_user_created'] = True
                results['temporary_password'] = None
            else:
                raise
        
        # Step 5: Create user record in DynamoDB
        logger.info("Creating user record in DynamoDB...")
        db_client.create_user({
            'user_email': admin_email,
            'organization_id': organization_id,
            'role': 'admin',
            'name': admin_name,
            'cognito_user_id': admin_email  # Cognito uses email as username
        })
        
        # Step 6: Send welcome email (placeholder - implement with SES)
        logger.info("Sending welcome email...")
        send_welcome_email(
            admin_email=admin_email,
            admin_name=admin_name,
            org_name=org_name,
            organization_id=organization_id,
            subdomain=subdomain,
            email_address=email,
            temporary_password=results['temporary_password'],
            tier=tier,
            trial_days=trial_days
        )
        
        logger.info(f"Successfully onboarded organization: {organization_id}")
        return results
        
    except Exception as e:
        logger.error(f"Onboarding failed: {str(e)}", exc_info=True)
        results['error'] = str(e)
        
        # Cleanup on failure (best effort)
        if results['organization_id']:
            logger.warning(f"Onboarding failed. Organization {results['organization_id']} may need manual cleanup.")
        
        raise


def send_welcome_email(admin_email: str, admin_name: str, org_name: str,
                      organization_id: str, subdomain: str, email_address: str,
                      temporary_password: str, tier: str, trial_days: int):
    """Send welcome email to new organization admin.
    
    Args:
        admin_email: Admin email address
        admin_name: Admin name
        org_name: Organization name
        organization_id: Organization ID
        subdomain: Organization subdomain
        email_address: Organization email for forwarding
        temporary_password: Temporary Cognito password
        tier: Subscription tier
        trial_days: Trial period days
    """
    # This is a placeholder - implement actual SES email sending
    logger.info(f"Welcome email details for {admin_email}:")
    logger.info(f"  Organization: {org_name} ({organization_id})")
    logger.info(f"  Email address: {email_address}")
    logger.info(f"  Subdomain: {subdomain}")
    logger.info(f"  Tier: {tier}")
    logger.info(f"  Trial: {trial_days} days")
    
    if temporary_password:
        logger.info(f"  Temporary password: {temporary_password}")
        logger.warning("IMPORTANT: Send this password securely to the user!")
    
    # TODO: Implement actual SES email
    # Example email content:
    email_content = f"""
    Welcome to Project Tracker!
    
    Hi {admin_name},
    
    Your organization "{org_name}" has been set up successfully!
    
    Getting Started:
    1. Log in at: https://app.myprojectr.com
    2. Use your email: {admin_email}
    3. Temporary password: {temporary_password}
       (You'll be prompted to change this on first login)
    
    Your Organization Details:
    - Organization ID: {organization_id}
    - Email for forwarding: {email_address}
    - Subdomain: {subdomain}
    - Subscription: {tier} tier
    - Trial period: {trial_days} days
    
    How to Use:
    1. Forward any project-related emails to {email_address}
    2. Our AI will automatically extract and organize project information
    3. View everything in your dashboard at app.myprojectr.com
    
    Need Help?
    - Documentation: https://docs.myprojectr.com
    - Support: support@myprojectr.com
    
    Best regards,
    The Project Tracker Team
    """
    
    logger.info("Welcome email content prepared (not sent - implement SES integration)")


def main():
    """Main entry point for client onboarding script."""
    parser = argparse.ArgumentParser(description='Onboard a new client organization')
    
    parser.add_argument('--org-name', required=True, help='Organization name (e.g., "ACME Construction")')
    parser.add_argument('--email', required=True, help='Organization email (e.g., "acme@myprojectr.com")')
    parser.add_argument('--subdomain', required=True, help='Subdomain identifier (e.g., "acme")')
    parser.add_argument('--admin-email', required=True, help='Admin user email')
    parser.add_argument('--admin-name', required=True, help='Admin user name')
    parser.add_argument('--tier', default='starter', choices=['starter', 'professional', 'enterprise'],
                       help='Subscription tier (default: starter)')
    parser.add_argument('--create-stripe-customer', action='store_true',
                       help='Create Stripe customer during onboarding')
    parser.add_argument('--trial-days', type=int, default=14, help='Trial period in days (default: 14)')
    
    args = parser.parse_args()
    
    # Validate email format
    if not args.email.endswith('@myprojectr.com'):
        logger.error("Organization email must end with @myprojectr.com")
        sys.exit(1)
    
    # Validate subdomain format
    if not args.subdomain.isalnum() or len(args.subdomain) < 3:
        logger.error("Subdomain must be alphanumeric and at least 3 characters")
        sys.exit(1)
    
    try:
        results = onboard_client(
            org_name=args.org_name,
            email=args.email,
            subdomain=args.subdomain,
            admin_email=args.admin_email,
            admin_name=args.admin_name,
            tier=args.tier,
            create_stripe=args.create_stripe_customer,
            trial_days=args.trial_days
        )
        
        # Print success summary
        print("\n" + "="*60)
        print("CLIENT ONBOARDING SUCCESSFUL!")
        print("="*60)
        print(f"Organization ID: {results['organization_id']}")
        print(f"Organization Email: {args.email}")
        print(f"Admin Email: {args.admin_email}")
        
        if results['temporary_password']:
            print(f"\n⚠️  TEMPORARY PASSWORD: {results['temporary_password']}")
            print("    Send this securely to the admin user!")
        
        if results['stripe_customer_id']:
            print(f"\nStripe Customer ID: {results['stripe_customer_id']}")
        
        if results['error']:
            print(f"\n⚠️  Warning: {results['error']}")
        
        print("\nNext Steps:")
        print(f"1. Admin logs in at: https://app.myprojectr.com")
        print(f"2. Emails can be forwarded to: {args.email}")
        print(f"3. Dashboard available after first login")
        print("="*60 + "\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print("CLIENT ONBOARDING FAILED!")
        print("="*60)
        print(f"Error: {str(e)}")
        print("\nPlease check the logs for more details.")
        print("="*60 + "\n")
        sys.exit(1)


# Import for datetime
from datetime import datetime, timedelta


if __name__ == '__main__':
    main()

