"""
Unit tests for logic.py
"""
import pytest
import os
from pathlib import Path
import tempfile
import shutil
from logic import SCORMGenerator


class TestExtractVideoID:
    """Tests for extract_video_id method."""
    
    def test_vimeo_id_direct(self, scorm_logic):
        """Test extracting Vimeo ID when already an ID."""
        result = scorm_logic.extract_video_id("123456789", "vimeo")
        assert result == "123456789"
    
    def test_vimeo_url_full(self, scorm_logic):
        """Test extracting Vimeo ID from full URL."""
        result = scorm_logic.extract_video_id("https://vimeo.com/123456789", "vimeo")
        assert result == "123456789"
    
    def test_vimeo_url_player(self, scorm_logic):
        """Test extracting Vimeo ID from player URL."""
        result = scorm_logic.extract_video_id("https://player.vimeo.com/video/123456789", "vimeo")
        assert result == "123456789"
    
    def test_youtube_id_direct(self, scorm_logic):
        """Test extracting YouTube ID when already an ID."""
        result = scorm_logic.extract_video_id("abc123def45", "youtube")
        assert result == "abc123def45"
    
    def test_youtube_url_watch(self, scorm_logic):
        """Test extracting YouTube ID from watch URL."""
        result = scorm_logic.extract_video_id("https://www.youtube.com/watch?v=abc123def45", "youtube")
        assert result == "abc123def45"
    
    def test_youtube_url_short(self, scorm_logic):
        """Test extracting YouTube ID from short URL."""
        result = scorm_logic.extract_video_id("https://youtu.be/abc123def45", "youtube")
        assert result == "abc123def45"
    
    def test_youtube_url_embed(self, scorm_logic):
        """Test extracting YouTube ID from embed URL."""
        result = scorm_logic.extract_video_id("https://www.youtube.com/embed/abc123def45", "youtube")
        assert result == "abc123def45"
    
    def test_remote_url_passthrough(self, scorm_logic):
        """Test that remote URLs are passed through."""
        url = "https://example.com/video.mp4"
        result = scorm_logic.extract_video_id(url, "videojs")
        assert result == url
    
    def test_empty_url(self, scorm_logic):
        """Test extracting from empty URL."""
        result = scorm_logic.extract_video_id("", "vimeo")
        assert result is None


class TestDetectVideoType:
    """Tests for detect_video_type method."""
    
    def test_detect_local_file_exists(self, scorm_logic, temp_dir):
        """Test detecting local file that exists."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"fake video")
        
        video_type, path = scorm_logic.detect_video_type(str(video_file))
        assert video_type == "local"
        assert path == str(video_file)
    
    def test_detect_local_windows_path(self, scorm_logic):
        """Test detecting Windows path format."""
        video_type, path = scorm_logic.detect_video_type("C:\\videos\\test.mp4")
        assert video_type == "local"
        assert path == "C:\\videos\\test.mp4"
    
    def test_detect_vimeo_url(self, scorm_logic):
        """Test detecting Vimeo URL."""
        video_type, path = scorm_logic.detect_video_type("https://vimeo.com/123456789")
        assert video_type == "vimeo"
        assert path == "https://vimeo.com/123456789"
    
    def test_detect_vimeo_id_numeric(self, scorm_logic):
        """Test detecting numeric Vimeo ID."""
        video_type, path = scorm_logic.detect_video_type("123456789")
        assert video_type == "vimeo"
        assert path == "123456789"
    
    def test_detect_youtube_url(self, scorm_logic):
        """Test detecting YouTube URL."""
        video_type, path = scorm_logic.detect_video_type("https://www.youtube.com/watch?v=abc123")
        assert video_type == "youtube"
        assert path == "https://www.youtube.com/watch?v=abc123"
    
    def test_detect_youtube_short_url(self, scorm_logic):
        """Test detecting YouTube short URL."""
        video_type, path = scorm_logic.detect_video_type("https://youtu.be/abc123def45")
        assert video_type == "youtube"
        assert path == "https://youtu.be/abc123def45"
    
    def test_detect_youtube_id_format(self, scorm_logic):
        """Test detecting YouTube ID format (11 chars)."""
        video_type, path = scorm_logic.detect_video_type("abc123def45")
        assert video_type == "youtube"
        assert path == "abc123def45"
    
    def test_detect_remote_url(self, scorm_logic):
        """Test detecting remote URL."""
        video_type, path = scorm_logic.detect_video_type("https://example.com/video.mp4")
        assert video_type == "videojs"
        assert path == "https://example.com/video.mp4"
    
    def test_detect_http_url(self, scorm_logic):
        """Test detecting HTTP URL."""
        video_type, path = scorm_logic.detect_video_type("http://example.com/video.mp4")
        assert video_type == "videojs"
        assert path == "http://example.com/video.mp4"


class TestValidateSingleInputs:
    """Tests for validate_single_inputs method."""
    
    def test_valid_inputs(self, scorm_logic):
        """Test validation with valid inputs."""
        is_valid, error = scorm_logic.validate_single_inputs(
            title="Test Course",
            video_input="123456789",
            video_type="vimeo",
            local_file_path=""
        )
        assert is_valid is True
        assert error is None
    
    def test_missing_title(self, scorm_logic):
        """Test validation with missing title."""
        is_valid, error = scorm_logic.validate_single_inputs(
            title="",
            video_input="123456789",
            video_type="vimeo",
            local_file_path=""
        )
        assert is_valid is False
        assert "Title" in error.lower()
    
    def test_whitespace_title(self, scorm_logic):
        """Test validation with whitespace-only title."""
        is_valid, error = scorm_logic.validate_single_inputs(
            title="   ",
            video_input="123456789",
            video_type="vimeo",
            local_file_path=""
        )
        assert is_valid is False
    
    def test_missing_video_input(self, scorm_logic):
        """Test validation with missing video input."""
        is_valid, error = scorm_logic.validate_single_inputs(
            title="Test Course",
            video_input="",
            video_type="vimeo",
            local_file_path=""
        )
        assert is_valid is False
        assert "video" in error.lower()
    
    def test_local_file_missing(self, scorm_logic):
        """Test validation with missing local file."""
        is_valid, error = scorm_logic.validate_single_inputs(
            title="Test Course",
            video_input="test.mp4",
            video_type="local",
            local_file_path="/nonexistent/path.mp4"
        )
        assert is_valid is False
        assert "file" in error.lower()
    
    def test_local_file_exists(self, scorm_logic, temp_dir):
        """Test validation with existing local file."""
        video_file = temp_dir / "test.mp4"
        video_file.write_bytes(b"fake video")
        
        is_valid, error = scorm_logic.validate_single_inputs(
            title="Test Course",
            video_input="test.mp4",
            video_type="local",
            local_file_path=str(video_file)
        )
        assert is_valid is True


class TestGetOutputFilename:
    """Tests for get_output_filename method."""
    
    def test_normal_title(self, scorm_logic, temp_dir):
        """Test getting output filename with normal title."""
        filename = scorm_logic.get_output_filename("Test Course", str(temp_dir))
        assert filename == str(temp_dir / "Test Course.zip")
    
    def test_title_with_special_chars(self, scorm_logic, temp_dir):
        """Test getting output filename with special characters."""
        filename = scorm_logic.get_output_filename("Course: Test <File>", str(temp_dir))
        # Should sanitize special characters
        assert ":" not in filename or ":" not in Path(filename).name
        assert "<" not in filename
        assert ">" not in filename
