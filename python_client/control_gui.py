
from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *

import numpy as np
import matplotlib.pyplot as plt
import ambu_control

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import time

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=10, height=10, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = [fig.add_subplot(311), fig.add_subplot(312), fig.add_subplot(313)]
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout(pad=3.0)

class PowerSwitch(QPushButton):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setMinimumWidth(66)
        self.setMinimumHeight(22)

    def paintEvent(self, event):
        label = "ON" if self.isChecked() else "OFF"
        bg_color = Qt.green if self.isChecked() else Qt.red

        radius = 10
        width = 32
        center = self.rect().center()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(center)
        painter.setBrush(QColor(0,0,0))

        pen = QPen(Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)

        painter.drawRoundedRect(QRect(-width, -radius, 2*width, 2*radius), radius, radius)
        painter.setBrush(QBrush(bg_color))
        sw_rect = QRect(-radius, -radius, width + radius, 2*radius)
        if not self.isChecked():
            sw_rect.moveLeft(-width)
        painter.drawRoundedRect(sw_rect, radius, radius)
        painter.drawText(sw_rect, Qt.AlignCenter, label)


class ControlGui(QWidget):

    updateCount = pyqtSignal(str)
    updateRate  = pyqtSignal(str)
    updateRR    = pyqtSignal(str)
    updateIT    = pyqtSignal(str)
    updateStart = pyqtSignal(str)
    updateStop  = pyqtSignal(str)
    updateVol   = pyqtSignal(str)
    updateState = pyqtSignal(int)

    def __init__(self, *, ambu, refPlot=False, parent=None):
        super(ControlGui, self).__init__(parent)

        self.refPlot = refPlot
        self.setWindowTitle("SLAC Accute Shortage Ventilator")

        self.ambu = ambu
        self.ambu.setDataCallBack(self.dataUpdated)
        self.ambu.setConfCallBack(self.confUpdated)

        self.rateInput    = None
        self.inTimeInput  = None
        self.startThInput = None
        self.stopThInput  = None
        self.volThInput   = None
        self.stateControl = None
        self.runControl   = None

        top = QVBoxLayout()
        self.setLayout(top)

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.tabs.addTab(self.tab1,"AMBU Control")
        self.tabs.addTab(self.tab2,"AMBU Expert")

        self.setupPageOne()
        self.setupPageTwo()

        top.addWidget(self.tabs)

    def setupPageOne(self):

        top = QHBoxLayout()
        self.tab1.setLayout(top)

        left = QVBoxLayout()
        top.addLayout(left)

        # Plot on right
        self.plot = MplCanvas()
        top.addWidget(self.plot)

        # Controls on left
        gb = QGroupBox('Control')
        left.addWidget(gb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        gb.setLayout(fl)

        self.rateInput = QLineEdit()
        self.rateInput.returnPressed.connect(self.setRate)
        self.updateRR.connect(self.rateInput.setText)
        fl.addRow('RR (Breaths/Min):',self.rateInput)

        self.inTimeInput = QLineEdit()
        self.inTimeInput.returnPressed.connect(self.setOnTime)
        self.updateIT.connect(self.inTimeInput.setText)
        fl.addRow('Inhalation Time (S):',self.inTimeInput)

        self.startThInput = QLineEdit()
        self.startThInput.returnPressed.connect(self.setStartThold)
        self.updateStart.connect(self.startThInput.setText)
        fl.addRow('Vol Inh P (cmH20):',self.startThInput)

        self.stopThInput = QLineEdit()
        self.stopThInput.returnPressed.connect(self.setStopThold)
        self.updateStop.connect(self.stopThInput.setText)
        fl.addRow('Pip Max (cmH20):',self.stopThInput)

        self.volThInput = QLineEdit()
        self.volThInput.returnPressed.connect(self.setVolThold)
        self.updateVol.connect(self.volThInput.setText)
        fl.addRow('V Max (mL):',self.volThInput)

        self.runControl = PowerSwitch()
        self.runControl.clicked.connect(self.setRunState)
        fl.addRow('Run Enable:',self.runControl)

        # Status
        gb = QGroupBox('Status')
        left.addWidget(gb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        gb.setLayout(fl)

        cycles = QLineEdit()
        cycles.setText("0")
        cycles.setReadOnly(True)
        self.updateCount.connect(cycles.setText)
        fl.addRow('Breaths:',cycles)

        sampRate = QLineEdit()
        sampRate.setText("0")
        sampRate.setReadOnly(True)
        self.updateRate.connect(sampRate.setText)
        fl.addRow('Sample Rate:',sampRate)

    def setupPageTwo(self):

        top = QHBoxLayout()
        self.tab2.setLayout(top)

        # Period Control
        gb = QGroupBox('GUI Control')
        top.addWidget(gb)

        vl = QVBoxLayout()
        gb.setLayout(vl)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vl.addLayout(fl)

        self.stateControl = QComboBox()
        self.stateControl.addItem("Relay Force Off")
        self.stateControl.addItem("Relay Force On")
        self.stateControl.addItem("Relay Run Off")
        self.stateControl.addItem("Relay Run On")
        self.stateControl.setCurrentIndex(3)
        self.updateState.connect(self.stateControl.setCurrentIndex)
        self.stateControl.currentIndexChanged.connect(self.setState)
        fl.addRow('State:',self.stateControl)

        self.pMinValue = QLineEdit()
        self.pMinValue.setText("-5")

        if self.refPlot:
            fl.addRow('Ref Flow Min Value:',self.pMinValue)
        else:
            fl.addRow('Pres Min Value:',self.pMinValue)

        self.pMaxValue = QLineEdit()
        self.pMaxValue.setText("40")

        if self.refPlot:
            fl.addRow('Ref Flow Max Value:',self.pMaxValue)
        else:
            fl.addRow('Pres Max Value:',self.pMaxValue)

        self.fMinValue = QLineEdit()
        self.fMinValue.setText("-5")
        fl.addRow('Flow Min Value:',self.fMinValue)

        self.fMaxValue = QLineEdit()
        self.fMaxValue.setText("250")
        fl.addRow('Flow Max Value:',self.fMaxValue)

        self.vMinValue = QLineEdit()
        self.vMinValue.setText("-5")
        fl.addRow('Vol Min Value:',self.vMinValue)

        self.vMaxValue = QLineEdit()
        self.vMaxValue.setText("500")
        fl.addRow('Vol Max Value:',self.vMaxValue)

        # Log File
        gb = QGroupBox('Log File')
        top.addWidget(gb)

        vl = QVBoxLayout()
        gb.setLayout(vl)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vl.addLayout(fl)

        self.logFile = QLineEdit()
        fl.addRow('Log File:',self.logFile)

        pb = QPushButton('Open File')
        pb.clicked.connect(self.openPressed)
        vl.addWidget(pb)

        pb = QPushButton('Close File')
        pb.clicked.connect(self.closePressed)
        vl.addWidget(pb)

        self.plotData = []
        self.rTime = time.time()

    @pyqtSlot()
    def setRate(self):
        try:
            self.ambu.cycleRate = float(self.rateInput.text())
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def setOnTime(self):
        try:
            self.ambu.onTime = float(self.inTimeInput.text())
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def setStartThold(self):
        try:
            self.ambu.startThold = float(self.startThInput.text())
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def setStopThold(self):
        try:
            self.ambu.stopThold = float(self.stopThInput.text())
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def setVolThold(self):
        try:
            self.ambu.volThold = float(self.volThInput.text())
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot(int)
    def setState(self,value):
        try:
            self.ambu.state = value

            if value == 3:
                self.runControl.setChecked(True)
            else:
                self.runControl.setChecked(False)

        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot(bool)
    def setRunState(self,st):
        if st:
            self.stateControl.setCurrentIndex(3)
        elif self.stateControl.currentIndex() >= 2:
            self.stateControl.setCurrentIndex(2)

    @pyqtSlot()
    def openPressed(self):
        f = self.logFile.text()
        self.ambu.openLog(f)

    @pyqtSlot()
    def closePressed(self):
        self.ambu.closeLog()

    def confUpdated(self):
        self.updateRR.emit("{:0.1f}".format(self.ambu.cycleRate))
        self.updateIT.emit("{:0.1f}".format(self.ambu.onTime))
        self.updateStart.emit("{:0.1f}".format(self.ambu.startThold))
        self.updateStop.emit("{:0.1f}".format(self.ambu.stopThold))
        self.updateVol.emit("{:0.1f}".format(self.ambu.volThold))
        self.updateState.emit(self.ambu.state)

        if self.ambu.state == 3:
            self.runControl.setChecked(True)
        else:
            self.runControl.setChecked(False)

    def dataUpdated(self,inData,count,rate):

        self.updateCount.emit(str(count))
        self.updateRate.emit(f"{rate:.1f}")

        try:
            self.plot.axes[0].cla()
            self.plot.axes[1].cla()
            self.plot.axes[2].cla()
            xa = np.array(inData['time'])

            self.plot.axes[0].plot(xa,np.array(inData['press']),color="yellow",linewidth=2.0)
            self.plot.axes[0].plot(xa,np.array(inData['inhP']),color="red",linewidth=1.0)
            self.plot.axes[0].plot(xa,np.array(inData['maxP']),color="red",linewidth=1.0)
            self.plot.axes[1].plot(xa,np.array(inData['flow']),color="green",linewidth=2.0)
            self.plot.axes[2].plot(xa,np.array(inData['vol']),color="blue",linewidth=2.0)
            self.plot.axes[2].plot(xa,np.array(inData['maxV']),color="red",linewidth=1.0)

            self.plot.axes[0].set_ylim([float(self.pMinValue.text()),float(self.pMaxValue.text())])
            self.plot.axes[1].set_ylim([float(self.fMinValue.text()),float(self.fMaxValue.text())])
            self.plot.axes[2].set_ylim([float(self.vMinValue.text()),float(self.vMaxValue.text())])

            self.plot.axes[0].set_xlabel('Time')

            if self.refPlot:
                self.plot.axes[0].set_ylabel('Ref Flow SL/Min')
            else:
                self.plot.axes[0].set_ylabel('Press cmH20')

            self.plot.axes[1].set_xlabel('Time')
            self.plot.axes[1].set_ylabel('Flow L/Min')

            self.plot.axes[2].set_xlabel('Time')
            self.plot.axes[2].set_ylabel('Volume mL')

            self.plot.draw()
        except Exception as e:
            print(f"Got plotting exception {e}")

