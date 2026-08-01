#ifndef HARDWARE_MANAGER_H
#define HARDWARE_MANAGER_H

#include <Arduino.h>
#include "Config.h"

enum RGBColor {
    COLOR_OFF,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_BLUE,
    COLOR_YELLOW,
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_WHITE
};

class HardwareManager {
public:
    HardwareManager();
    void begin();
    
    // Backlight & LDR
    void setBacklight(uint8_t percentage);
    uint8_t getBacklight() const { return currentBrightness; }
    void setAutoBrightnessEnabled(bool enable) { autoBrightnessEnabled = enable; }
    bool isAutoBrightnessEnabled() const { return autoBrightnessEnabled; }
    void updateAutoBrightness();

    // Speaker / Sound
    void playBeep(uint16_t freqHz = 2000, uint16_t durationMs = 80);
    void playAlarmTune();
    void stopSound();

    // RGB LED
    void setRGBColor(RGBColor color);
    void setRGBRaw(bool r, bool g, bool b);

private:
    uint8_t currentBrightness;
    bool autoBrightnessEnabled;
    unsigned long lastLdrCheck;
    int smoothedLdr;
};

extern HardwareManager hardware;

#endif // HARDWARE_MANAGER_H
