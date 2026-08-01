// ═══════════════════════════════════════════════════════════════════════
//  TouchManager.cpp — Touch input with auto-calibration for CYD boards
//  Supports: XPT2046 (SPI resistive), CST816/GT911 (I2C capacitive)
//  Calibration data stored in NVS flash, survives reboot
// ═══════════════════════════════════════════════════════════════════════
#include "TouchManager.h"
#include "HardwareManager.h"

TouchManager touch;

TouchManager::TouchManager()
    : touchAddress(0),
      isTouching(false),
      touchStartTime(0),
      startX(0), startY(0),
      lastX(0), lastY(0),
      calibState(CALIB_NONE),
      calibValid(false),
      calibWaitRelease(false),
      calibDoneTime(0),
      calibXis90(true),
      calibXmin(350), calibXmax(3800),
      calibYmin(350), calibYmax(3800) {}

void TouchManager::begin() {
    // Scan I2C bus to auto-detect Capacitive Touch controllers
    Wire.begin(33, 32); // CYD capacitive touch I2C pins (SDA=33, SCL=32)

    uint8_t addrs[] = { 0x5D, 0x14, 0x15, 0x38 };
    bool found = false;
    for (uint8_t addr : addrs) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            touchAddress = addr;
            found = true;
            calibValid = true; // Capacitive touch doesn't need calibration
            Serial.printf("[TouchManager] Capacitive Touch Detected at I2C 0x%02X\n", addr);
            break;
        }
    }

    if (!found) {
        // Fallback to Resistive SPI XPT2046
        touchAddress = 0;
        Wire.end();
        pinMode(PIN_TOUCH_CS, OUTPUT);
        digitalWrite(PIN_TOUCH_CS, HIGH);
        pinMode(PIN_TOUCH_IRQ, INPUT);
        Serial.println("[TouchManager] Defaulting to Resistive SPI XPT2046 Touch");

        // Load calibration from NVS (if exists)
        loadCalibration();

        // If no calibration data, start calibration automatically
        if (!calibValid) {
            Serial.println("[TouchManager] No calibration found — entering calibration mode");
            startCalibration();
        }
    }
}

const char* TouchManager::getTouchTypeString() const {
    if (touchAddress == 0) return "XPT2046 (SPI)";
    if (touchAddress == 0x5D || touchAddress == 0x14) return "GT911 (I2C)";
    if (touchAddress == 0x15 || touchAddress == 0x38) return "CST816 (I2C)";
    return "Unknown";
}

// ─────────────────────────────────────────────────────────────────────
//  XPT2046 Software SPI Bit-Banging
// ─────────────────────────────────────────────────────────────────────
uint16_t TouchManager::xpt_read_channel(uint8_t cmd) {
    digitalWrite(PIN_TOUCH_CS, LOW);

    pinMode(25, OUTPUT); // CLK
    pinMode(32, OUTPUT); // MOSI
    pinMode(39, INPUT);  // MISO

    for (int i = 7; i >= 0; i--) {
        digitalWrite(32, (cmd >> i) & 1);
        digitalWrite(25, HIGH);
        delayMicroseconds(2);
        digitalWrite(25, LOW);
        delayMicroseconds(2);
    }

    uint16_t result = 0;
    for (int i = 11; i >= 0; i--) {
        digitalWrite(25, HIGH);
        delayMicroseconds(2);
        if (digitalRead(39)) result |= (1 << i);
        digitalWrite(25, LOW);
        delayMicroseconds(2);
    }

    digitalWrite(PIN_TOUCH_CS, HIGH);
    return result;
}

// ─────────────────────────────────────────────────────────────────────
//  Read raw ADC values from both XPT2046 channels (no mapping)
// ─────────────────────────────────────────────────────────────────────
bool TouchManager::readRawResistive(uint16_t *raw90, uint16_t *rawD0) {
    if (digitalRead(PIN_TOUCH_IRQ) == HIGH) return false;

    long sum90 = 0, sumD0 = 0;
    int samples = 8;
    for (int i = 0; i < samples; i++) {
        sum90 += xpt_read_channel(0x90);
        sumD0 += xpt_read_channel(0xD0);
    }

    *raw90 = sum90 / samples;
    *rawD0 = sumD0 / samples;

    // Reject noise / edge touches
    if (*raw90 < 100 || *rawD0 < 100 || *raw90 > 4000 || *rawD0 > 4000) return false;
    return true;
}

// ─────────────────────────────────────────────────────────────────────
//  Read resistive touch with calibrated coordinate mapping
// ─────────────────────────────────────────────────────────────────────
bool TouchManager::readResistiveTouch(uint16_t *x, uint16_t *y) {
    uint16_t raw90, rawD0;
    if (!readRawResistive(&raw90, &rawD0)) return false;

    int rawX = calibXis90 ? raw90 : rawD0;
    int rawY = calibXis90 ? rawD0 : raw90;

    // Map from calibration raw range to calibration screen positions,
    // then the constrain extends to full screen
    long calX = map((long)rawX, calibXmin, calibXmax, CALIB_TL_X, CALIB_TR_X);
    long calY = map((long)rawY, calibYmin, calibYmax, CALIB_TL_Y, CALIB_BL_Y);

    *x = constrain(calX, 0, 319);
    *y = constrain(calY, 0, 239);

    return true;
}

