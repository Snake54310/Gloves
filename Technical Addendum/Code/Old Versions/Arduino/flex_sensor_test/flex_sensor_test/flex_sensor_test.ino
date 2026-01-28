//Flex sensors are labeled left-right, and connected in numeric order to A0-4
int shortFSPin = A0;
int longFSPin1 = A1;
int longFSPin2 = A2;
int longFSPin3 = A3;
int longFSPin4 = A6;

int shortFSReading;
int longFSReading1;
int longFSReading2;
int longFSReading3;
int longFSReading4;

//Estimates for short and long flex sensors' readings at maximum and minimum flex. 
//This assumes 100K divider resistors for the short FS and 10k for the long FS
int shortFSMinReading = 440;
int shortFSMaxReading = 825;

int longFSMinReading = 90;
int longFSMaxReading = 500;

void setup() {
  Serial.begin(9600);

}

void loop() {
  shortFSReading = analogRead(shortFSPin);
  longFSReading1 = analogRead(longFSPin1);
  longFSReading2 = analogRead(longFSPin2);
  longFSReading3 = analogRead(longFSPin3);
  longFSReading4 = analogRead(longFSPin4);

  //Shift the readings down so that max flex roughly equates to a reading of zero.
  //Once we have the gloves built and the max/min values more tuned, we can use
  //remap() in order to map to a flex value from 0-100 (or whatever range we decide)
  shortFSReading -= shortFSMinReading;
  if (shortFSReading < 0){
    shortFSReading = 0;
  } 

  longFSReading1 -=  longFSMinReading;
  longFSReading2 -=  longFSMinReading;
  longFSReading3 -=  longFSMinReading;
  longFSReading4 -=  longFSMinReading;

  if (longFSReading1 < 0){
    longFSReading1 = 0;
  }
  if (longFSReading2 < 0){
    longFSReading2 = 0;
  }
  if (longFSReading3 < 0){
    longFSReading3 = 0;
  }
  if (longFSReading4 < 0){
    longFSReading4 = 0;
  }


  


//Print data in CSV format over serial
//  (thumb, pointer finger, middle finger, ring finger, pinky)
  Serial.print(shortFSReading);
  Serial.print(",");
  Serial.print(longFSReading1);
  Serial.print(",");
  Serial.print(longFSReading2);
  Serial.print(",");
  Serial.print(longFSReading3);
  Serial.print(",");
  Serial.print(longFSReading4);
  Serial.println();
  delay(1000);
}
