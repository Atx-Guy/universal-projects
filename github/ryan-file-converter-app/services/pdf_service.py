# services/pdf_service.py
import os
import logging
import tempfile
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
import io
import uuid
import shutil
from PIL import Image
import subprocess
import sys

logger = logging.getLogger(__name__)

class PDFService:
    """Service for handling various PDF operations with reduced dependencies."""
    
    def __init__(self, temp_dir='temp'):
        """Initialize PDF service with temporary directory for processing."""
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check for required dependencies and set availability flags."""
        self.has_pymupdf = False
        self.has_pdf2image = False
        self.has_poppler = False
        
        # Check for PyMuPDF
        try:
            import fitz
            # Test PyMuPDF functionality
            test_pdf = os.path.join(self.temp_dir, "test.pdf")
            with open(test_pdf, 'wb') as f:
                f.write(b'%PDF-1.4\n')  # Minimal valid PDF
            try:
                doc = fitz.open(test_pdf)
                doc.close()
                self.has_pymupdf = True
                logger.info("PyMuPDF (fitz) is available and working")
            except Exception as e:
                logger.warning(f"PyMuPDF failed functionality test: {str(e)}")
            finally:
                if os.path.exists(test_pdf):
                    os.remove(test_pdf)
        except ImportError:
            logger.warning("PyMuPDF is not available")
        
        # Check for pdf2image and poppler
        try:
            from pdf2image import convert_from_path
            
            # Check for poppler installation
            if sys.platform.startswith('win'):
                poppler_path = os.environ.get('POPPLER_PATH')
                if not poppler_path:
                    logger.warning("POPPLER_PATH environment variable not set on Windows")
                else:
                    self.has_poppler = os.path.exists(os.path.join(poppler_path, 'pdftoppm.exe'))
            else:
                # On Linux/Mac, check if pdftoppm is in PATH
                try:
                    subprocess.run(['pdftoppm', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.has_poppler = True
                except (subprocess.SubprocessError, FileNotFoundError):
                    logger.warning("poppler-utils is not installed or not in PATH")
            
            if self.has_poppler:
                self.has_pdf2image = True
                logger.info("pdf2image and poppler are available")
            else:
                logger.warning("poppler-utils is required for pdf2image to work")
        except ImportError:
            logger.warning("pdf2image is not available")
        
        if not (self.has_pymupdf or (self.has_pdf2image and self.has_poppler)):
            logger.warning("No PDF to image conversion methods are available")
    
    def _get_temp_path(self, prefix='pdf_', suffix='.pdf'):
        """Generate a temporary file path."""
        return os.path.join(self.temp_dir, f"{prefix}{uuid.uuid4()}{suffix}")
    
    def split_pdf(self, input_path, page_ranges):
        """
        Split a PDF file according to specified page ranges.
        
        Args:
            input_path (str): Path to the input PDF file
            page_ranges (list): List of page ranges, e.g. ['1-3', '5-7', '9']
        
        Returns:
            list: List of paths to split PDF files
        """
        try:
            reader = PdfReader(input_path)
            output_paths = []
            
            for page_range in page_ranges:
                writer = PdfWriter()
                
                # Parse page range (e.g., '1-3' or '5')
                if '-' in page_range:
                    start, end = map(int, page_range.split('-'))
                else:
                    start = end = int(page_range)
                
                # Adjust for 0-based indexing
                start = max(0, start - 1)
                end = min(len(reader.pages) - 1, end - 1)
                
                # Add pages to writer
                for page_num in range(start, end + 1):
                    writer.add_page(reader.pages[page_num])
                
                # Save split PDF
                output_path = self._get_temp_path(prefix=f'split_{page_range}_')
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                output_paths.append(output_path)
            
            return output_paths
            
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            raise
    
    def merge_pdfs(self, input_paths, output_filename=None):
        """
        Merge multiple PDFs into a single PDF.
        
        Args:
            input_paths (list): List of paths to input PDF files
            output_filename (str, optional): Custom filename for the merged PDF
        
        Returns:
            str: Path to the merged PDF file
        """
        try:
            merger = PdfMerger()
            
            # Add each PDF to the merger
            for path in input_paths:
                merger.append(path)
            
            # Generate output path
            if output_filename:
                output_path = self._get_temp_path(prefix=f"{output_filename}_")
            else:
                output_path = self._get_temp_path(prefix='merged_')
            
            # Write merged PDF
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            
            merger.close()
            return output_path
            
        except Exception as e:
            logger.error(f"Error merging PDFs: {str(e)}")
            raise
    
    def add_password(self, input_path, user_password, owner_password=None):
        """
        Add password protection to a PDF.
        
        Args:
            input_path (str): Path to the input PDF file
            user_password (str): Password required to open the document
            owner_password (str, optional): Password for full access rights
        
        Returns:
            str: Path to the password-protected PDF
        """
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Add all pages to the writer
            for page in reader.pages:
                writer.add_page(page)
            
            # If owner_password is not provided, use user_password
            if not owner_password:
                owner_password = user_password
            
            # Encrypt the PDF
            writer.encrypt(user_password, owner_password)
            
            # Save protected PDF
            output_path = self._get_temp_path(prefix='protected_')
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding password to PDF: {str(e)}")
            raise
    
    def remove_password(self, input_path, password):
        """
        Remove password protection from a PDF.
        
        Args:
            input_path (str): Path to the input PDF file
            password (str): Current password of the PDF
        
        Returns:
            str: Path to the unprotected PDF
        """
        try:
            # Open encrypted PDF
            reader = PdfReader(input_path)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                # Try to decrypt with provided password
                success = reader.decrypt(password)
                if not success:
                    raise ValueError("Incorrect password")
            
            # Create a new unencrypted PDF
            writer = PdfWriter()
            
            # Add all pages to the writer
            for page in reader.pages:
                writer.add_page(page)
            
            # Save unprotected PDF
            output_path = self._get_temp_path(prefix='unprotected_')
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error removing password from PDF: {str(e)}")
            raise
    
    def rotate_pdf(self, input_path, rotation, pages='all'):
        """
        Rotate pages in a PDF (simplified version using PyPDF2).
        
        Args:
            input_path (str): Path to the input PDF file
            rotation (int): Rotation angle in degrees (90, 180, 270)
            pages (str or list): 'all' or list of page numbers
        
        Returns:
            str: Path to the rotated PDF
        """
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Determine which pages to rotate
            if pages == 'all':
                page_indices = range(len(reader.pages))
            else:
                # Convert page numbers to 0-based indices
                page_indices = [p - 1 for p in pages if 0 < p <= len(reader.pages)]
            
            # Process each page
            for i in range(len(reader.pages)):
                page = reader.pages[i]
                if i in page_indices:
                    # PyPDF2 rotation is counterclockwise, so we negate the angle
                    page.rotate(rotation)
                writer.add_page(page)
            
            # Save rotated PDF
            output_path = self._get_temp_path(prefix='rotated_')
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error rotating PDF: {str(e)}")
            raise
    
    def compress_pdf(self, input_path, quality='medium'):
        """
        Compress a PDF file to reduce its size.
        
        Args:
            input_path (str): Path to the input PDF file
            quality (str): Compression quality - 'low', 'medium', or 'high'
        
        Returns:
            str: Path to the compressed PDF file
        """
        try:
            # Generate output path
            output_path = self._get_temp_path(prefix='compressed_')
            
            # First attempt: Try using PyPDF2's built-in compression
            try:
                reader = PdfReader(input_path)
                writer = PdfWriter()
                
                # Copy pages with compression enabled
                for page in reader.pages:
                    writer.add_page(page)
                
                # Set compression parameters
                writer.add_metadata(reader.metadata or {})
                
                # Save with compression
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                # Verify the output file is valid
                try:
                    PdfReader(output_path)
                    return output_path
                except Exception:
                    logger.warning("Initial compression produced invalid PDF, trying alternative method")
                    
            except Exception as e:
                logger.warning(f"First compression attempt failed: {str(e)}")
            
            # Second attempt: Try using PyMuPDF if available
            try:
                import fitz
                logger.info("Using PyMuPDF for PDF compression")
                
                # Open the PDF
                pdf = fitz.open(input_path)
                
                # Quality settings
                quality_settings = {
                    'low': {'garbage': 4, 'clean': True, 'deflate': True, 'linear': True},
                    'medium': {'garbage': 3, 'clean': True, 'deflate': True},
                    'high': {'garbage': 2, 'clean': True}
                }
                
                settings = quality_settings.get(quality, quality_settings['medium'])
                
                # Save with compression options
                pdf.save(output_path, **settings)
                pdf.close()
                
                # Verify the output file is valid
                try:
                    PdfReader(output_path)
                    return output_path
                except Exception:
                    logger.warning("PyMuPDF compression produced invalid PDF, falling back to simple copy")
                    
            except ImportError:
                logger.warning("PyMuPDF not available")
            except Exception as e:
                logger.warning(f"PyMuPDF compression failed: {str(e)}")
            
            # Final fallback: Copy the file if compression fails
            logger.warning("Compression failed, copying original file")
            shutil.copy2(input_path, output_path)
            return output_path
                
        except Exception as e:
            logger.error(f"Error during PDF compression: {str(e)}", exc_info=True)
            raise RuntimeError(f"PDF compression failed: {str(e)}")
    
    def images_to_pdf(self, image_paths, output_filename=None):
        """
        Convert images to a PDF using Pillow.
        
        Args:
            image_paths (list): List of paths to image files
            output_filename (str, optional): Custom filename for the output PDF
        
        Returns:
            str: Path to the generated PDF file
        """
        try:
            # Generate output path
            if output_filename:
                output_path = self._get_temp_path(prefix=f"{output_filename}_")
            else:
                output_path = self._get_temp_path(prefix='images_to_pdf_')
            
            # Use Pillow to create a PDF
            from PIL import Image
            
            # Open the first image to get dimensions
            images = []
            for path in image_paths:
                img = Image.open(path).convert('RGB')
                images.append(img)
            
            # Save as PDF
            if images:
                images[0].save(
                    output_path, 
                    save_all=True, 
                    append_images=images[1:] if len(images) > 1 else []
                )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting images to PDF: {str(e)}")
            raise
    
    def perform_ocr(self, input_path, output_format='pdf', language='eng'):
        """
        Perform OCR on a PDF file.
        
        Args:
            input_path (str): Path to the input PDF file
            output_format (str): Output format ('pdf' or 'txt')
            language (str): OCR language code
        
        Returns:
            str: Path to the OCR result file
        """
        try:
            from services.ocr_service import OCRService
            ocr_service = OCRService(self.temp_dir)
            
            # Perform OCR using OCR service
            output_path = ocr_service.perform_ocr(input_path, output_format, language)
            
            if not output_path or not os.path.exists(output_path):
                raise RuntimeError("OCR processing failed to produce output file")
            
            return output_path
            
        except ImportError:
            logger.error("OCR service not available")
            raise RuntimeError("OCR functionality is not available. Please ensure pytesseract is installed.")
        except Exception as e:
            logger.error(f"Error performing OCR: {str(e)}")
            raise
    
    def add_watermark(self, input_path, watermark_text, position='center', opacity=0.3, color='black'):
        """
        Add text watermark to a PDF.
        
        Args:
            input_path (str): Path to the input PDF file
            watermark_text (str): Text to use as watermark
            position (str): Position of watermark ('center', 'top', 'bottom')
            opacity (float): Opacity of watermark (0-1)
            color (str): Color of watermark text ('black' or 'white')
        
        Returns:
            str: Path to the watermarked PDF
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.colors import white, black
            from PyPDF2 import PdfReader, PdfWriter
            import io
            
            # Create watermark PDF using ReportLab
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            width, height = letter
            
            # Configure text appearance
            c.setFont("Helvetica-Bold", 72)  # Larger, bold font
            
            # Calculate text width for centering
            text_width = c.stringWidth(watermark_text, "Helvetica-Bold", 72)
            
            # Calculate diagonal size for text scaling
            diagonal = (width**2 + height**2)**0.5
            scale_factor = diagonal / text_width
            font_size = min(72 * scale_factor * 0.5, 144)  # Cap maximum size
            c.setFont("Helvetica-Bold", font_size)
            
            # Recalculate text width with new font size
            text_width = c.stringWidth(watermark_text, "Helvetica-Bold", font_size)
            
            # Set opacity and color
            c.setFillAlpha(opacity)
            c.setFillColor(white if color == 'white' else black)
            
            # Position text based on selected position
            if position == 'center':
                x = (width - text_width) / 2
                y = height / 2
            elif position == 'top':
                x = (width - text_width) / 2
                y = height - 100
            else:  # bottom
                x = (width - text_width) / 2
                y = 100
            
            # Save initial state
            c.saveState()
            
            # Translate to position, then rotate around that point
            c.translate(x, y)
            c.rotate(45)
            c.drawString(0, 0, watermark_text)
            
            # Restore state
            c.restoreState()
            c.save()
            
            # Move to beginning of buffer
            packet.seek(0)
            
            # Create PDF from the buffer
            watermark = PdfReader(packet)
            existing_pdf = PdfReader(input_path)
            output = PdfWriter()
            
            # Add watermark to each page
            for page in existing_pdf.pages:
                page.merge_page(watermark.pages[0])
                output.add_page(page)
            
            # Write output file
            output_path = self._get_temp_path(prefix='watermarked_')
            with open(output_path, 'wb') as output_file:
                output.write(output_file)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error adding watermark: {str(e)}")
            raise
    
    def cleanup_temp_files(self, file_paths=None):
        """
        Clean up temporary files.
        
        Args:
            file_paths (list, optional): List of specific file paths to clean up.
                                        If None, all files in temp_dir will be removed.
        """
        try:
            if file_paths:
                for path in file_paths:
                    if os.path.exists(path):
                        os.remove(path)
            else:
                # Clean all files in temp directory
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")
    
    def pdf_to_images(self, input_path, image_format='png', dpi=200):
        """
        Convert PDF pages to images using multiple fallback methods.
        
        Args:
            input_path (str): Path to the input PDF file
            image_format (str): Output image format ('png', 'jpg', 'tiff', 'bmp')
            dpi (int): Resolution in DPI (72-600)
        
        Returns:
            list: List of paths to generated image files
        
        Raises:
            RuntimeError: If no conversion method is available or if conversion fails
            FileNotFoundError: If input file doesn't exist
            ValueError: If image format or DPI is invalid
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input PDF file not found: {input_path}")
        
        # Normalize image format
        image_format = image_format.lower()
        if image_format == 'jpeg':
            image_format = 'jpg'
            
        # Validate image format
        if image_format not in ['png', 'jpg', 'tiff', 'bmp']:
            raise ValueError(f"Unsupported image format: {image_format}")
        
        # Validate DPI
        dpi = max(72, min(600, dpi))  # Ensure DPI is between 72 and 600
        
        errors = []
        
        # Try PyMuPDF first
        if self.has_pymupdf:
            try:
                import fitz
                logger.info("Converting PDF to images using PyMuPDF")
                
                pdf = fitz.open(input_path)
                output_paths = []
                
                for page_num in range(len(pdf)):
                    page = pdf[page_num]
                    zoom = dpi / 72  # Default PDF DPI is 72
                    matrix = fitz.Matrix(zoom, zoom)
                    
                    # Use RGB for JPEG, RGBA for others
                    if image_format == 'jpg':
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                    else:
                        pix = page.get_pixmap(matrix=matrix)
                    
                    output_path = os.path.join(
                        self.temp_dir,
                        f'page_{page_num + 1}.{image_format}'
                    )
                    
                    # Save with proper format
                    if image_format == 'jpg':
                        pix.save(output_path, "jpeg")
                    else:
                        pix.save(output_path)
                        
                    output_paths.append(output_path)
                
                pdf.close()
                logger.info(f"Successfully converted {len(output_paths)} pages using PyMuPDF")
                return output_paths
                
            except Exception as e:
                error_msg = f"PyMuPDF conversion failed: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        # Try pdf2image as fallback
        if self.has_pdf2image and self.has_poppler:
            try:
                from pdf2image import convert_from_path
                logger.info("Converting PDF to images using pdf2image")
                
                images = convert_from_path(
                    input_path,
                    dpi=dpi,
                    fmt=image_format,
                    poppler_path=None  # Use system poppler
                )
                
                output_paths = []
                for i, image in enumerate(images):
                    output_path = os.path.join(
                        self.temp_dir,
                        f'page_{i + 1}.{image_format}'
                    )
                    
                    if image_format == 'jpg':
                        image.save(output_path, format='JPEG', quality=95)
                    else:
                        image.save(output_path, format=image_format.upper())
                        output_paths.append(output_path)
                
                logger.info(f"Successfully converted {len(output_paths)} pages using pdf2image")
                return output_paths
                
            except Exception as e:
                error_msg = f"pdf2image conversion failed: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
    
        # If all methods failed
        error_messages = "\n".join(errors)
        raise RuntimeError(
            f"PDF to image conversion failed. No working conversion method available.\n"
            f"Install PyMuPDF or pdf2image+poppler to enable this feature.\n"
            f"Errors encountered:\n{error_messages}"
        )