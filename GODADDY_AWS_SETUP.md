# GoDaddy + AWS Hybrid Setup - Quick Reference

**For users with existing GoDaddy domain and website**

---

## Overview

You'll run a **hybrid setup**:
- **Website**: Stays on GoDaddy (for now)
- **Email processing**: Runs on AWS
- **DNS**: Managed in GoDaddy (simple records only)
- **Future**: Migrate fully to AWS when dashboard is ready

---

## What You Need

- Existing GoDaddy domain (with or without website)
- GoDaddy login credentials
- AWS account (we'll create this)
- OpenAI API key

---

## DNS Records You'll Add to GoDaddy

All of these go in: **GoDaddy → My Products → Your Domain → DNS**

### 1. DKIM Records (3 CNAME records)
**Purpose**: Verify your domain for Amazon SES email sending

```
Type: CNAME
Name: abc123._domainkey
Value: abc123.dkim.amazonses.com
TTL: 600

(Repeat for all 3 records shown in AWS SES Console)
```

**Source**: Copy these from AWS SES Console after verifying your domain

### 2. MX Record (1 record)
**Purpose**: Route incoming email to AWS

**Option A - Subdomain (Recommended for testing)**:
```
Type: MX
Name: project
Priority: 10
Value: inbound-smtp.us-east-1.amazonaws.com
TTL: 600
```
Result: Email sent to `anything@project.yourdomain.com` goes to AWS

**Option B - Root domain** (For production):
```
Type: MX
Name: @ (or leave blank)
Priority: 10
Value: inbound-smtp.us-east-1.amazonaws.com
TTL: 600
```
Result: Email sent to `anything@yourdomain.com` goes to AWS

⚠️ **Warning**: Option B will replace any existing email setup!

---

## What STAYS in GoDaddy

**DO NOT DELETE OR MODIFY THESE**:
- A record for `@` (your website's IP address)
- A record for `www` (if you have one)
- CNAME for `www` (if you have one)
- Any other records your website needs

---

## Step-by-Step Setup

### Phase 1: AWS Setup (Do First)
1. Follow `AWS_SETUP_GUIDE.md` Parts 1-2 (AWS account, CLI setup)
2. Skip Part 3 (domain registration) - you already have one!
3. Follow Part 3.1 in guide (create Route 53 hosted zone)
   - This is just for AWS to know about your domain
   - You won't use the nameservers yet

### Phase 2: SES & DNS (Do Second)
1. Follow `AWS_SETUP_GUIDE.md` Part 4 (SES setup)
2. When it says "add DNS records":
   - Add DKIM CNAMEs to **GoDaddy DNS** (not Route 53)
   - Copy values from AWS SES Console
   - Wait 5-30 minutes
   - Return to SES Console to verify

### Phase 3: Deploy Backend (Do Third)
1. Follow `AWS_SETUP_GUIDE.md` Parts 6-7 (SAM CLI install and deploy)
2. Save all output values

### Phase 4: Configure Email (Do Fourth)
1. Add MX record to **GoDaddy DNS**
2. Start with subdomain (Option A) for safety
3. Run SES configuration script
4. Test email flow

### Phase 5: Test (Do Fifth)
1. Send test email to `anything@project.yourdomain.com` (or root domain if you chose that)
2. Check AWS CloudWatch logs
3. Check DynamoDB for data
4. Verify your website still works!

---

## Common Questions

### Q: Will this break my website?
**A**: No, if you only add the records above. Your website uses A records, email uses MX records. They don't conflict.

### Q: Can I keep my existing email?
**A**: Yes, use the subdomain option (project.yourdomain.com) for AWS email. Your existing email continues working at yourdomain.com.

### Q: Do I need to move my domain to AWS?
**A**: Not required! You can keep it at GoDaddy forever. However, for production it's cleaner to migrate DNS to Route 53 later.

### Q: What about my website?
**A**: Three options:
1. **Keep on GoDaddy** - Easiest, no changes needed
2. **Migrate to AWS S3** - More work, better integration
3. **Wait and replace with dashboard** - Do this when your SaaS frontend is ready

### Q: When should I migrate fully to AWS?
**A**: After Phase 4-5 (frontend development) when you're ready to:
- Replace website with dashboard, OR
- Host static site on S3 + CloudFront

---

## DNS Record Summary Table

| Record Type | Name | Value | Where to Add | Purpose |
|-------------|------|-------|--------------|---------|
| A | @ | (GoDaddy IP) | GoDaddy | **KEEP** - Your website |
| CNAME (×3) | xxx._domainkey | xxx.dkim.amazonses.com | GoDaddy | **ADD** - Email verification |
| MX | project | inbound-smtp.us-east-1.amazonaws.com | GoDaddy | **ADD** - Receive emails |

---

## Troubleshooting

### Website stopped working after DNS changes
1. Check if A record for `@` still exists in GoDaddy
2. Restore it if deleted
3. Value should be your GoDaddy website's IP (check with GoDaddy support)

### Email not being received
1. Verify MX record added to GoDaddy (not Route 53)
2. Check spelling: `inbound-smtp.us-east-1.amazonaws.com`
3. Test: `nslookup -type=MX yourdomain.com` (should show AWS)
4. Check SES sandbox mode (can only send to verified emails)

### SES domain not verifying
1. Check all 3 DKIM CNAME records added to GoDaddy
2. Remove any trailing dots from record values
3. Wait 30 minutes for DNS propagation
4. Use `nslookup` to verify records are live

### Can't find where to add DNS records in GoDaddy
1. Log into GoDaddy.com
2. Click "My Products"
3. Find your domain
4. Click "DNS" button next to it
5. Scroll down to "Records" section
6. Click "Add" to add new records

---

## Migration Path (Future)

When ready to go full production:

### Option 1: Full AWS Migration
1. Export GoDaddy website content
2. Set up S3 + CloudFront static hosting
3. Build Next.js dashboard (Phases 4-7)
4. Update A record in GoDaddy to point to CloudFront
5. Change MX from subdomain to root domain
6. Eventually: Switch nameservers to Route 53 for full AWS control

### Option 2: Keep Hybrid
1. Website stays on GoDaddy (marketing site)
2. Dashboard runs on subdomain: `app.yourdomain.com`
3. Email on root domain or subdomain
4. This works fine forever!

---

## Security Checklist

Before going live:
- [ ] All DNS records use GoDaddy's encrypted connection
- [ ] MFA enabled on GoDaddy account
- [ ] Website A record backed up (know the IP address)
- [ ] Test email flow thoroughly
- [ ] Website still loads correctly
- [ ] SES production access approved
- [ ] AWS account secured with MFA

---

## Cost Implications

**GoDaddy Costs** (unchanged):
- Domain renewal: $15-20/year (you already pay this)
- Website hosting: Whatever you currently pay (if any)

**New AWS Costs**:
- Route 53 hosted zone: $0.50/month
- Everything else: $7-30/month (see AWS_SETUP_GUIDE.md)

**Total New Costs**: ~$10-30/month for email processing system

---

## Support Resources

**GoDaddy DNS Help**:
- https://www.godaddy.com/help/add-a-cname-record-19236
- https://www.godaddy.com/help/add-an-mx-record-19234

**AWS SES Help**:
- See AWS_SETUP_GUIDE.md sections 4-5

**General Questions**:
- Review NEXT_STEPS.md for what to do after AWS setup

---

**Last Updated**: 2025-10-14  
**Recommended For**: Users with existing GoDaddy domain who want to add AWS email processing without disrupting their website

