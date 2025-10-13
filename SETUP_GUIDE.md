# Email AI Project Tracker - Setup Guide

This guide walks you through setting up the Email-based AI Project Tracking system from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Domain Registration](#domain-registration)
4. [Local Development Setup](#local-development-setup)
5. [AWS Deployment](#aws-deployment)
6. [SES Configuration](#ses-configuration)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

Install these on your Windows machine:

1. **Docker Desktop**
   - Download from: https://www.docker.com/products/docker-desktop
   - Requires Windows 10/11 Pro or Enterprise with WSL 2
   - After installation, verify: `docker --version`

2. **Python 3.11**
   - Download from: https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"
   - Verify: `python --version`

3. **AWS CLI v2**
   - Download from: https://awscli.amazonaws.com/AWSCLIV2.msi
   - Run the installer
   - Verify: `aws --version`

4. **Git** (optional, but recommended)
   - Download from: https://git-scm.com/download/win
   - Verify: `git --version`

### Required Accounts

1. **AWS Account**
   - Sign up at: https://aws.amazon.com/
   - Requires credit card (but we'll stay in free tier)

2. **OpenAI Account**
   - Sign up at: https://platform.openai.com/signup
   - Add payment method to get API access
   - Generate API key from: https://platform.openai.com/api-keys

---

## AWS Account Setup

### Step 1: Secure Your Root Account

1. Log in to AWS Console: https://console.aws.amazon.com/
2. Navigate to: IAM → Dashboard
3. Enable MFA on root account:
   - Click "Add MFA" next to root user
   - Use Google Authenticator or Authy app
   - **IMPORTANT**: Save backup codes in a secure location

### Step 2: Create IAM Admin User

1. Go to: IAM → Users → Add User
2. User name: `admin-user`
3. Select: "Provide user access to the AWS Management Console"
4. Create a strong password
5. Attach policy: `AdministratorAccess`
6. Create user and **save the credentials**

### Step 3: Generate Access Keys

1. Click on the newly created user
2. Go to "Security credentials" tab
3. Create access key → Choose "CLI"
4. Download or copy:
   - Access Key ID
   - Secret Access Key
5. **Store these securely** - you'll need them soon

### Step 4: Configure AWS CLI

Open PowerShell and run:

```powershell
aws configure
```

Enter:
- AWS Access Key ID: [your key]
- AWS Secret Access Key: [your secret]
- Default region: `us-east-1`
- Default output format: `json`

Verify:
```powershell
aws sts get-caller-identity
```

### Step 5: Enable CloudTrail

1. Go to: CloudTrail → Trails → Create trail
2. Trail name: `project-tracker-audit`
3. Storage location: Create new S3 bucket
4. Leave other settings as default
5. Create trail

### Step 6: Set Up Billing Alerts

1. Go to: Billing → Budgets → Create budget
2. Choose: Zero spend budget (free tier)
3. Add email for notifications
4. Create additional budgets:
   - $5 threshold
   - $10 threshold
   - $20 threshold

---

## Domain Registration

### Step 1: Choose a Domain

Think of a professional domain name for your business:
- Examples: `projecttrack.com`, `builderpm.com`, `tradehub.com`
- Keep it short and memorable
- `.com` is recommended (~$12-15/year)

### Step 2: Register via Route 53

1. Go to: Route 53 → Registered domains → Register domain
2. Search for your desired domain
3. Add to cart and proceed
4. Fill in contact information
5. **Enable privacy protection** (included free)
6. Enable auto-renewal
7. Complete purchase

**Note**: Domain registration takes 24-48 hours to complete.

### Step 3: Verify Hosted Zone

After registration:
1. Go to: Route 53 → Hosted zones
2. You should see your domain listed
3. Note the 4 nameserver (NS) records
4. These are already configured by Route 53

---

## Local Development Setup

### Step 1: Clone/Create Project Directory

```powershell
# Navigate to your projects folder
cd C:\Users\[YourUsername]\Projects

# If using git:
git clone [your-repo-url] email-ai-tracker
cd email-ai-tracker

# Or create from scratch - all files are already created by the implementation
```

### Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Install Dependencies

```powershell
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Step 4: Create Environment File

Create a `.env` file in the project root:

```powershell
# Copy the example
copy .env.example .env

# Edit .env with your favorite text editor
notepad .env
```

Update these values in `.env`:
```ini
ENVIRONMENT=dev
AWS_REGION=us-east-1
USE_LOCALSTACK=true
AWS_ENDPOINT_URL=http://localhost:4566

# Your domain
PROJECT_DOMAIN=yourdomain.com
EMAIL_FROM_ADDRESS=project@yourdomain.com

# OpenAI API key (for local testing)
OPENAI_API_KEY=sk-your-key-here

# Leave other values as default for now
```

### Step 5: Start LocalStack

```powershell
# Start LocalStack
docker-compose up -d

# Verify it's running
docker-compose ps

# Check logs
docker-compose logs -f localstack
```

You should see LocalStack services starting. Press Ctrl+C to stop viewing logs.

### Step 6: Set Up Local Resources

```powershell
# Run the setup script
python scripts/setup_local_resources.py
```

This creates:
- S3 bucket for emails
- SNS topic for notifications
- SQS queues for processing
- DynamoDB tables
- Secrets Manager secrets

### Step 7: Run Tests

```powershell
# Run all tests
pytest

# Run specific test file
pytest tests/test_email_parser.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Step 8: Test Email Flow Locally

```powershell
# Send a test email through the system
python scripts/test_email_flow.py
```

This simulates the complete email processing flow locally.

---

## AWS Deployment

### Step 1: Install SAM CLI

```powershell
# Download SAM CLI installer
# Visit: https://aws.amazon.com/serverless/sam/
# Or use Chocolatey:
choco install aws-sam-cli
```

### Step 2: Store OpenAI API Key

```powershell
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret `
    --name openai-api-key `
    --secret-string '{\"api_key\":\"sk-your-actual-key-here\"}' `
    --region us-east-1
```

### Step 3: Deploy Infrastructure

```powershell
# Option 1: Guided deployment (recommended for first time)
cd infrastructure
sam build
sam deploy --guided

# Follow prompts:
# - Stack name: project-tracker-dev
# - AWS Region: us-east-1
# - Parameter Environment: dev
# - Parameter ProjectDomain: yourdomain.com
# - Confirm changes: Y
# - Allow SAM CLI IAM role creation: Y
# - Save arguments to config: Y

# Option 2: Using deployment script
python scripts/deploy.py --domain yourdomain.com --environment dev --guided
```

Deployment takes 5-10 minutes.

### Step 4: Note the Outputs

After deployment, SAM will show outputs:
- EmailBucket: Note the S3 bucket name
- EmailReceivedTopicArn: Note the SNS topic ARN
- EmailQueueUrl: Note the SQS queue URL

**Save these - you'll need them for SES configuration!**

---

## SES Configuration

### Step 1: Verify Domain

```powershell
# Run SES configuration script
python scripts/configure_ses.py `
    --domain yourdomain.com `
    --bucket project-emails-[your-account-id]-dev `
    --topic-arn arn:aws:sns:us-east-1:[account-id]:email-received-dev
```

This will output DNS records you need to add.

### Step 2: Add DNS Records to Route 53

1. Go to: Route 53 → Hosted zones → [yourdomain.com]
2. Add the TXT record for domain verification
3. Add the 3 CNAME records for DKIM
4. Add the MX record for receiving emails

Example MX record:
- Name: yourdomain.com
- Type: MX
- Priority: 10
- Value: inbound-smtp.us-east-1.amazonaws.com

### Step 3: Wait for Verification

```powershell
# Check verification status (wait 5-30 minutes)
aws ses get-identity-verification-attributes `
    --identities yourdomain.com `
    --region us-east-1
```

Look for `"VerificationStatus": "Success"`

### Step 4: Request Production Access

While in SES sandbox, you can only send to verified email addresses.

To send to any email:

1. Go to: SES → Account dashboard (us-east-1)
2. Click "Request production access"
3. Fill out form:
   - Use case: "Project tracking system for construction subcontractors"
   - Website: Your domain
   - Expected volume: Start with 100/day
   - Compliance: Yes (we'll handle bounces/complaints)
4. Submit request

Approval usually takes 24-48 hours.

### Step 5: Verify Your Email (for testing)

While waiting for production access:

1. Go to: SES → Verified identities → Create identity
2. Choose "Email address"
3. Enter your personal email
4. Check your email and click verification link

---

## Testing

### Test 1: Send Email to SES

Send an email from your verified email address to:
```
project@yourdomain.com
```

Subject: "Test - New Project"
Body:
```
Hi,

This is a test for the Main Street Renovation project.

We need the electrical work completed by March 15th.
Budget approved: $50,000

Thanks!
```

### Test 2: Check Processing

1. Go to: CloudWatch → Log groups → `/aws/lambda/email-processor-dev`
2. View latest log stream
3. Look for "Successfully extracted project data"

### Test 3: Check DynamoDB

1. Go to: DynamoDB → Tables → ProjectTracking-Projects-dev
2. Explore items - you should see a project created
3. Check ProjectTracking-Events-dev for the email event

### Test 4: Verify Reply (if configured)

Check your email for a reply from `project@yourdomain.com`

---

## Troubleshooting

### LocalStack Issues

**Problem**: LocalStack won't start

```powershell
# Reset LocalStack
docker-compose down -v
docker-compose up -d
python scripts/setup_local_resources.py
```

**Problem**: Can't connect to LocalStack

- Check if Docker is running: `docker ps`
- Verify LocalStack is up: `docker-compose ps`
- Check endpoint: http://localhost:4566

### AWS Deployment Issues

**Problem**: SAM deployment fails

1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify you're in us-east-1: `aws configure get region`
3. Check CloudFormation events in AWS Console

**Problem**: Lambda timeout errors

- Increase timeout in `template.yaml`
- Check CloudWatch logs for actual errors

### SES Issues

**Problem**: Domain won't verify

- DNS propagation takes time (up to 72 hours, usually 30 minutes)
- Verify DNS records in Route 53 are correct
- Use `nslookup -type=TXT _amazonses.yourdomain.com` to check

**Problem**: Emails not being received

1. Verify MX record: `nslookup -type=MX yourdomain.com`
2. Check SES receipt rules are active
3. Look for emails in S3 bucket
4. Check CloudWatch logs

**Problem**: Sandbox limitations

- You can only send to verified email addresses
- Request production access (takes 24-48 hours)
- Verify your personal email for testing

### Cost Issues

**Problem**: Unexpected costs

1. Check billing dashboard
2. Common culprits:
   - OpenAI API usage (check usage at platform.openai.com)
   - DynamoDB reads/writes (should be minimal)
   - S3 storage (delete old test data)
3. Set up billing alerts if not already done

---

## Next Steps

Once everything is working:

1. **Onboard Your First Client**
   - Have them forward emails to `project@yourdomain.com`
   - Create a unique project ID: `project+PROJ123@yourdomain.com`

2. **Monitor System**
   - Set up CloudWatch dashboards
   - Configure alarms for errors
   - Review costs weekly

3. **Scale Up**
   - Request higher SES sending limits if needed
   - Enable DynamoDB point-in-time recovery for production
   - Set up VPC for Lambdas (enhanced security)

4. **Future Enhancements**
   - Build web dashboard for clients
   - Add estimate generation features
   - Integrate with accounting software

---

## Support

For issues:
1. Check CloudWatch logs first
2. Review this guide's troubleshooting section
3. Check AWS documentation
4. Review project README.md

---

## Cost Summary

**Setup Costs** (one-time):
- Domain registration: $12-15/year
- Everything else: FREE (using free tier)

**Monthly Costs** (estimated):
- Route 53 hosted zone: $0.50
- AWS services (low usage): $0-5
- OpenAI API: $5-20 (depends on usage)
- **Total: $10-30/month** for first few clients

**Scaling** (per 1000 emails/day):
- AWS: $50-100/month
- OpenAI: $50-200/month (depends on features used)

