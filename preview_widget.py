import sys, subprocess, os, threading, time, cv2
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

import numpy as np
from scipy.interpolate import interp1d
from PIL import Image
from skimage import io

from sortedcontainers import SortedDict

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
pg.setConfigOptions(antialias=True)
pg.setConfigOption('leftButtonPan', False)

def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print ('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed

class PreviewWidget(pg.MultiPlotWidget):
    grid = True
    transform = np.array([x for x in range(256)]).astype("uint8")

    def __init__(self, parent=None, image_filename="Untitled.png"):
        pg.MultiPlotWidget.__init__(self, parent=parent)
        self.parent = parent
        # _in_data = Image.open(self.image_filename)

        self.v = self.addPlot()
        self.v.setMenuEnabled(False)
        # self.v.hideButtons()
        self.v.setAspectLocked()
        self.v.hideAxis("bottom")
        self.v.hideAxis("left")
        self.v.showGrid(x=False, y=False, alpha=1)
        self.v.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        self.imageItem = pg.ImageItem(axisOrder='row-major')#, autoLevels=False, lut=self.transform)
        # self.imageItem.setLookupTable(self.transform)
        # self.imageItem.setLevels([0, 255])
        self.v.addItem(self.imageItem)
        self.v.invertY()

        # histo = image_item.getHistogram()
        # self.v.addLine(angle=45, pen=pg.mkPen("r", width=0.5))

        self.setImage(image_filename)
        self.v.setRange(xRange=[0,self.image.shape[1]],
                        yRange=[0, self.image.shape[0]],
                        padding=0.0)

        self.gridItem1 = pg.PlotCurveItem()
        self.gridItem2 = pg.PlotCurveItem()
        self.v.addItem(self.gridItem1)
        self.v.addItem(self.gridItem2)

    # @timeit
    def setImage(self, image_filename):
        # print(image_filename)
        # image_filename = "/home/calzzone/Documents/Imager/eclipse/capture_00001.cr2.tiff"
        self.image_filename = image_filename
        self.original_image = cv2.imread(self.image_filename, cv2.IMREAD_UNCHANGED)

        # cv2.imshow('image', self.original_image)
        # print("reading", image_filename)
        # self.original_image = io.imread(self.image_filename)
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

        if not self.transform is None:
            self.applyColorTransform()

        # print(self.transform)
        # self.imageItem.setLookupTable(self.transform)

        # self.imageItem.setImage(self.image, lut=self.transform)
        self.imageItem.setImage(self.image)


    def getImageForCurves(self):
        scale_percent = 10 # percent of original size
        width = int(img.shape[1] * scale_percent / 100)
        height = int(img.shape[0] * scale_percent / 100)
        dim = (width, height)
        # dim = (300, 300)

        # resize image
        resized = cv2.resize(self.original_image, dim) #, interpolation = cv2.INTER_AREA)
        return resized

    def setZoomFit(self):
        self.v.setRange(xRange=[0,self.image.shape[1]],
                        yRange=[0, self.image.shape[0]],
                        padding=0.0)

    def setZoom100(self):
        center = (self.image.shape[1]/2, self.image.shape[0]/2)
        crop_size = (self.parent.size().width()/2, self.parent.size().height()/2)

        self.v.setRange(xRange=[center[0]-crop_size[0], center[0]+crop_size[0]],
                        yRange=[center[1]-crop_size[1], center[1]+crop_size[1]],
                        padding=0.0)

    def setGrid(self, grid=True):
        if grid is None: grid = self.grid
        else: self.grid = grid

        if grid:
            center = (self.image.shape[1]/2, self.image.shape[0]/2)
            rect_size = (self.image.shape[1]/4, self.image.shape[0]/4)
            xs = [center[0]-rect_size[0], center[0]+rect_size[0], center[0]+rect_size[0], center[0]-rect_size[0], center[0]-rect_size[0] ]
            ys = [center[1]-rect_size[1], center[1]-rect_size[1], center[1]+rect_size[1], center[1]+rect_size[1], center[1]-rect_size[1] ]
            self.gridItem1.setData(x=xs, y=ys)

            rect_size = min(self.image.shape[1], self.image.shape[0])/20
            xs = [center[0], center[0]+rect_size, center[0], center[0]-rect_size, center[0] ]
            ys = [center[1]-rect_size, center[1], center[1]+rect_size, center[1], center[1]-rect_size ]
            self.gridItem2.setData(x=xs, y=ys)
        else:
            self.gridItem1.clear()
            self.gridItem2.clear()

    def applyColorTransform(self):
        if self.transform is None: return()
        try: self.image = cv2.LUT(self.original_image, self.transform)
        except: return()


    def setColorTransform(self, transform):
        self.transform = transform
        # self.imageItem.setLookupTable(self.transform)

        self.applyColorTransform()
        self.imageItem.setImage(self.image)
