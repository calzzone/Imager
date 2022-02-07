import sys
import subprocess
import os
import threading
import time
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

import numpy as np
from scipy.interpolate import interp1d
from PIL import Image
from rawkit.raw import Raw
import rawpy
import imageio
from skimage import io

import circle_item as CI
import handle_points_graph as HPG
import misc

import floating_widget as FW

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
pg.setConfigOptions(antialias=True)
pg.setConfigOption('leftButtonPan', False)
#pg.setConfigOption('mouseRateLimit', 60) # default: 100
# useCupy = False
# useNumba = False


class PreviewWidget(pg.MultiPlotWidget):
    grid = True
    transform = np.array([x for x in range(256)]).astype("uint8")
    floating_button = None

    def __init__(self, parent=None, image_filename="Untitled.png"):
        pg.MultiPlotWidget.__init__(self, parent=parent)
        self.parent = parent
        # _in_data = Image.open(self.image_filename)

        # a combo box that lets me chose the circle label
        self.floating_widget = FW.FloatingQComboBoxWidget(self)
        self.floating_widget.setHidden(True)
        #self.floating_widget.update_position()

        # prepare axes
        self.v = self.addPlot()
        self.v.setMenuEnabled(False)
        # self.v.hideButtons()
        self.v.setAspectLocked()
        self.v.hideAxis("bottom")
        self.v.hideAxis("left")
        self.v.showGrid(x=False, y=False, alpha=1)
        self.v.invertY()
        self.v.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        # main plot: plot an image
        # , autoLevels=False, lut=self.transform)
        self.imageItem = pg.ImageItem(axisOrder='row-major')
        self.setImage(image_filename)
        # self.imageItem.setLookupTable(self.transform)
        # self.imageItem.setLevels([0, 255])
        self.v.addItem(self.imageItem)

        # histo = image_item.getHistogram()
        # self.v.addLine(angle=45, pen=pg.mkPen("r", width=0.5))

        # add a grid
        self.gridItem1 = pg.PlotCurveItem()
        self.gridItem2 = pg.PlotCurveItem()
        self.v.addItem(self.gridItem1)
        self.v.addItem(self.gridItem2)

        # add manual circles
        self.circles = {}
        self.master_circle = None
        self.g = HPG.HandlePointsGraph(main_plot=self.v,
                                       image_size=self.image.shape,
                                       circles=self.circles,
                                       master_circle=self.master_circle,
                                       floating_widget=self.floating_widget)

        self.v.addItem(self.g)

        # scale all to image dimensions
        self.v.setRange(xRange=[0, self.image.shape[1]],
                        yRange=[0, self.image.shape[0]],
                        padding=0.0)

    def resizeEvent(self, event):
        #pass
        super().resizeEvent(event)
        if hasattr(self.floating_button, 'update_position'):
            self.floating_button.update_position()

    # @misc.timeit
    def setImage(self, image_filename):
        # print(image_filename)
        # image_filename = "/home/calzzone/Documents/Imager/eclipse/capture_00001.cr2.tiff"
        self.image_filename = image_filename
        self.original_image = None
        if self.image_filename.endswith(".cr2") or self.image_filename.endswith(".cr2.tiff"):
            print("Warning: This is apparently a raw file.")
            self.original_image = cv2.imread(
                self.image_filename, cv2.IMREAD_UNCHANGED)
            if self.original_image is None:
                print("Warning: Trying to use rawpy to read it.")
                # https://pypi.org/project/rawpy/
                self.original_image = rawpy.imread(self.image_filename)
                self.original_image = self.original_image.postprocess()  # slow
                self.original_image = self.original_image[:, :, ::-1].copy()

        else:
            self.original_image = cv2.imread(
                self.image_filename, cv2.IMREAD_UNCHANGED)

        if self.original_image is None:
            print("Error: Could not read", self.image_filename)
            return

        self.original_image = cv2.cvtColor(
            self.original_image, cv2.COLOR_BGR2RGB)
        if self.original_image is None:
            print("Error: Could not color-convert", self.image_filename)
            return

        if self.transform is not None:
            self.applyColorTransform()

        # print(self.transform)
        # self.imageItem.setLookupTable(self.transform)

        # self.imageItem.setImage(self.image, lut=self.transform)
        self.imageItem.setImage(self.image)

    def getImageForCurves(self):

        if self.original_image is None:
            print("Error: Image is not loaded or is loaded with errors:",
                  self.image_filename)
            return

        scale_percent = 10  # percent of original size
        width = int(self.original_image.shape[1] * scale_percent / 100)
        height = int(self.original_image.shape[0] * scale_percent / 100)
        dim = (width, height)
        # dim = (300, 300)

        # resize image
        # , interpolation = cv2.INTER_AREA)
        resized = cv2.resize(self.original_image, dim)
        return resized

    def setZoomFit(self):
        self.v.setRange(xRange=[0, self.image.shape[1]],
                        yRange=[0, self.image.shape[0]],
                        padding=0.0)

    def setZoom100(self):
        center = (self.image.shape[1]/2, self.image.shape[0]/2)
        crop_size = (self.parent.size().width()/2,
                     self.parent.size().height()/2)

        self.v.setRange(xRange=[center[0]-crop_size[0], center[0]+crop_size[0]],
                        yRange=[center[1]-crop_size[1],
                                center[1]+crop_size[1]],
                        padding=0.0)

    def setGrid(self, grid=True):
        if grid is None:
            grid = self.grid
        else:
            self.grid = grid

        if grid:
            center = (self.image.shape[1]/2, self.image.shape[0]/2)
            rect_size = (self.image.shape[1]/4, self.image.shape[0]/4)
            xs = [center[0]-rect_size[0], center[0]+rect_size[0], center[0]
                  + rect_size[0], center[0]-rect_size[0], center[0]-rect_size[0]]
            ys = [center[1]-rect_size[1], center[1]-rect_size[1], center[1]
                  + rect_size[1], center[1]+rect_size[1], center[1]-rect_size[1]]
            self.gridItem1.setData(x=xs, y=ys)

            rect_size = min(self.image.shape[1], self.image.shape[0])/20
            xs = [center[0], center[0]+rect_size,
                  center[0], center[0]-rect_size, center[0]]
            ys = [center[1]-rect_size, center[1], center[1]
                  + rect_size, center[1], center[1]-rect_size]
            self.gridItem2.setData(x=xs, y=ys)

        else:
            self.gridItem1.clear()
            self.gridItem2.clear()

    def applyColorTransform(self):
        if self.transform is None:
            return()

        try:
            self.image = cv2.LUT(self.original_image, self.transform)
        except Exception as e:
            # print(e)
            return()

    def setColorTransform(self, transform):
        self.transform = transform
        # self.imageItem.setLookupTable(self.transform)

        self.applyColorTransform()
        self.imageItem.setImage(self.image)

    def listCircleData(self):
        if self.circles is None or len(self.circles) == 0:
            print("{no circles}")
            return {}

        circles_dict = {}
        for c in self.circles:
            circle = {"position": self.circles[c].center,
                      "edge":     self.circles[c].radius_point,
                      "radius":   self.circles[c].radius,
                      "angle":    self.circles[c].angle,
                      "arc span": self.circles[c].angle_span,
                      "selected": self.circles[c].is_selected,
                      "hidden":   self.circles[c].is_hidden,
                      "label":    self.circles[c].label
                      }

            circles_dict[c] = circle

        for c in circles_dict:
            print(c, ":", circles_dict[c])
        return circles_dict
