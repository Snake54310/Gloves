"""
SensorDataProcessor.py

Handles all signal processing for incoming glove sensor data:
  - Butterworth low-pass filtering for all 41 sensor channels
  - Live sample rate estimation
  - Flex-sensor-to-joint-angle polynomial conversions
  - [Research scaffolding] Per-finger gyro data recording to CSV
  - Position recording: continuous CSV logging and labelled snapshot capture
    for random-forest training data collection.

This module is used by GloveMonitorWindow to transform raw serial strings
into filtered, display-ready values before passing them on to HandKinematics
and the Qt label display.

Typical call sequence each frame:
    processor.update_sample_rate()       # track inter-sample timing
    filtered = processor.process(raw)    # filter all 41 channels
"""

import os
import time
import math
from collections import deque
from csv import DictWriter
from scipy import signal


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


# ---------------------------------------------------------------------------
# Angle Conversion Helpers
# ---------------------------------------------------------------------------

def finger_flex_to_angle(flex_value):
    try:
        flex = float(flex_value)
        return 0.00001595 * flex**3 - 0.003083 * flex**2 + 0.4174 * flex + 0.8620
    except (ValueError, TypeError):
        return None


def thumb_flex_to_angle(flex_value):
    try:
        flex = float(flex_value)
        return 0.000005956 * flex**3 - 0.001171 * flex**2 + 0.2502 * flex + 2.747
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Sensor Data Processor
# ---------------------------------------------------------------------------

class SensorProcessor:
    NUM_FLEX_FILTERS = 5
    NUM_ACC_FILTERS  = 18
    NUM_GYRO_FILTERS = 18

    def __init__(self, initial_sample_rate=100, cutoff_freq=5):
        self._cutoff_freq = cutoff_freq

        self._last_update_time = None
        self._sample_intervals = deque(maxlen=50)
        self.estimated_sample_rate = initial_sample_rate

        self._init_filters(initial_sample_rate)

    def _init_filters(self, sample_rate):
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
        current_time = time.time()

        if self._last_update_time is not None:
            interval = current_time - self._last_update_time
            if interval > 0:
                self._sample_intervals.append(interval)

                if len(self._sample_intervals) >= 10:
                    avg_interval = sum(self._sample_intervals) / len(self._sample_intervals)
                    new_rate = 1.0 / avg_interval

                    if abs(new_rate - self.estimated_sample_rate) > 10:
                        self.estimated_sample_rate = new_rate
                        self._init_filters(self.estimated_sample_rate)
                        print(f"Sample rate updated to: {self.estimated_sample_rate:.1f} Hz")
                    else:
                        self.estimated_sample_rate = new_rate

        self._last_update_time = current_time

    def process(self, data_array):
        if len(data_array) < 41:
            return None

        filtered = []
        try:
            for i in range(5):
                filtered.append(self.flex_filters[i].update(data_array[i]))

            finger_starts = [5, 11, 17, 23, 29]
            for finger_idx, start in enumerate(finger_starts):
                acc_base  = finger_idx * 3
                gyro_base = finger_idx * 3
                for i in range(3):
                    filtered.append(self.acc_filters[acc_base + i].update(data_array[start + i]))
                for i in range(3):
                    filtered.append(self.gyro_filters[gyro_base + i].update(data_array[start + 3 + i]))

            for i in range(3):
                filtered.append(self.acc_filters[15 + i].update(data_array[35 + i]))

            for i in range(3):
                try:
                    dps = float(data_array[38 + i])
                    rad_per_sec = dps * (math.pi / 180.0)
                    filtered.append(self.gyro_filters[15 + i].update(rad_per_sec))
                except (ValueError, TypeError):
                    filtered.append(0.0)

            filtered.append(data_array[41] if len(data_array) > 41 else '0')

        except (ValueError, IndexError):
            return None

        return filtered


# ---------------------------------------------------------------------------
# GyroRecorder  (research scaffolding — unchanged)
# ---------------------------------------------------------------------------

class GyroRecorder:
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
        self.session           = 0
        self.is_recording      = False
        self._begin_flag       = False
        self._end_flag         = False

    def start_episode(self):
        if not self.is_recording:
            self._begin_flag = True
            print("Gyro recording started")
        else:
            print("Gyro recording already in progress")

    def stop_episode(self):
        if self.is_recording:
            self._end_flag = True
            print("Gyro recording ended")

    def record(self, timestamp, wrist, thumb, pointer, middle, ring, pinky):
        marker = ""
        record_this_sample = self.is_recording

        if self._end_flag and self._begin_flag:
            marker = "error - begin and end"
            print("Error: begin and end flags set simultaneously on GyroRecorder")
        elif self._end_flag:
            marker = "end"
            self.is_recording = False
        elif self._begin_flag:
            marker = "start"
            self.is_recording  = True
            record_this_sample = True
            self.session      += 1

        if record_this_sample:
            sensor_data = {
                'wrist': wrist, 'thumb': thumb, 'pointer': pointer,
                'middle': middle, 'ring': ring, 'pinky': pinky,
            }
            for name, (x, y, z) in sensor_data.items():
                row = {
                    'episode_id': self.session,
                    'timestamp':  timestamp,
                    'wx': x, 'wy': y, 'wz': z,
                    'marker': marker,
                }
                with open(self.FILE_MAP[name], 'a', newline='') as f:
                    DictWriter(f, fieldnames=self.FIELDS).writerow(row)

        self._begin_flag = False
        self._end_flag   = False


