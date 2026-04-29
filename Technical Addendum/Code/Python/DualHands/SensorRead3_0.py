import serial
import csv
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
import sys
from GloveMonitorWindow import GloveMonitorWindow

# ============================================================
# Default COM port values — edit these to match your hardware
# ============================================================
DEFAULT_PORT_RIGHT = 'COM13'
DEFAULT_PORT_LEFT  = 'COM8'

baudRate = 2000000

# ---- Right glove state ----
port_right      = DEFAULT_PORT_RIGHT
reader_right    = None
dataThread_right = None
csvFile_right   = None
csvWriter_right = None
outputFileName_right = "GloveData_Right.csv"

# ---- Left glove state ----
port_left       = DEFAULT_PORT_LEFT
reader_left     = None
dataThread_left = None
csvFile_left    = None
csvWriter_left  = None
outputFileName_left = "GloveData_Left.csv"

enable_right = False
enable_left  = False

liveGUIWindow = None   # single shared GloveMonitorWindow (contains both hands)

startTime = 0.0


# ------------------------------------------------------------
# CSV header row
# ------------------------------------------------------------
CSV_HEADER = [
    "Timestamp",
    "Thumb Flex", "Pointer Flex", "Middle Flex", "Ring Flex", "Pinky Flex",
    "Thumb Acc. X", "Thumb Acc. Y", "Thumb Acc. Z", "Thumb Gyro X", "Thumb Gyro Y", "Thumb Gyro Z",
    "Pointer Acc. X", "Pointer Acc. Y", "Pointer Acc. Z", "Pointer Gyro X", "Pointer Gyro Y", "Pointer Gyro Z",
    "Middle Acc. X", "Middle Acc. Y", "Middle Acc. Z", "Middle Gyro X", "Middle Gyro Y", "Middle Gyro Z",
    "Ring Acc. X", "Ring Acc. Y", "Ring Acc. Z", "Ring Gyro X", "Ring Gyro Y", "Ring Gyro Z",
    "Pinky Acc. X", "Pinky Acc. Y", "Pinky Acc. Z", "Pinky Gyro X", "Pinky Gyro Y", "Pinky Gyro Z",
    "Wrist Gyro X", "Wrist Gyro Y", "Wrist Gyro Z", "Wrist Acc. X", "Wrist Acc. Y", "Wrist Acc. Z",
    "Hand",
]


# ============================================================
# Helpers
# ============================================================

def set_status(status):
    """Update the status bar label from any thread."""
    root.after(0, statusText.config, {"text": status})
    root.after(0, statusText.update)


def _open_serial(port):
    """Open a serial port and wait 3 s for the device to boot."""
    reader = serial.Serial(port, baudRate)
    time.sleep(3)
    return reader


# ============================================================
# Live display helpers
# ============================================================

def liveDisplayOpen():
    global liveGUIWindow
    liveGUIWindow = GloveMonitorWindow()
    liveGUIWindow.initDisplay()
    return liveGUIWindow


def liveDisplayClose(window):
    global liveGUIWindow
    if window is not None:
        window.terminateDisplay()
        window.deleteLater()
    liveGUIWindow = None


# ============================================================
# START — both gloves
# ============================================================

