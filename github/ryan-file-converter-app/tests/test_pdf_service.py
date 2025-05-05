# tests/test_pdf_service.py
import os
import unittest
import tempfile
from services.pdf_service import PDFService
from PyPDF2 import PdfReader

class TestPDFService(unittest.TestCase):
    """Test cases for PDFService."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_service = PDFService(temp_dir=self.temp_dir)
        
        # Create a simple test PDF
        self.test_pdf_path = os.path.join(self.temp_dir, 'test.pdf')
        with open(self.test_pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n')
    
    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_split_pdf(self):
        """Test splitting a PDF."""
        # Test with a valid page range
        page_ranges = ['1']
        output_paths = self.pdf_service.split_pdf(self.test_pdf_path, page_ranges)
        
        self.assertEqual(len(output_paths), 1)
        self.assertTrue(os.path.exists(output_paths[0]))
        
        # Test with multiple page ranges
        page_ranges = ['1', '1']
        output_paths = self.pdf_service.split_pdf(self.test_pdf_path, page_ranges)
        
        self.assertEqual(len(output_paths), 2)
        for path in output_paths:
            self.assertTrue(os.path.exists(path))
    
    def test_merge_pdfs(self):
        """Test merging PDFs."""
        # Create a second test PDF
        test_pdf2_path = os.path.join(self.temp_dir, 'test2.pdf')
        with open(test_pdf2_path, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n')
        
        # Test merging
        input_paths = [self.test_pdf_path, test_pdf2_path]
        output_path = self.pdf_service.merge_pdfs(input_paths)
        
        self.assertTrue(os.path.exists(output_path))
        
        # Test with custom output filename
        output_path = self.pdf_service.merge_pdfs(input_paths, output_filename="custom_merged")
        self.assertTrue(os.path.exists(output_path))
        self.assertIn("custom_merged", output_path)
    
    def test_compress_pdf(self):
        """Test compressing a PDF."""
        output_path = self.pdf_service.compress_pdf(self.test_pdf_path)
        
        self.assertTrue(os.path.exists(output_path))
        
        # Check that file size is not larger than original
        self.assertLessEqual(os.path.getsize(output_path), 
                           os.path.getsize(self.test_pdf_path) * 1.1)  # Allow 10% overhead
        
        # Test with different quality settings
        for quality in ['low', 'medium', 'high']:
            output_path = self.pdf_service.compress_pdf(self.test_pdf_path, quality=quality)
            self.assertTrue(os.path.exists(output_path))
    
    def test_add_password(self):
        """Test adding password protection to a PDF."""
        user_password = "testpass"
        output_path = self.pdf_service.add_password(self.test_pdf_path, user_password)
        
        self.assertTrue(os.path.exists(output_path))
        
        # Verify that the PDF is password-protected
        reader = PdfReader(output_path)
        self.assertTrue(reader.is_encrypted)
        
        # Test with both user and owner passwords
        output_path = self.pdf_service.add_password(
            self.test_pdf_path, 
            user_password="user123", 
            owner_password="owner456"
        )
        self.assertTrue(os.path.exists(output_path))
        
    def test_remove_password(self):
        """Test removing password from a PDF."""
        # First create a password-protected PDF
        password = "testpass"
        protected_path = self.pdf_service.add_password(self.test_pdf_path, password)
        
        # Now remove the password
        unprotected_path = self.pdf_service.remove_password(protected_path, password)
        
        self.assertTrue(os.path.exists(unprotected_path))
        
        # Verify that the PDF is no longer password-protected
        reader = PdfReader(unprotected_path)
        self.assertFalse(reader.is_encrypted)
        
    def test_rotate_pdf(self):
        """Test rotating a PDF."""
        # Test with 90 degree rotation
        for angle in [90, 180, 270]:
            output_path = self.pdf_service.rotate_pdf(self.test_pdf_path, angle)
            self.assertTrue(os.path.exists(output_path))
        
        # Test with specific pages
        output_path = self.pdf_service.rotate_pdf(self.test_pdf_path, 90, pages=[1])
        self.assertTrue(os.path.exists(output_path))
    
    def test_add_watermark(self):
        """Test adding watermark to a PDF."""
        output_path = self.pdf_service.add_watermark(
            self.test_pdf_path, 
            watermark_text="CONFIDENTIAL"
        )
        self.assertTrue(os.path.exists(output_path))
        
        # Test with different positions and colors
        positions = ['center', 'top', 'bottom']
        colors = ['black', 'white']
        
        for position in positions:
            for color in colors:
                output_path = self.pdf_service.add_watermark(
                    self.test_pdf_path,
                    watermark_text="TEST",
                    position=position,
                    opacity=0.5,
                    color=color
                )
                self.assertTrue(os.path.exists(output_path))
    
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        # Create some temporary files
        test_files = []
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f'temp_file_{i}.txt')
            with open(file_path, 'w') as f:
                f.write('test content')
            test_files.append(file_path)
        
        # Test cleaning specific files
        self.pdf_service.cleanup_temp_files(test_files[:2])
        self.assertFalse(os.path.exists(test_files[0]))
        self.assertFalse(os.path.exists(test_files[1]))
        self.assertTrue(os.path.exists(test_files[2]))
        
        # Test cleaning all files
        os.makedirs(os.path.join(self.temp_dir, 'subdir'))  # Create a subdirectory
        self.pdf_service.cleanup_temp_files()
        # Only files should be removed, not directories
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, 'subdir')))