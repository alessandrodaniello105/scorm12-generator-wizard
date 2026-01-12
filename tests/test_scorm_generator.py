"""
Unit tests for SCORMGenerator class in logic.py
"""
import pytest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import shutil
from logic import SCORMGenerator


class TestSanitizeFilename:
    """Tests for sanitize_filename method."""
    
    def test_normal_filename(self, scorm_generator):
        """Test sanitizing a normal filename."""
        result = scorm_generator.sanitize_filename("My Course Title")
        assert result == "My Course Title"
    
    def test_filename_with_invalid_chars(self, scorm_generator):
        """Test sanitizing filename with invalid characters."""
        result = scorm_generator.sanitize_filename("Course: <Test> | File?")
        assert result == "Course_ _Test_ _ File_"
        assert ":" not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert "?" not in result
    
    def test_filename_with_slashes(self, scorm_generator):
        """Test sanitizing filename with slashes."""
        result = scorm_generator.sanitize_filename("Course/Path\\File")
        assert "/" not in result
        assert "\\" not in result
    
    def test_empty_filename(self, scorm_generator):
        """Test sanitizing empty filename."""
        result = scorm_generator.sanitize_filename("")
        assert result == "scorm_package"
    
    def test_filename_with_leading_trailing_spaces(self, scorm_generator):
        """Test sanitizing filename with leading/trailing spaces."""
        result = scorm_generator.sanitize_filename("  Course Title  ")
        assert result == "Course Title"
    
    def test_filename_with_dots(self, scorm_generator):
        """Test sanitizing filename with leading/trailing dots."""
        result = scorm_generator.sanitize_filename("...Course Title...")
        assert not result.startswith(".")
        assert not result.endswith(".")


class TestGenerate:
    """Tests for generate method."""
    
    def test_generate_vimeo_package(self, scorm_generator, temp_dir):
        """Test generating a SCORM package with Vimeo video."""
        output_path = scorm_generator.generate(
            title="Test Vimeo Course",
            description="Test description",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir)
        )
        
        assert Path(output_path).exists()
        assert output_path.endswith(".zip")
        
        # Verify ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zipf:
            files = zipf.namelist()
            assert "imsmanifest.xml" in files
            assert "index.html" in files
            assert "config.js" in files
    
    def test_generate_youtube_package(self, scorm_generator, temp_dir):
        """Test generating a SCORM package with YouTube video."""
        output_path = scorm_generator.generate(
            title="Test YouTube Course",
            description="Test description",
            video_type="youtube",
            video_url="abc123def45",
            output_dir=str(temp_dir)
        )
        
        assert Path(output_path).exists()
    
    def test_generate_remote_url_package(self, scorm_generator, temp_dir):
        """Test generating a SCORM package with remote URL."""
        output_path = scorm_generator.generate(
            title="Test Remote Course",
            description="Test description",
            video_type="videojs",
            video_url="https://example.com/video.mp4",
            output_dir=str(temp_dir)
        )
        
        assert Path(output_path).exists()
    
    def test_generate_local_file_package(self, scorm_generator, temp_dir, sample_video_file):
        """Test generating a SCORM package with local video file."""
        output_path = scorm_generator.generate(
            title="Test Local Course",
            description="Test description",
            video_type="local",
            video_url="test_video.mp4",
            local_video_file=sample_video_file,
            output_dir=str(temp_dir)
        )
        
        assert Path(output_path).exists()
        
        # Verify video file is in ZIP
        with zipfile.ZipFile(output_path, 'r') as zipf:
            files = zipf.namelist()
            assert "test_video.mp4" in files
    
    def test_generate_with_custom_filename(self, scorm_generator, temp_dir):
        """Test generating with custom output filename."""
        custom_path = temp_dir / "custom_name.zip"
        output_path = scorm_generator.generate(
            title="Test Course",
            description="Test description",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir),
            output_filename=str(custom_path)
        )
        
        assert output_path == str(custom_path)
        assert Path(custom_path).exists()


