# System Architecture

## Overview

The Email AI Project Tracker is a serverless application built on AWS that processes construction project emails using AI to extract and track key information.

## Architecture Diagram

```
┌─────────────┐
│   Client    │
│ (Contractor)│
└──────┬──────┘
       │ Forwards email
       ▼
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                             │
│                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│  │   SES    │────▶│    S3    │     │   SNS    │           │
│  │ (Receive)│     │  Bucket  │────▶│  Topic   │           │
│  └──────────┘     └──────────┘     └────┬─────┘           │
│                                          │                  │
│                                          ▼                  │
│                                   ┌──────────┐             │
│                                   │   SQS    │             │
│                                   │  Queue   │             │
│                                   └────┬─────┘             │
│                                        │ Triggers           │
│                                        ▼                    │
│  ┌──────────────────────────────────────────┐             │
│  │         Lambda: Email Processor          │             │
│  │  - Downloads email from S3               │             │
│  │  - Parses email & attachments            │             │
│  │  - Calls AI for extraction               │             │
│  │  - Stores in DynamoDB                    │             │
│  └────┬─────────────────────────────────┬───┘             │
│       │                                  │                 │
│       ▼                                  ▼                 │
│  ┌────────────┐                   ┌────────────┐          │
│  │  OpenAI    │                   │ DynamoDB   │          │
│  │    API     │                   │  Tables    │          │
│  │            │                   │ - Projects │          │
│  │ - GPT-4o   │                   │ - Events   │          │
│  │ - Analyze  │                   │ - Users    │          │
│  │ - Extract  │                   └────────────┘          │
│  └────────────┘                                            │
│       │                                  │                 │
│       │                                  ▼                 │
│       │                          ┌──────────────┐         │
│       │                          │   Lambda:    │         │
│       │                          │Reply Sender  │         │
│       │                          └──────┬───────┘         │
│       │                                 │                 │
│       └─────────────────────────────────┘                 │
│                                          │                 │
│                                          ▼                 │
│                                   ┌──────────┐            │
│                                   │   SES    │            │
│                                   │  (Send)  │            │
│                                   └────┬─────┘            │
└────────────────────────────────────────┼──────────────────┘
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │   Client    │
                                  │   Inbox     │
                                  └─────────────┘
```

## Component Descriptions

### 1. Email Receiving Layer

**Amazon SES (Simple Email Service)**
- **Purpose**: Receives emails sent to `project@yourdomain.com`
- **Configuration**: 
  - MX records point to AWS SES
  - Receipt rules trigger S3 storage and SNS notification
  - DKIM/SPF configured for security
- **Cost**: Receiving is free, sending ~$0.10 per 1,000 emails

**Amazon S3**
- **Purpose**: Stores raw email MIME files
- **Configuration**:
  - Versioning enabled for audit trail
  - Encryption at rest (SSE-S3)
  - Lifecycle policy: Delete after 90 days
  - Public access blocked
- **Cost**: ~$0.023 per GB/month

### 2. Message Queue Layer

**Amazon SNS (Simple Notification Service)**
- **Purpose**: Publishes email received events
- **Why**: Decouples SES from processing logic
- **Configuration**:
  - Standard topic (not FIFO)
  - Encryption enabled
- **Cost**: $0.50 per million requests

**Amazon SQS (Simple Queue Service)**
- **Purpose**: Queues emails for processing
- **Why**: 
  - Durability: Messages persist if Lambda fails
  - Retry logic: Automatic retries with exponential backoff
  - Dead Letter Queue: Failed messages go to DLQ for investigation
- **Configuration**:
  - Visibility timeout: 5 minutes (matches Lambda timeout)
  - Message retention: 14 days
  - Max retries: 3 (then moved to DLQ)
- **Cost**: First 1M requests free

### 3. Processing Layer

**AWS Lambda: Email Processor**
- **Purpose**: Main email processing logic
- **Responsibilities**:
  1. Download email from S3
  2. Parse MIME structure
  3. Extract text and attachments
  4. Store attachments back to S3
  5. Call OpenAI for AI extraction
  6. Determine/create project
  7. Store event in DynamoDB
  8. Trigger reply if needed
- **Configuration**:
  - Runtime: Python 3.11
  - Memory: 512 MB
  - Timeout: 5 minutes
  - Trigger: SQS queue
  - Concurrency: Default (1000)
- **IAM Permissions**:
  - Read from S3 email bucket
  - Write to S3 email bucket (attachments)
  - Read/Write DynamoDB
  - Read Secrets Manager (OpenAI key)
  - Poll SQS queue
- **Cost**: Free tier includes 1M requests/month

**AWS Lambda: AI Orchestrator**
- **Purpose**: Advanced AI operations
- **Responsibilities**:
  - Generate estimates from documents
  - Analyze attachments
  - Complex AI workflows
