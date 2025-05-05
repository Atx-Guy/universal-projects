# routes/pdf_routes.py
import os
import logging
import zipfile
from flask import Blueprint, request, jsonify, current_app, send_file, render_template
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from models import db, Conversion
from services.pdf_service import PDFService
from utils.file_utils import allowed_file, save_uploaded_file, create_download_response, get_file_extension

# Configure logging
logger = logging.getLogger(__name__)

pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

# Initialize services
pdf_service = PDFService()

# Routes for PDF operations
@pdf_bp.route('/', methods=['GET'])
def pdf_operations():
    """Render PDF operations dashboard."""
    return render_template('pdf/dashboard.html')

@pdf_bp.route('/split', methods=['GET', 'POST'])
def split_pdf():
    """Split PDF into multiple files."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get page ranges from form
            page_ranges = request.form.get('page_ranges', '').split(',')
            page_ranges = [pr.strip() for pr in page_ranges if pr.strip()]
            
            if not page_ranges:
                return jsonify({'error': 'Please specify at least one page range'}), 400
            
            # Split PDF
            output_paths = pdf_service.split_pdf(input_path, page_ranges)
            
            # If only one output file, send it directly
            if len(output_paths) == 1:
                output_filename = f"split_{secure_filename(os.path.splitext(file.filename)[0])}.pdf"
                
                # Record conversion for logged in users
                if current_user.is_authenticated:
                    conversion = Conversion(
                        user_id=current_user.id,
                        operation='pdf_split',
                        input_filename=file.filename,
                        output_filename=output_filename
                    )
                    db.session.add(conversion)
                    db.session.commit()
                
                return create_download_response(output_paths[0], output_filename)
            
            # If multiple outputs, zip them
            zip_path = os.path.join(current_app.config['TEMP_FOLDER'], 'split_pages.zip')
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for i, path in enumerate(output_paths):
                    file_name = f"split_part_{i+1}.pdf"
                    zip_file.write(path, file_name)
                    # Clean up individual files after adding to zip
                    os.remove(path)
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_split_multiple',
                    input_filename=file.filename,
                    output_filename='split_pages.zip'
                )
                db.session.add(conversion)
                db.session.commit()
            
            return create_download_response(zip_path, 'split_pages.zip')
        
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            return jsonify({'error': 'An error occurred during PDF splitting'}), 500
    
    return render_template('pdf/split.html')

@pdf_bp.route('/merge', methods=['GET', 'POST'])
def merge_pdfs():
    """Merge multiple PDFs into one."""
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files[]')
        if not files or len(files) < 2:
            return jsonify({'error': 'Please upload at least two PDF files to merge'}), 400
        
        try:
            # Save uploaded PDFs
            input_paths = []
            for file in files:
                if file and allowed_file(file.filename, ['pdf']):
                    input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
                    input_paths.append(input_path)
            
            if len(input_paths) < 2:
                return jsonify({'error': 'At least two valid PDF files are required'}), 400
            
            # Get custom output filename
            output_filename = request.form.get('output_filename')
            if output_filename:
                output_filename = secure_filename(output_filename)
                if not output_filename.lower().endswith('.pdf'):
                    output_filename += '.pdf'
            else:
                output_filename = 'merged.pdf'
            
            # Merge PDFs
            output_path = pdf_service.merge_pdfs(input_paths)
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_merge',
                    input_filename=','.join([f.filename for f in files]),
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input files
            for path in input_paths:
                try:
                    os.remove(path)
                except Exception as e:
                    logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except Exception as e:
            logger.error(f"Error merging PDFs: {str(e)}")
            return jsonify({'error': 'An error occurred during PDF merging'}), 500
    
    return render_template('pdf/merge.html')

@pdf_bp.route('/compress', methods=['GET', 'POST'])
def compress_pdf():
    """Compress PDF to reduce file size."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get compression quality
            quality = request.form.get('quality', 'medium')
            if quality not in ['low', 'medium', 'high']:
                quality = 'medium'
            
            # Compress PDF
            output_path = pdf_service.compress_pdf(input_path, quality)
            
            # Determine output filename
            output_filename = f"compressed_{secure_filename(os.path.splitext(file.filename)[0])}.pdf"
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_compress',
                    input_filename=file.filename,
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except Exception as e:
            logger.error(f"Error compressing PDF: {str(e)}", exc_info=True)  # Log full stack trace
            error_message = str(e)
            if len(error_message) > 100:  # Trim very long messages
                error_message = error_message[:100] + "..."
            return jsonify({'error': f"PDF compression failed: {error_message}"}), 500
    
    return render_template('pdf/compress.html')

