"""
GloveMonitorWindow.py

Live sensor monitor window for the right glove. Acts as the central coordinator
between:
    SensorDataProcessor      — filters incoming sensor data
    RightHandKinematics      — kinematics for the right glove
    HandRenderer             — renders the hand in a Qt3D window

Public interface (called by SensorRead3_0.py):
    GloveMonitorWindow()
    .initDisplay()
    .updateData(data: str, timestamp: float)
    .terminateDisplay()
    .deleteLater()
"""

import joblib
import pandas as pd

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QGridLayout,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer

from SensorDataProcessor import SensorProcessor, GyroRecorder, PositionRecorder, finger_flex_to_angle, thumb_flex_to_angle
from HandKinematics import RightHand
from HandRenderer        import AnimationWindow


_app = QApplication.instance()
if _app is None:
    _app = QApplication([])


class GloveMonitorWindow(QMainWindow):
    ANIMATION_SAMPLE_RATE_MULTIPLIER = 2

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Acquisition Window')

        self.processor        = SensorProcessor(initial_sample_rate=100, cutoff_freq=5)
        self.rightHand        = RightHand()
        self.gyroRecorder     = GyroRecorder()
        self.positionRecorder = PositionRecorder()

        self._filtered_data     = None
        self._current_timestamp = None
        self._sample_index      = 0
        self._current_view      = 'Thumb'
        self._recording_mode    = 'Disabled'

        self.model = None
        self.predictionLabel = None

        self._build_ui()
        self.animationView = AnimationWindow()

        self._event_timer = QTimer()
        self._event_timer.timeout.connect(QApplication.processEvents)
        self._event_timer.start(10)

    def _build_ui(self):
        container = QWidget()
        self.setCentralWidget(container)
        self._layout = QGridLayout(container)
        self._build_menu()
        self._build_labels()
        self._build_buttons()
        self._apply_layout()

    def _build_menu(self):
        view_menu = self.menuBar().addMenu('View')
        for name in ('Thumb', 'Pointer', 'Middle', 'Ring', 'Pinky', 'Wrist'):
            action = view_menu.addAction(name)
            action.triggered.connect(lambda checked, n=name: self._change_view(n))

        record_menu = self.menuBar().addMenu('Recording')
        for mode in ('Disabled', 'Continuous', 'Snapshots', 'Identify'):
            action = record_menu.addAction(mode)
            action.triggered.connect(lambda checked, m=mode: self._set_recording_mode(m))

    def _build_labels(self):
        self.timestampLabel  = self._centered_label('Timestamp: --')
        self.sampleRateLabel = self._centered_label('Sample Rate: -- Hz')
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

        self.predictionLabel = self._centered_label('Predicted Pose: --')
        self.predictionLabel.setStyleSheet("font-weight: bold; color: #22aa22; font-size: 12pt;")

    def _build_buttons(self):
        self.gyroResetButton  = QPushButton("Zero Gyro", self)
        self.gyroResetButton.clicked.connect(self._zero_gyros)

        self.gyroRecordButton = QPushButton("Record Gyro", self)
        self.gyroRecordButton.clicked.connect(self.gyroRecorder.start_episode)

        self.gyroStopButton   = QPushButton("Stop Gyro Recording", self)
        self.gyroStopButton.clicked.connect(self.gyroRecorder.stop_episode)

        self.beginPositionButton = QPushButton("Begin Position Recording", self)
        self.beginPositionButton.clicked.connect(self.positionRecorder.start_continuous)

        self.endPositionButton   = QPushButton("End Position Recording", self)
        self.endPositionButton.clicked.connect(self.positionRecorder.stop_continuous)

        self.guessButton = QPushButton("Guess Current Pose", self)
        self.guessButton.clicked.connect(self._guess_pose)

        self.snapshotButtons = {}
        for label in PositionRecorder.SNAPSHOT_LABELS:
            display_text = label.replace('_', ' ').title()
            btn = QPushButton(display_text, self)
            btn.clicked.connect(lambda checked, l=label: self._record_snapshot(l))
            self.snapshotButtons[label] = btn

    def _apply_layout(self):
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

        self._layout.addWidget(self.timestampLabel,  0, 0, 1, 3)
        self._layout.addWidget(self.sampleRateLabel, 1, 0, 1, 3)
        self._layout.addWidget(self.viewTitleLabel,  2, 0, 1, 3)

        if self._current_view == 'Wrist':
            self.flexLabel.hide()
            self.flexAngleLabel.hide()
            self.orientationLabel.show()
            self._layout.addWidget(self.gyroXLabel,       3, 0)
            self._layout.addWidget(self.gyroYLabel,       3, 1)
            self._layout.addWidget(self.gyroZLabel,       3, 2)
            self._layout.addWidget(self.accXLabel,        4, 0)
            self._layout.addWidget(self.accYLabel,        4, 1)
            self._layout.addWidget(self.accZLabel,        4, 2)
            self._layout.addWidget(self.orientationLabel, 5, 0, 1, 3)
        else:
            self.flexLabel.show()
            self.flexAngleLabel.show()
            self.orientationLabel.hide()
            self._layout.addWidget(self.flexLabel,        3, 0)
            self._layout.addWidget(self.flexAngleLabel,   3, 1)
            self._layout.addWidget(self.gyroXLabel,       4, 0)
            self._layout.addWidget(self.gyroYLabel,       4, 1)
            self._layout.addWidget(self.gyroZLabel,       4, 2)
            self._layout.addWidget(self.accXLabel,        5, 0)
            self._layout.addWidget(self.accYLabel,        5, 1)
            self._layout.addWidget(self.accZLabel,        5, 2)

        self._layout.addWidget(self.gyroResetButton,  6, 0, 1, 3)
        self._layout.addWidget(self.gyroRecordButton, 7, 0, 1, 3)
        self._layout.addWidget(self.gyroStopButton,   8, 0, 1, 3)

        self._layout.addWidget(self.beginPositionButton, 9, 0, 1, 3)
        self._layout.addWidget(self.endPositionButton,  10, 0, 1, 3)

        if self._recording_mode == 'Identify':
            self._layout.addWidget(self.guessButton, 11, 0, 1, 3)
            self._layout.addWidget(self.predictionLabel, 12, 0, 1, 3)

        if self._recording_mode == 'Snapshots':
            row = 11
            for btn in self.snapshotButtons.values():
                self._layout.addWidget(btn, row, 0, 1, 3)
                row += 1

    @staticmethod
    def _centered_label(text):
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        return label

    def _change_view(self, view_name):
        self._current_view = view_name
        self.viewTitleLabel.setText(f'{view_name} Data')
        self._apply_layout()
        if self._filtered_data is not None:
            self._update_labels(self._filtered_data, self._current_timestamp)

    def _set_recording_mode(self, mode):
        self._recording_mode = mode
        print(f"Recording mode changed to: {mode}")

        if mode == 'Continuous':
            self.positionRecorder.start_continuous()
        elif mode == 'Disabled':
            self.positionRecorder.stop_continuous()

        self._apply_layout()

    # =====================================================================
    # PUBLIC INTERFACE REQUIRED BY SensorRead3.0.py
    # =====================================================================
    def initDisplay(self):
        self.show()
        self.animationView.show()

    def terminateDisplay(self):
        self._event_timer.stop()
        self.animationView.close()
        self.close()

    def updateData(self, data: str, timestamp: float):
        try:
            data_array = [s.strip() for s in data.split(',')]
            if len(data_array) < 41:
                return
        except Exception:
            return

        self.processor.update_sample_rate()
        filtered = self.processor.process(data_array)
        if filtered is None:
            return

        self._filtered_data     = filtered
        self._current_timestamp = timestamp

        self.sampleRateLabel.setText(f'Sample Rate: {self.processor.estimated_sample_rate:.1f} Hz')

        self._update_kinematics(filtered, timestamp)
        self._update_labels(filtered, timestamp)

        self._sample_index += 1
        if self._sample_index >= self.ANIMATION_SAMPLE_RATE_MULTIPLIER:
            self._sample_index = 0
            self._update_animation(filtered)

    # =====================================================================
    # INTERNAL HELPERS
    # =====================================================================
    def _update_kinematics(self, d, timestamp):
        thumb_angle   = thumb_flex_to_angle(d[0])
        pointer_angle = finger_flex_to_angle(d[1])
        middle_angle  = finger_flex_to_angle(d[2])
        ring_angle    = finger_flex_to_angle(d[3])
        pinky_angle   = finger_flex_to_angle(d[4])

        self.rightHand.set_j1_angles(
            thumb_angle,
            pointer_angle * 0.75 if pointer_angle else 0,
            middle_angle  * 0.75 if middle_angle  else 0,
            ring_angle    * 0.75 if ring_angle    else 0,
            pinky_angle   * 0.75 if pinky_angle   else 0,
        )
        self.rightHand.set_j2_angles(
            pointer_angle * 0.25 if pointer_angle else 0,
            middle_angle  * 0.25 if middle_angle  else 0,
            ring_angle    * 0.25 if ring_angle    else 0,
            pinky_angle   * 0.25 if pinky_angle   else 0,
        )

        self.rightHand.update_sample_rate(self.processor.estimated_sample_rate)

        try:
            self.rightHand.update_orientation(float(d[38]), float(d[39]), float(d[40]))
            self.rightHand.update_orientation_fingers(
                float(d[8]), float(d[9]), float(d[10]),
                float(d[14]), float(d[15]), float(d[16]),
                float(d[20]), float(d[21]), float(d[22]),
                float(d[26]), float(d[27]), float(d[28]),
                float(d[32]), float(d[33]), float(d[34]),
            )
        except (ValueError, TypeError):
            return

        try:
            self.gyroRecorder.record(
                timestamp,
                wrist=(float(d[38]), float(d[39]), float(d[40])),
                thumb=(float(d[8]), float(d[9]), float(d[10])),
                pointer=(float(d[14]), float(d[15]), float(d[16])),
                middle=(float(d[20]), float(d[21]), float(d[22])),
                ring=(float(d[26]), float(d[27]), float(d[28])),
                pinky=(float(d[32]), float(d[33]), float(d[34])),
            )
        except (ValueError, TypeError):
            pass

        if self._recording_mode == 'Continuous':
            try:
                wrist_q   = self.rightHand.get_orientation_q()
                finger_qs = self.rightHand.get_relative_orientations_q()
                j1        = self.rightHand.get_j1_angles()
                j2        = self.rightHand.get_j2_angles()
                self.positionRecorder.record_continuous(timestamp, wrist_q, finger_qs, j1, j2)
            except Exception:
                pass

    def _update_animation(self, d):
        j1 = self.rightHand.get_j1_angles()
        j2 = self.rightHand.get_j2_angles()
        self.animationView.setAnglesPointer(j1[1], j2[0])
        self.animationView.setAnglesMiddle(j1[2], j2[1])
        self.animationView.setAnglesRing(j1[3], j2[2])
        self.animationView.setAnglesPinky(j1[4], j2[3])
        self.animationView.setAngleThumb(j1[0])
        self.animationView.setOrientationPalm(*self.rightHand.get_orientation_q())
        self.animationView.setOrientationFingers(self.rightHand.get_relative_orientations_q())

    def _update_labels(self, d, timestamp):
        self.timestampLabel.setText(f'Timestamp: {timestamp:.3f}s')

        def fmt(value):
            try:
                return f'{float(value):.2f}'
            except (ValueError, TypeError):
                return '--'

        view = self._current_view
        FINGER_OFFSETS = {
            'Thumb': (0, 5, 8), 'Pointer': (1, 11, 14), 'Middle': (2, 17, 20),
            'Ring': (3, 23, 26), 'Pinky': (4, 29, 32),
        }

        if view in FINGER_OFFSETS:
            flex_i, acc_i, gyro_i = FINGER_OFFSETS[view]
            flex_val = d[flex_i]
            angle_fn = thumb_flex_to_angle if view == 'Thumb' else finger_flex_to_angle
            angle = angle_fn(flex_val)

            self.flexLabel.setText(f'Flex: {fmt(flex_val)}')
            self.flexAngleLabel.setText(f'Flex Angle (deg): {fmt(angle)}')
            self.gyroXLabel.setText(f'Gyro X: {fmt(d[gyro_i])}')
            self.gyroYLabel.setText(f'Gyro Y: {fmt(d[gyro_i + 1])}')
            self.gyroZLabel.setText(f'Gyro Z: {fmt(d[gyro_i + 2])}')
            self.accXLabel.setText(f'Acc X: {fmt(d[acc_i])}')
            self.accYLabel.setText(f'Acc Y: {fmt(d[acc_i + 1])}')
            self.accZLabel.setText(f'Acc Z: {fmt(d[acc_i + 2])}')
        elif view == 'Wrist':
            self.gyroXLabel.setText(f'Gyro X: {fmt(d[38])}')
            self.gyroYLabel.setText(f'Gyro Y: {fmt(d[39])}')
            self.gyroZLabel.setText(f'Gyro Z: {fmt(d[40])}')
            self.accXLabel.setText(f'Acc X: {fmt(d[35])}')
            self.accYLabel.setText(f'Acc Y: {fmt(d[36])}')
            self.accZLabel.setText(f'Acc Z: {fmt(d[37])}')
            ox, oy, oz = self.rightHand.get_orientation()
            self.orientationLabel.setText(
                f'Wrist Orientation (deg):\nX = {fmt(ox)}\nY = {fmt(oy)}\nZ = {fmt(oz)}'
            )

    def _zero_gyros(self):
        self.rightHand.zero_orientation()
        print("Gyroscope orientation zeroed")

    def _record_snapshot(self, label):
        try:
            wrist_q   = self.rightHand.get_orientation_q()
            finger_qs = self.rightHand.get_relative_orientations_q()
            j1        = self.rightHand.get_j1_angles()
            j2        = self.rightHand.get_j2_angles()
            self.positionRecorder.record_snapshot(self._current_timestamp, wrist_q, finger_qs, j1, j2, label)
        except Exception as e:
            print(f"Snapshot failed: {e}")

    def _guess_pose(self):
        """Guess current pose using the trained model (robust version)."""
        if self.model is None:
            try:
                self.model = joblib.load('models/hand_pose_random_forest_model.pkl')
                print("✅ Loaded hand pose model successfully")
            except FileNotFoundError:
                self.predictionLabel.setText("Predicted Pose: MODEL NOT FOUND")
                print("❌ Could not find hand_pose_random_forest_model.pkl")
                return
            except Exception as e:
                self.predictionLabel.setText("Predicted Pose: LOAD ERROR")
                print(f"❌ Model load error: {e}")
                return

        try:
            # Get current kinematic state
            wrist_q   = self.rightHand.get_orientation_q()
            finger_qs = self.rightHand.get_relative_orientations_q()
            j1        = self.rightHand.get_j1_angles()
            j2        = self.rightHand.get_j2_angles()

            # Build values in the exact order the model expects
            feature_values = [
                wrist_q[0], wrist_q[1], wrist_q[2], wrist_q[3],           # Wrist
                finger_qs[0], finger_qs[1], finger_qs[2], finger_qs[3],   # Thumb
                finger_qs[4], finger_qs[5], finger_qs[6], finger_qs[7],   # Pointer
                finger_qs[8], finger_qs[9], finger_qs[10], finger_qs[11], # Middle
                finger_qs[12], finger_qs[13], finger_qs[14], finger_qs[15], # Ring
                finger_qs[16], finger_qs[17], finger_qs[18], finger_qs[19], # Pinky
                j1[0],                                                     # Thumb_J1
                j1[1], j2[0],                                              # Pointer
                j1[2], j2[1],                                              # Middle
                j1[3], j2[2],                                              # Ring
                j1[4], j2[3]                                               # Pinky
            ]

            # Use the model's own feature names (guaranteed correct order)
            if hasattr(self.model, 'feature_names_in_'):
                df = pd.DataFrame([feature_values], columns=self.model.feature_names_in_)
            else:
                # Fallback column names (matches training)
                feature_names = [
                    'Wrist_qx','Wrist_qy','Wrist_qz','Wrist_qw',
                    'Thumb_qx','Thumb_qy','Thumb_qz','Thumb_qw',
                    'Pointer_qx','Pointer_qy','Pointer_qz','Pointer_qw',
                    'Middle_qx','Middle_qy','Middle_qz','Middle_qw',
                    'Ring_qx','Ring_qy','Ring_qz','Ring_qw',
                    'Pinky_qx','Pinky_qy','Pinky_qz','Pinky_qw',
                    'Thumb_J1',
                    'Pointer_J1','Pointer_J2',
                    'Middle_J1','Middle_J2',
                    'Ring_J1','Ring_J2',
                    'Pinky_J1','Pinky_J2'
                ]
                df = pd.DataFrame([feature_values], columns=feature_names)

            prediction = self.model.predict(df)[0]
            self.predictionLabel.setText(f"Predicted Pose: **{prediction.upper()}**")
            print(f"Guess → {prediction}")

        except Exception as e:
            self.predictionLabel.setText("Predicted Pose: ERROR")
            print(f"Prediction error: {e}")


if __name__ == "__main__":
    pass