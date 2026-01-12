"""
Integration tests for batch CSV processing.
"""
import pytest
import csv
from pathlib import Path
import tempfile
import shutil


class TestBatchProcessing:
    """Tests for batch CSV processing."""
    
    def test_process_valid_csv(self, scorm_logic, sample_csv_file, temp_dir):
        """Test processing a valid CSV file."""
        processed, errors = scorm_logic.process_batch_csv(
            csv_file=sample_csv_file,
            output_dir=str(temp_dir),
            conflict_handler=None
        )
        
        # Should process all rows (3 in sample)
        assert processed == 3
        assert len(errors) == 0
        
        # Check that ZIP files were created
        output_files = list(temp_dir.glob("*.zip"))
        assert len(output_files) == 3
    
    def test_process_csv_with_missing_title(self, scorm_logic, temp_dir):
        """Test processing CSV with missing title."""
        csv_content = """title,description,path_or_url
,Description 1,https://vimeo.com/123456789
Test Course 2,Description 2,https://vimeo.com/987654321"""
        
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content, encoding='utf-8')
        
        processed, errors = scorm_logic.process_batch_csv(
            csv_file=str(csv_file),
            output_dir=str(temp_dir),
            conflict_handler=None
        )
        
        assert processed == 1
        assert len(errors) == 1
        assert "Missing title" in errors[0]
    
    def test_process_csv_with_missing_path(self, scorm_logic, temp_dir):
        """Test processing CSV with missing path_or_url."""
        csv_content = """title,description,path_or_url
Test Course 1,Description 1,
Test Course 2,Description 2,https://vimeo.com/987654321"""
        
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content, encoding='utf-8')
        
        processed, errors = scorm_logic.process_batch_csv(
            csv_file=str(csv_file),
            output_dir=str(temp_dir),
            conflict_handler=None
        )
        
        assert processed == 1
        assert len(errors) == 1
        assert "path_or_url" in errors[0].lower()
    
    def test_process_csv_case_insensitive_columns(self, scorm_logic, temp_dir):
        """Test that CSV column names are case-insensitive."""
        csv_content = """TITLE,DESCRIPTION,PATH_OR_URL
Test Course 1,Description 1,https://vimeo.com/123456789
Test Course 2,Description 2,https://vimeo.com/987654321"""
        
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content, encoding='utf-8')
        
        processed, errors = scorm_logic.process_batch_csv(
            csv_file=str(csv_file),
            output_dir=str(temp_dir),
            conflict_handler=None
        )
        
        assert processed == 2
        assert len(errors) == 0
    
    def test_process_csv_with_local_files(self, scorm_logic, temp_dir):
        """Test processing CSV with local file paths."""
        # Create test video files
        video1 = temp_dir / "video1.mp4"
        video2 = temp_dir / "video2.mp4"
        video1.write_bytes(b"fake video 1")
        video2.write_bytes(b"fake video 2")
        
        csv_content = f"""title,description,path_or_url
Test Course 1,Description 1,{video1}
Test Course 2,Description 2,{video2}"""
        
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content, encoding='utf-8')
        
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        processed, errors = scorm_logic.process_batch_csv(
            csv_file=str(csv_file),
            output_dir=str(output_dir),
            conflict_handler=None
        )
        
        assert processed == 2
        assert len(errors) == 0
