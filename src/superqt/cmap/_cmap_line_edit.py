from __future__ import annotations

from cmap import Colormap
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon, QPainter, QPaintEvent, QPalette
from qtpy.QtWidgets import QApplication, QLineEdit, QStyle, QWidget

from ._cmap_utils import draw_colormap, pick_font_color, try_cast_colormap

MISSING = QStyle.StandardPixmap.SP_TitleBarContextHelpButton


class QColormapLineEdit(QLineEdit):
    """A QLineEdit that shows a colormap swatch.

    When the current text is a valid colormap name from the `cmap` package, a swatch
    of the colormap will be shown to the left of the text (if `fractionalColormapWidth`
    is less than .75) or behind the text (for when the colormap fills the full width).

    If the current text is not a valid colormap name, a swatch of the fallback colormap
    will be shown instead (by default, a gray colormap) if `fractionalColormapWidth` is
    less than .75.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget.
    fractional_colormap_width : float, optional
        The fraction of the widget width to use for the colormap swatch. If the
        colormap is full width (greater than 0.75), the swatch will be drawn behind
        the text. Otherwise, the swatch will be drawn to the left of the text.
        Default is 0.33.
    fallback_cmap : Colormap | str | None, optional
        The colormap to use when the current text is not a recognized colormap.
        by default "gray".
    missing_icon : QIcon | QStyle.StandardPixmap, optional
        The icon to show when the current text is not a recognized colormap and
        `fractionalColormapWidth` is less than .75. Default is a question mark.
    checkerboard_size : int, optional
        Size (in pixels) of the checkerboard pattern to draw behind colormaps with
        transparency, by default 4. If 0, no checkerboard is drawn.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        fractional_colormap_width: float = 0.33,
        fallback_cmap: Colormap | str | None = "gray",
        missing_icon: QIcon | QStyle.StandardPixmap = MISSING,
        checkerboard_size: int = 4,
    ) -> None:
        super().__init__(parent)
        self.setFractionalColormapWidth(fractional_colormap_width)
        self.setMissingColormap(fallback_cmap)
        self._checkerboard_size = checkerboard_size

        if isinstance(missing_icon, QStyle.StandardPixmap):
            self._missing_icon: QIcon = self.style().standardIcon(missing_icon)
        elif isinstance(missing_icon, QIcon):
            self._missing_icon = missing_icon
        else:  # pragma: no cover
            raise TypeError("missing_icon must be a QIcon or QStyle.StandardPixmap")

        self._cmap: Colormap | None = None  # current colormap
        self.textChanged.connect(self.setColormap)

    def setFractionalColormapWidth(self, fraction: float) -> None:
        self._colormap_fraction: float = float(fraction)
        align = Qt.AlignmentFlag.AlignVCenter
        if self._cmap_is_full_width():
            align |= Qt.AlignmentFlag.AlignCenter
        else:
            align |= Qt.AlignmentFlag.AlignLeft
        self.setAlignment(align)

    def fractionalColormapWidth(self) -> float:
        return self._colormap_fraction

    def setMissingColormap(self, cmap: Colormap | str | None) -> None:
        self._missing_cmap: Colormap | None = try_cast_colormap(cmap)

    def colormap(self) -> Colormap | None:
        return self._cmap

    def setColormap(self, cmap: Colormap | str | None) -> None:
        self._cmap = try_cast_colormap(cmap)

        # set self font color to contrast with the colormap
        if self._cmap and self._cmap_is_full_width():
            text = pick_font_color(self._cmap)
        else:
            text = QApplication.palette().color(QPalette.ColorRole.Text)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Text, text)
        self.setPalette(palette)

    def _cmap_is_full_width(self):
        return self._colormap_fraction >= 0.75

    def paintEvent(self, e: QPaintEvent) -> None:
        # don't draw the background
        # otherwise it will cover the colormap during super().paintEvent
        # FIXME: this appears to need to be reset during every paint event...
        # otherwise something is resetting it
        palette = self.palette()
        palette.setColor(palette.ColorRole.Base, Qt.GlobalColor.transparent)
        self.setPalette(palette)

        cmap_rect = self.rect().adjusted(2, 0, 0, 0)
        cmap_rect.setWidth(int(cmap_rect.width() * self._colormap_fraction))

        left_margin = 6
        if not self._cmap_is_full_width():
            # leave room for the colormap
            left_margin += cmap_rect.width()
        self.setTextMargins(left_margin, 2, 0, 0)

        if self._cmap:
            draw_colormap(
                self, self._cmap, cmap_rect, checkerboard_size=self._checkerboard_size
            )
        elif not self._cmap_is_full_width():
            if self._missing_cmap:
                draw_colormap(self, self._missing_cmap, cmap_rect)
            self._missing_icon.paint(QPainter(self), cmap_rect.adjusted(4, 4, 0, -4))

        super().paintEvent(e)  # draw text (must come after draw_colormap)
