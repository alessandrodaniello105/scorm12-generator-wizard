"""
Tests specifically for video type detection and ID extraction.
"""
import pytest


class TestVideoDetectionEdgeCases:
    """Test edge cases for video detection."""
    
    def test_vimeo_url_variations(self, scorm_logic):
        """Test various Vimeo URL formats."""
        test_cases = [
            ("https://vimeo.com/123456789", "vimeo"),
            ("https://www.vimeo.com/123456789", "vimeo"),
            ("http://vimeo.com/123456789", "vimeo"),
            ("vimeo.com/123456789", "vimeo"),
            ("https://player.vimeo.com/video/123456789", "vimeo"),
        ]
        
        for url, expected_type in test_cases:
            video_type, _ = scorm_logic.detect_video_type(url)
            assert video_type == expected_type, f"Failed for {url}"
    
    def test_youtube_url_variations(self, scorm_logic):
        """Test various YouTube URL formats."""
        test_cases = [
            ("https://www.youtube.com/watch?v=abc123def45", "youtube"),
            ("https://youtube.com/watch?v=abc123def45", "youtube"),
            ("https://youtu.be/abc123def45", "youtube"),
            ("http://www.youtube.com/watch?v=abc123def45", "youtube"),
            ("https://www.youtube.com/embed/abc123def45", "youtube"),
            ("youtube.com/watch?v=abc123def45", "youtube"),
        ]
        
        for url, expected_type in test_cases:
            video_type, _ = scorm_logic.detect_video_type(url)
            assert video_type == expected_type, f"Failed for {url}"
    
    def test_youtube_id_extraction_edge_cases(self, scorm_logic):
        """Test YouTube ID extraction with various formats."""
        test_cases = [
            ("https://www.youtube.com/watch?v=abc123def45&list=PLxyz", "abc123def45"),
            ("https://www.youtube.com/watch?feature=player_embedded&v=abc123def45", "abc123def45"),
            ("https://youtu.be/abc123def45?t=30", "abc123def45"),
        ]
        
        for url, expected_id in test_cases:
            result = scorm_logic.extract_video_id(url, "youtube")
            assert result == expected_id, f"Failed for {url}"
