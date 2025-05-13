import sys
import os
import json
import requests
import shutil
import base64
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QScrollArea, QLabel, QPushButton, 
                            QFrame, QGridLayout, QMessageBox, QProgressBar,
                            QStackedWidget)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices, QFont
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from app_card import AppCard
from app_detail_view import AppDetailView
from utils import get_installed_apps

class GitHubFetcher(QThread):
    app_data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    finished_loading = pyqtSignal()
    
    def __init__(self, repo_url):
        super().__init__()
        self.repo_url = repo_url
        self.api_url = "https://api.github.com/repos/WeXetProgram/ddpapps/contents/Apps"
        self.is_running = True
        
    def run(self):
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                apps = response.json()
                for app in apps:
                    if not self.is_running:
                        return
                    if app['type'] == 'dir':
                        self.fetch_app_data(app['path'])
            else:
                self.error_occurred.emit(f"Failed to fetch apps: {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"Error fetching apps: {str(e)}")
        finally:
            self.finished_loading.emit()
            
    def fetch_app_data(self, app_path):
        if not self.is_running:
            return
            
        try:
            app_data = {
                'name': 'Unknown App',
                'description': '',
                'logo_path': '',
                'screenshots': [],
                'package_files': [],
                'is_installed': False,
                'app_path': app_path
            }
            
            # Get app name from path
            app_folder_name = app_path.split('/')[-1]
            app_data['folder_name'] = app_folder_name
            
            # Fetch Info directory contents
            info_path = f"{app_path}/Info"
            info_response = requests.get(f"https://api.github.com/repos/WeXetProgram/ddpapps/contents/{info_path}")
            if info_response.status_code == 200:
                info_files = info_response.json()
                for file in info_files:
                    if file['name'].lower() == 'name.txt':
                        content = requests.get(file['download_url']).text
                        app_data['name'] = content.strip()
                    elif file['name'].lower() == 'description.txt':
                        content = requests.get(file['download_url']).text
                        app_data['description'] = content.strip()
                    elif file['name'].lower() == 'extra.txt':
                        content = requests.get(file['download_url']).text
                        app_data['extra'] = self.parse_extra_file(content)
            
            # Fetch Images directory contents
            images_path = f"{app_path}/Images"
            images_response = requests.get(f"https://api.github.com/repos/WeXetProgram/ddpapps/contents/{images_path}")
            if images_response.status_code == 200:
                image_files = images_response.json()
                for file in image_files:
                    if file['name'].lower() == 'logo.png':
                        app_data['logo_path'] = file['download_url']
                    elif file['name'].lower() == 'banner.png':
                        app_data['banner_path'] = file['download_url']
                    elif file['name'].lower().startswith('screen') and file['name'].lower().endswith('.png'):
                        app_data['screenshots'].append(file['download_url'])
            
            # Fetch Package directory contents
            package_path = f"{app_path}/Package"
            package_response = requests.get(f"https://api.github.com/repos/WeXetProgram/ddpapps/contents/{package_path}")
            if package_response.status_code == 200:
                package_files = package_response.json()
                for file in package_files:
                    app_data['package_files'].append({
                        'name': file['name'],
                        'download_url': file['download_url'],
                        'size': file['size']
                    })
            
            self.app_data_ready.emit(app_data)
            
        except Exception as e:
            print(f"Error fetching app data for {app_path}: {str(e)}")
    
    def parse_extra_file(self, content):
        result = {}
        for line in content.splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
            else:  # For lines without a colon
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0]
                    value = ' '.join(parts[1:])
                    result[key] = value
        return result
    
    def stop(self):
        self.is_running = False

class AppGridView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("DDP App Store")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Create loading indicator
        self.loading_indicator = QProgressBar()
        self.loading_indicator.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.loading_indicator)
        
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

class AppStore(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DDP App Store")
        self.setMinimumSize(1200, 800)
        
        # Create stacked widget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create grid view
        self.grid_view = AppGridView()
        self.stacked_widget.addWidget(self.grid_view)
        
        # Initialize network manager
        self.network_manager = QNetworkAccessManager()
        
        # Initialize GitHub fetcher
        self.github_fetcher = GitHubFetcher("https://github.com/WeXetProgram/ddpapps/")
        self.github_fetcher.app_data_ready.connect(self.add_app_card)
        self.github_fetcher.error_occurred.connect(self.show_error)
        self.github_fetcher.finished_loading.connect(self.on_loading_finished)
        
        # Initialize row and column counters
        self.current_row = 0
        self.current_col = 0
        self.max_cols = 4  # Show 4 apps per row for a more grid-like appearance
        
        # Initialize back button for detail view
        self.back_button = QPushButton("Back to Apps")
        self.back_button.setFixedSize(120, 40)
        self.back_button.clicked.connect(self.show_grid_view)
        
        # Load apps
        self.load_apps()
        
    def load_apps(self):
        # Clear existing apps
        for i in reversed(range(self.grid_view.apps_layout.count())): 
            widget = self.grid_view.apps_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Reset row and column
        self.current_row = 0
        self.current_col = 0
        
        # Show loading indicator
        self.grid_view.loading_indicator.show()
        
        # Start fetching apps from GitHub
        self.github_fetcher.start()
        
    def add_app_card(self, app_data):
        # Create app card
        app_card = AppCard(app_data)
        app_card.app_clicked.connect(lambda data: self.show_app_details(data))
        
        # Add to grid layout
        self.grid_view.apps_layout.addWidget(app_card, self.current_row, self.current_col)
        
        # Update grid position
        self.current_col += 1
        if self.current_col >= self.max_cols:
            self.current_col = 0
            self.current_row += 1
        
    def on_loading_finished(self):
        # Hide loading indicator
        self.grid_view.loading_indicator.hide()
        
        # If no apps were found, show a message
        if self.grid_view.apps_layout.count() == 0:
            empty_label = QLabel("No apps found")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_view.apps_layout.addWidget(empty_label, 0, 0)
        
    def show_error(self, error_message):
        QMessageBox.warning(self, "Error", error_message)
        
    def show_app_details(self, app_data):
        # Create detail view
        detail_view = AppDetailView(app_data)
        
        # Create container with back button
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Add back button
        layout.addWidget(self.back_button)
        
        # Add detail view
        layout.addWidget(detail_view)
        
        # Add to stacked widget and show
        self.stacked_widget.addWidget(container)
        self.stacked_widget.setCurrentWidget(container)
        
    def show_grid_view(self):
        # Show grid view and remove any detail views
        self.stacked_widget.setCurrentWidget(self.grid_view)
        
        # Remove all widgets except the grid view
        while self.stacked_widget.count() > 1:
            widget = self.stacked_widget.widget(self.stacked_widget.count() - 1)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()
        
    def closeEvent(self, event):
        # Stop the thread before closing
        if self.github_fetcher.isRunning():
            self.github_fetcher.stop()
            self.github_fetcher.wait(1000)  # Wait up to 1 second
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = AppStore()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
