# Quick Start Guide

Get up and running in 15 minutes (local development) or 1 hour (AWS deployment).

## Option A: Local Development (Fastest)

Perfect for testing and development without AWS costs.

### Step 1: Install Prerequisites (5 minutes)

```powershell
# Check if you have Docker
docker --version

# Check if you have Python 3.11
python --version

# If missing, download from:
# Docker: https://www.docker.com/products/docker-desktop
# Python: https://www.python.org/downloads/
```

### Step 2: Set Up Project (5 minutes)

```powershell
# Navigate to project directory
cd C:\Users\[YourName]\OneDrive\Herrick Technologies\Project

# Create virtual environment
python -m venv venv

# Activate it (PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 3: Configure Environment (2 minutes)

```powershell
# Copy environment template
copy .env.example .env

# Edit .env file
notepad .env
```

**Minimum required changes in `.env`**:
```ini
# Get your OpenAI key from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-actual-key-here

# Everything else can stay as default for local testing
```

### Step 4: Start LocalStack (2 minutes)

```powershell
# Start LocalStack (simulates AWS locally)
docker-compose up -d

# Verify it's running
docker-compose ps
# Should show localstack container running
```

### Step 5: Create Local Resources (1 minute)

```powershell
# Creates S3 buckets, DynamoDB tables, SQS queues, etc.
python scripts/setup_local_resources.py
```

You should see:
```
Created S3 bucket: project-emails-dev
Created SNS topic: arn:aws:sns:...
Created SQS queue: http://localhost:4566/...
Creating table: ProjectTracking-Projects-dev
LocalStack setup complete!
```

### Step 6: Test It! (1 minute)

```powershell
# Run the test suite
pytest

# Test the email flow
python scripts/test_email_flow.py
```

**Success!** You now have a working local environment.

### What You Can Do Now

- **Modify Lambda code** in `src/lambdas/`
- **Test changes** with `python scripts/test_email_flow.py`
- **Run unit tests** with `pytest`
- **Check logs** with `docker-compose logs -f localstack`

---

## Option B: AWS Deployment (Production)

Deploy to real AWS for production use.

### Prerequisites Checklist

Before starting, ensure you have:

- [ ] AWS Account created
- [ ] Credit card added to AWS
- [ ] OpenAI account with API key
- [ ] Basic understanding of AWS (or willingness to learn!)

### Step 1: AWS Account Setup (20 minutes)

```powershell
# Install AWS CLI (if not already installed)
# Download from: https://awscli.amazonaws.com/AWSCLIV2.msi

# Configure AWS CLI
aws configure

# You'll need:
# - AWS Access Key ID (from IAM user)
# - AWS Secret Access Key (from IAM user)
# - Default region: us-east-1
# - Default output format: json

# Test it works
aws sts get-caller-identity
```

**Important**: 
1. Enable MFA on your root AWS account
2. Create an IAM admin user (don't use root)
3. Enable CloudTrail for audit logging

See **SETUP_GUIDE.md** section 2 for detailed AWS setup.

### Step 2: Register Domain (5 minutes + 24-48hr wait)

```powershell
# Option 1: Via AWS Console (recommended for first time)
# 1. Go to Route 53 → Register Domain
# 2. Search for domain (e.g., yourcompany.com)
# 3. Add to cart ($12-15 for .com)
# 4. Enable privacy protection
# 5. Complete purchase

# Option 2: Via CLI (if you know what you're doing)
aws route53domains register-domain --domain-name yourcompany.com --cli-input-json file://domain-config.json
```

**Note**: Domain registration takes 24-48 hours. Continue with other steps while waiting.

### Step 3: Store Secrets (2 minutes)

```powershell
# Store your OpenAI API key in AWS Secrets Manager
aws secretsmanager create-secret `
    --name openai-api-key `
    --secret-string '{\"api_key\":\"sk-your-actual-key-here\"}' `
    --region us-east-1
```

### Step 4: Deploy Infrastructure (15 minutes)

```powershell
# Navigate to infrastructure directory
cd infrastructure

# Build the SAM application
sam build

# Deploy with guided setup (first time)
sam deploy --guided

# Answer the prompts:
# Stack name: project-tracker-dev
# AWS Region: us-east-1
# Parameter Environment: dev
# Parameter ProjectDomain: yourcompany.com
# Confirm changes: Y
# Allow SAM CLI IAM role creation: Y
# Save arguments to config: Y

# Deployment takes ~10 minutes
# Watch CloudFormation in AWS Console if you want to see progress
```

**Save the outputs!** You'll need:
- EmailBucket
- EmailReceivedTopicArn
- EmailQueueUrl

### Step 5: Configure SES (20 minutes)

```powershell
# Return to project root
cd ..

# Run SES configuration script
python scripts/configure_ses.py `
    --domain yourcompany.com `
    --bucket [EmailBucket-from-step4] `
    --topic-arn [EmailReceivedTopicArn-from-step4]