@pdf_bp.route('/protect', methods=['GET', 'POST'])
def protect_pdf():
    """Add password protection to PDF."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get passwords
            user_password = request.form.get('user_password')
            owner_password = request.form.get('owner_password')
            
            if not user_password:
                return jsonify({'error': 'User password is required'}), 400
            
            # Protect PDF
            output_path = pdf_service.add_password(input_path, user_password, owner_password)
            
            # Determine output filename
            output_filename = f"protected_{secure_filename(os.path.splitext(file.filename)[0])}.pdf"
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_protect',
                    input_filename=file.filename,
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except Exception as e:
            logger.error(f"Error protecting PDF: {str(e)}")
            return jsonify({'error': 'An error occurred during PDF protection'}), 500
    
    return render_template('pdf/protect.html')

@pdf_bp.route('/unlock', methods=['GET', 'POST'])
def unlock_pdf():
    """Remove password protection from PDF."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get password
            password = request.form.get('password')
            
            if not password:
                return jsonify({'error': 'Password is required'}), 400
            
            # Unlock PDF
            output_path = pdf_service.remove_password(input_path, password)
            
            # Determine output filename
            output_filename = f"unlocked_{secure_filename(os.path.splitext(file.filename)[0])}.pdf"
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_unlock',
                    input_filename=file.filename,
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Error unlocking PDF: {str(e)}")
            return jsonify({'error': 'An error occurred during PDF unlocking'}), 500
    
    return render_template('pdf/unlock.html')

@pdf_bp.route('/rotate', methods=['GET', 'POST'])
def rotate_pdf():
    """Rotate pages in a PDF."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get rotation parameters
            rotation = int(request.form.get('rotation', 90))
            if rotation not in [90, 180, 270]:
                rotation = 90
            
            pages_param = request.form.get('pages', 'all')
            if pages_param == 'all':
                pages = 'all'
            else:
                # Parse pages like "1,3,5-7"
                pages = []
                parts = pages_param.split(',')
                for part in parts:
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        pages.extend(range(start, end + 1))
                    else:
                        pages.append(int(part))
            
            # Rotate PDF
            output_path = pdf_service.rotate_pdf(input_path, rotation, pages)
            
            # Determine output filename
            output_filename = f"rotated_{secure_filename(os.path.splitext(file.filename)[0])}.pdf"
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_rotate',
                    input_filename=file.filename,
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except Exception as e:
            logger.error(f"Error rotating PDF: {str(e)}")
            return jsonify({'error': 'An error occurred during PDF rotation'}), 500
    
    return render_template('pdf/rotate.html')

@pdf_bp.route('/watermark', methods=['GET', 'POST'])
def watermark_pdf():
    """Add text watermark to PDF."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get watermark parameters
            watermark_text = request.form.get('watermark_text', 'Watermark')
            position = request.form.get('position', 'center')
            if position not in ['center', 'top', 'bottom']:
                position = 'center'
            
            # Get color option
            color = request.form.get('color', 'black')
            if color not in ['black', 'white']:
                color = 'black'
            
            # Convert opacity from percentage (10-90) to decimal (0.1-0.9)
            opacity = float(request.form.get('opacity', 30)) / 100
            opacity = max(0.1, min(0.9, opacity))
            
            # Add watermark
            output_path = pdf_service.add_watermark(input_path, watermark_text, position, opacity, color)
            
            # Determine output filename
            output_filename = f"watermarked_{secure_filename(os.path.splitext(file.filename)[0])}.pdf"
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_watermark',
                    input_filename=file.filename,
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
            
        except Exception as e:
            logger.error(f"Error adding watermark to PDF: {str(e)}")
            return jsonify({'error': 'An error occurred while adding watermark'}), 500
    
    return render_template('pdf/watermark.html')

