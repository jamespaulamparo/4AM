import json
import mistune
import os
import re
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsTextItem, 
                             QGraphicsRectItem, QGraphicsItem, QApplication, QGraphicsPixmapItem,
                             QMenu, QMessageBox, QListWidget)
from PySide6.QtCore import Qt, QUrl, Signal, QPoint
from PySide6.QtGui import (QFont, QColor, QPainter, QBrush, QPen, QShortcut, 
                           QKeySequence, QTextCursor, QCursor, QMouseEvent, QPixmap, QAction)

class CardTextItem(QGraphicsTextItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_markdown = ""
        self.is_editing = False
        self.setOpenExternalLinks(False) 
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)

    def render_html(self):
            processed_text = re.sub(r'\[\[(.*?)\]\]', r'<a href="wiki:\1">\1</a>', self.raw_markdown)
            
            # FIX: The Obsidian "Strict Line Breaks: Off" trick
            processed_text = processed_text.replace('\n', '  \n')
            
            html_content = mistune.html(processed_text)
            
            styled_html = f"""
            <style>
                body {{ color: #cccccc; font-family: "iA Writer Quattro S"; font-size: 16px; }}
                h1, h2, h3 {{ color: #ffffff; font-weight: bold; }}
                strong {{ font-weight: bold; color: #ffffff; }}
                em {{ font-style: italic; color: #aaaaaa; }}
                a {{ color: #5bc0de; text-decoration: none; }}
                blockquote {{ color: #888888; font-style: italic; }}
            </style>
            <body>{html_content}</body>
            """
            self.setHtml(styled_html)

    def mouseDoubleClickEvent(self, event):
        """Double Click to enter Edit Mode, leaving single clicks free for links!"""
        if event.button() == Qt.LeftButton:
            self.is_editing = True
            self.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.setPlainText(self.raw_markdown)
            self.setDefaultTextColor(QColor("#cccccc"))
            self.setFont(QFont("iA Writer Quattro S", 12))
            self.setFocus()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        # FIX: Only overwrite raw_markdown if we were ACTUALLY in edit mode. 
        # Prevents the app from deleting your [[ ]] brackets!
        if self.is_editing:
            self.raw_markdown = self.toPlainText()
            self.is_editing = False
            self.render_html() 
            self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        # 1. Connect to the Canvas Engine's Autocomplete List
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if view.completer_list.isVisible():
                if event.key() == Qt.Key_Down:
                    view.completer_list.setCurrentRow((view.completer_list.currentRow() + 1) % view.completer_list.count())
                    return
                elif event.key() == Qt.Key_Up:
                    view.completer_list.setCurrentRow((view.completer_list.currentRow() - 1) % view.completer_list.count())
                    return
                elif event.key() in (Qt.Key_Enter, Qt.Key_Return):
                    view._insert_completion()
                    return
                elif event.key() == Qt.Key_Escape:
                    view.completer_list.hide()
                    return

        # 2. Standard formatting
        if event.modifiers() == Qt.ControlModifier:
            if event.matches(QKeySequence.Paste):
                clipboard = QApplication.clipboard()
                self.textCursor().insertText(clipboard.text())
                return
            elif event.key() == Qt.Key_B: self.wrap_selection("**"); return
            elif event.key() == Qt.Key_I: self.wrap_selection("*"); return
            elif event.key() == Qt.Key_U: self.wrap_selection("<u>", "</u>"); return
            
        super().keyPressEvent(event)
        
        # 3. Check for [[ trigger
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        
        match = re.search(r'\[\[([^\]]*)$', block_text[:pos])
        if match:
            search_term = match.group(1).lower()
            if self.scene() and self.scene().views():
                self.scene().views()[0]._show_completer(self, search_term)
        else:
            if self.scene() and self.scene().views():
                self.scene().views()[0].completer_list.hide()

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


