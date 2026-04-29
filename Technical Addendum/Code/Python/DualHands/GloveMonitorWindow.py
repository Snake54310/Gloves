"""
GloveMonitorWindow.py

Live sensor monitor window for BOTH gloves.  Acts as the central coordinator
between:
    SensorDataProcessor      — filters incoming sensor data for each glove
    RightHandKinematics      — kinematics for the right glove
    LeftHandKinematics       — kinematics for the left glove
    HandRenderer             — renders both hands in a single Qt3D window

Public interface (called by SensorRead3_0.py):
    GloveMonitorWindow()
    .initDisplay()
    .updateData(data: str, timestamp: float, hand_side: str)
        hand_side must be 'right' or 'left'
    .terminateDisplay()
    .deleteLater()

UI additions over the single-glove version:
    • "Hand" dropdown in the menu bar — selects which hand's data are shown
      in the sensor-data labels (Right / Left).
    • The View menu still selects which finger/wrist to display.
    • "Zero Gyro" and "Record Gyro" operate on whichever hand is currently
      selected in the Hand dropdown.
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QGridLayout,
    QPushButton, QComboBox,
)
from PySide6.QtCore import Qt, QTimer

from SensorDataProcessor import SensorProcessor, GyroRecorder, finger_flex_to_angle, thumb_flex_to_angle
from RightHandKinematics import RightHand
from LeftHandKinematics  import LeftHand
from HandRenderer        import AnimationWindow


# ---------------------------------------------------------------------------
# QApplication singleton guard
# ---------------------------------------------------------------------------
_app = QApplication.instance()
if _app is None:
    _app = QApplication([])


# ---------------------------------------------------------------------------
# GloveMonitorWindow
# ---------------------------------------------------------------------------

class GloveMonitorWindow(QMainWindow):
    """
    Main live-display window for dual-glove sensor data.

    Owns two independent processing pipelines (one per hand):
        processor_right / processor_left   — SensorProcessor instances
        rightHand / leftHand               — kinematic models
        gyroRecorder_right / _left         — optional research logging

    The 3D renderer (AnimationWindow) contains both hand models and is
    updated from either pipeline depending on which hand sent new data.
    """

    ANIMATION_SAMPLE_RATE_MULTIPLIER = 4 # THIS IS THE NUMBER YOU CHANGE IF YOUR COMPUTER IS LAGGING

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Acquisition Window')

        # --- Right-hand pipeline ---
        self.processor_right  = SensorProcessor(initial_sample_rate=100, cutoff_freq=5)
        self.rightHand        = RightHand()
        self.gyroRecorder_right = GyroRecorder()

        # --- Left-hand pipeline ---
        self.processor_left   = SensorProcessor(initial_sample_rate=100, cutoff_freq=5)
        self.leftHand         = LeftHand()
        self.gyroRecorder_left  = GyroRecorder()

        # --- Per-hand cached filtered data (for view-switch refresh) ---
        self._filtered_right     = None
        self._timestamp_right    = None
        self._filtered_left      = None
        self._timestamp_left     = None

        # --- Frame counters for animation throttling ---
        self._sample_index_right = 0
        self._sample_index_left  = 0

        # --- UI state ---
        self._current_view = 'Thumb'    # which finger/wrist is shown in labels
        self._current_hand = 'right'    # which hand's data the labels show

        self._build_ui()

        self.animationView = AnimationWindow()

        # Qt event pump — keeps Qt alive while Tkinter owns the main loop
        self._event_timer = QTimer()
        self._event_timer.timeout.connect(QApplication.processEvents)
        self._event_timer.start(10)

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        container = QWidget()
        self.setCentralWidget(container)
        self._layout = QGridLayout(container)
        self._build_menu()
        self._build_labels()
        self._build_buttons()
        self._apply_layout()

    def _build_menu(self):
        # View menu — which finger/wrist
        view_menu = self.menuBar().addMenu('View')
        for name in ('Thumb', 'Pointer', 'Middle', 'Ring', 'Pinky', 'Wrist'):
            action = view_menu.addAction(name)
            action.triggered.connect(lambda checked, n=name: self._change_view(n))

        # Hand menu — which glove's data is shown
        hand_menu = self.menuBar().addMenu('Hand')
        for name in ('right', 'left'):
            action = hand_menu.addAction(name.capitalize())
            action.triggered.connect(lambda checked, h=name: self._change_hand(h))

    def _build_labels(self):
        self.timestampLabel  = self._centered_label('Timestamp: --')
        self.sampleRateLabel = self._centered_label('Sample Rate: -- Hz')
        self.handLabel       = self._centered_label('Hand: Right')
        self.handLabel.setStyleSheet("color: #2255aa; font-weight: bold;")
        self.viewTitleLabel  = self._centered_label('Thumb Data')
        self.viewTitleLabel.setStyleSheet("font-weight: bold; font-size: 14pt;")

        self.flexLabel        = self._centered_label('Flex: --')
        self.flexAngleLabel   = self._centered_label('Flex Angle (deg): --')
        self.gyroXLabel       = self._centered_label('Gyro X: --')
        self.gyroYLabel       = self._centered_label('Gyro Y: --')
        self.gyroZLabel       = self._centered_label('Gyro Z: --')
        self.accXLabel        = self._centered_label('Acc X: --')
        self.accYLabel        = self._centered_label('Acc Y: --')
        self.accZLabel        = self._centered_label('Acc Z: --')
        self.orientationLabel = self._centered_label('Wrist Orientation (deg): --')

    def _build_buttons(self):
        self.gyroResetButton  = QPushButton("Zero Gyro", self)
        self.gyroResetButton.clicked.connect(self._zero_gyros)

        self.gyroRecordButton = QPushButton("Record Gyro", self)
        self.gyroRecordButton.clicked.connect(self._start_recording)

    def _apply_layout(self):
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

        self._layout.addWidget(self.timestampLabel,  0, 0, 1, 3)
        self._layout.addWidget(self.sampleRateLabel, 1, 0, 1, 3)
        self._layout.addWidget(self.handLabel,       2, 0, 1, 3)
        self._layout.addWidget(self.viewTitleLabel,  3, 0, 1, 3)

        if self._current_view == 'Wrist':
            self.flexLabel.hide()
            self.flexAngleLabel.hide()
            self.orientationLabel.show()
            self._layout.addWidget(self.gyroXLabel,       4, 0)
            self._layout.addWidget(self.gyroYLabel,       4, 1)
            self._layout.addWidget(self.gyroZLabel,       4, 2)
            self._layout.addWidget(self.accXLabel,        5, 0)
            self._layout.addWidget(self.accYLabel,        5, 1)
            self._layout.addWidget(self.accZLabel,        5, 2)
            self._layout.addWidget(self.orientationLabel, 6, 0, 1, 3)
            self._layout.addWidget(self.gyroResetButton,  7, 0, 1, 3)
            self._layout.addWidget(self.gyroRecordButton, 8, 0, 1, 3)
        else:
            self.flexLabel.show()
            self.flexAngleLabel.show()
            self.orientationLabel.hide()
            self._layout.addWidget(self.flexLabel,        4, 0)
            self._layout.addWidget(self.flexAngleLabel,   4, 1)
            self._layout.addWidget(self.gyroXLabel,       5, 0)
            self._layout.addWidget(self.gyroYLabel,       5, 1)
            self._layout.addWidget(self.gyroZLabel,       5, 2)
            self._layout.addWidget(self.accXLabel,        6, 0)
            self._layout.addWidget(self.accYLabel,        6, 1)
            self._layout.addWidget(self.accZLabel,        6, 2)
            self._layout.addWidget(self.gyroResetButton,  7, 0, 1, 3)
            self._layout.addWidget(self.gyroRecordButton, 8, 0, 1, 3)

    @staticmethod
    def _centered_label(text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        return label

    # ------------------------------------------------------------------ #
    # View / hand switching                                                #
    # ------------------------------------------------------------------ #

    def _change_view(self, view_name):
        self._current_view = view_name
        self.viewTitleLabel.setText(f'{view_name} Data')
        self._apply_layout()
        self._refresh_labels()

    def _change_hand(self, hand_side):
        """Switch which hand's data is shown in the labels."""
        self._current_hand = hand_side
        colour = '#2255aa' if hand_side == 'right' else '#226622'
        self.handLabel.setStyleSheet(f"color: {colour}; font-weight: bold;")
        self.handLabel.setText(f'Hand: {hand_side.capitalize()}')
        self._refresh_labels()

    def _refresh_labels(self):
        """Re-display cached data for the currently selected hand and view."""
        if self._current_hand == 'right' and self._filtered_right is not None:
            self._update_labels(self._filtered_right, self._timestamp_right, 'right')
        elif self._current_hand == 'left' and self._filtered_left is not None:
            self._update_labels(self._filtered_left, self._timestamp_left, 'left')

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def initDisplay(self):
        self.show()
        self.animationView.show()

    def terminateDisplay(self):
        self._event_timer.stop()
        self.animationView.close()
        self.close()

    def updateData(self, data: str, timestamp: float, hand_side: str):
        """
        Process one incoming data frame from one glove.

        Args:
            data:      raw comma-separated string (41 values) from serial.
            timestamp: seconds since acquisition start.
            hand_side: 'right' or 'left'
        """
        try:
            data_array = [s.strip() for s in data.split(',')]
            if len(data_array) < 41:
                return
        except Exception:
            return

        if hand_side == 'right':
            processor = self.processor_right
            hand_model = self.rightHand
            gyroRec    = self.gyroRecorder_right
        else:
            processor = self.processor_left
            hand_model = self.leftHand
            gyroRec    = self.gyroRecorder_left

        processor.update_sample_rate()
        filtered = processor.process(data_array)
        if filtered is None:
            return

        # Cache per hand
        if hand_side == 'right':
            self._filtered_right  = filtered
            self._timestamp_right = timestamp
        else:
            self._filtered_left   = filtered
            self._timestamp_left  = timestamp

        # Update labels only if this is the currently-displayed hand
        if hand_side == self._current_hand:
            self.sampleRateLabel.setText(
                f'Sample Rate: {processor.estimated_sample_rate:.1f} Hz'
            )
            self._update_labels(filtered, timestamp, hand_side)

        # Kinematics
        self._update_kinematics(filtered, timestamp, hand_model, gyroRec)

        # Animation throttle
        if hand_side == 'right':
            self._sample_index_right += 1
            if self._sample_index_right >= self.ANIMATION_SAMPLE_RATE_MULTIPLIER:
                self._sample_index_right = 0
                self._update_animation_right(filtered)
        else:
            self._sample_index_left += 1
            if self._sample_index_left >= self.ANIMATION_SAMPLE_RATE_MULTIPLIER:
                self._sample_index_left = 0
                self._update_animation_left(filtered)

    # ------------------------------------------------------------------ #
    # Internal update helpers                                              #
    # ------------------------------------------------------------------ #

    def _update_kinematics(self, d, timestamp, hand_model, gyroRec):
        """Push filtered data into a hand kinematic model (right or left)."""
        thumb_angle   = thumb_flex_to_angle(d[0])
        pointer_angle = finger_flex_to_angle(d[1])
        middle_angle  = finger_flex_to_angle(d[2])
        ring_angle    = finger_flex_to_angle(d[3])
        pinky_angle   = finger_flex_to_angle(d[4])

        hand_model.set_j1_angles(
            thumb_angle,
            pointer_angle * 0.75 if pointer_angle else 0,
            middle_angle  * 0.75 if middle_angle  else 0,
            ring_angle    * 0.75 if ring_angle    else 0,
            pinky_angle   * 0.75 if pinky_angle   else 0,
        )
        hand_model.set_j2_angles(
            pointer_angle * 0.25 if pointer_angle else 0,
            middle_angle  * 0.25 if middle_angle  else 0,
            ring_angle    * 0.25 if ring_angle    else 0,
            pinky_angle   * 0.25 if pinky_angle   else 0,
        )

        # Use the processor associated with this hand for sample rate
        if hand_model is self.rightHand:
            hand_model.update_sample_rate(self.processor_right.estimated_sample_rate)
        else:
            hand_model.update_sample_rate(self.processor_left.estimated_sample_rate)

        try:
            hand_model.update_orientation(float(d[38]), float(d[39]), float(d[40]))
            hand_model.update_orientation_fingers(
                float(d[8]),  float(d[9]),  float(d[10]),
                float(d[14]), float(d[15]), float(d[16]),
                float(d[20]), float(d[21]), float(d[22]),
                float(d[26]), float(d[27]), float(d[28]),
                float(d[32]), float(d[33]), float(d[34]),
            )
        except (ValueError, TypeError) as e:
            print(f"Waiting for gyro read: {e}")
            return

        try:
            gyroRec.record(
                timestamp,
                wrist   = (float(d[38]), float(d[39]), float(d[40])),
                thumb   = (float(d[8]),  float(d[9]),  float(d[10])),
                pointer = (float(d[14]), float(d[15]), float(d[16])),
                middle  = (float(d[20]), float(d[21]), float(d[22])),
                ring    = (float(d[26]), float(d[27]), float(d[28])),
                pinky   = (float(d[32]), float(d[33]), float(d[34])),
            )
        except (ValueError, TypeError):
            pass

    def _update_animation_right(self, d):
        j1 = self.rightHand.get_j1_angles()
        j2 = self.rightHand.get_j2_angles()
        self.animationView.setAnglesPointer_R(j1[1], j2[0])
        self.animationView.setAnglesMiddle_R( j1[2], j2[1])
        self.animationView.setAnglesRing_R(   j1[3], j2[2])
        self.animationView.setAnglesPinky_R(  j1[4], j2[3])
        self.animationView.setAngleThumb_R(   j1[0])
        self.animationView.setOrientationPalm_R(*self.rightHand.get_orientation_q())
        self.animationView.setOrientationFingers_R(self.rightHand.get_relative_orientations_q())

    def _update_animation_left(self, d):
        j1 = self.leftHand.get_j1_angles()
        j2 = self.leftHand.get_j2_angles()
        self.animationView.setAnglesPointer_L(j1[1], j2[0])
        self.animationView.setAnglesMiddle_L( j1[2], j2[1])
        self.animationView.setAnglesRing_L(   j1[3], j2[2])
        self.animationView.setAnglesPinky_L(  j1[4], j2[3])
        self.animationView.setAngleThumb_L(   j1[0])
        self.animationView.setOrientationPalm_L(*self.leftHand.get_orientation_q())
        self.animationView.setOrientationFingers_L(self.leftHand.get_relative_orientations_q())

    def _update_labels(self, d, timestamp, hand_side):
        """Update display labels for the currently-selected view."""
        self.timestampLabel.setText(f'Timestamp: {timestamp:.3f}s')

        def fmt(value):
            try:
                return f'{float(value):.2f}'
            except (ValueError, TypeError):
                return '--'

        view = self._current_view

        FINGER_OFFSETS = {
            'Thumb':   (0,   5,  8),
            'Pointer': (1,  11, 14),
            'Middle':  (2,  17, 20),
            'Ring':    (3,  23, 26),
            'Pinky':   (4,  29, 32),
        }

        if view in FINGER_OFFSETS:
            flex_i, acc_i, gyro_i = FINGER_OFFSETS[view]
            flex_val = d[flex_i]
            angle_fn = thumb_flex_to_angle if view == 'Thumb' else finger_flex_to_angle
            angle    = angle_fn(flex_val)

            self.flexLabel.setText(     f'Flex: {fmt(flex_val)}')
            self.flexAngleLabel.setText(f'Flex Angle (deg): {fmt(angle)}')
            self.gyroXLabel.setText(    f'Gyro X: {fmt(d[gyro_i])}')
            self.gyroYLabel.setText(    f'Gyro Y: {fmt(d[gyro_i + 1])}')
            self.gyroZLabel.setText(    f'Gyro Z: {fmt(d[gyro_i + 2])}')
            self.accXLabel.setText(     f'Acc X: {fmt(d[acc_i])}')
            self.accYLabel.setText(     f'Acc Y: {fmt(d[acc_i + 1])}')
            self.accZLabel.setText(     f'Acc Z: {fmt(d[acc_i + 2])}')

        elif view == 'Wrist':
            self.gyroXLabel.setText(f'Gyro X: {fmt(d[38])}')
            self.gyroYLabel.setText(f'Gyro Y: {fmt(d[39])}')
            self.gyroZLabel.setText(f'Gyro Z: {fmt(d[40])}')
            self.accXLabel.setText( f'Acc X: {fmt(d[35])}')
            self.accYLabel.setText( f'Acc Y: {fmt(d[36])}')
            self.accZLabel.setText( f'Acc Z: {fmt(d[37])}')

            hand_model = self.rightHand if hand_side == 'right' else self.leftHand
            ox, oy, oz = hand_model.get_orientation()
            self.orientationLabel.setText(
                f'Wrist Orientation (deg):\n'
                f'X = {fmt(ox)}\n'
                f'Y = {fmt(oy)}\n'
                f'Z = {fmt(oz)}'
            )

    # ------------------------------------------------------------------ #
    # Button handlers                                                      #
    # ------------------------------------------------------------------ #

    def _zero_gyros(self):
        """Zero the orientation of whichever hand is currently selected."""
        if self._current_hand == 'right':
            self.rightHand.zero_orientation()
            self.gyroRecorder_right.stop_episode()
        else:
            self.leftHand.zero_orientation()
            self.gyroRecorder_left.stop_episode()
        print(f"Gyroscope orientation zeroed ({self._current_hand})")

    def _start_recording(self):
        """Start a gyro recording episode for the currently selected hand."""
        if self._current_hand == 'right':
            self.gyroRecorder_right.start_episode()
        else:
            self.gyroRecorder_left.start_episode()