class TestManifestGeneration:
    """Tests for manifest XML generation."""
    
    def test_manifest_structure(self, scorm_generator, temp_dir):
        """Test that generated manifest has correct structure."""
        output_path = scorm_generator.generate(
            title="Test Course",
            description="Test description",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            manifest_content = zipf.read("imsmanifest.xml").decode('utf-8')
            
            # Parse XML
            root = ET.fromstring(manifest_content)
            
            # Check namespace
            assert "http://www.imsproject.org/xsd/imscp_rootv1p1p2" in root.tag
            
            # Check metadata
            metadata = root.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}metadata")
            assert metadata is not None
            
            # Check organization
            org = root.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}organization")
            assert org is not None
    
    def test_manifest_xml_escaping(self, scorm_generator, temp_dir):
        """Test that special characters are escaped in manifest."""
        output_path = scorm_generator.generate(
            title="Test <Course> & 'Special' \"Chars\"",
            description="Description with <tags> & symbols",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            manifest_content = zipf.read("imsmanifest.xml").decode('utf-8')
            
            # Should not contain unescaped special characters
            assert "<Course>" not in manifest_content
            assert "&lt;Course&gt;" in manifest_content or "&amp;lt;Course&amp;gt;" in manifest_content
            assert "&" not in manifest_content or "&amp;" in manifest_content or "&apos;" in manifest_content


class TestHTMLGeneration:
    """Tests for HTML generation."""
    
    def test_html_structure(self, scorm_generator, temp_dir):
        """Test that generated HTML has correct structure."""
        output_path = scorm_generator.generate(
            title="Test Course",
            description="Test description",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            html_content = zipf.read("index.html").decode('utf-8')
            
            assert "<!DOCTYPE html>" in html_content
            assert "<html>" in html_content
            assert "config.js" in html_content
            assert "main.js" in html_content
    
    def test_html_escaping(self, scorm_generator, temp_dir):
        """Test that special characters are escaped in HTML."""
        output_path = scorm_generator.generate(
            title="Test <Course> & 'Special' \"Chars\"",
            description="Description with <tags> & symbols",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            html_content = zipf.read("index.html").decode('utf-8')
            
            # Should not contain unescaped special characters
            assert "<Course>" not in html_content
            assert "&lt;Course&gt;" in html_content


class TestConfigGeneration:
    """Tests for config.js generation."""
    
    def test_config_vimeo(self, scorm_generator, temp_dir):
        """Test config.js for Vimeo video."""
        output_path = scorm_generator.generate(
            title="Test Course",
            description="Test description",
            video_type="vimeo",
            video_url="123456789",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            config_content = zipf.read("config.js").decode('utf-8')
            
            assert "playerType: \"vimeo\"" in config_content
            assert "url: \"123456789\"" in config_content
            assert "trackingMode: \"scorm12\"" in config_content
    
    def test_config_youtube(self, scorm_generator, temp_dir):
        """Test config.js for YouTube video."""
        output_path = scorm_generator.generate(
            title="Test Course",
            description="Test description",
            video_type="youtube",
            video_url="abc123def45",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            config_content = zipf.read("config.js").decode('utf-8')
            
            assert "playerType: \"youtube\"" in config_content
            assert "url: \"abc123def45\"" in config_content
    
    def test_config_videojs(self, scorm_generator, temp_dir):
        """Test config.js for videojs (remote URL)."""
        output_path = scorm_generator.generate(
            title="Test Course",
            description="Test description",
            video_type="videojs",
            video_url="https://example.com/video.mp4",
            output_dir=str(temp_dir)
        )
        
        with zipfile.ZipFile(output_path, 'r') as zipf:
            config_content = zipf.read("config.js").decode('utf-8')
            
            assert "playerType: \"videojs\"" in config_content
            assert "https://example.com/video.mp4" in config_content
