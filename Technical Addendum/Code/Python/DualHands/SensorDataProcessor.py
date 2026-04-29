"""
SensorDataProcessor.py

Handles all signal processing for incoming glove sensor data:
  - Butterworth low-pass filtering for all 41 sensor channels
  - Live sample rate estimation
  - Flex-sensor-to-joint-angle polynomial conversions
  - [Research scaffolding] Per-finger gyro data recording to CSV

This module is used by GloveMonitorWindow to transform raw serial strings
into filtered, display-ready values before passing them on to HandKinematics
and the Qt label display.

Typical call sequence each frame:
    processor.update_sample_rate()       # track inter-sample timing
    filtered = processor.process(raw)    # filter all 41 channels
"""

import time                     # used to timestamp each incoming sample for rate estimation
import math                     # used for the deg/s → rad/s conversion (math.pi)
from collections import deque   # fixed-length queue for rolling sample-interval history
from csv import DictWriter       # used by GyroRecorder to append rows to CSV files
from scipy import signal         # provides the Butterworth filter design and IIR filter function


# ---------------------------------------------------------------------------
# Low-Pass Filter
# ---------------------------------------------------------------------------

class LowPassFilter:
    """
    Single-channel, stateful 2nd-order Butterworth IIR low-pass filter.

    "IIR" (Infinite Impulse Response) means the filter output depends on both
    the current input and its own previous outputs — this produces a smooth
    response with very few arithmetic operations per sample, which is important
    when filtering 41 channels at high sample rates.

    "Stateful" means the filter remembers where it left off between calls
    (stored in self.zi), so it can be fed one sample at a time from a live
    serial stream rather than needing the whole signal up front.

    A Butterworth filter is chosen because its frequency response is maximally
    flat in the passband (no ripple), which avoids distorting the sensor signals
    we want to keep.
    """

    def __init__(self, cutoff_freq=5, sample_rate=100, order=2):
        """
        Design the filter coefficients for the given sample rate and cutoff.

        Args:
            cutoff_freq:  Frequencies above this value (Hz) are attenuated.
                          Default 5 Hz — hand motion is slow; this removes
                          high-frequency electrical noise without blurring gesture.
            sample_rate:  Expected number of samples per second from the glove.
                          Must be at least 1; clamped to 100 if below.
            order:        Filter order. 2 gives a gentle 12 dB/octave roll-off.
                          Higher order = steeper cutoff but more phase lag.
        """
        # Guard against a degenerate sample rate (e.g. if the glove hasn't
        # started sending yet and rate estimation returns 0).
        if sample_rate < 1:
            sample_rate = 100

        # The Nyquist frequency is the highest frequency representable at this
        # sample rate. The cutoff must stay strictly below it.
        nyquist = sample_rate / 2

        # If someone passes a cutoff at or above Nyquist, clamp it to 90% of
        # Nyquist so scipy.signal.butter doesn't raise a ValueError.
        if cutoff_freq >= nyquist:
            cutoff_freq = nyquist * 0.9

        # scipy.signal.butter expects a "normalised" cutoff in (0, 1) where
        # 1.0 == the Nyquist frequency.
        normal_cutoff = cutoff_freq / nyquist

        # Final sanity clamp in case numerical edge cases produce a value
        # outside (0, 1) after the division.
        if not (0 < normal_cutoff < 1):
            normal_cutoff = 0.1

        # Design the filter: returns feedforward (b) and feedback (a) coefficient
        # arrays. These are the two arrays that define the IIR difference equation.
        self.b, self.a = signal.butter(order, normal_cutoff, btype='low')

        # Compute the steady-state initial conditions so the filter output
        # starts at a neutral (zero-equivalent) state rather than ringing
        # during the first few samples.
        self.zi = signal.lfilter_zi(self.b, self.a)

    def update(self, new_value):
        """
        Push one new sample through the filter and return the filtered value.

        self.zi carries the filter's memory forward between calls — this is
        what makes streaming filtering possible without re-processing history.

        Args:
            new_value: the raw sensor reading (string or float).

        Returns:
            The filtered float value, or the original new_value unchanged if
            it cannot be converted (e.g. a non-numeric string at startup).
        """
        try:
            value = float(new_value)   # convert string from serial to float
            # signal.lfilter processes a length-1 array [value], using and
            # updating self.zi in-place. filtered_value is also length-1.
            filtered_value, self.zi = signal.lfilter(self.b, self.a, [value], zi=self.zi)
            return filtered_value[0]   # unwrap the single-element array
        except (ValueError, TypeError):
            # If the value can't be cast (e.g. "ERR" during initialisation),
            # pass it through unchanged so the caller can handle it.
            return new_value


