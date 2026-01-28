# Flex Sensor Test Code
## Usage
Ideally, the code here can be added to the appropriate places in the loop/setup code of our final
integated code, with the removal of the 'sleep(1000)' command

## Data Input
> [!CAUTION]
> The Arduino we are using cannot accept over 3.3V ADC input. For now, ONLY connect the flex 
> sensor input to the 3v3 pin. (Connecting to 5v proooobably won't break the Arduino, but worst
case could blow up an ADC)

All flex sensors are connected in a resistor divider format. IE : 3v3 -> flex sensor -> resistor -> ground. ADC probes are connected between the flex sensor and resistor.
As of now, the system is using a 100k resistor on the short FS, and 10k resistors on the long FS's

| pin | connection |
|----|------|
| A0 | thumb FS |
| A1 | pointer finger FS |
| A2 | middle finger FS |
| A3 | ring finger FS |
| A6 | pinky FS |

## Data output

Under the current setup, I stored the minimum value the sensors reached when fully flexed, and try to adjust that to be our zero.
Eventually, we can remap the range of the sensor values to something more useful (like 0 to 255). However, this will take
more testing/calibration to adjust.

Data is output in CSV in the format (thumb flex, pointer finger flex, middle finger flex, ring finger flex, index finger flex, pinky flex)
