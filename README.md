# Email-Based AI Project Tracking System

An intelligent email-based project tracking system for construction subcontractors, built on AWS serverless architecture.

## Overview

This system allows construction subcontractors to:
1. Forward project-related emails to an AI agent that extracts key information, fills forms, and generates estimates
2. Automatically track project decisions, timelines, and dependencies through email analysis

## Architecture

**Email Flow**: SES → S3 → SNS → SQS → Lambda → AI (OpenAI) → DynamoDB → SES Reply

**Key Technologies**:
- AWS Services: SES, Lambda, S3, DynamoDB, SQS, SNS, Secrets Manager, CloudWatch
- Python 3.11
- OpenAI API (GPT-4o-mini for extraction, GPT-4o for estimates)
- Docker & LocalStack (for local development)

## Prerequisites

### Required Tools
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (for Windows)
- [Python 3.11](https://www.python.org/downloads/)
- [AWS CLI v2](https://aws.amazon.com/cli/)
- AWS Account with IAM credentials
- OpenAI API Account

### AWS Setup Steps

**IMPORTANT**: Complete these steps before deploying to AWS.

#### 1. AWS Account & Security Setup

```bash
# After creating AWS account at aws.amazon.com:

# Enable MFA on root account (AWS Console → Security Credentials)
# Create IAM admin user (IAM Console → Users → Add User)
# Enable CloudTrail (CloudTrail Console → Create Trail)
# Set up billing alerts (Billing → Budgets → Create Budget)
```

#### 2. Configure AWS CLI

```bash
aws configure
# Enter:
#   AWS Access Key ID: [from IAM user]
#   AWS Secret Access Key: [from IAM user]
#   Default region: us-east-1
#   Default output format: json
```

#### 3. Domain Registration

1. Navigate to Route 53 in AWS Console
2. Register Domain → Choose `.com` domain (~$12-15/year)
3. Enable privacy protection
4. Wait 24-48 hours for registration

#### 4. SES Setup (After Domain Registration)

```bash
# 1. Verify your domain in SES (us-east-1 region)
# 2. Add DNS records (DKIM, MX, TXT) to Route 53
# 3. Wait for verification (5-30 minutes)
# 4. Request production access (explain your use case)
```

## Local Development Setup

### 1. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Start LocalStack (AWS Emulator)

```bash
# Start LocalStack services
docker-compose up -d

# Verify it's running
docker-compose ps

# View logs
docker-compose logs -f localstack
```

### 3. Set Up Local Environment Variables

```bash
# Copy example env file
copy .env.example .env

# Edit .env and add:
# - OpenAI API key
# - AWS credentials (for LocalStack)
# - Your domain name
```

### 4. Initialize Local AWS Resources

```bash
# Create local DynamoDB tables, S3 buckets, etc.
python scripts/setup_local_resources.py
```

## Project Structure

```
project/
├── infrastructure/              # Infrastructure as Code
│   ├── template.yaml           # AWS SAM template
│   ├── create_tables.py        # DynamoDB table creation
│   └── policies/               # IAM policies
├── src/
│   ├── lambdas/
│   │   ├── email_processor/    # Main email ingestion
│   │   ├── ai_orchestrator/    # AI analysis logic
│   │   └── reply_sender/       # Email reply sender
│   ├── shared/                 # Shared utilities
│   │   ├── db_client.py        # DynamoDB helpers
│   │   ├── s3_client.py        # S3 operations
│   │   ├── ai_client.py        # OpenAI wrapper
│   │   └── email_parser.py     # Email parsing
│   └── parsers/                # Document parsers
│       ├── pdf_parser.py
│       ├── docx_parser.py
│       └── image_parser.py
├── tests/                      # Unit & integration tests
├── scripts/                    # Utility scripts
├── docker-compose.yml          # LocalStack configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Testing

### Local Testing with LocalStack

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_email_processor.py -v

# Test email processing end-to-end locally
python scripts/test_email_flow.py
```

### Manual Testing

```bash
# Send test email to local SES
python scripts/send_test_email.py

# Check processing results
python scripts/check_dynamodb.py
```

## Deployment

### Deploy to AWS

```bash
# Build Lambda packages
python scripts/build_lambdas.py

# Deploy infrastructure using AWS SAM
cd infrastructure
sam build
sam deploy --guided

# Or use the deployment script
python scripts/deploy.py --environment production
```

### Post-Deployment Setup

```bash
# Store OpenAI API key in Secrets Manager
aws secretsmanager create-secret \
    --name openai-api-key \
    --secret-string '{"api_key":"sk-your-key-here"}' \
    --region us-east-1

# Configure SES receiving rules
python scripts/configure_ses.py --domain your-domain.com

# Set up CloudWatch alarms
python scripts/setup_monitoring.py
```

## Configuration

### Environment Variables

- `AWS_REGION`: AWS region (default: us-east-1)
- `ENVIRONMENT`: dev/staging/production
- `OPENAI_API_KEY_SECRET`: Secrets Manager secret name
- `PROJECT_DOMAIN`: Your registered domain
- `EMAIL_BUCKET`: S3 bucket for email storage
- `PROJECTS_TABLE`: DynamoDB projects table name
- `EVENTS_TABLE`: DynamoDB events table name

### Security Configuration

All sensitive data is encrypted:
- **At Rest**: S3 (SSE-S3), DynamoDB (AWS-managed), Secrets Manager (KMS)
- **In Transit**: TLS 1.2+ for all connections
- **Access Control**: Least-privilege IAM roles
- **Audit Logging**: CloudTrail enabled for all API calls

## Monitoring & Logging

### CloudWatch Dashboards
- Email processing rate
- Lambda execution duration
- Error rates
- DynamoDB capacity usage
- Daily costs

### Alarms
- Lambda errors > 5%
- SQS Dead Letter Queue messages > 0
- Daily cost > $10

Access dashboards: AWS Console → CloudWatch → Dashboards

## Cost Estimates

### AWS Free Tier (First 12 Months)
- Lambda: 1M requests/month
- DynamoDB: 25GB storage
- S3: 5GB storage
- SES: Receiving is free

### Estimated Monthly Costs
- **Low usage** (100 emails/day): $10-20/month
- **Medium usage** (500 emails/day): $30-50/month
- **High usage** (1000 emails/day): $50-100/month

Primary costs: OpenAI API usage, DynamoDB, S3 storage

## Security Best Practices

1. **Never commit credentials** - Use `.env` (gitignored) and Secrets Manager
2. **Enable MFA** - On all AWS accounts
3. **Use IAM roles** - No long-lived access keys in production
4. **Encrypt everything** - At rest and in transit
5. **Monitor access** - CloudTrail and CloudWatch logs
6. **Regular updates** - Keep dependencies updated
7. **Input validation** - Sanitize all inputs to prevent injection

## Troubleshooting

### LocalStack Issues
```bash
# Reset LocalStack
docker-compose down -v
docker-compose up -d
python scripts/setup_local_resources.py
```

### Lambda Deployment Issues
```bash
# Check Lambda logs
aws logs tail /aws/lambda/email-processor --follow

# Test Lambda directly
aws lambda invoke \
    --function-name email-processor \
    --payload file://tests/fixtures/test_event.json \
    response.json
```

### SES Issues
- Ensure domain is verified in SES Console
- Check DNS records in Route 53
- Verify you're in us-east-1 region (SES receiving limitation)
- Check SES sending limits (sandbox vs production)

## Support & Documentation

- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LocalStack Documentation](https://docs.localstack.cloud/)

## License

Proprietary - All rights reserved

## Contact

For support, contact: [your-email@domain.com]

