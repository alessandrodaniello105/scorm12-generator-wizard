"""
Pytest configuration and fixtures for SCORM Generator tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logic import SCORMLogic, SCORMGenerator


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def scorm_generator():
    """Create a SCORMGenerator instance for testing."""
    return SCORMGenerator()


@pytest.fixture
def scorm_logic():
    """Create a SCORMLogic instance for testing."""
    return SCORMLogic()


@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file for testing."""
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"fake video content")
    return str(video_path)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for batch testing."""
    return """title,description,path_or_url
Test Course 1,Description 1,https://vimeo.com/123456789
Test Course 2,Description 2,https://www.youtube.com/watch?v=abc123def45
Test Course 3,Description 3,https://example.com/video.mp4"""


@pytest.fixture
def sample_csv_file(temp_dir, sample_csv_content):
    """Create a sample CSV file for batch testing."""
    csv_path = temp_dir / "test_batch.csv"
    csv_path.write_text(sample_csv_content, encoding='utf-8')
    return str(csv_path)
