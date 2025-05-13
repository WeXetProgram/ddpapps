from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

class AppCard(QFrame):
    def __init__(self, app_data, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setMinimumSize(300, 400)
        
        layout = QVBoxLayout(self)
        
        # App logo
        logo_label = QLabel()
        logo_pixmap = QPixmap(self.app_data.get('logo_path', ''))
        logo_label.setPixmap(logo_pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # App name
        name_label = QLabel(self.app_data.get('name', 'Unknown App'))
        name_label.setStyleSheet('font-size: 16px; font-weight: bold;')
        layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Description
        desc_label = QLabel(self.app_data.get('description', ''))
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        install_btn = QPushButton('Install')
        install_btn.clicked.connect(self.on_install_clicked)
        button_layout.addWidget(install_btn)
        
        if self.app_data.get('is_installed', False):
            uninstall_btn = QPushButton('Uninstall')
            uninstall_btn.clicked.connect(self.on_uninstall_clicked)
            button_layout.addWidget(uninstall_btn)
            
        layout.addLayout(button_layout)
        
    def on_install_clicked(self):
        # TODO: Implement install functionality
        pass
        
    def on_uninstall_clicked(self):
        # TODO: Implement uninstall functionality
        pass
