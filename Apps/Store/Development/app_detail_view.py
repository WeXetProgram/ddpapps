from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QScrollArea, QSizePolicy, QFrame,
                           QMessageBox, QTabWidget, QGridLayout)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QFont
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

class ScreenshotGallery(QWidget):
    def __init__(self, screenshots, parent=None):
        super().__init__(parent)
        self.screenshots = screenshots
        self.image_loaders = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if not self.screenshots:
            no_screenshots = QLabel("No screenshots available")
            no_screenshots.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_screenshots)
            return
            
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        screenshots_widget = QWidget()
        screenshots_layout = QHBoxLayout(screenshots_widget)
        screenshots_layout.setSpacing(10)
        
        for screenshot_url in self.screenshots:
            screenshot_frame = QFrame()
            screenshot_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
            screenshot_frame.setFixedSize(400, 300)
            
            screenshot_layout = QVBoxLayout(screenshot_frame)
            screenshot_layout.setContentsMargins(0, 0, 0, 0)
            
            screenshot_label = QLabel()
            screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            screenshot_label.setScaledContents(False)
            
            self.load_image(screenshot_url, screenshot_label, QSize(380, 280))
            
            screenshot_layout.addWidget(screenshot_label)
            screenshots_layout.addWidget(screenshot_frame)
            
        screenshots_layout.addStretch()
        scroll_area.setWidget(screenshots_widget)
        layout.addWidget(scroll_area)
        
    def load_image(self, url, label, size):
        loader = ImageLoader(url)
        self.image_loaders.append(loader)  # Keep a reference
        loader.image_loaded.connect(lambda pixmap: label.setPixmap(
            pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, 
                          Qt.TransformationMode.SmoothTransformation)))
        loader.start()

class AppDetailView(QWidget):
    def __init__(self, app_data, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.image_loaders = []
        self.download_threads = []
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header section
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        
        # App logo
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(120, 120)
        if self.app_data.get('logo_path'):
            self.load_image(self.app_data['logo_path'], self.logo_label, QSize(120, 120))
        header_layout.addWidget(self.logo_label)
        
        # App title and info
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = QLabel(self.app_data.get('name', 'Unknown App'))
        name_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_layout.addWidget(name_label)
        
        if self.app_data.get('extra') and 'Version' in self.app_data['extra']:
            version_label = QLabel(f"Version: {self.app_data['extra']['Version']}")
            version_label.setFont(QFont("Arial", 12))
            title_layout.addWidget(version_label)
            
        header_layout.addWidget(title_widget, 1)
        
        # Buttons
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        if self.app_data.get('package_files'):
            install_btn = QPushButton('Install')
            install_btn.setFixedSize(120, 40)
            install_btn.setFont(QFont("Arial", 12))
            install_btn.clicked.connect(self.on_install_clicked)
            button_layout.addWidget(install_btn)
            
            uninstall_btn = QPushButton('Uninstall')
            uninstall_btn.setFixedSize(120, 40)
            uninstall_btn.setFont(QFont("Arial", 12))
            uninstall_btn.clicked.connect(self.on_uninstall_clicked)
            button_layout.addWidget(uninstall_btn)
        else:
            install_btn = QPushButton('Unavailable')
            install_btn.setFixedSize(120, 40)
            install_btn.setFont(QFont("Arial", 12))
            install_btn.setEnabled(False)
            button_layout.addWidget(install_btn)
            
        header_layout.addWidget(button_widget)
        main_layout.addWidget(header_widget)
        
        # Add a separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)
        
        # Tab widget for different sections
        tab_widget = QTabWidget()
        
        # Overview tab
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        
        # Screenshots section
        screenshots_label = QLabel("Screenshots")
        screenshots_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        overview_layout.addWidget(screenshots_label)
        
        screenshots_gallery = ScreenshotGallery(self.app_data.get('screenshots', []))
        overview_layout.addWidget(screenshots_gallery)
        
        # Description section
        description_label = QLabel("Description")
        description_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        overview_layout.addWidget(description_label)
        
        desc = self.app_data.get('description', 'No description available.')
        description_text = QLabel(desc)
        description_text.setWordWrap(True)
        description_text.setTextFormat(Qt.TextFormat.RichText)
        overview_layout.addWidget(description_text)
        
        # Add some stretch at the end
        overview_layout.addStretch()
        
        # Details tab
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        if self.app_data.get('extra'):
            details_grid = QGridLayout()
            row = 0
            
            for key, value in self.app_data['extra'].items():
                key_label = QLabel(f"{key}:")
                key_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                
                value_label = QLabel(value)
                value_label.setFont(QFont("Arial", 12))
                
                details_grid.addWidget(key_label, row, 0)
                details_grid.addWidget(value_label, row, 1)
                row += 1
                
            details_layout.addLayout(details_grid)
        else:
            no_details = QLabel("No additional details available.")
            details_layout.addWidget(no_details)
            
        details_layout.addStretch()
        
        # Add tabs
        tab_widget.addTab(overview_widget, "Overview")
        tab_widget.addTab(details_widget, "Details")
        
        main_layout.addWidget(tab_widget)
        
    def load_image(self, url, label, size):
        loader = ImageLoader(url)
        self.image_loaders.append(loader)  # Keep a reference
        loader.image_loaded.connect(lambda pixmap: label.setPixmap(
            pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, 
                          Qt.TransformationMode.SmoothTransformation)))
        loader.start()
        
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