# ---------------------------------------------------------------------------
# Angle Conversion Helpers
# ---------------------------------------------------------------------------

def finger_flex_to_angle(flex_value):
    """
    Convert a raw ADC flex-sensor reading to an estimated joint angle in degrees
    for the four non-thumb fingers (pointer, middle, ring, pinky).

    The mapping is a cubic polynomial fitted empirically to (flex_reading, known_angle)
    calibration pairs collected across the flex sensor's physical range.
    A cubic is used because the flex sensor's resistance-versus-bend curve is
    nonlinear and a linear fit introduces visible error at the extremes.

    Args:
        flex_value: raw ADC value (int or float) from the flex sensor.

    Returns:
        Estimated joint angle in degrees, or None if the value is non-numeric.
    """
    try:
        flex = float(flex_value)
        # Cubic polynomial: angle = c3*x³ + c2*x² + c1*x + c0
        return 0.00001595 * flex**3 - 0.003083 * flex**2 + 0.4174 * flex + 0.8620
    except (ValueError, TypeError):
        return None   # caller checks for None before displaying


def thumb_flex_to_angle(flex_value):
    """
    Convert a raw ADC flex-sensor reading to an estimated joint angle in degrees
    for the thumb specifically.

    The thumb has different geometry and range of motion from the other fingers,
    so a separate polynomial fit was derived for it from thumb-specific calibration data.

    Args:
        flex_value: raw ADC value (int or float) from the thumb flex sensor.

    Returns:
        Estimated joint angle in degrees, or None if the value is non-numeric.
    """
    try:
        flex = float(flex_value)
        # Separate cubic polynomial fitted to thumb calibration data.
        return 0.000005956 * flex**3 - 0.001171 * flex**2 + 0.2502 * flex + 2.747
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Sensor Data Processor
# ---------------------------------------------------------------------------

