import sys
import os
import json
import requests
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QScrollArea, QLabel, QPushButton, 
                            QFrame, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from app_card import AppCard
from utils import get_installed_apps

class AppStore(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DDP App Store")
        self.setMinimumSize(1200, 800)
        
        # Initialize network manager
        self.network_manager = QNetworkAccessManager()
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create scroll area for apps
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create container for apps
        self.apps_container = QWidget()
        self.apps_layout = QGridLayout(self.apps_container)
        self.apps_layout.setSpacing(20)
        
        scroll_area.setWidget(self.apps_container)
        layout.addWidget(scroll_area)
        
        # Load apps
        self.load_apps()
        
    def load_apps(self):
        # Clear existing apps
        for i in reversed(range(self.apps_layout.count())): 
            self.apps_layout.itemAt(i).widget().setParent(None)
        
        # Get installed apps for status checking
        installed_apps = get_installed_apps()
        
        # Load apps from local directory structure
        apps_dir = Path("Apps")
        if not apps_dir.exists():
            QMessageBox.warning(self, "Error", "Apps directory not found!")
            return
        
        row = 0
        col = 0
        max_cols = 3  # Number of apps per row
        
        for app_dir in apps_dir.iterdir():
            if not app_dir.is_dir():
                continue
            
            # Check for required files and directories
            info_dir = app_dir / "Info"
            images_dir = app_dir / "Images"
            package_dir = app_dir / "Package"
            
            if not (info_dir.exists() and images_dir.exists() and package_dir.exists()):
                continue
            
            # Load app data
            app_data = {
                'name': 'Unknown App',
                'description': '',
                'logo_path': '',
                'screenshots': [],
                'package_files': [],
                'is_installed': False
            }
            
            # Load name
            name_file = info_dir / "Name.txt"
            if name_file.exists():
                with open(name_file, 'r', encoding='utf-8') as f:
                    app_data['name'] = f.read().strip()
                
            # Load description
            desc_file = info_dir / "description.txt"
            if desc_file.exists():
                with open(desc_file, 'r', encoding='utf-8') as f:
                    app_data['description'] = f.read().strip()
                
            # Load logo
            logo_file = images_dir / "logo.png"
            if logo_file.exists():
                app_data['logo_path'] = str(logo_file)
            
            # Load screenshots
            for i in range(1, 6):
                screenshot = images_dir / f"screen{i}.png"
                if screenshot.exists():
                    app_data['screenshots'].append(str(screenshot))
                
            # Load package files
            for file in package_dir.iterdir():
                if file.is_file():
                    app_data['package_files'].append(str(file))
                
            # Check if app is installed
            app_data['is_installed'] = app_data['name'] in installed_apps
            
            # Create and add app card
            app_card = AppCard(app_data)
            self.apps_layout.addWidget(app_card, row, col)
            
            # Update grid position
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
    def create_app_card(self, app_data):
        # TODO: Implement app card creation
        pass
        
    def download_app(self, app_data):
        # TODO: Implement app download functionality
        pass
        
    def install_app(self, app_data):
        # TODO: Implement app installation
        pass
        
    def create_shortcut(self, app_data):
        # TODO: Implement shortcut creation
        pass
        
    def uninstall_app(self, app_data):
        # TODO: Implement app uninstallation
        pass

def main():
    app = QApplication(sys.argv)
    window = AppStore()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
