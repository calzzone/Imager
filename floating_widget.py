import sys

from PyQt5 import QtCore, QtWidgets

# from https://www.deskriders.dev/posts/007-pyqt5-overlay-button-widget/


class FloatingQComboBoxWidget(QtWidgets.QComboBox):

    padding = 5

    def __init__(self, parent):
        super().__init__(parent)
        self.addItems(("Master", "?", "FOX", "CMP", "VAN", "GEN", "MTZ"))
        self.setCurrentText("?")

    def update_position(self):
        if hasattr(self.parent(), 'viewport'):
            parent_rect = self.parent().viewport().rect()
        else:
            parent_rect = self.parent().rect()

        if not parent_rect:
            return

        self.setPosition(self.padding, self.padding)

    def setPosition(self, x, y):
        self.setGeometry(x + self.padding, y + self.padding,
                         self.width() + self.padding, self.height() + self.padding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_position()