@pdf_bp.route('/to-images', methods=['GET', 'POST'])
def pdf_to_images():
    """Convert PDF to images."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF file'}), 400
            
        try:
            # Initialize output_paths to empty list
            output_paths = []
            
            # Save uploaded PDF
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get and validate conversion parameters
            image_format = request.form.get('format', 'png').lower()
            if image_format not in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
                return jsonify({'error': 'Invalid image format selected'}), 400
            
            try:
                dpi = int(request.form.get('dpi', 200))
                if not (72 <= dpi <= 600):
                    return jsonify({'error': 'DPI must be between 72 and 600'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid DPI value'}), 400
            
            # Convert PDF to images
            output_paths = pdf_service.pdf_to_images(input_path, image_format, dpi)
            
            if not output_paths:
                raise ValueError("No images were generated")
                
            # Create output filename base
            base_filename = secure_filename(os.path.splitext(file.filename)[0])
            
            # If only one page, return directly
            if len(output_paths) == 1:
                output_filename = f"{base_filename}_page.{image_format}"
                
                # Record conversion
                if current_user.is_authenticated:
                    conversion = Conversion(
                        user_id=current_user.id,
                        operation='pdf_to_image',
                        input_filename=file.filename,
                        output_filename=output_filename
                    )
                    db.session.add(conversion)
                    db.session.commit()
                
                return create_download_response(output_paths[0], output_filename)
            
            # For multiple pages, create a zip file
            zip_path = os.path.join(current_app.config['TEMP_FOLDER'], f"{base_filename}_images.zip")
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for i, path in enumerate(output_paths, 1):
                        file_name = f"{base_filename}_page_{i}.{image_format}"
                        zip_file.write(path, file_name)
                        # Clean up individual image file after adding to zip
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.warning(f"Failed to remove temporary image: {str(e)}")
            except Exception as e:
                logger.error(f"Error creating zip file: {str(e)}")
                # Clean up any remaining images
                for path in output_paths:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                raise
            
            # Record conversion
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_to_images',
                    input_filename=file.filename,
                    output_filename=f"{base_filename}_images.zip"
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.warning(f"Failed to remove input file: {str(e)}")
            
            return create_download_response(zip_path, f"{base_filename}_images.zip")
            
        except FileNotFoundError as e:
            logger.error(f"Input file error: {str(e)}")
            return jsonify({'error': 'The uploaded file could not be processed'}), 400
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return jsonify({'error': str(e)}), 400
            
        except RuntimeError as e:
            logger.error(f"Conversion error: {str(e)}")
            return jsonify({'error': 'PDF to image conversion is not available. Please ensure all required dependencies are installed.'}), 500
            
        except Exception as e:
            logger.error(f"Unexpected error in PDF to images conversion: {str(e)}", exc_info=True)
            return jsonify({'error': 'An unexpected error occurred during conversion'}), 500
        
        finally:
            # Clean up temporary files in case of any error
            for path in output_paths:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
    
    return render_template('pdf/to_images.html')

@pdf_bp.route('/from-images', methods=['GET', 'POST'])
def images_to_pdf():
    """Convert images to PDF."""
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files[]')
        if not files:
            return jsonify({'error': 'Please upload at least one image file'}), 400
        
        # Check file types
        image_extensions = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp']
        
        try:
            # Save uploaded images
            input_paths = []
            for file in files:
                ext = get_file_extension(file.filename)
                if file and ext.lower() in image_extensions:
                    input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
                    input_paths.append(input_path)
            
            if not input_paths:
                return jsonify({'error': 'No valid image files were uploaded'}), 400
            
            # Get custom output filename
            output_filename = request.form.get('output_filename')
            if output_filename:
                output_filename = secure_filename(output_filename)
                if not output_filename.lower().endswith('.pdf'):
                    output_filename += '.pdf'
            else:
                output_filename = 'images.pdf'
            
            # Convert images to PDF
            output_path = pdf_service.images_to_pdf(input_paths)
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='images_to_pdf',
                    input_filename=','.join([f.filename for f in files]),
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input files
            for path in input_paths:
                try:
                    os.remove(path)
                except Exception as e:
                    logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except Exception as e:
            logger.error(f"Error converting images to PDF: {str(e)}")
            return jsonify({'error': 'An error occurred during conversion'}), 500
    
    return render_template('pdf/from_images.html')

@pdf_bp.route('/ocr', methods=['GET', 'POST'])
def ocr_pdf():
    """Perform OCR on a PDF."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename, ['pdf']):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        try:
            # Save uploaded PDF with temp directory
            input_path = save_uploaded_file(file, directory=current_app.config['TEMP_FOLDER'])
            
            # Get OCR parameters
            output_format = request.form.get('output_format', 'pdf')
            if output_format not in ['pdf', 'txt']:
                output_format = 'pdf'
            
            language = request.form.get('language', 'eng')
            
            # Perform OCR
            output_path = pdf_service.perform_ocr(input_path, output_format, language)
            
            # Determine output filename
            base_name = secure_filename(os.path.splitext(file.filename)[0])
            output_filename = f"ocr_{base_name}.{output_format}"
            
            # Record conversion for logged in users
            if current_user.is_authenticated:
                conversion = Conversion(
                    user_id=current_user.id,
                    operation='pdf_ocr',
                    input_filename=file.filename,
                    output_filename=output_filename
                )
                db.session.add(conversion)
                db.session.commit()
            
            # Clean up input file
            try:
                os.remove(input_path)
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")
            
            return create_download_response(output_path, output_filename)
        
        except Exception as e:
            logger.error(f"Error performing OCR: {str(e)}")
            return jsonify({'error': 'An error occurred during OCR processing'}), 500
    
    return render_template('pdf/ocr.html')