// ─────────────────────────────────────────────────────────────────────
//  Capacitive Touch Readers (CST816 / GT911)
// ─────────────────────────────────────────────────────────────────────
bool TouchManager::getTouch(uint16_t *x, uint16_t *y) {
    if (touchAddress == 0) {
        return readResistiveTouch(x, y);
    }

    // CST816 / FT6336 / CST820 Capacitive touch
    if (touchAddress == 0x15 || touchAddress == 0x38) {
        Wire.beginTransmission(touchAddress);
        Wire.write(0x02);
        if (Wire.endTransmission() == 0) {
            Wire.requestFrom((uint8_t)touchAddress, (uint8_t)5);
            if (Wire.available() >= 5) {
                uint8_t status = Wire.read();
                uint8_t x1 = Wire.read();
                uint8_t x2 = Wire.read();
                uint8_t y1 = Wire.read();
                uint8_t y2 = Wire.read();

                int touches = status & 0x0F;
                if (touches > 0 && touches <= 5) {
                    uint16_t touchX = ((x1 & 0x0F) << 8) | x2;
                    uint16_t touchY = ((y1 & 0x0F) << 8) | y2;
                    *x = touchY;
                    *y = 240 - touchX;
                    return true;
                }
            }
        }
    }
    // GT911 Capacitive touch
    else if (touchAddress == 0x5D || touchAddress == 0x14) {
        Wire.beginTransmission(touchAddress);
        Wire.write(0x81);
        Wire.write(0x4E);
        if (Wire.endTransmission() == 0) {
            Wire.requestFrom((uint8_t)touchAddress, (uint8_t)1);
            if (Wire.available()) {
                uint8_t status = Wire.read();
                uint8_t touches = status & 0x0F;
                bool gotTouch = false;
                if (touches > 0 && touches <= 5) {
                    Wire.beginTransmission(touchAddress);
                    Wire.write(0x81);
                    Wire.write(0x50);
                    if (Wire.endTransmission() == 0) {
                        Wire.requestFrom((uint8_t)touchAddress, (uint8_t)4);
                        if (Wire.available() >= 4) {
                            uint8_t xl = Wire.read();
                            uint8_t xh = Wire.read();
                            uint8_t yl = Wire.read();
                            uint8_t yh = Wire.read();
                            *x = (yl | (yh << 8));
                            *y = 240 - (xl | (xh << 8));
                            gotTouch = true;
                        }
                    }
                }
                Wire.beginTransmission(touchAddress);
                Wire.write(0x81);
                Wire.write(0x4E);
                Wire.write(0);
                Wire.endTransmission();
                return gotTouch;
            }
        }
    }
    return false;
}

// ═══════════════════════════════════════════════════════════════════════
//  CALIBRATION SYSTEM
// ═══════════════════════════════════════════════════════════════════════

void TouchManager::startCalibration() {
    if (touchAddress != 0) {
        Serial.println("[Calib] Capacitive touch — calibration not needed");
        return;
    }
    calibState = CALIB_WAIT_TL;
    calibWaitRelease = true; // Wait for any current touch to release first
    Serial.println("[Calib] Started — touch the crosshair targets");
}

void TouchManager::loadCalibration() {
    Preferences prefs;
    prefs.begin("touch_cal", true);
    calibValid = prefs.getBool("valid", false);
    if (calibValid) {
        calibXis90 = prefs.getBool("xIs90", true);
        calibXmin  = prefs.getShort("xMin", 350);
        calibXmax  = prefs.getShort("xMax", 3800);
        calibYmin  = prefs.getShort("yMin", 350);
        calibYmax  = prefs.getShort("yMax", 3800);
        Serial.printf("[Calib] Loaded NVS: xCh=0x%02X, X[%d→%d], Y[%d→%d]\n",
                      calibXis90 ? 0x90 : 0xD0, calibXmin, calibXmax, calibYmin, calibYmax);
    } else {
        Serial.println("[Calib] No NVS calibration data");
    }
    prefs.end();
}

void TouchManager::saveCalibration() {
    Preferences prefs;
    prefs.begin("touch_cal", false);
    prefs.putBool("valid", true);
    prefs.putBool("xIs90", calibXis90);
    prefs.putShort("xMin", calibXmin);
    prefs.putShort("xMax", calibXmax);
    prefs.putShort("yMin", calibYmin);
    prefs.putShort("yMax", calibYmax);
    prefs.end();
    calibValid = true;
    Serial.printf("[Calib] Saved NVS: xCh=0x%02X, X[%d→%d], Y[%d→%d]\n",
                  calibXis90 ? 0x90 : 0xD0, calibXmin, calibXmax, calibYmin, calibYmax);
}

