from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QGridLayout
from PySide6.QtCore import Qt, QTimer
from scipy import signal
from collections import deque
from RightHand import RightHand  # Assuming this is your hand model class
import time
from AnimationWindow import AnimationWindow
import math

# CRITICAL: Create QApplication instance ONCE at module level
# This must exist before any Qt widgets are created
app = QApplication.instance()
if app is None:
    app = QApplication([])


class LowPassFilter:
    def __init__(self, cutoff_freq=5, sample_rate=100, order=2):
        if sample_rate < 1:
            sample_rate = 100
        nyquist = sample_rate / 2
        if cutoff_freq >= nyquist:
            cutoff_freq = nyquist * 0.9
        normal_cutoff = cutoff_freq / nyquist
        if not (0 < normal_cutoff < 1):
            normal_cutoff = 0.1
        self.b, self.a = signal.butter(order, normal_cutoff, btype='low')
        self.zi = signal.lfilter_zi(self.b, self.a)

    def update(self, new_value):
        try:
            value = float(new_value)
            filtered_value, self.zi = signal.lfilter(self.b, self.a, [value], zi=self.zi)
            return filtered_value[0]
        except (ValueError, TypeError):
            return new_value

class GloveMonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Acquisition Window')
        self.rightHand = RightHand()

        self.currentData = None
        self.filteredData = None
        self.currentTimestamp = None
        self.currentView = 'Thumb'

        self.last_update_time = None
        self.sample_intervals = deque(maxlen=50)
        self.estimated_sample_rate = 100
        self.initializeFilters(sample_rate=100, cutoff_freq=5)

        container = QWidget()
        self.setCentralWidget(container)
        self.layout = QGridLayout(container)

        menuBar = self.menuBar()
        viewSelectMenu = menuBar.addMenu('View')
        thumbView = viewSelectMenu.addAction('Thumb')
        thumbView.triggered.connect(lambda: self.changeView('Thumb'))
        pointerView = viewSelectMenu.addAction('Pointer')
        pointerView.triggered.connect(lambda: self.changeView('Pointer'))
        middleView = viewSelectMenu.addAction('Middle')
        middleView.triggered.connect(lambda: self.changeView('Middle'))
        ringView = viewSelectMenu.addAction('Ring')
        ringView.triggered.connect(lambda: self.changeView('Ring'))
        pinkyView = viewSelectMenu.addAction('Pinky')
        pinkyView.triggered.connect(lambda: self.changeView('Pinky'))
        wristView = viewSelectMenu.addAction('Wrist')
        wristView.triggered.connect(lambda: self.changeView('Wrist'))

        self.timestampLabel = QLabel('Timestamp: --')
        self.timestampLabel.setAlignment(Qt.AlignCenter)
        self.sampleRateLabel = QLabel('Sample Rate: -- Hz')
        self.sampleRateLabel.setAlignment(Qt.AlignCenter)
        self.viewTitleLabel = QLabel('Thumb Data')
        self.viewTitleLabel.setAlignment(Qt.AlignCenter)
        self.viewTitleLabel.setStyleSheet("font-weight: bold; font-size: 14pt;")

        self.dataLabel1 = QLabel('Flex: --')
        self.dataLabel1.setAlignment(Qt.AlignCenter)
        self.dataLabel2 = QLabel('Gyro X: --')
        self.dataLabel2.setAlignment(Qt.AlignCenter)
        self.dataLabel3 = QLabel('Gyro Y: --')
        self.dataLabel3.setAlignment(Qt.AlignCenter)
        self.dataLabel4 = QLabel('Gyro Z: --')
        self.dataLabel4.setAlignment(Qt.AlignCenter)
        self.dataLabel5 = QLabel('Acc X: --')
        self.dataLabel5.setAlignment(Qt.AlignCenter)
        self.dataLabel6 = QLabel('Acc Y: --')
        self.dataLabel6.setAlignment(Qt.AlignCenter)
        self.dataLabel7 = QLabel('Acc Z: --')
        self.dataLabel7.setAlignment(Qt.AlignCenter)
        self.dataLabel8 = QLabel('Flex Angle (deg): --')
        self.dataLabel8.setAlignment(Qt.AlignCenter)

        self.setupLayout()

        # Create animation window
        self.animationView = AnimationWindow()

        # Setup a timer to process Qt events periodically
        self.event_timer = QTimer()
        self.event_timer.timeout.connect(self.process_events)
        self.event_timer.start(10)  # Process events every 10ms

    def process_events(self):
        """Process Qt events - necessary when running with Tkinter"""
        QApplication.processEvents()

    def initializeFilters(self, sample_rate, cutoff_freq=5):
        self.flex_filters = [LowPassFilter(cutoff_freq, sample_rate, order=2) for _ in range(5)]
        self.gyro_filters = [LowPassFilter(cutoff_freq, sample_rate, order=2) for _ in range(18)]
        self.acc_filters = [LowPassFilter(cutoff_freq, sample_rate, order=2) for _ in range(18)]

    def updateSampleRate(self):
        current_time = time.time()
        if self.last_update_time is not None:
            interval = current_time - self.last_update_time
            if interval > 0:
                self.sample_intervals.append(interval)
                if len(self.sample_intervals) >= 10:
                    avg_interval = sum(self.sample_intervals) / len(self.sample_intervals)
                    new_sample_rate = 1.0 / avg_interval
                    if abs(new_sample_rate - self.estimated_sample_rate) > 10:
                        self.estimated_sample_rate = new_sample_rate
                        self.initializeFilters(self.estimated_sample_rate)
                        print(f"Sample rate updated to: {self.estimated_sample_rate:.1f} Hz")
                    else:
                        self.estimated_sample_rate = new_sample_rate
                    self.sampleRateLabel.setText(f'Sample Rate: {self.estimated_sample_rate:.1f} Hz')
        self.last_update_time = current_time

    def setupLayout(self):
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)
        self.layout.addWidget(self.timestampLabel, 0, 0, 1, 3)
        self.layout.addWidget(self.sampleRateLabel, 1, 0, 1, 3)
        self.layout.addWidget(self.viewTitleLabel, 2, 0, 1, 3)
        if self.currentView == 'Wrist':
            self.dataLabel1.hide()
            self.dataLabel8.hide()
            self.layout.addWidget(self.dataLabel2, 3, 0)
            self.layout.addWidget(self.dataLabel3, 3, 1)
            self.layout.addWidget(self.dataLabel4, 3, 2)
            self.layout.addWidget(self.dataLabel5, 4, 0)
            self.layout.addWidget(self.dataLabel6, 4, 1)
            self.layout.addWidget(self.dataLabel7, 4, 2)
        else:
            self.dataLabel1.show()
            self.dataLabel8.show()
            self.layout.addWidget(self.dataLabel1, 3, 0)
            self.layout.addWidget(self.dataLabel2, 4, 0)
            self.layout.addWidget(self.dataLabel3, 4, 1)
            self.layout.addWidget(self.dataLabel4, 4, 2)
            self.layout.addWidget(self.dataLabel5, 5, 0)
            self.layout.addWidget(self.dataLabel6, 5, 1)
            self.layout.addWidget(self.dataLabel7, 5, 2)
            self.layout.addWidget(self.dataLabel8, 3, 1)

    def changeView(self, viewName):
        self.currentView = viewName
        self.viewTitleLabel.setText(f'{viewName} Data')
        self.setupLayout()
        if self.filteredData is not None:
            self.updateDisplay(self.filteredData, self.currentTimestamp)

    def initDisplay(self):
        self.show()
        self.animationView.show()

    def terminateDisplay(self):
        if self.event_timer:
            self.event_timer.stop()
        if self.animationView:
            self.animationView.close()
        self.close()

    def updateData(self, data, timestamp):
        try:
            dataArray = [s.strip() for s in data.split(',')]
            if len(dataArray) < 41:
                return
        except:
            return

        self.currentData = dataArray
        self.currentTimestamp = timestamp
        self.updateSampleRate()

        filteredArray = []
        try:
            # Flex (0-4)
            for i in range(5):
                filteredArray.append(self.flex_filters[i].update(dataArray[i]))
            # Thumb acc/gyro (5-10)
            for i in range(6):
                if i < 3:
                    filteredArray.append(self.acc_filters[i].update(dataArray[5 + i]))
                else:
                    filteredArray.append(self.gyro_filters[i - 3].update(dataArray[5 + i]))
            # Pointer acc/gyro (11-16)
            for i in range(6):
                if i < 3:
                    filteredArray.append(self.acc_filters[3 + i].update(dataArray[11 + i]))
                else:
                    filteredArray.append(self.gyro_filters[3 + i - 3].update(dataArray[11 + i]))
            # Middle acc/gyro (17-22)
            for i in range(6):
                if i < 3:
                    filteredArray.append(self.acc_filters[6 + i].update(dataArray[17 + i]))
                else:
                    filteredArray.append(self.gyro_filters[6 + i - 3].update(dataArray[17 + i]))
            # Ring acc/gyro (23-28)
            for i in range(6):
                if i < 3:
                    filteredArray.append(self.acc_filters[9 + i].update(dataArray[23 + i]))
                else:
                    filteredArray.append(self.gyro_filters[9 + i - 3].update(dataArray[23 + i]))
            # Pinky acc/gyro (29-34)
            for i in range(6):
                if i < 3:
                    filteredArray.append(self.acc_filters[12 + i].update(dataArray[29 + i]))
                else:
                    filteredArray.append(self.gyro_filters[12 + i - 3].update(dataArray[29 + i]))
            # Wrist gyro/acc (35-40)
            for i in range(6):
                if i < 3:
                    filteredArray.append(self.gyro_filters[15 + i].update(dataArray[35 + i]))
                else:
                    filteredArray.append(self.acc_filters[15 + i - 3].update(dataArray[35 + i]))
            # Hand indicator (41)
            filteredArray.append(dataArray[41] if len(dataArray) > 41 else '0')
        except ValueError:
            return  # Skip if filtering fails

        self.filteredData = filteredArray
        self.updateDisplay(filteredArray, timestamp)

    def updateDisplay(self, dataArray, timestamp):
        self.timestampLabel.setText(f'Timestamp: {timestamp:.3f}s')
        if len(dataArray) < 41:
            return

        def format_value(value):
            try:
                return f'{float(value):.2f}'
            except (ValueError, TypeError):
                return '--'

        def getFingerAngle(value):
            try:
                flex = float(value)
                return 0.00001595 * flex ** 3 - 0.003083 * flex ** 2 + 0.4174 * flex + 0.8620
            except (ValueError, TypeError):
                return '--'

        def getThumbAngle(value):
            try:
                flex = float(value)
                return 0.000005956 * flex ** 3 - 0.001171 * flex ** 2 + 0.2502 * flex + 2.747
            except (ValueError, TypeError):
                return '--'

        try:
            # get finger angles, convert to joint-based information
            #  and store as variables of right-hand object
            thumbAngle = getThumbAngle(dataArray[0])
            pointerAngle = getFingerAngle(dataArray[1])
            middleAngle = getFingerAngle(dataArray[2])
            ringAngle = getFingerAngle(dataArray[3])
            pinkyAngle = getFingerAngle(dataArray[4])
            self.rightHand.setJ1Angles(thumbAngle, pointerAngle * 0.75, middleAngle * 0.75, ringAngle * 0.75,
                                       pinkyAngle * 0.75)
            self.rightHand.setJ2Angles(pointerAngle * 0.25, middleAngle * 0.25, ringAngle * 0.25, pinkyAngle * 0.25)

            # Update displayed finger angles
            self.animationView.setAngles(
                self.rightHand.pointer.getJ1Flex(),
                self.rightHand.pointer.getJ2Flex()
            )
        except (ValueError, TypeError) as e:
            print(f"Waiting for Legible Flex Values: {e}")

        # View-specific label updates
        if self.currentView == 'Thumb':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[0])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[8])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[9])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[10])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[5])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[6])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[7])}')
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getThumbAngle(dataArray[0]))}')
        elif self.currentView == 'Pointer':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[1])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[14])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[15])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[16])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[11])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[12])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[13])}')
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(dataArray[1]))}')
        elif self.currentView == 'Middle':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[2])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[20])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[21])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[22])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[17])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[18])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[19])}')
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(dataArray[2]))}')
        elif self.currentView == 'Ring':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[3])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[26])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[27])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[28])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[23])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[24])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[25])}')
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(dataArray[3]))}')
        elif self.currentView == 'Pinky':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[4])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[32])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[33])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[34])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[29])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[30])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[31])}')
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(dataArray[4]))}')
        elif self.currentView == 'Wrist':
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[35])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[36])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[37])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[38])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[39])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[40])}')