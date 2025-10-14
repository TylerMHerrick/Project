"""Billing client for Stripe integration."""
import stripe
import boto3
import json
from typing import Dict, Optional, Any, List
from datetime import datetime
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)


# Subscription tier configurations
SUBSCRIPTION_TIERS = {
    'starter': {
        'name': 'Starter',
        'price_monthly': 49.00,
        'email_limit': 500,
        'project_limit': 2,
        'api_budget': 20.00,
        'user_limit': 1,
        'features': [
            'Email processing',
            'AI extraction',
            'Basic timeline',
            'Email support'
        ]
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': 149.00,
        'email_limit': 2000,
        'project_limit': None,  # Unlimited
        'api_budget': 100.00,
        'user_limit': 5,
        'features': [
            'Everything in Starter',
            'Unlimited projects',
            'Advanced analytics',
            'Priority support',
            'Custom integrations'
        ]
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': None,  # Custom pricing
        'email_limit': None,  # Unlimited
        'project_limit': None,  # Unlimited
        'api_budget': None,  # Custom
        'user_limit': None,  # Unlimited
        'features': [
            'Everything in Professional',
            'Dedicated support',
            'Custom AI models',
            'SLA guarantee',
            'On-premise deployment option'
        ]
    }
}


class BillingClient:
    """Wrapper for Stripe billing operations."""
    
    def __init__(self):
        """Initialize Stripe client."""
        self.api_key = self._get_stripe_api_key()
        stripe.api_key = self.api_key
    
    def _get_stripe_api_key(self) -> str:
        """Get Stripe API key from Secrets Manager.
        
        Returns:
            Stripe API key
        """
        import os
        # Check environment variable first (for local dev)
        if os.environ.get('STRIPE_API_KEY'):
            return os.environ.get('STRIPE_API_KEY')
        
        # Get from AWS Secrets Manager for production
        try:
            secrets_client = boto3.client('secretsmanager', **Config.get_boto3_config())
            response = secrets_client.get_secret_value(SecretId='stripe-api-key')
            secret_data = json.loads(response['SecretString'])
            return secret_data['api_key']
        except Exception as e:
            logger.error(f"Failed to retrieve Stripe API key: {str(e)}")
            logger.warning("Using test mode Stripe key")
            return "sk_test_dummy"
    
    def create_customer(self, email: str, organization_name: str, 
                       organization_id: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a Stripe customer.
        
        Args:
            email: Customer email
            organization_name: Organization name
            organization_id: Organization ID
            metadata: Additional metadata
            
        Returns:
            Stripe customer object
        """
        try:
            customer_metadata = {
                'organization_id': organization_id,
                'organization_name': organization_name,
                **(metadata or {})
            }
            
            customer = stripe.Customer.create(
                email=email,
                name=organization_name,
                metadata=customer_metadata
            )
            
            logger.info(f"Created Stripe customer for organization: {organization_id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise
    
    def create_subscription(self, customer_id: str, price_id: str, 
                          trial_days: int = 14) -> Dict[str, Any]:
        """Create a subscription for a customer.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Number of trial days
            
        Returns:
            Stripe subscription object
        """
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_period_days=trial_days,
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent']
            )
            
            logger.info(f"Created subscription for customer: {customer_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise
    
    def cancel_subscription(self, subscription_id: str, 
                           cancel_at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            cancel_at_period_end: If True, cancel at end of billing period
            
        Returns:
            Updated subscription object
        """
        try:
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Canceled subscription: {subscription_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            raise
    
    def update_subscription(self, subscription_id: str, new_price_id: str) -> Dict[str, Any]:
        """Update subscription to a different price/tier.
        
        Args:
            subscription_id: Stripe subscription ID
            new_price_id: New Stripe price ID
            
        Returns:
            Updated subscription object
        """
        try:
            # Get current subscription
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Update subscription item with new price
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations'
            )
            
            logger.info(f"Updated subscription {subscription_id} to new price: {new_price_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            raise
    
    def create_checkout_session(self, customer_id: str, price_id: str, 
                               success_url: str, cancel_url: str) -> Dict[str, Any]:
        """Create a Stripe Checkout session.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            
        Returns:
            Checkout session object
        """
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                subscription_data={
                    'trial_period_days': 14
                }
            )
            
            logger.info(f"Created checkout session for customer: {customer_id}")
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {str(e)}")
            raise
    
    def create_billing_portal_session(self, customer_id: str, 
                                     return_url: str) -> Dict[str, Any]:
        """Create a Stripe billing portal session.
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session
            
        Returns:
            Billing portal session object
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            
            logger.info(f"Created billing portal session for customer: {customer_id}")
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create billing portal session: {str(e)}")
            raise
    
    def record_usage(self, subscription_item_id: str, quantity: int, 
                    timestamp: Optional[int] = None) -> Dict[str, Any]:
        """Record usage for metered billing.
        
        Args:
            subscription_item_id: Stripe subscription item ID
            quantity: Usage quantity
            timestamp: Unix timestamp (defaults to now)
            
        Returns:
            Usage record object
        """
        try:
            usage_record = stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                quantity=quantity,
                timestamp=timestamp or int(datetime.now().timestamp()),
                action='set'  # 'set' replaces value, 'increment' adds to it
            )
            
            logger.info(f"Recorded usage: {quantity} for subscription item: {subscription_item_id}")
            return usage_record
        except stripe.error.StripeError as e:
            logger.error(f"Failed to record usage: {str(e)}")
            raise
    
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve a Stripe customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Customer object
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve customer: {str(e)}")
            raise
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Retrieve a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Subscription object
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription: {str(e)}")
            raise
    
    def list_invoices(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List invoices for a customer.
        
        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoice objects
        """
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            return invoices.data
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list invoices: {str(e)}")
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str, 
                                 webhook_secret: str) -> Dict[str, Any]:
        """Verify Stripe webhook signature and parse event.
        
        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value
            webhook_secret: Webhook endpoint secret
            
        Returns:
            Parsed event object
            
        Raises:
            stripe.error.SignatureVerificationError: If signature is invalid
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            raise
    
    @staticmethod
    def get_tier_config(tier_name: str) -> Dict[str, Any]:
        """Get configuration for a subscription tier.
        
        Args:
            tier_name: Tier name (starter, professional, enterprise)
            
        Returns:
            Tier configuration
        """
        return SUBSCRIPTION_TIERS.get(tier_name.lower(), SUBSCRIPTION_TIERS['starter'])
    
    @staticmethod
    def check_usage_limits(tier_name: str, email_count: int, project_count: int, 
                          api_spend: float) -> Dict[str, bool]:
        """Check if usage is within tier limits.
        
        Args:
            tier_name: Tier name
            email_count: Number of emails processed
            project_count: Number of projects
            api_spend: API spending in USD
            
        Returns:
            Dictionary with limit check results
        """
        tier = SUBSCRIPTION_TIERS.get(tier_name.lower(), SUBSCRIPTION_TIERS['starter'])
        
        return {
            'email_limit_exceeded': tier['email_limit'] is not None and email_count > tier['email_limit'],
            'project_limit_exceeded': tier['project_limit'] is not None and project_count > tier['project_limit'],
            'api_budget_exceeded': tier['api_budget'] is not None and api_spend > tier['api_budget'],
            'email_count': email_count,
            'email_limit': tier['email_limit'],
            'project_count': project_count,
            'project_limit': tier['project_limit'],
            'api_spend': api_spend,
            'api_budget': tier['api_budget']
        }

