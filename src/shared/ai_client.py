"""OpenAI client wrapper for AI operations."""
import json
import boto3
from typing import Dict, Any, Optional, List
from openai import OpenAI
from .config import Config
from .logger import setup_logger

logger = setup_logger(__name__)


class AIClient:
    """Wrapper for OpenAI API operations."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.api_key = self._get_api_key()
        self.client = OpenAI(api_key=self.api_key)
        self.extraction_model = Config.OPENAI_MODEL_EXTRACTION
        self.estimation_model = Config.OPENAI_MODEL_ESTIMATION
    
    def _get_api_key(self) -> str:
        """Get OpenAI API key from Secrets Manager or environment.
        
        Returns:
            OpenAI API key
        """
        # Use environment variable for local development
        if Config.USE_LOCALSTACK and Config.OPENAI_API_KEY:
            return Config.OPENAI_API_KEY
        
        # Get from AWS Secrets Manager for production
        try:
            secrets_client = boto3.client('secretsmanager', **Config.get_boto3_config())
            response = secrets_client.get_secret_value(SecretId=Config.OPENAI_API_KEY_SECRET)
            secret_data = json.loads(response['SecretString'])
            return secret_data['api_key']
        except Exception as e:
            logger.error(f"Failed to retrieve OpenAI API key: {str(e)}")
            raise
    
    def extract_project_data(self, sender: str, subject: str, body: str, 
                            attachments_summary: Optional[str] = None) -> Dict[str, Any]:
        """Extract project information from email using AI.
        
        Args:
            sender: Email sender address
            subject: Email subject
            body: Email body text
            attachments_summary: Summary of attachments (optional)
            
        Returns:
            Extracted project data as structured JSON
        """
        system_prompt = """You are an expert construction project manager assistant.

Your job is to analyze emails and extract:
1. Project identification (name, address, job number)
2. Decisions made (who decided what, when)
3. Changes to scope, budget, timeline
4. Action items and owners
5. Risks or blockers mentioned

Always return valid JSON with these keys:
{
  "project_id": "extracted or null",
  "project_name": "string or null",
  "project_address": "string or null",
  "decisions": [
    {"decision": "text", "made_by": "person", "timestamp": "when", "affects": ["items"]}
  ],
  "action_items": [
    {"task": "text", "owner": "person", "deadline": "date or null", "priority": "high/medium/low"}
  ],
  "scope_changes": ["change1", "change2"],
  "budget_mentions": ["budget item 1"],
  "timeline_changes": ["timeline change"],
  "risks": ["risk1", "risk2"],
  "key_points": ["summary point 1", "point 2"],
  "people_mentioned": ["person1", "person2"],
  "requires_response": true/false
}

Be conservative. If unsure, return null. Maintain strict JSON format."""

        user_prompt = f"""Email from: {sender}
Subject: {subject}

Body:
{body}"""

        if attachments_summary:
            user_prompt += f"\n\nAttachments: {attachments_summary}"
        
        try:
            logger.info("Calling OpenAI for project data extraction")
            response = self.client.chat.completions.create(
                model=self.extraction_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Low temperature for consistency
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info("Successfully extracted project data")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to extract project data: {str(e)}")
            raise
    
    def generate_estimate(self, documents_text: str, project_type: str, 
                         trade: Optional[str] = None) -> Dict[str, Any]:
        """Generate construction estimate from documents using AI.
        
        Args:
            documents_text: Extracted text from bid documents
            project_type: Type of construction project
            trade: Specific trade (electrical, plumbing, HVAC, etc.)
            
        Returns:
            Structured estimate data
        """
        system_prompt = """You are an expert construction estimator.

Generate a preliminary estimate based on the provided documents.

Return JSON with this structure:
{
  "estimate_id": "unique_id",
  "line_items": [
    {
      "description": "Work item description",
      "quantity": number,
      "unit": "unit of measure",
      "unit_cost": number,
      "total_cost": number,
      "notes": "any relevant notes"
    }
  ],
  "summary": {
    "subtotal": number,
    "contingency_percent": 10,
    "contingency_amount": number,
    "total": number
  },
  "assumptions": ["assumption 1", "assumption 2"],
  "exclusions": ["exclusion 1"],
  "confidence_level": "low/medium/high",
  "notes": "Overall notes about the estimate"
}

Mark all costs as PRELIMINARY. Be conservative with estimates."""

        trade_context = f" for {trade} trade" if trade else ""
        user_prompt = f"""Generate a preliminary estimate for this {project_type} project{trade_context}.

Documents:
{documents_text}

Provide detailed line items with quantities and unit costs."""
        
        try:
            logger.info(f"Generating estimate for {project_type} project")
            response = self.client.chat.completions.create(
                model=self.estimation_model,  # Use more capable model for estimates
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info("Successfully generated estimate")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to generate estimate: {str(e)}")
            raise
    
    def generate_response(self, email_context: Dict[str, Any], 
                         extracted_data: Dict[str, Any],
                         request_type: str = "acknowledgment") -> str:
        """Generate email response based on context.
        
        Args:
            email_context: Original email information
            extracted_data: AI-extracted project data
            request_type: Type of response (acknowledgment, estimate, form_fill, etc.)
            
        Returns:
            Generated response text
        """
        system_prompt = """You are a helpful construction project assistant.

Generate professional, concise email responses.

For acknowledgments: Confirm receipt, summarize key points, list next steps.
For estimates: Present the estimate professionally with disclaimers.
For form responses: Provide filled information clearly.

Keep responses friendly but professional. Sign as "Your Project Tracking Assistant"."""

        user_prompt = f"""Generate a {request_type} response for this email.

Original Subject: {email_context.get('subject', 'N/A')}
Sender: {email_context.get('sender', 'N/A')}

Extracted Information:
{json.dumps(extracted_data, indent=2)}

Generate an appropriate response."""
        
        try:
            logger.info(f"Generating {request_type} response")
            response = self.client.chat.completions.create(
                model=self.extraction_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7  # Higher temperature for more natural responses
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            raise
    
    def sanitize_input(self, text: str, max_length: int = 100000) -> str:
        """Sanitize user input to prevent prompt injection.
        
        Args:
            text: Input text
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        # Truncate if too long
        if len(text) > max_length:
            logger.warning(f"Input truncated from {len(text)} to {max_length} chars")
            text = text[:max_length]
        
        # Remove potential injection attempts (basic sanitization)
        # In production, consider more sophisticated sanitization
        dangerous_patterns = [
            "ignore previous instructions",
            "disregard all prior",
            "forget everything",
            "new instructions:",
            "system:",
        ]
        
        lower_text = text.lower()
        for pattern in dangerous_patterns:
            if pattern in lower_text:
                logger.warning(f"Potential injection attempt detected: {pattern}")
                # Don't remove, but log for monitoring
        
        return text

