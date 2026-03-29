import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeView, 
                             QPushButton, QFileDialog, QFileSystemModel, QInputDialog, 
                             QAbstractItemView, QMenu, QMessageBox, QApplication)
from PySide6.QtCore import Qt, Signal, QFileInfo, QSortFilterProxyModel
from PySide6.QtGui import QAction

class GhostProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        file_info = model.fileInfo(index)
        
        if file_info.fileName() in [".history", "_attachments"]:
            return False
            
        return super().filterAcceptsRow(source_row, source_parent)

    def data(self, proxy_index, role=Qt.DisplayRole):
        if role == Qt.DecorationRole:
            return None 

        if role == Qt.DisplayRole:
            source_index = self.mapToSource(proxy_index)
            model = self.sourceModel()
            file_info = model.fileInfo(source_index)
            
            if file_info.isDir():
                folder_name = file_info.fileName()
                ghost_path = os.path.join(file_info.absoluteFilePath(), f"{folder_name}.md")
                if os.path.exists(ghost_path):
                    return f"{folder_name}.md"
        return super().data(proxy_index, role)

class VaultTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dragMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        index = self.indexAt(event.pos())
        proxy_model = self.model()
        source_model = proxy_model.sourceModel()
        
        if not index.isValid(): return super().dropEvent(event)
        
        source_index = proxy_model.mapToSource(index)
        target_path = source_model.filePath(source_index)
        
        urls = event.mimeData().urls()
        if not urls: return super().dropEvent(event)
            
        source_path = urls[0].toLocalFile()
        if not source_path or source_path == target_path: return super().dropEvent(event)
            
        if os.path.isfile(target_path) and target_path.endswith('.md'):
            target_dir = os.path.dirname(target_path)
            target_filename = os.path.basename(target_path)
            target_basename = target_filename.replace('.md', '')
            
            new_folder_path = os.path.join(target_dir, target_basename)
            if not os.path.exists(new_folder_path): os.makedirs(new_folder_path)
            
            new_target_path = os.path.join(new_folder_path, target_filename)
            os.rename(target_path, new_target_path)
            
            source_filename = os.path.basename(source_path)
            new_source_path = os.path.join(new_folder_path, source_filename)
            os.rename(source_path, new_source_path)
            
            event.accept()
            return
        super().dropEvent(event)

