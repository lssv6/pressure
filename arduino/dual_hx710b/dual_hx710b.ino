#include "HX710B.h"

const int DOUT_Pin = 2;   // Sensor data pin
const int SCLK_Pin = 3;   // Sensor clock pin

const int DOUT_Pin2 = 4;   // Sensor data pin
const int SCLK_Pin2 = 5;   // Sensor clock pin

#define READ_TIMES 5
float RES = 2.98023e-7;
//HX710B centro;
HX710B pressure_sensor1;
HX710B pressure_sensor2;

void setup() {
  Serial.begin(9600);
  pressure_sensor1.begin(DOUT_Pin, SCLK_Pin, 128);
  pressure_sensor2.begin(DOUT_Pin2, SCLK_Pin2, 128);
}

void loop() {
  while(!pressure_sensor1.is_ready() && pressure_sensor2.is_ready()){delay(10);}
  
  // --- Fallback (no calibration): preserve your current behavior ---
  // If your project defines RES/READ_TIMES/SCALE meaningfully, keep it.
  // Otherwise, consider replacing this with a datasheet-based linear estimate.
  long base1 = pressure_sensor1.read_average(READ_TIMES) - pressure_sensor1.get_offset();
  long base2 = pressure_sensor2.read_average(READ_TIMES) - pressure_sensor2.get_offset();
  float Ppas1 = (base1 * RES) * 20.0f - 50.0f;  // your original logic
  float Ppas2 = (base2 * RES) * 20.0f - 50.0f;  // your original logic
  
  Serial.print(Ppas1);  // Calibrated reading
  Serial.print(",");
  Serial.print(Ppas2);  // Calibrated reading
  Serial.print("\n");
}
