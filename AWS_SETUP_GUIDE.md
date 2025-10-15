# AWS Setup Guide - GoDaddy Subdomain Configuration

This guide will walk you through setting up your AWS account from scratch and deploying your email processing system using a subdomain approach.

**Setup Type**: Hybrid (Website on GoDaddy + Email on AWS)  
**Email Format**: `clientname@project.yourdomain.com` (subdomain)  
**Time Required**: 1-2 weeks (mostly waiting for approvals)  
**Cost**: ~$15-30/month initially

---

## Prerequisites

Before starting, you'll need:
- ✅ Credit card (for AWS account)
- ✅ Email address (for AWS account)
- ✅ Phone number (for MFA)
- ✅ OpenAI API key (from platform.openai.com)
- ✅ **Your existing GoDaddy domain** (you already have this!)
- ✅ GoDaddy account login credentials

**Your Setup**: This guide is customized for keeping your GoDaddy website unchanged while adding AWS email processing on a subdomain. Your website stays on GoDaddy, email goes to AWS. Both systems work independently with zero conflict.

---

## Part 1: AWS Account Creation (30 minutes)

### Step 1.1: Create AWS Account

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Enter your email and choose an AWS account name
4. Choose "Personal" account type
5. Enter billing information (credit card)
6. Verify phone number
7. Select "Basic Support - Free" plan
8. Complete signup

**Important**: You'll receive a confirmation email. Click the link to verify.

### Step 1.2: Secure Your Root Account

**This is CRITICAL for security!**

1. Log into AWS Console: https://console.aws.amazon.com/
2. Click your account name (top right) → "Security Credentials"
3. Under "Multi-factor authentication (MFA)":
   - Click "Assign MFA device"
   - Choose "Virtual MFA device"
   - Use Google Authenticator or Authy app on your phone
   - Scan QR code and enter two consecutive codes
   - Click "Assign MFA"

**✅ Checkpoint**: You should now see MFA enabled on your root account.

### Step 1.3: Create IAM Admin User

**Don't use root account for daily work!**

1. Go to IAM Console: https://console.aws.amazon.com/iam/
2. Click "Users" → "Add users"
3. User name: `admin-user`
4. Check "Provide user access to the AWS Management Console"
5. Choose "I want to create an IAM user"
6. Console password: Choose "Custom password" and create a strong one
7. Uncheck "Users must create a new password at next sign-in"
8. Click "Next"
9. Select "Attach policies directly"
10. Search for and select: `AdministratorAccess`
11. Click "Next" → "Create user"
12. **IMPORTANT**: Download the .csv file with credentials
13. Note the "Console sign-in URL" - bookmark this!

### Step 1.4: Set Up MFA for Admin User

1. Log out of root account
2. Log in with admin user (use the Console sign-in URL you bookmarked)
3. Click username (top right) → "Security credentials"
4. Under "Multi-factor authentication (MFA)":
   - Click "Assign MFA device"
   - Use same authenticator app (different QR code)

**✅ Checkpoint**: You can now log in as admin user with MFA.

---

## Part 2: AWS CLI Setup (15 minutes)

### Step 2.1: Install AWS CLI

**Windows**:
1. Download: https://awscli.amazonaws.com/AWSCLIV2.msi
2. Run installer
3. Open PowerShell and verify: `aws --version`

Expected output: `aws-cli/2.x.x ...`

### Step 2.2: Create Access Keys

1. Log into AWS Console as admin user
2. IAM Console → Users → Click your admin username
3. Click "Security credentials" tab
4. Scroll to "Access keys" section
5. Click "Create access key"
6. Choose use case: "Command Line Interface (CLI)"
7. Check the acknowledgement box
8. Click "Next" → Add optional tag (optional) → "Create access key"
9. **CRITICAL**: Download .csv or copy both keys immediately
   - Access key ID: `AKIA...`
   - Secret access key: (long random string)
10. Click "Done"

**⚠️ SECURITY WARNING**: Never share these keys or commit them to Git!

### Step 2.3: Configure AWS CLI

Open PowerShell and run:

```powershell
aws configure
```

