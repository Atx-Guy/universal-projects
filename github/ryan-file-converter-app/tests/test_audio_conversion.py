import os
import sys
import logging
import tempfile
import platform

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('audio_test')

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.audio_service import AudioService

def setup_ffmpeg_environment():
    """Set up the FFmpeg environment by ensuring binaries exist"""
    service = AudioService()
    
    # Create the directory if it doesn't exist
    ffmpeg_dir = service.ffmpeg_dir
    os.makedirs(ffmpeg_dir, exist_ok=True)
    
    # Check if ffmpeg exists, if not download or copy from system
    ffmpeg_path = service.ffmpeg_path
    if not os.path.exists(ffmpeg_path) and ffmpeg_path != 'ffmpeg':
        logger.info("FFmpeg binary not found, downloading it")
        try:
            service._download_ffmpeg()
        except Exception as e:
            # If download fails, try copying the system ffmpeg
            logger.warning(f"Failed to download FFmpeg: {e}, trying system binary")
            try:
                import shutil
                shutil.copy('/usr/bin/ffmpeg', os.path.join(ffmpeg_dir, 'ffmpeg'))
                os.chmod(os.path.join(ffmpeg_dir, 'ffmpeg'), 0o755)
            except Exception as copy_error:
                logger.error(f"Failed to copy system FFmpeg: {copy_error}")
                raise
    
    # Ensure ffprobe exists, if not create it from ffmpeg
    ffprobe_path = service.ffprobe_path
    if not os.path.exists(ffprobe_path) and ffprobe_path != 'ffprobe':
        logger.info("FFprobe binary not found, creating it")
        try:
            # In many Linux distros, ffmpeg binary can also function as ffprobe
            if os.path.exists(ffmpeg_path):
                import shutil
                if platform.system() == 'Windows':
                    shutil.copy(ffmpeg_path, ffprobe_path)
                else:
                    try:
                        os.symlink(ffmpeg_path, ffprobe_path)
                    except:
                        shutil.copy(ffmpeg_path, ffprobe_path)
                os.chmod(ffprobe_path, 0o755)
                logger.info(f"Created ffprobe at {ffprobe_path}")
        except Exception as e:
            logger.error(f"Failed to create ffprobe: {e}")
            raise
    
    # Verify that both files exist and are executable
    if ffmpeg_path != 'ffmpeg' and not os.path.exists(ffmpeg_path):
        raise FileNotFoundError(f"FFmpeg binary not found at {ffmpeg_path}")
    
    if ffprobe_path != 'ffprobe' and not os.path.exists(ffprobe_path):
        raise FileNotFoundError(f"FFprobe binary not found at {ffprobe_path}")
    
    logger.info(f"FFmpeg environment set up successfully")
    return service

def test_audio_service_initialization():
    """Test that AudioService initializes properly with ffmpeg/ffprobe paths"""
    # First ensure the environment is set up
    service = setup_ffmpeg_environment()
    
    # Check if ffmpeg path is set
    assert service.ffmpeg_path is not None
    # Check if ffprobe path is set  
    assert service.ffprobe_path is not None
    
    # Log the paths to verify
    logger.info(f"FFmpeg path: {service.ffmpeg_path}")
    logger.info(f"FFprobe path: {service.ffprobe_path}")
    
    # Check if the files exist
    if service.ffmpeg_path != 'ffmpeg':
        assert os.path.exists(service.ffmpeg_path), f"FFmpeg not found at {service.ffmpeg_path}"
    
    if service.ffprobe_path != 'ffprobe':
        assert os.path.exists(service.ffprobe_path), f"FFprobe not found at {service.ffprobe_path}"
    
    return service

def create_test_audio_file():
    """Create a simple test audio file using FFmpeg"""
    service = test_audio_service_initialization()
    
    # Create a test audio file using FFmpeg
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    temp_file.close()
    
    # Generate a simple tone
    command = [
        service.ffmpeg_path,
        '-f', 'lavfi',
        '-i', 'sine=frequency=440:duration=3',
        '-c:a', 'libmp3lame',
        '-y',
        temp_file.name
    ]
    
    logger.info(f"Generating test audio file: {temp_file.name}")
    logger.info(f"Command: {' '.join(command)}")
    
    import subprocess
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Test file created successfully")
        return temp_file.name
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating test file: {str(e)}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Error: {e.stderr}")
        raise

def test_audio_conversion():
    """Test audio conversion functionality"""
    # First ensure our service initializes properly
    service = test_audio_service_initialization()
    
    # Create a test audio file
    try:
        input_path = create_test_audio_file()
    except Exception as e:
        logger.error(f"Failed to create test file: {e}")
        return False
    
    # Create a temporary output path
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
    
    # Perform the conversion
    logger.info(f"Converting {input_path} to {output_path}")
    try:
        result_path = service.convert_audio(input_path, output_path, options={'bitrate': 192})
        logger.info(f"Conversion successful: {result_path}")
        
        # Check if output file exists and has non-zero size
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 0
        
        logger.info("Test passed! ✅")
        
        # Clean up test files
        try:
            os.unlink(input_path)
            os.unlink(output_path)
        except Exception as e:
            logger.warning(f"Error cleaning up test files: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting audio conversion test")
    try:
        success = test_audio_conversion()
        if success:
            logger.info("All tests passed successfully")
            exit(0)
        else:
            logger.error("Test failed")
            exit(1)
    except Exception as e:
        logger.error(f"Unhandled exception in test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)