- **Configuration**:
  - Runtime: Python 3.11
  - Memory: 1024 MB (more for document processing)
  - Timeout: 10 minutes
  - Trigger: Invoked by Email Processor or API Gateway
- **Cost**: Billed per invocation

**AWS Lambda: Reply Sender**
- **Purpose**: Send email replies
- **Responsibilities**:
  - Format email responses
  - Attach documents if needed
  - Send via SES
- **Configuration**:
  - Runtime: Python 3.11
  - Memory: 512 MB
  - Timeout: 2 minutes
- **Cost**: Minimal (only SES sending costs)

### 4. AI Layer

**OpenAI API**
- **Models Used**:
  - `gpt-4o-mini`: Email extraction, classification (~$0.15/1M input tokens)
  - `gpt-4o`: Estimate generation, complex analysis (~$2.50/1M input tokens)
- **Purpose**: 
  - Extract project information
  - Identify decisions and action items
  - Generate estimates
  - Classify emails
- **Security**: API key stored in AWS Secrets Manager
- **Cost Optimization**:
  - Use cheaper model for simple tasks
  - Cache common prompts
  - Limit token usage

### 5. Data Layer

**Amazon DynamoDB**

**Projects Table**
- **Schema**:
  - Partition Key: `project_id` (string)
  - Sort Key: `created_at` (number, timestamp)
  - GSI: `client_email-index` for querying by client
- **Attributes**:
  - client_email, client_name
  - project_name, project_address
  - status, metadata
- **Access Patterns**:
  - Get project by ID
  - List projects by client
  - Update project information

**Events Table** (Append-Only Audit Log)
- **Schema**:
  - Partition Key: `project_id` (string)
  - Sort Key: `event_timestamp` (number)
- **Attributes**:
  - event_type, event_id
  - source_email_id, sender, subject
  - ai_extracted_data
  - raw_s3_key, attachments
- **Access Patterns**:
  - Get events for project (chronological)
  - Query recent events
  - Full audit trail

**Users Table**
- **Schema**:
  - Partition Key: `user_email` (string)
- **Attributes**:
  - company_name, created_at
  - subscription_tier, api_quota
- **Purpose**: 
  - User account management
  - Quota tracking
  - Billing information

**DynamoDB Configuration**:
- Billing Mode: Pay-per-request (on-demand)
- Encryption: AWS-managed keys
- Point-in-time recovery: Disabled (enable for production)
- Cost: Free tier includes 25 GB storage, 25 read/write capacity units

### 6. Security Layer

**AWS Secrets Manager**
- **Purpose**: Store sensitive credentials
- **Secrets**:
  - `openai-api-key`: OpenAI API key
  - Future: Database credentials, third-party API keys
- **Access**: Only Lambda execution roles can read
- **Rotation**: Can be configured for automatic rotation
- **Cost**: $0.40 per secret/month

**IAM (Identity and Access Management)**
- **Principle**: Least privilege
- **Roles**:
  - `EmailProcessorRole`: S3 read/write, DynamoDB, Secrets Manager
  - `AIOrchestratorRole`: S3 read, DynamoDB, Secrets Manager
  - `ReplySenderRole`: S3 read, SES send
- **Policies**: Custom policies per Lambda function

**AWS CloudTrail**
- **Purpose**: Audit all API calls
- **Configuration**: One trail in S3
- **Use**: Security auditing, compliance, troubleshooting
- **Cost**: First trail is free

### 7. Monitoring Layer

**Amazon CloudWatch**

**Logs**:
- Lambda execution logs
- Structured JSON logging
- Retention: 30 days
- Cost: 5 GB free, then $0.50/GB

**Metrics**:
- Lambda invocations, errors, duration
- SQS queue depth
- DynamoDB read/write capacity
- Custom metrics (email processing rate)

**Alarms**:
- Lambda errors > 5% → Email alert
- DLQ messages > 0 → Email alert
- Daily cost > $10 → Email alert

**Dashboards**:
- Email processing overview
- System health
- Cost tracking

## Data Flow

### Email Receipt Flow

1. User sends email to `project@yourdomain.com`
2. SES receives email (validates SPF/DKIM)
3. SES stores email in S3 bucket
4. SES publishes notification to SNS topic
5. SNS sends message to SQS queue
6. SQS triggers Lambda (Email Processor)

### Email Processing Flow

1. Lambda receives SQS event
2. Extract S3 location from event
3. Download raw email from S3
4. Parse email (headers, body, attachments)
5. Validate sender (if allowlist enabled)
6. Skip if auto-reply
7. Store attachments in S3
8. Call OpenAI API to extract project data
9. Determine or create project ID
10. Store event in DynamoDB Events table
11. Update project metadata
12. Trigger reply (if required)
13. Delete message from SQS (success)

