"""
GloveMonitorWindow.py

Live sensor monitor window. This is the top-level PySide6 class imported and
instantiated by SensorRead3_0.py. It acts as the central coordinator between
the three supporting modules:

    SensorDataProcessor  — filters all 41 incoming sensor channels, tracks
                           the live sample rate, and owns PositionRecorder.
    HandKinematics       — integrates IMU gyro data into orientation quaternions
                           and maintains joint flex angle state.
    HandRenderer         — renders the 3D hand model in a separate Qt3D window.

Data flow each frame (triggered by SensorRead3_0 calling updateData()):
    1. SensorProcessor filters the raw 41-value data array.
    2. RightHand updates joint angles from flex sensor readings.
    3. RightHand integrates wrist + finger gyro into quaternions.
    4. Qt labels are updated for whichever finger/view is currently selected.
    5. Every ANIMATION_SAMPLE_RATE_MULTIPLIER frames, the 3D renderer is updated.
    6. If continuous position recording is active, one row is appended to CSV.

Menu structure:
    View        — switch sensor label display between finger/wrist views
                  (Thumb / Pointer / Middle / Ring / Pinky / Wrist)
    Recording   — switch the active recording mode, which controls which
                  buttons are visible below the sensor labels:
                    Disabled    — sensor labels + Zero/Record Gyro only (default)
                    Continuous  — adds Begin/End Position Recording buttons
                    Snapshots   — adds one snapshot button per pose label
                    Identify    — adds Guess Current Pose button + prediction label

Threading note:
    SensorRead3_0.py calls updateData() from a background thread. Qt widgets
    must only be updated from the main thread. Here this is safe because the
    QTimer-driven processEvents() call keeps the Qt event loop running on the
    main thread, and all label/renderer updates happen synchronously within
    the same Qt event pump cycle. If threading issues arise in future, consider
    routing updates through QMetaObject.invokeMethod().

Public interface (names and signatures fixed — SensorRead3_0.py calls these directly):
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

from SensorDataProcessor import (
    SensorProcessor, GyroRecorder, PositionRecorder,
    finger_flex_to_angle, thumb_flex_to_angle,
)
from HandKinematics import RightHand
from HandRenderer   import AnimationWindow


# ---------------------------------------------------------------------------
# QApplication singleton guard
#
# Qt requires exactly one QApplication instance per process. Since this module
# is imported by SensorRead3_0.py (which already has a Tkinter mainloop running),
# we must create the QApplication here at module import time — before any
# QWidget is constructed — and guard against creating a second instance if the
# module is somehow imported twice.
# ---------------------------------------------------------------------------
_app = QApplication.instance()   # returns the existing instance if one exists
if _app is None:
    _app = QApplication([])       # create a new one only if none exists yet


# ---------------------------------------------------------------------------
# GloveMonitorWindow
# ---------------------------------------------------------------------------

class GloveMonitorWindow(QMainWindow):
    """
    Main live-display window for glove sensor data.

    Owns:
        - A SensorProcessor for per-frame filtering.
        - A RightHand for kinematics and orientation integration.
        - A GyroRecorder for optional research gyro logging.
        - A PositionRecorder for continuous and snapshot position CSV output.
        - An AnimationWindow (separate Qt3D window) for 3D visualisation.
        - A QTimer that pumps Qt events every 10 ms (necessary because
          Qt's event loop is not running — Tkinter's is).

    The window uses a single flat QGridLayout. The set of buttons visible below
    the sensor labels changes depending on the active recording mode, which is
    set via the Recording menu. On initial boot only the Zero Gyro and
    Record/Stop Gyro buttons are visible; all mode-specific buttons start hidden.

    Recording modes (set via the Recording menu):
        Disabled    — only gyro control buttons shown (default at boot)
        Continuous  — shows Begin / End Position Recording buttons
        Snapshots   — shows one labelled snapshot button per pose class
        Identify    — shows Guess Current Pose button and a live prediction label

    The View menu (Thumb / Pointer / Middle / Ring / Pinky / Wrist) controls
    which finger's sensor data is displayed in the labels and is independent of
    the recording mode.
    """

    # How many incoming data frames to skip between 3D renderer updates.
    # 2 = render every other frame, halving the rendering workload.
    # Increase this value if the animation is causing performance issues.
    ANIMATION_SAMPLE_RATE_MULTIPLIER = 2  # THIS IS THE NUMBER YOU CHANGE IF YOUR COMPUTER IS LAGGING

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Acquisition Window')

        # --- Instantiate supporting objects ---
        # SensorProcessor owns all 41 filter instances and the sample rate estimator.
        self.processor = SensorProcessor(initial_sample_rate=100, cutoff_freq=5)

        # RightHand owns the kinematic model: joint angles, quaternion integration,
        # and calibrated wrist gyro correction matrices.
        self.rightHand = RightHand()

        # GyroRecorder handles optional research CSV logging of raw gyro data.
        # Can be removed along with its calls in _update_kinematics if no longer needed.
        self.gyroRecorder = GyroRecorder()

        # PositionRecorder handles continuous and snapshot position CSV recording.
        # Continuous mode appends one row per frame; snapshot mode appends one row
        # per button press with a pose label attached.
        self.positionRecorder = PositionRecorder()

        # Cache the most recent filtered data and timestamp so the view can be
        # switched and labels refreshed without waiting for the next serial frame.
        self._filtered_data     = None
        self._current_timestamp = None

        # Frame counter for throttling the 3D renderer updates.
        self._sample_index = 0

        # Name of the currently-displayed sensor view (finger or 'Wrist').
        self._current_view = 'Thumb'

        # Current recording mode — controls which buttons are visible.
        # Starts as 'Disabled' so only the gyro buttons appear on boot.
        self._recording_mode = 'Disabled'

        # Cached random-forest model for the Identify mode.
        # Loaded lazily on first use of _guess_pose() to avoid startup delay.
        self.model = None

        # Build all Qt widgets and lay them out.
        self._build_ui()

        # 3D renderer — a separate Qt3DWindow that shows alongside this window.
        self.animationView = AnimationWindow()

        # Qt event pump timer. Because SensorRead3_0.py runs Tkinter's mainloop
        # (not Qt's), Qt's own event processing would never run without this.
        # Every 10 ms, QApplication.processEvents() handles pending Qt events
        # (redraws, button clicks, timer callbacks, etc.).
        self._event_timer = QTimer()
        self._event_timer.timeout.connect(QApplication.processEvents)
        self._event_timer.start(10)   # milliseconds between event pump calls

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        """
        Create all Qt widgets and assemble the window layout.
        Called once during __init__. Constructs the container widget, grid
        layout, menu bar, labels, and buttons, then applies the initial layout.
        """
        container = QWidget()
        self.setCentralWidget(container)
        # QGridLayout allows precise row/column placement of all widgets.
        self._layout = QGridLayout(container)

        self._build_menu()
        self._build_labels()
        self._build_buttons()
        self._apply_layout()   # place all widgets into the grid for the initial view/mode

    def _build_menu(self):
        """
        Add the 'View' and 'Recording' menus to the menu bar.

        View menu:
            Each item switches the active sensor view, changing which finger's
            data is displayed in the labels.

        Recording menu:
            Each item switches the active recording mode, which determines
            which set of action buttons is shown below the sensor labels.
            Switching to Continuous automatically starts position recording;
            switching to any other mode automatically stops it.
        """
        # --- View menu ---
        view_menu = self.menuBar().addMenu('View')
        for name in ('Thumb', 'Pointer', 'Middle', 'Ring', 'Pinky', 'Wrist'):
            action = view_menu.addAction(name)
            # Lambda captures 'name' at definition time via the default argument trick
            # (n=name). Without this, all lambdas would capture the final value of 'name'.
            action.triggered.connect(lambda checked, n=name: self._change_view(n))

        # --- Recording menu ---
        record_menu = self.menuBar().addMenu('Recording')
        for mode in ('Disabled', 'Continuous', 'Snapshots', 'Identify'):
            action = record_menu.addAction(mode)
            # Same default-argument capture trick as above.
            action.triggered.connect(lambda checked, m=mode: self._set_recording_mode(m))

    def _build_labels(self):
        """
        Instantiate all QLabel widgets used to display sensor data.

        Labels are named by their role in finger views. In the Wrist view,
        some labels are hidden and others show different data — but the same
        label objects are reused to avoid rebuilding the layout each time.

        The predictionLabel is only visible in Identify mode and starts hidden.
        """
        self.timestampLabel  = self._centered_label('Timestamp: --')
        self.sampleRateLabel = self._centered_label('Sample Rate: -- Hz')
        self.viewTitleLabel  = self._centered_label('Thumb Data')
        self.viewTitleLabel.setStyleSheet("font-weight: bold; font-size: 14pt;")

        self.flexLabel        = self._centered_label('Flex: --')              # raw ADC value
        self.flexAngleLabel   = self._centered_label('Flex Angle (deg): --')  # converted angle
        self.gyroXLabel       = self._centered_label('Gyro X: --')
        self.gyroYLabel       = self._centered_label('Gyro Y: --')
        self.gyroZLabel       = self._centered_label('Gyro Z: --')
        self.accXLabel        = self._centered_label('Acc X: --')
        self.accYLabel        = self._centered_label('Acc Y: --')
        self.accZLabel        = self._centered_label('Acc Z: --')
        # Only visible in Wrist view — shows integrated [X, Y, Z] orientation in degrees.
        self.orientationLabel = self._centered_label('Wrist Orientation (deg): --')

        # Visible only in Identify mode — updated by _guess_pose() with the
        # model's predicted pose class string. Starts hidden.
        self.predictionLabel = self._centered_label('Predicted Pose: --')
        self.predictionLabel.setStyleSheet("font-weight: bold; color: #22aa22; font-size: 12pt;")
        self.predictionLabel.hide()   # hidden until Identify mode is selected

    def _build_buttons(self):
        """
        Instantiate all QPushButton widgets and connect them to their handlers.

        Buttons are divided into three groups by recording mode.

        Always-visible (shown in every mode):
            gyroResetButton   — zeros all orientation quaternions.
            gyroRecordButton  — starts a GyroRecorder episode.
            gyroStopButton    — stops the current GyroRecorder episode.

        Continuous mode only (hidden on boot):
            beginPositionButton — calls positionRecorder.start_continuous().
            endPositionButton   — calls positionRecorder.stop_continuous().

        Snapshots mode only (hidden on boot):
            snapshotButtons — one button per pose label (dict keyed by label string).
                              Each press calls _record_snapshot() with that label,
                              appending one labelled row to the snapshot CSV.

        Identify mode only (hidden on boot):
            guessButton — loads the random-forest model on first call, then runs
                          predict() on the current kinematic state and updates
                          predictionLabel with the result.
        """
        # --- Always-visible gyro control buttons ---

        # Zero Gyro: resets all integrated orientation quaternions to identity,
        # re-zeroing the reference frame from the hand's current physical pose.
        self.gyroResetButton = QPushButton("Zero Gyro", self)
        self.gyroResetButton.clicked.connect(self._zero_gyros)

        # Record Gyro: starts a new GyroRecorder episode for research logging.
        self.gyroRecordButton = QPushButton("Record Gyro", self)
        self.gyroRecordButton.clicked.connect(self.gyroRecorder.start_episode)

        # Stop Gyro Recording: ends the active GyroRecorder episode.
        self.gyroStopButton = QPushButton("Stop Gyro Recording", self)
        self.gyroStopButton.clicked.connect(self.gyroRecorder.stop_episode)

        # --- Continuous mode buttons (hidden on boot) ---

        # Begin Position Recording: activates the PositionRecorder so that
        # each incoming frame is appended to the continuous position CSV.
        self.beginPositionButton = QPushButton("Begin Position Recording", self)
        self.beginPositionButton.clicked.connect(self.positionRecorder.start_continuous)
        self.beginPositionButton.hide()   # not visible until Continuous mode is selected

        # End Position Recording: deactivates the PositionRecorder, stopping CSV output.
        self.endPositionButton = QPushButton("End Position Recording", self)
        self.endPositionButton.clicked.connect(self.positionRecorder.stop_continuous)
        self.endPositionButton.hide()   # not visible until Continuous mode is selected

        # --- Snapshot mode buttons (hidden on boot) ---

        # One button per pose label. Pressing any of these calls _record_snapshot()
        # with that label's string, which appends one labelled row to the snapshot CSV.
        # Stored in a dict keyed by label string so they can be shown/hidden as a group.
        self.snapshotButtons = {}
        for label in PositionRecorder.SNAPSHOT_LABELS:
            display_text = label.replace('_', ' ').title()   # e.g. 'thumbs_up' → 'Thumbs Up'
            btn = QPushButton(display_text, self)
            btn.clicked.connect(lambda checked, l=label: self._record_snapshot(l))
            btn.hide()   # not visible until Snapshots mode is selected
            self.snapshotButtons[label] = btn

        # --- Identify mode button (hidden on boot) ---

        # Guess Current Pose: loads the saved random-forest model on first call,
        # then runs predict() on the current kinematic state and displays the result
        # in predictionLabel.
        self.guessButton = QPushButton("Guess Current Pose", self)
        self.guessButton.clicked.connect(self._guess_pose)
        self.guessButton.hide()   # not visible until Identify mode is selected

    def _apply_layout(self):
        """
        Place all widgets into the QGridLayout for the current view and recording mode.

        Called once during init and again each time the view or recording mode changes.
        Clears the layout first without destroying widgets, then re-adds all visible
        widgets in the correct grid positions.

        Layout structure:
            Rows 0-2:  Always-visible header labels (timestamp, sample rate, view title).
            Rows 3-5:  Sensor data labels — layout differs between finger views (has flex
                       row) and the Wrist view (has orientation row instead).
            Rows 6-8:  Gyro control buttons — always placed regardless of mode.
            Rows 9+:   Mode-specific widgets — only the active mode's widgets are shown;
                       all others are explicitly hidden before the mode check.
        """
        # Remove all widgets from the layout without deleting them.
        # setParent(None) detaches the widget from the layout item; the widget
        # objects are kept alive by the instance attributes (self.flexLabel, etc.).
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

        # --- Rows 0-2: always-visible header labels ---
        self._layout.addWidget(self.timestampLabel,  0, 0, 1, 3)
        self._layout.addWidget(self.sampleRateLabel, 1, 0, 1, 3)
        self._layout.addWidget(self.viewTitleLabel,  2, 0, 1, 3)

        # --- Rows 3-5: sensor data labels (layout differs by view) ---
        if self._current_view == 'Wrist':
            # Wrist has no flex sensor — hide flex labels, show orientation.
            self.flexLabel.hide()
            self.flexAngleLabel.hide()
            self.orientationLabel.show()

            # Row 3: raw gyro X/Y/Z (three columns)
            self._layout.addWidget(self.gyroXLabel,       3, 0)
            self._layout.addWidget(self.gyroYLabel,       3, 1)
            self._layout.addWidget(self.gyroZLabel,       3, 2)
            # Row 4: accelerometer X/Y/Z
            self._layout.addWidget(self.accXLabel,        4, 0)
            self._layout.addWidget(self.accYLabel,        4, 1)
            self._layout.addWidget(self.accZLabel,        4, 2)
            # Row 5: integrated orientation (multi-line label, spans all columns)
            self._layout.addWidget(self.orientationLabel, 5, 0, 1, 3)
        else:
            # Finger views: show flex, angle, gyro, acc.
            self.flexLabel.show()
            self.flexAngleLabel.show()
            self.orientationLabel.hide()

            # Row 3: raw flex value and converted angle (two of three columns)
            self._layout.addWidget(self.flexLabel,        3, 0)
            self._layout.addWidget(self.flexAngleLabel,   3, 1)
            # Row 4: gyro X/Y/Z
            self._layout.addWidget(self.gyroXLabel,       4, 0)
            self._layout.addWidget(self.gyroYLabel,       4, 1)
            self._layout.addWidget(self.gyroZLabel,       4, 2)
            # Row 5: accelerometer X/Y/Z
            self._layout.addWidget(self.accXLabel,        5, 0)
            self._layout.addWidget(self.accYLabel,        5, 1)
            self._layout.addWidget(self.accZLabel,        5, 2)

        # --- Rows 6-8: gyro control buttons (always visible) ---
        self._layout.addWidget(self.gyroResetButton,  6, 0, 1, 3)
        self._layout.addWidget(self.gyroRecordButton, 7, 0, 1, 3)
        self._layout.addWidget(self.gyroStopButton,   8, 0, 1, 3)

        # --- Rows 9+: mode-specific widgets ---
        # First hide all mode-specific widgets so we start from a clean state,
        # then show and place only the ones for the active recording mode.

        self.beginPositionButton.hide()
        self.endPositionButton.hide()
        for btn in self.snapshotButtons.values():
            btn.hide()
        self.guessButton.hide()
        self.predictionLabel.hide()

        if self._recording_mode == 'Continuous':
            # Show Begin / End position recording buttons.
            self.beginPositionButton.show()
            self.endPositionButton.show()
            self._layout.addWidget(self.beginPositionButton, 9,  0, 1, 3)
            self._layout.addWidget(self.endPositionButton,   10, 0, 1, 3)

        elif self._recording_mode == 'Snapshots':
            # Show one button per pose label, stacked vertically from row 9 onward.
            for row_offset, btn in enumerate(self.snapshotButtons.values()):
                btn.show()
                self._layout.addWidget(btn, 9 + row_offset, 0, 1, 3)

        elif self._recording_mode == 'Identify':
            # Show the Guess button and the prediction result label.
            self.guessButton.show()
            self.predictionLabel.show()
            self._layout.addWidget(self.guessButton,     9,  0, 1, 3)
            self._layout.addWidget(self.predictionLabel, 10, 0, 1, 3)

        # 'Disabled' mode: all mode-specific widgets already hidden above — nothing more to do.

    @staticmethod
    def _centered_label(text):
        """Create a QLabel with centred alignment. Used for all data display labels."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        return label

    # -----------------------------------------------------------------------
    # View and mode switching
    # -----------------------------------------------------------------------

    def _change_view(self, view_name):
        """
        Switch the active sensor display view to view_name and refresh the layout.

        Called when the user selects a finger from the View menu. Re-applies
        the layout (which hides/shows the appropriate labels for the new view)
        and immediately updates the labels with the last known data so the display
        isn't blank until the next frame arrives.

        Args:
            view_name: one of 'Thumb', 'Pointer', 'Middle', 'Ring', 'Pinky', 'Wrist'.
        """
        self._current_view = view_name
        self.viewTitleLabel.setText(f'{view_name} Data')
        self._apply_layout()   # rebuild layout for new view (hides/shows labels)
        # Re-display the cached filtered data for the new view immediately.
        if self._filtered_data is not None:
            self._update_labels(self._filtered_data, self._current_timestamp)

    def _set_recording_mode(self, mode):
        """
        Switch the active recording mode and refresh the button layout.

        Called when the user selects a mode from the Recording menu.

        Side effects:
            - Switching to 'Continuous' automatically calls start_continuous() on
              the PositionRecorder so recording begins as soon as the mode is selected,
              without requiring an extra button press.
            - Switching to any other mode calls stop_continuous() to ensure continuous
              recording is not left running unintentionally in the background.
              stop_continuous() is a no-op if recording was not active.
            - _apply_layout() is called to show/hide the appropriate buttons.

        Args:
            mode: one of 'Disabled', 'Continuous', 'Snapshots', 'Identify'.
        """
        self._recording_mode = mode
        print(f"Recording mode changed to: {mode}")

        # Automatically start/stop continuous recording when the mode changes.
        if mode == 'Continuous':
            self.positionRecorder.start_continuous()
        else:
            # For all other modes, ensure continuous recording is not left running.
            self.positionRecorder.stop_continuous()

        self._apply_layout()   # rebuild button section for the new mode

    # -----------------------------------------------------------------------
    # Public interface (called by SensorRead3_0.py — do not rename)
    # -----------------------------------------------------------------------

    def initDisplay(self):
        """
        Show the monitor window and the 3D animation window.
        Called by SensorRead3_0.py immediately after creating this object,
        before data acquisition begins.
        """
        self.show()                 # show this QMainWindow (data labels + menu)
        self.animationView.show()   # show the separate Qt3D hand renderer window

    def terminateDisplay(self):
        """
        Stop the Qt event pump timer and close both windows.
        Called by SensorRead3_0.py when the user presses 'Stop Acquisition'.

        Also ensures continuous position recording is cleanly stopped if it was
        still active when acquisition was halted, so no CSV rows are lost.
        """
        # Cleanly stop continuous recording if still active.
        if self.positionRecorder.is_recording:
            self.positionRecorder.stop_continuous()

        self._event_timer.stop()    # stop the 10 ms Qt event pump
        self.animationView.close()  # close the 3D renderer window
        self.close()                # close this monitor window

    def updateData(self, data: str, timestamp: float):
        """
        Process one incoming data frame from the glove. Called by SensorRead3_0.py
        from its background acquisition thread on every serial line received.

        Steps:
            1. Split the raw CSV string into a list and validate length.
            2. Update the sample rate estimate (measures wall-clock interval).
            3. Filter all 41 channels through SensorProcessor.
            4. Push the filtered data into the kinematic model and gyro recorder.
            5. Update the display labels for the current view.
            6. Every ANIMATION_SAMPLE_RATE_MULTIPLIER frames, update the 3D renderer.

        Args:
            data:      raw comma-separated string from the serial line
                       (41 values, matching the layout in SensorProcessor).
            timestamp: seconds since acquisition start (float), from time.perf_counter().
        """
        try:
            # Split the CSV string and strip whitespace from each token.
            data_array = [s.strip() for s in data.split(',')]
            if len(data_array) < 41:
                return   # incomplete frame — skip silently
        except Exception:
            return   # malformed data — skip silently

        # Update the rolling sample rate estimate before filtering.
        self.processor.update_sample_rate()

        # Run all 41 channels through the Butterworth filter bank.
        filtered = self.processor.process(data_array)
        if filtered is None:
            return

        # Cache for use by _change_view(), _record_snapshot(), and _guess_pose().
        self._filtered_data     = filtered
        self._current_timestamp = timestamp

        self.sampleRateLabel.setText(
            f'Sample Rate: {self.processor.estimated_sample_rate:.1f} Hz'
        )

        # Update the kinematic model (joint angles + orientation integration)
        # and, if continuous recording is active, write one position row.
        self._update_kinematics(filtered, timestamp)

        # Update the display labels for the currently-selected view.
        self._update_labels(filtered, timestamp)

        # Throttle 3D renderer updates: only render every Nth frame.
        self._sample_index += 1
        if self._sample_index >= self.ANIMATION_SAMPLE_RATE_MULTIPLIER:
            self._sample_index = 0
            self._update_animation(filtered)

    # -----------------------------------------------------------------------
    # Internal update helpers (called from updateData each frame)
    # -----------------------------------------------------------------------

    def _update_kinematics(self, d, timestamp):
        """
        Push the current filtered frame into the hand kinematic model.

        Two main operations per frame:
            A. Flex → joint angles: polynomial-converted flex values are split
               75% / 25% between J1 and J2 joints, reflecting the biomechanical
               tendency for the proximal joint to flex more than the middle joint.
            B. Gyro → orientation: wrist and finger gyro values are integrated
               into running quaternions by RightHand.

        After kinematics are updated, this method also:
            C. Logs gyro data via GyroRecorder if an episode is active.
            D. Appends one row to the continuous position CSV via PositionRecorder
               if is_recording is True. record_continuous() is a no-op otherwise,
               so no explicit guard is needed in the caller.

        Filtered array index reference (matches SensorProcessor output layout):
            [0-4]   Flex (thumb through pinky)
            [5-7]   Thumb Acc X/Y/Z,   [8-10]  Thumb Gyro X/Y/Z
            [11-13] Pointer Acc X/Y/Z, [14-16] Pointer Gyro X/Y/Z
            [17-19] Middle Acc X/Y/Z,  [20-22] Middle Gyro X/Y/Z
            [23-25] Ring Acc X/Y/Z,    [26-28] Ring Gyro X/Y/Z
            [29-31] Pinky Acc X/Y/Z,   [32-34] Pinky Gyro X/Y/Z
            [35-37] Wrist Acc X/Y/Z,   [38-40] Wrist Gyro X/Y/Z (rad/s)

        Args:
            d:         filtered data array from SensorProcessor.process().
            timestamp: seconds since acquisition start (used by GyroRecorder
                       and PositionRecorder for row timestamps).
        """
        # --- A. Flex sensor → joint angles ---
        thumb_angle   = thumb_flex_to_angle(d[0])
        pointer_angle = finger_flex_to_angle(d[1])
        middle_angle  = finger_flex_to_angle(d[2])
        ring_angle    = finger_flex_to_angle(d[3])
        pinky_angle   = finger_flex_to_angle(d[4])

        # Split total flex angle 75% / 25% between J1 (proximal) and J2 (middle) joints.
        # The 'if angle else 0' guards against None returns from the polynomial functions
        # when the flex value is non-numeric during startup.
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

        # Pass the current sample rate so RightHand can scale gyro integration correctly.
        self.rightHand.update_sample_rate(self.processor.estimated_sample_rate)

        # --- B. Gyro → orientation integration ---
        try:
            # Wrist gyro (indices 38-40): already in rad/s after SensorProcessor conversion.
            self.rightHand.update_orientation(float(d[38]), float(d[39]), float(d[40]))

            # Finger gyros (indices 8-10, 14-16, 20-22, 26-28, 32-34): rad/s.
            self.rightHand.update_orientation_fingers(
                float(d[8]),  float(d[9]),  float(d[10]),   # Thumb
                float(d[14]), float(d[15]), float(d[16]),   # Pointer
                float(d[20]), float(d[21]), float(d[22]),   # Middle
                float(d[26]), float(d[27]), float(d[28]),   # Ring
                float(d[32]), float(d[33]), float(d[34]),   # Pinky
            )
        except (ValueError, TypeError) as e:
            # Non-numeric values during startup — skip integration for this frame.
            print(f"Waiting for gyro read: {e}")
            return

        # --- C. GyroRecorder (research scaffolding) ---
        # This block can be removed once research gyro logging is no longer needed.
        try:
            self.gyroRecorder.record(
                timestamp,
                wrist   = (float(d[38]), float(d[39]), float(d[40])),
                thumb   = (float(d[8]),  float(d[9]),  float(d[10])),
                pointer = (float(d[14]), float(d[15]), float(d[16])),
                middle  = (float(d[20]), float(d[21]), float(d[22])),
                ring    = (float(d[26]), float(d[27]), float(d[28])),
                pinky   = (float(d[32]), float(d[33]), float(d[34])),
            )
        except (ValueError, TypeError):
            pass   # silently skip logging if values are non-numeric

        # --- D. Continuous position recording ---
        # record_continuous() is a no-op when PositionRecorder.is_recording is False,
        # so this call is safe to make unconditionally every frame.
        try:
            self.positionRecorder.record_continuous(
                runtime_timestamp = timestamp,
                wrist_q           = self.rightHand.get_orientation_q(),
                finger_qs         = self.rightHand.get_relative_orientations_q(),
                j1_angles         = self.rightHand.get_j1_angles(),
                j2_angles         = self.rightHand.get_j2_angles(),
            )
        except Exception:
            pass   # silently skip if any getter fails during startup

    def _update_animation(self, d):
        """
        Push the current hand pose to the 3D renderer (AnimationWindow).
        Called every ANIMATION_SAMPLE_RATE_MULTIPLIER frames from updateData().

        Two components are updated:
            1. Flex angles: J1 and J2 angles for each finger's middle/distal segments,
               producing the curling motion.
            2. Orientations: wrist quaternion (rotates the whole palm) and per-finger
               proximal quaternions (captures spreading/twisting of each finger base).
        """
        j1 = self.rightHand.get_j1_angles()   # [thumb, pointer, middle, ring, pinky]
        j2 = self.rightHand.get_j2_angles()   # [pointer, middle, ring, pinky] (no thumb J2)

        # Apply finger curl angles. Thumb only has a distal joint (setAngleThumb takes one value).
        self.animationView.setAnglesPointer(j1[1], j2[0])
        self.animationView.setAnglesMiddle( j1[2], j2[1])
        self.animationView.setAnglesRing(   j1[3], j2[2])
        self.animationView.setAnglesPinky(  j1[4], j2[3])
        self.animationView.setAngleThumb(   j1[0])

        # Rotate the entire palm (and all parented fingers) by the wrist quaternion.
        self.animationView.setOrientationPalm(*self.rightHand.get_orientation_q())

        # Set the base-segment orientation for each finger independently.
        # This drives abduction/adduction (spreading) and twist beyond what flex captures.
        self.animationView.setOrientationFingers(
            self.rightHand.get_relative_orientations_q()
        )

    def _update_labels(self, d, timestamp):
        """
        Update all visible Qt display labels for the currently-selected view.

        For finger views (Thumb/Pointer/Middle/Ring/Pinky), looks up the array
        indices for that finger's flex, acc, and gyro values using the
        FINGER_OFFSETS table, then formats and sets each label's text.

        For the Wrist view, displays wrist acc/gyro raw values plus the
        integrated orientation from RightHand.get_orientation().

        Args:
            d:         filtered data array (same layout as SensorProcessor output).
            timestamp: seconds since acquisition start.
        """
        self.timestampLabel.setText(f'Timestamp: {timestamp:.3f}s')

        def fmt(value):
            """Format a sensor value to 2 decimal places, or '--' if non-numeric."""
            try:
                return f'{float(value):.2f}'
            except (ValueError, TypeError):
                return '--'

        view = self._current_view

        # FINGER_OFFSETS maps each view name to the three array index bases for
        # that finger's data in the filtered array:
        #   flex_i:  index of the flex value
        #   acc_i:   index of Acc X (Acc Y = acc_i+1, Acc Z = acc_i+2)
        #   gyro_i:  index of Gyro X (Gyro Y = gyro_i+1, Gyro Z = gyro_i+2)
        FINGER_OFFSETS = {
            #            flex_i  acc_i  gyro_i
            'Thumb':   (  0,      5,      8  ),
            'Pointer': (  1,     11,     14  ),
            'Middle':  (  2,     17,     20  ),
            'Ring':    (  3,     23,     26  ),
            'Pinky':   (  4,     29,     32  ),
        }

        if view in FINGER_OFFSETS:
            flex_i, acc_i, gyro_i = FINGER_OFFSETS[view]

            flex_val = d[flex_i]   # raw ADC flex reading
            # Thumb and non-thumb fingers use different polynomial fits.
            angle_fn = thumb_flex_to_angle if view == 'Thumb' else finger_flex_to_angle
            angle    = angle_fn(flex_val)   # convert ADC → degrees

            self.flexLabel.setText(     f'Flex: {fmt(flex_val)}')
            self.flexAngleLabel.setText(f'Flex Angle (deg): {fmt(angle)}')
            self.gyroXLabel.setText(    f'Gyro X: {fmt(d[gyro_i])}')
            self.gyroYLabel.setText(    f'Gyro Y: {fmt(d[gyro_i + 1])}')
            self.gyroZLabel.setText(    f'Gyro Z: {fmt(d[gyro_i + 2])}')
            self.accXLabel.setText(     f'Acc X: {fmt(d[acc_i])}')
            self.accYLabel.setText(     f'Acc Y: {fmt(d[acc_i + 1])}')
            self.accZLabel.setText(     f'Acc Z: {fmt(d[acc_i + 2])}')

        elif view == 'Wrist':
            # Wrist accelerometer lives at indices 35–37.
            # Wrist gyro lives at indices 38–40 (rad/s after SensorProcessor conversion).
            self.gyroXLabel.setText(f'Gyro X: {fmt(d[38])}')
            self.gyroYLabel.setText(f'Gyro Y: {fmt(d[39])}')
            self.gyroZLabel.setText(f'Gyro Z: {fmt(d[40])}')
            self.accXLabel.setText( f'Acc X: {fmt(d[35])}')
            self.accYLabel.setText( f'Acc Y: {fmt(d[36])}')
            self.accZLabel.setText( f'Acc Z: {fmt(d[37])}')

            # Integrated orientation from the running quaternion, in degrees [X, Y, Z].
            # This is the cumulative rotation since the last 'Zero Gyro' press.
            ox, oy, oz = self.rightHand.get_orientation()
            self.orientationLabel.setText(
                f'Wrist Orientation (deg):\n'
                f'X = {fmt(ox)}\n'
                f'Y = {fmt(oy)}\n'
                f'Z = {fmt(oz)}'
            )

    # -----------------------------------------------------------------------
    # Button handlers
    # -----------------------------------------------------------------------

    def _zero_gyros(self):
        """
        Reset all integrated orientation quaternions to identity.

        After this call, all subsequent orientations are expressed relative
        to the hand's pose at the moment this button was pressed — i.e.,
        the current pose becomes the new 'zero' reference.
        """
        self.rightHand.zero_orientation()
        print("Gyroscope orientation zeroed")

    def _record_snapshot(self, label):
        """
        Capture one labelled position snapshot from the current kinematic state.

        Called when any of the snapshot buttons is pressed. Uses the most recently
        cached kinematic state (updated every frame via _update_kinematics), so it
        is valid at any point after the first data frame has arrived.

        The snapshot is appended immediately to the snapshot CSV via PositionRecorder.
        Does not require continuous recording to be active — snapshots operate
        independently of the Continuous mode.

        Args:
            label: one of PositionRecorder.SNAPSHOT_LABELS
                   ('thumbs_up', 'thumbs_down', 'peace', 'point', 'no_position').
        """
        try:
            self.positionRecorder.record_snapshot(
                runtime_timestamp = self._current_timestamp,
                wrist_q           = self.rightHand.get_orientation_q(),
                finger_qs         = self.rightHand.get_relative_orientations_q(),
                j1_angles         = self.rightHand.get_j1_angles(),
                j2_angles         = self.rightHand.get_j2_angles(),
                label             = label,
            )
        except Exception as e:
            print(f"Snapshot failed: {e}")

    def _guess_pose(self):
        """
        Predict the current hand pose using the trained random-forest model.

        Called when the 'Guess Current Pose' button is pressed in Identify mode.

        On first call, the model is loaded lazily from
        'models/hand_pose_random_forest_model.pkl'. Subsequent calls reuse the
        already-loaded model stored in self.model, avoiding repeated disk I/O.

        The feature vector is built in the exact column order that the model was
        trained on (matching POSITION_FIELDS in SensorDataProcessor, minus the two
        timestamp columns). If the model exposes feature_names_in_, those names are
        used directly to construct the DataFrame, guaranteeing column alignment even
        if the model was trained with a different column ordering.

        The predicted class string is displayed in self.predictionLabel.
        """
        # --- Lazy model load ---
        # Load the model on the first call rather than at startup, so a missing model
        # file does not prevent the window from opening.
        if self.model is None:
            try:
                self.model = joblib.load('models/hand_pose_random_forest_model.pkl')
                print("Loaded hand pose model successfully")
            except FileNotFoundError:
                self.predictionLabel.setText("Predicted Pose: MODEL NOT FOUND")
                print("Could not find hand_pose_random_forest_model.pkl")
                return
            except Exception as e:
                self.predictionLabel.setText("Predicted Pose: LOAD ERROR")
                print(f"Model load error: {e}")
                return

        try:
            # --- Build feature vector from current kinematic state ---
            wrist_q   = self.rightHand.get_orientation_q()           # [qx, qy, qz, qw]
            finger_qs = self.rightHand.get_relative_orientations_q() # 20 floats: [qx,qy,qz,qw] × 5
            j1        = self.rightHand.get_j1_angles()               # [thumb, ptr, mid, rng, pnk]
            j2        = self.rightHand.get_j2_angles()               # [ptr, mid, rng, pnk]

            # Values in training column order (POSITION_FIELDS minus the two timestamp columns).
            feature_values = [
                wrist_q[0],    wrist_q[1],    wrist_q[2],    wrist_q[3],       # Wrist qx/qy/qz/qw
                finger_qs[0],  finger_qs[1],  finger_qs[2],  finger_qs[3],     # Thumb
                finger_qs[4],  finger_qs[5],  finger_qs[6],  finger_qs[7],     # Pointer
                finger_qs[8],  finger_qs[9],  finger_qs[10], finger_qs[11],    # Middle
                finger_qs[12], finger_qs[13], finger_qs[14], finger_qs[15],    # Ring
                finger_qs[16], finger_qs[17], finger_qs[18], finger_qs[19],    # Pinky
                j1[0],                                                          # Thumb J1
                j1[1], j2[0],                                                   # Pointer J1, J2
                j1[2], j2[1],                                                   # Middle J1, J2
                j1[3], j2[2],                                                   # Ring J1, J2
                j1[4], j2[3],                                                   # Pinky J1, J2
            ]

            # Build DataFrame using the model's own feature names if available,
            # falling back to the hard-coded training column order otherwise.
            if hasattr(self.model, 'feature_names_in_'):
                # Model stores the exact column names it was trained with — use these
                # to ensure correct alignment even if the ordering differs from above.
                df = pd.DataFrame([feature_values], columns=self.model.feature_names_in_)
            else:
                # Fallback hard-coded names matching the training CSV column order.
                feature_names = [
                    'Wrist_qx',   'Wrist_qy',   'Wrist_qz',   'Wrist_qw',
                    'Thumb_qx',   'Thumb_qy',   'Thumb_qz',   'Thumb_qw',
                    'Pointer_qx', 'Pointer_qy', 'Pointer_qz', 'Pointer_qw',
                    'Middle_qx',  'Middle_qy',  'Middle_qz',  'Middle_qw',
                    'Ring_qx',    'Ring_qy',    'Ring_qz',    'Ring_qw',
                    'Pinky_qx',   'Pinky_qy',   'Pinky_qz',   'Pinky_qw',
                    'Thumb_J1',
                    'Pointer_J1', 'Pointer_J2',
                    'Middle_J1',  'Middle_J2',
                    'Ring_J1',    'Ring_J2',
                    'Pinky_J1',   'Pinky_J2',
                ]
                df = pd.DataFrame([feature_values], columns=feature_names)

            # Run the prediction and display the result in the label.
            prediction = self.model.predict(df)[0]
            self.predictionLabel.setText(f"Predicted Pose: {prediction.upper()}")
            print(f"Guess → {prediction}")

        except Exception as e:
            self.predictionLabel.setText("Predicted Pose: ERROR")
            print(f"Prediction error: {e}")


if __name__ == "__main__":
    pass