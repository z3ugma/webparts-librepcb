from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QLabel


class ClickableLabel(QLabel):
    """
    A custom QLabel that emits signals for clicks and double-clicks.
    """

    clicked = Signal()
    doubleClicked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event: QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class ZoomPanGraphicsView(QGraphicsView):
    """
    A QGraphicsView that supports:
    - Panning with a two-finger trackpad gesture OR by dragging with the middle mouse button.
    - Zooming with a pinch gesture OR a traditional mouse wheel.
    """

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setInteractive(True)
        self._is_panning = False
        self._last_mouse_position = None
        self._initial_fit_done = False

    def resizeEvent(self, event):
        """Override resizeEvent to perform the initial fit-in-view."""
        super().resizeEvent(event)
        if not self._initial_fit_done and self.scene() and self.scene().items():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)
            self._initial_fit_done = True

    def setScene(self, scene: QGraphicsScene):
        """Reset the initial fit flag when the scene changes."""
        self._initial_fit_done = False
        super().setScene(scene)

    def wheelEvent(self, event: QWheelEvent):
        """Handles mouse wheel and trackpad gestures for zooming and panning."""
        # Differentiate between zoom (vertical) and pan (horizontal) on trackpads
        if not event.pixelDelta().isNull():
            # It's a trackpad
            if abs(event.pixelDelta().y()) > abs(event.pixelDelta().x()):
                # Vertical scroll is dominant: Zoom
                if event.pixelDelta().y() < 0 and self._is_at_minimum_zoom():
                    return  # Prevent zooming out further
                zoom_factor = 1 + event.pixelDelta().y() / 360.0
                self.scale(zoom_factor, zoom_factor)
            else:
                # Horizontal scroll is dominant: Pan
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() - event.pixelDelta().x()
                )
                self.verticalScrollBar().setValue(
                    self.verticalScrollBar().value() - event.pixelDelta().y()
                )
        elif not event.angleDelta().isNull():
            # It's a traditional mouse wheel: Zoom only
            if event.angleDelta().y() < 0 and self._is_at_minimum_zoom():
                return  # Prevent zooming out further

            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor
            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
        else:
            event.accept()

    def _is_at_minimum_zoom(self) -> bool:
        """Checks if the view is at or below the 'fit in view' zoom level."""
        if not self.scene() or not self.scene().items():
            return True

        current_scale = self.transform().m11()

        view_rect = self.viewport().rect()
        scene_rect = self.scene().itemsBoundingRect()

        if scene_rect.isEmpty() or scene_rect.width() == 0 or scene_rect.height() == 0:
            return True

        h_scale = view_rect.width() / scene_rect.width()
        v_scale = view_rect.height() / scene_rect.height()
        fit_scale = min(h_scale, v_scale)

        # Use a small tolerance for floating point comparisons
        return current_scale <= fit_scale + 0.001

    def mousePressEvent(self, event: QMouseEvent):
        """Initiates panning with the left mouse button."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = True
            self._last_mouse_position = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Performs panning if the left mouse button is held down."""
        if self._is_panning:
            delta = event.pos() - self._last_mouse_position
            self._last_mouse_position = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Stops the panning operation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