class VaultSidebar(QWidget):
    file_selected = Signal(str, bool) 

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        
        # Allows you to drag and resize the sidebar to be thinner
        self.setMinimumWidth(150) 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)
        
        self.btn_open_vault = QPushButton("VAULT")
        self.btn_open_vault.setStyleSheet("background-color: #333; color: #ccc; border: none; padding: 8px; border-radius: 4px; font-weight: bold; letter-spacing: 1px;")
        self.btn_open_vault.clicked.connect(self.open_vault_dialog)
        layout.addWidget(self.btn_open_vault)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        self.btn_new_file = QPushButton("NOTE")
        self.btn_new_file.setStyleSheet("background-color: #262626; color: #5bc0de; border: none; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;")
        self.btn_new_file.clicked.connect(self.create_new_file)
        
        self.btn_new_canvas = QPushButton("CANVAS")
        self.btn_new_canvas.setStyleSheet("background-color: #262626; color: #ebcb8b; border: none; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;")
        self.btn_new_canvas.clicked.connect(self.create_new_canvas)

        self.btn_new_folder = QPushButton("FOLDER")
        self.btn_new_folder.setStyleSheet("background-color: #262626; color: #a3be8c; border: none; padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;")
        self.btn_new_folder.clicked.connect(self.create_new_folder)
        
        btn_layout.addWidget(self.btn_new_file)
        btn_layout.addWidget(self.btn_new_canvas)
        btn_layout.addWidget(self.btn_new_folder)
        layout.addLayout(btn_layout)
        
        self.file_model = QFileSystemModel()
        self.file_model.setReadOnly(False) 
        self.file_model.setNameFilters(["*.md", "*.txt", "*.canvas"]) 
        self.file_model.setNameFilterDisables(False) 
        self.file_model.setRootPath("") 
        
        self.proxy_model = GhostProxyModel()
        self.proxy_model.setSourceModel(self.file_model)
        
        self.tree = VaultTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setHeaderHidden(True)
        
        # Tightens the indent width to be closer to VS Code (12 pixels)
        self.tree.setIndentation(12) 
        
        for i in range(1, 4): self.tree.setColumnHidden(i, True)
            
        self.tree.setStyleSheet("""
            QTreeView { background-color: transparent; border: none; color: #cccccc; font-size: 13px; }
            QTreeView::item { padding: 4px 0px; border-radius: 4px; }
            QTreeView::item:hover { background-color: #2a2a2a; }
            QTreeView::item:selected { background-color: #333333; color: #ffffff; font-weight: bold; }
        """)
        
        self.tree.clicked.connect(self.on_file_clicked)

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        
        layout.addWidget(self.tree)

    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #262626; color: #cccccc; border: 1px solid #333; border-radius: 4px; font-family: "iA Writer Quattro S"; font-size: 12px;}
            QMenu::item { padding: 8px 25px; }
            QMenu::item:selected { background-color: #5bc0de; color: #1a1a1a; }
        """)

        if index.isValid():
            open_new_action = QAction("Open in New Pane", self)
            open_new_action.triggered.connect(lambda checked=False, idx=index: self.trigger_context_open(idx))
            menu.addAction(open_new_action)

            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda checked=False, idx=index: self.tree.edit(idx))
            menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda checked=False, idx=index: self.delete_item(idx))
            menu.addAction(delete_action)
        else:
            new_note_action = QAction("New Note", self)
            new_note_action.triggered.connect(self.create_new_file)
            menu.addAction(new_note_action)

            new_folder_action = QAction("New Folder", self)
            new_folder_action.triggered.connect(self.create_new_folder)
            menu.addAction(new_folder_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def trigger_context_open(self, proxy_index):
        self.process_click(proxy_index, force_new_pane=True)

    def on_file_clicked(self, proxy_index):
        modifiers = QApplication.keyboardModifiers()
        force_new_pane = bool(modifiers == Qt.ControlModifier)
        self.process_click(proxy_index, force_new_pane)

    def process_click(self, proxy_index, force_new_pane):
        source_index = self.proxy_model.mapToSource(proxy_index)
        file_path = self.file_model.filePath(source_index)
        
        if self.file_model.isDir(source_index):
            folder_name = os.path.basename(file_path)
            ghost_note_path = os.path.join(file_path, f"{folder_name}.md")
            if os.path.exists(ghost_note_path):
                self.file_selected.emit(ghost_note_path, force_new_pane)
        else:
            self.file_selected.emit(file_path, force_new_pane)

    def delete_item(self, proxy_index):
        source_index = self.proxy_model.mapToSource(proxy_index)
        path = self.file_model.filePath(source_index)
        file_name = os.path.basename(path)

        msg = QMessageBox(self)
        msg.setWindowTitle("Confirm Deletion")
        msg.setText(f"Destroy '{file_name}' permanently?")
        msg.setStyleSheet("QMessageBox { background-color: #1a1a1a; color: #cccccc; } QPushButton { background-color: #333; color: #fff; padding: 5px 15px; border: none; font-weight: bold; } QPushButton:hover { background-color: #ff5555; }")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path) 
                else:
                    os.remove(path) 
            except PermissionError:
                QMessageBox.warning(self, "File Locked", "Windows cannot delete this file because it is currently open in a pane. Please close the pane ('X') and try again.")
            except Exception as e:
                pass
        
    def open_vault_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Vault Folder")
        if folder_path: self.load_vault(folder_path)
            
    def load_vault(self, folder_path):
        self.file_model.setRootPath(folder_path)
        source_index = self.file_model.index(folder_path)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.tree.setRootIndex(proxy_index)
        self.btn_open_vault.setText(f"{folder_path.split('/')[-1].upper()[:14]}")

    def get_target_directory(self):
        root = self.file_model.rootPath()
        if not root: return None
        proxy_index = self.tree.currentIndex()
        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            path = self.file_model.filePath(source_index)
            if self.file_model.isDir(source_index): return path 
            else: return QFileInfo(path).absolutePath() 
        return root 

    def create_new_file(self):
        target_dir = self.get_target_directory()
        if not target_dir: return 
        file_name, ok = QInputDialog.getText(self, "New Note", "Enter chapter name:")
        if ok and file_name:
            if not file_name.endswith('.md'): file_name += '.md'
            full_path = os.path.join(target_dir, file_name)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(f"# {file_name.replace('.md', '')}\n\n")
            self.tree.expand(self.proxy_model.mapFromSource(self.file_model.index(target_dir)))
            self.file_selected.emit(full_path, False)

    def create_new_canvas(self):
        target_dir = self.get_target_directory()
        if not target_dir: return 
        file_name, ok = QInputDialog.getText(self, "New Canvas", "Enter board name:")
        if ok and file_name:
            if not file_name.endswith('.canvas'): file_name += '.canvas'
            full_path = os.path.join(target_dir, file_name)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write("[]") 
            self.tree.expand(self.proxy_model.mapFromSource(self.file_model.index(target_dir)))
            self.file_selected.emit(full_path, False)

    def create_new_folder(self):
        target_dir = self.get_target_directory()
        if not target_dir: return 
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and folder_name:
            full_path = os.path.join(target_dir, folder_name)
            if not os.path.exists(full_path):
                os.makedirs(full_path)