class SensorProcessor:
    """
    Manages the complete per-frame filtering pipeline for one glove session.

    One SensorProcessor instance is created when the acquisition window opens
    and lives for the duration of the session. It owns all 41 filter instances
    and the sample rate estimator.

    Raw serial data layout (41 comma-separated values, 0-indexed):
    ┌─────────┬────────────────────────────────────────────────────────┐
    │ Index   │ Content                                                │
    ├─────────┼────────────────────────────────────────────────────────┤
    │  0 – 4  │ Flex sensor ADC readings: Thumb, Pointer, Middle,      │
    │         │   Ring, Pinky                                          │
    │  5 – 10 │ Thumb IMU:  Acc X/Y/Z (m/s²), Gyro X/Y/Z (deg/s)     │
    │ 11 – 16 │ Pointer IMU: same layout                              │
    │ 17 – 22 │ Middle IMU:  same layout                              │
    │ 23 – 28 │ Ring IMU:    same layout                              │
    │ 29 – 34 │ Pinky IMU:   same layout                              │
    │ 35 – 37 │ Wrist IMU:  Acc X/Y/Z (m/s²)                         │
    │ 38 – 40 │ Wrist IMU:  Gyro X/Y/Z (deg/s) ← converted to rad/s  │
    │    41   │ Hand label string (optional, passed through unchanged) │
    └─────────┴────────────────────────────────────────────────────────┘

    The output of process() has the same layout, with all numeric values
    replaced by their filtered equivalents and wrist gyro converted to rad/s.
    """

    # Class-level constants: number of independent filter instances per group.
    # Each axis of each sensor gets its own filter so their states never mix.
    NUM_FLEX_FILTERS = 5    # one per finger (thumb through pinky)
    NUM_ACC_FILTERS  = 18   # 3 axes × 6 IMUs (5 fingers + 1 wrist)
    NUM_GYRO_FILTERS = 18   # 3 axes × 6 IMUs (5 fingers + 1 wrist)

    def __init__(self, initial_sample_rate=100, cutoff_freq=5):
        """
        Args:
            initial_sample_rate: Hz to use for initial filter design. The live
                estimator will update this as real data arrives. 100 Hz is a
                reasonable starting assumption for the glove hardware.
            cutoff_freq: Low-pass cutoff in Hz, shared by all filter instances.
                5 Hz passes all intentional hand gesture motion while blocking
                electrical noise and vibration artefacts.
        """
        self._cutoff_freq = cutoff_freq   # stored so filters can be rebuilt at the same cutoff later

        # --- Sample rate estimation state ---
        # We don't know the true sample rate until data starts arriving, so we
        # estimate it by measuring the wall-clock time between successive frames.
        self._last_update_time = None              # timestamp of the previous call
        self._sample_intervals = deque(maxlen=50)  # rolling window of inter-sample gaps (seconds)
        self.estimated_sample_rate = initial_sample_rate  # current best estimate (Hz)

        # Create all filter instances using the initial rate assumption.
        self._init_filters(initial_sample_rate)

    # --- Filter management --------------------------------------------------

    def _init_filters(self, sample_rate):
        """
        (Re-)create all filter bank instances for the given sample rate.

        Called once at startup and again whenever the estimated rate changes
        by more than 10 Hz. Rebuilding resets all filter states (zi), which
        causes a brief transient in the output — acceptable because a rate
        shift this large indicates a hardware change anyway.

        Args:
            sample_rate: the new sample rate (Hz) to design filters for.
        """
        # List comprehensions create one LowPassFilter per channel.
        # Each filter is independent — separate state, separate coefficients.
        self.flex_filters = [
            LowPassFilter(self._cutoff_freq, sample_rate) for _ in range(self.NUM_FLEX_FILTERS)
        ]
        self.gyro_filters = [
            LowPassFilter(self._cutoff_freq, sample_rate) for _ in range(self.NUM_GYRO_FILTERS)
        ]
        self.acc_filters = [
            LowPassFilter(self._cutoff_freq, sample_rate) for _ in range(self.NUM_ACC_FILTERS)
        ]

    def update_sample_rate(self):
        """
        Measure the time since the last call and update the sample rate estimate.

        Must be called once per incoming data frame, before process().
        Uses a rolling average of the last 50 inter-sample intervals to smooth
        over jitter in the serial delivery timing.

        If the newly estimated rate differs from the current estimate by more
        than 10 Hz, all filter banks are rebuilt for the new rate. The 10 Hz
        hysteresis prevents constant rebuilding due to minor timing jitter.
        """
        current_time = time.time()   # wall clock, seconds (float)

        if self._last_update_time is not None:
            interval = current_time - self._last_update_time   # seconds between this and last frame
            if interval > 0:   # guard against duplicate timestamps on very fast hardware
                self._sample_intervals.append(interval)

                # Only estimate once we have at least 10 intervals to average.
                # Fewer than 10 gives an unreliable estimate during startup.
                if len(self._sample_intervals) >= 10:
                    avg_interval = sum(self._sample_intervals) / len(self._sample_intervals)
                    new_rate = 1.0 / avg_interval   # Hz = 1 / seconds_per_sample

                    if abs(new_rate - self.estimated_sample_rate) > 10:
                        # Rate has shifted significantly — rebuild filters for the new rate.
                        # This resets filter state (zi), causing a brief output transient.
                        self.estimated_sample_rate = new_rate
                        self._init_filters(self.estimated_sample_rate)
                        print(f"Sample rate updated to: {self.estimated_sample_rate:.1f} Hz")
                    else:
                        # Small drift — update the estimate without rebuilding filters.
                        self.estimated_sample_rate = new_rate

        self._last_update_time = current_time   # store for next call's interval measurement

    # --- Main filtering pipeline --------------------------------------------

    def process(self, data_array):
        """
        Filter all sensor channels from one incoming data frame.

        Iterates through the raw data array in the order defined by the serial
        protocol, passing each value through its dedicated filter instance.
        The wrist gyro channels are unit-converted (deg/s → rad/s) before
        filtering because HandKinematics expects rad/s for quaternion integration.

        Args:
            data_array: list of raw values (strings or floats), length >= 41.
                        Produced by splitting one serial line on commas.

        Returns:
            A new list of the same length with all numeric values replaced by
            their filtered equivalents, or None if the array is too short or
            a conversion error occurs.
        """
        if len(data_array) < 41:
            return None   # incomplete frame — discard silently

        filtered = []   # built up in the same index order as data_array
        try:
            # --- Flex sensors (indices 0–4) ---
            # Each of the 5 fingers has one dedicated flex filter.
            # flex_filters[0] = thumb, [1] = pointer, ..., [4] = pinky.
            for i in range(5):
                filtered.append(self.flex_filters[i].update(data_array[i]))

            # --- Finger IMU blocks (indices 5–34) ---
            # Each finger contributes 6 consecutive values: Acc X, Acc Y, Acc Z,
            # Gyro X, Gyro Y, Gyro Z. The five blocks start at indices 5, 11, 17, 23, 29.
            #
            # Filter index mapping:
            #   acc_filters[0..2]   = Thumb Acc X/Y/Z
            #   acc_filters[3..5]   = Pointer Acc X/Y/Z
            #   acc_filters[6..8]   = Middle Acc X/Y/Z
            #   acc_filters[9..11]  = Ring Acc X/Y/Z
            #   acc_filters[12..14] = Pinky Acc X/Y/Z
            #   (acc_filters[15..17] are reserved for the wrist block below)
            #
            #   gyro_filters[0..2]  = Thumb Gyro X/Y/Z
            #   gyro_filters[3..5]  = Pointer Gyro X/Y/Z
            #   ... gyro_filters[12..14] = Pinky Gyro X/Y/Z
            #   (gyro_filters[15..17] are reserved for the wrist block below)
            finger_starts = [5, 11, 17, 23, 29]   # index of Acc X for each finger in data_array
            for finger_idx, start in enumerate(finger_starts):
                acc_base  = finger_idx * 3   # first acc filter index for this finger
                gyro_base = finger_idx * 3   # first gyro filter index for this finger
                # Filter Acc X, Acc Y, Acc Z (at offsets 0, 1, 2 from start)
                for i in range(3):
                    filtered.append(self.acc_filters[acc_base + i].update(data_array[start + i]))
                # Filter Gyro X, Gyro Y, Gyro Z (at offsets 3, 4, 5 from start)
                for i in range(3):
                    filtered.append(self.gyro_filters[gyro_base + i].update(data_array[start + 3 + i]))

            # --- Wrist accelerometer (indices 35–37) ---
            # acc_filters[15, 16, 17] are dedicated to the wrist.
            # (index 15 = 5 fingers × 3 axes per finger)
            for i in range(3):
                filtered.append(self.acc_filters[15 + i].update(data_array[35 + i]))

            # --- Wrist gyroscope (indices 38–40): unit conversion + filter ---
            # The wrist gyro arrives in degrees/second from the hardware.
            # HandKinematics.update_orientation() expects rad/s for its
            # Rotation.from_rotvec() call (which works in radians).
            # Conversion: rad/s = deg/s × (π / 180)
            # gyro_filters[15, 16, 17] are dedicated to the wrist.
            for i in range(3):
                try:
                    dps = float(data_array[38 + i])          # raw deg/s value from hardware
                    rad_per_sec = dps * (math.pi / 180.0)    # convert to rad/s
                    filtered.append(self.gyro_filters[15 + i].update(rad_per_sec))
                except (ValueError, TypeError):
                    # Non-numeric value (e.g. during startup) — substitute 0
                    # so downstream quaternion integration doesn't blow up.
                    filtered.append(0.0)

            # --- Hand label (index 41, optional) ---
            # A single string token appended by the firmware to identify which
            # hand is being used. Not a numeric sensor — passed through unchanged.
            filtered.append(data_array[41] if len(data_array) > 41 else '0')

        except (ValueError, IndexError):
            # Any unexpected conversion failure discards the whole frame.
            return None

        return filtered   # same layout as input, all numerics now filtered floats


