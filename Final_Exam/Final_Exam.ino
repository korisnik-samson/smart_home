#include <DHT.h>
#define dht_pin A2
#define DHTTYPE DHT11

DHT dhtSensor(dht_pin, DHTTYPE);

#define heaterRelayPin 8  // Relay for controlling the heater
#define fanRelayPin 4     // Relay for controlling the fan
#define tempSensorPin A0  // LM35 temperature sensor connected to analog pin A0
#define photoresistorPin A1  // Photoresistor connected to analog pin A1
#define motionSensorPin 2    // Motion sensor connected to digital pin 2
#define diodeRelayPin 7      // Relay for controlling the diode
#define redLedPin 10         // Red LED for emergency mode
#define greenLedPin 11       // Green LED for normal mode
#define emergencyButtonPin 3 // Emergency button

// Flags that enable/disable modes
bool climateControlEnabled = false;
bool lightModeEnabled = false;
bool motionModeEnabled = false;
bool emergencyModeEnabled = false;

// Light threshold percentage for activating the diode
int lightThreshold = 30;

// State variables
bool diodeState = false;
unsigned long motionStartTime = 0;
unsigned long previousMillis = 0;
unsigned long dailyReportMillis = 0;
const long interval = 600000; // 10 minutes for temperature and illumination checks

// Daily data tracking
float minTemperature = 100;
float maxTemperature = -100;
float temperatureSum = 0;
int temperatureCount = 0;

int minIllumination = 100;
int maxIllumination = 0;
int illuminationSum = 0;
int illuminationCount = 0;

int motionDetectionCount = 0;
unsigned long homeSecureDuration = 0;
unsigned long lightAutoDuration = 0;
unsigned long emergencyStartTime = 0;

void setup() {
    pinMode(heaterRelayPin, OUTPUT);
    pinMode(fanRelayPin, OUTPUT);
    pinMode(diodeRelayPin, OUTPUT);
    pinMode(redLedPin, OUTPUT);
    pinMode(greenLedPin, OUTPUT);
    pinMode(emergencyButtonPin, INPUT);

    Serial.begin(9600);

    pinMode(photoresistorPin, INPUT);
    pinMode(motionSensorPin, INPUT);

    digitalWrite(greenLedPin, HIGH); // Green LED on by default (normal mode)
}

void loop() {
    // Check for serial commands
    processSerialCommands();

    // Handle emergency mode
    if (digitalRead(emergencyButtonPin) == HIGH && !emergencyModeEnabled) {
        activateEmergencyMode();
    }

    if (emergencyModeEnabled) {
        handleEmergencyMode();

    } else {
        unsigned long currentMillis = millis();

        // Handle climate control
        if (climateControlEnabled) {
            climateControl();
        } else {
            // Ensure both heater and fan are off
            digitalWrite(heaterRelayPin, LOW);
            digitalWrite(fanRelayPin, LOW);
        }

        // Handle light mode
        if (lightModeEnabled && !motionModeEnabled) {
            handleLightMode();
        }

        // Handle motion mode
        if (motionModeEnabled) {
            handleMotionMode();
        }

        // Measure temperature and illumination every 10 minutes
        if (currentMillis - previousMillis >= interval) {
            previousMillis = currentMillis;
            measureAndLogData();
        }

        // Handle daily report (e.g., every 24 hours)
        if (millis() - dailyReportMillis >= 86400000) { // 24 hours
            dailyReportMillis = millis();
            sendDailyReport();
        }
    }
}

void climateControl() {
    float temperature = readTemperature();

    if (temperature < 17) {
        digitalWrite(heaterRelayPin, HIGH);
        digitalWrite(fanRelayPin, LOW);
        Serial.println("Heater ON, Fan OFF");

    } else if (temperature > 23) {
        digitalWrite(heaterRelayPin, LOW);
        digitalWrite(fanRelayPin, HIGH);
        Serial.println("Heater OFF, Fan ON");

    } else {
        digitalWrite(heaterRelayPin, LOW);
        digitalWrite(fanRelayPin, LOW);
        Serial.println("Heater OFF, Fan OFF");
    }
}

void handleLightMode() {
    int lightLevel = map(analogRead(photoresistorPin), 0, 1023, 0, 100);

    if (lightLevel < lightThreshold) {
        digitalWrite(diodeRelayPin, HIGH);

    } else {
        digitalWrite(diodeRelayPin, LOW);
    }
}

