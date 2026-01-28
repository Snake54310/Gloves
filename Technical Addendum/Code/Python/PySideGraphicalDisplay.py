from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QGridLayout
from PySide6.QtCore import Qt
from scipy import signal
from collections import deque
import time

app = QApplication.instance()
if app is None:
    app = QApplication([])


class LowPassFilter:
    def __init__(self, cutoff_freq=5, sample_rate=27.4, order=2):
        nyquist = sample_rate / 2
        normal_cutoff = cutoff_freq / nyquist
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
            self.layout.addWidget(self.dataLabel2, 3, 0)
            self.layout.addWidget(self.dataLabel3, 3, 1)
            self.layout.addWidget(self.dataLabel4, 3, 2)
            self.layout.addWidget(self.dataLabel5, 4, 0)
            self.layout.addWidget(self.dataLabel6, 4, 1)
            self.layout.addWidget(self.dataLabel7, 4, 2)
        else:
            # Finger views have flex sensor
            self.dataLabel1.show()
            self.layout.addWidget(self.dataLabel1, 3, 1)
            self.layout.addWidget(self.dataLabel2, 4, 0)
            self.layout.addWidget(self.dataLabel3, 4, 1)
            self.layout.addWidget(self.dataLabel4, 4, 2)
            self.layout.addWidget(self.dataLabel5, 5, 0)
            self.layout.addWidget(self.dataLabel6, 5, 1)
            self.layout.addWidget(self.dataLabel7, 5, 2)

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

        # Update based on current view (using filtered data)
        if self.currentView == 'Thumb':
            self.dataLabel1.setText(f'Flex: {dataArray[0]:.2f}')
            self.dataLabel2.setText(f'Gyro X: {dataArray[8]:.2f}')
            self.dataLabel3.setText(f'Gyro Y: {dataArray[9]:.2f}')
            self.dataLabel4.setText(f'Gyro Z: {dataArray[10]:.2f}')
            self.dataLabel5.setText(f'Acc X: {dataArray[5]:.2f}')
            self.dataLabel6.setText(f'Acc Y: {dataArray[6]:.2f}')
            self.dataLabel7.setText(f'Acc Z: {dataArray[7]:.2f}')

        elif self.currentView == 'Pointer':
            self.dataLabel1.setText(f'Flex: {dataArray[1]:.2f}')
            self.dataLabel2.setText(f'Gyro X: {dataArray[14]:.2f}')
            self.dataLabel3.setText(f'Gyro Y: {dataArray[15]:.2f}')
            self.dataLabel4.setText(f'Gyro Z: {dataArray[16]:.2f}')
            self.dataLabel5.setText(f'Acc X: {dataArray[11]:.2f}')
            self.dataLabel6.setText(f'Acc Y: {dataArray[12]:.2f}')
            self.dataLabel7.setText(f'Acc Z: {dataArray[13]:.2f}')

        elif self.currentView == 'Middle':
            self.dataLabel1.setText(f'Flex: {dataArray[2]:.2f}')
            self.dataLabel2.setText(f'Gyro X: {dataArray[20]:.2f}')
            self.dataLabel3.setText(f'Gyro Y: {dataArray[21]:.2f}')
            self.dataLabel4.setText(f'Gyro Z: {dataArray[22]:.2f}')
            self.dataLabel5.setText(f'Acc X: {dataArray[17]:.2f}')
            self.dataLabel6.setText(f'Acc Y: {dataArray[18]:.2f}')
            self.dataLabel7.setText(f'Acc Z: {dataArray[19]:.2f}')

        elif self.currentView == 'Ring':
            self.dataLabel1.setText(f'Flex: {dataArray[3]:.2f}')
            self.dataLabel2.setText(f'Gyro X: {dataArray[26]:.2f}')
            self.dataLabel3.setText(f'Gyro Y: {dataArray[27]:.2f}')
            self.dataLabel4.setText(f'Gyro Z: {dataArray[28]:.2f}')
            self.dataLabel5.setText(f'Acc X: {dataArray[23]:.2f}')
            self.dataLabel6.setText(f'Acc Y: {dataArray[24]:.2f}')
            self.dataLabel7.setText(f'Acc Z: {dataArray[25]:.2f}')

        elif self.currentView == 'Pinky':
            self.dataLabel1.setText(f'Flex: {dataArray[4]:.2f}')
            self.dataLabel2.setText(f'Gyro X: {dataArray[32]:.2f}')
            self.dataLabel3.setText(f'Gyro Y: {dataArray[33]:.2f}')
            self.dataLabel4.setText(f'Gyro Z: {dataArray[34]:.2f}')
            self.dataLabel5.setText(f'Acc X: {dataArray[29]:.2f}')
            self.dataLabel6.setText(f'Acc Y: {dataArray[30]:.2f}')
            self.dataLabel7.setText(f'Acc Z: {dataArray[31]:.2f}')

        elif self.currentView == 'Wrist':
            # Wrist has no flex sensor
            self.dataLabel2.setText(f'Gyro X: {dataArray[35]:.2f}')
            self.dataLabel3.setText(f'Gyro Y: {dataArray[36]:.2f}')
            self.dataLabel4.setText(f'Gyro Z: {dataArray[37]:.2f}')
            self.dataLabel5.setText(f'Acc X: {dataArray[38]:.2f}')
            self.dataLabel6.setText(f'Acc Y: {dataArray[39]:.2f}')
            self.dataLabel7.setText(f'Acc Z: {dataArray[40]:.2f}')