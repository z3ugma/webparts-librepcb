import os
import logging
from typing import List

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
    QVBoxLayout, QHeaderView
)
from PySide6.QtUiTools import QUiLoader

from library_manager import LibraryManager
from models.library_part import LibraryPart
from models.status import StatusValue
from .part_info_widget import PartInfoWidget
from .hero_image_widget import HeroImageWidget
from models.elements import LibrePCBElement
from constants import WebPartsFilename, UIText

logger = logging.getLogger(__name__)


class LibraryTreeWidget(QTreeWidget):
    """Custom QTreeWidget that can detect clicks in empty areas"""
    clicked_empty_area = Signal()
    
    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item is None:
            self.clearSelection()
            self.setCurrentItem(None)
            self.clicked_empty_area.emit()
        super().mousePressEvent(event)


class LibraryPartLite:
    """Lightweight summary of a LibraryPart for fast loading."""
    __slots__ = ("uuid", "vendor", "part_name", "lcsc_id", "description", "status_flags", "hero_path")

    def __init__(self, uuid: str, vendor: str, part_name: str, lcsc_id: str, description: str, status_flags: dict, hero_path: str):
        self.uuid = uuid
        self.vendor = vendor
        self.part_name = part_name
        self.lcsc_id = lcsc_id
        self.description = description
        self.status_flags = status_flags
        self.hero_path = hero_path


class LibraryLoaderWorker(QObject):
    parts_loaded = Signal(list)
    load_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.manager = LibraryManager()

    def load_parts(self):
        try:
            parts_lite = []
            for part in self.manager.get_all_parts():
                flags = {
                    "footprint": part.status.footprint.value,
                    "symbol": part.status.symbol.value,
                    "component": part.status.component.value,
                    "device": part.status.device.value,
                }
                hero = LibrePCBElement.PACKAGE.dir.parent / "webparts" / part.uuid / WebPartsFilename.HERO_IMAGE.value
                parts_lite.append(LibraryPartLite(
                    part.uuid, part.vendor, part.part_name, part.lcsc_id, 
                    part.description, flags, str(hero)
                ))
            self.parts_loaded.emit(parts_lite)
        except Exception as e:
            logger.error("Library loading failed", exc_info=True)
            self.load_failed.emit(str(e))


class PartHydratorWorker(QObject):
    hydration_ready = Signal(object, str)  # (part, uuid) to identify which row to update
    hydration_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.manager = LibraryManager()

    def hydrate(self, lite: LibraryPartLite):
        try:
            all_parts = self.manager.get_all_parts()
            part = next((p for p in all_parts if p.uuid == lite.uuid), None)
            if not part:
                raise FileNotFoundError(f"Part manifest not found: {lite.uuid}")
            
            pixmap = QPixmap()
            if lite.hero_path and os.path.exists(lite.hero_path):
                pixmap.load(lite.hero_path)
            part._hero_pixmap = pixmap
            
            # Emit both the part data AND the UUID to identify which tree row to update
            self.hydration_ready.emit(part, lite.uuid)
        except Exception as e:
            logger.error(f"❌ Part hydration failed for {lite.uuid}: {e}", exc_info=True)
            self.hydration_failed.emit(str(e))


