"""
Script to configure SES receiving rules.
Run this after deploying infrastructure to set up email receiving.
"""
import boto3
import argparse
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.logger import setup_logger

logger = setup_logger(__name__)


def verify_domain(domain):
    """Verify domain in SES."""
    ses = boto3.client('ses', region_name='us-east-1')  # SES receiving requires us-east-1
    
    try:
        response = ses.verify_domain_identity(Domain=domain)
        verification_token = response['VerificationToken']
        
        logger.info(f"Domain verification initiated for: {domain}")
        logger.info(f"Verification token: {verification_token}")
        logger.info("\nAdd this TXT record to your DNS:")
        logger.info(f"  Name: _amazonses.{domain}")
        logger.info(f"  Type: TXT")
        logger.info(f"  Value: {verification_token}")
        
        return verification_token
        
    except Exception as e:
        logger.error(f"Failed to verify domain: {str(e)}")
        raise


def configure_dkim(domain):
    """Configure DKIM for domain."""
    ses = boto3.client('ses', region_name='us-east-1')
    
    try:
        response = ses.verify_domain_dkim(Domain=domain)
        dkim_tokens = response['DkimTokens']
        
        logger.info(f"\nDKIM configuration for: {domain}")
        logger.info("Add these CNAME records to your DNS:")
        
        for i, token in enumerate(dkim_tokens, 1):
            logger.info(f"\nRecord {i}:")
            logger.info(f"  Name: {token}._domainkey.{domain}")
            logger.info(f"  Type: CNAME")
            logger.info(f"  Value: {token}.dkim.amazonses.com")
        
        return dkim_tokens
        
    except Exception as e:
        logger.error(f"Failed to configure DKIM: {str(e)}")
        raise


def create_receipt_rule_set(domain, bucket_name, topic_arn):
    """Create SES receipt rule set."""
    ses = boto3.client('ses', region_name='us-east-1')
    
    rule_set_name = 'project-tracker-rules'
    
    try:
        # Create rule set if it doesn't exist
        try:
            ses.create_receipt_rule_set(RuleSetName=rule_set_name)
            logger.info(f"Created receipt rule set: {rule_set_name}")
        except ses.exceptions.AlreadyExistsException:
            logger.info(f"Receipt rule set already exists: {rule_set_name}")
        
        # Create receipt rule
        rule_name = 'store-and-notify'
        
        rule = {
            'Name': rule_name,
            'Enabled': True,
            'TlsPolicy': 'Require',  # Security: require TLS
            'Recipients': [
                f'project@{domain}',
                f'project+*@{domain}'  # Support project+ID@domain addressing
            ],
            'Actions': [
                {
                    'S3Action': {
                        'BucketName': bucket_name,
                        'ObjectKeyPrefix': 'emails/'
                    }
                },
                {
                    'SNSAction': {
                        'TopicArn': topic_arn,
                        'Encoding': 'UTF-8'
                    }
                }
            ],
            'ScanEnabled': True  # Enable spam and virus scanning
        }
        
        try:
            ses.create_receipt_rule(
                RuleSetName=rule_set_name,
                Rule=rule
            )
            logger.info(f"Created receipt rule: {rule_name}")
        except ses.exceptions.AlreadyExistsException:
            # Update existing rule
            ses.update_receipt_rule(
                RuleSetName=rule_set_name,
                Rule=rule
            )
            logger.info(f"Updated receipt rule: {rule_name}")
        
        # Set as active rule set
        ses.set_active_receipt_rule_set(RuleSetName=rule_set_name)
        logger.info(f"Activated receipt rule set: {rule_set_name}")
        
        # Add MX record instructions
        logger.info(f"\nAdd this MX record to your DNS for {domain}:")
        logger.info(f"  Name: {domain}")
        logger.info(f"  Type: MX")
        logger.info(f"  Priority: 10")
        logger.info(f"  Value: inbound-smtp.us-east-1.amazonaws.com")
        
    except Exception as e:
        logger.error(f"Failed to create receipt rule: {str(e)}")
        raise


def check_verification_status(domain):
    """Check domain verification status."""
    ses = boto3.client('ses', region_name='us-east-1')
    
    try:
        response = ses.get_identity_verification_attributes(Identities=[domain])
        
        if domain in response['VerificationAttributes']:
            status = response['VerificationAttributes'][domain]['VerificationStatus']
            logger.info(f"Domain verification status: {status}")
            return status
        else:
            logger.warning(f"Domain {domain} not found in SES")
            return None
            
    except Exception as e:
        logger.error(f"Failed to check verification status: {str(e)}")
        raise


def main():
    """Main SES configuration function."""
    parser = argparse.ArgumentParser(description='Configure SES for email receiving')
    parser.add_argument(
        '--domain',
        required=True,
        help='Domain name to configure'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='S3 bucket name for email storage'
    )
    parser.add_argument(
        '--topic-arn',
        required=True,
        help='SNS topic ARN for notifications'
    )
    parser.add_argument(
        '--skip-verification',
        action='store_true',
        help='Skip domain verification step'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("SES Configuration")
    logger.info("=" * 60)
    logger.info(f"Domain: {args.domain}")
    logger.info(f"Bucket: {args.bucket}")
    logger.info(f"Topic ARN: {args.topic_arn}")
    
    try:
        if not args.skip_verification:
            # Verify domain
            logger.info("\n--- Domain Verification ---")
            verify_domain(args.domain)
            
            # Configure DKIM
            logger.info("\n--- DKIM Configuration ---")
            configure_dkim(args.domain)
            
            # Check status
            logger.info("\n--- Verification Status ---")
            status = check_verification_status(args.domain)
            
            if status != 'Success':
                logger.warning("\nDomain not yet verified. Complete DNS configuration and wait for verification.")
                logger.warning("Run this script again with --skip-verification after domain is verified.")
                return
        
        # Create receipt rules
        logger.info("\n--- Receipt Rules ---")
        create_receipt_rule_set(args.domain, args.bucket, args.topic_arn)
        
        logger.info("\n" + "=" * 60)
        logger.info("SES configuration complete!")
        logger.info("=" * 60)
        logger.info("\nYou can now receive emails at:")
        logger.info(f"  - project@{args.domain}")
        logger.info(f"  - project+[project-id]@{args.domain}")
        
    except Exception as e:
        logger.error(f"Configuration failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

