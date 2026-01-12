"""
Modulo di logica per la gestione dei dati e calcoli del SCORM Generator.
Contiene tutte le funzioni di business logic separate dalla GUI.
"""
import os
import re
import csv
import shutil
import zipfile
import xml.etree.ElementTree as ET
import uuid
import sys
from pathlib import Path
from io import StringIO
from typing import Optional, Tuple, List, Dict
from PySide6.QtCore import QObject, Signal  # type: ignore


def _get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        # Running as script, use current directory
        base_path = Path(__file__).parent
    
    return base_path / relative_path


class SCORMGenerator:
    """Generates SCORM 1.2 packages."""
    
    def __init__(self):
        self.template_dir = _get_resource_path("working_scorm_zip_example")
        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory 'working_scorm_zip_example' not found at {self.template_dir}!")
    
    def generate(self, title, description, video_type, video_url, local_video_file=None, 
                 subtitle_file=None, output_dir=".", output_filename=None):
        """
        Generate a SCORM 1.2 package
        
        Args:
            title: Course title (required)
            description: Course description (optional)
            video_type: "vimeo", "youtube", "videojs", or "local"
            video_url: Video ID or URL depending on type
            local_video_file: Path to local video file (if video_type is "local")
            subtitle_file: Path to subtitle file (.srt or .vtt) (optional)
            output_dir: Directory to save the SCORM package
            output_filename: Optional custom filename for the ZIP file (if None, uses sanitized title)
        
        Returns:
            Path to the generated ZIP file
        """
        # Create temporary directory for package
        package_name = self.sanitize_filename(title)
        temp_dir = Path(output_dir) / f"scorm_temp_{uuid.uuid4().hex[:8]}"
        package_dir = temp_dir / package_name
        
        try:
            # Copy template files
            self._copy_template_files(package_dir)
            
            # Copy local video file if provided
            if video_type == "local" and local_video_file:
                shutil.copy2(local_video_file, package_dir / os.path.basename(local_video_file))
            
            # Copy subtitle file if provided
            subtitle_filename = None
            if subtitle_file and os.path.exists(subtitle_file):
                subtitle_filename = os.path.basename(subtitle_file)
                shutil.copy2(subtitle_file, package_dir / subtitle_filename)
            
            # Generate config.js
            self._generate_config(package_dir, video_type, video_url, subtitle_filename)
            
            # Generate imsmanifest.xml
            self._generate_manifest(package_dir, title, description)
            
            # Generate index.html
            self._generate_index_html(package_dir, title, description, video_type, subtitle_filename)
            
            # Create ZIP file - use custom filename if provided, otherwise use default
            if output_filename:
                zip_path = Path(output_filename)
            else:
                zip_path = Path(output_dir) / f"{package_name}.zip"
            self._create_zip(package_dir, zip_path)
            
            return str(zip_path)
            
        finally:
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        return filename or "scorm_package"
    
    def _copy_template_files(self, package_dir):
        """Copy all template files from working example"""
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files and directories
        for item in self.template_dir.iterdir():
            if item.is_file():
                # Skip config.js and imsmanifest.xml as we'll generate them
                if item.name not in ['config.js', 'imsmanifest.xml', 'index.html']:
                    shutil.copy2(item, package_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, package_dir / item.name, dirs_exist_ok=True)
    
    def _generate_config(self, package_dir, video_type, video_url, subtitle_filename=None):
        """Generate config.js file"""
        # Map video_type to playerType
        player_type_map = {
            "vimeo": "vimeo",
            "youtube": "youtube",
            "videojs": "videojs",
            "local": "videojs"
        }
        
        player_type = player_type_map.get(video_type, "videojs")
        
        # Generate tracks array if subtitle file exists
        # Note: Tracks only work with VideoJS player (local and remote URLs)
        # Vimeo and YouTube have their own subtitle systems
        tracks_content = ""
        if subtitle_filename and player_type == "videojs":
            # Determine kind based on file extension
            kind = "subtitles"
            srclang = "en"  # Default language, could be extracted from filename
            label = "English"  # Default label
            
            # Try to extract language from filename (e.g., subtitles.en.srt)
            lang_match = re.search(r'\.([a-z]{2})\.(srt|vtt)$', subtitle_filename.lower())
            if lang_match:
                srclang = lang_match.group(1)
                label = srclang.upper()
            
            # Escape the filename for JavaScript
            subtitle_filename_escaped = subtitle_filename.replace('\\', '/').replace('"', '\\"')
            
            tracks_content = f"""
        {{
            src: "{subtitle_filename_escaped}",
            kind: "{kind}",
            srclang: "{srclang}",
            label: "{label}",
            default: true
        }}"""
        
        config_content = f"""var videoall_config = {{
    // Tracking mode is:
    // "none" for no tracking
    // "scorm12" for SCORM 1.2
    // "scorm2004" for SCORM 2004
    // "xapi" for Tin Can/XAPI
    trackingMode: "scorm12",
    // Player type can be:
    // "youtube" for Youtube videos.  "url" is the ID of the Youtube video.
    // "vimeo" for Vimeo videos.  "url" is the ID of the Vimeo video.
    // "videojs" for local videos.  "url" is a URL to the video, relative or absolute.
    playerType: "{player_type}",
    width: "100%",
    height: "100%",
    url: "{video_url}",
    
    autoplay: true,
    seekModeIncomplete: "ONLY_BACKWARD", // NONE, ANYWHERE, ONLY_BACKWARD
    seekModeCompleted: "ANYWHERE", // NONE, ANYWHERE, ONLY_BACKWARD
    bookmarkQuestion: "Would you like to return to your bookmark?",
    bookmarkForceResume: true,
    completionBy: "END", // END, PERCENT_WATCHED
    completionFraction: 1,
    completeFn: function() {{
        // console.log("Perform custom completion activities here.");
    }},
    tracks: [{tracks_content}
    ],
    poster: ""
}};
"""
        with open(package_dir / "config.js", "w", encoding="utf-8") as f:
            f.write(config_content)
    
    def _generate_manifest(self, package_dir, title, description):
        """Generate imsmanifest.xml file"""
        # Escape XML special characters
        def escape_xml(text):
            if not text:
                return ""
            return (text.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;")
                       .replace('"', "&quot;")
                       .replace("'", "&apos;"))
        
        title_escaped = escape_xml(title)
        
        manifest_content = f'''<manifest identifier="ssv" version="3.0.2" xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd
http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
	<metadata>
		<schema>ADL SCORM</schema>
		<schemaversion>1.2</schemaversion>
	</metadata>
	<organizations default="JCA">
		<organization identifier="JCA">
			<title>{title_escaped}</title>
			<item identifier="quiz1" identifierref="testerf" isvisible="true">
				<title>{title_escaped}</title>
			</item>
		</organization>
	</organizations>
	<resources>
		<resource adlcp:scormtype="sco" identifier="testerf" type="webcontent" href="index.html">
		</resource>
	</resources>
</manifest>'''
        
        with open(package_dir / "imsmanifest.xml", "w", encoding="utf-8") as f:
            f.write(manifest_content)
    
    def _generate_index_html(self, package_dir, title, description, video_type="videojs", subtitle_filename=None):
        """Generate index.html file"""
        # Escape HTML special characters
        def escape_html(text):
            if not text:
                return ""
            return (text.replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;")
                       .replace('"', "&quot;")
                       .replace("'", "&#x27;"))
        
        title_escaped = escape_html(title)
        desc_escaped = escape_html(description)
        
        # Add script to manually add tracks for VideoJS players if subtitle exists
        # This is a fallback in case the compiled main.js doesn't handle tracks from config
        tracks_script = ""
        if subtitle_filename and video_type in ["videojs", "local"]:
            # Determine language from filename
            srclang = "en"
            label = "English"
            lang_match = re.search(r'\.([a-z]{2})\.(srt|vtt)$', subtitle_filename.lower())
            if lang_match:
                srclang = lang_match.group(1)
                label = srclang.upper()
            
            subtitle_filename_escaped = escape_html(subtitle_filename)
            # Escape for JavaScript string
            subtitle_filename_js = subtitle_filename.replace('\\', '/').replace('"', '\\"')
            tracks_script = f"""
        // Manually add subtitle tracks for VideoJS player as fallback
        // This ensures tracks are added even if main.js doesn't handle config.tracks
        (function() {{
            function addTracksToPlayer() {{
                try {{
                    // Try to get player from videoall object
                    var player = null;
                    if (typeof ssv !== 'undefined' && ssv.videoall) {{
                        var playerType = ssv.videoall.config && ssv.videoall.config.playerType;
                        if (playerType === 'videojs' && ssv.videoall.videojs) {{
                            player = ssv.videoall.videojs.player || ssv.videoall.videojs;
                        }}
                    }}
                    
                    // If player not found, try to find VideoJS player by ID
                    if (!player && typeof videojs !== 'undefined') {{
                        var players = videojs.getPlayers();
                        for (var id in players) {{
                            player = players[id];
                            break;
                        }}
                    }}
                    
                    if (player && typeof player.addRemoteTextTrack === 'function') {{
                        // Check if track already exists
                        var tracks = player.textTracks();
                        var trackExists = false;
                        for (var i = 0; i < tracks.length; i++) {{
                            if (tracks[i].src && tracks[i].src.indexOf("{subtitle_filename_js}") !== -1) {{
                                trackExists = true;
                                break;
                            }}
                        }}
                        
                        if (!trackExists) {{
                            player.addRemoteTextTrack({{
                                src: "{subtitle_filename_js}",
                                kind: "subtitles",
                                srclang: "{srclang}",
                                label: "{label}",
                                default: true
                            }}, true);
                        }}
                    }}
                }} catch(e) {{
                    console.log('Error adding subtitle tracks:', e);
                }}
            }}
            
            // Try immediately
            addTracksToPlayer();
            
            // Try after player initialization (with delays)
            setTimeout(addTracksToPlayer, 500);
            setTimeout(addTracksToPlayer, 1500);
            setTimeout(addTracksToPlayer, 3000);
        }})();"""
        
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <link href="js/3rd/videojs/video-js.css" rel="stylesheet">
    <link href="css/style.css" rel="stylesheet">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script type="text/javascript">
        document.createElement('video');
        document.createElement('audio');
        document.createElement('track');
    </script>
    <script src="js/3rd/videojs/video.js"></script>
    <script>
        videojs.options.techOrder = ['html5'];
    </script>
    <script type="text/javascript" src="js/3rd/xapiwrapper.min.js"></script>
    <script type="text/javascript" src="config.js"></script>
    <script type="text/javascript" src="js/main.js"></script>
