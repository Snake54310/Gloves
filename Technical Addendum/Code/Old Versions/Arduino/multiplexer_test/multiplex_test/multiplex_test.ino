/**
* TCA9548 I2CScanner.ino -- I2C bus scanner for Arduino
*
* Based on https://playground.arduino.cc/Main/I2cScanner/
*
*/
#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#define PCAADDR 0x70
#define IMUADDR 0x69

Adafruit_ICM20948 icm;
//Adafruit_ICM20948 icm2;
//Adafruit_ICM20948 icm3;
uint16_t measurement_delay_us = 65535;

void pcaselect(uint8_t i) {
  if (i > 7) return;
  Wire.beginTransmission(PCAADDR);
  if (Wire.write(1 << i)) {
    //Serial.println("\nPCA select success!\n");
  }
  Wire.endTransmission();
}
// standard Arduino setup()
void setup()
{
  while (!Serial);
  delay(1000);

  Wire.begin();

  Serial.begin(115200);
  Serial.println("\nPCAScanner ready!");

  for (uint8_t t = 0; t < 7; t++) {
    pcaselect(t);
    Serial.print("PCA Port #"); Serial.println(t);
    delay(10);
    for (uint8_t addr = 0; addr<=127; addr++) {
      if (addr == PCAADDR) continue;
        Wire.beginTransmission(addr);
        if (!Wire.endTransmission()) {
          Serial.print("Found I2C 0x"); Serial.println(addr,HEX);
        }
      }
    /*if (!icm.begin_I2C()) {
      Serial.println("Failed to find ICM20948 chip");
    } else {
      Serial.println("GRAH");
    }*/
  }

  Serial.println("\nDone, starting in 3 seconds...");
  delay(3000);
}
void loop()
{
  sensors_event_t accel0;
  sensors_event_t gyro0;
  sensors_event_t mag0;
  sensors_event_t temp0;

  sensors_event_t accel1;
  sensors_event_t gyro1;
  sensors_event_t mag1;
  sensors_event_t temp1;

  sensors_event_t accel2;
  sensors_event_t gyro2;
  sensors_event_t mag2;
  sensors_event_t temp2;

  sensors_event_t accel3;
  sensors_event_t gyro3;
  sensors_event_t mag3;
  sensors_event_t temp3;

  sensors_event_t accel4;
  sensors_event_t gyro4;
  sensors_event_t mag4;
  sensors_event_t temp4;

  sensors_event_t accel5;
  sensors_event_t gyro5;
  sensors_event_t mag5;
  sensors_event_t temp5;

  sensors_event_t accel6;
  sensors_event_t gyro6;
  sensors_event_t mag6;
  sensors_event_t temp6;

  sensors_event_t accel7;
  sensors_event_t gyro7;
  sensors_event_t mag7;
  sensors_event_t temp7;

  pcaselect(0);
  if (!icm.begin_I2C()) {
    Serial.println("Failed to find ICM20948 chip on Port 0");
  } else {
    icm.getEvent(&accel0, &gyro0, &temp0, &mag0);
    Serial.print("\t\tTemperature of S0: ");
    Serial.print(temp0.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel0.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel0.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel0.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag0.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag0.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag0.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro0.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro0.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro0.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(1);
  if (!icm.begin_I2C()) {
    Serial.println("Failed to find ICM20948 chip on Port 1");
  } else {
    icm.getEvent(&accel1, &gyro1, &temp1, &mag1);
    Serial.print("\t\tTemperature of S1: ");
    Serial.print(temp1.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel1.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel1.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel1.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag1.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag1.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag1.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro1.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro1.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro1.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(2);
  if (!icm.begin_I2C()) {
    Serial.println("Failed to find ICM20948 chip on Port 2");
  } else {
    icm.getEvent(&accel2, &gyro2, &temp2, &mag2);
    Serial.print("\t\tTemperature of S2: ");
    Serial.print(temp2.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel2.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel2.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel2.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag2.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag2.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag2.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro2.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro2.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro2.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(3);
  if (!icm.begin_I2C()) {

    Serial.println("Failed to find ICM20948 chip on Port 3");
  } else {
    icm.getEvent(&accel3, &gyro3, &temp3, &mag3);
    Serial.print("\t\tTemperature of S3: ");
    Serial.print(temp3.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel3.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel3.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel3.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag3.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag3.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag3.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro3.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro3.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro3.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(4);
  if (!icm.begin_I2C()) {

    Serial.println("Failed to find ICM20948 chip on Port 4");
  } else {
    icm.getEvent(&accel4, &gyro4, &temp4, &mag4);
    Serial.print("\t\tTemperature of S4: ");
    Serial.print(temp4.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel4.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel4.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel4.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag4.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag4.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag4.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro4.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro4.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro4.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(5);
  if (!icm.begin_I2C()) {

    Serial.println("Failed to find ICM20948 chip on Port 5");
  } else {
    icm.getEvent(&accel5, &gyro5, &temp5, &mag5);
    Serial.print("\t\tTemperature of S5: ");
    Serial.print(temp5.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel5.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel5.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel5.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag5.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag5.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag5.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro5.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro5.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro5.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(6);
  if (!icm.begin_I2C()) {

    Serial.println("Failed to find ICM20948 chip on Port 6");
  } else {
    icm.getEvent(&accel6, &gyro6, &temp6, &mag6);
    Serial.print("\t\tTemperature of S6: ");
    Serial.print(temp6.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel6.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel6.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel6.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag6.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag6.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag6.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro6.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro6.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro6.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);

  pcaselect(7);
  if (!icm.begin_I2C()) {

    Serial.println("Failed to find ICM20948 chip on Port 7");
  } else {
    icm.getEvent(&accel7, &gyro7, &temp7, &mag7);
    Serial.print("\t\tTemperature of S7: ");
    Serial.print(temp7.temperature);
    Serial.println(" deg C");
    /* Display the results (acceleration is measured in m/s^2) */
    Serial.print("\t\tAccel X: ");
    Serial.print(accel7.acceleration.x);
    Serial.print(" \tY: ");
    Serial.print(accel7.acceleration.y);
    Serial.print(" \tZ: ");
    Serial.print(accel7.acceleration.z);
    Serial.println(" m/s^2 ");

    Serial.print("\t\tMag X: ");
    Serial.print(mag7.magnetic.x);
    Serial.print(" \tY: ");
    Serial.print(mag7.magnetic.y);
    Serial.print(" \tZ: ");
    Serial.print(mag7.magnetic.z);
    Serial.println(" uT");

    // Display the results (acceleration is measured in m/s^2) 
    Serial.print("\t\tGyro X: ");
    Serial.print(gyro7.gyro.x);
    Serial.print(" \tY: ");
    Serial.print(gyro7.gyro.y);
    Serial.print(" \tZ: ");
    Serial.print(gyro7.gyro.z);
    Serial.println(" radians/s ");
    Serial.println();
  }
  delay(1000);
}