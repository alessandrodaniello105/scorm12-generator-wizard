"""
SCORM package validation module.
Validates SCORM 1.2 package structure and files.
"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict


class SCORMValidator:
    """Validates SCORM 1.2 packages."""
    
    REQUIRED_FILES = [
        'imsmanifest.xml',
        'index.html',
        'config.js'
    ]
    
    REQUIRED_DIRS = [
        'js',
        'css'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_package(self, zip_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a SCORM package ZIP file.
        
        Args:
            zip_path: Path to the SCORM package ZIP file
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        if not Path(zip_path).exists():
            self.errors.append(f"Package file does not exist: {zip_path}")
            return False, self.errors, self.warnings
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                files = zipf.namelist()
                
                # Check required files
                self._check_required_files(files)
                
                # Check manifest structure
                if 'imsmanifest.xml' in files:
                    self._validate_manifest(zipf, files)
                else:
                    self.errors.append("imsmanifest.xml is missing")
                
                # Check for common issues
                self._check_common_issues(files)
        
        except zipfile.BadZipFile:
            self.errors.append("Invalid ZIP file format")
            return False, self.errors, self.warnings
        except Exception as e:
            self.errors.append(f"Error reading package: {str(e)}")
            return False, self.errors, self.warnings
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _check_required_files(self, files: List[str]):
        """Check if all required files are present."""
        for required_file in self.REQUIRED_FILES:
            if required_file not in files:
                self.errors.append(f"Required file missing: {required_file}")
    
    def _validate_manifest(self, zipf: zipfile.ZipFile, files: List[str]):
        """Validate the imsmanifest.xml structure."""
        try:
            manifest_content = zipf.read('imsmanifest.xml').decode('utf-8')
            root = ET.fromstring(manifest_content)
            
            # Check namespace
            if 'http://www.imsproject.org/xsd/imscp_rootv1p1p2' not in root.tag:
                self.warnings.append("Manifest namespace may be incorrect")
            
            # Check metadata
            metadata = root.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}metadata")
            if metadata is None:
                self.warnings.append("Manifest metadata section is missing")
            else:
                schema = metadata.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}schema")
                if schema is None or "ADL SCORM" not in schema.text:
                    self.warnings.append("SCORM schema declaration may be missing or incorrect")
            
            # Check organization
            org = root.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}organization")
            if org is None:
                self.errors.append("Manifest organization section is missing")
            
            # Check resources
            resources = root.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}resources")
            if resources is None:
                self.errors.append("Manifest resources section is missing")
            else:
                # Check if index.html is referenced
                resource = resources.find(".//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}resource[@href='index.html']")
                if resource is None:
                    self.errors.append("index.html is not referenced in manifest resources")
                else:
                    # Check scormtype attribute
                    scormtype = resource.get("{http://www.adlnet.org/xsd/adlcp_rootv1p2}scormtype")
                    if scormtype != "sco":
                        self.warnings.append("Resource scormtype should be 'sco' for SCORM 1.2")
        
        except ET.ParseError as e:
            self.errors.append(f"Manifest XML is malformed: {str(e)}")
        except Exception as e:
            self.errors.append(f"Error parsing manifest: {str(e)}")
    
    def _check_common_issues(self, files: List[str]):
        """Check for common issues in the package."""
        # Check for index.html
        if 'index.html' not in files:
            self.errors.append("index.html is missing")
        
        # Check for config.js
        if 'config.js' not in files:
            self.errors.append("config.js is missing")
        
        # Check for JS directory
        js_files = [f for f in files if f.startswith('js/')]
        if not js_files:
            self.warnings.append("No JavaScript files found in js/ directory")
        
        # Check for CSS directory
        css_files = [f for f in files if f.startswith('css/')]
        if not css_files:
            self.warnings.append("No CSS files found in css/ directory")
        
        # Check for empty files
        # This would require reading the ZIP, so we'll skip for now
    
    def get_validation_report(self, zip_path: str) -> str:
        """
        Get a formatted validation report.
        
        Args:
            zip_path: Path to the SCORM package ZIP file
        
        Returns:
            Formatted validation report string
        """
        is_valid, errors, warnings = self.validate_package(zip_path)
        
        report = f"SCORM Package Validation Report\n"
        report += f"{'=' * 50}\n\n"
        report += f"Package: {Path(zip_path).name}\n"
        report += f"Status: {'✓ VALID' if is_valid else '✗ INVALID'}\n\n"
        
        if errors:
            report += f"Errors ({len(errors)}):\n"
            for i, error in enumerate(errors, 1):
                report += f"  {i}. {error}\n"
            report += "\n"
        
        if warnings:
            report += f"Warnings ({len(warnings)}):\n"
            for i, warning in enumerate(warnings, 1):
                report += f"  {i}. {warning}\n"
            report += "\n"
        
        if is_valid and not warnings:
            report += "Package is valid and ready for use!\n"
        
        return report
