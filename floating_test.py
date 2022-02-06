
# from # from https://www.deskriders.dev/posts/007-pyqt5-overlay-button-widget/

import sys

from PyQt5 import QtCore
from PyQt5 import QtWidgets


class FloatingQComboBoxWidget(QtWidgets.QComboBox):

    def __init__(self, parent):
        super().__init__(parent)
        self.paddingLeft = 5
        self.paddingTop = 5
        self.addItems(("Master", "?", "FOX", "CMP", "VAN", "GEN", "MTZ"))
        self.setCurrentText("Master")

    def update_position(self):
        if hasattr(self.parent(), 'viewport'):
            parent_rect = self.parent().viewport().rect()
        else:
            parent_rect = self.parent().rect()

        if not parent_rect:
            return

        x = parent_rect.width() - self.width() - self.paddingLeft
        y = self.paddingTop
        self.setGeometry(x, y, self.width(), self.height())
        #print(x, y)

    def setPosition(self, x, y):
        self.setGeometry(x, y, self.width(), self.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_position()

    #def mousePressEvent(self, event):
        #self.parent().floatingButtonClicked.emit()

class FloatingButtonWidget(QtWidgets.QPushButton):

    def __init__(self, parent):
        super().__init__(parent)
        self.paddingLeft = 5
        self.paddingTop = 5

    def update_position(self):
        if hasattr(self.parent(), 'viewport'):
            parent_rect = self.parent().viewport().rect()
        else:
            parent_rect = self.parent().rect()

        if not parent_rect:
            return

        x = parent_rect.width() - self.width() - self.paddingLeft
        y = self.paddingTop
        self.setGeometry(x, y, self.width(), self.height())
        print(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_position()

    def mousePressEvent(self, event):
        self.parent().floatingButtonClicked.emit()


class OverlayedPlainTextEdit(QtWidgets.QPlainTextEdit):
    floatingButtonClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.floating_button = FloatingButtonWidget(parent=self)

    def update_floating_button_text(self, txt):
        self.floating_button.setText(txt)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.floating_button.update_position()


# NOTE: This class is generated from QtDesigner
class Ui_DebugWindow(object):
    def setupUi(self, DebugWindow):
        DebugWindow.setObjectName("DebugWindow")
        DebugWindow.resize(622, 498)
        self.centralwidget = QtWidgets.QWidget(DebugWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.plainTextEdit = OverlayedPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.verticalLayout.addWidget(self.plainTextEdit)
        DebugWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(DebugWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 622, 22))
        self.menubar.setObjectName("menubar")
        DebugWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(DebugWindow)
        self.statusbar.setObjectName("statusbar")
        DebugWindow.setStatusBar(self.statusbar)

        self.retranslateUi(DebugWindow)
        QtCore.QMetaObject.connectSlotsByName(DebugWindow)

    def retranslateUi(self, DebugWindow):
        _translate = QtCore.QCoreApplication.translate
        DebugWindow.setWindowTitle(_translate("DebugWindow", "MainWindow"))


class DebugWindow(QtWidgets.QMainWindow, Ui_DebugWindow):
    edit_mode = True

    def __init__(self, parent=None):
        super(DebugWindow, self).__init__(parent)
        self.setupUi(self)
        # ui events
        self.plainTextEdit.floatingButtonClicked.connect(self.on_test)
        self.update_floating_button_text()

    def on_test(self):
        self.edit_mode = not self.edit_mode
        self.plainTextEdit.appendPlainText("Button Clicked - Mode: {}".format("Edit" if self.edit_mode else "Preview"))
        self.update_floating_button_text()

    def update_floating_button_text(self):
        if self.edit_mode:
            self.plainTextEdit.update_floating_button_text("Edit")
        else:
            self.plainTextEdit.update_floating_button_text("Preview")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = DebugWindow()
    window.show()
    sys.exit(app.exec_())
