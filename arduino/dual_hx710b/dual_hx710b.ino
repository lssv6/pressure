/*
 * Dual HX710B pressure sensor bridge.
 *
 * Streams one line per acquisition to the serial port:
 *
 *     <raw sensor 1>,<raw sensor 2>
 *
 * The values are the signed 24-bit differential readings of the HX710B, which
 * the desktop application converts to a pressure using its own calibration.
 * Lines starting with '#' are diagnostics and are ignored by the application.
 *
 * Wiring (any digital pins will do, change the tables below):
 *
 *     Sensor 1: OUT -> D2, SCK -> D3
 *     Sensor 2: OUT -> D4, SCK -> D5
 *     Both:     VCC -> 5V, GND -> GND
 */

const uint8_t SENSOR_COUNT = 2;
const uint8_t DATA_PINS[SENSOR_COUNT] = {2, 4};
const uint8_t CLOCK_PINS[SENSOR_COUNT] = {3, 5};

const unsigned long SERIAL_BAUD = 115200;

/*
 * Pulses after the 24 data bits select the next conversion:
 * 25 = 10 samples/s, 26 = 40 samples/s, 27 = temperature.
 */
const uint8_t MODE_PULSES = 26;

/* A sensor that never reports ready is reported instead of stalling the loop. */
const unsigned long READY_TIMEOUT_MS = 500;

void setup() {
  Serial.begin(SERIAL_BAUD);
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    pinMode(DATA_PINS[i], INPUT);
    pinMode(CLOCK_PINS[i], OUTPUT);
    digitalWrite(CLOCK_PINS[i], LOW);
  }
  Serial.println(F("# dual HX710B ready"));
}

/* The HX710B pulls OUT low once a conversion is available. */
bool isReady(uint8_t index) {
  return digitalRead(DATA_PINS[index]) == LOW;
}

bool waitUntilReady(uint8_t index) {
  unsigned long start = millis();
  while (!isReady(index)) {
    if (millis() - start > READY_TIMEOUT_MS) {
      return false;
    }
  }
  return true;
}

/* Keeping SCK high for more than ~60 us powers the chip down, so pulses stay short. */
bool clockPulse(uint8_t index) {
  digitalWrite(CLOCK_PINS[index], HIGH);
  delayMicroseconds(1);
  bool bitValue = digitalRead(DATA_PINS[index]) == HIGH;
  digitalWrite(CLOCK_PINS[index], LOW);
  delayMicroseconds(1);
  return bitValue;
}

int32_t readSensor(uint8_t index) {
  uint32_t value = 0;
  for (uint8_t bit = 0; bit < 24; bit++) {
    value = (value << 1) | (clockPulse(index) ? 1UL : 0UL);
  }
  for (uint8_t extra = 24; extra < MODE_PULSES; extra++) {
    clockPulse(index);
  }
  if (value & 0x800000UL) {
    value |= 0xFF000000UL;  /* sign extend the 24-bit two's complement value */
  }
  return (int32_t)value;
}

void loop() {
  int32_t readings[SENSOR_COUNT];

  /* Both channels are read back to back so a printed pair is one moment in time. */
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    if (!waitUntilReady(i)) {
      Serial.print(F("# sensor "));
      Serial.print(i + 1);
      Serial.println(F(" not responding"));
      return;
    }
    readings[i] = readSensor(i);
  }

  Serial.print(readings[0]);
  Serial.print(',');
  Serial.println(readings[1]);
}
