# Modified app.py with proper error handling for missing dependencies
import os
import logging
import traceback
import uuid
from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User
from models.conversion import Conversion
from routes.pdf_routes import pdf_bp
from routes.auth_routes import auth_bp
from routes.conversion_routes import conversion_bp
from routes.api_routes import api_bp
from utils.file_utils import (
    create_temp_directory, 
    allowed_file, 
    get_file_extension, 
    get_file_mime_type,
    generate_unique_filename,
    get_file_category
)

import config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config.DevelopmentConfig)

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# Configure database
db.init_app(app)

# Initialize services with proper error handling
try:
    from services.audio_service import AudioService
    audio_service = AudioService()
    logger.info("Audio service initialized successfully")
except ImportError as e:
    logger.warning(f"Audio service initialization error: {str(e)}")
    logger.warning("Audio conversion features will be limited")
    # Create a stub AudioService class
    class AudioService:
        def convert_audio(self, *args, **kwargs):
            raise ImportError("Audio conversion is not available due to missing dependencies")
    audio_service = AudioService()

try:
    from services.image_service import ImageService
    image_service = ImageService()
    logger.info("Image service initialized successfully")
except ImportError as e:
    logger.warning(f"Image service initialization error: {str(e)}")
    logger.warning("Image conversion features will be limited")
    # Create a stub ImageService class
    class ImageService:
        def convert_image(self, *args, **kwargs):
            raise ImportError("Image conversion is not available due to missing dependencies")
    image_service = ImageService()

try:
    from services.document_service import DocumentService
    document_service = DocumentService()
    logger.info("Document service initialized successfully")
except ImportError as e:
    logger.warning(f"Document service initialization error: {str(e)}")
    logger.warning("Document conversion features will be limited")
    # Create a stub DocumentService class
    class DocumentService:
        def convert_document(self, *args, **kwargs):
            raise ImportError("Document conversion is not available due to missing dependencies")
    document_service = DocumentService()

try:
    from services.pdf_service import PDFService
    pdf_service = PDFService()
    logger.info("PDF service initialized successfully")
except ImportError as e:
    logger.warning(f"PDF service initialization error: {str(e)}")
    logger.warning("PDF conversion features will be limited")
    # Create a stub PDFService class
    class PDFService:
        def __init__(self, temp_dir='temp'):
            self.temp_dir = temp_dir
            os.makedirs(temp_dir, exist_ok=True)
            
        def split_pdf(self, *args, **kwargs):
            raise ImportError("PDF splitting is not available due to missing dependencies")
        
        def merge_pdfs(self, *args, **kwargs):
            raise ImportError("PDF merging is not available due to missing dependencies")
            
        # Add stubs for other PDF methods as needed
    pdf_service = PDFService()

# Import and initialize feature detector after services are set up
from utils.feature_detector import FeatureDetector

# Detect available features
available_features = {
    'pdf': FeatureDetector.get_pdf_features(),
    'document': FeatureDetector.get_document_features(),
    'image': FeatureDetector.get_image_features(),
    'audio': FeatureDetector.get_audio_features()
}

# Log available features
logger.info("Available PDF features: %s", available_features['pdf'])
logger.info("Available document features: %s", available_features['document'])
logger.info("Available image features: %s", available_features['image'])
logger.info("Available audio features: %s", available_features['audio'])

