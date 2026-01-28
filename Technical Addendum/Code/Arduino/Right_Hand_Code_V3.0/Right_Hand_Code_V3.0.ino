#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <Arduino_BMI270_BMM150.h>
#include <elapsedMillis.h>

//Timer for data collection
//elapsedMilis was used so that USB output can buffer even while sensors are running
elapsedMillis elapsedTime;

//Sample 10 times/sec
int samplePeriod = 100;

//Device State Controls
enum : byte {idle,cal1,cal2,collecting} state;
bool enable;
bool calibration1Done;
bool calibration2Done;

//Constants for IMU multiplexer
#define PCAADDR 0x70
#define IMUADDR 0x69
Adafruit_ICM20948 icm;
sensors_event_t accel0,gyro0,temp0;
sensors_event_t accel1,gyro1,temp1;
sensors_event_t accel2,gyro2,temp2;
sensors_event_t accel3,gyro3,temp3;
sensors_event_t accel7,gyro7,temp7;

//Variables for IMU multiplexer
bool IMU_found = false;
//Edit if IMUs are connected to differnt ports on the multiplexer
int PCA_ports_connected [] = {7,3,2,1,0};

//variables to store IMU data
String finger0Data, finger1Data, finger2Data, finger3Data, finger4Data;
String palmOutAcc, palmOutGyro;
float palmAccX, palmAccY, palmAccZ;
float palmGyroX, palmGyroY, palmGyroZ;

//Flex sensors are labeled left-right, and connected in numeric order on ports A0-4, and A6
int shortFSPin = A0;
int longFSPin1 = A2;
int longFSPin2 = A1;
int longFSPin3 = A3;
int longFSPin4 = A6;

//Variables to store Flex sensor's readings
int shortFSReading;
int longFSReading1;
int longFSReading2;
int longFSReading3;
int longFSReading4;

int shortFSReading_adj;
int longFSReading1_adj;
int longFSReading2_adj;
int longFSReading3_adj;
int longFSReading4_adj;

//Variable to store flex sensor CSV entries
String fsOut;

//Variable to store L/R hand
String handType;

//Estimates for short and long flex sensors' readings at maximum and minimum flex. 
//This assumes 100K divider resistors for the short FS and 10k for the long FS
//These values will be adjusted when calibration is run
int shortFSMinReading = 440;
int shortFSMaxReading = 825;
int longFSMinReading1 = 90;
int longFSMaxReading1 = 500;
int longFSMinReading2 = 90;
int longFSMaxReading2 = 500;
int longFSMinReading3 = 90;
int longFSMaxReading3 = 500;
int longFSMinReading4 = 90;
int longFSMaxReading4 = 500;

void setup() {

  //Wait for serial and IMUs to boot
  while (!Serial);
    delay(1000);
  Wire.begin();
  Serial.begin(2000000);
  if (!IMU.begin()) {
    Serial.println("Failed to initialize on-board IMU!");
    while (1);
  }

  //Scan for IMU locations, disable magnetometers
  for (uint8_t t = 0; t < 5; t++) {
    pcaselect(PCA_ports_connected[t]);
    delay(10);
    for (uint8_t addr = 0; addr<=127; addr++) {
      if (addr == PCAADDR) continue;
        Wire.beginTransmission(addr);
        if (!Wire.endTransmission()) {
        }
      }
      if (!icm.begin_I2C()) {
        Serial.print("couldn't find/not connected");
      } else {
        icm.setAccelRange(ICM20948_ACCEL_RANGE_16_G);
        icm.setGyroRange(ICM20948_GYRO_RANGE_2000_DPS);
        icm.setMagDataRate(AK09916_MAG_DATARATE_SHUTDOWN);
        icm.setAccelRateDivisor(0);
        icm.setGyroRateDivisor(0);
      }
  }

  //Set device to default state
  enable = false;
  calibration1Done = false;
  calibration2Done = false;
  pcaselect(0);
  handType = "R";
  delay(1000);
}



void loop() {
  //If new input from Python, switch state
  if (Serial.available() > 0){
    String s = Serial.readStringUntil('\n');
    s.trim();
    if (s.equals("ON")) {
      state = collecting;
    } else if (s.equals("OFF")){
      state = idle;
    } else if (s.equals("CAL1")) {
      state = cal1;
    } else if (s.equals("CAL2")) {
      state = cal2;
    } else {
      state = idle;
    }
  }

  //If no user input, run current state
  switch(state){
    //Collecting: Read data from sensors, write over terminal
    case collecting:
      sensorCalls();
      break;

    //Cal1: calibration 1. See calibration1() function below
    case cal1:
      if(!calibration1Done){
        calibration1();
      }
      calibration1Done = true;
      break;

    //Cal2: calibration 2. See calibration2() function below
    case cal2:
      if(!calibration2Done){
        calibration2();
      }
      calibration2Done = true;
      break;

    //Idle: Reset calibration finished flags, do not collect data
    case idle:
      calibration1Done = false;
      calibration2Done = false;
      break;

    default:
      Serial.println("ERROR: Invalid State");
      break;
  }

}

//Select specific IMU from I2C multiplexer
void pcaselect(uint8_t i) {
  if (i > 7) return;
  Wire.beginTransmission(PCAADDR);
  if (Wire.write(1 << i)) {
    //Serial.println("\nPCA select success!\n");
  }
  Wire.endTransmission();
}