Enter when prompted:
```
AWS Access Key ID: [paste your access key ID]
AWS Secret Access Key: [paste your secret access key]
Default region name: us-east-1
Default output format: json
```

### Step 2.4: Test AWS CLI

```powershell
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/admin-user"
}
```

**✅ Checkpoint**: AWS CLI is configured and working!

---

## Part 3: GoDaddy Domain Setup (30 minutes)

**Note**: You already have a domain at GoDaddy with an active website. We'll configure it to work with AWS while preserving your website (or migrating it).

### Step 3.1: Create Route 53 Hosted Zone

Even though your domain is registered at GoDaddy, you need a Route 53 hosted zone for AWS to manage DNS.

1. Go to Route 53 Console: https://console.aws.amazon.com/route53/
2. Click "Hosted zones" → "Create hosted zone"
3. Domain name: Enter your GoDaddy domain (e.g., `yourdomain.com`)
4. Type: "Public hosted zone"
5. Click "Create hosted zone"

**✅ Checkpoint**: Hosted zone created. You'll see 4 NS (nameserver) records.

### Step 3.2: Setup Strategy - Subdomain for Email

**Your Setup**: Keep website on GoDaddy, use subdomain for AWS email processing

**What this means**:
- Website stays at GoDaddy (no changes needed)
- Email goes to: `anything@project.yourdomain.com` (or whatever subdomain you choose)
- Both systems work independently
- Zero downtime, zero risk to website

**Why use subdomain?**
- Safest approach - website won't be affected
- Easy to test without disrupting existing setup
- Can switch to root domain later when ready for production
- Professional subdomains work fine: `acme@project.yourdomain.com`

### Step 3.3: Setup DNS Records in GoDaddy

We'll add email records WITHOUT touching your website configuration.

**In GoDaddy**:
1. Log into GoDaddy
2. Go to "My Products" → Find your domain → Click "DNS"
3. **DO NOT change nameservers** - keep as-is
4. **DO NOT modify** existing A, CNAME, or other records for your website
5. We'll only ADD new records in the next steps

**In Route 53**:
1. Go to your hosted zone (already created in Step 3.1)
2. Note the 4 nameserver values (like `ns-123.awsdns-12.com`)
3. **You won't use these** - they're just there for AWS to know about your domain
4. All DNS management stays in GoDaddy

**✅ Checkpoint**: GoDaddy DNS panel open, existing records unchanged, ready to add new records.

---

## Part 4: SES Setup (30 minutes + 24-48 hour wait)

### Step 4.1: Verify Domain in SES

**IMPORTANT**: SES receiving only works in `us-east-1` region!

1. Make sure you're in **us-east-1** region (check top-right dropdown)
2. Go to SES Console: https://console.aws.amazon.com/ses/
3. Click "Verified identities" → "Create identity"
4. Identity type: "Domain"
5. Domain: Enter your domain (e.g., `myprojectr.com`)
6. Click "Create identity"

### Step 4.2: Add DNS Records

You'll see a screen with several DNS records to add. **We'll add these to GoDaddy.**

**In GoDaddy DNS Manager**:

1. Log into GoDaddy → "My Products" → Your domain → "DNS"
2. Scroll down to the DNS records section

**Add DKIM Records** (3 CNAME records from SES):

For each of the 3 DKIM records shown in SES:
1. Click "Add" → Select "CNAME"
2. **Name**: Enter the subdomain part only (e.g., if SES shows `abc123._domainkey.yourdomain.com`, just enter `abc123._domainkey`)
3. **Value**: Enter the full value from SES (e.g., `abc123.dkim.amazonses.com`)
4. **TTL**: 600 (or leave default)
5. Click "Save"
6. Repeat for all 3 DKIM records

**Example**:
```
Name: abc123._domainkey
Type: CNAME
Value: abc123.dkim.amazonses.com
TTL: 600
```

**⏳ Wait 5-30 minutes for DNS propagation.**

### Step 4.3: Verify Domain Status

1. Return to SES Console → "Verified identities"
2. Click your domain
3. Under "DomainKeys Identified Mail (DKIM)", wait for status: "Successful"
4. This can take 5-30 minutes