```

The script will output DNS records. Copy them.

**Add DNS Records to Route 53**:

1. Go to: Route 53 → Hosted Zones → yourcompany.com
2. Click "Create record"
3. Add each record the script gave you:
   - 1 TXT record (domain verification)
   - 3 CNAME records (DKIM)
   - 1 MX record (email receiving)

**Wait for verification** (5-30 minutes):

```powershell
# Check status
aws ses get-identity-verification-attributes `
    --identities yourcompany.com `
    --region us-east-1

# Look for "VerificationStatus": "Success"
```

### Step 6: Request Production Access (5 minutes + 24-48hr wait)

While in SES sandbox, you can only send to verified email addresses.

**Request production access**:
1. Go to: SES Console → Account dashboard
2. Click "Request production access"
3. Fill out the form:
   - Use case: "Project tracking system for construction contractors"
   - Website URL: http://yourcompany.com
   - Expected volume: 100 emails/day
   - Compliance: Yes (we handle bounces)
4. Submit

Approval usually takes 24-48 hours.

**Meanwhile, verify your email** for testing:
1. SES Console → Verified identities → Create identity
2. Choose "Email address"
3. Enter your email
4. Check inbox and click verification link

### Step 7: Test! (5 minutes)

Send an email from your verified email to:
```
project@yourcompany.com
```

Example email:
```
Subject: Test - Main Street Project

Hi,

This is a test for our Main Street Renovation project.

We need electrical work completed by March 15th.
Budget approved: $50,000.

Key decisions:
- Use LED fixtures
- Upgrade to 200A panel

Thanks!
```

**Check Processing**:

1. **S3**: Go to S3 bucket, you should see the email stored
2. **CloudWatch**: Check logs at `/aws/lambda/email-processor-dev`
3. **DynamoDB**: Check `ProjectTracking-Projects-dev` table for new project
4. **Email**: You should receive a reply with extracted information

**Success!** Your system is live.

---

## Troubleshooting Quick Fixes

### "Docker won't start"

```powershell
# Restart Docker Desktop
# Right-click Docker icon in system tray → Restart

# If still failing, reinstall Docker Desktop
```

### "Can't activate virtual environment"

```powershell
# PowerShell execution policy issue
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again
.\venv\Scripts\Activate.ps1
```

### "AWS credentials not found"

```powershell
# Reconfigure AWS CLI
aws configure

# Check if it worked
aws sts get-caller-identity
```

### "LocalStack not responding"

```powershell
# Reset everything
docker-compose down -v
docker-compose up -d

# Wait 30 seconds for startup
timeout /t 30

# Try again
python scripts/setup_local_resources.py
```

### "Domain not verifying"

- DNS can take up to 72 hours (usually 30 minutes)
- Double-check DNS records are correct
- Use `nslookup -type=TXT _amazonses.yourcompany.com` to verify

### "Emails not being received"

1. Check MX record: `nslookup -type=MX yourcompany.com`
2. Verify SES receipt rules are active
3. Look in S3 bucket for emails
4. Check CloudWatch logs for errors

### "High AWS costs"

- Check OpenAI usage at https://platform.openai.com/usage
- Review AWS cost explorer
- Verify no runaway Lambdas in CloudWatch
- Delete old test data from S3

---

## What's Next?

### Learn More

- Read **SETUP_GUIDE.md** for detailed explanations
- Review **ARCHITECTURE.md** to understand the system
- Study **SECURITY.md** for security best practices
- Check **PROJECT_SUMMARY.md** for overview

### Start Using

1. **Forward real emails** to your system
2. **Monitor extraction quality** in DynamoDB
3. **Adjust AI prompts** in `src/shared/ai_client.py` if needed
4. **Set up monitoring dashboards** in CloudWatch

### Extend the System

- Add estimate generation features (Phase 2)
- Build a web dashboard
- Integrate with QuickBooks
- Add mobile notifications

---

## Getting Help

### Self-Help

1. Check **CloudWatch Logs** first (most errors are logged there)
2. Review **Troubleshooting** section above
3. Read the relevant documentation file
4. Search AWS documentation

### Checklist for Asking Questions

If you need to ask for help, include:

- [ ] What you're trying to do
- [ ] What command you ran
- [ ] Error message (full text)
- [ ] CloudWatch logs (if applicable)
- [ ] Your environment (local vs AWS)
- [ ] What you've already tried

---

## Success Checklist

You're done when:

- [ ] LocalStack runs successfully (for development)
- [ ] OR AWS deployment completes (for production)
- [ ] Domain is verified in SES
- [ ] You can send/receive test emails
- [ ] DynamoDB shows project data
- [ ] CloudWatch logs show successful processing
- [ ] You understand how to monitor the system

**Congratulations!** You now have a working AI-powered project tracking system.

---

## Cost Reminder

**Development** (LocalStack):
- $0/month (completely free)
- Only cost: OpenAI API testing (~$1-5/month)

**Production** (AWS):
- Domain: $12-15/year (one-time)
- AWS: $0-5/month (free tier)
- OpenAI: $5-20/month
- **Total: ~$10-30/month**

Watch costs with AWS Budgets (already set up in deployment).