void handleMotionMode() {
    if (digitalRead(motionSensorPin) == HIGH) {
        motionStartTime = millis();

        digitalWrite(diodeRelayPin, HIGH);
        motionDetectionCount++;

        Serial.println("Motion detected! Email notification sent."); // Mock email notification
    }

    if (millis() - motionStartTime > 10000 && digitalRead(motionSensorPin) == LOW) {
        digitalWrite(diodeRelayPin, LOW);
    }
}

void measureAndLogData() {
    float temperature = readTemperature();
    int lightLevel = map(analogRead(photoresistorPin), 0, 1023, 0, 100);

    // Log temperature
    minTemperature = min(minTemperature, temperature);
    maxTemperature = max(maxTemperature, temperature);
    temperatureSum += temperature;
    temperatureCount++;

    // Log illumination
    minIllumination = min(minIllumination, lightLevel);
    maxIllumination = max(maxIllumination, lightLevel);
    illuminationSum += lightLevel;
    illuminationCount++;

    Serial.print("Humidity (%): ");
    Serial.println((float) dhtSensor.readHumidity(), 2);

    Serial.print("Temperature (°C): ");
    Serial.println(temperature);

    Serial.print("Illumination (%): ");
    Serial.println(lightLevel);
}

float readTemperature() {
    int reading = analogRead(tempSensorPin);
    float voltage = reading * 5.0 / 1024.0;  // Convert reading to voltage
    float temperatureC = voltage * 100;     // Convert voltage to Celsius (LM35: 10mV per degree)

    return temperatureC;
}

void processSerialCommands() {
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim();

        if (command == "climate_on") {
            climateControlEnabled = true;
            Serial.println("Climate control enabled");

        } else if (command == "climate_off") {
            climateControlEnabled = false;
            Serial.println("Climate control disabled");

        } else if (command == "light_on") {
            lightModeEnabled = false;
            motionModeEnabled = false;
            digitalWrite(diodeRelayPin, HIGH);
            Serial.println("Light turned ON (manual)");

        } else if (command == "light_off") {
            lightModeEnabled = false;
            motionModeEnabled = false;
            digitalWrite(diodeRelayPin, LOW);
            Serial.println("Light turned OFF (manual)");

        } else if (command == "auto_on") {
            lightModeEnabled = true;
            motionModeEnabled = false;
            Serial.println("Light auto mode enabled");

        } else if (command == "auto_off") {
            lightModeEnabled = false;
            Serial.println("Light auto mode disabled");

        } else if (command == "secure_on") {
            motionModeEnabled = true;
            lightModeEnabled = false;
            Serial.println("Home secure mode enabled");

        } else if (command == "secure_off") {
            motionModeEnabled = false;
            Serial.println("Home secure mode disabled");

        } else if (command == "emergency_off") {
            deactivateEmergencyMode();

        } else {
            Serial.println("Invalid command");
        }
    }
}

void activateEmergencyMode() {
    emergencyModeEnabled = true;

    digitalWrite(redLedPin, HIGH);
    digitalWrite(greenLedPin, LOW);

    climateControlEnabled = false;
    lightModeEnabled = false;
    motionModeEnabled = true; // Keep home secure mode on

    digitalWrite(heaterRelayPin, LOW);
    digitalWrite(fanRelayPin, LOW);

    Serial.println("Emergency mode activated! Email sent.");
}

void deactivateEmergencyMode() {
    emergencyModeEnabled = false;

    digitalWrite(redLedPin, LOW);
    digitalWrite(greenLedPin, HIGH);

    Serial.println("Emergency mode deactivated.");
}

void handleEmergencyMode() {
    // Ensure that only secure mode and red LED are active
    digitalWrite(diodeRelayPin, HIGH);
}

void sendDailyReport() {
    // Mocking report creation and email sending
    Serial.println("Sending daily report:");

    Serial.print("Min Temp: "); Serial.println(minTemperature);
    Serial.print("Max Temp: "); Serial.println(maxTemperature);
    Serial.print("Avg Temp: "); Serial.println(temperatureSum / temperatureCount);

    Serial.print("Min Illumination: "); Serial.println(minIllumination);
    Serial.print("Max Illumination: "); Serial.println(maxIllumination);
    Serial.print("Avg Illumination: "); Serial.println(illuminationSum / illuminationCount);

    Serial.print("Total motion detections: "); Serial.println(motionDetectionCount);
}