### Reply Flow

1. Email Processor invokes Reply Sender Lambda
2. Reply Sender formats email body
3. Retrieves attachments from S3 (if needed)
4. Sends via SES using send_raw_email
5. SES delivers email to user

### Error Handling Flow

1. Lambda execution fails
2. Message returns to SQS (increases receive count)
3. After 3 failed attempts → moved to DLQ
4. CloudWatch alarm triggers
5. Admin investigates via:
   - CloudWatch logs
   - DLQ messages
   - CloudTrail audit logs

## Scalability

### Current Capacity

- **Emails**: ~1,000/day
- **Concurrent Lambdas**: 1,000 (AWS default)
- **DynamoDB**: Unlimited (on-demand)
- **S3**: Unlimited
- **Cost**: $50-100/month at this scale

### Scaling Limits

| Component | Limit | How to Increase |
|-----------|-------|-----------------|
| SES Sending | 200/day (sandbox) | Request production access |
| Lambda Concurrency | 1,000 | Request limit increase |
| DynamoDB | 40K read/write units | Automatic (on-demand) |
| S3 | Unlimited | N/A |
| API Gateway | 10K requests/sec | Request limit increase |

### Performance Targets

- Email processing latency: < 30 seconds
- Reply latency: < 10 seconds
- Database query time: < 100ms
- API response time: < 500ms

## Security Architecture

### Defense in Depth

**Layer 1: Network**
- SES: TLS required for email
- S3: Block public access
- VPC: Optional for Lambdas (future)

**Layer 2: Identity & Access**
- IAM: Least privilege roles
- MFA: Required for AWS Console
- Secrets Manager: No keys in code

**Layer 3: Data**
- Encryption at rest: All services
- Encryption in transit: TLS 1.2+
- S3 versioning: Audit trail

**Layer 4: Application**
- Input validation: All user inputs
- Prompt injection protection: Sanitization
- Rate limiting: Per-customer quotas
- Auto-reply detection: Skip processing

**Layer 5: Monitoring**
- CloudTrail: All API calls logged
- CloudWatch: All errors logged
- Alarms: Immediate notification
- Regular audits: Review logs weekly

## Disaster Recovery

### Backup Strategy

**DynamoDB**:
- Point-in-time recovery (enable for production)
- Can restore to any second in last 35 days
- Cost: ~$0.20 per GB/month

**S3**:
- Versioning enabled
- Can recover deleted objects
- Lifecycle policy: Move old emails to Glacier (optional)

**Lambda**:
- Code in version control (Git)
- SAM template for infrastructure
- Can redeploy in minutes

### Recovery Procedures

**Scenario: Lambda Failure**
1. Check CloudWatch logs
2. Fix code bug
3. Deploy new version
4. Reprocess failed messages from DLQ

**Scenario: DynamoDB Corruption**
1. Restore from point-in-time backup
2. Or replay events from S3 emails

**Scenario: Complete Region Failure**
1. Deploy infrastructure to new region
2. Update DNS (MX records)
3. Restore DynamoDB from backup
4. Resume operations (RTO: ~2 hours)

## Cost Optimization

### Current Costs (100 emails/day)

- Route 53: $0.50/month (fixed)
- Lambda: $0-2/month (under free tier)
- DynamoDB: $0-5/month
- S3: $1-2/month
- SES: $0 (receiving free)
- OpenAI: $5-20/month (variable)
- **Total: $10-30/month**

### Optimization Strategies

1. **Use cheaper AI models**: gpt-4o-mini for simple tasks
2. **Cache AI responses**: Avoid duplicate calls
3. **Lifecycle policies**: Delete old emails from S3
4. **Reserved capacity**: If usage becomes predictable
5. **Compress attachments**: Reduce S3 storage
6. **Batch processing**: Process multiple emails together (if latency allows)

## Future Enhancements

### Phase 2 Features

- **Web Dashboard**: View projects, search emails
- **Advanced Estimates**: ML-based quantity takeoff
- **Integrations**: QuickBooks, Procore, etc.
- **Mobile App**: iOS/Android clients
- **Team Collaboration**: Multi-user access

### Architecture Changes

- **API Gateway**: RESTful API for web/mobile
- **Cognito**: User authentication
- **ElastiCache**: Cache frequent queries
- **Step Functions**: Complex workflows
- **VPC**: Enhanced security
- **Multi-region**: Disaster recovery

## Conclusion

This architecture provides:
- ✅ **Scalability**: Handles growth from 10 to 10,000 emails/day
- ✅ **Reliability**: 99.9%+ uptime with AWS services
- ✅ **Security**: Defense in depth, encryption everywhere
- ✅ **Cost-effective**: Pay only for what you use
- ✅ **Maintainable**: Infrastructure as code, clear separation of concerns

