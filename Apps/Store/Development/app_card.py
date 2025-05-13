from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtGui import QPixmap, QIcon, QCursor
import requests
from io import BytesIO
import os
import tempfile
import subprocess
from pathlib import Path

class ImageLoader(QThread):
    image_loaded = pyqtSignal(QPixmap)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            response = requests.get(self.url)
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                pixmap = QPixmap()
                pixmap.loadFromData(image_data.getvalue())
                self.image_loaded.emit(pixmap)
        except Exception as e:
            print(f"Error loading image: {str(e)}")

class FileDownloader(QThread):
    download_complete = pyqtSignal(str)
    download_error = pyqtSignal(str)
    download_progress = pyqtSignal(int, int)
    
    def __init__(self, url, destination):
        super().__init__()
        self.url = url
        self.destination = destination
        
    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            
            with open(self.destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        self.download_progress.emit(bytes_downloaded, total_size)
                        
            self.download_complete.emit(self.destination)
        except Exception as e:
            self.download_error.emit(str(e))

class AppCard(QFrame):
    app_clicked = pyqtSignal(dict)
    
    def __init__(self, app_data, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.image_loaders = []
        self.download_threads = []
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setFixedSize(250, 300)
        self.setStyleSheet("""
            AppCard {
                background-color: #f0f0f0;
                border-radius: 10px;
            }
            AppCard:hover {
                background-color: #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # App logo
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(180, 180)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("background-color: transparent;")
        if self.app_data.get('logo_path'):
            self.load_image(self.app_data['logo_path'], self.logo_label, QSize(180, 180))
        layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # App name
        name_label = QLabel(self.app_data.get('name', 'Unknown App'))
        name_label.setStyleSheet('font-size: 16px; font-weight: bold; background-color: transparent;')
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Short description (first 50 chars)
        desc = self.app_data.get('description', '')
        short_desc = desc[:50] + '...' if len(desc) > 50 else desc
        desc_label = QLabel(short_desc)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet('color: #555; background-color: transparent;')
        layout.addWidget(desc_label)
        
    def load_image(self, url, label, size):
        loader = ImageLoader(url)
        self.image_loaders.append(loader)  # Keep a reference
        loader.image_loaded.connect(lambda pixmap: label.setPixmap(
            pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, 
                          Qt.TransformationMode.SmoothTransformation)))
        loader.start()
        
    def mousePressEvent(self, event):
        self.app_clicked.emit(self.app_data)
        super().mousePressEvent(event)
        
    def on_install_clicked(self):
        if not self.app_data.get('package_files'):
            QMessageBox.warning(self, "Error", "No installable files available.")
            return
            
        folder_name = self.app_data.get('folder_name', 'unknown_app')
        
        # Create app directory in user's AppData
        app_dir = Path(os.path.expandvars('%LOCALAPPDATA%')) / 'DDPApps' / folder_name
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # Download the first package file
        package_file = self.app_data['package_files'][0]
        file_name = package_file['name']
        download_url = package_file['download_url']
        
        destination = app_dir / file_name
        
        msg = QMessageBox()
        msg.setWindowTitle("Download")
        msg.setText(f"Downloading {file_name}...")
        msg.setStandardButtons(QMessageBox.StandardButton.Cancel)
        
        downloader = FileDownloader(download_url, str(destination))
        self.download_threads.append(downloader)
        
        downloader.download_complete.connect(
            lambda path: self.on_download_complete(path, msg))
        downloader.download_error.connect(
            lambda error: self.on_download_error(error, msg))
        
        downloader.start()
        msg.exec()
        
    def on_download_complete(self, path, msg_box):
        msg_box.accept()
        
        # Ask to create shortcut
        reply = QMessageBox.question(
            self, "Installation Complete",
            f"Would you like to create a desktop shortcut?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.create_shortcut(path)
            
        QMessageBox.information(
            self, "Success", 
            f"App installed successfully at {path}"
        )
        
    def on_download_error(self, error, msg_box):
        msg_box.accept()
        QMessageBox.critical(self, "Download Error", f"Error downloading file: {error}")
        
    def create_shortcut(self, target_path):
        try:
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            shortcut_path = os.path.join(desktop, f"{self.app_data.get('name', 'App')}.lnk")
            
            # Create shortcut using PowerShell
            ps_command = f'''
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{target_path}"
            $Shortcut.Save()
            '''
            
            subprocess.run(['powershell', '-Command', ps_command], capture_output=True)
            
        except Exception as e:
            QMessageBox.warning(self, "Shortcut Error", f"Failed to create shortcut: {str(e)}")
        
    def on_uninstall_clicked(self):
        folder_name = self.app_data.get('folder_name', 'unknown_app')
        app_dir = Path(os.path.expandvars('%LOCALAPPDATA%')) / 'DDPApps' / folder_name
        
        # Check if the app is installed
        if not app_dir.exists():
            QMessageBox.warning(self, "Error", "App is not installed.")
            return
            
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Uninstall",
            f"Are you sure you want to uninstall {self.app_data.get('name', 'this app')}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Remove the app directory
                import shutil
                shutil.rmtree(app_dir)
                
                # Remove desktop shortcut
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                shortcut_path = os.path.join(desktop, f"{self.app_data.get('name', 'App')}.lnk")
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    
                QMessageBox.information(
                    self, "Success", 
                    f"App uninstalled successfully."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", 
                    f"Failed to uninstall app: {str(e)}"
                )
