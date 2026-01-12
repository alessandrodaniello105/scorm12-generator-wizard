"""
Entry point principale per il SCORM Generator.
Collega la GUI alla logica tramite Signals di PySide6.
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal
from qt_material import apply_stylesheet

from gui_main import SCORMWizard
from logic import SCORMLogic
import subprocess
from pathlib import Path


class GenerationWorker(QThread):
    """
    Worker thread per la generazione SCORM in background.
    Permette di non bloccare l'UI durante la generazione.
    """
    progress_updated = Signal(int, str)
    package_generated = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, logic, title, description, video_type, video_url, 
                 local_file, output_dir, output_filename=None, subtitle_file=None):
        super().__init__()
        self.logic = logic
        self.title = title
        self.description = description
        self.video_type = video_type
        self.video_url = video_url
        self.local_file = local_file
        self.subtitle_file = subtitle_file
        self.output_dir = output_dir
        self.output_filename = output_filename
    
    def run(self):
        """Esegue la generazione in background"""
        try:
            # Connetti i signals della logica ai signals del worker
            self.logic.progress_updated.connect(self.progress_updated.emit)
            
            output_path = self.logic.generate_scorm_package(
                title=self.title,
                description=self.description,
                video_type=self.video_type,
                video_url=self.video_url,
                local_video_file=self.local_file,
                subtitle_file=self.subtitle_file,
                output_dir=self.output_dir,
                output_filename=self.output_filename
            )
            
            self.package_generated.emit(output_path)
        except Exception as e:
            self.error_occurred.emit(str(e))


class BatchWorker(QThread):
    """
    Worker thread per il processamento batch in background.
    """
    progress_updated = Signal(int, int, str)
    batch_complete = Signal(int, list)
    error_occurred = Signal(str)
    conflict_detected = Signal(str, object)  # file_path, apply_to_all
    
    def __init__(self, logic, csv_file, output_dir):
        super().__init__()
        self.logic = logic
        self.csv_file = csv_file
        self.output_dir = output_dir
        self.conflict_result = None
        self.conflict_waiting = False
        self._cancelled = False
        self.start_time = None
    
    def cancel(self):
        """Cancel the batch processing."""
        self._cancelled = True
    
    def run(self):
        """Esegue il processamento batch in background"""
        try:
            import time
            self.start_time = time.time()
            
            # Connetti i signals della logica ai signals del worker
            self.logic.batch_progress_updated.connect(self.progress_updated.emit)
            
            # Crea conflict handler che emette un signal
            def conflict_handler(file_path, apply_to_all):
                if self._cancelled:
                    return 'cancel', None, None
                    
                self.conflict_waiting = True
                self.conflict_result = None
                self.conflict_detected.emit(file_path, apply_to_all)
                
                # Attendi la risposta (con timeout)
                timeout_ms = 300000  # 5 minuti in millisecondi
                elapsed = 0
                while self.conflict_waiting and elapsed < timeout_ms and not self._cancelled:
                    self.msleep(100)  # 100ms
                    elapsed += 100
                
                if self._cancelled or self.conflict_result is None:
                    return 'cancel', None, None
                
                result = self.conflict_result
                self.conflict_result = None
                return result
            
            processed, errors = self.logic.process_batch_csv(
                csv_file=self.csv_file,
                output_dir=self.output_dir,
                conflict_handler=conflict_handler
            )
            
            if not self._cancelled:
                self.batch_complete.emit(processed, errors)
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(str(e))
    
    def set_conflict_result(self, result):
        """Imposta il risultato del conflitto e sveglia il thread"""
        self.conflict_result = result
        self.conflict_waiting = False


class SCORMApplication:
    """
    Classe principale che collega la GUI alla logica.
    Gestisce tutti i signals e la comunicazione tra i componenti.
    """
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        # Crea istanze di GUI e logica
        self.gui = SCORMWizard()
        self.logic = SCORMLogic()
        
        # Worker threads
        self.generation_worker = None
        self.batch_worker = None
        
        # Connetti signals
        self._connect_signals()
        
        # Applica tema
        apply_stylesheet(self.app, theme='light_blue.xml')
    
    def _connect_signals(self):
        """Collega tutti i signals tra GUI e logica"""
        # Signals da GUI a logica (tramite handler)
        self.gui.generate_requested.connect(self._handle_generate_request)
        self.gui.batch_process_requested.connect(self._handle_batch_request)
        
        # Signals dalla logica alla GUI
        self.logic.progress_updated.connect(self.gui.update_progress)
        self.logic.batch_progress_updated.connect(self.gui.update_batch_progress)
        self.logic.error_occurred.connect(self.gui.show_error)
    
    def _handle_generate_request(self, title, description, video_type, 
                                 video_input, local_file_path, subtitle_file_path, output_dir):
        """
        Gestisce la richiesta di generazione dalla GUI.
        Valida gli input e avvia la generazione.
        """
        # Valida input usando la logica
        is_valid, error_msg = self.logic.validate_single_inputs(
            title=title,
            video_input=video_input,
            video_type=video_type,
            local_file_path=local_file_path
        )
        
        if not is_valid:
            self.gui.show_error(error_msg)
            return
        
        # Estrai video URL/ID
        if video_type == "local":
            video_url = os.path.basename(local_file_path) if local_file_path else video_input
            local_file = local_file_path
        else:
            video_url = self.logic.extract_video_id(video_input, video_type)
            local_file = None
        
        # Controlla conflitto file
        from pathlib import Path
        output_file = self.logic.get_output_filename(title, output_dir)
        
        if Path(output_file).exists():
            action, final_path = self.gui.handle_file_conflict(output_file, batch_mode=False)
            
            if action == 'cancel':
                return
            
            if action == 'rename':
                output_filename = final_path
            else:  # overwrite
                output_filename = output_file
        else:
            output_filename = output_file
        
        # Prepara per la generazione
        self.gui.set_generating_state(True)
        self.gui.update_progress(0, "Preparing package...")
        
        # Crea e avvia worker thread
        self.generation_worker = GenerationWorker(
            logic=self.logic,
            title=title,
            description=description,
            video_type=video_type,
            video_url=video_url,
            local_file=local_file,
            subtitle_file=subtitle_file_path if subtitle_file_path else None,
            output_dir=output_dir,
            output_filename=output_filename
        )
        
        # Connetti signals del worker
        self.generation_worker.progress_updated.connect(self.gui.update_progress)
        self.generation_worker.package_generated.connect(self._on_package_generated)
        self.generation_worker.error_occurred.connect(self._on_generation_error)
        
        # Avvia generazione
        self.generation_worker.start()
    
    def _handle_batch_request(self, csv_file, output_dir):
        """
        Gestisce la richiesta di processamento batch dalla GUI.
        """
        # Prepara per il processamento
        self.gui.set_batch_processing_state(True)
        self.gui.update_batch_progress(0, 0, "Loading CSV file...")
        
        # Crea e avvia worker thread
        self.batch_worker = BatchWorker(
            logic=self.logic,
            csv_file=csv_file,
            output_dir=output_dir
        )
        
        # Connetti signals del worker
        self.batch_worker.progress_updated.connect(self.gui.update_batch_progress)
        self.batch_worker.batch_complete.connect(self._on_batch_complete)
        self.batch_worker.error_occurred.connect(self._on_batch_error)
        self.batch_worker.conflict_detected.connect(self._handle_batch_conflict)
        
        # Connect cancel button
        self.gui.on_cancel_batch = lambda: self.batch_worker.cancel()
        
        # Avvia processamento
        self.batch_worker.start()
    
    def _handle_batch_conflict(self, file_path, apply_to_all):
        """Gestisce un conflitto di file durante il batch processing"""
        # Chiama la GUI per mostrare il dialog (nel thread principale)
        result = self.gui.handle_file_conflict(file_path, batch_mode=True, apply_to_all=apply_to_all)
        
        # Restituisci il risultato al worker thread
        self.batch_worker.set_conflict_result(result)
    
    def _on_package_generated(self, output_path):
        """Gestisce il completamento della generazione"""
        self.gui.set_generating_state(False)
        
        # Get file size for display
        from pathlib import Path
        file_size = Path(output_path).stat().st_size
        size_mb = file_size / (1024 * 1024)
        size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{file_size / 1024:.2f} KB"
        
        self.gui.show_success(
            f"SCORM package generated successfully!\n\nSaved to:\n{output_path}\n\nSize: {size_str}",
            output_path=output_path
        )
        
        # Auto-open folder if configured
        if self.gui.config.get_auto_open_folder():
            self.gui._open_output_folder(output_path)
    
    def _on_generation_error(self, error_msg):
        """Gestisce errori durante la generazione con messaggi migliorati"""
        self.gui.set_generating_state(False)
        
        # Enhanced error message with suggestions
        enhanced_msg = self._enhance_error_message(error_msg, "generation")
        self.gui.show_error(enhanced_msg)
        import traceback
        traceback.print_exc()
    
    def _enhance_error_message(self, error_msg: str, context: str) -> str:
        """Enhance error message with actionable suggestions."""
        enhanced = f"Failed to {context}:\n\n{error_msg}\n\n"
        
        # Add suggestions based on error type
        if "template" in error_msg.lower() or "not found" in error_msg.lower():
            enhanced += "What went wrong?\n"
            enhanced += "• Required template files are missing\n\n"
            enhanced += "How to fix it?\n"
            enhanced += "• Ensure 'working_scorm_zip_example' folder exists\n"
            enhanced += "• Reinstall the application if the problem persists"
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            enhanced += "What went wrong?\n"
            enhanced += "• Cannot write to the output directory\n\n"
            enhanced += "How to fix it?\n"
            enhanced += "• Choose a different output directory\n"
            enhanced += "• Check folder permissions\n"
            enhanced += "• Close any programs using the output folder"
        elif "video" in error_msg.lower() or "file" in error_msg.lower():
            enhanced += "What went wrong?\n"
            enhanced += "• Video file or URL is invalid\n\n"
            enhanced += "How to fix it?\n"
            enhanced += "• Verify the video file exists (for local files)\n"
            enhanced += "• Check the video URL is accessible (for remote URLs)\n"
            enhanced += "• Ensure video ID is correct (for Vimeo/YouTube)"
        else:
            enhanced += "What went wrong?\n"
            enhanced += "• An unexpected error occurred\n\n"
            enhanced += "How to fix it?\n"
            enhanced += "• Check all input fields are valid\n"
            enhanced += "• Try again with different inputs\n"
            enhanced += "• Contact support if the problem persists"
        
        return enhanced
    
    def _on_batch_complete(self, processed, errors):
        """Gestisce il completamento del processamento batch"""
        # Completa la progress bar al 100%
        self.gui.update_batch_progress(100, 100, "Complete!")
        
        self.gui.set_batch_processing_state(False)
        
        result_msg = f"Batch processing complete!\n\nProcessed: {processed} packages"
        if errors:
            result_msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                result_msg += f"\n... and {len(errors) - 10} more errors"
        
        # Mostra il messaggio nella finestra batch
        batch_window = getattr(self.gui, 'batch_window', None)
        self.gui.show_success(result_msg, window=batch_window)
        self.gui.batch_status.setText(f"✓ Complete! Processed {processed} packages successfully.")
    
    def _on_batch_error(self, error_msg):
        """Gestisce errori durante il processamento batch"""
        self.gui.set_batch_processing_state(False)
        batch_window = getattr(self.gui, 'batch_window', None)
        enhanced_msg = self._enhance_error_message(error_msg, "process batch")
        self.gui.show_error(enhanced_msg, window=batch_window)
        import traceback
        traceback.print_exc()
    
    def run(self):
        """Avvia l'applicazione"""
        self.gui.show()
        return self.app.exec()


if __name__ == "__main__":
    import os
    app = SCORMApplication()
    sys.exit(app.run())
