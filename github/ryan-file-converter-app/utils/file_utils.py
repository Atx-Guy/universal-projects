# utils/file_utils.py
import os
import uuid
import mimetypes
import logging
import shutil
from typing import List, Set, Optional, Tuple
from flask import send_file, make_response
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

# Dictionary of allowed file extensions by type
ALLOWED_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg'},
    'audio': {'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma'},
    'document': {'pdf', 'docx', 'doc', 'txt', 'rtf', 'odt', 'md', 'html', 'htm'},
    'spreadsheet': {'xlsx', 'xls', 'csv', 'ods'},
    'presentation': {'pptx', 'ppt', 'odp'},
    'archive': {'zip', 'rar', '7z', 'tar', 'gz'}
}

# Flatten the dictionary for quick lookup
ALL_ALLOWED_EXTENSIONS: Set[str] = set()
for extensions in ALLOWED_EXTENSIONS.values():
    ALL_ALLOWED_EXTENSIONS.update(extensions)

def allowed_file(filename: str, file_types: Optional[List[str]] = None) -> bool:
    """
    Check if a file is allowed based on its extension.
    
    Args:
        filename (str): The name of the file to check
        file_types (list, optional): Specific file types to allow (e.g., ['image', 'document'])
                                   If None, all allowed extensions are considered
                                   
    Returns:
        bool: True if the file is allowed, False otherwise
    """
    if not filename or '.' not in filename:
        return False
        
    ext = filename.rsplit('.', 1)[1].lower()
    
    if file_types:
        # Only check specific file types
        allowed_exts = set()
        for file_type in file_types:
            allowed_exts.update(ALLOWED_EXTENSIONS.get(file_type, set()))
        return ext in allowed_exts
    else:
        # Check all allowed extensions
        return ext in ALL_ALLOWED_EXTENSIONS

def get_file_extension(filename: str) -> str:
    """
    Get the extension of a file.
    
    Args:
        filename (str): The name of the file
        
    Returns:
        str: The extension of the file, or an empty string if no extension
    """
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()

def create_temp_directory(directory: str) -> str:
    """
    Create a temporary directory if it doesn't exist.
    
    Args:
        directory (str): The path to the directory to create
        
    Returns:
        str: The path to the created directory
    """
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Temporary directory created or verified: {directory}")
        return directory
    except Exception as e:
        logger.error(f"Error creating temporary directory: {str(e)}")
        raise

def generate_unique_filename(original_filename: str, prefix: str = '', suffix: str = '') -> str:
    """
    Generate a unique filename based on the original filename.
    
    Args:
        original_filename (str): The original filename
        prefix (str, optional): Prefix to add to the filename
        suffix (str, optional): Suffix to add to the filename
        
    Returns:
        str: A unique filename
    """
    name, ext = os.path.splitext(original_filename)
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}{name}_{unique_id}{suffix}{ext}"

def get_file_mime_type(filename: str) -> str:
    """
    Get the MIME type of a file.
    
    Args:
        filename (str): The name or path to the file
        
    Returns:
        str: The MIME type of the file, or 'application/octet-stream' if unknown
    """
    mime_type, _ = mimetypes.guess_type(filename)
    
    # If mimetypes fails, try to determine from extension
    if not mime_type:
        ext = get_file_extension(filename)
        
        if ext in ALLOWED_EXTENSIONS['image']:
            mime_type = f'image/{ext}'
        elif ext in ALLOWED_EXTENSIONS['audio']:
            mime_type = f'audio/{ext}'
        elif ext == 'pdf':
            mime_type = 'application/pdf'
        elif ext == 'docx':
            mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif ext == 'xlsx':
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif ext == 'pptx':
            mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        elif ext == 'txt':
            mime_type = 'text/plain'
        elif ext in ['html', 'htm']:
            mime_type = 'text/html'
        else:
            mime_type = 'application/octet-stream'
    
    return mime_type

