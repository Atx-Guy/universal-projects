# tests/test_image_service.py
import os
import unittest
import tempfile
from services.image_service import ImageService
from PIL import Image

class TestImageService(unittest.TestCase):
    """Test cases for ImageService."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.image_service = ImageService(temp_dir=self.temp_dir)
        
        # Create a simple test image
        self.test_image_path = os.path.join(self.temp_dir, 'test.jpg')
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(self.test_image_path)
        
        # Create a test PNG with transparency
        self.test_png_path = os.path.join(self.temp_dir, 'test.png')
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        img.save(self.test_png_path)
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_convert_image(self):
        """Test basic image conversion."""
        formats = ['.jpg', '.png', '.webp', '.bmp']
        
        for output_format in formats:
            output_path = os.path.join(self.temp_dir, f'converted{output_format}')
            result = self.image_service.convert_image(self.test_image_path, output_path)
            
            self.assertTrue(os.path.exists(result))
            
            # Verify the format is correct
            img = Image.open(result)
            if output_format == '.jpg':
                self.assertEqual(img.format, 'JPEG')
            else:
                self.assertEqual(img.format, output_format.lstrip('.').upper())
    
    def test_convert_image_with_options(self):
        """Test image conversion with processing options."""
        output_path = os.path.join(self.temp_dir, 'converted_with_options.jpg')
        
        options = {
            'resize': (50, 50),
            'brightness': 1.2,
            'contrast': 1.1,
            'sharpness': 1.3
        }
        
        result = self.image_service.convert_image(self.test_image_path, output_path, options)
        self.assertTrue(os.path.exists(result))
        
        # Verify the size changed
        img = Image.open(result)
        self.assertEqual(img.size, (50, 50))
    
    def test_convert_rgba_to_rgb(self):
        """Test converting RGBA (PNG) to RGB (JPG)."""
        output_path = os.path.join(self.temp_dir, 'converted_rgba_to_rgb.jpg')
        result = self.image_service.convert_image(self.test_png_path, output_path)
        
        self.assertTrue(os.path.exists(result))
        
        # Verify it's a proper JPEG
        img = Image.open(result)
        self.assertEqual(img.format, 'JPEG')
        self.assertEqual(img.mode, 'RGB')  # Should be RGB, not RGBA
    
    def test_apply_image_processing(self):
        """Test various image processing functions."""
        img = Image.open(self.test_image_path)
        
        test_cases = [
            {'resize': (50, 50)},
            {'resize': (50, None)},
            {'resize': (None, 50)},
            {'crop': (10, 10, 50, 50)},
            {'rotate': 45},
            {'flip': 'horizontal'},
            {'flip': 'vertical'},
            {'brightness': 1.5},
            {'contrast': 0.8},
            {'sharpness': 2.0},
            {'filter': 'grayscale'},
            {'filter': 'sepia'},
            {'filter': 'negative'}
        ]
        
        for options in test_cases:
            processed = self.image_service._apply_image_processing(img, options)
            self.assertIsInstance(processed, Image.Image)
            
            # Check specific transformations
            if 'resize' in options and all(options['resize']):
                self.assertEqual(processed.size, options['resize'])
            if 'filter' in options and options['filter'] == 'grayscale':
                # Check if it's grayscale (mode L or 1 channel in RGB)
                self.assertTrue(processed.mode == 'L' or len(processed.getbands()) == 1)
    
    def test_batch_process_images(self):
        """Test batch processing of images."""
        # Create additional test images
        test_images = [self.test_image_path]
        for i in range(2):
            path = os.path.join(self.temp_dir, f'test_batch_{i}.jpg')
            img = Image.new('RGB', (100, 100), color=(i * 100, i * 50, 255 - i * 50))
            img.save(path)
            test_images.append(path)
        
        output_dir = os.path.join(self.temp_dir, 'batch_output')
        output_format = 'png'
        
        # Test batch processing
        results = self.image_service.batch_process_images(test_images, output_dir, output_format)
        
        self.assertEqual(len(results), len(test_images))
        for path in results:
            self.assertTrue(os.path.exists(path))
            self.assertTrue(path.endswith(f'.{output_format}'))
    
    def test_create_thumbnail(self):
        """Test thumbnail creation."""
        output_path = os.path.join(self.temp_dir, 'thumbnail.jpg')
        size = (50, 50)
        
        result = self.image_service.create_thumbnail(self.test_image_path, output_path, size)
        
        self.assertTrue(os.path.exists(result))
        
        # Verify the thumbnail size
        img = Image.open(result)
        self.assertLessEqual(img.width, size[0])
        self.assertLessEqual(img.height, size[1])
    
    def test_add_watermark(self):
        """Test adding watermark to an image."""
        output_path = os.path.join(self.temp_dir, 'watermarked.jpg')
        watermark_text = "TEST WATERMARK"
        
        # Test with different positions
        positions = ['center', 'topleft', 'topright', 'bottomleft', 'bottomright']
        
        for position in positions:
            result = self.image_service.add_watermark(
                self.test_image_path,
                output_path,
                watermark_text,
                position=position,
                opacity=0.5
            )
            
            self.assertTrue(os.path.exists(result))
            
            # Basic verification that the image is valid
            img = Image.open(result)
            self.assertIsInstance(img, Image.Image)

if __name__ == "__main__":
    unittest.main()