#!/usr/bin/env python3
"""
Setup script for FFmpeg binaries for the file converter application.
This script ensures that both ffmpeg and ffprobe binaries are available.
"""

import os
import sys
import platform
import shutil
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ffmpeg_setup')

def ensure_directory_exists(directory_path):
    """Ensure that the specified directory exists"""
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    logger.info(f"Directory exists: {directory_path}")

def find_system_binary(binary_name):
    """Find a system binary by name"""
    try:
        # Try using 'which' on Unix-like systems or 'where' on Windows
        if platform.system() == 'Windows':
            result = subprocess.run(['where', binary_name], capture_output=True, text=True, check=False)
        else:
            result = subprocess.run(['which', binary_name], capture_output=True, text=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass
    
    # Check common locations
    common_paths = [
        '/usr/bin', '/usr/local/bin', '/opt/local/bin',  # Unix-like
        'C:\\Program Files\\ffmpeg\\bin', 'C:\\ffmpeg\\bin'  # Windows
    ]
    
    for path in common_paths:
        bin_path = os.path.join(path, binary_name)
        if platform.system() == 'Windows':
            bin_path += '.exe'
        
        if os.path.exists(bin_path) and os.path.isfile(bin_path):
            return bin_path
    
    return None

def copy_binary(source, destination, make_executable=True):
    """Copy a binary file to the destination and make it executable if needed"""
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Copy the file
        shutil.copy2(source, destination)
        logger.info(f"Copied {source} to {destination}")
        
        # Make it executable on Unix-like systems
        if make_executable and platform.system() != 'Windows':
            os.chmod(destination, 0o755)
            logger.info(f"Made {destination} executable")
        
        return True
    except Exception as e:
        logger.error(f"Failed to copy {source} to {destination}: {e}")
        return False

def create_symlink(source, destination):
    """Create a symbolic link from source to destination"""
    try:
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Remove destination if it already exists
        if os.path.exists(destination):
            if os.path.islink(destination) or os.path.isfile(destination):
                os.unlink(destination)
        
        # Create the symlink
        os.symlink(source, destination)
        logger.info(f"Created symlink from {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to create symlink from {source} to {destination}: {e}")
        return False

def create_ffprobe_from_ffmpeg(ffmpeg_path, ffprobe_path):
    """Create ffprobe from ffmpeg using direct file operation"""
    try:
        # Read ffmpeg binary content
        with open(ffmpeg_path, 'rb') as f_in:
            content = f_in.read()
            
        # Write to ffprobe
        with open(ffprobe_path, 'wb') as f_out:
            f_out.write(content)
        
        # Make executable on Unix
        if platform.system() != 'Windows':
            os.chmod(ffprobe_path, 0o755)
        
        logger.info(f"Created ffprobe at {ffprobe_path} from {ffmpeg_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create ffprobe from ffmpeg: {e}")
        return False

def main():
    """Main function to set up FFmpeg binaries"""
    ffmpeg_dir = os.path.join(os.getcwd(), 'ffmpeg-static')
    
    # Ensure the directory exists
    ensure_directory_exists(ffmpeg_dir)
    
    # Define binary paths
    if platform.system() == 'Windows':
        ffmpeg_bin = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
        ffprobe_bin = os.path.join(ffmpeg_dir, 'ffprobe.exe')
    else:
        ffmpeg_bin = os.path.join(ffmpeg_dir, 'ffmpeg')
        ffprobe_bin = os.path.join(ffmpeg_dir, 'ffprobe')
    
    # Step 1: Check if FFmpeg exists in our directory
    if os.path.exists(ffmpeg_bin):
        logger.info(f"FFmpeg already exists at {ffmpeg_bin}")
    else:
        # Try to find FFmpeg in the system
        system_ffmpeg = find_system_binary('ffmpeg')
        if system_ffmpeg:
            logger.info(f"Found system FFmpeg at {system_ffmpeg}")
            copy_binary(system_ffmpeg, ffmpeg_bin)
        else:
            logger.error("FFmpeg not found in system, please install FFmpeg manually")
            return 1
    
    # Step 2: Check if FFprobe exists in our directory
    if os.path.exists(ffprobe_bin):
        logger.info(f"FFprobe already exists at {ffprobe_bin}")
    else:
        # Try to find FFprobe in the system
        system_ffprobe = find_system_binary('ffprobe')
        
        if system_ffprobe:
            logger.info(f"Found system FFprobe at {system_ffprobe}")
            copy_binary(system_ffprobe, ffprobe_bin)
        else:
            # FFprobe not found, try to create a symlink from FFmpeg
            logger.info("FFprobe not found, creating a link from FFmpeg")
            if platform.system() == 'Windows':
                copy_binary(ffmpeg_bin, ffprobe_bin)
            else:
                if not create_symlink(ffmpeg_bin, ffprobe_bin):
                    logger.info("Failed to create symlink, copying instead")
                    if not create_ffprobe_from_ffmpeg(ffmpeg_bin, ffprobe_bin):
                        logger.error("Failed to create ffprobe from ffmpeg")
                        return 1
    
    # Step 3: Verify that both binaries exist and are executable
    if not os.path.exists(ffmpeg_bin):
        logger.error(f"FFmpeg not found at {ffmpeg_bin}")
        return 1
    
    if not os.path.exists(ffprobe_bin):
        logger.error(f"FFprobe not found at {ffprobe_bin}")
        return 1
    
    logger.info("FFmpeg setup completed successfully")
    print(f"FFmpeg: {ffmpeg_bin}")
    print(f"FFprobe: {ffprobe_bin}")
    return 0

if __name__ == "__main__":
    sys.exit(main())