// Calibration 1: Set minimum levels for flex sensors
//    User must have hand flat on table for proper calibration
void calibration1() {
  delay(10);

  shortFSMaxReading = analogRead(shortFSPin);
  longFSMaxReading1 = analogRead(longFSPin1);
  longFSMaxReading2 = analogRead(longFSPin2);
  longFSMaxReading3 = analogRead(longFSPin3);
  longFSMaxReading4 = analogRead(longFSPin4);

  return;
}

//Calibration 2: Set maximum levels for flex sensors
//    User must have hand in a fist with thumb tucked for proper calibration
void calibration2() {
  delay(10);

  shortFSMinReading = analogRead(shortFSPin);
  longFSMinReading1 = analogRead(longFSPin1);
  longFSMinReading2 = analogRead(longFSPin2);
  longFSMinReading3 = analogRead(longFSPin3);
  longFSMinReading4 = analogRead(longFSPin4);

  return;
}

//sensorCalls: Read all sensors, print results over serial to be read by Python script
void sensorCalls() {
  if (elapsedTime > samplePeriod){
    // Read flex sensors
    shortFSReading = analogRead(shortFSPin);
    longFSReading1 = analogRead(longFSPin1);
    longFSReading2 = analogRead(longFSPin2);
    longFSReading3 = analogRead(longFSPin3);
    longFSReading4 = analogRead(longFSPin4);

    //Map values from 0 to 255 flex
    shortFSReading_adj = map(shortFSReading,shortFSMinReading,shortFSMaxReading,0,255);
    longFSReading1_adj = map(longFSReading1,longFSMinReading1,longFSMaxReading1,0,255);
    longFSReading2_adj = map(longFSReading2,longFSMinReading2,longFSMaxReading2,0,255);
    longFSReading3_adj = map(longFSReading3,longFSMinReading3,longFSMaxReading3,0,255);
    longFSReading4_adj = map(longFSReading4,longFSMinReading4,longFSMaxReading4,0,255);
    
    //Constrain to 1 byte
    shortFSReading_adj = constrain(shortFSReading_adj,0,255);
    longFSReading1_adj = constrain(longFSReading1_adj,0,255);
    longFSReading2_adj = constrain(longFSReading2_adj,0,255);
    longFSReading3_adj = constrain(longFSReading3_adj,0,255);
    longFSReading4_adj = constrain(longFSReading4_adj,0,255);

    //Format output to be sent out
    fsOut = String(shortFSReading_adj) + "," + String(longFSReading1_adj) + "," + String(longFSReading2_adj) + "," + String(longFSReading3_adj) + "," + String(longFSReading4_adj) + ",";

    //Select each IMU, read acceleration and gyro. In case of errors, output "E,E,E,E,E,E"
    //Thumb
    pcaselect(7);

    icm.getEvent(&accel7, &gyro7, &temp7);
    finger0Data =String(accel7.acceleration.x) + "," + String(accel7.acceleration.y) + "," + String(accel7.acceleration.z) + "," + String(gyro0.gyro.x) + "," + String(gyro0.gyro.y) + "," + String(gyro0.gyro.z) + ",";

    //Pointer
    pcaselect(3);
    icm.getEvent(&accel3, &gyro3, &temp3);
    finger1Data = String(accel3.acceleration.x) + "," + String(accel3.acceleration.y) + "," + String(accel3.acceleration.z) + "," + String(gyro3.gyro.x) + "," + String(gyro3.gyro.y) + "," + String(gyro3.gyro.z) + ",";

    //Middle
    pcaselect(2);
    icm.getEvent(&accel2, &gyro2, &temp2);
    finger2Data = String(accel2.acceleration.x) + "," + String(accel2.acceleration.y) + "," + String(accel2.acceleration.z) + "," + String(gyro2.gyro.x) + "," + String(gyro2.gyro.y) + "," + String(gyro2.gyro.z) + ",";

    //Ring
    pcaselect(1);
    icm.getEvent(&accel1, &gyro1, &temp1);
    finger3Data = String(accel1.acceleration.x) + "," + String(accel1.acceleration.y) + "," + String(accel1.acceleration.z) + "," + String(gyro1.gyro.x) + "," + String(gyro1.gyro.y) + "," + String(gyro1.gyro.z) + ",";

    //Pinky
    pcaselect(0);
    icm.getEvent(&accel0, &gyro0, &temp0);
    finger4Data = String(accel0.acceleration.x) + "," + String(accel0.acceleration.y) + "," + String(accel0.acceleration.z) + "," + String(gyro0.gyro.x) + "," + String(gyro0.gyro.y) + "," + String(gyro0.gyro.z) + ",";

    //Read wrist-mounted IMU
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(palmAccX, palmAccY, palmAccZ);
      palmOutAcc = String(palmAccX) + "," + String(palmAccY) + "," + String(palmAccZ) + ",";
    } else {
      Serial.print("E,E,E,"); 
    }
    if (IMU.gyroscopeAvailable()) {
      IMU.readGyroscope(palmGyroX, palmGyroY, palmGyroZ);
      palmOutGyro = String(palmGyroX) + "," + String(palmGyroY) + "," + String(palmGyroZ) + ",";
    } else {
      Serial.print("E,E,E,");
    }
    
    


    //Print data in CSV format over serial in the following format
    //  flex (each finger), acceleration XYZ, gyro XYZ (each finger), acceleration XYZ, gyro XYZ (wrist), hand type (L/R)
    Serial.println(fsOut + finger0Data + finger1Data + finger2Data + finger3Data + finger4Data + palmOutAcc + palmOutGyro + handType);
  }
}