def start_data_acquire():
    global enable_right, enable_left
    global reader_right, reader_left
    global dataThread_right, dataThread_left
    global outputFileName_right, outputFileName_left
    global port_right, port_left
    global liveGUIWindow, startTime

    outputFileName_right = fileNameEntry_right.get()
    outputFileName_left  = fileNameEntry_left.get()
    port_right = comPortEntry_right.get()
    port_left  = comPortEntry_left.get()

    try:
        set_status("Connecting to gloves...")

        if reader_right is None:
            reader_right = _open_serial(port_right)
        if reader_left is None:
            reader_left = _open_serial(port_left)

        startButton.configure(state=tk.DISABLED)
        stopButton.configure(state=tk.NORMAL)

        liveGUIWindow = liveDisplayOpen()

        startTime = time.perf_counter()

        dataThread_right = threading.Thread(
            target=data_acquire,
            args=(reader_right, outputFileName_right, 'right'),
            daemon=True,
        )
        dataThread_left = threading.Thread(
            target=data_acquire,
            args=(reader_left, outputFileName_left, 'left'),
            daemon=True,
        )
        dataThread_right.start()
        dataThread_left.start()

        set_status("Reading data...")

    except serial.SerialException as e:
        messagebox.showerror("Error", f"Could not open serial port:\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)

    except Exception as e:
        set_status(f"Unexpected error: {e}")
        messagebox.showerror("Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)


# ============================================================
# Data acquisition thread (runs once per glove)
# ============================================================

def data_acquire(reader, output_filename, hand_side):
    """
    hand_side: 'right' or 'left'
    Reads serial data and writes to CSV.  Also forwards each frame to the
    shared GloveMonitorWindow.
    """
    global enable_right, enable_left, liveGUIWindow, startTime

    enable_flag_name = f'enable_{hand_side}'   # 'enable_right' or 'enable_left'

    # Signal glove to start sending
    reader.write(b"ON\n")

    csv_file   = open(output_filename, 'w', newline='')
    csv_writer = csv.writer(csv_file, lineterminator='\n')
    csv_writer.writerow(CSV_HEADER)

    # Set the enable flag for this side
    if hand_side == 'right':
        global enable_right
        enable_right = True
    else:
        global enable_left
        enable_left = True

    try:
        while globals()[enable_flag_name] and reader.isOpen():
            raw = reader.readline().decode('utf-8').strip()
            if raw:
                timestamp = round(time.perf_counter() - startTime, 3)
                row = raw.split(',')
                row.insert(0, timestamp)
                csv_writer.writerow(row)

                if liveGUIWindow:
                    liveGUIWindow.updateData(raw, timestamp, hand_side)

    except serial.SerialException as e:
        messagebox.showerror("Error", f"Serial error ({hand_side}):\n{e}")
    except Exception as e:
        set_status(f"Unexpected error ({hand_side}): {e}")
        messagebox.showerror("Error", f"Unexpected Error ({hand_side})\n{e}")
    finally:
        try:
            csv_file.close()
        except Exception:
            pass


# ============================================================
# STOP
# ============================================================

def stop_data():
    global enable_right, enable_left, reader_right, reader_left

    set_status("Stopping...")
    enable_right = False
    enable_left  = False

    for reader in (reader_right, reader_left):
        if reader:
            try:
                reader.write(b"OFF\n")
            except Exception:
                pass

    stopButton.config(state=tk.DISABLED)
    startButton.config(state=tk.NORMAL)
    set_status(f"Data saved to {outputFileName_right} and {outputFileName_left}")

    liveDisplayClose(liveGUIWindow)


# ============================================================
# Resource cleanup
# ============================================================

def free_resources():
    global reader_right, reader_left, dataThread_right, dataThread_left, liveGUIWindow

    if liveGUIWindow is not None:
        try:
            liveGUIWindow.close()
            liveGUIWindow.deleteLater()
        except Exception:
            pass
        liveGUIWindow = None

    for reader, name in ((reader_right, 'right'), (reader_left, 'left')):
        if reader:
            try:
                reader.close()
                print(f"Serial port ({name}) closed")
            except serial.SerialException as e:
                print(f"Error closing serial port ({name}): {e}")

    for thread, name in ((dataThread_right, 'right'), (dataThread_left, 'left')):
        if thread and thread.is_alive():
            try:
                thread.join(timeout=2)
                print(f"Data thread ({name}) closed")
            except Exception as e:
                print(f"Error joining data thread ({name}): {e}")


def on_close():
    if enable_right or enable_left:
        if messagebox.askokcancel("Warning", "Data acquisition is still running. Continue?"):
            free_resources()
            root.destroy()
            sys.exit()
    else:
        free_resources()
        root.destroy()
        sys.exit()


# ============================================================
# Calibration — separate per glove
# ============================================================

def _ensure_serial(port, reader_attr):
    """Open serial for the given port if not already open. Returns reader."""
    reader = globals()[reader_attr]
    if reader is None:
        set_status("Connecting to glove...")
        reader = serial.Serial(port, baudRate)
        globals()[reader_attr] = reader
        time.sleep(1)
    return reader


def calibrate_right():
    global reader_right, port_right
    port_right = comPortEntry_right.get()
    try:
        reader_right = _ensure_serial(port_right, 'reader_right')
    except serial.SerialException as e:
        messagebox.showerror("Error", f"Could not open serial port (right):\n{e}")
        return
    calibrationFrame1.lift()
    calibrationFrame1._target_reader = 'reader_right'
    calibrationFrame1._target_frame  = calibrationFrame2R


def calibrate_left():
    global reader_left, port_left
    port_left = comPortEntry_left.get()
    try:
        reader_left = _ensure_serial(port_left, 'reader_left')
    except serial.SerialException as e:
        messagebox.showerror("Error", f"Could not open serial port (left):\n{e}")
        return
    calibrationFrame1L.lift()
    calibrationFrame1L._target_reader = 'reader_left'
    calibrationFrame1L._target_frame  = calibrationFrame2L


def calibration1_generic(frame1, frame2):
    reader = globals()[frame1._target_reader]
    if reader:
        reader.write(b"CAL1\n")
    frame2._target_reader = frame1._target_reader
    frame2.lift()


def calibration2_generic(frame2):
    reader = globals()[frame2._target_reader]
    if reader:
        reader.write(b"CAL2\n")
    calibrationFinishedFrame.lift()


def finishCalibration():
    dataFrame.lift()
    startButton.configure(state=tk.NORMAL)
    set_status("Ready to collect data")


# ============================================================
# UI construction
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Dual Glove Data Reader")

    # --------------------------------------------------------
    # Main data frame
    # --------------------------------------------------------
    dataFrame = ttk.Frame(root)
    dataFrame.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    dataFrame.grid_columnconfigure(0, weight=1, pad=10)
    dataFrame.grid_columnconfigure(1, weight=1, pad=10)
    dataFrame.grid_columnconfigure(2, weight=1, pad=10)

    # --- Right glove row ---
    ttk.Label(dataFrame, text="Right Glove Output File:").grid(column=0, row=0, sticky="E")
    fileNameEntry_right = ttk.Entry(dataFrame)
    fileNameEntry_right.grid(column=1, row=0, padx=5, sticky="NSEW")
    fileNameEntry_right.insert(0, outputFileName_right)

    ttk.Label(dataFrame, text="COM Port (Right):").grid(column=0, row=1, sticky="E")
    comPortEntry_right = ttk.Entry(dataFrame)
    comPortEntry_right.grid(column=1, row=1, padx=5, sticky="NSEW")
    comPortEntry_right.insert(0, DEFAULT_PORT_RIGHT)

    calibrateButtonRight = ttk.Button(dataFrame, text="Calibrate Right Glove",
                                      command=calibrate_right)
    calibrateButtonRight.grid(column=2, row=0, rowspan=2, padx=5, sticky="NSEW")

    # --- Left glove row ---
    ttk.Label(dataFrame, text="Left Glove Output File:").grid(column=0, row=2, sticky="E")
    fileNameEntry_left = ttk.Entry(dataFrame)
    fileNameEntry_left.grid(column=1, row=2, padx=5, sticky="NSEW")
    fileNameEntry_left.insert(0, outputFileName_left)

    ttk.Label(dataFrame, text="COM Port (Left):").grid(column=0, row=3, sticky="E")
    comPortEntry_left = ttk.Entry(dataFrame)
    comPortEntry_left.grid(column=1, row=3, padx=5, sticky="NSEW")
    comPortEntry_left.insert(0, DEFAULT_PORT_LEFT)

    calibrateButtonLeft = ttk.Button(dataFrame, text="Calibrate Left Glove",
                                     command=calibrate_left)
    calibrateButtonLeft.grid(column=2, row=2, rowspan=2, padx=5, sticky="NSEW")

    # --- Start / Stop ---
    startButton = ttk.Button(dataFrame, text="Start Acquisition",
                             command=start_data_acquire, state=tk.DISABLED)
    startButton.grid(column=0, row=4, columnspan=2, padx=5, pady=(8, 0), sticky="NEW")

    stopButton = ttk.Button(dataFrame, text="Stop Acquisition",
                            command=stop_data, state=tk.DISABLED)
    stopButton.grid(column=2, row=4, padx=5, pady=(8, 0), sticky="NEW")

    statusText = ttk.Label(dataFrame, text="")
    statusText.grid(column=0, row=5, columnspan=3)
    set_status("Gloves not calibrated")

    # --------------------------------------------------------
    # Right calibration frames
    # --------------------------------------------------------
    calibrationFrame1 = ttk.Frame(root)
    calibrationFrame1.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame1._target_reader = 'reader_right'
    calibrationFrame1._target_frame  = None   # set at runtime

    ttk.Label(calibrationFrame1,
              text="RIGHT GLOVE — Place your hand flat with fingers spread wide.\n"
                   "Wait a few seconds, then press Next.").grid(column=0, row=0, sticky="EW")
    ttk.Button(calibrationFrame1, text="Next",
               command=lambda: calibration1_generic(calibrationFrame1, calibrationFrame1._target_frame)
               ).grid(column=1, row=1, padx=5, sticky="NEW")

    calibrationFrame2R = ttk.Frame(root)
    calibrationFrame2R.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame2R._target_reader = 'reader_right'

    ttk.Label(calibrationFrame2R,
              text="RIGHT GLOVE — Bend your fingers into a fist.\n"
                   "Wait a few seconds, then press Next.").grid(column=0, row=0, sticky="EW")
    ttk.Button(calibrationFrame2R, text="Next",
               command=lambda: calibration2_generic(calibrationFrame2R)
               ).grid(column=1, row=1, padx=5, sticky="NEW")

    # --------------------------------------------------------
    # Left calibration frames
    # --------------------------------------------------------
    calibrationFrame1L = ttk.Frame(root)
    calibrationFrame1L.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame1L._target_reader = 'reader_left'
    calibrationFrame1L._target_frame  = None   # set at runtime

    ttk.Label(calibrationFrame1L,
              text="LEFT GLOVE — Place your hand flat with fingers spread wide.\n"
                   "Wait a few seconds, then press Next.").grid(column=0, row=0, sticky="EW")
    ttk.Button(calibrationFrame1L, text="Next",
               command=lambda: calibration1_generic(calibrationFrame1L, calibrationFrame1L._target_frame)
               ).grid(column=1, row=1, padx=5, sticky="NEW")

    calibrationFrame2L = ttk.Frame(root)
    calibrationFrame2L.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame2L._target_reader = 'reader_left'

    ttk.Label(calibrationFrame2L,
              text="LEFT GLOVE — Bend your fingers into a fist.\n"
                   "Wait a few seconds, then press Next.").grid(column=0, row=0, sticky="EW")
    ttk.Button(calibrationFrame2L, text="Next",
               command=lambda: calibration2_generic(calibrationFrame2L)
               ).grid(column=1, row=1, padx=5, sticky="NEW")

    # --------------------------------------------------------
    # Shared calibration-finished frame
    # --------------------------------------------------------
    calibrationFinishedFrame = ttk.Frame(root)
    calibrationFinishedFrame.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    ttk.Label(calibrationFinishedFrame, text="Calibration Finished!").grid(column=0, row=0, sticky="EW")
    ttk.Button(calibrationFinishedFrame, text="Finish",
               command=finishCalibration).grid(column=1, row=1, padx=5, sticky="NEW")

    # Link calibration frame 1 targets now that frame objects exist
    calibrationFrame1._target_frame  = calibrationFrame2R
    calibrationFrame1L._target_frame = calibrationFrame2L

    # --------------------------------------------------------
    # Show main frame
    # --------------------------------------------------------
    dataFrame.lift()
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
