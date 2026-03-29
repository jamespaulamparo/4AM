import sys
import os
import json
import ctypes
import shutil
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QDockWidget, QLabel, QPushButton,
                             QPlainTextEdit, QTextEdit, QLineEdit) 
from PySide6.QtGui import QFontDatabase, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QSize, QTimer, QByteArray
from PySide6.QtGui import QIcon

from ui.editor import DualEditorEngine 
from ui.hud import ReactiveHUD
from ui.sidebar import VaultSidebar
from ui.mode_canvas import CanvasEngine
from ui.oracle import OmniSearch    

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')
STYLES_DIR = os.path.join(ASSETS_DIR, 'styles')
SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'session.json')

class CoreFrameworkWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("4AM")
        self.resize(1300, 800) 
        self.setMinimumSize(QSize(1000, 600))

        self.load_application_fonts()
        self.load_qss_theme()
        self.set_native_dark_titlebar()

        self.setDockNestingEnabled(True)

        self.dummy_central = QWidget()
        self.setCentralWidget(self.dummy_central)
        self.dummy_central.hide()

        self.sidebar = VaultSidebar(self)
        self.sidebar_dock = QDockWidget("", self)
        self.sidebar_dock.setTitleBarWidget(QWidget()) 
        self.sidebar_dock.setWidget(self.sidebar)
        self.sidebar_dock.setFeatures(QDockWidget.NoDockWidgetFeatures) 
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar_dock)
        
        # Locks sidebar to 200px on very first load before memory kicks in
        self.resizeDocks([self.sidebar_dock], [200], Qt.Horizontal)

        self.hud = ReactiveHUD()
        self.hud_dock = QDockWidget("", self)
        self.hud_dock.setTitleBarWidget(QWidget()) 
        self.hud_dock.setWidget(self.hud)
        self.addDockWidget(Qt.RightDockWidgetArea, self.hud_dock)
        self.hud_dock.hide() 

        self.open_docks = {}
        self.is_focus_mode = False
        self.hud_visible_in_focus = False

        self.setWindowIcon(QIcon("logo.ico"))

        self.sidebar.file_selected.connect(self.route_file_click) 

        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.toggle_focus_mode)
        QShortcut(QKeySequence("F11"), self).activated.connect(self.toggle_fullscreen)
        QShortcut(QKeySequence("Shift+Tab"), self).activated.connect(self.toggle_ghost_hud)
        QShortcut(QKeySequence("Ctrl+Shift+H"), self).activated.connect(self.toggle_hud_float)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.trigger_reading_mode)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self).activated.connect(self.center_align_text)
        QShortcut(QKeySequence("Ctrl+Shift+F"), self).activated.connect(self.trigger_omni_search)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.trigger_local_search)

        self.snapshot_timer = QTimer(self)
        self.snapshot_timer.timeout.connect(self.take_vault_snapshots)
        self.snapshot_timer.start(10 * 60 * 1000) 

        self.load_session()

    def route_file_click(self, file_path, force_new_pane=False):
        self.current_active_file = file_path 
        
        if file_path in self.open_docks:
            self.open_docks[file_path].raise_()
            self.open_docks[file_path].activateWindow()
            return

        if file_path.endswith('.canvas'):
            engine = CanvasEngine()
        else:
            engine = DualEditorEngine()
            engine.text_scanned.connect(self.hud.process_text)
            engine.link_clicked.connect(self.handle_wiki_link)
            engine.highlighter.set_render_mode(1 if self.is_focus_mode else 0)
            
        engine.load_file(file_path)

        active_dock = None
        active_path = None
        
        if not force_new_pane:
            for path, dock in self.open_docks.items():
                if dock.isActiveWindow() or dock.hasFocus():
                    active_dock = dock
                    active_path = path
                    break
                    
            if not active_dock and self.open_docks:
                active_path, active_dock = list(self.open_docks.items())[0]

        file_name = os.path.basename(file_path)

        if active_dock and not force_new_pane:
            old_widget = active_dock.widget()
            active_dock.setWidget(engine)
            
            title_bar = QWidget()
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(15, 5, 15, 5)
            
            title_label = QLabel(file_name.upper())
            title_label.setStyleSheet("color: #666; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
            
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(20, 20)
            close_btn.setStyleSheet("QPushButton { background: transparent; color: #555; border: none; font-weight: bold; } QPushButton:hover { color: #ff5555; }")
            
            close_btn.clicked.connect(lambda checked=False, f=file_path: self.close_pane(f))
            
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            
            search_bar = QLineEdit()
            search_bar.setObjectName("local_search")
            search_bar.setPlaceholderText("Find...")
            search_bar.setFixedWidth(150)
            search_bar.hide() 
            search_bar.setStyleSheet("background: #1a1a1a; color: #ccc; border: 1px solid #3a3a3a; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            search_bar.textChanged.connect(lambda text, d=active_dock if active_dock and not force_new_pane else new_dock: self.execute_local_search(text, d))
            search_bar.returnPressed.connect(lambda d=active_dock if active_dock and not force_new_pane else new_dock: self.find_next_local(d))
            
            title_layout.addWidget(search_bar)
            title_layout.addWidget(close_btn)
            title_bar.setStyleSheet("background: #1a1a1a; border-bottom: 1px solid #262626;")
            
            active_dock.setTitleBarWidget(title_bar) 
            
            del self.open_docks[active_path]
            self.open_docks[file_path] = active_dock
            old_widget.deleteLater() 
        else:
            new_dock = QDockWidget(file_name, self)
            title_bar = QWidget()
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(15, 5, 15, 5)
            
            title_label = QLabel(file_name.upper())
            title_label.setStyleSheet("color: #666; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
            
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(20, 20)
            close_btn.setStyleSheet("QPushButton { background: transparent; color: #555; border: none; font-weight: bold; } QPushButton:hover { color: #ff5555; }")
            
            close_btn.clicked.connect(lambda checked=False, f=file_path: self.close_pane(f))
            
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            
            search_bar = QLineEdit()
            search_bar.setObjectName("local_search")
            search_bar.setPlaceholderText("Find...")
            search_bar.setFixedWidth(150)
            search_bar.hide() 
            search_bar.setStyleSheet("background: #1a1a1a; color: #ccc; border: 1px solid #3a3a3a; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            search_bar.textChanged.connect(lambda text, d=active_dock if active_dock and not force_new_pane else new_dock: self.execute_local_search(text, d))
            search_bar.returnPressed.connect(lambda d=active_dock if active_dock and not force_new_pane else new_dock: self.find_next_local(d))
            
            title_layout.addWidget(search_bar)
            title_layout.addWidget(close_btn)
            title_bar.setStyleSheet("background: #1a1a1a; border-bottom: 1px solid #262626;")
            
            new_dock.setTitleBarWidget(title_bar)
            new_dock.setWidget(engine)

            self.addDockWidget(Qt.RightDockWidgetArea, new_dock)
            self.open_docks[file_path] = new_dock

    def close_pane(self, file_path):
        if file_path in self.open_docks:
            dock = self.open_docks[file_path]
            self.removeDockWidget(dock)
            dock.deleteLater()
            del self.open_docks[file_path]

    def trigger_reading_mode(self):
        # 1. Ask PySide what widget the user is actually typing or looking at right now
        focus_widget = QApplication.focusWidget()
        
        # 2. Climb up the UI tree to find the Editor Engine that owns it
        parent = focus_widget
        while parent:
            if isinstance(parent, DualEditorEngine):
                parent.toggle_reading_mode()
                return
            parent = parent.parent()
            
        # 3. Fallback: If they clicked a title bar instead, find the active dock
        for dock in self.open_docks.values():
            if dock.isActiveWindow() or dock.hasFocus():
                if isinstance(dock.widget(), DualEditorEngine):
                    dock.widget().toggle_reading_mode()
                    return

    def toggle_focus_mode(self):
        self.is_focus_mode = not self.is_focus_mode
        if self.is_focus_mode:
            self.sidebar_dock.hide()
            self.hud_dock.hide() 
            self.hud_visible_in_focus = False
            for dock in self.open_docks.values():
                if isinstance(dock.widget(), DualEditorEngine):
                    dock.widget().setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    dock.widget().highlighter.set_render_mode(1) 
        else:
            self.sidebar_dock.show()
            self.hud_dock.show() 
            for dock in self.open_docks.values():
                if isinstance(dock.widget(), DualEditorEngine):
                    dock.widget().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    dock.widget().highlighter.set_render_mode(0) 

    def toggle_ghost_hud(self):
        if self.is_focus_mode:
            self.hud_visible_in_focus = not self.hud_visible_in_focus
            if self.hud_visible_in_focus: self.hud_dock.show()
            else: self.hud_dock.hide()
        else:
            if self.hud_dock.isVisible(): self.hud_dock.hide()
            else: self.hud_dock.show()

    def toggle_hud_float(self):
        is_floating = self.hud_dock.isFloating()
        self.hud_dock.setFloating(not is_floating)

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def set_native_dark_titlebar(self):
        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            hwnd = self.winId()
            rendering_policy = ctypes.c_int(2) 
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
        except Exception as e:
            pass

    def load_application_fonts(self):
        for root, _, files in os.walk(FONTS_DIR):
            for file in files:
                if file.lower().endswith(('.ttf', '.otf', '.woff2', '.woff')):
                    font_path = os.path.join(root, file)
                    QFontDatabase.addApplicationFont(font_path)

    def load_qss_theme(self):
        theme_path = os.path.join(STYLES_DIR, 'dark.qss')
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                self.setStyleSheet(f.read())

    def handle_wiki_link(self, target, force_new_pane=False):
        if not target.startswith("wiki:"): return
        target_name = target.replace("wiki:", "").strip()
        current_vault = self.sidebar.file_model.rootPath()
        if not current_vault: return

        found_path = None
        
        for root, dirs, files in os.walk(current_vault):
            if ".history" in dirs: dirs.remove(".history")
            if "_attachments" in dirs: dirs.remove("_attachments")
                
            if f"{target_name}.md" in files:
                found_path = os.path.join(root, f"{target_name}.md")
                break
            elif f"{target_name}.canvas" in files:
                found_path = os.path.join(root, f"{target_name}.canvas")
                break

        if found_path: 
            self.route_file_click(found_path, force_new_pane)
        else:
            new_path = os.path.join(current_vault, f"{target_name}.md")
            with open(new_path, 'w', encoding='utf-8') as f:
                f.write(f"# {target_name}\n\n")
            self.route_file_click(new_path, force_new_pane)

    def load_session(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                vault_path = data.get("vault_path")
                last_file = data.get("last_file")
                window_state = data.get("window_state")
                
                if vault_path and os.path.exists(vault_path):
                    self.sidebar.load_vault(vault_path)
                if last_file and os.path.exists(last_file):
                    self.route_file_click(last_file)
                    
                if window_state:
                    self.restoreState(QByteArray.fromHex(window_state.encode('utf-8')))
            except Exception as e:
                pass

    def closeEvent(self, event):
        self.take_vault_snapshots()
        
        session_data = {
            "vault_path": self.sidebar.file_model.rootPath(),
            "last_file": getattr(self, 'current_active_file', None),
            "window_state": self.saveState().toHex().data().decode('utf-8') 
        }
        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(session_data, f)
        except Exception as e:
            pass
        event.accept()
    
    def center_align_text(self):
        for dock in self.open_docks.values():
            if dock.isActiveWindow() or dock.hasFocus():
                widget = dock.widget()
                if isinstance(widget, DualEditorEngine):
                    text_edit = widget.findChild(QPlainTextEdit) or widget.findChild(QTextEdit)
                    if text_edit:
                        cursor = text_edit.textCursor()
                        if cursor.hasSelection():
                            text = cursor.selectedText()
                            cursor.insertText(f"<center>{text}</center>")
                        else:
                            cursor.insertText("<center></center>")
                            cursor.movePosition(cursor.Left, cursor.MoveAnchor, 9)
                            text_edit.setTextCursor(cursor)
                break

    def trigger_omni_search(self):
        vault_path = self.sidebar.file_model.rootPath()
        if not vault_path: return
        
        self.oracle = OmniSearch(self, vault_path)
        self.oracle.file_selected.connect(lambda path: self.route_file_click(path, force_new_pane=False))
        
        rect = self.geometry()
        self.oracle.move(rect.center().x() - self.oracle.width() // 2, rect.center().y() - self.oracle.height() // 2)
        
        self.oracle.show()
        self.oracle.search_bar.setFocus()

    def take_vault_snapshots(self):
        if not self.sidebar.file_model.rootPath(): return
        vault_path = self.sidebar.file_model.rootPath()
        
        history_dir = os.path.join(vault_path, ".history")
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
            if os.name == 'nt': 
                try: ctypes.windll.kernel32.SetFileAttributesW(history_dir, 2)
                except: pass
                    
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        
        for file_path in self.open_docks.keys():
            if not os.path.exists(file_path): continue
            
            file_name = os.path.basename(file_path)
            base, ext = os.path.splitext(file_name)
            snap_name = f"{base}_{timestamp}{ext}"
            snap_path = os.path.join(history_dir, snap_name)
            
            try: shutil.copy2(file_path, snap_path)
            except Exception: pass

    def trigger_local_search(self):
        for dock in self.open_docks.values():
            if dock.isActiveWindow() or dock.hasFocus():
                title_bar = dock.titleBarWidget()
                search_bar = title_bar.findChild(QLineEdit, "local_search")
                if search_bar:
                    if search_bar.isVisible():
                        search_bar.hide()
                        dock.widget().setFocus() 
                    else:
                        search_bar.show()
                        search_bar.setFocus()
                        search_bar.selectAll()
                break

    def execute_local_search(self, text, dock):
        widget = dock.widget()
        if isinstance(widget, DualEditorEngine):
            text_edit = widget.findChild(QPlainTextEdit) or widget.findChild(QTextEdit)
            if text_edit:
                cursor = text_edit.textCursor()
                cursor.setPosition(0)
                text_edit.setTextCursor(cursor)
                
                if text:
                    text_edit.find(text) 

    def find_next_local(self, dock):
        search_bar = dock.titleBarWidget().findChild(QLineEdit, "local_search")
        widget = dock.widget()
        if isinstance(widget, DualEditorEngine) and search_bar and search_bar.text():
            text_edit = widget.findChild(QPlainTextEdit) or widget.findChild(QTextEdit)
            if text_edit:
                if not text_edit.find(search_bar.text()):
                    cursor = text_edit.textCursor()
                    cursor.setPosition(0)
                    text_edit.setTextCursor(cursor)
                    text_edit.find(search_bar.text())