</head>
<body onbeforeunload="ssv.videoall.updateBookmark()">
<div id="bookmarkAlert" class="modal" style="display: none">
    <div class="modal-content">
        <h3>Bookmark Detected</h3>
        <p id="bookmarkQuestion">...</p>
        <button id="bookmarkYes">Yes</button>
        <button id="bookmarkNo">No</button>
    </div>
</div>
<div id="container">
    <div id="player"></div>
    <div id="titlebox">
        <div style="flex-grow: 10; padding: 10px;">
            {title_escaped}
            <br/>
            <div class="desc" style="font-weight:normal;">{desc_escaped}</div>
            
        </div>
    </div>
</div>
    <script>
        document.getElementById('titlebox').style.width = ssv.videoall.config.width + 'px';
        document.addEventListener('contextmenu', event => event.preventDefault());{tracks_script}
    </script>
</body>
</html>'''
        
        with open(package_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _create_zip(self, package_dir, zip_path):
        """Create ZIP file from package directory"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)


class SCORMLogic(QObject):
    """
    Classe che gestisce tutta la logica di business per il generatore SCORM.
    Comunica con la GUI tramite Signals di PySide6.
    """
    # Signals per comunicare con la GUI
    progress_updated = Signal(int, str)  # progress_percentage, status_message
    package_generated = Signal(str)  # output_path
    error_occurred = Signal(str)  # error_message
    batch_progress_updated = Signal(int, int, str)  # current, total, status_message
    batch_complete = Signal(int, list)  # processed_count, errors_list
    
    def __init__(self):
        super().__init__()
        self.generator = SCORMGenerator()
    
    def extract_video_id(self, url: str, video_type: str) -> Optional[str]:
        """
        Estrae l'ID del video dall'URL o restituisce l'input se è già un ID.
        
        Args:
            url: URL o ID del video
            video_type: Tipo di video ("vimeo", "youtube", "videojs", "local")
        
        Returns:
            ID del video o URL processato
        """
        if not url:
            return None
            
        if video_type == "vimeo":
            # Vimeo: estrae ID dall'URL o usa come-is se numerico
            if url.isdigit():
                return url
            # Estrae da vimeo.com/ID o player.vimeo.com/video/ID
            match = re.search(r'vimeo\.com/(?:video/)?(\d+)', url)
            return match.group(1) if match else url
        elif video_type == "youtube":
            # YouTube: estrae ID dall'URL o usa come-is
            if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
                return url
            # Estrae da vari formati di URL YouTube
            patterns = [
                r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
                r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return url
        else:
            return url
    
    def detect_video_type(self, path_or_url: str) -> Tuple[str, str]:
        """
        Rileva il tipo di video da path o URL.
        
        Args:
            path_or_url: Path locale o URL del video
        
        Returns:
            Tupla (video_type, video_input)
        """
        path_or_url = path_or_url.strip()
        
        # Controlla se è un path locale (Windows)
        if os.path.exists(path_or_url) or (len(path_or_url) > 2 and path_or_url[1] == ':'):
            return "local", path_or_url
        
        # Controlla per Vimeo
        if "vimeo.com" in path_or_url.lower():
            return "vimeo", path_or_url
        
        # Controlla per YouTube
        if "youtube.com" in path_or_url.lower() or "youtu.be" in path_or_url.lower():
            return "youtube", path_or_url
        
        # Default a remote URL
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return "videojs", path_or_url
        
        # Se è solo un numero, assume Vimeo ID
        if path_or_url.isdigit():
            return "vimeo", path_or_url
        
        # Se sembra un YouTube ID (11 caratteri alfanumerici)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', path_or_url):
            return "youtube", path_or_url
        
        # Default a videojs per URL
        return "videojs", path_or_url
    
    def get_output_filename(self, title: str, output_dir: str) -> str:
        """
        Ottiene il nome del file di output per un pacchetto SCORM.
        
        Args:
            title: Titolo del corso
            output_dir: Directory di output
        
        Returns:
            Path completo del file ZIP
        """
        package_name = self.generator.sanitize_filename(title)
        return str(Path(output_dir) / f"{package_name}.zip")
    
    def validate_single_inputs(self, title: str, video_input: str, 
                              video_type: str, local_file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Valida gli input per la modalità singola.
        
        Args:
            title: Titolo del corso
            video_input: Input video (ID/URL)
            video_type: Tipo di video
            local_file_path: Path del file locale (se applicabile)
        
        Returns:
            Tupla (is_valid, error_message)
        """
        if not title or not title.strip():
            return False, "Title is required!"
        
        if not video_input or not video_input.strip():
            return False, "Please provide video ID/URL or select a file!"
        
        if video_type == "local":
            if not local_file_path or not os.path.exists(local_file_path):
                return False, "Please select a valid video file!"
        
        return True, None
    
    def generate_scorm_package(self, title: str, description: str, video_type: str,
                               video_url: str, local_video_file: Optional[str],
                               output_dir: str, output_filename: Optional[str] = None,
                               subtitle_file: Optional[str] = None) -> str:
        """
        Genera un pacchetto SCORM.
        
        Args:
            title: Titolo del corso
            description: Descrizione del corso
            video_type: Tipo di video
            video_url: URL o ID del video
            local_video_file: Path del file video locale (se applicabile)
            output_dir: Directory di output
            output_filename: Nome file personalizzato (opzionale)
            subtitle_file: Path del file subtitle (opzionale)
        
        Returns:
            Path del file ZIP generato
        """
        self.progress_updated.emit(25, "Extracting video information...")
        
        # Estrae video ID/URL se necessario
        if video_type == "local":
            video_url = os.path.basename(local_video_file) if local_video_file else video_url
        else:
            video_url = self.extract_video_id(video_url, video_type)
        
        self.progress_updated.emit(50, "Generating SCORM package...")
        
        # Genera il pacchetto SCORM
        output_path = self.generator.generate(
            title=title,
            description=description,
            video_type=video_type,
            video_url=video_url,
            local_video_file=local_video_file,
            subtitle_file=subtitle_file,
            output_dir=output_dir,
            output_filename=output_filename
        )
        
        self.progress_updated.emit(100, "✓ Package generated successfully!")
        return output_path
    
    def process_batch_csv(self, csv_file: str, output_dir: str, 
                         conflict_handler=None) -> Tuple[int, List[str]]:
        """
        Processa un file CSV in modalità batch.
        
        Args:
            csv_file: Path del file CSV
            output_dir: Directory di output
            conflict_handler: Funzione callback per gestire conflitti di file.
                             Deve accettare (file_path, apply_to_all) e restituire
                             (action, final_path, new_apply_to_all)
                             dove action può essere: 'overwrite', 'rename', 'skip', 'cancel'
        
        Returns:
            Tupla (processed_count, errors_list)
        """
        processed = 0
        errors = []
        apply_to_all = None  # Track "apply to all" setting for file conflicts
        
        # Prova diversi encoding
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        csv_data = None
        encoding_used = None
        
        for enc in encodings:
            try:
                with open(csv_file, 'r', encoding=enc) as f:
                    csv_data = f.read()
                    encoding_used = enc
                    break
            except UnicodeDecodeError:
                continue
        
        if csv_data is None:
            raise ValueError("Could not read CSV file. Please check the file encoding.")
        
        # Rileva delimiter
        sniffer = csv.Sniffer()
        try:
            delimiter = sniffer.sniff(csv_data[:1024]).delimiter
        except:
            delimiter = ','  # Default a virgola
        
        # Leggi CSV con delimiter rilevato
        reader = csv.DictReader(StringIO(csv_data), delimiter=delimiter)
        
        # Ottieni fieldnames originali
        original_fieldnames = reader.fieldnames
        if not original_fieldnames:
            raise ValueError("CSV file appears to be empty or has no headers!")
        
        # Crea mapping case-insensitive dei fieldnames
        fieldname_map = {}
        for orig_name in original_fieldnames:
            normalized = orig_name.strip().lower()
            fieldname_map[normalized] = orig_name
        
        # Conta righe totali
        reader_temp = csv.DictReader(StringIO(csv_data), delimiter=delimiter)
        total_rows = sum(1 for _ in reader_temp)
        
        # Emetti info sulle colonne rilevate
        columns_info = f"Detected columns: {', '.join(original_fieldnames)}"
        if total_rows > 0:
            self.batch_progress_updated.emit(0, total_rows, 
                                            f"{columns_info}\nFound {total_rows} rows to process")
        else:
            self.batch_progress_updated.emit(0, 0, columns_info)
        
        # Reset reader
        reader = csv.DictReader(StringIO(csv_data), delimiter=delimiter)
        
        # Helper function per ottenere valore case-insensitive
        def get_field(row, field_name, alternatives=None):
            if alternatives is None:
                alternatives = [field_name]
            # Prima prova usando fieldname_map
            if field_name in fieldname_map:
                orig_key = fieldname_map[field_name]
                if orig_key in row:
                    value = str(row[orig_key]).strip()
                    if value:
                        return value
            # Prova match case-insensitive su tutte le chiavi
            for key in row.keys():
                key_normalized = key.strip().lower()
                if key_normalized in alternatives or key_normalized == field_name:
                    value = str(row[key]).strip()
                    if value:
                        return value
            return ''
        
        for row_num, row in enumerate(reader, start=2):  # Inizia da 2 (header è riga 1)
            try:
                # Debug prima riga
                if row_num == 2:
                    debug_info = f"First row keys: {list(row.keys())}\nFirst row values: {list(row.values())}"
                    if total_rows > 0:
                        self.batch_progress_updated.emit(0, total_rows, 
                                                        f"{columns_info}\n{debug_info}")
                    else:
                        self.batch_progress_updated.emit(0, 0, f"{columns_info}\n{debug_info}")
                
                # Ottieni valori (case-insensitive)
                title = get_field(row, 'title')
                description = get_field(row, 'description')
                path_or_url = get_field(row, 'path_or_url', 
                                       ['path_or_url', 'path', 'url', 'video_path', 'video_url'])
                subtitle_path = get_field(row, 'subtitle_path', 
                                         ['subtitle_path', 'subtitle', 'subtitle_file', 'srt', 'vtt'])
                
                if not title:
                    errors.append(f"Row {row_num}: Missing title")
                    continue
                
                if not path_or_url:
                    errors.append(f"Row {row_num}: Missing path_or_url")
                    continue
                
                # Rileva tipo video
                video_type, video_input = self.detect_video_type(path_or_url)
                
                # Estrae video ID/URL
                if video_type == "local":
                    if not os.path.exists(video_input):
                        errors.append(f"Row {row_num}: Local file not found: {video_input}")
                        continue
                    video_url = os.path.basename(video_input)
                    local_file = video_input
                else:
                    video_url = self.extract_video_id(video_input, video_type)
                    local_file = None
                
                # Aggiorna progresso prima del processamento
                if total_rows > 0:
                    progress = (row_num - 2) / total_rows * 100
                    self.batch_progress_updated.emit(row_num - 1, total_rows, 
                                                    f"Processing row {row_num - 1}/{total_rows}: {title[:50]}...")
                else:
                    self.batch_progress_updated.emit(row_num - 1, 0, 
                                                    f"Processing row {row_num - 1}: {title[:50]}...")
                
                # Genera pacchetto SCORM
                output_file = self.get_output_filename(title, output_dir)
                
                # Controlla se il file esiste e gestisci conflitto
                final_path = output_file
                if os.path.exists(output_file):
                    if conflict_handler:
                        # Usa il conflict handler per gestire il conflitto
                        action, final_path, apply_to_all = conflict_handler(output_file, apply_to_all)
                        
                        if action == 'cancel':
                            errors.append(f"Row {row_num}: Cancelled by user")
                            break  # Interrompi il processamento
                        
                        if action == 'skip':
                            errors.append(f"Row {row_num}: Skipped by user")
                            continue  # Salta questo file e continua
                        
                        # action è 'overwrite' o 'rename', final_path è già impostato
                    else:
                        # Nessun handler, salta automaticamente
                        errors.append(f"Row {row_num}: File already exists (skipped): {output_file}")
                        continue
                
                # Validate subtitle file if provided
                subtitle_file = None
                if subtitle_path:
                    if os.path.exists(subtitle_path):
                        subtitle_file = subtitle_path
                    else:
                        errors.append(f"Row {row_num}: Subtitle file not found: {subtitle_path}")
                        # Continue without subtitle
                
                output_path = self.generator.generate(
                    title=title,
                    description=description,
                    video_type=video_type,
                    video_url=video_url,
                    local_video_file=local_file,
                    subtitle_file=subtitle_file,
                    output_dir=output_dir,
                    output_filename=final_path
                )
                
                processed += 1
                if total_rows > 0:
                    progress = processed / total_rows * 100
                    self.batch_progress_updated.emit(processed, total_rows,
                                                    f"✓ Processed {processed}/{total_rows}: {title[:50]}")
                else:
                    self.batch_progress_updated.emit(processed, 0,
                                                    f"✓ Processed {processed}: {title[:50]}")
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        return processed, errors
