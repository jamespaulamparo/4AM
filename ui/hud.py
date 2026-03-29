import os
import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, Slot

# Point to your new portraits folder
PORTRAITS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'portraits')

class PortraitSlot(QFrame):
    """A single slot for a character portrait."""
    def __init__(self, character_name):
        super().__init__()
        self.character_name = character_name
        self.setFixedSize(160, 220) 
        
        self.set_inactive_style()
        
        layout = QVBoxLayout(self)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        
        img_path = os.path.join(PORTRAITS_DIR, f"{character_name.lower()}.png")
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(140, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText(f"[ NO SIGNAL ]\n\n{character_name.upper()}")
            font = self.image_label.font()
            font.setFamily("iA Writer Quattro S")
            self.image_label.setFont(font)
            
        layout.addWidget(self.image_label)
        
    def set_active_style(self):
        self.setStyleSheet("""
            PortraitSlot { 
                border: 2px solid #5bc0de; 
                background-color: #2a2a2a; 
                border-radius: 8px; 
            }
            QLabel { color: #5bc0de; font-weight: bold; }
        """)
        
    def set_inactive_style(self):
        self.setStyleSheet("""
            PortraitSlot { 
                border: 2px solid #333333; 
                background-color: transparent; 
                border-radius: 8px; 
            }
            QLabel { color: #555555; }
        """)

class ReactiveHUD(QWidget):
    """The side-panel that manages the crew slots with Frameless Dragging."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(180, 200)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter) 
        self.main_layout.setSpacing(15)
        
        self.header = QLabel("CREW STATUS")
        self.header.setStyleSheet("color: #666666; font-weight: bold; letter-spacing: 2px;")
        self.header.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.header)
        
        self.slots = {
            "june": PortraitSlot("June"),
            "emilio": PortraitSlot("Emilio"),
            "brook": PortraitSlot("Brook")
        }
        
        for slot in self.slots.values():
            self.main_layout.addWidget(slot)
            
        self.is_horizontal = False 
        
        # Physics Tracker for dragging
        self._is_dragging = False
        self._drag_offset = None

    def resizeEvent(self, event):
        """The Shape-Shifter Engine: Flips between vertical and horizontal."""
        super().resizeEvent(event)
        
        width = self.width()
        height = self.height()
        
        should_be_horizontal = width > height
        
        if should_be_horizontal and not self.is_horizontal:
            self.is_horizontal = True
            self.main_layout.setDirection(QVBoxLayout.LeftToRight)
            self.header.hide() 
        elif not should_be_horizontal and self.is_horizontal:
            self.is_horizontal = False
            self.main_layout.setDirection(QVBoxLayout.TopToBottom)
            self.header.show() 

    @Slot(str)
    def process_text(self, text):
        text_lower = text.lower()
        for name, slot in self.slots.items():
            if re.search(rf'\b{name}\b', text_lower):
                slot.set_active_style()
            else:
                slot.set_inactive_style()

    # --- CUSTOM FRAMELESS DRAG PHYSICS ---
    def _get_dock_parent(self):
        """Helper to find the floating wrapper."""
        parent = self.parentWidget()
        while parent:
            if parent.metaObject().className() == "QDockWidget":
                return parent
            parent = parent.parentWidget()
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            dock = self._get_dock_parent()
            # ONLY let them drag it if it's currently floating off the wall!
            if dock and dock.isFloating():
                self._is_dragging = True
                self._drag_offset = event.globalPosition().toPoint() - dock.pos()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            dock = self._get_dock_parent()
            if dock and dock.isFloating():
                dock.move(event.globalPosition().toPoint() - self._drag_offset)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
        super().mouseReleaseEvent(event)