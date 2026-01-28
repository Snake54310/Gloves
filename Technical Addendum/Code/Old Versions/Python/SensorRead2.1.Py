import serial
import csv
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
import sys

portL = 'COM4'
portR = 'COM5'
baudRate = 9600
dataLine = [0]
samplePeriod = 0.01
dataThread = None
readerL = None
readerR = None
enable = 0

# CSV file setup
outputFileNameL = "GloveData_L.csv"
csvFileL = None
csvWriterL = None

outputFileNameR = "GloveData_R.csv"
csvFileR = None
csvWriterR = None


def start_data_aquire():
    global enable, readerL, csvWriterL, csvFileL, readerR, csvWriterR, csvFileR, startTime, dataThread
    if not enable:
        outputFileNameL = fileNameEntryL.get()
        portL = comPortEntryL.get()

        outputFileNameR = fileNameEntryR.get()
        portR = comPortEntryR.get()

    set_status("Connecting...")
    stopButton.config(state=tk.NORMAL)
    startButton.config(state=tk.DISABLED)
    dataThread = threading.Thread(target=data_aquire, args=(portL, portR, baudRate, outputFileNameL, outputFileNameR))
    dataThread.start()


def data_aquire(portL, portR, baudRate, outputFileNameL, outputFileNameR):
    global enable, readerL, csvFileL, csvWriterL, readerR, csvFileR, csvWriterR, startTime
    # Try to open serial port
    try:
        if(readerL == None):
            readerL = serial.Serial(portL, baudRate)
        print(f"Connected to {portL} at {baudRate} baud")
        if(readerR == None):
            readerR = serial.Serial(portR, baudRate)
        print(f"Connected to {portR} at {baudRate} baud")
        set_status("Reading data...")
        if(readerL):
            readerL.write(b"ON")
        if (readerR):
            readerL.write(b"ON")
        startTime = time.perf_counter()
        csvFileR = open(outputFileNameR, 'w', newline='')
        csvWriterR = csv.writer(csvFileR, lineterminator='\n')
        csvFileL = open(outputFileNameL, 'w', newline='')
        csvWriterL = csv.writer(csvFileL, lineterminator='\n')
        # Write header row
        csvWriterL.writerow(
            ["Timestamp", "Thumb Flex", "Pointer Flex", "Middle Flex", "Ring Flex", "Pinky Flex", "Thumb Acc. X",
             "Thumb Acc. Y", "Thumb Acc. Z", "Pointer Acc. X", "Pointer Acc. Y", "Pointer Acc. Z", "Middle Acc. X",
             "Middle Acc. Y", "Middle Acc. Z", "Ring Acc. X", "Ring Acc. Y", "Ring Acc. Z", "Pinky Acc. X",
             "Pinky Acc. Y", "Pinky Acc. Z", "Thumb Gyro X", "Thumb Gyro Y", "Thumb Gyro Z", "Pointer Gyro X",
             "Pointer Gyro Y", "Pointer Gyro Z", "Middle Gyro X", "Middle Gyro Y", "Middle Gyro Z", "Ring Gyro X",
             "Ring Gyro Y", "Ring Gyro Z", "Pinky Gyro X", "Pinky Gyro Y", "Pinky Gyro Z", "Wrist Gyro X", "Wrist Gyro Y",
             "Wrist Gyro Z", "Wrist Acc. X", "Wrist Acc. Y", "Wrist Acc. Z" "Hand"])
        csvWriterR.writerow(
            ["Timestamp", "Thumb Flex", "Pointer Flex", "Middle Flex", "Ring Flex", "Pinky Flex", "Thumb Acc. X",
             "Thumb Acc. Y", "Thumb Acc. Z", "Pointer Acc. X", "Pointer Acc. Y", "Pointer Acc. Z", "Middle Acc. X",
             "Middle Acc. Y", "Middle Acc. Z", "Ring Acc. X", "Ring Acc. Y", "Ring Acc. Z", "Pinky Acc. X",
             "Pinky Acc. Y", "Pinky Acc. Z", "Thumb Gyro X", "Thumb Gyro Y", "Thumb Gyro Z", "Pointer Gyro X",
             "Pointer Gyro Y", "Pointer Gyro Z", "Middle Gyro X", "Middle Gyro Y", "Middle Gyro Z", "Ring Gyro X",
             "Ring Gyro Y", "Ring Gyro Z", "Pinky Gyro X", "Pinky Gyro Y", "Pinky Gyro Z", "Wrist Gyro X", "Wrist Gyro Y",
             "Wrist Gyro Z", "Wrist Acc. X", "Wrist Acc. Y", "Wrist Acc. Z" "Hand"])
        enable = True
        # Send a char to enable data collection, wait, then do the next code
        while enable and readerL.isOpen() and readerR.isOpen():
            # Read data from serial port
            dataL = readerL.readline().decode('utf-8').strip()

            if dataL:
                timestamp = round(time.perf_counter() - startTime, 3)
                dataLine = (dataL.split(','))
                dataLine.insert(0, timestamp)
                csvWriterL.writerow(dataLine)

            dataR = readerR.readline().decode('utf-8').strip()

            if dataR:
                timestamp = round(time.perf_counter() - startTime, 3)
                dataLine = (dataR.split(','))
                dataLine.insert(0, timestamp)
                csvWriterR.writerow(dataLine)

    except serial.SerialException as e:
        print(f"Error: Could not open serial port: {e}")
        tk.messagebox.showerror(f"Error", f"Error: Could not open serial port\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    except Exception as e:
        set_status(f"An unexpected error occurred: {e}")
        tk.messagebox.showerror(f"Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()
    finally:
        free_resources()
        if (enable):
            set_status(f"Data saved to {outputFileNameL}, {outputFileNameR}")
        else:
            stopButton.configure(state=tk.DISABLED)
            set_status("Ready to collect data")


def stop_data():
    global enable, readerL, readerR
    enable = False
    if (readerL):
        readerL.write(b"OFF")
    if (readerR):
        readerR.write(b"OFF")
    stopButton.config(state=tk.DISABLED)
    startButton.config(state=tk.NORMAL)
    set_status("Stopping...")


def free_resources():
    global  readerL, csvFileL, readerR, csvFileR, dataThread
    if readerL:
        try:
            if(readerL != None):
                readerL.close()
            print("Serial port closed")
        except serial.SerialException as e:
            print(f"Error closing serial port: {e}")
    if csvFileL:
        try:
            csvFileL.close()
            print("Csv file closed")
        except Exception as e:
            print("Error closing CSV file: {e}")
    if readerR:
        try:
            if(readerR != None):
                readerR.close()
            print("Serial port closed")
        except serial.SerialException as e:
            print(f"Error closing serial port: {e}")
    if csvFileR:
        try:
            csvFileR.close()
            print("Csv file closed")
        except Exception as e:
            print(f"Error closing CSV file: {e}")
    if dataThread:
        try:
            if dataThread and dataThread.is_alive():
                dataThread.join(timeout=2)
            print("Data thread closed")
        except Exception as e:
            print(f"Error closing data thread: {e}")


def on_close():
    if enable:
        if messagebox.askokcancel("Warning", "Data aquisition is still running. Continue?"):
            enabled = False
            free_resources()
            root.destroy()
            sys.exit()
    else:
        free_resources()
        root.destroy()
        sys.exit()




def set_status(status):
    root.after(0, statusText.config(text=status))


def calibrate_gloves():
    global readerL, readerR
    Lconnected = False;
    Rconnected = False;
    try:
        if(readerL == None):
            readerL = serial.Serial(portL, baudRate)
        print(f"Connected to {portL} at {baudRate} baud")
        Lconnected = True;
    except serial.SerialException as e:
        print(f"Left glove not found, trying right glove")

    except Exception as e:
        set_status(f"An unexpected error occurred: {e}")
        tk.messagebox.showerror(f"Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    try:
        if (readerR == None):
            readerR = serial.Serial(portR, baudRate)
        print(f"Connected to {portR} at {baudRate} baud")
        Rconnected = True;
    except serial.SerialException as e:
        print(f"Right glove not found")

    except Exception as e:
        set_status(f"An unexpected error occurred: {e}")
        tk.messagebox.showerror(f"Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    if(Lconnected and Rconnected):
        tk.messagebox.showerror("Error", "Both gloves detected. Please calibrate gloves one at a time, unplugging glove not being calibrated")
    calibrationFrame1.lift()


def calibration1():
    global readerL, readerR
    if (readerL):
        readerL.write(b"CAL1")
    if (readerR):
        readerR.write(b"CAL1")
    calibrationFrame2.lift()


def calibration2():
    global readerL, readerR
    if (readerL):
        readerL.write(b"CAL2")
    if (readerR):
        readerL.write(b"CAL2")
    calibrationFinishedFrame.lift()


def finishCalibration():
    dataFrame.lift()


if __name__ == "__main__":
    # root
    root = tk.Tk()
    root.title("Glove Data Reader")

    # Data Frame-------------------------------------------------------
    dataFrame = ttk.Frame(root)
    dataFrame.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    dataFrame.grid_columnconfigure(0, weight=1, pad=10)
    dataFrame.grid_columnconfigure(1, weight=1, pad=10)

    fileNameLabelL = ttk.Label(dataFrame, text="Output File (Left Hand):")
    fileNameLabelL.grid(column=0, row=0)
    fileNameEntryL = ttk.Entry(dataFrame)
    fileNameEntryL.grid(column=1, row=0, padx=5, sticky="NSEW")
    fileNameEntryL.insert(0, outputFileNameL)

    comPortLabelL = ttk.Label(dataFrame, text="COM Port (Left Hand):")
    comPortLabelL.grid(column=0, row=1)
    comPortEntryL = ttk.Entry(dataFrame)
    comPortEntryL.grid(column=1, row=1, padx=5, sticky="NSEW")
    comPortEntryL.insert(0, portL)

    fileNameLabelR = ttk.Label(dataFrame, text="Output File (Right Hand):")
    fileNameLabelR.grid(column=0, row=2)
    fileNameEntryR = ttk.Entry(dataFrame)
    fileNameEntryR.grid(column=1, row=2, padx=5, sticky="NSEW")
    fileNameEntryR.insert(0, outputFileNameR)

    comPortLabelR = ttk.Label(dataFrame, text="COM Port (Right Hand):")
    comPortLabelR.grid(column=0, row=3)
    comPortEntryR = ttk.Entry(dataFrame)
    comPortEntryR.grid(column=1, row=3, padx=5, sticky="NSEW")
    comPortEntryR.insert(0, portR)

    startButton = ttk.Button(dataFrame, text="Start Aquisition", command=start_data_aquire)
    startButton.grid(column=0, row=4, padx=5, sticky="NEW")

    stopButton = ttk.Button(dataFrame, text="Stop Aquisition", command=stop_data)
    stopButton.configure(state=tk.DISABLED)
    stopButton.grid(column=1, row=4, padx=5, sticky="NEW")

    calibrateButton = ttk.Button(dataFrame, text="Calibrate Gloves", command=calibrate_gloves)
    calibrateButton.grid(column=0, row=5, columnspan=2, sticky="ew")

    statusText = ttk.Label(dataFrame, text="")
    statusText.grid(column=0, row=6, columnspan=2)
    set_status("Ready to collect data")
    # -----------------------------------------------------------------------------

    # Calibration Frame1--------------------------------------------------------------
    calibrationFrame1 = ttk.Frame(root)
    calibrationFrame1.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame1.grid_columnconfigure(0, weight=1)

    calibrationLabel1 = ttk.Label(calibrationFrame1,
                                  text="Place your hand on a flat surface with fingers spread, then press next")
    calibrationLabel1.grid(column=0, row=0, sticky="EW")

    nextButton = ttk.Button(calibrationFrame1, text="Next", command=calibration1)
    nextButton.grid(column=1, row=1, padx=5, sticky="NEW")

    # Calibration Frame2-------------------------------------------------------------
    calibrationFrame2 = ttk.Frame(root)
    calibrationFrame2.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame2.grid_columnconfigure(0, weight=1)

    calibrationLabel2 = ttk.Label(calibrationFrame2, text="Now, make a fist with your thumb tucked, then press next")
    calibrationLabel2.grid(column=0, row=0, sticky="EW")

    nextButton = ttk.Button(calibrationFrame2, text="Next", command=calibration2)
    nextButton.grid(column=1, row=1, padx=5, sticky="NEW")

    # Finished Calibration Frame-------------------------------------------------------------
    calibrationFinishedFrame = ttk.Frame(root)
    calibrationFinishedFrame.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFinishedFrame.grid_columnconfigure(0, weight=1)

    calibrationLabel2 = ttk.Label(calibrationFinishedFrame, text="Calibration Finished!")
    calibrationLabel2.grid(column=0, row=0, sticky="EW")

    nextButton = ttk.Button(calibrationFinishedFrame, text="Finish", command=finishCalibration)
    nextButton.grid(column=1, row=1, padx=5, sticky="NEW")

    dataFrame.lift()
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

