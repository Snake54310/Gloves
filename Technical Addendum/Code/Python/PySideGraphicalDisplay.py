from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QGridLayout
from PySide6.QtCore import Qt
from scipy import signal
from collections import deque
import time
import math

app = QApplication.instance()
if app is None:
    app = QApplication([])


class LowPassFilter:
    def __init__(self, cutoff_freq=5, sample_rate=100, order=2):
        # Ensure sample rate is reasonable
        if sample_rate < 1:
            sample_rate = 100  # Default fallback

        nyquist = sample_rate / 2

        # Ensure cutoff is less than Nyquist frequency
        # Rule: cutoff must be < sample_rate / 2
        if cutoff_freq >= nyquist:
            cutoff_freq = nyquist * 0.9  # Use 90% of Nyquist

        normal_cutoff = cutoff_freq / nyquist

        # Safety check: must be between 0 and 1
        if normal_cutoff <= 0 or normal_cutoff >= 1:
            normal_cutoff = 0.1  # Conservative default

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

        # Store the latest data - now stores both raw and filtered
        self.currentData = None  # Raw data
        self.filteredData = None  # Filtered data
        self.currentTimestamp = None
        self.currentView = 'Thumb'  # Default view

        # Sample rate measurement
        self.last_update_time = None
        self.sample_intervals = deque(maxlen=50)  # Store last 50 intervals
        self.estimated_sample_rate = 100  # Initial guess, will be updated

        # Initialize filters - we'll create them after we estimate sample rate
        # For now, use a default sample rate of 100 Hz
        self.initializeFilters(sample_rate=100, cutoff_freq=5)

        container = QWidget()
        self.setCentralWidget(container)

        self.layout = QGridLayout(container)

        menuBar = self.menuBar()

        # dropDown Menus
        viewSelectMenu = menuBar.addMenu('View')

        # Dropdown Actions - connect them to view change methods
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

        # Create labels as instance variables
        self.timestampLabel = QLabel('Timestamp: --')
        self.timestampLabel.setAlignment(Qt.AlignCenter)

        self.sampleRateLabel = QLabel('Sample Rate: -- Hz')
        self.sampleRateLabel.setAlignment(Qt.AlignCenter)

        self.viewTitleLabel = QLabel('Thumb Data')
        self.viewTitleLabel.setAlignment(Qt.AlignCenter)
        self.viewTitleLabel.setStyleSheet("font-weight: bold; font-size: 14pt;")

        # Data labels that will change based on view
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

        # Initial layout
        self.setupLayout()

    def initializeFilters(self, sample_rate, cutoff_freq=5):
        """Initialize all filters with given sample rate"""
        # Flex sensors (5 fingers)
        self.flex_filters = [LowPassFilter(cutoff_freq, sample_rate, order=2) for _ in range(5)]

        # Gyro sensors (6 sensors * 3 axes = 18 filters)
        self.gyro_filters = [LowPassFilter(cutoff_freq, sample_rate, order=2) for _ in range(18)]

        # Accelerometer (6 sensors * 3 axes = 18 filters)
        self.acc_filters = [LowPassFilter(cutoff_freq, sample_rate, order=2) for _ in range(18)]

    def updateSampleRate(self):
        """Measure and update the sample rate"""
        current_time = time.time()

        if self.last_update_time is not None:
            interval = current_time - self.last_update_time
            if interval > 0:  # Avoid division by zero
                self.sample_intervals.append(interval)

                # Calculate average sample rate from recent intervals
                if len(self.sample_intervals) >= 10:
                    avg_interval = sum(self.sample_intervals) / len(self.sample_intervals)
                    new_sample_rate = 1.0 / avg_interval

                    # If sample rate changed significantly, reinitialize filters
                    if abs(new_sample_rate - self.estimated_sample_rate) > 10:
                        self.estimated_sample_rate = new_sample_rate
                        self.initializeFilters(self.estimated_sample_rate)
                        print(f"Sample rate updated to: {self.estimated_sample_rate:.1f} Hz")
                    else:
                        self.estimated_sample_rate = new_sample_rate

                    # Update display
                    self.sampleRateLabel.setText(f'Sample Rate: {self.estimated_sample_rate:.1f} Hz')

        self.last_update_time = current_time

    def setupLayout(self):
        """Setup the layout based on current view"""
        # Clear existing layout
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

        # Add timestamp, sample rate, and title (common to all views)
        self.layout.addWidget(self.timestampLabel, 0, 0, 1, 3)
        self.layout.addWidget(self.sampleRateLabel, 1, 0, 1, 3)
        self.layout.addWidget(self.viewTitleLabel, 2, 0, 1, 3)

        if self.currentView == 'Wrist':
            # Wrist has no flex sensor, so different layout
            self.dataLabel1.hide()  # Hide flex label
            self.dataLabel8.hide()
            self.layout.addWidget(self.dataLabel2, 3, 0)
            self.layout.addWidget(self.dataLabel3, 3, 1)
            self.layout.addWidget(self.dataLabel4, 3, 2)
            self.layout.addWidget(self.dataLabel5, 4, 0)
            self.layout.addWidget(self.dataLabel6, 4, 1)
            self.layout.addWidget(self.dataLabel7, 4, 2)

        else:
            # Finger views have flex sensor
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
        """Change which finger/wrist data is being displayed"""
        self.currentView = viewName
        self.viewTitleLabel.setText(f'{viewName} Data')
        self.setupLayout()

        # Update display with current data if available
        if self.filteredData is not None:
            self.updateDisplay(self.filteredData, self.currentTimestamp)

    def initDisplay(self):
        self.show()
        return

    def terminateDisplay(self):
        self.close()
        return

    def updateData(self, data, timestamp):
        """Store new data, apply filters, and update the display"""
        dataArray = data.split(',')

        # Store raw data
        self.currentData = dataArray
        self.currentTimestamp = timestamp

        # Measure sample rate
        self.updateSampleRate()

        # Check if we have enough data
        if len(dataArray) < 41:
            return

        # Apply filters to all data
        filteredArray = []

        # Filter flex sensors (indices 0-4)
        for i in range(5):
            filtered = self.flex_filters[i].update(dataArray[i])
            filteredArray.append(filtered)

        # Filter thumb sensors (acc: 5-7, gyro: 8-10)
        for i in range(6):
            if i < 3:  # Acceleration
                filtered = self.acc_filters[i].update(dataArray[5 + i])
            else:  # Gyro
                filtered = self.gyro_filters[i - 3].update(dataArray[5 + i])
            filteredArray.append(filtered)

        # Filter pointer sensors (acc: 11-13, gyro: 14-16)
        for i in range(6):
            if i < 3:  # Acceleration
                filtered = self.acc_filters[3 + i].update(dataArray[11 + i])
            else:  # Gyro
                filtered = self.gyro_filters[3 + i - 3].update(dataArray[11 + i])
            filteredArray.append(filtered)

        # Filter middle sensors (acc: 17-19, gyro: 20-22)
        for i in range(6):
            if i < 3:  # Acceleration
                filtered = self.acc_filters[6 + i].update(dataArray[17 + i])
            else:  # Gyro
                filtered = self.gyro_filters[6 + i - 3].update(dataArray[17 + i])
            filteredArray.append(filtered)

        # Filter ring sensors (acc: 23-25, gyro: 26-28)
        for i in range(6):
            if i < 3:  # Acceleration
                filtered = self.acc_filters[9 + i].update(dataArray[23 + i])
            else:  # Gyro
                filtered = self.gyro_filters[9 + i - 3].update(dataArray[23 + i])
            filteredArray.append(filtered)

        # Filter pinky sensors (acc: 29-31, gyro: 32-34)
        for i in range(6):
            if i < 3:  # Acceleration
                filtered = self.acc_filters[12 + i].update(dataArray[29 + i])
            else:  # Gyro
                filtered = self.gyro_filters[12 + i - 3].update(dataArray[29 + i])
            filteredArray.append(filtered)

        # Filter wrist sensors (gyro: 35-37, acc: 38-40)
        for i in range(6):
            if i < 3:  # Gyro
                filtered = self.gyro_filters[15 + i].update(dataArray[35 + i])
            else:  # Acceleration
                filtered = self.acc_filters[15 + i - 3].update(dataArray[35 + i])
            filteredArray.append(filtered)

        # Add hand indicator (no filtering needed)
        filteredArray.append(dataArray[41] if len(dataArray) > 41 else '0')

        # Store filtered data
        self.filteredData = filteredArray

        # Update the display with filtered data
        self.updateDisplay(filteredArray, timestamp)

        return

    def updateDisplay(self, dataArray, timestamp):
        """Update the labels based on current view and data"""

        # Update timestamp
        self.timestampLabel.setText(f'Timestamp: {timestamp:.3f}s')

        # Check if we have enough data
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
                angle = 0.00001595*flex**3 - 0.003083*flex**2 + 0.4174*flex + 0.8620
                return angle
            except (ValueError, TypeError):
                return '--'

        def getThumbAngle(value):
            try:
                flex = float(value)
                angle = 0.000005956*flex**3 - 0.001171*flex**2 + 0.2502*flex + 2.747
                return angle # poor approximation for now, will need to do actual collection of thumb data
            except (ValueError, TypeError):
                return '--'

        # Update based on current view (using filtered data)
        if self.currentView == 'Thumb':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[0])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[8])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[9])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[10])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[5])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[6])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[7])}')
            # Live Angle display:
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getThumbAngle(format_value(dataArray[0])))}')

        elif self.currentView == 'Pointer':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[1])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[14])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[15])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[16])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[11])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[12])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[13])}')
            # Live Angle display:
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(format_value(dataArray[1])))}')


        elif self.currentView == 'Middle':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[2])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[20])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[21])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[22])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[17])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[18])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[19])}')
            # Live Angle display:
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(format_value(dataArray[2])))}')

        elif self.currentView == 'Ring':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[3])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[26])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[27])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[28])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[23])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[24])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[25])}')
            # Live Angle display:
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(format_value(dataArray[3])))}')

        elif self.currentView == 'Pinky':
            self.dataLabel1.setText(f'Flex: {format_value(dataArray[4])}')
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[32])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[33])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[34])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[29])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[30])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[31])}')
            # Live Angle display:
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(format_value(dataArray[4])))}')

        elif self.currentView == 'Wrist':
            # Wrist has no flex sensor
            self.dataLabel2.setText(f'Gyro X: {format_value(dataArray[35])}')
            self.dataLabel3.setText(f'Gyro Y: {format_value(dataArray[36])}')
            self.dataLabel4.setText(f'Gyro Z: {format_value(dataArray[37])}')
            self.dataLabel5.setText(f'Acc X: {format_value(dataArray[38])}')
            self.dataLabel6.setText(f'Acc Y: {format_value(dataArray[39])}')
            self.dataLabel7.setText(f'Acc Z: {format_value(dataArray[40])}')
            # Live Angle display:
            self.dataLabel8.setText(f'Flex Angle (deg): {format_value(getFingerAngle(format_value(dataArray[5])))}')