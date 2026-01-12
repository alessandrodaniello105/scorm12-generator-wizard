"""
Modulo GUI per l'interfaccia PySide6 del SCORM Generator.
Contiene solo la classe per l'interfaccia utente, la comunicazione con la logica
avviene tramite Signals di PySide6.
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, #type: ignore
                                QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, 
                                QRadioButton, QButtonGroup, QProgressBar, QMessageBox, 
                                QFileDialog, QDialog, QFrame) #type: ignore
from PySide6.QtCore import Qt, Signal, QThread #type: ignore
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut #type: ignore
from PySide6.QtWidgets import QStyle #type: ignore
import os
import re
from config import Config


class SCORMWizard(QMainWindow):
    """
    Classe principale per l'interfaccia grafica del SCORM Generator.
    Comunica con la logica tramite Signals.
    """
    # Signals emessi dalla GUI verso la logica
    generate_requested = Signal(str, str, str, str, str, str, str)  # title, description, video_type, video_url, local_file, subtitle_file, output_dir
    batch_process_requested = Signal(str, str)  # csv_file, output_dir
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCORM Wrapper Wizard v0.4")
        self.setFixedSize(600, 550)  # Increased height for error labels
        
        # Variables
        self.video_type = "vimeo"
        self.video_url = ""
        self.title_text = ""
        self.description_text = ""
        self.local_file_path = ""
        self.subtitle_file_path = ""
        self.batch_mode = False
        self.config = Config()
        
        # Validation state
        self.validation_errors = {
            'title': '',
            'video': ''
        }
        
        self.setup_ui()
        
        # Imposta sempre i tooltip
        self._setup_tooltips()
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
        # Load saved preferences
        self._load_preferences()
        
        # Setup real-time validation
        self._setup_validation()
        
    def setup_ui(self):
        """Configura l'interfaccia utente"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # Title and Help button layout
        title_layout = QHBoxLayout()
        title_label = QLabel("SCORM 1.2 Wrapper Wizard")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Help button with icon
        self.help_btn = QPushButton()
        self.help_btn.setFixedSize(30, 30)
        # Use Qt standard help icon
        help_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        self.help_btn.setIcon(help_icon)
        self.help_btn.setIconSize(self.help_btn.size())
        self.help_btn.clicked.connect(self.show_help_modal)
        self.help_btn.setToolTip("Apri la guida completa")
        title_layout.addWidget(self.help_btn)
        main_layout.addLayout(title_layout)
        
        # Video Type Selection
        video_type_layout = QHBoxLayout()
        video_type_label = QLabel("Video Source:")
        video_type_font = QFont("Arial", 10, QFont.Bold)
        video_type_label.setFont(video_type_font)
        video_type_layout.addWidget(video_type_label)
        
        # Radio buttons group
        self.video_type_group = QButtonGroup()
        video_frame = QWidget()
        video_frame_layout = QHBoxLayout(video_frame)
        video_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.vimeo_radio = QRadioButton("Vimeo")
        self.vimeo_radio.setChecked(True)
        self.vimeo_radio.toggled.connect(self.on_video_type_change)
        self.video_type_group.addButton(self.vimeo_radio, 0)
        video_frame_layout.addWidget(self.vimeo_radio)
        
        self.youtube_radio = QRadioButton("YouTube")
        self.youtube_radio.toggled.connect(self.on_video_type_change)
        self.video_type_group.addButton(self.youtube_radio, 1)
        video_frame_layout.addWidget(self.youtube_radio)
        
        self.remote_radio = QRadioButton("Remote URL")
        self.remote_radio.toggled.connect(self.on_video_type_change)
        self.video_type_group.addButton(self.remote_radio, 2)
        video_frame_layout.addWidget(self.remote_radio)
        
        self.local_radio = QRadioButton("Local File")
        self.local_radio.toggled.connect(self.on_video_type_change)
        self.video_type_group.addButton(self.local_radio, 3)
        video_frame_layout.addWidget(self.local_radio)
        
        video_type_layout.addWidget(video_frame)
        video_type_layout.addStretch()
        main_layout.addLayout(video_type_layout)
        
        # Riferimenti ai widget per i tooltip
        self.video_source_label = video_type_label
        self.video_source_frame = video_frame
        
        # Video URL/ID Input
        url_container = QWidget()
        url_container_layout = QVBoxLayout(url_container)
        url_container_layout.setContentsMargins(0, 0, 0, 0)
        url_container_layout.setSpacing(2)
        
        url_layout = QHBoxLayout()
        self.url_label = QLabel("Vimeo Video ID:")
        url_layout.addWidget(self.url_label)
        
        self.url_entry = QLineEdit()
        url_layout.addWidget(self.url_entry)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_file)
        self.browse_btn.hide()  # Hide initially
        url_layout.addWidget(self.browse_btn)
        url_container_layout.addLayout(url_layout)
        
        # Error label for video input
        self.video_error_label = QLabel("")
        self.video_error_label.setStyleSheet("color: red; font-size: 9px;")
        self.video_error_label.setWordWrap(True)
        url_container_layout.addWidget(self.video_error_label)
        
        main_layout.addWidget(url_container)
        
        # Title Input
        title_container = QWidget()
        title_container_layout = QVBoxLayout(title_container)
        title_container_layout.setContentsMargins(0, 0, 0, 0)
        title_container_layout.setSpacing(2)
        
        title_layout = QHBoxLayout()
        title_label = QLabel("Title:")
        title_label.setFont(video_type_font)
        title_layout.addWidget(title_label)
        self.title_entry = QLineEdit()
        title_layout.addWidget(self.title_entry)
        title_container_layout.addLayout(title_layout)
        
        # Error label for title
        self.title_error_label = QLabel("")
        self.title_error_label.setStyleSheet("color: red; font-size: 9px;")
        self.title_error_label.setWordWrap(True)
        title_container_layout.addWidget(self.title_error_label)
        
        main_layout.addWidget(title_container)
        
        # Riferimenti ai widget per i tooltip
        self.title_label_widget = title_label
        
        # Description Input
        desc_layout = QHBoxLayout()
        desc_label = QLabel("Description:")
        desc_label.setFont(video_type_font)
        desc_layout.addWidget(desc_label)
        self.desc_text = QTextEdit()
        self.desc_text.setMaximumHeight(100)
        desc_layout.addWidget(self.desc_text)
        main_layout.addLayout(desc_layout)
        
        # Riferimenti ai widget per i tooltip
        self.description_label_widget = desc_label
        
        # Subtitle Input (optional)
        subtitle_layout = QHBoxLayout()
        subtitle_label = QLabel("Subtitle File (optional):")
        subtitle_label.setFont(video_type_font)
        subtitle_layout.addWidget(subtitle_label)
        self.subtitle_entry = QLineEdit()
        self.subtitle_entry.setEnabled(False)
        subtitle_layout.addWidget(self.subtitle_entry)
        self.subtitle_browse_btn = QPushButton("Browse")
        self.subtitle_browse_btn.clicked.connect(self.browse_subtitle_file)
        subtitle_layout.addWidget(self.subtitle_browse_btn)
        main_layout.addLayout(subtitle_layout)
        
        # Help text
        help_text = "For Vimeo/YouTube: Enter video ID only\nFor Remote URL: Enter full video URL\nFor Local File: Click Browse to select"
        help_label = QLabel(help_text)
        help_font = QFont("Arial", 8)
        help_label.setFont(help_font)
        help_label.setStyleSheet("color: gray;")
        main_layout.addWidget(help_label)
        
        # Generate Button
        self.generate_btn = QPushButton("Generate SCORM Package")
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        self.generate_btn.setEnabled(False)  # Disabled until valid
        main_layout.addWidget(self.generate_btn)
        
        # Progress bar (initially hidden)
        self.progress_bar_single = QProgressBar()
        self.progress_bar_single.setMaximum(100)
        self.progress_bar_single.hide()
        main_layout.addWidget(self.progress_bar_single)
        
        # Status label for single mode
        self.status_label_single = QLabel("")
        status_font = QFont("Arial", 9)
        self.status_label_single.setFont(status_font)
        main_layout.addWidget(self.status_label_single)
        
        main_layout.addStretch()
        
        # Batch Mode Button (bottom right)
        self.batch_btn = QPushButton("Batch Mode")
        self.batch_btn.clicked.connect(self.toggle_batch_mode)
        self.batch_btn.setParent(central_widget)
        self.batch_btn.setGeometry(450, 500, 130, 30)
    
    def _setup_tooltips(self):
        """Imposta sempre i tooltip sui widget per la modalità single"""
        if self.batch_mode:
            return
        
        video_source_tooltip_text = (
            "Dove si trova il tuo video?\n"
            "- Vimeo: allora inserisci solo l'id del video\n"
            "- YouTube: allora inserisci solo l'id del video\n"
            "- Remote URL: inserisci il link intero fino a \".mp4\"\n"
            "- Local File: inserisci il percorso completo del file (\"C:\\Windows\\...\\nome-file.mp4\")"
        )
        
        title_tooltip_text = "Il titolo che verrà mostrato per il modulo di questo video (obbligatorio)"
        
        description_tooltip_text = "La descrizione che verrà mostrata per il modulo di questo video (facoltativo)"
        
        generate_tooltip_text = (
            "Clicca qui per scegliere la cartella di destinazione del pacchetto .zip. "
            "Subito dopo seguirà la generazione pacchetto SCORM."
        )
        
        # Imposta sempre i tooltip sui widget
        self.video_source_label.setToolTip(video_source_tooltip_text)
        self.video_source_frame.setToolTip(video_source_tooltip_text)
        self.title_label_widget.setToolTip(title_tooltip_text)
        self.title_entry.setToolTip(title_tooltip_text)
        self.description_label_widget.setToolTip(description_tooltip_text)
        self.desc_text.setToolTip(description_tooltip_text)
        self.generate_btn.setToolTip(generate_tooltip_text)
        
        # Tooltip per il pulsante Browse
        self.browse_btn.setToolTip("Clicca su \"Browse\" per selezionare il file video")
        
        # Imposta il tooltip dinamico per il campo video in base al tipo corrente
        self._update_video_input_tooltip()
    
    def show_help_modal(self):
        """Mostra una finestra modale con tutti i tooltip"""
        if self.batch_mode:
            # Per batch mode, implementeremo quando avremo i tooltip
            return
        
        # Crea finestra modale per single mode
        
        # Crea finestra modale per single mode
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Guida - SCORM Wrapper Wizard")
        help_dialog.setFixedSize(500, 400)
        help_dialog.setModal(True)
        
        layout = QVBoxLayout(help_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Titolo
        title_label = QLabel("Guida all'utilizzo")
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Video Source
        video_source_label = QLabel("<b>Video Source:</b>")
        video_source_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(video_source_label)
        
        video_source_text = QLabel(
            "Dove si trova il tuo video?\n"
            "• Vimeo: allora inserisci solo l'id del video\n"
            "• YouTube: allora inserisci solo l'id del video\n"
            "• Remote URL: inserisci il link intero fino a \".mp4\"\n"
            "• Local File: clicca su \"Browse\" per selezionare il file video"
        )
        video_source_text.setWordWrap(True)
        video_source_text.setStyleSheet("padding: 5px;")
        layout.addWidget(video_source_text)
        
        # Title
        title_help_label = QLabel("<b>Title:</b>")
        title_help_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_help_label)
        
        title_help_text = QLabel("Il titolo che verrà mostrato per il modulo di questo video (obbligatorio)")
        title_help_text.setWordWrap(True)
        title_help_text.setStyleSheet("padding: 5px;")
        layout.addWidget(title_help_text)
        
        # Description
        desc_help_label = QLabel("<b>Description:</b>")
        desc_help_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(desc_help_label)
        
        desc_help_text = QLabel("La descrizione che verrà mostrata per il modulo di questo video (facoltativo)")
        desc_help_text.setWordWrap(True)
        desc_help_text.setStyleSheet("padding: 5px;")
        layout.addWidget(desc_help_text)
        
        # Generate Button
        generate_help_label = QLabel("<b>Bottone \"GENERATE SCORM PACKAGE\":</b>")
        generate_help_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(generate_help_label)
        
        generate_help_text = QLabel(
            "Clicca qui per scegliere la cartella di destinazione del pacchetto .zip. "
            "Subito dopo inizierà la generazione pacchetto SCORM."
        )
        generate_help_text.setWordWrap(True)
        generate_help_text.setStyleSheet("padding: 5px;")
        layout.addWidget(generate_help_text)
        
        layout.addStretch()
        
        # Pulsante chiudi
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(help_dialog.accept)
        layout.addWidget(close_btn)
        
        help_dialog.exec()
    
    def _setup_validation(self):
        """Setup real-time validation for input fields."""
        self.title_entry.textChanged.connect(self._validate_title)
        self.url_entry.textChanged.connect(self._validate_video_input)
        self.desc_text.textChanged.connect(self._validate_form)
        # Initial validation
        self._validate_form()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+G: Generate
        QShortcut(QKeySequence("Ctrl+G"), self, self.on_generate_clicked)
        # Ctrl+B: Toggle batch mode
        QShortcut(QKeySequence("Ctrl+B"), self, self.toggle_batch_mode)
        # F1: Help
        QShortcut(QKeySequence("F1"), self, self.show_help_modal)
        # Enter: Submit (when form is valid)
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(lambda: self.on_generate_clicked() if self.generate_btn.isEnabled() else None)
    
    def _load_preferences(self):
        """Load saved user preferences."""
        # Load last video type
        last_type = self.config.get_last_video_type()
        if last_type == "youtube":
            self.youtube_radio.setChecked(True)
            self.on_video_type_change()
        elif last_type == "videojs":
            self.remote_radio.setChecked(True)
            self.on_video_type_change()
        elif last_type == "local":
            self.local_radio.setChecked(True)
            self.on_video_type_change()
    
    def _validate_title(self):
        """Validate title field."""
        title = self.title_entry.text().strip()
        if not title:
            self.validation_errors['title'] = "Title is required"
            self._show_field_error(self.title_entry, self.title_error_label, "Title is required")
        else:
            self.validation_errors['title'] = ''
            self._clear_field_error(self.title_entry, self.title_error_label)
        self._validate_form()
    
    def _validate_video_input(self):
        """Validate video input field."""
        video_input = self.url_entry.text().strip()
        error = ''
        
        if self.video_type == "local":
            if not self.local_file_path or not os.path.exists(self.local_file_path):
                error = "Please select a valid video file"
        else:
            if not video_input:
                error = "Please provide video ID/URL"
            elif self.video_type == "vimeo":
                # Vimeo ID should be numeric or extractable from URL
                if not video_input.isdigit() and "vimeo.com" not in video_input.lower():
                    error = "Invalid Vimeo ID. Expected format: 123456789 or vimeo.com/123456789"
            elif self.video_type == "youtube":
                # YouTube ID should be 11 chars or extractable from URL
                if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_input) and "youtube.com" not in video_input.lower() and "youtu.be" not in video_input.lower():
                    error = "Invalid YouTube ID. Expected format: abc123def45 or youtube.com/watch?v=abc123def45"
            elif self.video_type == "videojs":
                # Remote URL should start with http:// or https://
                if not video_input.startswith(("http://", "https://")):
                    error = "Invalid URL. Must start with http:// or https://"
        
        self.validation_errors['video'] = error
        if error:
            self._show_field_error(self.url_entry, self.video_error_label, error)
        else:
            self._clear_field_error(self.url_entry, self.video_error_label)
        self._validate_form()
    
    def _validate_form(self):
        """Validate entire form and enable/disable generate button."""
        is_valid = not any(self.validation_errors.values())
        self.generate_btn.setEnabled(is_valid)
    
    def _show_field_error(self, field, error_label, message):
        """Show error styling on field and error message."""
        field.setStyleSheet("border: 2px solid red;")
        error_label.setText(message)
        error_label.show()
    
    def _clear_field_error(self, field, error_label):
        """Clear error styling from field."""
        field.setStyleSheet("")
        error_label.setText("")
        error_label.hide()
    
    def _update_video_input_tooltip(self):
        """Aggiorna il tooltip del campo input video in base al tipo selezionato"""
        if self.video_type == "vimeo" or self.video_type == "youtube":
            self.url_entry.setToolTip("Inserisci solo l'id del video")
            self.url_label.setToolTip("Inserisci solo l'id del video")
        elif self.video_type == "videojs":
            self.url_entry.setToolTip("Inserisci l'URL intero fino a \".mp4\"")
            self.url_label.setToolTip("Inserisci l'URL intero fino a \".mp4\"")
        elif self.video_type == "local":
            # Per local file, il campo è disabilitato quindi non serve tooltip
            self.url_entry.setToolTip("")
            self.url_label.setToolTip("")
    
    def on_video_type_change(self):
        """Gestisce il cambio del tipo di video"""
        if self.vimeo_radio.isChecked():
            self.video_type = "vimeo"
            self.url_label.setText("Vimeo Video ID:")
            self.browse_btn.hide()
            self.url_entry.setEnabled(True)
        elif self.youtube_radio.isChecked():
            self.video_type = "youtube"
            self.url_label.setText("YouTube Video ID:")
            self.browse_btn.hide()
            self.url_entry.setEnabled(True)
        elif self.remote_radio.isChecked():
            self.video_type = "videojs"
            self.url_label.setText("Remote Video URL:")
            self.browse_btn.hide()
            self.url_entry.setEnabled(True)
        elif self.local_radio.isChecked():
            self.video_type = "local"
            self.url_label.setText("Video File:")
            self.browse_btn.show()
            self.url_entry.setEnabled(False)
        
        # Save preference
        self.config.set_last_video_type(self.video_type)
        
        # Aggiorna il tooltip del campo input in base al nuovo tipo
        self._update_video_input_tooltip()
        
        # Re-validate video input
        self._validate_video_input()
    
    def browse_file(self):
        """Apre il dialog per selezionare un file video"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video files (*.mp4 *.webm *.ogg *.mov);;MP4 files (*.mp4);;WebM files (*.webm);;All files (*.*)"
        )
        if filename:
            self.local_file_path = filename
            self.url_entry.setText(os.path.basename(filename))
            self._validate_video_input()
    
    def browse_subtitle_file(self):
        """Apre il dialog per selezionare un file subtitle"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Subtitle File",
            "",
            "Subtitle files (*.srt *.vtt);;SRT files (*.srt);;VTT files (*.vtt);;All files (*.*)"
        )
        if filename:
            self.subtitle_file_path = filename
            self.subtitle_entry.setText(os.path.basename(filename))
            self.subtitle_entry.setEnabled(True)
    
    def on_generate_clicked(self):
        """Gestisce il click sul pulsante Generate"""
        # Validate form first
        if not self.generate_btn.isEnabled():
            return
        
        # La validazione e la generazione saranno gestite dal main.py
        # che connetterà i signals
        title = self.title_entry.text().strip()
        description = self.desc_text.toPlainText().strip()
        video_input = self.url_entry.text().strip()
        
        # Chiedi directory di output (use last directory if available)
        last_dir = self.config.get_last_output_dir()
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory", last_dir)
        if not output_dir:
            return
        
        # Save output directory preference
        self.config.set_last_output_dir(output_dir)
        
        # Emetti signal per richiedere la generazione
        self.generate_requested.emit(
            title, description, self.video_type, video_input,
            self.local_file_path, self.subtitle_file_path, output_dir
        )
    
    def handle_file_conflict(self, file_path, batch_mode=False, apply_to_all=None):
        """
        Gestisce il conflitto di file esistente. 
        Restituisce:
        - ('cancel', None): Utente vuole cancellare
        - ('overwrite', path): Utente vuole sovrascrivere
        - ('rename', new_path): Utente vuole rinominare
        - ('overwrite_all', path): Utente vuole sovrascrivere tutti
        - ('rename_all', new_path): Utente vuole rinominare tutti
        
        Args:
            file_path: Path del file
            batch_mode: Se True, mostra opzioni "Yes to all" e "No to all"
            apply_to_all: Se impostato, applica la stessa azione a tutti i file
        """
        from pathlib import Path
        path = Path(file_path)
        
        if not path.exists():
            if batch_mode:
                return 'overwrite', file_path, apply_to_all
            return 'overwrite', file_path
        
        # Se abbiamo un'impostazione "apply to all", usala
        if apply_to_all:
            if apply_to_all == 'overwrite':
                if batch_mode:
                    return 'overwrite', file_path, apply_to_all
                return 'overwrite', file_path
            elif apply_to_all == 'rename':
                # Genera filename numerato
                stem = path.stem
                suffix = path.suffix
                parent = path.parent
                counter = 1
                while True:
                    new_name = f"{stem} ({counter}){suffix}"
                    new_path = parent / new_name
                    if not new_path.exists():
                        if batch_mode:
                            return 'rename', str(new_path), apply_to_all
                        return 'rename', str(new_path)
                    counter += 1
        
        # File esiste, chiedi all'utente
        if batch_mode:
            # Crea dialog personalizzato per batch mode con "Yes to all" e "No to all"
            dialog = QDialog(self.batch_window)
            dialog.setWindowTitle("File Already Exists")
            dialog.setFixedSize(450, 250)
            dialog.setModal(True)
            
            layout = QVBoxLayout(dialog)
            
            msg = f"The file already exists:\n{file_path}\n\nWhat would you like to do?"
            msg_label = QLabel(msg)
            msg_label.setWordWrap(True)
            layout.addWidget(msg_label)
            
            button_frame = QWidget()
            button_layout = QHBoxLayout(button_frame)
            
            result = {'action': None, 'apply_to_all': None}
            
            overwrite_btn = QPushButton("Overwrite")
            overwrite_btn.clicked.connect(lambda: self._set_conflict_result(dialog, result, 'overwrite', None))
            button_layout.addWidget(overwrite_btn)
            
            rename_btn = QPushButton("Rename")
            rename_btn.clicked.connect(lambda: self._set_conflict_result(dialog, result, 'rename', None))
            button_layout.addWidget(rename_btn)
            
            skip_btn = QPushButton("Skip This")
            skip_btn.clicked.connect(lambda: self._set_conflict_result(dialog, result, 'skip', None))
            button_layout.addWidget(skip_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(lambda: self._set_conflict_result(dialog, result, 'cancel', None))
            button_layout.addWidget(cancel_btn)
            
            layout.addWidget(button_frame)
            
            button_frame2 = QWidget()
            button_layout2 = QHBoxLayout(button_frame2)
            
            overwrite_all_btn = QPushButton("Overwrite All")
            overwrite_all_btn.clicked.connect(lambda: self._set_conflict_result(dialog, result, 'overwrite', 'overwrite'))
            button_layout2.addWidget(overwrite_all_btn)
            
            rename_all_btn = QPushButton("Rename All")
            rename_all_btn.clicked.connect(lambda: self._set_conflict_result(dialog, result, 'rename', 'rename'))
            button_layout2.addWidget(rename_all_btn)
            
            layout.addWidget(button_frame2)
            
            dialog.exec()
            
            action = result['action']
            apply_to_all = result['apply_to_all']
            
            if action == 'cancel':
                return 'cancel', None, apply_to_all
            elif action == 'skip':
                return 'skip', None, apply_to_all
            elif action == 'overwrite':
                return 'overwrite', file_path, apply_to_all
            elif action == 'rename':
                # Aggiungi (n) prima dell'estensione
                stem = path.stem
                suffix = path.suffix
                parent = path.parent
                counter = 1
                while True:
                    new_name = f"{stem} ({counter}){suffix}"
                    new_path = parent / new_name
                    if not new_path.exists():
                        return 'rename', str(new_path), apply_to_all
                    counter += 1
        else:
            # Single mode - usa dialog standard
            reply = QMessageBox.question(
                self,
                "File Already Exists",
                f"The file already exists:\n{file_path}\n\n"
                "What would you like to do?\n\n"
                "Yes = Overwrite\n"
                "No = Add (n) to filename\n"
                "Cancel = Cancel operation",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                return 'cancel', None
            elif reply == QMessageBox.Yes:
                return 'overwrite', file_path
            else:  # No = Rename
                # Aggiungi (n) prima dell'estensione
                stem = path.stem
                suffix = path.suffix
                parent = path.parent
                counter = 1
                while True:
                    new_name = f"{stem} ({counter}){suffix}"
                    new_path = parent / new_name
                    if not new_path.exists():
                        return 'rename', str(new_path)
                    counter += 1
    
    def _set_conflict_result(self, dialog, result, action, apply_to_all):
        """Helper per impostare il risultato del dialog di conflitto"""
        result['action'] = action
        result['apply_to_all'] = apply_to_all
        dialog.accept()
    
    def toggle_batch_mode(self):
        """Passa tra modalità singola e batch"""
        if self.batch_mode:
            # Ritorna a modalità singola
            self.batch_mode = False
            self.setWindowTitle("SCORM Wrapper Wizard v0.3")
            # Chiudi finestra batch se aperta
            if hasattr(self, 'batch_window') and self.batch_window.isVisible():
                self.batch_window.close()
            # Imposta tooltip per modalità single
            self._setup_tooltips()
        else:
            # Entra in modalità batch
            self.batch_mode = True
            self.setWindowTitle("SCORM Wrapper Wizard v0.3 - Batch Mode")
            self.open_batch_window()
    
    def open_batch_window(self):
        """Apre la finestra per la modalità batch"""
        self.batch_window = QDialog(self)
        self.batch_window.setWindowTitle("Batch Mode - SCORM Generator")
        self.batch_window.setFixedSize(600, 600)
        self.batch_window.setModal(False)
        
        # Main layout
        batch_layout = QVBoxLayout(self.batch_window)
        batch_layout.setContentsMargins(20, 20, 20, 20)
        batch_layout.setSpacing(10)
        
        # Title and Help button layout
        title_layout = QHBoxLayout()
        title_label = QLabel("Batch SCORM Generator")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Help button with icon per batch mode
        self.batch_help_btn = QPushButton()
        self.batch_help_btn.setFixedSize(30, 30)
        # Use Qt standard help icon
        help_icon = self.batch_window.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        self.batch_help_btn.setIcon(help_icon)
        self.batch_help_btn.setIconSize(self.batch_help_btn.size())
        self.batch_help_btn.clicked.connect(self.show_help_modal)
        self.batch_help_btn.setToolTip("Apri la guida completa")
        title_layout.addWidget(self.batch_help_btn)
        batch_layout.addLayout(title_layout)
        
        # Instructions
        instructions = """CSV Format Columns (Headers): title, description, path_or_url, subtitle_path:
- title: Course title (will be used as ZIP filename)
- description: Course description
- path_or_url: Windows path to local file OR complete URL (Vimeo, YouTube, or remote file)
- subtitle_path: (Optional) Path to subtitle file (.srt or .vtt)

Example:
title,description,path_or_url,subtitle_path
My Course,This is a course,C:\\videos\\video.mp4,C:\\subtitles\\subtitles.srt
Vimeo Course,Another course,https://vimeo.com/123456789,
YouTube Course,Yet another,https://www.youtube.com/watch?v=abc123,C:\\subtitles\\youtube_subtitles.vtt"""
        
        instructions_label = QLabel(instructions)
        instructions_font = QFont("Arial", 9)
        instructions_label.setFont(instructions_font)
        instructions_label.setWordWrap(True)
        batch_layout.addWidget(instructions_label)
        
        # CSV file selection
        csv_layout = QHBoxLayout()
        csv_label = QLabel("CSV File:")
        csv_layout.addWidget(csv_label)
        self.csv_entry = QLineEdit()
        csv_layout.addWidget(self.csv_entry)
        csv_browse_btn = QPushButton("Browse")
        csv_browse_btn.clicked.connect(self.browse_csv)
        csv_layout.addWidget(csv_browse_btn)
        batch_layout.addLayout(csv_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Dir:")
        output_layout.addWidget(output_label)
        self.batch_output_entry = QLineEdit()
        output_layout.addWidget(self.batch_output_entry)
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(output_browse_btn)
        batch_layout.addLayout(output_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        batch_layout.addWidget(separator)
        
        # Process button (prominent, large)
        self.process_btn = QPushButton("▶ Process Batch")
        self.process_btn.clicked.connect(self.on_process_batch_clicked)
        batch_layout.addWidget(self.process_btn)
        
        # Cancel button (initially hidden)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.on_cancel_batch)
        self.cancel_btn.hide()
        batch_layout.addWidget(self.cancel_btn)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.hide()
        batch_layout.addWidget(self.progress_bar)
        
        # Status label
        self.batch_status = QLabel("Ready to process")
        status_font = QFont("Arial", 9)
        self.batch_status.setFont(status_font)
        batch_layout.addWidget(self.batch_status)
        
        batch_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close Batch Mode")
        close_btn.clicked.connect(self.toggle_batch_mode)
        batch_layout.addWidget(close_btn)
        
        self.batch_window.show()
    
    def browse_csv(self):
        """Apre il dialog per selezionare un file CSV"""
        filename, _ = QFileDialog.getOpenFileName(
            self.batch_window,
            "Select CSV File",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )
        if filename:
            self.csv_entry.setText(filename)
    
    def browse_output_dir(self):
        """Apre il dialog per selezionare una directory di output"""
        dirname = QFileDialog.getExistingDirectory(self.batch_window, "Select Output Directory")
        if dirname:
            self.batch_output_entry.setText(dirname)
    
    def on_process_batch_clicked(self):
        """Gestisce il click sul pulsante Process Batch"""
        csv_file = self.csv_entry.text().strip()
        output_dir = self.batch_output_entry.text().strip()
        
        if not csv_file:
            QMessageBox.critical(self.batch_window, "Error", "Please select a CSV file!")
            return
        
        if not os.path.exists(csv_file):
            QMessageBox.critical(self.batch_window, "Error", "CSV file does not exist!")
            return
        
        if not output_dir:
            QMessageBox.critical(self.batch_window, "Error", "Please select an output directory!")
            return
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self.batch_window, "Error", f"Cannot create output directory:\n{str(e)}")
                return
        
        # Emetti signal per richiedere il processamento batch
        self.batch_process_requested.emit(csv_file, output_dir)
    
    # Metodi per aggiornare l'UI in risposta ai signals dalla logica
    def update_progress(self, percentage: int, message: str):
        """Aggiorna la barra di progresso per modalità singola"""
        self.progress_bar_single.setValue(percentage)
        self.status_label_single.setText(message)
        if percentage == 0:
            self.progress_bar_single.show()
        if percentage == 100:
            self.progress_bar_single.hide()
            self.status_label_single.setText("")
    
    def update_batch_progress(self, current: int, total: int, message: str):
        """Aggiorna la barra di progresso per modalità batch"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        self.batch_status.setText(message)
    
    def show_success(self, message: str, window=None, output_path=None):
        """Mostra un messaggio di successo con opzione per aprire la cartella e validare"""
        target_window = window if window else self
        
        msg_box = QMessageBox(target_window)
        msg_box.setWindowTitle("Success")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        
        # Add "Open Folder" button if output path is provided
        if output_path:
            open_folder_btn = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            open_folder_btn.clicked.connect(lambda: self._open_output_folder(output_path))
            
            # Add "Validate Package" button
            validate_btn = msg_box.addButton("Validate Package", QMessageBox.ButtonRole.ActionRole)
            validate_btn.clicked.connect(lambda: self._validate_package(output_path, msg_box))
        
        msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        msg_box.exec()
    
    def _validate_package(self, zip_path: str, parent_msg_box=None):
        """Validate the generated SCORM package."""
        from scorm_validator import SCORMValidator
        
        validator = SCORMValidator()
        is_valid, errors, warnings = validator.validate_package(zip_path)
        report = validator.get_validation_report(zip_path)
        
        # Close parent message box if provided
        if parent_msg_box:
            parent_msg_box.close()
        
        # Show validation results
        validation_dialog = QDialog(self)
        validation_dialog.setWindowTitle("Package Validation")
        validation_dialog.setFixedSize(600, 400)
        
        layout = QVBoxLayout(validation_dialog)
        
        # Status label
        status_label = QLabel("✓ VALID" if is_valid else "✗ INVALID")
        status_font = QFont("Arial", 14, QFont.Bold)
        status_label.setFont(status_font)
        if is_valid:
            status_label.setStyleSheet("color: green;")
        else:
            status_label.setStyleSheet("color: red;")
        layout.addWidget(status_label)
        
        # Report text
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_text.setPlainText(report)
        layout.addWidget(report_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(validation_dialog.accept)
        layout.addWidget(close_btn)
        
        validation_dialog.exec()
    
    def _open_output_folder(self, file_path):
        """Open the folder containing the output file."""
        import subprocess
        from pathlib import Path
        
        folder_path = Path(file_path).parent
        if os.name == 'nt':  # Windows
            subprocess.Popen(f'explorer "{folder_path}"')
        elif os.name == 'posix':  # Linux/Mac
            subprocess.Popen(['xdg-open', str(folder_path)])
    
    def show_error(self, message: str, window=None):
        """Mostra un messaggio di errore"""
        target_window = window if window else self
        QMessageBox.critical(target_window, "Error", message)
    
    def set_generating_state(self, is_generating: bool):
        """Imposta lo stato del pulsante Generate"""
        self.generate_btn.setEnabled(not is_generating)
        if is_generating:
            self.generate_btn.setText("Generating...")
        else:
            self.generate_btn.setText("Generate SCORM Package")
    
    def set_batch_processing_state(self, is_processing: bool):
        """Imposta lo stato del pulsante Process Batch"""
        self.process_btn.setEnabled(not is_processing)
        if is_processing:
            self.process_btn.setText("Processing...")
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.cancel_btn.show()
        else:
            self.process_btn.setText("▶ Process Batch")
            self.progress_bar.hide()
            self.cancel_btn.hide()
    
    def on_cancel_batch(self):
        """Handle cancel button click for batch processing."""
        # This will be connected from main.py
        pass