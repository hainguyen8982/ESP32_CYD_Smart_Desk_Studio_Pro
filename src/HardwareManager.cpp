#include "HardwareManager.h"

HardwareManager hardware;

HardwareManager::HardwareManager()
    : currentBrightness(85),
      autoBrightnessEnabled(true), // Enable Auto-Brightness by default
      touchSoundEnabled(true),
      lastLdrCheck(0),
      smoothedLdr(-1) {}

void HardwareManager::begin() {
    // Backlight initialization
    pinMode(PIN_TFT_BL, OUTPUT);
    setBacklight(90);

    // LDR pin configuration (GPIO 34 ADC1)
    pinMode(PIN_LDR, INPUT);
    analogSetPinAttenuation(PIN_LDR, ADC_11db);

    // Speaker pin
    pinMode(PIN_SPEAKER, OUTPUT);
    digitalWrite(PIN_SPEAKER, LOW);

    // RGB LED pins (Active-LOW on standard CYD boards)
    pinMode(PIN_RGB_RED, OUTPUT);
    pinMode(PIN_RGB_GREEN, OUTPUT);
    pinMode(PIN_RGB_BLUE, OUTPUT);
    setRGBColor(COLOR_OFF);
}

void HardwareManager::setBacklight(uint8_t percentage) {
    if (percentage > 100) percentage = 100;
    currentBrightness = percentage;

    uint32_t duty = (percentage * 255) / 100;
    analogWrite(PIN_TFT_BL, duty);
}

void HardwareManager::setTouchSoundEnabled(bool enable) {
    touchSoundEnabled = enable;
}

void HardwareManager::updateAutoBrightness() {
    if (!autoBrightnessEnabled) return;
    if (millis() - lastLdrCheck < LDR_CHECK_INTERVAL_MS) return;
    lastLdrCheck = millis();

    int rawLdr = analogRead(PIN_LDR);
    
    // Correct Hardware Behavior for CYD ESP32 LDR (Active-Low Voltage Divider on GPIO 34):
    // - Light / Normal Room / Torch: rawLdr near 0 -> 95% High Brightness
    // - Hand Covering / Dark Room: rawLdr increases (200..900+) -> Dim down to 15%
    int targetBrightness = map(rawLdr, 0, 800, 95, 15);
    targetBrightness = constrain(targetBrightness, 15, 100);

    // Night Sleep Schedule (23:00 - 06:00): Auto-dim backlight to 5%
    time_t now = time(NULL);
    struct tm ti;
    if (now >= 1600000000 && localtime_r(&now, &ti)) {
        if (ti.tm_hour >= 23 || ti.tm_hour < 6) {
            targetBrightness = 5;
        }
    }

    if (smoothedLdr == -1) {
        smoothedLdr = targetBrightness;
    } else {
        // Smooth transition
        smoothedLdr = (smoothedLdr * 2 + targetBrightness) / 3;
    }

    setBacklight(smoothedLdr);
    Serial.printf("[LDR Diagnostic] Pin 34 Raw: %d | Target BL: %d%% | Active BL: %d%%\n", rawLdr, targetBrightness, smoothedLdr);
}

void HardwareManager::playBeep(uint16_t freqHz, uint16_t durationMs) {
    if (!touchSoundEnabled) return;
    tone(PIN_SPEAKER, freqHz, durationMs);
}

void HardwareManager::playAlarmTune() {
    static const int notes[] = { 1047, 1318, 1568, 2093 }; // C6, E6, G6, C7
    for (int note : notes) {
        tone(PIN_SPEAKER, note, 120);
        delay(140);
    }
    noTone(PIN_SPEAKER);
}

void HardwareManager::stopSound() {
    noTone(PIN_SPEAKER);
    digitalWrite(PIN_SPEAKER, LOW);
}

void HardwareManager::setRGBRaw(bool r, bool g, bool b) {
    // CYD RGB pins are Active-LOW (LOW = ON, HIGH = OFF)
    digitalWrite(PIN_RGB_RED, r ? LOW : HIGH);
    digitalWrite(PIN_RGB_GREEN, g ? LOW : HIGH);
    digitalWrite(PIN_RGB_BLUE, b ? LOW : HIGH);
}

void HardwareManager::setRGBColor(RGBColor color) {
    switch (color) {
        case COLOR_RED:     setRGBRaw(true, false, false); break;
        case COLOR_GREEN:   setRGBRaw(false, true, false); break;
        case COLOR_BLUE:    setRGBRaw(false, false, true); break;
        case COLOR_YELLOW:  setRGBRaw(true, true, false); break;
        case COLOR_CYAN:    setRGBRaw(false, true, true); break;
        case COLOR_MAGENTA: setRGBRaw(true, false, true); break;
        case COLOR_WHITE:   setRGBRaw(true, true, true); break;
        case COLOR_OFF:
        default:            setRGBRaw(false, false, false); break;
    }
}