**✅ Checkpoint**: Domain shows "Verified" status in SES.

### Step 4.4: Verify Email Address (For Testing)

While in SES sandbox, you can only send TO verified email addresses.

1. SES Console → "Verified identities" → "Create identity"
2. Identity type: "Email address"
3. Email address: Your personal email
4. Click "Create identity"
5. Check your email for verification link
6. Click the verification link

**✅ Checkpoint**: Your email shows "Verified" status.

### Step 4.5: Request Production Access

**This is REQUIRED to receive emails from anyone!**

1. SES Console → Left sidebar → "Account dashboard"
2. Click "Request production access" button
3. Fill out the form:

**Mail type**: Transactional

**Website URL**: Your domain or GoDaddy website URL

**Use case description**: (Example below)
```
I am building an email-based project management system for construction 
subcontractors. Clients will forward project-related emails to a dedicated 
address (e.g., company@mydomain.com), and my system will:
1. Process and parse the emails using AI
2. Extract project information, decisions, and action items
3. Store data in a database
4. Send acknowledgment emails back to clients

Expected volume: 50-200 emails per day initially, scaling to 500-1000/day.
All recipients are existing business clients who have explicitly signed up 
for this service. I will implement bounce/complaint handling and maintain 
high email quality standards.
```

**Process description**: (Example below)
```
1. Only send emails to users who have signed up for our service
2. All emails are transactional (acknowledgments and notifications)
3. Include unsubscribe links in all emails
4. Monitor bounce and complaint rates
5. Maintain bounce rate < 2% and complaint rate < 0.1%
```

**Compliance**: Check all boxes confirming compliance

4. Click "Submit request"

**⏳ WAIT**: AWS usually responds within 24-48 hours. You'll receive an email.

**Common reasons for rejection**:
- Vague use case description
- No bounce/complaint handling plan
- Suspicious activity (new account)

**If rejected**: Reply to the email with more details and resubmit.

**✅ Checkpoint**: Production access approved (shows in Account dashboard).

---

## Part 5: Store OpenAI API Key (5 minutes)

### Step 5.1: Get OpenAI API Key

1. Go to https://platform.openai.com/
2. Sign up or log in
3. Click your profile → "API keys"
4. Click "Create new secret key"
5. Name it: "Email Project Tracker"
6. Copy the key (starts with `sk-proj-...` or `sk-...`)
7. **SAVE IT SOMEWHERE SAFE** - you can't see it again!

### Step 5.2: Store in AWS Secrets Manager