# ---------------------------------------------------------------------------
# PositionRecorder
# ---------------------------------------------------------------------------

POSITION_FIELDS = [
    'Timestamp_RealTime', 'Timestamp_RunTime',
    'Wrist_qx', 'Wrist_qy', 'Wrist_qz', 'Wrist_qw',
    'Thumb_qx', 'Thumb_qy', 'Thumb_qz', 'Thumb_qw',
    'Pointer_qx', 'Pointer_qy', 'Pointer_qz', 'Pointer_qw',
    'Middle_qx', 'Middle_qy', 'Middle_qz', 'Middle_qw',
    'Ring_qx', 'Ring_qy', 'Ring_qz', 'Ring_qw',
    'Pinky_qx', 'Pinky_qy', 'Pinky_qz', 'Pinky_qw',
    'Thumb_J1', 'Pointer_J1', 'Middle_J1', 'Ring_J1', 'Pinky_J1',
    'Pointer_J2', 'Middle_J2', 'Ring_J2', 'Pinky_J2',
]

SNAPSHOT_FIELDS = POSITION_FIELDS + ['Label']


class PositionRecorder:
    SNAPSHOT_LABELS = ('thumbs_up', 'thumbs_down', 'peace', 'point', 'no_position')

    def __init__(self,
                 continuous_filename='PositionData_Continuous.csv',
                 snapshot_filename='PositionData_Snapshots.csv'):

        self.continuous_filename = continuous_filename
        self.snapshot_filename   = snapshot_filename
        self.is_recording = False

    @staticmethod
    def _build_position_row(runtime_timestamp, wrist_q, finger_qs, j1_angles, j2_angles):
        return {
            'Timestamp_RealTime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'Timestamp_RunTime':  round(runtime_timestamp, 4),
            'Wrist_qx': wrist_q[0], 'Wrist_qy': wrist_q[1], 'Wrist_qz': wrist_q[2], 'Wrist_qw': wrist_q[3],
            'Thumb_qx': finger_qs[0], 'Thumb_qy': finger_qs[1], 'Thumb_qz': finger_qs[2], 'Thumb_qw': finger_qs[3],
            'Pointer_qx': finger_qs[4], 'Pointer_qy': finger_qs[5], 'Pointer_qz': finger_qs[6], 'Pointer_qw': finger_qs[7],
            'Middle_qx': finger_qs[8], 'Middle_qy': finger_qs[9], 'Middle_qz': finger_qs[10], 'Middle_qw': finger_qs[11],
            'Ring_qx': finger_qs[12], 'Ring_qy': finger_qs[13], 'Ring_qz': finger_qs[14], 'Ring_qw': finger_qs[15],
            'Pinky_qx': finger_qs[16], 'Pinky_qy': finger_qs[17], 'Pinky_qz': finger_qs[18], 'Pinky_qw': finger_qs[19],
            'Thumb_J1': j1_angles[0], 'Pointer_J1': j1_angles[1], 'Middle_J1': j1_angles[2],
            'Ring_J1': j1_angles[3], 'Pinky_J1': j1_angles[4],
            'Pointer_J2': j2_angles[0], 'Middle_J2': j2_angles[1], 'Ring_J2': j2_angles[2], 'Pinky_J2': j2_angles[3],
        }

    @staticmethod
    def _append_row(filename, fields, row):
        write_header = not os.path.exists(filename) or os.path.getsize(filename) == 0
        with open(filename, 'a', newline='') as f:
            writer = DictWriter(f, fieldnames=fields)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    def start_continuous(self):
        if not self.is_recording:
            self.is_recording = True
            print(f"Continuous position recording started → {self.continuous_filename}")

    def stop_continuous(self):
        if self.is_recording:
            self.is_recording = False
            print(f"Continuous position recording stopped → {self.continuous_filename}")

    def record_continuous(self, runtime_timestamp, wrist_q, finger_qs, j1_angles, j2_angles):
        if not self.is_recording:
            return
        row = self._build_position_row(runtime_timestamp, wrist_q, finger_qs, j1_angles, j2_angles)
        self._append_row(self.continuous_filename, POSITION_FIELDS, row)

    def record_snapshot(self, runtime_timestamp, wrist_q, finger_qs, j1_angles, j2_angles, label):
        if label not in self.SNAPSHOT_LABELS:
            print(f"Warning: unknown snapshot label '{label}'")
            return
        row = self._build_position_row(runtime_timestamp, wrist_q, finger_qs, j1_angles, j2_angles)
        row['Label'] = label
        self._append_row(self.snapshot_filename, SNAPSHOT_FIELDS, row)
        print(f"Snapshot recorded: {label} → {self.snapshot_filename}")