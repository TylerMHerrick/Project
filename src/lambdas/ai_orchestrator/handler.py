"""
AI Orchestrator Lambda
Handles advanced AI operations like estimate generation and document analysis.
"""
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from shared.ai_client import AIClient
from shared.s3_client import S3Client
from shared.db_client import DynamoDBClient
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Initialize clients
ai_client = AIClient()
s3_client = S3Client()
db_client = DynamoDBClient()


def lambda_handler(event, context):
    """Handle AI orchestration requests.
    
    Args:
        event: Event containing AI task details
        context: Lambda context
        
    Returns:
        AI processing results
    """
    task_type = event.get('task_type')
    
    logger.info(f"Processing AI task: {task_type}")
    
    if task_type == 'generate_estimate':
        return handle_estimate_generation(event)
    elif task_type == 'analyze_documents':
        return handle_document_analysis(event)
    elif task_type == 'generate_response':
        return handle_response_generation(event)
    else:
        logger.error(f"Unknown task type: {task_type}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Unknown task type: {task_type}'})
        }


def handle_estimate_generation(event):
    """Generate construction estimate from documents.
    
    Args:
        event: Event containing estimate parameters
        
    Returns:
        Generated estimate
    """
    project_id = event.get('project_id')
    document_keys = event.get('document_keys', [])
    project_type = event.get('project_type', 'construction')
    trade = event.get('trade')
    
    logger.info(f"Generating estimate for project {project_id}")
    
    # Retrieve and parse documents
    documents_text = ""
    for doc_key in document_keys:
        try:
            doc_data = s3_client.get_attachment(doc_key)
            # Parse document (will use parsers in Phase 4)
            # For now, assume text extraction is done
            documents_text += f"\n\n--- Document: {doc_key} ---\n"
            # TODO: Use document parsers to extract text
        except Exception as e:
            logger.error(f"Failed to retrieve document {doc_key}: {str(e)}")
    
    if not documents_text.strip():
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No valid documents to process'})
        }
    
    # Generate estimate using AI
    try:
        estimate = ai_client.generate_estimate(documents_text, project_type, trade)
        
        # Store estimate in database
        event_data = {
            'event_type': 'ESTIMATE_GENERATED',
            'estimate_data': estimate,
            'documents_used': document_keys,
        }
        event_id = db_client.create_event(project_id, event_data)
        
        logger.info(f"Generated estimate {estimate.get('estimate_id')} for project {project_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'estimate': estimate,
                'event_id': event_id
            })
        }
    except Exception as e:
        logger.error(f"Failed to generate estimate: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_document_analysis(event):
    """Analyze documents for project information.
    
    Args:
        event: Event containing document keys
        
    Returns:
        Analysis results
    """
    project_id = event.get('project_id')
    document_keys = event.get('document_keys', [])
    
    logger.info(f"Analyzing documents for project {project_id}")
    
    # Retrieve documents
    analyzed_docs = []
    for doc_key in document_keys:
        try:
            doc_data = s3_client.get_attachment(doc_key)
            # TODO: Parse document based on type
            # For now, placeholder
            analyzed_docs.append({
                'key': doc_key,
                'status': 'processed',
                'extracted_data': {}
            })
        except Exception as e:
            logger.error(f"Failed to analyze document {doc_key}: {str(e)}")
            analyzed_docs.append({
                'key': doc_key,
                'status': 'error',
                'error': str(e)
            })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'project_id': project_id,
            'documents': analyzed_docs
        })
    }


def handle_response_generation(event):
    """Generate email response based on context.
    
    Args:
        event: Event containing response parameters
        
    Returns:
        Generated response
    """
    email_context = event.get('email_context', {})
    extracted_data = event.get('extracted_data', {})
    request_type = event.get('request_type', 'acknowledgment')
    
    logger.info(f"Generating {request_type} response")
    
    try:
        response_text = ai_client.generate_response(email_context, extracted_data, request_type)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response_text': response_text,
                'request_type': request_type
            })
        }
    except Exception as e:
        logger.error(f"Failed to generate response: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