# Create temp directories
create_temp_directory(app.config['TEMP_FOLDER'])

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(conversion_bp)
app.register_blueprint(api_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_features():
    """Make available features accessible in templates."""
    return {
        'features': available_features
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get recent conversions for dashboard
    recent_conversions = []
    if current_user.is_authenticated:
        recent_conversions = Conversion.query.filter_by(user_id=current_user.id)\
                                           .order_by(Conversion.created_at.desc())\
                                           .limit(5)\
                                           .all()
    return render_template('dashboard.html', recent_conversions=recent_conversions)

@app.route('/history')
@login_required
def history():
    # Get user's conversion history
    conversions = Conversion.query.filter_by(user_id=current_user.id)\
                                 .order_by(Conversion.created_at.desc())\
                                 .limit(50)\
                                 .all()
    return render_template('history.html', conversions=conversions)

@app.route('/batch')
def batch_processing():
    return render_template('batch.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/convert')
def convert():
    conversion_type = request.args.get('type', 'general')
    if conversion_type not in ['general', 'audio', 'image', 'document']:
        conversion_type = 'general'
    return render_template(f'convert/{conversion_type}.html')

@app.route('/convert-file', methods=['POST'])
def convert_file_route():
    """Process file conversion request."""
    # Check for file in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No selected file'}), 400
    
    # Validate file
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported'}), 400
        
    # Get original filename without extension
    original_filename, _ = os.path.splitext(file.filename)
    
    # Get input and output formats
    filename = file.filename.lower()
    input_format = get_file_extension(filename)
    output_format = request.form.get('output_format', '').lower()
    
    # Get custom filename if provided, otherwise use original filename + "copy"
    custom_filename = request.form.get('custom_filename')
    if custom_filename and custom_filename.strip():
        output_filename = f"{custom_filename}.{output_format}"
    else:
        output_filename = f"{original_filename}_copy.{output_format}"
    
    # Generate unique input/output paths
    input_path = os.path.join(app.config['TEMP_FOLDER'], f"temp_input_{uuid.uuid4()}.{input_format}")
    output_path = os.path.join(app.config['TEMP_FOLDER'], f"temp_output_{uuid.uuid4()}.{output_format}")
    
    try:
        # Save uploaded file
        file.save(input_path)
        
        # Determine file type and use appropriate service
        file_type = determine_file_type(input_format, output_format)
        
        try:
            if file_type == 'audio':
                # Convert audio file
                logger.info(f"Converting audio from {input_format} to {output_format}")
                audio_service.convert_audio(input_path, output_path)
                operation = 'convert_audio'
            elif file_type == 'image':
                # Convert image file
                logger.info(f"Converting image from {input_format} to {output_format}")
                image_service.convert_image(input_path, output_path)
                operation = 'convert_image'
            elif file_type == 'document':
                # Convert document
                logger.info(f"Converting document from {input_format} to {output_format}")
                document_service.convert_document(input_path, output_path)
                operation = 'convert_document'
            else:
                clean_up_temp_files([input_path])
                return jsonify({'error': 'Unsupported conversion'}), 400
        except ImportError as e:
            # Handle missing dependencies errors
            logger.error(f"Conversion error (missing dependencies): {str(e)}")
            clean_up_temp_files([input_path])
            return jsonify({'error': f'This conversion is not available: {str(e)}'}), 500
        
        # Record conversion for logged in users
        if current_user.is_authenticated:
            conversion = Conversion(
                user_id=current_user.id,
                operation=operation,
                input_filename=file.filename,
                output_filename=output_filename
            )
            db.session.add(conversion)
            db.session.commit()
        
        # Read the converted file
        with open(output_path, 'rb') as f:
            file_data = f.read()
        
        # Clean up files
        clean_up_temp_files([input_path, output_path])
        
        # Determine MIME type
        mime_type = get_file_mime_type(output_filename)
        
        # Send the response
        response = make_response(file_data)
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'attachment; filename="{output_filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Clean up files in case of error
        clean_up_temp_files([input_path, output_path])
        
        return jsonify({'error': 'An error occurred during conversion. Please try again.'}), 500

def clean_up_temp_files(file_paths):
    """Clean up temporary files."""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Error cleaning up file {path}: {str(e)}")

def determine_file_type(input_format, output_format):
    """Determine file type based on input and output formats."""
    audio_formats = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']
    image_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff']
    document_formats = ['pdf', 'docx', 'txt', 'md', 'html']
    
    if input_format in audio_formats and output_format in audio_formats:
        return 'audio'
    elif input_format in image_formats and output_format in image_formats:
        return 'image'
    elif input_format in document_formats and output_format in document_formats:
        return 'document'
    else:
        return None

@app.context_processor
def utility_processor():
    """Add utility functions to Jinja2 context."""
    def get_conversion_count():
        if current_user.is_authenticated:
            return Conversion.query.filter_by(user_id=current_user.id).count()
        return 0
    
    return dict(get_conversion_count=get_conversion_count)

@app.route('/privacy')
def privacy_policy():
    return render_template('legal/privacy.html')

@app.route('/terms')
def terms_of_service():
    return render_template('legal/terms.html')

@app.route('/api-docs')
def api_docs():
    return render_template('api_docs.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=app.config['DEBUG'])