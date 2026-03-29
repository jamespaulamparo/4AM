import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget, 
                             QListWidgetItem, QDialog, QLabel)
from PySide6.QtCore import Qt, Signal

class OmniSearch(QDialog):
    file_selected = Signal(str) 

    def __init__(self, parent=None, vault_path=""):
        super().__init__(parent)
        self.vault_path = vault_path
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setFixedSize(650, 450) # Slightly wider to fit the text snippets
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; border: 1px solid #333333; border-radius: 8px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search the Vault... (Titles and Contents)")
        self.search_bar.setStyleSheet("""
            QLineEdit { 
                background-color: #262626; color: #cccccc; padding: 12px; 
                font-size: 16px; border: 1px solid #3a3a3a; border-radius: 6px; 
                font-family: "iA Writer Quattro S";
            }
            QLineEdit:focus { border: 1px solid #5bc0de; }
        """)
        self.search_bar.textChanged.connect(self.perform_search)
        layout.addWidget(self.search_bar)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; outline: none; }
            QListWidget::item { 
                padding: 12px; border-bottom: 1px solid #222222; 
            }
            QListWidget::item:selected { 
                background-color: #333333; border-radius: 6px;
            }
        """)
        self.results_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.results_list)

    def perform_search(self, query):
        self.results_list.clear()
        if len(query) < 2: return 

        query_lower = query.lower()
        
        for root, dirs, files in os.walk(self.vault_path):
            if ".history" in dirs: dirs.remove(".history")
            if "_attachments" in dirs: dirs.remove("_attachments")

            for file in files:
                if file.endswith(('.md', '.canvas')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            content_lower = content.lower()
                            
                            if query_lower in content_lower or query_lower in file.lower():
                                # --- THE CONTEXT ENGINE ---
                                snippet = ""
                                if query_lower in content_lower:
                                    idx = content_lower.find(query_lower)
                                    # Grab 40 chars before and 60 chars after
                                    start = max(0, idx - 40)
                                    end = min(len(content), idx + len(query) + 60)
                                    
                                    raw_snippet = content[start:end].replace('\n', ' ').strip()
                                    prefix = "..." if start > 0 else ""
                                    suffix = "..." if end < len(content) else ""
                                    snippet = f"\n      <span style='color: #888888; font-size: 12px;'><i>{prefix}{raw_snippet}{suffix}</i></span>"

                                icon = "📝" if file.endswith('.md') else "🗂️"
                                title_clean = file.replace('.md', '').replace('.canvas', '')
                                
                                # Use Rich Text (HTML) inside the list item for beautiful formatting
                                display_html = f"<span style='color: #cccccc; font-family: \"iA Writer Quattro S\"; font-size: 14px; font-weight: bold;'>{icon}  {title_clean}</span>{snippet}"
                                
                                # We have to use a QLabel inside the QListWidget to render HTML snippets
                                item = QListWidgetItem(self.results_list)
                                self.results_list.addItem(item)
                                
                                label = QLabel(display_html)
                                label.setStyleSheet("background: transparent;")
                                label.setWordWrap(True)
                                
                                item.setSizeHint(label.sizeHint())
                                item.setData(Qt.UserRole, file_path) 
                                
                                self.results_list.setItemWidget(item, label)
                    except Exception:
                        pass

    def on_item_clicked(self, item):
        file_path = item.data(Qt.UserRole)
        self.file_selected.emit(file_path)
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Down:
            self.results_list.setFocus()
            if self.results_list.currentRow() < 0:
                self.results_list.setCurrentRow(0)
        elif event.key() == Qt.Key_Up and self.results_list.hasFocus() and self.results_list.currentRow() == 0:
            self.search_bar.setFocus()
        elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if self.results_list.currentItem():
                self.on_item_clicked(self.results_list.currentItem())
        else:
            super().keyPressEvent(event)