import sys, subprocess, os, threading, time, cv2
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

import numpy as np
from scipy.interpolate import interp1d
from PIL import Image

from sortedcontainers import SortedDict

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
pg.setConfigOptions(antialias=True)
pg.setConfigOption('leftButtonPan', False)

# a class to handle the curves graph
# clicking on an empty segment of the line adds a handlepoint
# doble clicking on a handlepoint deletes it
# handle points are placed on a separate graph (HandlePointsGraph())
class CurveGraph(pg.PlotCurveItem):

    previewer = None
    def __init__(self, previewer = None):
        pg.PlotCurveItem.__init__(self)
        self.clickable=True
        self.previewer = previewer

    def setData(self, **kwds):
        self.data = kwds
        self.data['pen']=pg.mkPen("w", width=2)
        self.data['pxMode']=True
        if 'handles' in self.data and len(self.data['handles'])>0:
            # handles_x = [x[0] for x in sorted(self.data['handles'].items())]
            handles_x = list(self.data['handles'].keys())
            # handles_y = [self.data['handles'][x[0]] for x in sorted(self.data['handles'].items())]
            handles_y = list(self.data['handles'].values())
            algo = 'cubic'
            if len(self.data['handles']) == 3: algo = "quadratic"
            elif len(self.data['handles']) == 2: algo = "linear"
            f2 = interp1d(handles_x, handles_y, kind=algo)
            xnew = np.linspace(0, 255, num=256, endpoint=True)
            ynew = f2(xnew)
            ynew[ynew>255] = 255
            ynew[ynew<0] = 0
            self.data['x'] = xnew
            self.data['y'] = ynew
        self.updateGraph()

    def updateGraph(self):
        pg.PlotCurveItem.setData(self, **self.data)
        if not self.previewer is None:
            # print('update')
            transform = self.data['y']
            transform = np.array(transform).astype("uint8")
            self.previewer.setColorTransform(transform)

    def mouseClickEvent(self, event):
        # print("mouseClickEvent")
        if not self.mouseShape().contains(event.pos()): return

        print("mouseClickEvent: clicked on the line")
        # points are 10 px diameter. euclidean distance < sqrt(25) means i clicked a point
        colision = {}
        for p in self.data["handles"]:
            distance = (p-event.pos()[0])**2+(self.data["handles"][p]-event.pos()[1])**2
            if distance <= 25:
                colision[distance] = p

        # print(colision, 'graph' in self.data, event.double())

        # option to delete a point
        if event.double() and 'graph' in self.data and len(colision) > 0:
            print("delete points: ", colision)
            for p in colision.values():
                if not p in (self.data['handles'].keys()[0], self.data['handles'].keys()[-1]):
                    self.data['graph'].data['handles'].pop(p)
            self.data['graph'].setData(**self.data['graph'].data)
            self.setData(**self.data)
            return

        # option to add a point
        if 'graph' in self.data and len(colision) == 0:
            print("add point", event.pos())
            # self.data['graph'].data['pos'] = np.vstack((self.data['graph'].data['pos'], (event.pos()[0], event.pos()[1])))
            self.data['graph'].data['handles'][event.pos()[0]] = event.pos()[1]
            self.data['graph'].setData(**self.data['graph'].data)
            # self.data['handles'][event.pos()[0]] = event.pos()[1]
            self.setData(**self.data)
            return

class HandlePointsGraph(pg.GraphItem):
    def __init__(self, curvesGraph):
        pg.GraphItem.__init__(self)
        self.ckickable = True
        self.dragPoint = None
        self.dragOffset = None
        self.marginalPoint = None # "left" / "right"; only move horizontally, between 0 and 255
        self.curvesGraph = curvesGraph

    def setData(self, **kwds):
        self.data = kwds
        self.data['size']=10
        self.data['pxMode']=True
        self.data['pen'] = None

        if 'handles' in self.data:
            npts = len(self.data['handles'])
            # self.data['x'] = list(self.data['handles'].keys())
            # self.data['y'] = list(self.data['handles'].values())
            self.data['pos'] = np.column_stack( (list(self.data['handles'].keys()), list(self.data['handles'].values())))
            self.data['adj'] = np.column_stack((np.arange(0, npts-1), np.arange(1, npts)))
            self.data['data'] = np.empty(npts, dtype=[('index', int)])
            self.data['data']['index'] = np.arange(npts)
            self.curvesGraph.setData(handles=self.data['handles'], graph=self)
        self.updateGraph()

    def updateGraph(self):
        pg.GraphItem.setData(self, **self.data)

    def mouseClickEvent(self, event):
        print("mouseClickEvent?")

    def mouseDragEvent(self, event):
        print("mouseDragEvent")
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return

        # if not self.dragPoint is None:
        #     print("dragging: ", self.dragPoint.data()[0])

        if event.isStart():
            pos = event.buttonDownPos()
            pts = self.scatter.pointsAt(pos)
            if len(pts) == 0:
                event.ignore()
                return

            self.dragPoint = pts[0]
            ind = pts[0].data()[0]
            if ind in [0, len(self.data['handles'])-1]:
                event.ignore()
                return

            key = self.data['handles'].keys()[ind]
            self.dragOffset = (self.data['handles'].keys()[ind] - pos[0], self.data['handles'][key] - pos[1])
            #print(self.dragOffset)

        elif event.isFinish():
            self.dragPoint = None
            self.marginalPoint = None
            return
        else:
            if self.dragPoint is None:
                event.ignore()
                return

            ind = self.dragPoint.data()[0]
            key = self.data['handles'].keys()[ind]
            pos = event.pos()

            if ind == 0:
                print("point left dragging")
                if pos[0] < 0: # too left
                    pos = (0, pos[1])
                    # event.ignore()
                    # return
                if pos[0] >= self.data['handles'].keys()[1]: # second point
                    pos = (self.data['handles'].keys()[1] - 1, pos[1])
                    # event.ignore()
                    # return

                pos = (pos[0], 0) # move only on the bottom line

            # elif ind == len(self.data['handles'])-1:
            #     print("point right dragging")
            #     pos = (pos[0], 255) # move only on the top line
            else:
                if pos[0] <= self.data['handles'].keys()[ind-1]:
                    p0 = pos
                    pos = (self.data['handles'].keys()[ind-1] + 1, pos[1])
                    print(ind, "left :", p0, "->", pos)
                    # event.ignore()
                    # return
                if pos[0] >= self.data['handles'].keys()[ind+1]:
                    p0 = pos
                    pos = (self.data['handles'].keys()[ind+1] - 1, pos[1])
                    print(ind, "right:", p0, "->", pos)
                    # event.ignore()
                    # return

                if pos[1] <= 0:
                    pos = (pos[0], 0)
                    # event.ignore()
                    # return
                if pos[1] >= 255:
                    pos = (pos[0], 255)
                    # event.ignore()
                    # return

            # self.data['pos'][ind][0] = event.pos()[0] + self.dragOffset[0]
            # self.data['pos'][ind][1] = event.pos()[1] + self.dragOffset[1]
            self.data["handles"].pop(key)
            self.data["handles"][pos[0] + self.dragOffset[0]] = pos[1] + self.dragOffset[1]
            self.data['pos'] = np.column_stack( (list(self.data['handles'].keys()), list(self.data['handles'].values())))
            # self.setData(**self.data)
            self.curvesGraph.setData(handles=self.data["handles"], graph=self)

        # print("moved point:", ind, self.data['pos'][ind][0], self.data['pos'][ind][1])
        self.updateGraph()
        event.accept()

