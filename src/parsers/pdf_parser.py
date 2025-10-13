"""PDF document parser."""
import io
from typing import Dict, List, Any, Optional
import pdfplumber
import fitz  # PyMuPDF

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from shared.logger import setup_logger

logger = setup_logger(__name__)


class PDFParser:
    """Parse PDF documents to extract text and tables."""
    
    @staticmethod
    def extract_text(file_bytes: bytes) -> str:
        """Extract text from PDF.
        
        Args:
            file_bytes: PDF file bytes
            
        Returns:
            Extracted text
        """
        try:
            # Try pdfplumber first (better text extraction)
            text = PDFParser._extract_with_pdfplumber(file_bytes)
            if text.strip():
                logger.info("Successfully extracted text with pdfplumber")
                return text
            
            # Fallback to PyMuPDF
            logger.info("Falling back to PyMuPDF")
            text = PDFParser._extract_with_pymupdf(file_bytes)
            if text.strip():
                return text
            
            # If still no text, might be scanned PDF - needs OCR
            logger.warning("No text extracted - PDF might be scanned (OCR required)")
            return ""
            
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {str(e)}")
            raise
    
    @staticmethod
    def _extract_with_pdfplumber(file_bytes: bytes) -> str:
        """Extract text using pdfplumber.
        
        Args:
            file_bytes: PDF file bytes
            
        Returns:
            Extracted text
        """
        text_parts = []
        
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {str(e)}")
        
        return "\n\n".join(text_parts)
    
    @staticmethod
    def _extract_with_pymupdf(file_bytes: bytes) -> str:
        """Extract text using PyMuPDF.
        
        Args:
            file_bytes: PDF file bytes
            
        Returns:
            Extracted text
        """
        text_parts = []
        
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num + 1}: {str(e)}")
        
        doc.close()
        return "\n\n".join(text_parts)
    
    @staticmethod
    def extract_tables(file_bytes: bytes) -> List[List[List[str]]]:
        """Extract tables from PDF.
        
        Args:
            file_bytes: PDF file bytes
            
        Returns:
            List of tables (each table is a list of rows, each row is a list of cells)
        """
        try:
            all_tables = []
            
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        tables = page.extract_tables()
                        if tables:
                            logger.info(f"Found {len(tables)} table(s) on page {page_num}")
                            all_tables.extend(tables)
                    except Exception as e:
                        logger.warning(f"Failed to extract tables from page {page_num}: {str(e)}")
            
            return all_tables
            
        except Exception as e:
            logger.error(f"Failed to extract PDF tables: {str(e)}")
            return []
    
    @staticmethod
    def extract_metadata(file_bytes: bytes) -> Dict[str, Any]:
        """Extract PDF metadata.
        
        Args:
            file_bytes: PDF file bytes
            
        Returns:
            PDF metadata
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            metadata = doc.metadata
            
            result = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'keywords': metadata.get('keywords', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'page_count': len(doc),
            }
            
            doc.close()
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {str(e)}")
            return {}
    
    @staticmethod
    def parse_construction_document(file_bytes: bytes) -> Dict[str, Any]:
        """Parse construction-specific information from PDF.
        
        Args:
            file_bytes: PDF file bytes
            
        Returns:
            Structured construction document data
        """
        text = PDFParser.extract_text(file_bytes)
        tables = PDFParser.extract_tables(file_bytes)
        metadata = PDFParser.extract_metadata(file_bytes)
        
        # Look for common construction document patterns
        result = {
            'text': text,
            'tables': tables,
            'metadata': metadata,
            'document_type': PDFParser._identify_document_type(text),
        }
        
        return result
    
    @staticmethod
    def _identify_document_type(text: str) -> Optional[str]:
        """Identify type of construction document.
        
        Args:
            text: Document text
            
        Returns:
            Document type or None
        """
        text_lower = text.lower()
        
        if 'bid' in text_lower and ('invitation' in text_lower or 'proposal' in text_lower):
            return 'bid_invitation'
        elif 'estimate' in text_lower or 'quote' in text_lower:
            return 'estimate'
        elif 'change order' in text_lower:
            return 'change_order'
        elif 'invoice' in text_lower or 'bill' in text_lower:
            return 'invoice'
        elif 'contract' in text_lower or 'agreement' in text_lower:
            return 'contract'
        elif 'drawing' in text_lower or 'blueprint' in text_lower or 'plan' in text_lower:
            return 'drawing'
        elif 'specification' in text_lower or 'spec' in text_lower:
            return 'specification'
        else:
            return 'unknown'