class LoreCard(QGraphicsRectItem):
    def __init__(self, x, y, width=300, raw_markdown=""):
        super().__init__()
        self.setPos(x, y)
        self.custom_width = width
        
        self.setZValue(10) 
        
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setBrush(QBrush(QColor("#262626"))) 
        self.setPen(QPen(QColor("#3a3a3a"), 1))  
        
        self.header = QGraphicsRectItem(self)
        self.header.setBrush(QBrush(QColor("#333333")))
        self.header.setPen(Qt.NoPen)
        
        self.text_item = CardTextItem(self)
        self.text_item.setPos(5, 15) 
        self.text_item.setTextWidth(self.custom_width - 15) 
        
        self.text_item.linkActivated.connect(self._on_link_click)
        
        if raw_markdown:
            self.text_item.raw_markdown = raw_markdown
            self.text_item.render_html() 
            
        self.resize_handle = QGraphicsRectItem(self)
        self.resize_handle.setBrush(QBrush(QColor("#5bc0de"))) 
        self.resize_handle.setPen(Qt.NoPen)
        self.resize_handle.setCursor(Qt.SizeHorCursor) 
        self.resizing = False
        
        self.text_item.document().contentsChanged.connect(self.auto_resize)
        self.auto_resize()

    def _on_link_click(self, url):
        # Opens in a new pane seamlessly!
        if self.scene() and self.scene().views():
            self.scene().views()[0].link_clicked.emit(url, True) 

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if value: 
                self.setPen(QPen(QColor("#5bc0de"), 2)) 
                self.header.setBrush(QBrush(QColor("#4a4a4a"))) 
            else: 
                self.setPen(QPen(QColor("#3a3a3a"), 1)) 
                self.header.setBrush(QBrush(QColor("#333333")))
        return super().itemChange(change, value)

    def auto_resize(self):
        doc_height = self.text_item.document().size().height()
        new_height = max(50, doc_height + 25)
        self.setRect(0, 0, self.custom_width, new_height)
        self.header.setRect(0, 0, self.custom_width, 15)
        self.resize_handle.setRect(self.custom_width - 6, (new_height / 2) - 15, 6, 30)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.resize_handle.rect().contains(event.pos()):
            self.resizing = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            new_width = max(100, event.pos().x())
            self.custom_width = new_width
            self.text_item.setTextWidth(self.custom_width - 15)
            self.auto_resize() 
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        super().mouseReleaseEvent(event)


