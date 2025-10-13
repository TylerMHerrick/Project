"""
Deployment script for AWS SAM.
Builds and deploys the Lambda functions and infrastructure.
"""
import subprocess
import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from shared.logger import setup_logger

logger = setup_logger(__name__)


def run_command(command, cwd=None):
    """Run a shell command and log output."""
    logger.info(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.info(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if e.stderr:
            logger.error(e.stderr)
        raise


def install_dependencies():
    """Install Python dependencies for Lambda layers."""
    logger.info("Installing dependencies...")
    
    # Install shared dependencies
    run_command('pip install -r requirements.txt -t src/shared/lib/python3.11/site-packages/')
    
    logger.info("Dependencies installed")


def build_sam():
    """Build SAM application."""
    logger.info("Building SAM application...")
    
    infrastructure_dir = os.path.join(os.path.dirname(__file__), '../infrastructure')
    run_command('sam build', cwd=infrastructure_dir)
    
    logger.info("SAM build complete")


def deploy_sam(environment, domain, guided=False):
    """Deploy SAM application to AWS."""
    logger.info(f"Deploying to {environment} environment...")
    
    infrastructure_dir = os.path.join(os.path.dirname(__file__), '../infrastructure')
    
    if guided:
        # Interactive guided deployment
        run_command('sam deploy --guided', cwd=infrastructure_dir)
    else:
        # Automated deployment with parameters
        cmd = f"""sam deploy \
            --stack-name project-tracker-{environment} \
            --parameter-overrides Environment={environment} ProjectDomain={domain} \
            --capabilities CAPABILITY_IAM \
            --no-fail-on-empty-changeset \
            --resolve-s3
        """
        run_command(cmd, cwd=infrastructure_dir)
    
    logger.info("Deployment complete")


def validate_template():
    """Validate SAM template."""
    logger.info("Validating SAM template...")
    
    infrastructure_dir = os.path.join(os.path.dirname(__file__), '../infrastructure')
    run_command('sam validate', cwd=infrastructure_dir)
    
    logger.info("Template validation successful")


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description='Deploy Email AI Project Tracker')
    parser.add_argument(
        '--environment',
        choices=['dev', 'staging', 'prod'],
        default='dev',
        help='Deployment environment'
    )
    parser.add_argument(
        '--domain',
        required=True,
        help='Project domain name'
    )
    parser.add_argument(
        '--guided',
        action='store_true',
        help='Use guided deployment'
    )
    parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Skip the build step'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate the template'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Email AI Project Tracker - Deployment")
    logger.info("=" * 60)
    logger.info(f"Environment: {args.environment}")
    logger.info(f"Domain: {args.domain}")
    
    try:
        # Validate template
        validate_template()
        
        if args.validate_only:
            logger.info("Validation complete. Exiting.")
            return
        
        # Build
        if not args.skip_build:
            build_sam()
        else:
            logger.info("Skipping build step")
        
        # Deploy
        deploy_sam(args.environment, args.domain, args.guided)
        
        logger.info("=" * 60)
        logger.info("Deployment successful!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Configure SES receiving rules in AWS Console")
        logger.info("2. Store OpenAI API key in Secrets Manager")
        logger.info("3. Request SES production access if not already done")
        logger.info("4. Test email flow with a verified email address")
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

