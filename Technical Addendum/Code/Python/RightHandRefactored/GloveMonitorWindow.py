"""
GloveMonitorWindow.py

Live sensor monitor window. This is the top-level PySide6 class imported and
instantiated by SensorRead3_0.py. It acts as the central coordinator between
the three supporting modules:

    SensorDataProcessor  — filters all 41 incoming sensor channels and tracks
                           the live sample rate.
    HandKinematics       — integrates IMU gyro data into orientation quaternions
                           and maintains joint flex angle state.
    HandRenderer         — renders the 3D hand model in a separate Qt3D window.

Data flow each frame (triggered by SensorRead3_0 calling updateData()):
    1. SensorProcessor filters the raw 41-value data array.
    2. RightHand updates joint angles from flex sensor readings.
    3. RightHand integrates wrist + finger gyro into quaternions.
    4. Qt labels are updated for whichever finger/view is currently selected.
    5. Every ANIMATION_SAMPLE_RATE_MULTIPLIER frames, the 3D renderer is updated.

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

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QGridLayout, QPushButton
from PySide6.QtCore import Qt, QTimer

from SensorDataProcessor import SensorProcessor, GyroRecorder, finger_flex_to_angle, thumb_flex_to_angle
from HandKinematics import RightHand
from HandRenderer import AnimationWindow


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
        - A GyroRecorder for optional research data logging.
        - An AnimationWindow (separate Qt3D window) for 3D visualisation.
        - A QTimer that pumps Qt events every 10 ms (necessary because
          Qt's event loop is not running — Tkinter's is).

    The window has a View menu to switch between six views:
        Thumb, Pointer, Middle, Ring, Pinky  — show flex + gyro + acc + angle
        Wrist                                — show gyro + acc + integrated orientation

    Label layout differs slightly between finger views and the Wrist view:
        Finger views: flexLabel, flexAngleLabel, gyroX/Y/Z, accX/Y/Z
        Wrist view:   gyroX/Y/Z, accX/Y/Z, orientationLabel (flex labels hidden)
    """

    # How many incoming data frames to skip between 3D renderer updates.
    # 2 = render every other frame, halving the rendering workload.
    ANIMATION_SAMPLE_RATE_MULTIPLIER = 2 # THIS IS THE NUMBER YOU CHANGE IF YOUR COMPUTER IS LAGGING

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Acquisition Window')

        # --- Instantiate supporting objects ---
        # SensorProcessor owns all 41 filter instances and the sample rate estimator.
        self.processor = SensorProcessor(initial_sample_rate=100, cutoff_freq=5)

        # RightHand owns the kinematic model: joint angles, quaternion integration,
        # and calibrated wrist gyro correction.
        self.rightHand = RightHand()

        # GyroRecorder handles optional research CSV logging (can be removed with
        # its associated calls in _update_kinematics if no longer needed).
        self.gyroRecorder = GyroRecorder()

        # Cache the most recent filtered data so the view can be changed without
        # waiting for the next incoming frame.
        self._filtered_data     = None
        self._current_timestamp = None

        # Frame counter for throttling the 3D renderer updates.
        self._sample_index = 0

        # Name of the currently-displayed sensor view.
        self._current_view = 'Thumb'

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
        Called once during __init__.
        """
        # QWidget as the central widget (QMainWindow requires one).
        container = QWidget()
        self.setCentralWidget(container)
        # QGridLayout allows precise row/column placement of labels and buttons.
        self._layout = QGridLayout(container)

        self._build_menu()
        self._build_labels()
        self._build_buttons()
        self._apply_layout()   # place all widgets into the grid for the initial view

    def _build_menu(self):
        """
        Add the 'View' menu to the menu bar. Each menu item switches the active
        sensor view, changing which finger's data is displayed in the labels.
        """
        view_menu = self.menuBar().addMenu('View')
        for name in ('Thumb', 'Pointer', 'Middle', 'Ring', 'Pinky', 'Wrist'):
            action = view_menu.addAction(name)
            # Lambda captures 'name' at definition time via the default argument trick
            # (n=name). Without this, all lambdas would capture the final value of 'name'.
            action.triggered.connect(lambda checked, n=name: self._change_view(n))

    def _build_labels(self):
        """
        Instantiate all QLabel widgets used to display sensor data.

        Labels are named by their role in finger views. In the Wrist view,
        some labels are hidden and others show different data — but the same
        label objects are reused to avoid rebuilding the layout each time.
        """
        self.timestampLabel  = self._centered_label('Timestamp: --')
        self.sampleRateLabel = self._centered_label('Sample Rate: -- Hz')
        self.viewTitleLabel  = self._centered_label('Thumb Data')
        self.viewTitleLabel.setStyleSheet("font-weight: bold; font-size: 14pt;")

        self.flexLabel        = self._centered_label('Flex: --')           # raw ADC value
        self.flexAngleLabel   = self._centered_label('Flex Angle (deg): --')  # converted angle
        self.gyroXLabel       = self._centered_label('Gyro X: --')
        self.gyroYLabel       = self._centered_label('Gyro Y: --')
        self.gyroZLabel       = self._centered_label('Gyro Z: --')
        self.accXLabel        = self._centered_label('Acc X: --')
        self.accYLabel        = self._centered_label('Acc Y: --')
        self.accZLabel        = self._centered_label('Acc Z: --')
        # Only visible in Wrist view — shows integrated [X, Y, Z] orientation in degrees.
        self.orientationLabel = self._centered_label('Wrist Orientation (deg): --')

    def _build_buttons(self):
        """
        Instantiate control buttons and connect them to their handlers.
        """
        # Zero Gyro: resets all integrated orientation quaternions to identity,
        # re-zeroing the reference frame from the hand's current physical pose.
        # Also signals the GyroRecorder to end the current recording episode.
        self.gyroResetButton = QPushButton("Zero Gyro", self)
        self.gyroResetButton.clicked.connect(self._zero_gyros)

        # Record Gyro: starts a new GyroRecorder episode (research scaffolding).
        # Can be removed along with GyroRecorder if research logging is no longer needed.
        self.gyroRecordButton = QPushButton("Record Gyro", self)
        self.gyroRecordButton.clicked.connect(self.gyroRecorder.start_episode)

    def _apply_layout(self):
        """
        Place all widgets into the QGridLayout for the current view.

        Called once during init and again each time the view is switched.
        Clears the layout first, then re-adds widgets in the correct positions.
        Widgets not used in the current view are hidden rather than destroyed.
        """
        # Remove all widgets from the layout without deleting them.
        # setParent(None) detaches the widget from the layout item; the widget
        # object itself is kept alive by the instance attributes (self.flexLabel, etc.).
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

        # Rows 0–2 are always visible regardless of the active view.
        self._layout.addWidget(self.timestampLabel,  0, 0, 1, 3)  # spans 3 columns
        self._layout.addWidget(self.sampleRateLabel, 1, 0, 1, 3)
        self._layout.addWidget(self.viewTitleLabel,  2, 0, 1, 3)

        if self._current_view == 'Wrist':
            # Wrist has no flex sensor — hide the flex labels.
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
            # Rows 6–7: buttons
            self._layout.addWidget(self.gyroResetButton,  6, 0, 1, 3)
            self._layout.addWidget(self.gyroRecordButton, 7, 0, 1, 3)

        else:
            # Finger views: show flex, angle, gyro, acc.
            self.flexLabel.show()
            self.flexAngleLabel.show()
            self.orientationLabel.hide()

            # Row 3: raw flex value and converted angle (two columns)
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
            # Rows 6–7: buttons
            self._layout.addWidget(self.gyroResetButton,  6, 0, 1, 3)
            self._layout.addWidget(self.gyroRecordButton, 7, 0, 1, 3)

    @staticmethod
    def _centered_label(text):
        """Create a QLabel with centred alignment. Used for all data display labels."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        return label

    # -----------------------------------------------------------------------
    # View switching
    # -----------------------------------------------------------------------

    def _change_view(self, view_name):
        """
        Switch the active view to view_name and refresh the display.

        Called when the user selects a finger from the View menu.
        Re-applies the layout (which hides/shows the appropriate labels for
        the new view) and immediately updates labels with the last known data
        so the display isn't blank until the next frame arrives.
        """
        self._current_view = view_name
        self.viewTitleLabel.setText(f'{view_name} Data')
        self._apply_layout()   # rebuild layout for new view (hides/shows labels)
        # Re-display the cached filtered data for the new view immediately.
        if self._filtered_data is not None:
            self._update_labels(self._filtered_data, self._current_timestamp)

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
        Called by SensorRead3_0.py when the user presses "Stop Acquisition".
        """
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

        # Update the rolling sample rate estimate. Must be called before process()
        # so the estimate reflects the current interval when filters are potentially rebuilt.
        self.processor.update_sample_rate()

        # Run all 41 channels through the Butterworth filter bank.
        # Returns None if the array is malformed.
        filtered = self.processor.process(data_array)
        if filtered is None:
            return

        # Cache for use by _change_view() when the user switches views.
        self._filtered_data     = filtered
        self._current_timestamp = timestamp

        # Update the sample rate label with the current estimate.
        self.sampleRateLabel.setText(
            f'Sample Rate: {self.processor.estimated_sample_rate:.1f} Hz'
        )

        # Update the kinematic model (joint angles + orientation integration).
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

        Two operations per frame:
            A. Flex → joint angles: the polynomial-converted flex values are split
               75%/25% between J1 and J2 joints, reflecting the biomechanical
               tendency for the proximal joint to flex more than the middle joint.
            B. Gyro → orientation: wrist and finger gyro values are integrated
               into running quaternions by RightHand.

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
            timestamp: seconds since acquisition start (used by GyroRecorder).
        """
        # --- A. Flex sensor → joint angles ---
        # Convert raw flex ADC values to degrees using the fitted polynomials.
        thumb_angle   = thumb_flex_to_angle(d[0])
        pointer_angle = finger_flex_to_angle(d[1])
        middle_angle  = finger_flex_to_angle(d[2])
        ring_angle    = finger_flex_to_angle(d[3])
        pinky_angle   = finger_flex_to_angle(d[4])

        # Split total flex angle 75% / 25% between J1 (proximal) and J2 (middle) joints.
        # The proximal joint (knuckle) accounts for more of the total finger bend.
        # The 'if angle else 0' guards against None returns from the polynomial functions
        # when the flex value is non-numeric during startup.
        self.rightHand.set_j1_angles(
            thumb_angle,                                      # thumb only has J1
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
            # Wrist gyro (indices 38-40): already in rad/s from SensorProcessor.
            self.rightHand.update_orientation(float(d[38]), float(d[39]), float(d[40]))

            # Finger gyros (indices 8-10, 14-16, 20-22, 26-28, 32-34):
            # these are also in rad/s (filtered but not unit-converted by SensorProcessor).
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

        # --- Research scaffolding: log gyro data if a recording episode is active ---
        # This block can be removed (along with the GyroRecorder import and attribute)
        # once research logging is no longer needed.
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
        j2 = self.rightHand.get_j2_angles()   # [pointer, middle, ring, pinky] (no thumb)

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

        # --- Finger views ---
        # FINGER_OFFSETS maps each view name to the three array index bases for
        # that finger's data in the filtered array:
        #   flex_i:  index of the flex value
        #   acc_i:   index of Acc X (Acc Y = acc_i+1, Acc Z = acc_i+2)
        #   gyro_i:  index of Gyro X (Gyro Y = gyro_i+1, Gyro Z = gyro_i+2)
        # These offsets directly mirror the layout documented in SensorProcessor.
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

            self.flexLabel.setText(      f'Flex: {fmt(flex_val)}')
            self.flexAngleLabel.setText( f'Flex Angle (deg): {fmt(angle)}')
            self.gyroXLabel.setText(     f'Gyro X: {fmt(d[gyro_i])}')
            self.gyroYLabel.setText(     f'Gyro Y: {fmt(d[gyro_i + 1])}')
            self.gyroZLabel.setText(     f'Gyro Z: {fmt(d[gyro_i + 2])}')
            self.accXLabel.setText(      f'Acc X: {fmt(d[acc_i])}')
            self.accYLabel.setText(      f'Acc Y: {fmt(d[acc_i + 1])}')
            self.accZLabel.setText(      f'Acc Z: {fmt(d[acc_i + 2])}')

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
            # This is the cumulative rotation since the last "Zero Gyro" press.
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
        the current pose becomes the new "zero" reference.

        Also signals the GyroRecorder to end the current recording episode
        (if one is active), since the zero event serves as a natural boundary
        in the research data.
        """
        self.rightHand.zero_orientation()   # reset wrist + all finger quaternions to identity
        self.gyroRecorder.stop_episode()    # research scaffolding: mark episode end
        print("Gyroscope orientation zeroed")