def get_file_category(filename: str) -> str:
    """
    Determine the category of a file based on its extension.
    
    Args:
        filename (str): The name of the file
        
    Returns:
        str: The category of the file ('image', 'audio', etc.) or 'unknown'
    """
    if not filename or '.' not in filename:
        return 'unknown'
        
    ext = get_file_extension(filename)
    
    for category, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return category
            
    return 'unknown'

def safe_file_operations(func):
    """
    Decorator for safe file operations with automatic cleanup.
    
    This decorator will catch exceptions and ensure temporary files are cleaned up.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    def wrapper(*args, **kwargs):
        temp_files = []
        try:
            # Call the original function
            result = func(*args, temp_files=temp_files, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
        finally:
            # Clean up any temporary files
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
    
    return wrapper

def copy_file_safe(src_path: str, dst_path: str) -> str:
    """
    Safely copy a file from source to destination.
    
    Args:
        src_path (str): Source file path
        dst_path (str): Destination file path
        
    Returns:
        str: The destination path if successful
        
    Raises:
        FileNotFoundError: If source file doesn't exist
        IOError: If copy operation fails
    """
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source file not found: {src_path}")
        
    try:
        # Make sure the destination directory exists
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
            
        shutil.copy2(src_path, dst_path)
        return dst_path
    except Exception as e:
        raise IOError(f"Failed to copy file: {str(e)}")

def split_filename_extension(filename: str) -> Tuple[str, str]:
    """
    Split a filename into name and extension.
    
    Args:
        filename (str): The filename to split
        
    Returns:
        tuple: (name, extension)
    """
    if not filename:
        return ('', '')
        
    # Handle special case of hidden files (e.g., .gitignore)
    if filename.startswith('.') and '.' not in filename[1:]:
        return (filename, '')
        
    return os.path.splitext(filename)

def get_human_readable_filesize(size_in_bytes: int) -> str:
    """
    Convert file size in bytes to a human-readable format.
    
    Args:
        size_in_bytes (int): File size in bytes
        
    Returns:
        str: Human-readable file size (e.g., "2.5 MB")
    """
    # Define size units and their respective thresholds
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    # Handle edge cases
    if size_in_bytes == 0:
        return "0 B"
    if size_in_bytes < 0:
        return "Unknown size"
        
    i = 0
    size = float(size_in_bytes)
    
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
        
    # Format with 1 decimal place for sizes > 1 unit, 0 decimals for < 1
    if size < 10:
        return f"{size:.1f} {units[i]}"
    else:
        return f"{int(size)} {units[i]}"

def save_uploaded_file(file: FileStorage, directory: str) -> str:
    """
    Save an uploaded file to a specified directory with a unique name.
    
    Args:
        file (FileStorage): The file to save from request.files
        directory (str): Directory where to save the file
        
    Returns:
        str: Path to the saved file
    """
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Get a secure filename with original extension
    original_filename = secure_filename(file.filename)
    _, ext = os.path.splitext(original_filename)
    
    # Generate a unique filename
    unique_id = uuid.uuid4()
    unique_filename = f"{unique_id}{ext}"
    
    # Create the full file path
    file_path = os.path.join(directory, unique_filename)
    
    # Save the file
    file.save(file_path)
    
    logger.info(f"File saved at: {file_path}")
    return file_path

def create_download_response(file_path: str, output_filename: str):
    """
    Create a response for downloading a file.
    
    Args:
        file_path (str): Path to the file to download
        output_filename (str): Filename to be used when downloading
        
    Returns:
        Response: Flask response object for file download
    """
    try:
        # Get MIME type
        mime_type = get_file_mime_type(output_filename)
        
        # Read the file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create response
        response = make_response(file_data)
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'attachment; filename="{output_filename}"'
        
        # Clean up file after creating response
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to clean up file {file_path}: {str(e)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating download response: {str(e)}")
        raise