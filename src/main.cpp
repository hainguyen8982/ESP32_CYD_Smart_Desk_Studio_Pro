#include <Arduino.h>
#include "Config.h"
#include "HardwareManager.h"
#include "TouchManager.h"
#include "DisplayManager.h"
#include "NetworkManager.h"
#include "PCMonitor.h"
#include "DeskUtilities.h"
#include "Theme.h"
#include <time.h>

// BOOT button (GPIO 0) long-press tracking
static unsigned long bootBtnPressStart = 0;
static bool bootBtnWasPressed = false;

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println("\n=============================================");
    Serial.println("   ESP32 CYD Desk Weather Clock & Dashboard   ");
    Serial.println("=============================================");

    // Initialize System Subsystems
    hardware.begin();
    display.begin();
    touch.begin();
    pcMonitor.begin();
    deskUtils.begin();

    // BOOT button as input (has external pull-up on CYD boards)
    pinMode(PIN_BOOT_BTN, INPUT_PULLUP);

    // Log detected touch hardware
    Serial.printf("[System] Touch Controller: %s\n", touch.getTouchTypeString());
    Serial.printf("[System] Touch Calibrated: %s\n", touch.isCalibrated() ? "Yes" : "No (entering calibration)");

    // Connect WiFi & start Web Server
    network.begin();
}

void loop() {
    // 1. Update Hardware Auto-Brightness from LDR Sensor
    hardware.updateAutoBrightness();

    // 2. Process USB Serial PC Stats Data
    pcMonitor.update();

    // 3. Process Async Network Tasks & APIs
    network.update();

    // 4. Update Desk Utilities (Pomodoro & Alarm)
    deskUtils.update();

    // Check NTP Alarm Trigger
    time_t now = time(NULL);
    struct tm timeinfo;
    if (now >= 1600000000 && localtime_r(&now, &timeinfo)) {
        deskUtils.checkAlarm(timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    }

    // 5. Handle Web Portal Remote Page Commands
    int remoteP = network.getRemoteRequestedPage();
    if (remoteP >= 0) {
        display.setCurrentPage(remoteP);
        network.clearRemoteRequestedPage();
    }

    // 6. BOOT Button (GPIO 0) — Long press 3s = Recalibrate
    if (!touch.isCalibrating()) {
        if (digitalRead(PIN_BOOT_BTN) == LOW) {
            if (!bootBtnWasPressed) {
                bootBtnWasPressed = true;
                bootBtnPressStart = millis();
            } else if (millis() - bootBtnPressStart > 3000) {
                Serial.println("[System] BOOT button held 3s -> Starting calibration");
                touch.startCalibration();
                bootBtnWasPressed = false;
            }
        } else {
            bootBtnWasPressed = false;
        }
    }

    // 7. Process Touch Coordinates & Gestures
    //    (During calibration, touch.update() handles calibration internally)
    TouchEvent evt = touch.update();

    if (!touch.isCalibrating() && evt.gesture != GESTURE_NONE) {
        if (evt.gesture == GESTURE_SWIPE_LEFT) {
            display.nextPage();
            Serial.printf("[Touch] Swiped Left -> Page %d\n", display.getCurrentPage());

        } else if (evt.gesture == GESTURE_SWIPE_RIGHT) {
            display.previousPage();
            Serial.printf("[Touch] Swiped Right -> Page %d\n", display.getCurrentPage());

        } else if (evt.gesture == GESTURE_TAP) {
            Serial.printf("[Touch] Tap at (%d, %d) Page=%d\n", evt.x, evt.y, display.getCurrentPage());

            if (deskUtils.isAlarmRinging()) {
                deskUtils.dismissAlarm();

            } else if (evt.y < 25 && evt.x > 250) {
                // Top-Right corner: Cycle Theme
                nextTheme();
                Serial.println("[Touch] Theme cycled");

            } else if (evt.y < 25 && evt.x < 80) {
                // Top-Left corner: Go to Home (Page 0)
                display.setCurrentPage(0);
                Serial.println("[Touch] Home");

            } else if (display.getCurrentPage() == 1 && evt.y >= 28 && evt.y <= 60) {
                // Page 1: Month navigation row
                if (evt.x < 110) {
                    display.prevCalendarMonth();
                } else if (evt.x > 210) {
                    display.nextCalendarMonth();
                } else {
                    display.resetCalendarMonth();
                }

            } else if (display.getCurrentPage() == 7 && evt.y >= 60 && evt.y <= 84) {
                // Settings Page: Tap "Calibrate Touch" menu item
                touch.startCalibration();
                Serial.println("[Touch] Settings -> Calibrate Touch");

            } else if (display.getCurrentPage() == 7 && evt.y >= 88 && evt.y <= 112) {
                // Settings Page: Toggle Auto Brightness
                hardware.setAutoBrightnessEnabled(!hardware.isAutoBrightnessEnabled());
                if (!hardware.isAutoBrightnessEnabled()) hardware.setBacklight(85);
                Serial.printf("[Touch] Settings -> Auto Brightness: %s\n",
                              hardware.isAutoBrightnessEnabled() ? "ON" : "OFF");

            } else if (display.getCurrentPage() == 6 && evt.x >= 100 && evt.x <= 220 && evt.y >= 60 && evt.y <= 180) {
                // Page 6: Toggle Pomodoro (center widget area only)
                deskUtils.togglePomodoro();

            } else {
                // Default: Left half = prev page, Right half = next page
                if (evt.x < 160) {
                    display.previousPage();
                    Serial.printf("[Touch] Left -> Page %d\n", display.getCurrentPage());
                } else {
                    display.nextPage();
                    Serial.printf("[Touch] Right -> Page %d\n", display.getCurrentPage());
                }
            }
        }
    }

    // 8. Render UI to TFT Screen
    display.update();
}