In PowerShell (make sure you're in your project directory):

```powershell
aws secretsmanager create-secret `
    --name openai-api-key `
    --secret-string '{\"api_key\":\"sk-your-actual-key-here\"}' `
    --region us-east-1
```

Replace `sk-your-actual-key-here` with your actual OpenAI key.

### Step 5.3: Verify Secret Stored

```powershell
aws secretsmanager describe-secret --secret-id openai-api-key --region us-east-1
```

You should see JSON output with your secret details.

**✅ Checkpoint**: OpenAI key is safely stored in AWS Secrets Manager.

---

## Part 6: Install AWS SAM CLI (15 minutes)

AWS SAM (Serverless Application Model) makes deploying Lambda functions easy.

### Step 6.1: Install SAM CLI

**Windows**:
1. Download: https://github.com/aws/aws-sam-cli/releases/latest/download/AWS_SAM_CLI_64_PY3.msi
2. Run installer
3. Open a NEW PowerShell window
4. Verify: `sam --version`

Expected output: `SAM CLI, version 1.x.x`

### Step 6.2: Verify Docker is Running

SAM uses Docker to build Lambda packages.

```powershell
docker --version
```

If Docker isn't installed:
1. Download Docker Desktop: https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Wait for it to fully start (whale icon in system tray)

**✅ Checkpoint**: SAM CLI and Docker are installed.

---

## Part 7: Deploy Your System to AWS (30 minutes)

### Step 7.1: Prepare Your Code

Make sure you're in your project directory:

```powershell
cd "C:\Users\tmher\OneDrive\Herrick Technologies\Project"
```

### Step 7.2: Install Python Dependencies

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install/update dependencies
pip install -r requirements.txt
```

### Step 7.3: Build Lambda Packages

```powershell
cd infrastructure
sam build
```

This will take 2-5 minutes. You'll see output about building each Lambda function.

### Step 7.4: Deploy to AWS (Guided)

```powershell
sam deploy --guided
```

**You'll be prompted for configuration**. Use these values:

```
Stack Name [sam-app]: project-tracker-dev
AWS Region [us-east-1]: us-east-1
Parameter ProjectDomain []: your-actual-domain.com
Parameter OpenAIKeySecretName [openai-api-key]: openai-api-key
Parameter Environment [dev]: dev
Confirm changes before deploy [Y/n]: Y
Allow SAM CLI IAM role creation [Y/n]: Y
Disable rollback [y/N]: N
EmailProcessorFunction may not have authorization defined, Is this okay? [y/N]: y
AIOrchestratorFunction may not have authorization defined, Is this okay? [y/N]: y
ReplySenderFunction may not have authorization defined, Is this okay? [y/N]: y
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: samconfig.toml
SAM configuration environment [default]: default
```

**Deployment will take 5-10 minutes**. You'll see CloudFormation creating resources.

### Step 7.5: Note the Outputs

At the end, you'll see output values. **SAVE THESE**:

```
Key                 Value
EmailBucket         project-emails-123456789012-dev
EmailReceivedTopicArn   arn:aws:sns:us-east-1:123456789012:email-received-dev
EmailQueueUrl       https://sqs.us-east-1.amazonaws.com/123456789012/email-processing-queue-dev
ProjectsTableName   ProjectTracking-Projects-dev
EventsTableName     ProjectTracking-Events-dev
UsersTableName      ProjectTracking-Users-dev
```

**✅ Checkpoint**: CloudFormation stack deployed successfully!

---

## Part 8: Configure SES Email Receipt (15 minutes)

### Step 8.1: Create MX Record in GoDaddy (Subdomain)

**What we're doing**: Adding an MX record for your subdomain so AWS can receive emails.

**In GoDaddy DNS Manager**:

1. Log into GoDaddy → "My Products" → Your domain → "DNS"
2. Scroll to "Records" section
3. Click "Add" → Select "MX"
4. Enter the following:
   - **Name**: `project` (or whatever subdomain you chose - this creates `project.yourdomain.com`)
   - **Priority**: 10
   - **Value**: `inbound-smtp.us-east-1.amazonaws.com`
   - **TTL**: 600 (or leave default)
5. Click "Save"

**What this creates**:
- Email sent to `anything@project.yourdomain.com` will be received by AWS
- Examples: `acme@project.yourdomain.com`, `clientname@project.yourdomain.com`
- Your existing email (if any) continues to work normally

**Common subdomain choices**:
- `project` → `acme@project.yourdomain.com`
- `mail` → `acme@mail.yourdomain.com`
- `tracking` → `acme@tracking.yourdomain.com`

**Note**: You can change the subdomain name if you want, just remember what you used!

**✅ Checkpoint**: MX record added for subdomain in GoDaddy.

### Step 8.2: Configure SES Receipt Rule

Run the configuration script:

```powershell
cd ..  # Back to project root
python scripts/configure_ses.py `
    --domain your-actual-domain.com `
    --bucket project-emails-123456789012-dev `
    --topic-arn arn:aws:sns:us-east-1:123456789012:email-received-dev
```

Replace values with your actual outputs from deployment.

### Step 8.3: Verify Receipt Rule

1. Go to SES Console → "Email receiving" → "Rule sets"
2. You should see a rule set named something like `email-receipt-rules`
3. Click it to see the rule

**✅ Checkpoint**: SES receipt rule is configured.

---

## Part 9: Test Your System (15 minutes)

### Step 9.1: Send Test Email

From a verified email address, send an email to:
```
anything@project.your-actual-domain.com
```

**Note**: Replace `project` with whatever subdomain you chose in Step 8.1, and replace `your-actual-domain.com` with your actual domain.

Subject: `New Project - Office Renovation`

Body:
```
Hi,

I need a quote for an office renovation project at 123 Main Street.

The work includes:
- New HVAC system
- Electrical upgrades
- Drywall repairs

Timeline: Need to start next month
Budget: Around $50,000

Let me know if you can help!

Thanks,
John Smith
ABC Construction
```

### Step 9.2: Check S3 for Email

1. Go to S3 Console
2. Find bucket: `project-emails-123456789012-dev`
3. You should see a file (looks like a random string)
4. This is your email in MIME format

**✅ Checkpoint**: Email stored in S3.

### Step 9.3: Check Lambda Logs

1. Go to CloudWatch Console → "Log groups"
2. Find: `/aws/lambda/email-processor-dev`
3. Click the latest log stream
4. Look for log entries showing:
   - "Processing email from S3..."
   - "Extracting project data with AI"
   - "Created event ... for project ..."

### Step 9.4: Check DynamoDB

1. Go to DynamoDB Console → "Tables"
2. Click `ProjectTracking-Projects-dev`
3. Click "Explore table items"
4. You should see 1 project created
5. Click `ProjectTracking-Events-dev`
6. You should see 1 event with extracted data

**✅ Checkpoint**: Email was processed and data stored!

### Step 9.5: Check for Reply Email

Within 1-2 minutes, you should receive an acknowledgment email at the address you sent from.

**If you don't receive it**: Check CloudWatch logs for errors.

---

## Part 10: Set Up Monitoring (15 minutes)

### Step 10.1: Create CloudWatch Dashboard

1. Go to CloudWatch Console → "Dashboards"
2. Click "Create dashboard"
3. Dashboard name: `Email-Tracker-Dev`
4. Add widgets:
   - **Lambda Invocations**: Choose `email-processor-dev`
   - **Lambda Errors**: Choose `email-processor-dev`
   - **SQS Messages**: Choose `email-processing-queue-dev`

### Step 10.2: Set Up Budget Alert

1. Go to Billing Console → "Budgets"
2. Click "Create budget"
3. Budget type: Cost budget
4. Name: `Monthly-AWS-Budget`
5. Amount: $50
6. Alert threshold: 80% of budgeted amount
7. Email address: Your email
8. Click "Create budget"

**✅ Checkpoint**: Monitoring and alerts configured!

---

## Troubleshooting

### Issue: Email not received by SES

**Checks**:
1. Verify MX record in Route 53 (can take 5-10 min to propagate)
2. Test with: `nslookup -type=MX yourdomain.com`
3. Check SES account is out of sandbox mode
4. Verify sender email if still in sandbox

### Issue: Lambda errors in logs

**Common causes**:
1. OpenAI API key not found → Verify Secrets Manager
2. Permission denied → Check IAM roles in CloudFormation
3. Timeout → Increase Lambda timeout in template.yaml

### Issue: No data in DynamoDB

**Checks**:
1. Check CloudWatch logs for errors
2. Verify SQS message was sent (SQS Console → Messages available)
3. Check Lambda was triggered (CloudWatch Metrics)

### Issue: High costs

**Causes**:
1. OpenAI API calls (usually the biggest cost)
2. Check CloudWatch Logs retention (reduce to 7 days for dev)
3. Delete old S3 test emails

### Issue: DNS records not working (GoDaddy specific)

**Checks**:
1. Verify you added records to GoDaddy, not Route 53
2. Check for typos in CNAME/MX record values
3. Remove any trailing dots from record values in GoDaddy
4. Wait 10-15 minutes for GoDaddy DNS propagation
5. Test DNS: `nslookup -type=MX yourdomain.com`
6. Test DKIM: `nslookup -type=CNAME record-name._domainkey.yourdomain.com`

### Issue: Website went down after DNS changes

**Recovery**:
1. Log into GoDaddy DNS immediately
2. Check if A record for `@` or `www` was accidentally deleted
3. Restore the A record (should point to your GoDaddy server IP)
4. If you switched nameservers to Route 53, switch back to GoDaddy
5. Contact GoDaddy support if needed

### Issue: Email working but website not loading

**Possible causes**:
1. MX record correct, but A record missing
2. Check GoDaddy DNS has A record for `@` pointing to website server
3. Clear browser cache and try incognito mode
4. Check GoDaddy website hosting is still active

---

## Next Steps

🎉 **Congratulations! Your system is live in AWS!**

Now you can:

1. **Test with real project emails** - Forward actual emails and verify extraction quality
2. **Monitor costs daily** - Check AWS Billing dashboard
3. **Refine AI prompts** - Adjust prompts in `src/shared/ai_client.py` based on results
4. **Move to Phase 1** - Implement multi-tenant architecture when ready

---

## Getting Help

**AWS Documentation**:
- SES: https://docs.aws.amazon.com/ses/
- Lambda: https://docs.aws.amazon.com/lambda/
- DynamoDB: https://docs.aws.amazon.com/dynamodb/

**AWS Support**:
- For production issues, consider AWS Support plan ($29/month)
- Use AWS Forums: https://repost.aws/

**Project Documentation**:
- See README.md for local development
- See ARCHITECTURE.md for system design
- See SECURITY.md for best practices

---

## Cost Tracking

Keep track of your monthly costs:

| Service | Expected Cost |
|---------|--------------|
| Route 53 Hosted Zone | $0.50/month |
| GoDaddy Domain (existing) | Already paid |
| SES | $0 (receiving free) |
| Lambda | $0-2 (under free tier) |
| DynamoDB | $0-5 |
| S3 | $1-2 |
| OpenAI | $5-20 |
| **AWS Total** | **$7-30/month** |

Check actual costs: AWS Console → Billing → Cost Explorer

---

## Next Steps After Deployment

🎉 **Your hybrid setup is complete!**

### What You Have Now
- ✅ Website running on GoDaddy (unchanged)
- ✅ Email processing on AWS (subdomain)
- ✅ Both systems working independently
- ✅ Multi-client backend infrastructure ready

### Immediate Next Steps
1. **Test with real emails** - Forward project emails to your subdomain
2. **Monitor AWS costs** - Check Billing dashboard daily for first week
3. **Verify website** - Make sure your GoDaddy site still works
4. **Check email flow** - Send several test emails from different addresses

### Moving Forward
- **Week 1-2**: Test thoroughly, refine AI prompts based on results
- **Week 3-8**: Build multi-tenant features (follow NEXT_STEPS.md)
- **Month 3+**: Build frontend dashboard for clients
- **Future**: Optionally switch to root domain when ready for production clients

### When Ready for Production
Eventually, you can switch from subdomain to root domain for cleaner client emails:
- Change from: `acme@project.yourdomain.com`
- To: `acme@yourdomain.com`

This requires updating the MX record in GoDaddy to point root domain (`@`) to AWS instead of subdomain (`project`). But there's no rush - subdomain works perfectly fine for testing and even production use.

---

**Last Updated**: 2025-10-14
**Questions?**: Review other documentation files or create a detailed issue.

## Important Notes for GoDaddy Users

### DNS Management
- You're managing DNS in **GoDaddy only** - simple and safe
- Route 53 hosted zone exists but you're not using its nameservers
- This hybrid setup is common and works great long-term

### Email with Subdomains
- Your client emails will look like: `clientname@project.yourdomain.com`
- This is perfectly professional and works for production
- Many SaaS products use subdomains (e.g., `support@help.company.com`)
- You can switch to root domain later if preferred, but it's not required

### Your Website
- GoDaddy website is completely unaffected by AWS setup
- All A records and website DNS stay in GoDaddy
- No risk of downtime or website issues
- Continue managing your website normally in GoDaddy

### What's in Each System
**GoDaddy manages**:
- Your website (A records)
- DKIM records for email verification (CNAME)
- MX record for subdomain (points to AWS)

**AWS manages**:
- Email processing (Lambda, DynamoDB, S3)
- AI extraction (OpenAI integration)
- Backend infrastructure

Both systems work together seamlessly without conflicts.