class CanvasEngine(QGraphicsView):
    link_clicked = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setStyleSheet("border: none; background-color: #1a1a1a;")
        self.setRenderHint(QPainter.Antialiasing)
        
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        
        self.deleted_history = []
        self.clipboard_lore = [] 
        self.current_file_path = None
        self.scene.changed.connect(self.auto_save) 
        
        # --- CANVAS AUTOCOMPLETE POPUP ---
        self.completer_list = QListWidget(self)
        self.completer_list.hide()
        self.completer_list.setFixedWidth(200)
        self.completer_list.setMaximumHeight(150)
        self.completer_list.setFocusPolicy(Qt.NoFocus) 
        self.completer_list.setStyleSheet("""
            QListWidget { background: #262626; color: #ccc; border: 1px solid #5bc0de; border-radius: 4px; font-size: 13px; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #333333; color: #5bc0de; font-weight: bold; }
        """)
        self.completer_list.itemClicked.connect(self._insert_completion)
        self.active_text_item = None
        
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.spawn_card_at_cursor)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self.zoom_reset)

    def _show_completer(self, text_item, search_term):
        self.active_text_item = text_item
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
            # Spawn the popup right under the card you are typing in
            scene_pos = text_item.mapToScene(0, 0)
            view_pos = self.mapFromScene(scene_pos)
            self.completer_list.move(view_pos.x() + 10, view_pos.y() + 40)
            self.completer_list.show()
            self.completer_list.raise_()
        else:
            self.completer_list.hide()

    def _insert_completion(self, item=None):
        if not item:
            item = self.completer_list.currentItem()
        if not item or not self.active_text_item: return
        text = item.text()
        
        cursor = self.active_text_item.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        match = re.search(r'\[\[([^\]]*)$', block_text[:pos])
        
        if match:
            length_to_remove = len(match.group(1))
            for _ in range(length_to_remove):
                cursor.deletePreviousChar()
            cursor.insertText(f"{text}]]")
            self.active_text_item.setTextCursor(cursor)
            
        self.completer_list.hide()
        self.active_text_item = None

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

    def _get_spawn_pos(self):
        view_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(view_pos): view_pos = self.rect().center()
        return self.mapToScene(view_pos)

    def spawn_card_at_cursor(self):
        scene_pos = self._get_spawn_pos()
        card = LoreCard(scene_pos.x(), scene_pos.y())
        self.scene.addItem(card)
        self.scene.clearSelection()
        card.setSelected(True)
        # Auto-trigger edit mode so you can type immediately
        card.text_item.is_editing = True
        card.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        card.text_item.setPlainText("")
        card.text_item.setDefaultTextColor(QColor("#cccccc"))
        card.text_item.setFont(QFont("iA Writer Quattro S", 12))
        card.text_item.setFocus() 

    def _handle_image_drop(self, image_data, scene_pos):
        vault_root = self._get_vault_root()
        if not vault_root: return

        attachments_dir = os.path.join(vault_root, "_attachments")
        if not os.path.exists(attachments_dir):
            os.makedirs(attachments_dir)

        from datetime import datetime
        filename = datetime.now().strftime("canvas_img_%Y%m%d_%H%M%S.png")
        save_path = os.path.join(attachments_dir, filename)
        image_data.save(save_path, "PNG")

        card = ImageLoreCard(scene_pos.x(), scene_pos.y(), filename, vault_root)
        self.scene.addItem(card)
        self.scene.clearSelection()
        card.setSelected(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        mime_data = event.mimeData()
        
        if mime_data.hasImage():
            image = mime_data.imageData()
            if image and not image.isNull():
                self._handle_image_drop(image, scene_pos)
                event.acceptProposedAction()
                return

        elif mime_data.hasUrls():
            urls = mime_data.urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    image = QPixmap(file_path).toImage()
                    self._handle_image_drop(image, scene_pos)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def mousePressEvent(self, event):
        # Hide completer if you click away
        if self.completer_list.isVisible():
            self.completer_list.hide()
            
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake_event = QMouseEvent(event.type(), event.pos(), event.globalPos(), Qt.LeftButton, event.buttons() | Qt.LeftButton, event.modifiers())
            super().mousePressEvent(fake_event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            fake_event = QMouseEvent(event.type(), event.pos(), event.globalPos(), Qt.LeftButton, event.buttons() & ~Qt.LeftButton, event.modifiers())
            super().mouseReleaseEvent(fake_event)
            self.setDragMode(QGraphicsView.RubberBandDrag) 
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if isinstance(self.scene.focusItem(), CardTextItem):
            super().keyPressEvent(event)
            return

        if event.matches(QKeySequence.Paste):
            mime_data = QApplication.clipboard().mimeData()
            
            if mime_data.hasImage():
                image = mime_data.imageData()
                if image and not image.isNull():
                    self._handle_image_drop(image, self._get_spawn_pos())
                    return

            if self.clipboard_lore:
                self.scene.clearSelection()
                scene_pos = self._get_spawn_pos()
                
                base_x = self.clipboard_lore[0]['x']
                base_y = self.clipboard_lore[0]['y']
                
                vault_root = self._get_vault_root()

                for data in self.clipboard_lore:
                    rel_x = data['x'] - base_x
                    rel_y = data['y'] - base_y
                    
                    if data['type'] == 'text':
                        card = LoreCard(scene_pos.x() + rel_x, scene_pos.y() + rel_y, data['width'], data['markdown'])
                    elif data['type'] == 'image' and vault_root:
                        card = ImageLoreCard(scene_pos.x() + rel_x, scene_pos.y() + rel_y, data['filename'], vault_root, data.get('width'), data.get('height'))
                        
                    self.scene.addItem(card)
                    card.setSelected(True)
                return

        elif event.matches(QKeySequence.Copy):
            self.clipboard_lore = []
            for item in self.scene.selectedItems():
                if isinstance(item, LoreCard):
                    self.clipboard_lore.append({
                        'type': 'text', 'x': item.x(), 'y': item.y(),
                        'width': item.custom_width,
                        'markdown': item.text_item.raw_markdown 
                    })
                elif isinstance(item, ImageLoreCard):
                    self.clipboard_lore.append({
                        'type': 'image', 'x': item.x(), 'y': item.y(),
                        'filename': item.filename,
                        'width': item.target_width,
                        'height': item.target_height 
                    })
            return 
            
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if not self.scene.focusItem():
                selected = self.scene.selectedItems()
                if selected:
                    from PySide6.QtWidgets import QMessageBox
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Destroy Cards")
                    msg.setText(f"Delete {len(selected)} lore card(s) permanently?")
                    msg.setInformativeText("Image attachments on disk will NOT be deleted.")
                    msg.setStyleSheet("QMessageBox { background-color: #1a1a1a; color: #cccccc; } QPushButton { background-color: #333; color: #fff; padding: 5px 15px; border: none; font-weight: bold; } QPushButton[text='Yes'] { background-color: #ff5555; }")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.setDefaultButton(QMessageBox.No)

                    if msg.exec() == QMessageBox.Yes:
                        for item in selected:
                            if isinstance(item, (LoreCard, ImageLoreCard)):
                                self.scene.removeItem(item)
            return

        super().keyPressEvent(event)

    def export_canvas_data(self):
        data = []
        for item in self.scene.items():
            if isinstance(item, LoreCard):
                data.append({
                    'type': 'text', 'x': item.x(), 'y': item.y(),
                    'width': item.custom_width,
                    'markdown': item.text_item.raw_markdown 
                })
            elif isinstance(item, ImageLoreCard):
                data.append({
                    'type': 'image', 'x': item.x(), 'y': item.y(),
                    'filename': item.filename,
                    'width': item.target_width,
                    'height': item.target_height 
                })
        return json.dumps(data)

    def import_canvas_data(self, json_string):
        self.scene.clear()
        if not json_string.strip(): return
        
        vault_root = self._get_vault_root()

        try:
            data = json.loads(json_string)
            for card_data in data:
                card_type = card_data.get('type', 'text')
                
                if card_type == 'text':
                    card = LoreCard(card_data['x'], card_data['y'], card_data['width'], card_data.get('markdown', ''))
                    self.scene.addItem(card)
                elif card_type == 'image' and vault_root:
                    card = ImageLoreCard(card_data['x'], card_data['y'], card_data['filename'], vault_root, card_data.get('width'), card_data.get('height'))
                    self.scene.addItem(card)
        except Exception:
            pass

    def load_file(self, file_path):
        self.current_file_path = file_path
        self.scene.blockSignals(True) 
        with open(file_path, 'r', encoding='utf-8') as f:
            self.import_canvas_data(f.read())
        self.scene.blockSignals(False) 

    def auto_save(self, *args):
        if self.current_file_path:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(self.export_canvas_data())

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0: self.zoom_in()
            else: self.zoom_out()
        else:
            super().wheelEvent(event)

    def zoom_in(self): self.scale(1.15, 1.15)
    def zoom_out(self): self.scale(0.85, 0.85)
    def zoom_reset(self): self.resetTransform()


class ImageLoreCard(QGraphicsPixmapItem):
    def __init__(self, x, y, filename, vault_root, target_w=None, target_h=None):
        self.filename = filename
        self.filepath = os.path.join(vault_root, "_attachments", filename)
        
        if os.path.exists(self.filepath):
            self.original_pixmap = QPixmap(self.filepath)
        else:
            self.original_pixmap = QPixmap(200, 200)
            self.original_pixmap.fill(QColor("#1a1a1a"))
            
        super().__init__()
        
        self.setPos(x, y)
        self.setZValue(1) 
        
        self.aspect_ratio = self.original_pixmap.width() / max(1, self.original_pixmap.height())
        
        self.target_width = target_w if target_w else self.original_pixmap.width()
        self.target_height = target_h if target_h else self.original_pixmap.height()
        
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        
        self.resize_handle = QGraphicsRectItem(self)
        self.resize_handle.setBrush(QBrush(QColor("#5bc0de")))
        self.resize_handle.setPen(Qt.NoPen)
        self.resize_handle.setCursor(Qt.SizeFDiagCursor)
        self.resizing = False
        
        self._apply_scale()
        
    def _apply_scale(self):
        self.target_width = max(30, self.target_width)
        self.target_height = max(30, self.target_height)
        
        scaled = self.original_pixmap.scaled(self.target_width, self.target_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        
        self.resize_handle.setRect(self.target_width - 10, self.target_height - 10, 10, 10)

    def itemChange(self, change, value):
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor("#a3be8c"), 3, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#333333")))
            painter.drawRect(0, 0, self.boundingRect().width(), min(self.boundingRect().height() * 0.05, 15))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.resize_handle.rect().contains(event.pos()):
            self.resizing = True
            event.accept()
            return
        elif event.button() == Qt.RightButton:
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QAction
            menu = QMenu()
            menu.setStyleSheet("""
                QMenu { background-color: #262626; color: #cccccc; border: 1px solid #333; border-radius: 4px; font-family: "iA Writer Quattro S"; font-size: 12px;}
                QMenu::item { padding: 8px 25px; }
                QMenu::item:selected { background-color: #a3be8c; color: #1a1a1a; }
            """)
            locate_action = QAction("Open Folder (Locate File)", menu)
            locate_action.triggered.connect(lambda: os.startfile(os.path.dirname(self.filepath)))
            menu.addAction(locate_action)
            menu.exec(QCursor.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            new_w = max(50, event.pos().x())
            self.target_width = new_w
            self.target_height = new_w / self.aspect_ratio
            self._apply_scale()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            if self.scene() and self.scene().views():
                self.scene().views()[0].auto_save()
        else:
            super().mouseReleaseEvent(event)