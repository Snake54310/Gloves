import serial
import csv
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
import sys
from PySideGraphicalDisplay import GloveMonitorWindow

#Serial port constants and variables
port = 'COM4'
baudRate = 2000000
dataLine = [0]
dataThread = None
reader = None
enable = 0
liveGUIWindow = None

# CSV file setup
outputFileName = "GloveData.csv"
csvFile = None
csvWriter = None

#start_data_acquire()
#Begin data collection. Disable start button, and start up data collection thread. If no serial, produce error code
def start_data_acquire():
    global enable, reader, csvWriter, csvFile, startTime, dataThread, outputFileName, port, liveGUIWindow
    set_status("Connecting...")
    outputFileName = fileNameEntry.get()
    port = comPortEntry.get()
    try:
        set_status("Connecting to glove...")
        if(reader == None):
            reader = serial.Serial(port, baudRate)
            time.sleep(3)
        startButton.configure(state=tk.DISABLED)
        stopButton.configure(state=tk.NORMAL)

        liveGUIWindow = liveDisplayOpen()  # Initiate Pyside Session

        dataThread = threading.Thread(target=data_acquire, args=(port, baudRate, outputFileName))
        dataThread.start()

    except serial.SerialException as e:
        tk.messagebox.showerror("Error", f"Error: Could not open serial port\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    except Exception as e:
        set_status(f"An unexpected error occurred: {e}")
        tk.messagebox.showerror("Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

#data_aquire(port, baudRate, outputFileName)
#port: COM port of gloves
#buadRate: communication baud rate
#outputFileName: CSV output file name

#Read data sent from gloves over serial, and output to desired file
def data_acquire(port, baudRate, outputFileName):
    global enable, reader, csvFile, csvWriter, startTime
    # Try to open serial port
    try:
        set_status("Connecting to glove...")
        if(reader == None):
            reader = serial.Serial(port, baudRate)
            time.sleep(3)
        #Begin data collection
        set_status("Reading data...")

        if reader:
            reader.write(b"ON")
        startTime = time.perf_counter()
        csvFile = open(outputFileName, 'w', newline='')
        csvWriter = csv.writer(csvFile, lineterminator='\n')

        # Write header row
        csvWriter.writerow(
            ["Timestamp",
             "Thumb Flex", "Pointer Flex", "Middle Flex", "Ring Flex", "Pinky Flex",
             "Thumb Acc. X", "Thumb Acc. Y", "Thumb Acc. Z", "Thumb Gyro X", "Thumb Gyro Y", "Thumb Gyro Z",
             "Pointer Acc. X", "Pointer Acc. Y", "Pointer Acc. Z", "Pointer Gyro X", "Pointer Gyro Y", "Pointer Gyro Z",
             "Middle Acc. X", "Middle Acc. Y", "Middle Acc. Z", "Middle Gyro X", "Middle Gyro Y", "Middle Gyro Z",
             "Ring Acc. X", "Ring Acc. Y", "Ring Acc. Z", "Ring Gyro X", "Ring Gyro Y", "Ring Gyro Z",
             "Pinky Acc. X","Pinky Acc. Y", "Pinky Acc. Z", "Pinky Gyro X", "Pinky Gyro Y", "Pinky Gyro Z",
             "Wrist Gyro X", "Wrist Gyro Y", "Wrist Gyro Z", "Wrist Acc. X", "Wrist Acc. Y", "Wrist Acc. Z",
             "Hand"])
        enable = True

        #While device enabled, read data from serial and write to file
        # Also, pipe data to PySide Window Manager
        while enable and reader.isOpen():
            # Read data from serial port
            data = reader.readline().decode('utf-8').strip()

            if data:
                timestamp = round(time.perf_counter() - startTime, 3)
                dataLine = (data.split(','))
                dataLine.insert(0, timestamp)
                csvWriter.writerow(dataLine)

                liveDisplayUpdate() # send data to liveDisplay for conversion to Interface Output

    except serial.SerialException as e:
        tk.messagebox.showerror("Error", f"Error: Could not open serial port\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    except Exception as e:
        set_status(f"An unexpected error occurred: {e}")
        tk.messagebox.showerror("Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

#stop_data()
#Stop collecting data from gloves
def stop_data():
    global enable, reader
    set_status("Stopping...")
    enable = False
    if reader:
        reader.write(b"OFF")
    stopButton.config(state=tk.DISABLED)
    startButton.config(state=tk.NORMAL)
    set_status("Data saved to " + outputFileName)

    liveDisplayClose(liveGUIWindow) # end PySide Session


#Close serial reader, csv file, and data thread
def free_resources():
    global  reader, csvFile, dataThread
    #Close serial reader
    if reader:
        try:
            reader.close()
            print("Serial port closed")
        except serial.SerialException as e:
            print(f"Error closing serial port: {e}")
    #Close csv file
    if csvFile:
        try:
            csvFile.close()
            print("Csv file closed")
        except Exception as e:
            print("Error closing CSV file: {e}")

    global liveGUIWindow
    liveGUIWindow = None

    #Join data thread with main thread
    if dataThread:
        try:
            if dataThread and dataThread.is_alive():
                dataThread.join(timeout=2)
            print("Data thread closed")
        except Exception as e:
            print(f"Error closing data thread: {e}")

#on_close()
#fires when x button is pressed. Close program
def on_close():
    #If collecting data still, warn user
    if enable:
        if messagebox.askokcancel("Warning", "Data acquisition is still running. Continue?"):
            enabled = False
            free_resources()
            root.destroy()
            sys.exit()
    #Otherwise, free resources and close
    else:
        free_resources()
        root.destroy()
        sys.exit()

#set_status()
#Set the status bar message in the UI
def set_status(status):
    global statusText
    root.after(0, statusText.config(text=status))
    root.after(0, statusText.update())

#Run flex sensor calibration
def calibrate_gloves():
    global reader, port
    port = comPortEntry.get()
    #If no serial reader/writer, open one
    try:
        if (reader == None):
            set_status("Connecting to glove...")
            reader = serial.Serial(port, baudRate)
            time.sleep(1)
    except serial.SerialException as e:
        tk.messagebox.showerror("Error", f"Error: Could not open serial port\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    except Exception as e:
        set_status(f"An unexpected error occurred: {e}")
        tk.messagebox.showerror("Error", f"Unexpected Error\n{e}")
        stopButton.config(state=tk.DISABLED)
        startButton.config(state=tk.NORMAL)
        exit()

    #Lift first calibration frame, with button to continue
    calibrationFrame1.lift()

#calibration1()
#Calibrate glove's minimum flex value
def calibration1():
    global reader
    if(reader):
        reader.write(b"CAL1")
    #Lift second calibration frame, with button to continue
    calibrationFrame2.lift()

#calibration2()
#calibrate glove's maximum flex value
def calibration2():
    global reader
    reader.write(b"CAL2")
    calibrationFinishedFrame.lift()

#finishCalibration()
#Return to main menu
def finishCalibration():
    dataFrame.lift()
    startButton.configure(state=tk.NORMAL)
    set_status("Ready to collect data")

def liveDisplayOpen():
    newWindow = GloveMonitorWindow()
    newWindow.initDisplay()
    return newWindow

def liveDisplayUpdate():
    pass

def liveDisplayClose(OldWindow):
    if OldWindow is not None:
        OldWindow.terminateDisplay()
    return

if __name__ == "__main__":
    # root
    root = tk.Tk()
    root.title("Glove Data Reader")

    # Data Frame (controls for data collection) ------------------------------------------------------------------------
    dataFrame = ttk.Frame(root)
    dataFrame.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    dataFrame.grid_columnconfigure(0, weight=1, pad=10)
    dataFrame.grid_columnconfigure(1, weight=1, pad=10)

    fileNameLabel = ttk.Label(dataFrame, text="Output File:")
    fileNameLabel.grid(column=0, row=0)
    fileNameEntry = ttk.Entry(dataFrame)
    fileNameEntry.grid(column=1, row=0, padx=5, sticky="NSEW")
    fileNameEntry.insert(0, outputFileName)

    comPortLabel = ttk.Label(dataFrame, text="COM Port:")
    comPortLabel.grid(column=0, row=1)
    comPortEntry = ttk.Entry(dataFrame)
    comPortEntry.grid(column=1, row=1, padx=5, sticky="NSEW")
    comPortEntry.insert(0, port)

    startButton = ttk.Button(dataFrame, text="Start Acquisition", command=start_data_acquire)
    startButton.configure(state=tk.DISABLED)
    startButton.grid(column=0, row=2, padx=5, sticky="NEW")

    stopButton = ttk.Button(dataFrame, text="Stop Acquisition", command=stop_data)
    stopButton.configure(state=tk.DISABLED)
    stopButton.grid(column=1, row=2, padx=5, sticky="NEW")

    calibrateButton = ttk.Button(dataFrame, text="Calibrate Glove", command=calibrate_gloves)
    calibrateButton.grid(column=0, row=3, columnspan=2, sticky="ew")

    statusText = ttk.Label(dataFrame, text="")
    statusText.grid(column=0, row=4, columnspan=2)
    set_status("Gloves not calibrated")
    # ------------------------------------------------------------------------------------------------------------------

    # Calibration Frame1 (first step of calibration, raised when "calibrate gloves" is clicked) ------------------------
    calibrationFrame1 = ttk.Frame(root)
    calibrationFrame1.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame1.grid_columnconfigure(0, weight=1)

    calibrationLabel1 = ttk.Label(calibrationFrame1,
                                  text="Place your hand on a flat surface with fingers spread, then press next")
    calibrationLabel1.grid(column=0, row=0, sticky="EW")

    nextButtonCal1 = ttk.Button(calibrationFrame1, text="Next", command=calibration1)
    nextButtonCal1.grid(column=1, row=1, padx=5, sticky="NEW")

    # Calibration Frame2 (second step of calibration, raised after calibration1 complete -------------------------------
    calibrationFrame2 = ttk.Frame(root)
    calibrationFrame2.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFrame2.grid_columnconfigure(0, weight=1)

    calibrationLabel2 = ttk.Label(calibrationFrame2, text="Now, make a fist with your thumb tucked, then press next")
    calibrationLabel2.grid(column=0, row=0, sticky="EW")

    nextButtonCal2 = ttk.Button(calibrationFrame2, text="Next", command=calibration2)
    nextButtonCal2.grid(column=1, row=1, padx=5, sticky="NEW")
    #-------------------------------------------------------------------------------------------------------------------

    # Finished Calibration Frame (shows "Calibration Finished!" message, raised after calibration2 completes -----------
    calibrationFinishedFrame = ttk.Frame(root)
    calibrationFinishedFrame.grid(column=0, row=0, padx=10, pady=10, sticky="NSEW")
    calibrationFinishedFrame.grid_columnconfigure(0, weight=1)

    calibrationLabel2 = ttk.Label(calibrationFinishedFrame, text="Calibration Finished!")
    calibrationLabel2.grid(column=0, row=0, sticky="EW")

    nextButtonFinal = ttk.Button(calibrationFinishedFrame, text="Finish", command=finishCalibration)
    nextButtonFinal.grid(column=1, row=1, padx=5, sticky="NEW")

    #-------------------------------------------------------------------------------------------------------------------

    #Lift main UI
    dataFrame.lift()
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    #Run UI, configure on_close to run on UI close
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