class LibraryPage(QWidget):
    go_to_search_requested = Signal()
    edit_part_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        loader = QUiLoader()
        loader.registerCustomWidget(PartInfoWidget)
        loader.registerCustomWidget(HeroImageWidget)
        ui_file = os.path.join(os.path.dirname(__file__), "page_library.ui")
        ui = loader.load(ui_file, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(ui)

        self.tree: QTreeWidget = ui.findChild(QTreeWidget, "libraryTree")
        self.search_button: QPushButton = ui.findChild(QPushButton, "go_to_search_button")
        self.edit_part_button: QPushButton = ui.findChild(QPushButton, "edit_part_button")
        self.select_none_button: QPushButton = ui.findChild(QPushButton, "select_none_button")
        self.hero_image_widget: HeroImageWidget = ui.findChild(HeroImageWidget, "hero_image_widget")
        self.part_info_widget: PartInfoWidget = ui.findChild(PartInfoWidget, "part_info_widget")
        self.label_3dModelStatus = ui.findChild(QLabel, 'label_3dModelStatus')
        self.datasheetLink = ui.findChild(QLabel, 'datasheetLink')
        
        if self.tree:
            custom_tree = LibraryTreeWidget()
            custom_tree.setObjectName("libraryTree")
            custom_tree.setHeaderLabels(["Vendor", "Part Name", "LCSC ID", "Description", "Footprint", "Symbol", "Component", "Device"])
            custom_tree.setColumnCount(8)
            header = custom_tree.header()
            header.setStretchLastSection(True)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            custom_tree.setColumnWidth(0, 120)
            custom_tree.setColumnWidth(1, 150)
            custom_tree.setColumnWidth(2, 80)
            custom_tree.setColumnWidth(4, 80)
            custom_tree.setColumnWidth(5, 80)
            custom_tree.setColumnWidth(6, 90)
            parent_layout = self.tree.parentWidget().layout()
            tree_index = parent_layout.indexOf(self.tree)
            parent_layout.insertWidget(tree_index, custom_tree)
            parent_layout.removeWidget(self.tree)
            self.tree.deleteLater()
            self.tree = custom_tree

        self.loader_thread = QThread()
        self.loader_worker = LibraryLoaderWorker()
        self.loader_worker.moveToThread(self.loader_thread)
        self.loader_worker.parts_loaded.connect(self.on_parts_loaded)
        self.loader_worker.load_failed.connect(lambda err: logger.error(f"Load failed: {err}"))
        self.loader_thread.started.connect(self.loader_worker.load_parts)

        self.hydrator_thread = QThread()
        self.hydrator_worker = PartHydratorWorker()
        self.hydrator_worker.moveToThread(self.hydrator_thread)
        self.hydrator_worker.hydration_ready.connect(self.on_hydration_ready)
        self.hydrator_worker.hydration_failed.connect(lambda err: logger.error(f"Hydration failed: {err}"))
        self.hydrator_thread.start()

        if self.search_button:
            self.search_button.clicked.connect(self.go_to_search_requested)
        if self.edit_part_button:
            self.edit_part_button.clicked.connect(self.on_edit_part_clicked)
        if self.select_none_button:
            self.select_none_button.clicked.connect(self.clear_selection)
        if self.tree:
            self.tree.currentItemChanged.connect(self.on_tree_selection_changed)
            self.tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
            if hasattr(self.tree, 'clicked_empty_area'):
                self.tree.clicked_empty_area.connect(self.on_empty_area_clicked)

        self.current_selected_part = None
        self.last_hydration_request_uuid = None
        self.refresh_library()

    def refresh_library(self):
        if not self.loader_thread.isRunning():
            self.loader_thread.start()

    def clear_selection(self):
        self.current_selected_part = None
        if self.tree:
            self.tree.clearSelection()
            self.tree.setCurrentItem(None)
        if self.hero_image_widget:
            self.hero_image_widget.clear()
        if self.part_info_widget:
            try:
                self.part_info_widget.clear()
            except RuntimeError:
                logger.warning("PartInfoWidget already deleted, skipping clear()")
        if self.label_3dModelStatus:
            self.label_3dModelStatus.setText("3D Model: (Not found)")
        if self.datasheetLink:
            self.datasheetLink.setText('Datasheet: <a href="#">(Not available)</a>')
        if self.edit_part_button:
            self.edit_part_button.setEnabled(False)

    def on_parts_loaded(self, parts_lite: List[LibraryPartLite]):
        self.tree.clear()
        for lite in parts_lite:
            item = QTreeWidgetItem([
                lite.vendor, lite.part_name, lite.lcsc_id, lite.description,
                "", "", "", ""
            ])
            item.setData(0, Qt.UserRole, lite)
            for col, key in enumerate(['footprint', 'symbol', 'component', 'device'], start=4):
                status_value = lite.status_flags.get(key)
                if status_value == "approved":
                    icon = StatusValue.APPROVED.icon
                elif status_value == "unavailable":
                    icon = StatusValue.UNAVAILABLE.icon
                elif status_value == "needs_review":
                    icon = StatusValue.NEEDS_REVIEW.icon
                else:
                    icon = StatusValue.ERROR.icon
                    
                item.setText(col, icon)
            self.tree.addTopLevelItem(item)
        self.loader_thread.quit()

    def on_tree_selection_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        if current:
            lite: LibraryPartLite = current.data(0, Qt.UserRole)
            logger.debug(f"🖱️ Selected {lite.lcsc_id} - triggering fresh disk read")
            
            # Track the latest request
            self.last_hydration_request_uuid = lite.uuid
                
            if self.hero_image_widget:
                self.hero_image_widget.show_loading()
            if self.part_info_widget:
                try:
                    self.part_info_widget.clear()
                except RuntimeError:
                    logger.warning("PartInfoWidget already deleted, skipping clear()")
            if self.label_3dModelStatus:
                self.label_3dModelStatus.setText(UIText.LOADING.value)
            if self.datasheetLink:
                self.datasheetLink.setText(f'Datasheet: <a href="#">({UIText.LOADING.value})</a>')
            if self.edit_part_button:
                self.edit_part_button.setEnabled(True)
            self.hydrator_worker.hydrate(lite)
        else:
            logger.debug(f"🔄 Deselected row - clearing sidebar")
            self.clear_selection()

    def on_hydration_ready(self, part, hydrated_uuid: str):
        """Handle hydration completion and update the specific tree row by UUID."""
        logger.debug(f"💧 Hydration complete for {part.lcsc_id} (UUID: {hydrated_uuid})")
        
        # Only update sidebar if this hydration matches the *last user request*
        if self.last_hydration_request_uuid == hydrated_uuid:
            logger.info(f"✅ Hydration matches last request. Updating sidebar for {part.lcsc_id}")
            self.current_selected_part = part
            pixmap = getattr(part, '_hero_pixmap', None)
            if self.hero_image_widget:
                if isinstance(pixmap, QPixmap) and not pixmap.isNull():
                    self.hero_image_widget.show_pixmap(pixmap)
                else:
                    self.hero_image_widget.show_no_image()
            if self.part_info_widget:
                self.part_info_widget.set_component(part)
            if self.label_3dModelStatus:
                self.label_3dModelStatus.setText("3D Model: Found" if part.has_3d_model else "3D Model: Not Found")
            if self.datasheetLink:
                if part.datasheet_url:
                    self.datasheetLink.setText(f'<a href="{part.datasheet_url}">Open Datasheet</a>')
                else:
                    self.datasheetLink.setText("Datasheet: Not Available")
            if self.edit_part_button:
                self.edit_part_button.setEnabled(True)
        else:
            logger.info(f"⚠️ Stale hydration received for {part.lcsc_id}. Ignoring sidebar update.")
        
        # ALWAYS update the tree icons for the specific row (by UUID) to allow "refresh on selection"
        target_item = self._find_tree_item_by_uuid(hydrated_uuid)
        if target_item:
            logger.debug(f"🔄 Updating tree icons for {part.lcsc_id} after fresh disk read")
            for col, key in enumerate(['footprint', 'symbol', 'component', 'device'], start=4):
                val = getattr(part.status, key)
                target_item.setText(col, val.icon)
        else:
            logger.warning(f"❌ Could not find tree item for UUID {hydrated_uuid}")

    def _find_tree_item_by_uuid(self, target_uuid: str) -> QTreeWidgetItem:
        """Find a tree item by its associated LibraryPartLite UUID."""
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            lite = item.data(0, Qt.UserRole)
            if lite and lite.uuid == target_uuid:
                return item
        return None

    def on_empty_area_clicked(self):
        self.clear_selection()

    def on_edit_part_clicked(self):
        logger.info(f"🖱️ Edit button clicked. Current selected part: {self.current_selected_part}")
        if self.current_selected_part:
            logger.info(f"🚀 Launching editor for {self.current_selected_part.lcsc_id}")
            self.edit_part_requested.emit(self.current_selected_part)
        else:
            logger.warning("❌ No part selected, cannot launch editor")

    def on_tree_item_double_clicked(self, item, column):
        self.on_edit_part_clicked()

    def cleanup(self):
        if self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait()
        if self.hydrator_thread.isRunning():
            self.hydrator_thread.quit()
            self.hydrator_thread.wait()
