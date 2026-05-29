import os
import logging
import numpy as np
from PIL import Image

logger = logging.getLogger("algonox.ocr")

class OCREngine:
    def __init__(self):
        self.paddle_ocr = None
        self.easy_ocr_reader = None
        self.initialized = False

    def initialize_engines(self):
        if self.initialized:
            return
        
        # 1. Try to load PaddleOCR
        try:
            logger.info("Attempting to initialize PaddleOCR...")
            from paddleocr import PaddleOCR
            # Initialize with English, enable angle classifier if needed
            self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            logger.info("PaddleOCR successfully initialized!")
        except Exception as e:
            logger.warning(f"PaddleOCR loading failed: {e}. Attempting fallback to EasyOCR...")
            
            # 2. Try to load EasyOCR
            try:
                import easyocr
                self.easy_ocr_reader = easyocr.Reader(['en'])
                logger.info("EasyOCR successfully initialized as fallback.")
            except Exception as e2:
                logger.error(f"EasyOCR also failed to initialize: {e2}. OCR will operate on structural PDF text extraction only.")
        
        self.initialized = True

    def extract_text_from_image_bytes(self, image_bytes: bytes) -> str:
        """
        Extracts text from image file bytes.
        """
        self.initialize_engines()
        import io
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to numpy array as expected by both OCR tools
            img_np = np.array(image.convert("RGB"))
            
            if self.paddle_ocr:
                logger.info("Executing PaddleOCR image extraction...")
                result = self.paddle_ocr.ocr(img_np, cls=True)
                if not result or not result[0]:
                    return ""
                text_lines = []
                for line in result[0]:
                    text_lines.append(line[1][0])
                return "\n".join(text_lines)
                
            elif self.easy_ocr_reader:
                logger.info("Executing EasyOCR image extraction...")
                result = self.easy_ocr_reader.readtext(img_np)
                if not result:
                    return ""
                text_lines = [item[1] for item in result]
                return "\n".join(text_lines)
                
            else:
                logger.error("No active OCR engines available.")
                return ""
        except Exception as e:
            logger.error(f"Error during OCR image text extraction: {e}")
            return ""

    def extract_text_from_pdf_page(self, pdf_page_image_np) -> str:
        """
        Extracts text from a pre-rendered PDF page numpy array.
        """
        self.initialize_engines()
        try:
            if self.paddle_ocr:
                result = self.paddle_ocr.ocr(pdf_page_image_np, cls=True)
                if not result or not result[0]:
                    return ""
                return "\n".join([line[1][0] for line in result[0]])
            elif self.easy_ocr_reader:
                result = self.easy_ocr_reader.readtext(pdf_page_image_np)
                if not result:
                    return ""
                return "\n".join([item[1] for item in result])
            else:
                return ""
        except Exception as e:
            logger.error(f"Error rendering OCR on PDF page: {e}")
            return ""
