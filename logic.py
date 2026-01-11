"""
Modulo di logica per la gestione dei dati e calcoli del SCORM Generator.
Contiene tutte le funzioni di business logic separate dalla GUI.
"""
import os
import re
import csv
from pathlib import Path
from io import StringIO
from typing import Optional, Tuple, List, Dict
from PySide6.QtCore import QObject, Signal  # type: ignore

from scorm_generator import SCORMGenerator


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
                               output_dir: str, output_filename: Optional[str] = None) -> str:
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
                
                output_path = self.generator.generate(
                    title=title,
                    description=description,
                    video_type=video_type,
                    video_url=video_url,
                    local_video_file=local_file,
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
