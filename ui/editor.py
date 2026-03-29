import re
import os
import json
import mistune
import ctypes
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, QPlainTextEdit, 
                             QTextBrowser, QMenu, QLabel, QApplication, QMessageBox, QListWidget)
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont, 
                           QTextCursor, QImage, QAction)
from PySide6.QtCore import Qt, Signal, QUrl, QMimeDatabase, QPoint

class FocusHighlighter(QSyntaxHighlighter):
    def __init__(self, document, editor_ref):
        super().__init__(document)
        self.editor_ref = editor_ref 
        self.current_block_num = 0
        self.render_mode = 1 

    def set_render_mode(self, mode):
        self.render_mode = mode
        self.rehighlight()

    def set_current_block(self, block_num):
        if self.current_block_num != block_num:
            self.current_block_num = block_num
            self.rehighlight()

    def highlightBlock(self, text):
        block = self.currentBlock()
        block_start = block.position()
        block_end = block_start + len(text)
        block_num = block.blockNumber()
        distance = abs(block_num - self.current_block_num)

        base_color = QColor("#cccccc") 
        if self.render_mode == 1:
            if distance == 0: base_color = QColor("#cccccc") 
            elif distance == 1: base_color = QColor("#737373") 
            elif distance == 2: base_color = QColor("#404040") 
            else: base_color = QColor("#262626") 

        base_fmt = QTextCharFormat()
        base_fmt.setForeground(base_color)
        self.setFormat(0, len(text), base_fmt)

        is_active = (distance == 0)

        for match in re.finditer(r'^(#{1,6}\s+)(.*)', text):
            level = len(match.group(1).strip())
            fmt = QTextCharFormat()
            fmt.setForeground(base_color)
            fmt.setFontWeight(QFont.Bold)
            fmt.setFontPointSize({1: 24, 2: 20, 3: 18, 4: 16, 5: 14, 6: 14}.get(level, 14))
            self.setFormat(match.start(), match.end() - match.start(), fmt)

        self.apply_live_markdown(r'(\*\*.*?\*\*)', text, base_color, weight=QFont.Bold)
        self.apply_live_markdown(r'((?<!\*)\*[^\*]+\*)', text, base_color, italic=True)
        self.apply_live_markdown(r'(_.*?_)', text, base_color, italic=True)
        
        quote_color = QColor("#888888") if is_active else base_color
        self.apply_live_markdown(r'^(>.*)', text, quote_color, italic=True)

        link_color = QColor("#5bc0de") if is_active else base_color
        
        self.apply_live_markdown(r'(!\[\[.*?\]\])', text, QColor("#a3be8c") if is_active else base_color)
        self.apply_live_markdown(r'(\[\[.*?\]\])', text, link_color)
        self.apply_live_markdown(r'(\[.*?\]\(.*?\))', text, link_color)

        editor_width = self.editor_ref.viewport().width()
        if editor_width <= 0: editor_width = 800 

        for p_start, p_end in self.editor_ref.pasted_ranges:
            if p_start < block_end and p_end > block_start:
                overlap_start = max(block_start, p_start)
                overlap_end = min(block_end, p_end)
                
                for i in range(overlap_start - block_start, overlap_end - block_start):
                    cursor = QTextCursor(block)
                    cursor.setPosition(block_start + i)
                    char_rect = self.editor_ref.cursorRect(cursor)
                    x_pos = char_rect.left()
                    ratio = max(0, min(1, x_pos / editor_width))

                    r1, g1, b1 = 224, 121, 73  
                    r2, g2, b2 = 118, 153, 237 

                    r = int(r1 + (r2 - r1) * ratio)
                    g = int(g1 + (g2 - g1) * ratio)
                    b = int(b1 + (b2 - b1) * ratio)
                    tint_color = QColor(r, g, b)
                    if self.render_mode == 1 and distance > 1:
                        tint_color = QColor(r//3, g//3, b//3)

                    tint_fmt = QTextCharFormat()
                    tint_fmt.setForeground(tint_color)
                    self.setFormat(i, 1, tint_fmt)

    def apply_live_markdown(self, pattern, text, color, weight=None, italic=False):
        for match in re.finditer(pattern, text):
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            if weight: fmt.setFontWeight(weight)
            if italic: fmt.setFontItalic(True)
            self.setFormat(match.start(), match.end() - match.start(), fmt)


class FocusEditor(QPlainTextEdit):
    text_scanned = Signal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("textEditor")
        self.current_file_path = None 
        self.pasted_ranges = []
        self.is_pasting = False
        
        self.setStyleSheet("""
            QPlainTextEdit { background-color: transparent; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #333333; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.setFont(QFont("iA Writer Quattro S", 14))
        self.highlighter = FocusHighlighter(self.document(), self)
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.completer_list = QListWidget(self)
        self.completer_list.hide()
        self.completer_list.setFixedWidth(200)
        self.completer_list.setMaximumHeight(150)
        self.completer_list.setStyleSheet("""
            QListWidget { background: #262626; color: #ccc; border: 1px solid #5bc0de; border-radius: 4px; font-size: 13px; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #333333; color: #5bc0de; font-weight: bold; }
        """)
        
        self.cursorPositionChanged.connect(self.update_focus)
        self.textChanged.connect(self.auto_save) 
        self.document().contentsChange.connect(self.update_pasted_ranges)

    def mousePressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.button() == Qt.LeftButton:
            # Compatibility for PySide6 point grabbing
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            cursor = self.cursorForPosition(pos)
            text_block = cursor.block().text()
            pos_in_block = cursor.positionInBlock()
            
            for match in re.finditer(r'\[\[(.*?)\]\]', text_block):
                if match.start() > 0 and text_block[match.start()-1] == '!':
                    continue
                if match.start() <= pos_in_block <= match.end():
                    target = match.group(1).split('|')[0] 
                    if hasattr(self, 'engine'):
                        self.engine.link_clicked.emit(f"wiki:{target}", True) 
                    return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """Hover over ![[img]] text, hold Alt, scroll wheel to magically rewrite the size!"""
        if event.modifiers() == Qt.AltModifier:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            cursor = self.cursorForPosition(pos)
            block = cursor.block()
            text = block.text()
            pos_in_block = cursor.positionInBlock()

            # Find the image tag you are hovering over
            for match in re.finditer(r'!\[\[(.*?\.(?:png|jpg|jpeg|gif|webp))(?:\|(\d+))?\]\]', text, flags=re.IGNORECASE):
                if match.start() <= pos_in_block <= match.end():
                    img_name = match.group(1)
                    # Default to 300px if no size exists yet
                    current_size = int(match.group(2)) if match.group(2) else 300 
                    
                    if event.angleDelta().y() > 0:
                        new_size = current_size + 25 # Scroll up, get bigger
                    else:
                        new_size = max(50, current_size - 25) # Scroll down, get smaller
                        
                    new_tag = f"![[{img_name}|{new_size}]]"
                    
                    # Highlight the old tag and replace it with the newly sized one
                    cursor.setPosition(block.position() + match.start())
                    cursor.setPosition(block.position() + match.end(), QTextCursor.KeepAnchor)
                    cursor.insertText(new_tag)
                    
                    event.accept()
                    return
        super().wheelEvent(event)

    def _get_vault_root(self):
        if not self.current_file_path: return None
        temp_dir = os.path.dirname(self.current_file_path)
        vault_root = temp_dir
        for _ in range(10): 
            if os.path.exists(os.path.join(temp_dir, ".history")):
                vault_root = temp_dir
                break
            parent = os.path.dirname(temp_dir)
            if parent == temp_dir: break
            temp_dir = parent
        return vault_root

    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #262626; color: #cccccc; border: 1px solid #333; border-radius: 4px; font-family: "iA Writer Quattro S"; font-size: 12px;}
            QMenu::item { padding: 8px 25px; }
            QMenu::item:selected { background-color: #a3be8c; color: #1a1a1a; }
        """)

        cursor = self.cursorForPosition(position)
        text_block = cursor.block().text()
        
        image_match = None
        for match in re.finditer(r'!\[\[(.*?\.(?:png|jpg|jpeg|gif|webp))(?:\|.*?)?\]\]', text_block, flags=re.IGNORECASE):
            if match.start() <= cursor.positionInBlock() <= match.end():
                image_match = match
                break
        
        if image_match:
            filename = image_match.group(1)
            vault_root = self._get_vault_root()
            attachment_path = os.path.join(vault_root, "_attachments", filename)
            
            locate_action = QAction(f"Locate '{filename}' in Explorer", self)
            locate_action.triggered.connect(lambda: os.startfile(os.path.dirname(attachment_path)))
            menu.addAction(locate_action)

            delete_action = QAction(f"Permanently Delete '{filename}'", self)
            delete_action.triggered.connect(lambda: self._delete_attachment_flow(filename, attachment_path, image_match))
            menu.addAction(delete_action)
            menu.addSeparator()

        standard_menu = self.createStandardContextMenu()
        for action in standard_menu.actions():
            menu.addAction(action)

        menu.exec(self.mapToGlobal(position))

    def _delete_attachment_flow(self, filename, filepath, regex_match):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirm Attachment Destruction")
        msg.setText(f"Delete file '{filename}' permanently from disk?")
        msg.setInformativeText("This will also remove the link from this document. This cannot be undone.")
        msg.setStyleSheet("QMessageBox { background-color: #1a1a1a; color: #cccccc; } QPushButton { background-color: #333; color: #fff; padding: 5px 15px; border: none; font-weight: bold; } QPushButton[text='Yes'] { background-color: #ff5555; }")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                QMessageBox.warning(self, "Delete Error", f"Windows locked the file: {str(e)}")
                return

            cursor = self.textCursor()
            block_start = cursor.block().position()
            cursor.setPosition(block_start + regex_match.start())
            cursor.setPosition(block_start + regex_match.end(), QTextCursor.KeepAnchor)
            cursor.removeSelectedText()

    def insertFromMimeData(self, source):
        if self.current_file_path and (source.hasImage() or source.hasUrls()):
            image = None
            if source.hasImage():
                image = source.imageData()
            elif source.hasUrls():
                urls = source.urls()
                if urls and urls[0].isLocalFile():
                    file_path = urls[0].toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        image = QImage(file_path)

            if image and not image.isNull():
                vault_root = self._get_vault_root()
                if not vault_root: return

                attachments_dir = os.path.join(vault_root, "_attachments")
                if not os.path.exists(attachments_dir):
                    os.makedirs(attachments_dir)
                    if os.name == 'nt':
                        try: ctypes.windll.kernel32.SetFileAttributesW(attachments_dir, 2)
                        except: pass
                
                filename = datetime.now().strftime("img_%Y%m%d_%H%M%S.png")
                save_path = os.path.join(attachments_dir, filename)
                image.save(save_path, "PNG")
                
                cursor = self.textCursor()
                cursor.insertText(f"\n![[{filename}]]\n")
                return

        self.is_pasting = True
        super().insertFromMimeData(source)
        self.is_pasting = False

    def update_pasted_ranges(self, position, charsRemoved, charsAdded):
        if charsRemoved == 0 and charsAdded == 0: return
        delta = charsAdded - charsRemoved
        new_ranges = []
        if self.is_pasting:
            new_ranges.append([position, position + charsAdded])
        for start, end in self.pasted_ranges:
            if position + charsRemoved <= start:
                new_ranges.append([start + delta, end + delta])
            elif position >= end:
                new_ranges.append([start, end])
            else:
                left_start = start
                left_end = min(position, end)
                if left_end > left_start:
                    new_ranges.append([left_start, left_end])
                right_start = max(position + charsRemoved, start) + delta
                right_end = end + delta
                if right_end > right_start:
                    new_ranges.append([right_start, right_end])

        if not new_ranges:
            self.pasted_ranges = []
            return
        new_ranges.sort(key=lambda x: x[0])
        merged = [new_ranges[0]]
        for current in new_ranges[1:]:
            previous = merged[-1]
            if current[0] <= previous[1]:
                previous[1] = max(previous[1], current[1])
            else:
                merged.append(current)
        self.pasted_ranges = [r for r in merged if r[1] > r[0]]
        self.highlighter.rehighlight()

    def keyPressEvent(self, event):
        if self.completer_list.isVisible():
            if event.key() == Qt.Key_Down:
                self.completer_list.setCurrentRow((self.completer_list.currentRow() + 1) % self.completer_list.count())
                return
            elif event.key() == Qt.Key_Up:
                self.completer_list.setCurrentRow((self.completer_list.currentRow() - 1) % self.completer_list.count())
                return
            elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
                self._insert_completion()
                return
            elif event.key() == Qt.Key_Escape:
                self.completer_list.hide()
                return

        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_B: self.wrap_selection("**"); return
            elif event.key() == Qt.Key_I: self.wrap_selection("*"); return
            elif event.key() == Qt.Key_U: self.wrap_selection("<u>", "</u>"); return
            
        super().keyPressEvent(event)
        
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        
        match = re.search(r'\[\[([^\]]*)$', block_text[:pos])
        if match:
            search_term = match.group(1).lower()
            self._show_completer(search_term)
        else:
            self.completer_list.hide()

    def _show_completer(self, search_term):
        vault_root = self._get_vault_root()
        if not vault_root: return
        
        self.completer_list.clear()
        
        for root, dirs, files in os.walk(vault_root):
            if ".history" in dirs: dirs.remove(".history")
            if "_attachments" in dirs: dirs.remove("_attachments")
            for f in files:
                if f.endswith('.md') or f.endswith('.canvas'):
                    name = f.rsplit('.', 1)[0]
                    if search_term in name.lower():
                        self.completer_list.addItem(name)
                        
        if self.completer_list.count() > 0:
            self.completer_list.setCurrentRow(0)
            rect = self.cursorRect()
            self.completer_list.move(rect.bottomLeft() + QPoint(0, 5))
            self.completer_list.show()
            self.completer_list.raise_()
        else:
            self.completer_list.hide()

    def _insert_completion(self):
        item = self.completer_list.currentItem()
        if not item: return
        text = item.text()
        
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        match = re.search(r'\[\[([^\]]*)$', block_text[:pos])
        
        if match:
            length_to_remove = len(match.group(1))
            for _ in range(length_to_remove):
                cursor.deletePreviousChar()
            cursor.insertText(f"{text}]]")
            self.setTextCursor(cursor)
            
        self.completer_list.hide()

    def wrap_selection(self, prefix, suffix=None):
        if not suffix: suffix = prefix
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{prefix}{text}{suffix}")
            cursor.setPosition(cursor.position() - len(text) - len(suffix))
            cursor.setPosition(cursor.position() + len(text), QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
        else:
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(cursor.position() - len(suffix))
            self.setTextCursor(cursor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        app_width = self.width()
        max_text_width = 800 
        if app_width > max_text_width:
            empty_space = int((app_width - max_text_width) / 2)
            self.setViewportMargins(empty_space, 40, empty_space, 40)
        else:
            self.setViewportMargins(40, 40, 40, 40)

    def update_focus(self):
        cursor = self.textCursor()
        block = cursor.block() 
        self.highlighter.set_current_block(block.blockNumber())
        self.centerCursor()
        self.text_scanned.emit(block.text()) 

    def load_file(self, file_path):
        self.current_file_path = file_path
        self.blockSignals(True) 
        with open(file_path, 'r', encoding='utf-8') as f:
            self.setPlainText(f.read())
        
        meta_path = file_path.replace('.md', '.meta.json')
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.pasted_ranges = data.get("pasted", [])
            except:
                self.pasted_ranges = []
        else:
            self.pasted_ranges = []
            
        self.blockSignals(False) 
        self.highlighter.set_current_block(0)

    def auto_save(self):
        if self.current_file_path:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            
            meta_path = self.current_file_path.replace('.md', '.meta.json')
            meta_data = {
                "pasted": self.pasted_ranges
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f)


class MarkdownViewer(QTextBrowser):
    link_clicked = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_file_path = None
        self.setStyleSheet("""
            QTextBrowser { background-color: transparent; border: none; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #333333; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.setOpenLinks(False) 
        self.anchorClicked.connect(self.handle_click)
        
    def handle_click(self, url):
        self.link_clicked.emit(url.toString())
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        app_width = self.width()
        max_text_width = 800 
        if app_width > max_text_width:
            empty_space = int((app_width - max_text_width) / 2)
            self.setViewportMargins(empty_space, 40, empty_space, 40)
        else:
            self.setViewportMargins(40, 40, 40, 40)
            
    def update_content(self, raw_markdown):
        vault_root = ""
        if self.current_file_path:
            temp_dir = os.path.dirname(self.current_file_path)
            vault_root = temp_dir
            for _ in range(10):
                if os.path.exists(os.path.join(temp_dir, ".history")):
                    vault_root = temp_dir
                    break
                parent = os.path.dirname(temp_dir)
                if parent == temp_dir: break
                temp_dir = parent

        def replace_img(match):
            img_name = match.group(1)
            custom_width = match.group(2) 
            
            img_path = os.path.join(vault_root, "_attachments", img_name)
            if not os.path.exists(img_path): return f"<b>[Attachment Missing: {img_name}]</b>"
            file_url = QUrl.fromLocalFile(img_path).toString()
            
            width_attr = custom_width if custom_width else "100%"
            
            return f'<br><img src="{file_url}" width="{width_attr}"><br>'

        processed_text = re.sub(r'!\[\[(.*?\.(?:png|jpg|jpeg|gif|webp))(?:\|(\d+))?\]\]', replace_img, raw_markdown, flags=re.IGNORECASE)
        processed_text = re.sub(r'\[\[(.*?)\]\]', r'<a href="wiki:\1">\1</a>', processed_text)
        
        html = mistune.html(processed_text)
        styled_html = f"""
        <style>
            body {{ color: #cccccc; font-family: "iA Writer Quattro S"; font-size: 18px; line-height: 1.6; padding-top: 40px; }}
            h1, h2, h3, h4 {{ color: #ffffff; font-weight: bold; margin-top: 1.5em; margin-bottom: 0.5em; }}
            strong {{ color: #ffffff; }}
            em {{ color: #aaaaaa; }}
            a {{ color: #5bc0de; text-decoration: none; font-weight: bold; }}
            blockquote {{ border-left: 3px solid #5bc0de; padding-left: 15px; color: #888; font-style: italic; }}
            img {{ border-radius: 4px; display: block; margin-left: auto; margin-right: auto;}} 
        </style>
        <body>{html}</body>
        """
        self.setHtml(styled_html)


class DualEditorEngine(QWidget):
    link_clicked = Signal(str, bool) 
    text_scanned = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.stack = QStackedWidget()
        
        self.viewer = MarkdownViewer()
        self.editor = FocusEditor()
        
        self.editor.engine = self
        self.viewer.engine = self
        
        self.stack.addWidget(self.editor)
        self.stack.addWidget(self.viewer)
        self.layout.addWidget(self.stack)
        
        self.editor.text_scanned.connect(self.text_scanned.emit)
        self.viewer.link_clicked.connect(lambda url: self.link_clicked.emit(url, False))
        
        self.highlighter = self.editor.highlighter
        
    def load_file(self, file_path):
        self.viewer.current_file_path = file_path 
        self.editor.load_file(file_path)
        
    def setVerticalScrollBarPolicy(self, policy):
        self.editor.setVerticalScrollBarPolicy(policy)
        self.viewer.setVerticalScrollBarPolicy(policy)
        
    def toggle_reading_mode(self):
        if self.stack.currentIndex() == 0:
            self.viewer.update_content(self.editor.toPlainText())
            self.stack.setCurrentIndex(1)
            self.viewer.setFocus()
        else:
            self.stack.setCurrentIndex(0)
            self.editor.setFocus()