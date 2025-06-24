import logging

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QMouseEvent, QNativeGestureEvent, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QLabel

log = logging.getLogger(__name__)


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
    - Panning with a two-finger trackpad gesture OR by dragging with the mouse.
    - Zooming with a pinch gesture OR a traditional mouse wheel.
    """

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        # Use ScrollHandDrag for mouse-based panning. Qt will automatically
        # translate two-finger trackpad gestures into this panning.
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setInteractive(True)
        # Hide the scrollbars so they don't clutter the UI.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._is_panning = False
        self._last_mouse_position = None
        self._initial_fit_done = False

    def event(self, event: QEvent) -> bool:
        """
        Overrides the base event handler to intercept native gesture events,
        specifically for handling pinch-to-zoom on macOS.
        """
        # # Log ALL events to see what's happening
        # if event.type() in [QEvent.Type.Wheel, QEvent.Type.NativeGesture,
        #                    QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
        #                    QEvent.Type.MouseMove]:
        #     log.debug(f"ZoomPanGraphicsView received event: {event.type()}")

        if event.type() == QEvent.Type.NativeGesture:
            # log.debug(f"Received native gesture event: {event.gestureType()}")
            if self.native_gesture_event(event):
                return True
        return super().event(event)

    def native_gesture_event(self, event: QNativeGestureEvent) -> bool:
        """Handles native gesture events, like pinch-to-zoom on macOS."""
        # log.debug(f"native_gesture_event called with {event.gestureType()}")
        if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
            # log.debug(f"Handling ZoomNativeGesture with value: {event.value()}")
            # --- Common setup for calculating min scale ---
            scene_rect = self.scene().itemsBoundingRect()
            if scene_rect.isEmpty():
                return True  # Nothing to zoom

            view_rect = self.viewport().rect()
            h_scale = (
                view_rect.width() / scene_rect.width() if scene_rect.width() > 0 else 1
            )
            v_scale = (
                view_rect.height() / scene_rect.height()
                if scene_rect.height() > 0
                else 1
            )
            fit_scale = min(h_scale, v_scale)
            # --- End common setup ---

            # value() for ZoomNativeGesture is a percentage delta, not a scale factor.
            # Convert percentage to scale factor: 1% zoom = 1.01 scale factor
            # Amplify by 250x for more responsive zooming
            zoom_factor = 1.0 + (
                event.value() * 2.5
            )  # Was /100.0, now *2.5 for 250x amplification
            # log.debug(f"Converted zoom factor: {zoom_factor}")

            if zoom_factor != 1.0:
                if zoom_factor < 1:  # Zooming out
                    # Prevent zooming out beyond the initial fit-in-view size
                    if self.transform().m11() * zoom_factor < fit_scale:
                        self.fitInView(scene_rect, Qt.KeepAspectRatio)
                        return True
                self.scale(zoom_factor, zoom_factor)
            return True
        return False

    def wheelEvent(self, event: QWheelEvent):
        """
        Handles mouse wheel for zooming and trackpad scrolling for panning.
        A pinch gesture is handled by native_gesture_event on supported platforms (macOS).
        """
        # log.debug(f"ZoomPanGraphicsView wheelEvent triggered. angleDelta=({event.angleDelta().x()}, {event.angleDelta().y()}), pixelDelta=({event.pixelDelta().x()}, {event.pixelDelta().y()}), source={event.source()}")
        # --- Common setup for calculating min scale ---
        scene_rect = self.scene().itemsBoundingRect()
        if scene_rect.isEmpty():
            event.accept()
            return

        view_rect = self.viewport().rect()
        h_scale = (
            view_rect.width() / scene_rect.width() if scene_rect.width() > 0 else 1
        )
        v_scale = (
            view_rect.height() / scene_rect.height() if scene_rect.height() > 0 else 1
        )
        fit_scale = min(h_scale, v_scale)
        # --- End common setup ---

        # Check if this is a synthesized event (trackpad on macOS)
        if event.source() == Qt.MouseEventSource.MouseEventSynthesizedBySystem:
            # Trackpad event - use for panning
            if not event.pixelDelta().isNull():
                delta = event.pixelDelta()
                # log.debug(
                #     f"Wheel event (trackpad pan): pixelDelta=({delta.x()}, {delta.y()})"
                # )

                # Get current scrollbar values
                h_before = self.horizontalScrollBar().value()
                v_before = self.verticalScrollBar().value()

                # Apply the delta
                self.horizontalScrollBar().setValue(h_before - delta.x())
                self.verticalScrollBar().setValue(v_before - delta.y())

                # Log the change
                # h_after = self.horizontalScrollBar().value()
                # v_after = self.verticalScrollBar().value()
                # log.debug(
                #     f"Scrollbar values: H({h_before}->{h_after}), V({v_before}->{v_after})"
                # )

                event.accept()
                return

        # Not a synthesized event - it's a real mouse wheel, use for zoom
        if not event.angleDelta().isNull():
            angle = event.angleDelta()
            # log.debug(f"Wheel event (mouse zoom): angleDelta={angle.y()}")

            # Use LibrePCB's approach: scale based on angle delta
            zoom_factor = pow(1.15, angle.y() / 120.0)

            if zoom_factor < 1:  # Zooming out
                if self.transform().m11() * zoom_factor < fit_scale:
                    self.fitInView(scene_rect, Qt.KeepAspectRatio)
                else:
                    self.scale(zoom_factor, zoom_factor)
            else:  # Zooming in
                self.scale(zoom_factor, zoom_factor)

            event.accept()
            return

        super().wheelEvent(event)

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