# ---------------------------------------------------------------------------
# --- Temporary Research Scaffolding ---
#
# GyroRecorder supports ad-hoc data collection sessions during development.
# It is NOT part of the core acquisition pipeline and can be safely removed
# (along with the gyroRecorder calls in GloveMonitorWindow) once the gyro
# calibration research phase is complete.
# ---------------------------------------------------------------------------

class GyroRecorder:
    """
    Records raw per-finger gyro readings to individual CSV files during
    manually-bounded episodes, for offline gyroscope calibration analysis.

    An "episode" is a single continuous recording session, delimited by
    button presses in the UI:
        - "Record Gyro" button  → start_episode()  → sets _begin_flag
        - "Zero Gyro"   button  → stop_episode()   → sets _end_flag
    The flags are consumed on the next call to record(), which writes a
    'start' or 'end' marker into the CSV for that sample.

    Each call to record() appends one row to each of six CSV files
    (one per sensor location) if an episode is currently active.

    Output files (appended, not overwritten, across sessions):
        gyro_log2.csv        — wrist
        gyro_log_thumb.csv   — thumb
        gyro_log_point.csv   — pointer
        gyro_log_mid.csv     — middle
        gyro_log_ring.csv    — ring
        gyro_log_pink.csv    — pinky

    Each row contains: episode_id, timestamp, wx, wy, wz, marker
    """

    # Maps logical sensor name → output file path.
    # Defined at class level so all instances share the same file names.
    FILE_MAP = {
        'wrist':   'gyro_log2.csv',
        'thumb':   'gyro_log_thumb.csv',
        'pointer': 'gyro_log_point.csv',
        'middle':  'gyro_log_mid.csv',
        'ring':    'gyro_log_ring.csv',
        'pinky':   'gyro_log_pink.csv',
    }
    FIELDS = ['episode_id', 'timestamp', 'wx', 'wy', 'wz', 'marker']

    def __init__(self):
        self.session           = 0      # monotonically-increasing episode counter
        self.is_recording      = False  # True while an episode is active
        self._begin_flag       = False  # set by start_episode(), consumed by record()
        self._end_flag         = False  # set by stop_episode(),  consumed by record()
        self.started_recording = False  # latched True once any recording has ever started

    def start_episode(self):
        """
        Signal that a new recording episode should begin on the next frame.
        Called when the user clicks the "Record Gyro" button.

        Sets _begin_flag rather than acting immediately so that the flag is
        consumed and written as a 'start' marker in the same CSV row as
        the first data sample of the episode.
        """
        if not self.is_recording:
            self._begin_flag = True
            print("Gyro recording started")
        else:
            print("Gyro recording already in progress")

    def stop_episode(self):
        """
        Signal that the current episode should end on the next frame.
        Called when the user clicks "Zero Gyro" (which serves dual purpose:
        resetting orientation AND marking the end of a recording episode).

        Sets _end_flag rather than acting immediately so the 'end' marker
        is written into the last CSV row of the episode.
        """
        if self.is_recording:
            self._end_flag = True
            print("Gyro recording ended")

    def record(self, timestamp, wrist, thumb, pointer, middle, ring, pinky):
        """
        Append one row of gyro data per sensor to the CSV files, if an episode
        is active (or is just beginning/ending on this frame).

        Called every frame from GloveMonitorWindow._update_kinematics().
        This is a no-op when no episode is active and no flags are set.

        Args:
            timestamp:  float — seconds since acquisition start.
            wrist:      (x, y, z) tuple of wrist gyro values.
            thumb:      (x, y, z) tuple of thumb gyro values.
            pointer:    (x, y, z) tuple of pointer gyro values.
            middle:     (x, y, z) tuple of middle gyro values.
            ring:       (x, y, z) tuple of ring gyro values.
            pinky:      (x, y, z) tuple of pinky gyro values.
        """
        # --- Determine the marker string and whether to write this sample ---
        marker = ""                             # empty string = mid-episode sample
        record_this_sample = self.is_recording  # default: write only if already active

        if self._end_flag and self._begin_flag:
            # Both flags set at once — this shouldn't happen in normal use.
            marker = "error - begin and end"
            print("Error: begin and end flags set simultaneously on GyroRecorder")

        elif self._end_flag:
            # This is the last sample of the episode.
            marker = "end"
            self.is_recording = False   # deactivate recording after writing this row

        elif self._begin_flag:
            # This is the first sample of a new episode.
            marker = "start"
            self.is_recording  = True   # activate recording
            record_this_sample = True   # write this frame even though we just started
            self.session      += 1      # increment episode counter for the episode_id column

        # --- Write one row per sensor to its dedicated CSV file ---
        if record_this_sample:
            sensor_data = {
                'wrist':   wrist,
                'thumb':   thumb,
                'pointer': pointer,
                'middle':  middle,
                'ring':    ring,
                'pinky':   pinky,
            }
            for name, (x, y, z) in sensor_data.items():
                row = {
                    'episode_id': self.session,
                    'timestamp':  timestamp,
                    'wx': x,
                    'wy': y,
                    'wz': z,
                    'marker': marker,   # 'start', 'end', or '' for mid-episode rows
                }
                # Open in append mode ('a') so multiple episodes accumulate
                # in the same file across the session without overwriting.
                with open(self.FILE_MAP[name], 'a', newline='') as f:
                    DictWriter(f, fieldnames=self.FIELDS).writerow(row)

        # --- Consume both flags regardless of outcome ---
        # Flags are single-use: reset here so they don't affect subsequent frames.
        self._begin_flag = False
        self._end_flag   = False
