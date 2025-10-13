"""Image parser with OCR capabilities."""
import io
from typing import Dict, Any, Optional
from PIL import Image
import pytesseract

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from shared.logger import setup_logger

logger = setup_logger(__name__)


class ImageParser:
    """Parse images to extract text using OCR."""
    
    @staticmethod
    def extract_text(file_bytes: bytes, language: str = 'eng') -> str:
        """Extract text from image using OCR.
        
        Args:
            file_bytes: Image file bytes
            language: Tesseract language code (default: 'eng')
            
        Returns:
            Extracted text
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(file_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Perform OCR
            text = pytesseract.image_to_string(image, lang=language)
            
            logger.info(f"Extracted {len(text)} characters from image using OCR")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract text from image: {str(e)}")
            # Check if Tesseract is installed
            if "tesseract is not installed" in str(e).lower():
                logger.error("Tesseract OCR is not installed. Please install it to enable OCR functionality.")
            raise
    
    @staticmethod
    def extract_text_with_confidence(file_bytes: bytes, language: str = 'eng') -> Dict[str, Any]:
        """Extract text with confidence scores.
        
        Args:
            file_bytes: Image file bytes
            language: Tesseract language code
            
        Returns:
            Dictionary with text and confidence data
        """
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extract text
            text = pytesseract.image_to_string(image, lang=language)
            
            result = {
                'text': text.strip(),
                'confidence': avg_confidence,
                'word_count': len([w for w in data['text'] if w.strip()]),
            }
            
            logger.info(f"OCR completed with {avg_confidence:.1f}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract text with confidence: {str(e)}")
            raise
    
    @staticmethod
    def preprocess_image(file_bytes: bytes) -> bytes:
        """Preprocess image for better OCR results.
        
        Args:
            file_bytes: Image file bytes
            
        Returns:
            Preprocessed image bytes
        """
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            # Convert to grayscale
            image = image.convert('L')
            
            # Increase contrast (simple implementation)
            # For production, consider more sophisticated preprocessing
            
            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to preprocess image: {str(e)}")
            return file_bytes  # Return original on failure
    
    @staticmethod
    def get_image_metadata(file_bytes: bytes) -> Dict[str, Any]:
        """Extract image metadata.
        
        Args:
            file_bytes: Image file bytes
            
        Returns:
            Image metadata
        """
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            metadata = {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height,
            }
            
            # Try to get EXIF data
            try:
                exif = image._getexif()
                if exif:
                    metadata['exif'] = exif
            except:
                pass
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract image metadata: {str(e)}")
            return {}

