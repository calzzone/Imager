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

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


class HandlePointsGraph(pg.GraphItem):
    #circles = {}
    clickable = True
    dragPoint = None
    currentCircle = None  # the circle currently primed to be named by the comobox

    def __init__(self, main_plot, image_size, circles, master_circle=None, floating_widget=None):
        pg.GraphItem.__init__(self)
        self.main_plot = main_plot
        self.floating_widget = floating_widget
        self.floating_widget.activated[str].connect(self.onComboChanged)
        self.size = (image_size[1], image_size[0])
        self.master_circle = master_circle
        self.circles = circles
        self.setData(coords=[(0, 0), self.size])
        self.scatter.sigClicked.connect(self.mouseClickEvent_scatter)

    def setData(self, **kwds):
        self.data = kwds
        self.data['size'] = 10
        self.data['pxMode'] = True
        self.data['pen'] = None

        if 'coords' in self.data:
            npts = len(self.data['coords'])
            xs = [c[0] for c in self.data['coords']]
            ys = [c[1] for c in self.data['coords']]
            self.data['pos'] = np.column_stack((xs, ys))
            self.data['adj'] = np.column_stack(
                (np.arange(0, npts-1), np.arange(1, npts)))
            self.data['data'] = np.empty(npts, dtype=[('index', int)])
            self.data['data']['index'] = np.arange(npts)
        self.updateGraph()

    def updateGraph(self):
        # update superclass' data
        pg.GraphItem.setData(self, **self.data)

    # double click a point do delete
    def mouseDoubleClickEvent(self, event):
        print("mouseDoubleClickEvent")
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return

        pos = event.pos()
        pts = self.scatter.pointsAt(event.pos())
        if len(pts) == 0:  # no point
            event.ignore()
            return

        point = (int(pts[0].pos()[0]), int(pts[0].pos()[1]))
        if point in [self.data['coords'][:2]]:
            print("can't delete image corners")
            event.ignore()
            return

        # self.circles[point].clear()
        if not point in self.circles:
            print(point, "Trying to delete a point that does not exist")
            event.ignore()
            return None

        self.main_plot.removeItem(self.circles[point])
        self.circles.pop(point)
        self._update_data()
        self.updateGraph()
        event.accept()

    def onComboChanged(self, text):
        if self.currentCircle is None:
            return
        if not self.currentCircle in self.circles:
            return

        self.circles[self.currentCircle].label = text
        self.circles[self.currentCircle].generatePicture()
        self.circles[self.currentCircle].update()

        # reset; another event will be generated but ignored because self.currentCircle is None
        self.floating_widget.setHidden(True)
        self.currentCircle = None
        self.floating_widget.setCurrentText("?")

    # click to select

    def mouseClickEvent(self, event):
        print("mouseClickEvent, scene")
        # left click on an empty area: cleanup
        # right click on a point: show combo

        pos = event.pos()
        pts = self.scatter.pointsAt(event.pos())
        if len(pts) == 0:  # no point
            if event.button() == QtCore.Qt.LeftButton:
                # cleanup
                event.accept()
                self.floating_widget.setHidden(True)
                self.currentCircle = None
                self._update_data()
                self.updateGraph()
            else:
                event.ignore()

            return

        # right click on a point: show combo
        if event.button() != QtCore.Qt.RightButton:
            event.ignore()
            return

        self.floating_widget.setHidden(True)
        self.currentCircle = None

        point = (int(pts[0].pos()[0]), int(pts[0].pos()[1]))
        # circle = self.getCircleAt(point)
        if point in [self.data['coords'][:2]]:
            print("can't select image corners")
            event.ignore()
            return

        if not point in self.circles:
            print(point, "Trying to select a point that does not exist")
            event.ignore()
            return None

        pos2 = event.scenePos()
        combo_coords = (int(pos2.x()), int(pos2.y()))
        self.floating_widget.setPosition(combo_coords[0], combo_coords[1])
        self.floating_widget.setHidden(False)

        self.currentCircle = point
        self.getCircleAt(point).select(True)

        self._update_data()
        self.updateGraph()
        event.accept()

    # click a point to select it

    def mouseClickEvent_scatter(self, sender, points):
        print("mouseClickEvent, scatter")

        if len(points) == 0:
            return
        point = (int(points[0].pos()[0]), int(points[0].pos()[1]))
        circle = self.getCircleAt(point)
        if circle is None:
            return
        circle.select(not circle.is_selected)

        pos2 = points[0].viewPos()
        combo_coords = (int(pos2.x()), int(pos2.y()))
        self.floating_widget.setPosition(combo_coords[0], combo_coords[1])

        self._update_data()
        self.updateGraph()

    def mouseDragEvent(self, event):
        print("custom HandlePointsGraph mouseDragEvent")
        if event.button() != QtCore.Qt.LeftButton:
            event.ignore()
            return

        if event.isStart():
            print("start drag")
            pos = event.buttonDownPos()
            coords = (int(pos[0]), int(pos[1]))
            pts = self.scatter.pointsAt(pos)

            if len(pts) > 0:  # existing point
                ind = pts[0].data()[0]
                # if temp_point in [self.data['coords'][:2]]:
                if ind in [0, 1]:
                    print("can't drag image corners")
                    event.ignore()
                    return

                self.newPoint = False
                self.dragPoint = (int(pts[0].pos()[0]), int(pts[0].pos()[1]))
                self.dragOrigin = self.dragPoint
                self.getCircleAt(self.dragOrigin).select(True)

            else:  # this is a new circle: add it, track it
                self.newPoint = True
                self.dragPoint = coords
                self.dragOrigin = self.dragPoint

                if self.master_circle is None:
                    # add master circle
                    self.master_circle = CI.MasterCircleItem()
                    self.master_circle.radiusChanged.sig_masterRadiusChanged.connect(
                        self.masterRadiusChanged)
                    self.master_circle.select(True)
                    self.main_plot.addItem(self.master_circle)
                    self.master_circle.setData(
                        center=self.dragOrigin, radius_point=self.dragPoint)
                else:
                    # add regular circle
                    self.circles[coords] = CI.RegularCircleItem()
                    self.circles[self.dragPoint].select(True)
                    self.main_plot.addItem(self.circles[self.dragPoint])
                    self.circles[self.dragPoint].setData(
                        center=self.dragOrigin, radius_point=self.dragPoint)

                self._update_data()
                self.updateGraph()
                event.accept()
                print("added", coords, " => ", list(self.circles.keys()))

        elif event.isFinish():
            # print("end drag", self.newPoint, self.dragOrigin, self.dragPoint)
            #self.circles[self.dragPoint].clear()
            if self.newPoint == True:
                self.getCircleAt(self.dragOrigin).select(False)
            elif self.newPoint == False:
                self.getCircleAt(self.dragPoint).select(False)
            self.newPoint = None
            self.dragPoint = None
            self.dragOrigin = None

            event.ignore()
            return
        else:
            # print("while drag")
            if self.dragPoint is None or self.newPoint is None:
                event.ignore()
                return

            pos2 = event.pos()
            coords2 = (int(pos2[0]), int(pos2[1]))

            #try: old_data = self.circles[self.dragPoint]
            #except:
            #print("key error", self.dragPoint, "not in", list(self.circles.keys()) )
            #event.ignore()
            #return
            # print("dragging", self.dragPoint, "to", coords2, " => ", list(self.circles.keys()))

            if self.newPoint == True:
                self.getCircleAt(self.dragOrigin).setData(
                    center=self.dragOrigin, radius_point=coords2)
            else:  # if self.newPoint == False:
                dragOffset = (coords2[0]-self.dragPoint[0],
                              coords2[1]-self.dragPoint[1])

                if not self.master_circle is None and self.dragPoint == self.master_circle.center:
                    old_radius_point = self.master_circle.radius_point
                    new_radius_point = (
                        old_radius_point[0]+dragOffset[0], old_radius_point[1]+dragOffset[1])
                    self.master_circle.setData(
                        center=coords2, radius_point=new_radius_point)
                elif self.dragPoint in self.circles:
                    circle = self.circles[self.dragPoint]
                    old_radius_point = circle.radius_point
                    new_radius_point = (
                        old_radius_point[0]+dragOffset[0], old_radius_point[1]+dragOffset[1])
                    circle.setData(center=self.dragPoint,
                                   radius_point=new_radius_point)
                    self.circles.pop(self.dragPoint)
                    self.circles[coords2] = circle
                else:
                    print(self.dragPoint, "I selected a point that does not exist")
                    return None

                self.dragPoint = coords2
                self._update_data()

        self.updateGraph()
        event.accept()

    def getCircleAt(self, coords):
        if not self.master_circle is None and coords == self.master_circle.center:
            return self.master_circle
        elif coords in self.circles:
            return self.circles[coords]
        else:
            print("getCircleAt", coords, "I selected a point that does not exist")
            return None

    def _update_data(self):
        xs = [0, self.data['coords'][1][0]] + [c[0]
                                               for c in self.circles.keys()]
        ys = [0, self.data['coords'][1][0]] + [c[1]
                                               for c in self.circles.keys()]
        if not self.master_circle is None:
            xs += [self.master_circle.center[0]]
            ys += [self.master_circle.center[1]]
        self.data['pos'] = np.column_stack((xs, ys))

        self.data['coords'] = self.data['coords'][:2] + \
            list(self.circles.keys())
        if not self.master_circle is None:
            self.data['coords'].append(self.master_circle.center)

        self.setData(**self.data)

    def masterRadiusChanged(self, event):
        print("masterRadiusChanged", event)
        new_master_radius = event
        for c in self.circles:
            self.circles[c].update_master_radius(new_master_radius)
        self._update_data()
        self.updateGraph()
