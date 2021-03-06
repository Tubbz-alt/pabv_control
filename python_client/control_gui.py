
from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
import queue

import numpy as np
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg


import ambu_control
import time
import traceback


import time

git_version="unknown"

try:
    import version
    git_version=version.version
except:
    pass


class PowerSwitch(QPushButton):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setMinimumWidth(100)
        self.setMinimumHeight(40)

    def paintEvent(self, event):
        label = "ON" if self.isChecked() else "OFF"
        bg_color = Qt.green if self.isChecked() else Qt.red

        radius = 14
        width = 50
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

    updateCount       = pyqtSignal(str)
    updateRate        = pyqtSignal(str)
    updateTime        = pyqtSignal(str)

    updateRespRate    = pyqtSignal(str)
    updateInhTime     = pyqtSignal(str)
    updatePipMax      = pyqtSignal(str)
    updatePipOffset   = pyqtSignal(str)
    updateVolMax      = pyqtSignal(str)
    updateVolFactor   = pyqtSignal(str)
    updateVolInhThold = pyqtSignal(str)
    updatePeepMin     = pyqtSignal(str)
    updateState       = pyqtSignal(int)

    updateVersion     = pyqtSignal(str)
    updateArTime      = pyqtSignal(str)
    updateCycVolMax   = pyqtSignal(str)
    updateCycPipMax   = pyqtSignal(str)

    updateAlarmPipMax  = pyqtSignal(str)
    updateAlarmVolLow  = pyqtSignal(str)
    updateAlarm12V     = pyqtSignal(str)
    updateWarn9V       = pyqtSignal(str)
    updateAlarmPresLow = pyqtSignal(str)
    updateWarnPeepMin  = pyqtSignal(str)

    def __init__(self, *, ambu, refPlot=False, parent=None):
        super(ControlGui, self).__init__(parent)
        self.refPlot = refPlot
        self.setWindowTitle("SLAC Accute Shortage Ventilator")

        self.ambu = ambu
        self.ambu.setConfigCallBack(self.configUpdated)
        self._queue=queue.Queue(1)
        self.ambu.setQueue(self._queue)
        self.respRate     = None
        self.inhTime      = None
        self.volInhThold  = None
        self.pipMax       = None
        self.volMax       = None
        self.stateControl = None
        self.runControl   = None
        top = QVBoxLayout()
        self.setLayout(top)

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        self.tabs.addTab(self.tab1,"AMBU Control")
        self.tabs.addTab(self.tab2,"AMBU Expert")
        self.tabs.addTab(self.tab3,"Calibration and Test")

        self.setupPageOne()
        self.setupPageTwo()
        self.setupPageThree()
        top.addWidget(self.tabs)
        self.last_update=time.time()
        QTimer.singleShot(100,self.updateAll)
    def setupPageOne(self):

        top = QHBoxLayout()
        self.tab1.setLayout(top)

        left = QVBoxLayout()
        top.addLayout(left)

        # Plot on right
        #self.plotWidget=pg.GraphicsView()
        self.gl=pg.GraphicsLayoutWidget()
        self.gl.setBackground("w")
        self.plot=[None]*3
        self.item=[None]*3
        self.plot[0]=self.gl.addPlot(row=1,col=1)
        self.plot[1]=self.gl.addPlot(row=2,col=1)
        self.plot[2]=self.gl.addPlot(row=3,col=1)
        item=pg.PlotItem()
        self.hidden=item.plot(pen=pg.mkPen("w"))

        self.plot[0].setLabel('bottom',"Time",color='black')
        self.plot[1].setLabel('bottom',"Time",color='black')
        self.plot[2].setLabel('bottom',"Time",color='black')
        legend=[None]*3
        legend[0]=pg.LegendItem(brush=pg.mkBrush("w"),horSpacing=-25)
        self.gl.addItem(legend[0],row=1,col=2)
        legend[1]=pg.LegendItem(brush=pg.mkBrush("w"),horSpacing=-100)
        self.gl.addItem(legend[1],row=2,col=2)
        legend[2]=pg.LegendItem(brush=pg.mkBrush("w"),horSpacing=-25)
        self.gl.addItem(legend[2],row=3,col=2)
        if self.refPlot:
            self.plot[0].setLabel('left',"Ref Flow SL/Min",color='black')
        else:
            self.plot[0].setLabel('left',"Press cmH20",color='black')
        self.plot[1].setLabel('left',"Flow L/Min",color='black')
        self.plot[2].setLabel('left',"Volume mL",color='black')
        for l in legend:
            pass
        for p in self.plot:
            p.setXRange(-60,0)
            p.setAutoVisible(x=False,y=False)
            p.enableAutoRange('x',False)
            p.enableAutoRange('y',False)
            p.setMouseEnabled(x=False,y=False)
            p.setMenuEnabled(False)
            p.hideButtons()

        self.curve=[None]*7
        width=3
        self.curve[0]=self.plot[0].plot(pen=pg.mkPen("m",width=width),name="Pressure")
        self.curve[1]=self.plot[0].plot(pen=pg.mkPen("r",width=width),name="P-thresh-high")
        self.curve[2]=self.plot[0].plot(pen=pg.mkPen("g",width=width),name="P-thresh-low")
        self.curve[3]=self.plot[0].plot(pen=pg.mkPen("r",width=width),name="Peep min")
        self.curve[4]=self.plot[1].plot(pen=pg.mkPen("g",width=width),name="Flow")
        self.curve[5]=self.plot[2].plot(pen=pg.mkPen("b",width=width),name="Volume")
        self.curve[6]=self.plot[2].plot(pen=pg.mkPen("r",width=width),name="V-thresh-high")

        legend[0].addItem(self.curve[0],"Pressure")
        legend[0].addItem(self.curve[1],"P-thresh-high")
        legend[0].addItem(self.curve[2],"P-thresh-low")
        legend[0].addItem(self.curve[3],"Peep min")
        for i in range(3): legend[0].addItem(self.hidden,"")
        legend[1].addItem(self.curve[4],"Flow")
        for i in range(6): legend[1].addItem(self.hidden,"")
        legend[2].addItem(self.curve[5],"Volume")
        legend[2].addItem(self.curve[6],"V-thresh-high")
        for i in range(5): legend[2].addItem(self.hidden,"")
        top.addWidget(self.gl,66)

        # Controls on left
        gb = QGroupBox('Control')
        left.addWidget(gb)

        fl = QFormLayout()
        fl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        gb.setLayout(fl)

        self.respRate = QLineEdit()
        self.respRate.returnPressed.connect(self.setRespRate)
        self.updateRespRate.connect(self.respRate.setText)
        fl.addRow('RR (Breaths/Min):',self.respRate)

        self.inhTime = QLineEdit()
        self.inhTime.returnPressed.connect(self.setInhTime)
        self.updateInhTime.connect(self.inhTime.setText)
        fl.addRow('Inhalation Time (S):',self.inhTime)

        self.volInhThold = QLineEdit()
        self.volInhThold.returnPressed.connect(self.setVolInhThold)
        self.updateVolInhThold.connect(self.volInhThold.setText)
        fl.addRow('Vol Inh P (cmH20):',self.volInhThold)

        self.pipMax = QLineEdit()
        self.pipMax.returnPressed.connect(self.setPipMax)
        self.updatePipMax.connect(self.pipMax.setText)
        fl.addRow('Pip Max (cmH20):',self.pipMax)

        self.volMax = QLineEdit()
        self.volMax.returnPressed.connect(self.setVolMax)
        self.updateVolMax.connect(self.volMax.setText)
        fl.addRow('V Max (mL):',self.volMax)

        self.peepMin = QLineEdit()
        self.peepMin.returnPressed.connect(self.setPeepMin)
        self.updatePeepMin.connect(self.peepMin.setText)
        fl.addRow('Peep Min (cmH20):',self.peepMin)

        self.runControl = PowerSwitch()
        self.runControl.clicked.connect(self.setRunState)
        fl.addRow('Run Enable:',self.runControl)

        muteAlarm = QPushButton("Mute Alarm")
        muteAlarm.pressed.connect(self.muteAlarm)
        fl.addRow('',muteAlarm)

        # Status
        gb = QGroupBox('Status')
        gb.setFixedWidth(300)
        left.addWidget(gb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        gb.setLayout(fl)

        #this will be a switch that will display true and turn red if any of the alarm conditions are met.  Hovering or looking at expert page will say which.  maybe even alarms settings page? or just alarm settings group box on expert page?
        #fl.addRow('Alarm Status:',self.alarmStatus)

        cycVolMax = QLineEdit()
        cycVolMax.setText("0")
        cycVolMax.setReadOnly(True)
        self.updateCycVolMax.connect(cycVolMax.setText)
        fl.addRow('Max Volume (mL):',cycVolMax)

        cycPipMax = QLineEdit()
        cycPipMax.setText("0")
        cycPipMax.setReadOnly(True)
        self.updateCycPipMax.connect(cycPipMax.setText)
        fl.addRow('Max Pip (cmH20):',cycPipMax)

        cycleRunTime=QLineEdit()
        cycleRunTime.setText("0")
        cycleRunTime.setReadOnly(True)
        # I think we want the time since they last clicked to start a cycle. there are a lot of times, I’ll try to find a way to make this less confusing.
        fl.addRow('Cycle run time:',cycleRunTime)


        cycles = QLineEdit()
        cycles.setText("0")
        cycles.setReadOnly(True)
        self.updateCount.connect(cycles.setText)
        fl.addRow('Breaths:',cycles)
        # I think we want breaths since cycle start rather than software start?


    def setupPageTwo(self):

        top = QHBoxLayout()
        self.tab2.setLayout(top)

        left = QVBoxLayout()
        top.addLayout(left)

        right = QVBoxLayout()
        top.addLayout(right)

        # Period Control
        gb = QGroupBox('GUI Control')
        left.addWidget(gb)

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

        self.pipOffset = QLineEdit()
        self.pipOffset.returnPressed.connect(self.setPipOffset)
        self.updatePipOffset.connect(self.pipOffset.setText)
        fl.addRow('Pip Offset (cmH20):',self.pipOffset)

        self.volFactor = QLineEdit()
        self.volFactor.returnPressed.connect(self.setVolFactor)
        self.updateVolFactor.connect(self.volFactor.setText)
        fl.addRow('Vol Factor:',self.volFactor)

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
        self.fMinValue.setText("-50")
        fl.addRow('Flow Min Value:',self.fMinValue)

        self.fMaxValue = QLineEdit()
        self.fMaxValue.setText("100")
        fl.addRow('Flow Max Value:',self.fMaxValue)

        self.vMinValue = QLineEdit()
        self.vMinValue.setText("-200")
        fl.addRow('Vol Min Value:',self.vMinValue)

        self.vMaxValue = QLineEdit()
        self.vMaxValue.setText("800")
        fl.addRow('Vol Max Value:',self.vMaxValue)

        # moved from front page
        # Status
        gb = QGroupBox('Status')
        right.addWidget(gb)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        gb.setLayout(fl)

        alarmPipMax = QLineEdit()
        alarmPipMax.setText("0")
        alarmPipMax.setReadOnly(True)
        self.updateAlarmPipMax.connect(alarmPipMax.setText)
        fl.addRow('Pip Max Alarm:',alarmPipMax)

        alarmVolLow = QLineEdit()
        alarmVolLow.setText("0")
        alarmVolLow.setReadOnly(True)
        self.updateAlarmVolLow.connect(alarmVolLow.setText)
        fl.addRow('Vol Low Alarm:',alarmVolLow)

        alarm12V = QLineEdit()
        alarm12V.setText("0")
        alarm12V.setReadOnly(True)
        self.updateAlarm12V.connect(alarm12V.setText)
        fl.addRow('12V Alarm:',alarm12V)

        warn9V = QLineEdit()
        warn9V.setText("0")
        warn9V.setReadOnly(True)
        self.updateWarn9V.connect(warn9V.setText)
        fl.addRow('9V Alarm:',warn9V)

        alarmPresLow = QLineEdit()
        alarmPresLow.setText("0")
        alarmPresLow.setReadOnly(True)
        self.updateAlarmPresLow.connect(alarmPresLow.setText)
        fl.addRow('Press Low Alarm:',alarmPresLow)

        warnPeepMin = QLineEdit()
        warnPeepMin.setText("0")
        warnPeepMin.setReadOnly(True)
        self.updateWarnPeepMin.connect(warnPeepMin.setText)
        fl.addRow('Peep Min Warning:',warnPeepMin)

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

        cycVolMax = QLineEdit()
        cycVolMax.setText("0")
        cycVolMax.setReadOnly(True)
        self.updateCycVolMax.connect(cycVolMax.setText)
        fl.addRow('Max Volume (mL):',cycVolMax)

        cycPipMax = QLineEdit()
        cycPipMax.setText("0")
        cycPipMax.setReadOnly(True)
        self.updateCycPipMax.connect(cycPipMax.setText)
        fl.addRow('Max Pip (cmH20):',cycPipMax)

        timeSinceStart=QLineEdit()
        timeSinceStart.setText("0")
        timeSinceStart.setReadOnly(True)
        self.updateTime.connect(timeSinceStart.setText)
        fl.addRow('Seconds since start:',timeSinceStart)

        arduinoUptime=QLineEdit()
        arduinoUptime.setText("0")
        arduinoUptime.setReadOnly(True)
        self.updateArTime.connect(arduinoUptime.setText)
        fl.addRow('Arduino uptime (s):',arduinoUptime)

        guiVersion = QLineEdit()
        guiVersion.setText(git_version)
        guiVersion.setReadOnly(True)
        fl.addRow('GUI version:',guiVersion)


        # Log File
        gb = QGroupBox('Log File')
        left.addWidget(gb)

        vl = QVBoxLayout()
        gb.setLayout(vl)

        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        vl.addLayout(fl)



        self.logFile = QLineEdit()
        self.logFile.setReadOnly(True);
        pb = QPushButton('Select output File')
        pb.clicked.connect(self.selectFile)
        vl.addWidget(pb)
        self.selectLog=pb
        fl.addRow('Log File:',self.logFile)

        pb = QPushButton('Begin Recording Data')
        pb.clicked.connect(self.openPressed)
        self.beginLog=pb
        vl.addWidget(pb)

        pb = QPushButton('Stop Recording Data')
        pb.clicked.connect(self.closePressed)
        self.endLog=pb
        vl.addWidget(pb)

        self.plotData = []
        self.rTime = time.time()
        self.beginLog.setEnabled(False)
        self.endLog.setEnabled(False)

    def setupPageThree(self):
        self.timeoutabort=0
        top = QHBoxLayout()
        self.tab3.setLayout(top)

        left = QVBoxLayout()
        top.addLayout(left)

        right = QVBoxLayout()
        top.addLayout(right)

        # Controls and plot on right

        #controls group box{
        gb = QGroupBox('Relay Control (Disabled for now to avoid conflict)')
        right.addWidget(gb)

        right.addSpacing(20)

        #f1 defines layout for group box gb
        fl = QFormLayout()
        fl.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fl.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        fl.setLabelAlignment(Qt.AlignRight)
        gb.setLayout(fl)

        #relay control
        self.stateControl2 = QComboBox()
        self.stateControl2.addItem("Relay Force Off")
        self.stateControl2.addItem("Relay Force On")
        self.stateControl2.addItem("Relay Run Off")
        self.stateControl2.addItem("Relay Run On")
        #self.stateControl.setCurrentIndex(3)
        #self.updateState.connect(self.stateControl.setCurrentIndex)
        #self.stateControl.currentIndexChanged.connect(self.setState)
        fl.addRow('State:',self.stateControl2)


        #} end controls gb

        #using self.plot makes it disappear from other page... this is placeholder for now


        # left
        gb = QGroupBox('Calibration Instructions')
        left.addWidget(gb)
        #left.addSpacing(300)
        gb.setMinimumWidth(450)
        gb.setMaximumHeight(500)


        vbox = QVBoxLayout()

        #Text field and control buttons for instructions

        self.instructions = []

        self.instructions.append("Click 'Next' to begin calibration procedure")

        self.instructions.append("The ASV should be off and the paddle up. Please check that the patient circuit is connected and a test lung in place. Make sure the compressed air supply is connected and on.")

        self.instructions.append("Press the paddle down by hand. The pressure, flow, and volume plots should indicate the bag compression.")

        self.instructions.append("The ASV is now cycling. Check that the paddle pushes the AMBU bag down smoothly before the paddle comes up. Adjust the air supply valve as needed. Adjust the exhaust valve so paddle rises smoothly.")


        self.instructions.append(" Leak Check. After the paddle goes down, observe the pressure plot. The pressure should decline slowly, taking at least 10 seconds to reach 0. Faster indicates a leak in the patient circuit.")

        self.instructions.append( " PIP Check: Check that the  PIP valve has marked cap indicating it has been modified for higher pressure. Set PIP for 40 cm H2O using calibration plot.")

        self.instructions.append(" Checking PIP.")

        self.instructions.append(" Please set PIP to 30 cm H2O.")

        self.instructions.append("Checking PIP")

        self.instructions.append(" Please set PIP to 20 cm H2O.")

        self.instructions.append(" Checking PIP.")

        self.instructions.append(" Below are the data. The values should be consistent with the calibration plot.")

        self.instructions.append("Please set PIP valve back to 30 cm H2O. Please set PIPmax parameter to 25 cm H2O.")

        self.instructions.append(" The ASV is running. Check the pressure plot to see that the paddle cycle stops when PIPmax is reached.")

        self.instructions.append("Calibration cycle compelete.")

        self.instlength = len(self.instructions)

        self.index=0

        self.textfield = QTextEdit()
        self.textfield.setReadOnly(True)

        self.textfield.setText(self.instructions[self.index])

        self.performAction()

        vbox.addWidget(self.textfield)
        gb.setLayout(vbox)

        buttongroup = QHBoxLayout()

        prevbutton = QPushButton('Previous')
        prevbutton.clicked.connect(self.prevPressed)

        nextbutton = QPushButton('Next')
        nextbutton.clicked.connect(self.nextPressed)

        repbutton = QPushButton('Repeat')
        repbutton.clicked.connect(self.repPressed)

        buttongroup.addWidget(prevbutton)
        buttongroup.addWidget(repbutton)
        buttongroup.addWidget(nextbutton)

        vbox.addLayout(buttongroup)



        #add results groupbox
        gb_results = QGroupBox('Results')
        left.addWidget(gb_results)
        #left.addSpacing(300)
        gb_results.setMinimumWidth(450)
        gb_results.setMinimumHeight(300)

        results_hbox = QVBoxLayout()
        gb_results.setLayout(results_hbox)

        #results_hbox.addLayout(nameofthing)
        self.doInit=True
        self.line=[None]*7

    def performAction(self):
        try:
            if self.index == 1 or self.index == 2 or self.index == 5 or self.index == 7  or self.index == 9 or self.index == 11 or self.index == 12:
                self.textfield.setText(str(self.index)+") "+self.textfield.toPlainText()+"\n\nState: Paddle up")
                self.stateControl.setCurrentIndex(0)

            if self.index == 3 or self.index == 13 or self.index == 14:
                self.textfield.setText(str(self.index)+") "+self.textfield.toPlainText()+"\n\nState: Paddle cycling")
                self.stateControl.setCurrentIndex(3)

            if self.index == 4:
                self.textfield.setText(str(self.index)+") "+self.textfield.toPlainText()+"\n\nState: Paddle up for 5 seconds, then Paddle down")
                self.stateControl.setCurrentIndex(0)
                sleeptime=5
                sleeptimer=0
                self.timeoutabort=0
                while sleeptimer<sleeptime:
                    time.sleep(0.1)
                    QCoreApplication.processEvents()
                    if self.timeoutabort>0:
                        break
                    sleeptimer=sleeptimer+0.1
                if self.timeoutabort==0:
                    self.stateControl.setCurrentIndex(1)

            if self.index == 6 or self.index == 8 or self.index == 10:
                self.textfield.setText(str(self.index)+") "+self.textfield.toPlainText()+"\n\nState: Running 10 cycles; calculating observed PIP from pressure plot.  Results will appear below.")
                self.stateControl.setCurrentIndex(3)
                sleeptime=30
                sleeptimer=0
                self.timeoutabort=0
                while sleeptimer<sleeptime:
                    time.sleep(0.1)
                    QCoreApplication.processEvents()
                    if self.timeoutabort>0:
                        break
                    sleeptimer=sleeptimer+0.1
                if self.timeoutabort==0:
                    self.stateControl.setCurrentIndex(0)


        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def nextPressed(self):
        try:
            self.timeoutabort=1
            if self.index < self.instlength-1:
                self.index=self.index+1
                self.textfield.setText(self.instructions[self.index])
                self.performAction()
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def prevPressed(self):
        try:
            self.timeoutabort=1
            if self.index > 0:
                self.index=self.index-1
                self.textfield.setText(self.instructions[self.index])
                self.performAction()
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def repPressed(self):
        try:
            self.timeoutabort=1
            self.textfield.setText(self.instructions[self.index])
            self.performAction()
        except Exception as e:
            print(f"Got GUI value error {e}")

    @pyqtSlot()
    def setRespRate(self):
        try:
            self.ambu.respRate = float(self.respRate.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setInhTime(self):
        try:
            self.ambu.inhTime = float(self.inhTime.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setVolInhThold(self):
        try:
            self.ambu.volInThold = float(self.volInhThold.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setPipMax(self):
        try:
            self.ambu.pipMax = float(self.pipMax.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setPipOffset(self):
        try:
            self.ambu.pipOffset = float(self.pipOffset.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setPeepMin(self):
        try:
            self.ambu.peepMin = float(self.peepMin.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setVolMax(self):
        try:
            self.ambu.volMax = float(self.volMax.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot()
    def setVolFactor(self):
        try:
            self.ambu.volFactor = float(self.volFactor.text())
        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot(int)
    def setState(self,value):
        try:
            self.ambu.runState = value

            if value == 3:
                self.runControl.setChecked(True)
            else:
                self.runControl.setChecked(False)

        except Exception as e:
            #print(f"Got GUI value error {e}")
            pass

    @pyqtSlot(bool)
    def setRunState(self,st):
        pass
        if st and self.stateControl.currentIndex() != 3:
            self.stateControl.setCurrentIndex(3)
        elif self.stateControl.currentIndex() > 2:
            self.stateControl.setCurrentIndex(2)

    @pyqtSlot()
    def muteAlarm(self):
        self.ambu.muteAlarm()

    @pyqtSlot()
    def openPressed(self):
        f = self.logFile.text()
        self.ambu.openLog(f)
        self.beginLog.setEnabled(False)
        self.endLog.setEnabled(True)
        self.selectLog.setEnabled(False)

    @pyqtSlot()
    def closePressed(self):
        self.ambu.closeLog()
        self.endLog.setEnabled(False)
        self.beginLog.setEnabled(True)
        self.selectLog.setEnabled(True)

    @pyqtSlot()
    def selectFile(self):
        dlg = QFileDialog()
        f=dlg.getSaveFileName(self, 'Save ventillator data:')[0]
        if(len(f)>0):
            state=not self.beginLog.isEnabled() and not self.endLog.isEnabled()
            if(state):
                self.beginLog.setEnabled(True)
                self.logFile.setText(f)
            self.logFile.update()


    def configUpdated(self):
        self.updateRespRate.emit("{:0.1f}".format(self.ambu.respRate))
        self.updateInhTime.emit("{:0.1f}".format(self.ambu.inhTime))
        self.updateVolInhThold.emit("{:0.1f}".format(self.ambu.volInThold))
        self.updatePipMax.emit("{:0.1f}".format(self.ambu.pipMax))
        self.updateVolMax.emit("{:0.1f}".format(self.ambu.volMax))
        self.updatePipOffset.emit("{:0.1f}".format(self.ambu.pipOffset))
        self.updateVolFactor.emit("{:0.1f}".format(self.ambu.volFactor))
        self.updatePeepMin.emit("{:0.1f}".format(self.ambu.peepMin))

        self.updateState.emit(self.ambu.runState)

        if self.ambu.runState == 3:
            self.runControl.setChecked(True)
        else:
            self.runControl.setChecked(False)

        self.updateVersion.emit(str(self.ambu.version))

    def updateDisplay(self,count,rate,stime,artime,volMax,pipMax):
        self.updateCount.emit(str(count))
        self.updateRate.emit(f"{rate:.1f}")
        self.updateTime.emit(f"{stime:.1f}")
        self.updateArTime.emit(f"{artime:.1f}")
        self.updateCycVolMax.emit(f"{volMax:.1f}")
        self.updateCycPipMax.emit(f"{pipMax:.1f}")

        self.updateAlarmPipMax.emit("{}".format(self.ambu.alarmPipMax))
        self.updateAlarmVolLow.emit("{}".format(self.ambu.alarmVolLow))
        self.updateAlarm12V.emit("{}".format(self.ambu.alarm12V))
        self.updateWarn9V.emit("{}".format(self.ambu.warn9V))
        self.updateAlarmPresLow.emit("{}".format(self.ambu.alarmPresLow))
        self.updateWarnPeepMin.emit("{}".format(self.ambu.warnPeepMin))
        if self.ambu.alarmPipMax or self.ambu.alarmVolLow or self.ambu.alarm12V or self.ambu.alarmPresLow:
            self.alarmStatus.setStyleSheet("""QLineEdit { background-color: red; color: black }""")
            self.alarmStatus.setText("Alarm")
        elif self.ambu.warn9V or self.ambu.warnPeepMin:
            self.alarmStatus.setStyleSheet("""QLineEdit { background-color: yellow; color: black }""")
            self.alarmStatus.setText("Warning")

        else:
            self.alarmStatus.setStyleSheet("""QLineEdit { background-color: lime; color: black }""")
            self.alarmStatus.setText("Clear")

    def updatePlot(self,inData):
        ambu_data = inData.get_data()
        if type(ambu_data) == type(None):
            return
        xa =  ambu_data[0,:]
        xa=xa-xa[-1]
        try:
            self.plot[0].setYRange(float(self.pMinValue.text()),float(self.pMaxValue.text()))
            self.plot[1].setYRange(float(self.fMinValue.text()),float(self.fMaxValue.text()))
            self.plot[2].setYRange(float(self.vMinValue.text()),float(self.vMaxValue.text()))
            data=[None]*7
            data[0]=ambu_data[2,:]
            data[1]=ambu_data[6,:]
            data[2]=ambu_data[5,:]
            data[3]=ambu_data[8,:]
            data[4]=ambu_data[3,:]
            data[5]=ambu_data[4,:]
            data[6]=ambu_data[7,:]

            for i in range(7):
                self.curve[i].setData(xa,data[i])
            #self.gl.update()
        except Exception as e:
            #print(e)
            pass

    def updateAll(self):
        ts=time.time()
        rate=100

        try:
            (data, count, rate, stime, artime, volMax, pipMax) = self._queue.get(block=False)
            self.updateDisplay(count,rate,stime,artime,volMax,pipMax)
            self.updatePlot(data)
        except:
            pass
        dt=(time.time()-self.last_update)*1000
        corr=dt-rate
        if(corr>=(rate/2) or dt>=rate): corr=0
        self.last_update=time.time()
        QTimer.singleShot(rate-corr, self.updateAll)
