import sys, subprocess, os, threading, time, cv2
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

import numpy as np
from scipy.interpolate import interp1d
from PIL import Image
from rawkit.raw import Raw
import rawpy, imageio
from skimage import io

from sortedcontainers import SortedDict

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui



class RadiusChangedEvent(QtCore.QObject):
    sig_masterRadiusChanged = QtCore.pyqtSignal(int)


# based on https://github.com/abhilb/pyqtgraphutils
class CircleItem(pg.GraphicsObject):

    MASTER_SCALED_RADIUS = 45 # petri dishes are 100 mm diameter
    is_master = False
    picture = None
    is_selected = True
    is_hidden = False
    master_radius = 275 # px of the photograph
    scaled_radius = 0 # mm IRL
    accent_color = 'r'
    clickable = True
    label = "fas"

    def __init__(self):
        pg.GraphicsObject.__init__(self)
        self.radiusChanged = RadiusChangedEvent()


    def setData(self, center, radius_point, angle_span=90):
        self.center = center
        self.radius_point = radius_point
        self.radius = np.sqrt((radius_point[0]-center[0])**2+(radius_point[1]-center[1])**2)
        self.angle = np.arctan2(radius_point[0]-center[0], radius_point[1]-center[1]) * 180 / np.pi
        # print("radius", self.radius, self.center, self.radius_point, self.angle)
        self.angle_span = angle_span


        # R/MR = SR / SMR
        # SR = R*SMR/MR
        # self.scaled_radius = self.MASTER_SCALED_RADIUS * self.radius / self.master_radius


        # self.textItem = QtGui.QGraphicsTextItem(self) #QGraphicsSimpleTextItem
        #self.textItem.setParentItem(self)
        #self.color = QtGui.QColor(255, 0, 0)
        #self.textItem.setDefaultTextColor(self.color)
        #self.textItem.setFont(QtGui.QFont("Arial", 15, QtGui.QFont.Bold))

        #self.generatePicture()


    def clear(self):
        self.picture = None

    def hide(self):
        if self.is_hidden == False:
            self.is_hidden = True
            self.picture = None
            self.update()

    def show(self):
        if self.is_hidden == True:
            self.is_hidden = False
            self.generatePicture()

    def select(self, is_selected = True):
        self.is_selected = is_selected
        if not self.picture is None:
            self.generatePicture()

    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setRenderHint(p.RenderHint.Antialiasing, True)
        #self.label = f"{self.center}: {round(self.radius, 1)} px = {round(self.scaled_radius, 1)} mm"

        if self.is_selected:
            p.setPen(pg.mkPen('w'))
            p.drawEllipse(QtCore.QPoint(self.center[0], self.center[1]), self.radius, self.radius)
            p.setPen(pg.mkPen(self.accent_color))
            p.drawLine(QtCore.QPoint(self.center[0], self.center[1]), QtCore.QPoint(self.radius_point[0], self.radius_point[1]))

        p.setPen(pg.mkPen(color=self.accent_color, width=3))
        p.drawArc(int(self.center[0]-self.radius),
                  int(self.center[1]-self.radius),
                  int(self.radius*2),
                  int(self.radius*2),
                  int((self.angle-90-self.angle_span/2)*16),
                  int(self.angle_span*16) )

        if self.is_selected:
            p.setPen(pg.mkPen(self.accent_color))
            p.setFont(QtGui.QFont("Arial", 18, QtGui.QFont.Bold))
        else:
            p.setPen(pg.mkPen('w'))
            p.setFont(QtGui.QFont("Arial", 13))

        text = f"{self.label}: {round(self.scaled_radius, 1)} mm"
        p.drawText(self.center[0]+10, self.center[1]+5, text)




        #self.textItem.setPlainText(str(self.center)+": " + str(round(self.radius, 1)))
        #self.textItem.setPos(pg.Point(self.center[0], self.center[1]))
        #self.textItem.update()
        #p.drawPolygon(self.textItem.mapToParent(self.textItem.boundingRect()))


        p.end()
        self.update()




    def paint(self, p, *args):
        if self.picture is None: return
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        if self.picture is None: return QtCore.QRectF(0, 0, 0, 0)
        return QtCore.QRectF(self.picture.boundingRect())

    def angle_between(self, angle0, angle1, angle_span):
        # print("angle_between", angle0, angle1, angle_span)
        if angle0 < angle1-angle_span/2: return False
        if angle0 > angle1+angle_span/2: return False
        return True

    def mouseClickEvent(self, event):
        print("mouseClickEvent, circle")
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return

        pos = event.pos()
        coords = (int(pos[0]), int(pos[1]))

        # not this circle
        dist = np.sqrt((coords[0]-self.center[0])**2+(coords[1]-self.center[1])**2)
        angle = np.arctan2(coords[0]-self.center[0], coords[1]-self.center[1]) * 180 / np.pi
        #print("dragging from point", self.center, coords, dist, self.radius, abs(dist-self.radius))
        if abs(dist-self.radius)>5 or not self.angle_between(angle, self.angle, self.angle_span):
            print("ignore click", dist, self.radius)
            event.ignore()
            return()

        self.select(not self.is_selected)
        event.accept()

    def mouseDragEvent(self, event):
        # print("mouseDragEvent, circle")
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return

        if event.isStart():
            print("start drag circle edge")
            pos = event.buttonDownPos()
            coords = (int(pos[0]), int(pos[1]))

            # not this circle
            dist = np.sqrt((coords[0]-self.center[0])**2+(coords[1]-self.center[1])**2)
            angle = np.arctan2(coords[0]-self.center[0], coords[1]-self.center[1]) * 180 / np.pi
            #print("dragging from point", self.center, coords, dist, self.radius, abs(dist-self.radius))
            if abs(dist-self.radius)>5 or not self.angle_between(angle, self.angle, self.angle_span):
                event.ignore()
                print("ignore drag", dist, self.radius)
                return()


            self.dragPoint = coords
            self.select(True)
            #event.accept()

        elif event.isFinish():
            print("end drag circle")
            #if self.is_master:
            self.radiusChanged.sig_masterRadiusChanged.emit(self.radius)
            self.dragPoint = None
            self.select(False)
            #event.accept()

        else:
            if self.dragPoint is None:
                event.ignore()
                return

            pos2 = event.pos()
            coords2 = (int(pos2[0]), int(pos2[1]))
            self.dragPoint = coords2
            self.setData(self.center, coords2, self.angle_span)
            # self.generatePicture()

            #if self.is_master:
                #self.radiusChanged.sig_masterRadiusChanged.emit(self.radius)

            #event.accept()
        self.generatePicture()
        self.update()
        #self.generatePicture()
        #self.update()
        event.accept()



class MasterCircleItem(CircleItem):
    is_master = True
    accent_color = 'b'
    label = "Master"

    def __init__(self):
        CircleItem.__init__(self)

    def setData(self, center, radius_point, angle_span=90):
        CircleItem.setData(self, center, radius_point, angle_span)
        self.master_radius = self.radius
        self.scaled_radius = self.MASTER_SCALED_RADIUS
        self.generatePicture()

class RegularCircleItem(CircleItem):
    is_master = False
    accent_color = 'r'
    label = "?"

    def __init__(self):
        CircleItem.__init__(self)

    def setData(self, center, radius_point, angle_span=90):
        CircleItem.setData(self, center, radius_point, angle_span)
        self.scaled_radius = self.MASTER_SCALED_RADIUS * self.radius / self.master_radius
        self.generatePicture()

    def update_master_radius(self, master_radius):
        self.master_radius = master_radius
        self.scaled_radius = self.MASTER_SCALED_RADIUS * self.radius / self.master_radius
        self.generatePicture()