class CurvesWidget(pg.MultiPlotWidget):
    previewer = None
    def __init__(self, parent=None, image=None):
        pg.MultiPlotWidget.__init__(self, parent=parent)
        self.image = image
        self.c = CurveGraph(previewer=self.previewer)
        self.g = HandlePointsGraph(self.c)
        self.v = self.addPlot()

        self.v.setMenuEnabled(False)
        self.v.hideButtons()
        self.v.setRange(xRange=[0,255], yRange=[0, 255], padding=0.01)
        # self.v.setAspectLocked()
        self.v.setMouseEnabled(x=False, y=False)
        ticks = [[(0, ""), (63, ""), (127, ""), (191, ""), (255, "")]]
        axes = {}
        for side in ("left", "right", "top", "bottom"):
            axes[side] = pg.AxisItem(side)
            axes[side].setTicks(ticks)
        self.v.setAxisItems(axes)

        self.v.showGrid(x=True, y=True, alpha=0.25)
        self.v.addLine(angle=45, pen=pg.mkPen("w", width=0.25))
        self.v.getViewBox().setMouseMode(pg.ViewBox.PanMode)



        self.histo_red = pg.PlotCurveItem(antialias=True, pen=pg.mkPen("r"))
        self.histo_green = pg.PlotCurveItem(antialias=True, pen=pg.mkPen("g"))
        self.histo_blue = pg.PlotCurveItem(antialias=True, pen=pg.mkPen("b"))

        self.v.addItem(self.histo_red)
        self.v.addItem(self.histo_green)
        self.v.addItem(self.histo_blue)


        self.v.addItem(self.c) # curves
        self.v.addItem(self.g) # handle points
        # handles = {p[0]:p[1] for p in points}
        # c.setData( handles=handles, size=10, pxMode=True)
        # points = [(0, 0), (50, 30), (128, 128), (200, 220), (255, 255), (150, 80)]
        points = [(0, 0), (255, 255)]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        pos = np.column_stack((xs,ys))
        handles = SortedDict({p[0]:p[1] for p in points})
        self.g.setData(handles = handles)

    # PIL version
    # def get_histogram_data(self, image):
    #     frequencies = image.histogram()
    #     max_freq = max(frequencies)
    #
    #     normalized_frequencies = {"red": [256*f / max_freq for f in frequencies[0:256]],
    #                               "green": [256*f / max_freq for f in frequencies[256:512]],
    #                               "blue": [256*f / max_freq for f in frequencies[512:768]]}
    #
    #     return (normalized_frequencies)

    def get_histogram_data(self, image):
        normalized_frequencies={}
        color = ('blue','green','red') # converted to RGB!

        red = cv2.calcHist([image],[0],None,[256],[0,256])[:, 0]
        red = np.log(red)
        # print(red)
        green = cv2.calcHist([image],[1],None,[256],[0,256])[:, 0]
        green = np.log(green)
        # print(green)
        blue = cv2.calcHist([image],[2],None,[256],[0,256])[:, 0]
        blue = np.log(blue)
        max_freq = max(np.max(red), np.max(green), np.max(blue))

        normalized_frequencies = {"red": red*256/max_freq,
                                  "green": green*256/max_freq,
                                  "blue": blue*256/max_freq}

        return (normalized_frequencies)

    def setPreviewer(self, previewer):
        self.previewer = previewer
        self.c.previewer = self.previewer

    def setImage(self, image):
        self.image = image

        # _in_data = Image.open(self.image_filename)
        # if _in_data.  mode == "RGB":
        # _in_data = cv2.imread(self.image_filename)

        normalized_frequencies = self.get_histogram_data(self.image)
        # print("blue", normalized_frequencies["blue"])

        self.histo_red.setData(y = normalized_frequencies["red"])
        self.histo_green.setData(y = normalized_frequencies["green"])
        self.histo_blue.setData(y = normalized_frequencies["blue"])