void TouchManager::computeCalibration() {
    // From TL and TR (same screen Y=30, screen X: 30→290):
    // The ADC channel with the LARGER delta = screen X axis
    int delta_90_horiz = abs((int)cal_raw90_tr - (int)cal_raw90_tl);
    int delta_D0_horiz = abs((int)cal_rawD0_tr - (int)cal_rawD0_tl);

    Serial.printf("[Calib] Horizontal deltas: ch0x90=%d, ch0xD0=%d\n", delta_90_horiz, delta_D0_horiz);

    if (delta_90_horiz > delta_D0_horiz) {
        // Channel 0x90 maps to screen X axis
        calibXis90 = true;
        calibXmin  = cal_raw90_tl;  // raw at screen X=30
        calibXmax  = cal_raw90_tr;  // raw at screen X=290
        calibYmin  = cal_rawD0_tl;  // raw at screen Y=30  (TL)
        calibYmax  = cal_rawD0_bl;  // raw at screen Y=210 (BL)
    } else {
        // Channel 0xD0 maps to screen X axis
        calibXis90 = false;
        calibXmin  = cal_rawD0_tl;
        calibXmax  = cal_rawD0_tr;
        calibYmin  = cal_raw90_tl;
        calibYmax  = cal_raw90_bl;
    }

    Serial.printf("[Calib] Result: X channel=0x%02X, X raw[%d→%d], Y raw[%d→%d]\n",
                  calibXis90 ? 0x90 : 0xD0, calibXmin, calibXmax, calibYmin, calibYmax);
}

void TouchManager::processCalibration() {
    // Handle CALIB_DONE timeout (show success for 1.5 seconds)
    if (calibState == CALIB_DONE) {
        if (millis() - calibDoneTime > 1500) {
            calibState = CALIB_NONE;
            Serial.println("[Calib] Returning to normal operation");
        }
        return;
    }

    uint16_t raw90, rawD0;
    bool pressed = readRawResistive(&raw90, &rawD0);

    // Wait for finger release between calibration points
    if (calibWaitRelease) {
        if (!pressed) {
            calibWaitRelease = false;
            delay(100); // Brief debounce
        }
        return;
    }

    if (!pressed) return;

    // Finger is down — capture this calibration point
    hardware.playBeep(2400, 50);

    switch (calibState) {
        case CALIB_WAIT_TL:
            cal_raw90_tl = raw90;
            cal_rawD0_tl = rawD0;
            Serial.printf("[Calib] TL captured: 0x90=%d, 0xD0=%d\n", raw90, rawD0);
            calibState = CALIB_WAIT_TR;
            calibWaitRelease = true;
            break;

        case CALIB_WAIT_TR:
            cal_raw90_tr = raw90;
            cal_rawD0_tr = rawD0;
            Serial.printf("[Calib] TR captured: 0x90=%d, 0xD0=%d\n", raw90, rawD0);
            calibState = CALIB_WAIT_BL;
            calibWaitRelease = true;
            break;

        case CALIB_WAIT_BL:
            cal_raw90_bl = raw90;
            cal_rawD0_bl = rawD0;
            Serial.printf("[Calib] BL captured: 0x90=%d, 0xD0=%d\n", raw90, rawD0);

            // Compute and save calibration
            computeCalibration();
            saveCalibration();

            calibState = CALIB_DONE;
            calibDoneTime = millis();
            hardware.playBeep(1800, 100);
            delay(120);
            hardware.playBeep(2400, 100);
            Serial.println("[Calib] ✓ Calibration complete and saved!");
            break;

        default:
            break;
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Main Update Loop — Gesture Detection or Calibration Processing
// ═══════════════════════════════════════════════════════════════════════
TouchEvent TouchManager::update() {
    TouchEvent event = { GESTURE_NONE, 0, 0 };

    // During calibration, suspend normal gesture detection
    if (calibState != CALIB_NONE) {
        processCalibration();
        return event;
    }

    // Normal gesture detection
    uint16_t currX = 0, currY = 0;
    bool pressed = getTouch(&currX, &currY);

    if (pressed) {
        if (!isTouching) {
            isTouching = true;
            touchStartTime = millis();
            startX = currX;
            startY = currY;
        }
        lastX = currX;
        lastY = currY;
    } else {
        if (isTouching) {
            isTouching = false;
            unsigned long duration = millis() - touchStartTime;
            int dx = lastX - startX;
            int dy = lastY - startY;

            // Swipe detection: min 30px horizontal, max 800ms, horizontal > vertical
            if (duration < 800 && abs(dx) > 30 && abs(dx) > abs(dy)) {
                if (dx > 0) {
                    event.gesture = GESTURE_SWIPE_RIGHT;
                } else {
                    event.gesture = GESTURE_SWIPE_LEFT;
                }
                hardware.playBeep(2800, 25);
            }
            // Tap detection: small movement, short duration
            else if (duration < 500 && abs(dx) < 30 && abs(dy) < 30) {
                event.gesture = GESTURE_TAP;
                event.x = startX;  // Use start position (more stable than last)
                event.y = startY;
                hardware.playBeep(2400, 30);
            }
        }
    }
    return event;
}
