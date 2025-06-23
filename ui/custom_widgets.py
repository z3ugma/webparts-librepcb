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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        # Calculate the minimum 'fit-in-view' scale
        scene_rect = self.scene().itemsBoundingRect()
        if scene_rect.isEmpty():
            # Nothing to zoom, so just accept the event
            event.accept()
            return

        view_rect = self.viewport().rect()
        h_scale = view_rect.width() / scene_rect.width() if scene_rect.width() > 0 else 1
        v_scale = (
            view_rect.height() / scene_rect.height() if scene_rect.height() > 0 else 1
        )
        fit_scale = min(h_scale, v_scale)

        # Differentiate between trackpad and mouse wheel
        if not event.pixelDelta().isNull():  # Trackpad
            if abs(event.pixelDelta().y()) > abs(event.pixelDelta().x()):  # Zooming
                zoom_factor = 1 + event.pixelDelta().y() / 360.0
                if zoom_factor < 1:  # Zooming out
                    # If applying zoom_factor would make it too small, snap to fit
                    if self.transform().m11() * zoom_factor < fit_scale:
                        self.fitInView(scene_rect, Qt.KeepAspectRatio)
                        return
                self.scale(zoom_factor, zoom_factor)
            else:  # Panning
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() - event.pixelDelta().x()
                )
        elif not event.angleDelta().isNull():  # Mouse Wheel
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor
            if event.angleDelta().y() > 0:  # Zooming in
                self.scale(zoom_in_factor, zoom_in_factor)
            else:  # Zooming out
                if self.transform().m11() * zoom_out_factor < fit_scale:
                    self.fitInView(scene_rect, Qt.KeepAspectRatio)
                else:
                    self.scale(zoom_out_factor, zoom_out_factor)
        else:
            event.accept()

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
