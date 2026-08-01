#include "HardwareManager.h"

HardwareManager hardware;

HardwareManager::HardwareManager()
    : currentBrightness(85),
      autoBrightnessEnabled(false),
      lastLdrCheck(0),
      smoothedLdr(-1) {}

void HardwareManager::begin() {
    // Backlight PWM initialization on dedicated LEDC Channel 7 (prevents tone() conflicts)
    pinMode(PIN_TFT_BL, OUTPUT);
    ledcSetup(7, 5000, 8); // Channel 7, 5kHz, 8-bit resolution
    ledcAttachPin(PIN_TFT_BL, 7);
    setBacklight(85);

    // LDR pin
    pinMode(PIN_LDR, INPUT);

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
    ledcWrite(7, duty);
}

void HardwareManager::updateAutoBrightness() {
    if (!autoBrightnessEnabled) return;
    if (millis() - lastLdrCheck < LDR_CHECK_INTERVAL_MS) return;
    lastLdrCheck = millis();

    int rawLdr = analogRead(PIN_LDR);
    // Map LDR analog values (typically ~300 in bright room to ~3500 in dark)
    int targetBrightness = map(rawLdr, 300, 3200, 15, 100);
    targetBrightness = constrain(targetBrightness, 15, 100);

    if (smoothedLdr == -1) {
        smoothedLdr = targetBrightness;
    } else {
        smoothedLdr = (smoothedLdr * 3 + targetBrightness) / 4;
    }

    setBacklight(smoothedLdr);
}

void HardwareManager::playBeep(uint16_t freqHz, uint16_t durationMs) {
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
