import logging
from .zoom_pan_image_text_widget import ZoomPanImageAndTextWidget
import constants as const

logger = logging.getLogger(__name__)


class HeroImageWidget(ZoomPanImageAndTextWidget):
    def __init__(self, parent=None):
        super().__init__(parent, zoom_factor=1.5)
        self.view.setMinimumHeight(250)
        self.clear()  # Set initial state
        logger.info("HeroImageWidget (subclassed) created.")

    def show_loading(self):
        self.show_text(const.UIText.LOADING.value)

    def show_no_image(self):
        self.show_text(const.UIText.NO_IMAGE.value)

    def show_image_not_available(self):
        self.show_text(const.UIText.IMAGE_NOT_AVAILABLE.value)

    def clear(self):
        super().clear(default_text=const.UIText.SELECT_PART.value)

