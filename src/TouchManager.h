#ifndef TOUCH_MANAGER_H
#define TOUCH_MANAGER_H

#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include "Config.h"

enum GestureType {
    GESTURE_NONE,
    GESTURE_TAP,
    GESTURE_DOUBLE_TAP,
    GESTURE_HOLD,
    GESTURE_SWIPE_LEFT,
    GESTURE_SWIPE_RIGHT
};

struct TouchEvent {
    GestureType gesture;
    uint16_t x;
    uint16_t y;
};

// Calibration state machine
enum CalibState {
    CALIB_NONE,       // Normal operation
    CALIB_WAIT_TL,    // Waiting for Top-Left touch
    CALIB_WAIT_TR,    // Waiting for Top-Right touch
    CALIB_WAIT_BL,    // Waiting for Bottom-Left touch
    CALIB_SAVING,     // Computing and saving
    CALIB_DONE        // Complete, showing success screen briefly
};

// Calibration target positions on screen (inset from edges)
#define CALIB_TL_X  30
#define CALIB_TL_Y  30
#define CALIB_TR_X  290
#define CALIB_TR_Y  30
#define CALIB_BL_X  30
#define CALIB_BL_Y  210

class TouchManager {
public:
    TouchManager();
    void begin();
    bool getTouch(uint16_t *x, uint16_t *y);
    TouchEvent update();
    uint8_t getTouchAddress() const { return touchAddress; }
    const char* getTouchTypeString() const;

    // Calibration interface
    void startCalibration();
    bool isCalibrating() const { return calibState != CALIB_NONE; }
    CalibState getCalibState() const { return calibState; }
    bool isCalibrated() const { return calibValid; }

private:
    uint8_t touchAddress; // 0 = XPT2046 SPI, 0x15/0x38 = CST816, 0x5D/0x14 = GT911

    // Internal touch reading
    bool readResistiveTouch(uint16_t *x, uint16_t *y);
    bool readRawResistive(uint16_t *raw90, uint16_t *rawD0);
    uint16_t xpt_read_channel(uint8_t cmd);

    // Gesture tracking state
    bool isTouching;
    unsigned long touchStartTime;
    uint16_t startX, startY;
    uint16_t lastX, lastY;
    unsigned long lastTapTime;
    uint16_t lastTapX, lastTapY;

    // Calibration state
    CalibState calibState;
    bool calibValid;
    bool calibWaitRelease;       // Waiting for finger lift between points
    unsigned long calibDoneTime; // Timestamp when CALIB_DONE entered

    // Raw captures during calibration
    uint16_t cal_raw90_tl, cal_rawD0_tl;
    uint16_t cal_raw90_tr, cal_rawD0_tr;
    uint16_t cal_raw90_bl, cal_rawD0_bl;

    // Computed calibration parameters (saved to NVS)
    bool calibXis90;               // true if channel 0x90 = screen X
    int16_t calibXmin, calibXmax;  // raw ADC range for screen X axis
    int16_t calibYmin, calibYmax;  // raw ADC range for screen Y axis

    void loadCalibration();
    void saveCalibration();
    void processCalibration();
    void computeCalibration();
};

extern TouchManager touch;

#endif // TOUCH_MANAGER_H
