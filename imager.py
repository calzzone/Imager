# builtin libs
import sys, subprocess, os
import threading, time

# PyQt5 libs
from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QPainter
# from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# custom libs
import misc #import Signal, Ticker, ShellCommandsRunner
from preview_widget2 import PreviewWidget
from curves_widget import CurvesWidget

import numpy as np

class Ui_MainWindow(QMainWindow):

    ticker = None
    threadpool = QThreadPool()

    frame_taker = None
    threadpool2 = QThreadPool()

    image_list_index = -1
    image_list = []

    def __init__(self, app):
        super(Ui_MainWindow, self).__init__()
        self.app = app
        self.setupUi()



    def setupUi(self):
        self.setWindowTitle("Imager") # MainWindow
        self.resize(640, 480) # MainWindow

        # self.menubar =

        self.centralwidget = QtWidgets.QWidget(self) # QWidget(MainWindow)
        self.setCentralWidget(self.centralwidget) # ? move to very end ? # MainWindow
        self.mainLayout = QtWidgets.QHBoxLayout(self.centralwidget)

        self.init_left()
        self.init_right()

        self.cw.setPreviewer(self.previewer)

        # menubar
        self.menubar = QtWidgets.QMenuBar(self)
        # self.menubar.setGeometry(QtCore.QRect(0, 0, 684, 27))
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setTitle("File")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setTitle("Settings")
        self.actionClose = QtWidgets.QAction(self)
        self.actionClose.setText("Close")
        self.menuFile.addAction(self.actionClose)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.setMenuBar(self.menubar)

        #statusbar
        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

        # make sure to kill all threads
        quit = QAction("Quit", self)
        quit.triggered.connect(self.closeEvent)

        # start the threadpool for tje ticker for continuous capture
        self.threadpool.start(self.ticker)


    # take control of closing the app
    # make sure to kill all sub-threads
    # there are still issues, but it's good enough for now
    def closeEvent(self, event):
        self.ticker.cancel()
        self.ticker.kill()

        try: self.frame_taker.cancel() # may be None
        except AttributeError: pass

        print("exitting")
        sys.exit()


    # Left pane:
    def init_left(self):
        # groupBox_config:
        #   verticalLayout_config:
        #       formLayout:
        #           ISO, Shutter, Format, Interval, Filename, Start At
        #       gridLayout_left_buttons:
        #           1 frame, continuous

        self.groupBox_config = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox_config.setTitle("Config")
        self.verticalLayout_config = QtWidgets.QVBoxLayout(self.groupBox_config)
        self.formLayout = QtWidgets.QFormLayout()

        # ISO
        self.label_2 = QtWidgets.QLabel(self.groupBox_config)
        self.label_2.setText("ISO")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.combo_iso = QtWidgets.QComboBox(self.groupBox_config)
        self.combo_iso.addItems(("Auto", "100", "200", "400", "800", "1600", "3200", "6400", "12800"))
        self.combo_iso.setCurrentText("1600")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.combo_iso)

        # Shutter
        self.label_3 = QtWidgets.QLabel(self.groupBox_config)
        self.label_3.setText("Shutter")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.combo_shutter = QtWidgets.QComboBox(self.groupBox_config)
        self.combo_shutter.addItems(("bulb", "30", "25", "20", "15", "13", "10.3", "8", "6.3", "5", "4", "3.2", "2.5", "2", "1.6", "1.3", "1", "0.8", "0.6", "0.5", "0.4", "0.3", "1/4", "1/5", "1/6", "1/8", "1/10", "1/13", "1/15", "1/20", "1/25", "1/30", "1/40", "1/50", "1/60", "1/80", "1/100", "1/125", "1/160", "1/200", "1/250", "1/320", "1/400", "1/500", "1/640", "1/800", "1/1000", "1/1250", "1/1600", "1/2000", "1/2500", "1/3200", "1/4000"))
        self.combo_shutter.setCurrentText("1")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.combo_shutter)

        # File Format
        self.label_4 = QtWidgets.QLabel(self.groupBox_config)
        self.label_4.setText("Format")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_4)
        self.combo_format = QtWidgets.QComboBox(self.groupBox_config)
        self.combo_format.addItems(("jpg", "cr2.tiff", "cr2"))
        self.combo_format.setCurrentText("cr2.tiff")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.combo_format)

        # Interval
        self.label_5 = QtWidgets.QLabel(self.groupBox_config)
        self.label_5.setText("Interval")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_5)
        self.spin_interval = QtWidgets.QDoubleSpinBox(self.groupBox_config)
        self.spin_interval.setValue(1)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.spin_interval)

        # Subfolder
        self.label_6 = QtWidgets.QLabel(self.groupBox_config)
        self.label_6.setText("Subfolder")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.label_6)
        self.line_subfolder = QtWidgets.QLineEdit(self.groupBox_config)
        self.line_subfolder.setText("Frames")
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.line_subfolder)

        # Filename
        self.label_7 = QtWidgets.QLabel(self.groupBox_config)
        self.label_7.setText("Filename")
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.label_7)
        self.line_filename = QtWidgets.QLineEdit(self.groupBox_config)
        self.line_filename.setText("capture_")
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.line_filename)

        # Start numbering at
        self.label_8 = QtWidgets.QLabel(self.groupBox_config)
        self.label_8.setText("Number")
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.LabelRole, self.label_8)
        self.spin_start = QtWidgets.QSpinBox(self.groupBox_config)
        self.spin_start.setMinimum(1)
        self.spin_start.setMaximum(999999999) # many digits, to make the box wider
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.spin_start)

        # end configs
        self.verticalLayout_config.addLayout(self.formLayout)

        # curves
        self.cw = CurvesWidget(self.groupBox_config)
        self.verticalLayout_config.addWidget(self.cw)

        # left buttons
        self.gridLayout_left_buttons = QtWidgets.QGridLayout()

        self.button_1frame = QtWidgets.QPushButton(self.groupBox_config)
        self.button_1frame.setText("1 frame")
        self.button_1frame.clicked.connect(self.button_1frame_clicked)
        self.gridLayout_left_buttons.addWidget(self.button_1frame, 0, 0, 1, 1)

        self.button_continuous = QtWidgets.QPushButton(self.groupBox_config)
        self.button_continuous.setText("Start capture")
        self.button_continuous.setCheckable(True)
        self.button_continuous.setChecked(False)
        self.button_continuous.clicked.connect(self.button_continuous_clicked)
        self.ticker = misc.Ticker(self.spin_interval.value())
        self.ticker.signal.signal.connect(self.take_frame)
        # self.threadpool.start(self.ticker)
        self.gridLayout_left_buttons.addWidget(self.button_continuous, 0, 1, 1, 1)

        self.verticalLayout_config.addLayout(self.gridLayout_left_buttons)

        # end left pane
        self.mainLayout.addWidget(self.groupBox_config, 0, QtCore.Qt.AlignLeft)

    # Right pane:
    def init_right(self):

        # groupBox_preview:
        #   verticalLayout_right:
        #       scrollArea: scrollAreaWidgetContents: scrollAreaWidgetContentsLayout
        #           previewer
        #       right_buttons_layout:
        #           prev, next, sep, grid, 100%, fit

        self.groupBox_preview = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox_preview.setTitle("Preview")
        self.verticalLayout_right = QtWidgets.QVBoxLayout(self.groupBox_preview)

        # self.scrollArea = QtWidgets.QScrollArea(self.groupBox_preview)
        # self.scrollArea.setWidgetResizable(True)
        # self.scrollArea.setAlignment(QtCore.Qt.AlignCenter)
        # self.scrollAreaWidgetContents = QtWidgets.QWidget()
        # # self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 640, 480))
        #
        # self.scrollAreaWidgetContentsLayout = QtWidgets.QHBoxLayout(self.scrollAreaWidgetContents)
        # # self.last_photo_pixmap = QtGui.QPixmap("IMG_0197.JPG")
        # # self.previewer = PreviewWidget(self.scrollAreaWidgetContents, self.last_photo_pixmap)
        # self.previewer = PreviewWidget(self.scrollAreaWidgetContents, "IMG_0147.JPG")
        # # self.previewer.resize(self.scrollAreaWidgetContents.size())
        # self.scrollAreaWidgetContentsLayout.addWidget(self.previewer)
        #
        # self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        # self.verticalLayout_right.addWidget(self.scrollArea)


        self.previewer_frame = QtWidgets.QFrame(self.groupBox_preview)
        self.previewer_frame_Layout = QtWidgets.QHBoxLayout(self.previewer_frame)
        self.previewer = PreviewWidget(self.previewer_frame, "IMG_0147.JPG")
        self.previewer_frame_Layout.addWidget(self.previewer)
        self.verticalLayout_right.addWidget(self.previewer_frame)

        # right buttons
        self.right_buttons_layout = QtWidgets.QHBoxLayout()

        self.pushButton_prev = QtWidgets.QPushButton(self.groupBox_preview)
        self.pushButton_prev.setText("<")
        self.pushButton_prev.clicked.connect(self.pushButton_prev_clicked)
        self.right_buttons_layout.addWidget(self.pushButton_prev)

        self.pushButton_next = QtWidgets.QPushButton(self.groupBox_preview)
        self.pushButton_next.setText(">")
        self.pushButton_next.clicked.connect(self.pushButton_next_clicked)
        self.right_buttons_layout.addWidget(self.pushButton_next)

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.right_buttons_layout.addItem(spacerItem)

        self.pushButton_list = QtWidgets.QPushButton(self.groupBox_preview)
        self.pushButton_list.setText("Show data")
        #self.pushButton_list.setCheckable(True)
        #self.pushButton_list.setChecked(False)
        self.pushButton_list.clicked.connect(self.pushButton_list_clicked)
        self.right_buttons_layout.addWidget(self.pushButton_list)

        self.pushButton_grid = QtWidgets.QPushButton(self.groupBox_preview)
        self.pushButton_grid.setText("Grid")
        self.pushButton_grid.setCheckable(True)
        self.pushButton_grid.setChecked(False)
        self.pushButton_grid.clicked.connect(self.pushButton_grid_clicked)
        self.right_buttons_layout.addWidget(self.pushButton_grid)

        self.pushButton_zoom = QtWidgets.QPushButton(self.groupBox_preview)
        self.pushButton_zoom.setText("100%")
        self.pushButton_zoom.clicked.connect(self.pushButton_zoom_clicked)
        self.right_buttons_layout.addWidget(self.pushButton_zoom)

        self.pushButton_fit = QtWidgets.QPushButton(self.groupBox_preview)
        self.pushButton_fit.setText("Fit")
        self.pushButton_fit.clicked.connect(self.pushButton_fit_clicked)
        self.right_buttons_layout.addWidget(self.pushButton_fit)

        # end right buttons
        self.verticalLayout_right.addLayout(self.right_buttons_layout)

        # end right pane
        self.mainLayout.addWidget(self.groupBox_preview)

    def take_frame(self):
        # print("take_frame 0")
        if self.ticker.is_busy: return()
        # print("take_frame 1")

        self.subfolder = self.line_subfolder.text() + "/"
        # number = self.spin_start.value()
        self.filename = f"{self.line_filename.text()}{self.spin_start.value():05d}.{self.combo_format.currentText()}"
        iso = f"--set-config-value iso={self.combo_iso.currentText()}"
        shutter = f"--set-config-value shutterspeed={self.combo_shutter.currentText()}"
        cmds = [f"gphoto2 {iso} {shutter} --filename={self.subfolder}{self.filename} --force-overwrite --port usb --capture-image-and-download"]
        # cmds.append("sleep 2")
        # cmds.append("convert Frames/capture_2*.tiff -gravity center -crop 600x440+0+0 +repage result.jpg")

        self.ticker.busy()
        # self.button_1frame.setEnabled(False)
        # self.button_continuous.setEnabled(False)
        self.statusBar().showMessage('Capturing...')
        self.app.processEvents()

        self.frame_taker = misc.ShellCommandsRunner(cmds)
        self.frame_taker.signal.signal.connect(self.frame_taken)
        self.frame_taker.start() # just mark it internally as able to run
        self.threadpool2.start(self.frame_taker)


    def frame_taken(self):
        ts = time.time()

        self.ticker.is_busy = False
        self.button_1frame.setEnabled(True)
        self.button_continuous.setEnabled(True)
        self.statusBar().showMessage('Ready')

        if self.filename in os.listdir(self.subfolder):
            try:
                # load the image file into the previewer
                # the previewer reads it, makes an in-memory copy and displays it
                # pass a downsampled in-memory image to the curves widget
                # the curves widget knows about the previewer and tells it to color-transform the image according to curves

                self.previewer.setImage(self.subfolder + self.filename)
                # self.cw.setImage(self.subfolder + self.filename) # don't read twice

                image_for_curves = self.previewer.getImageForCurves()
                self.cw.setImage(image_for_curves)

                self.image_list.append(self.subfolder + self.filename)
                self.image_list_index = len(self.image_list)-1

            except Exception as e:
                print("error reading frame:", e)

        self.spin_start.setValue(self.spin_start.value()+1)
        self.ticker.setInteval(self.spin_interval.value())

        te = time.time()
        print ('%r  %2.2f ms' % ("frame_taken", (te - ts) * 1000))


    def button_1frame_clicked(self):
        # print ("button_1frame_clicked")
        self.take_frame()

    def button_continuous_clicked(self):
        # print ("button_continuous_clicked")
        # self.threadpool.start(self.ticker)

        if self.ticker.is_active:
            self.ticker.cancel()
            self.button_continuous.setText("Resume capture")
        else:
            self.ticker.setInteval(self.spin_interval.value())
            self.ticker.start()
            self.button_continuous.setText("Recording...")



    def pushButton_prev_clicked(self):
        print ("pushButton_prev_clicked", self.image_list_index, self.image_list)
        self.image_list_index -= 1
        if self.image_list_index < 0: self.image_list_index = len(self.image_list)-1
        print ("pushButton_prev_clicked", self.image_list_index, self.image_list)
        image = self.image_list[self.image_list_index]

        self.previewer.setImage(image)
        #image_for_curves = self.previewer.getImageForCurves()
        #self.cw.setImage(image_for_curves)



    def pushButton_next_clicked(self):
        print ("pushButton_next_clicked", self.image_list_index, self.image_list)
        self.image_list_index += 1
        if self.image_list_index >= len(self.image_list): self.image_list_index = 0
        print ("pushButton_next_clicked", self.image_list_index, self.image_list)
        image = self.image_list[self.image_list_index]

        self.previewer.setImage(image)
        #image_for_curves = self.previewer.getImageForCurves()
        #self.cw.setImage(image_for_curves)

    def pushButton_list_clicked(self):
        # print ("pushButton_list_clicked", self.pushButton_grid.isChecked())
        self.previewer.listCircleData()

    def pushButton_grid_clicked(self):
        # print ("pushButton_grid_clicked", self.pushButton_grid.isChecked())
        self.previewer.setGrid(self.pushButton_grid.isChecked())

    def pushButton_fit_clicked(self):
        # print ("pushButton_fit_clicked")
        self.previewer.setZoomFit()

    def pushButton_zoom_clicked(self):
        # print ("pushButton_zoom_clicked")
        self.previewer.setZoom100()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Ui_MainWindow(app)
    win.show()#Maximized()
    sys.exit(app.exec_())
    print("here 4")
