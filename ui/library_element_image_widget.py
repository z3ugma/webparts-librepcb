import logging
from .zoom_pan_image_text_widget import ZoomPanImageAndTextWidget

logger = logging.getLogger(__name__)


class LibraryElementImageWidget(ZoomPanImageAndTextWidget):
    def __init__(self, parent=None):
        # Library elements should just fit the view without extra zoom.
        super().__init__(parent, zoom_factor=1.0)
        logger.debug("LibraryElementImageWidget created.")
