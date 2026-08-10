#include <Arduino.h>
#include "Config.h"
#include "HardwareManager.h"
#include "TouchManager.h"
#include "DisplayManager.h"
#include "NetworkManager.h"
#include "PCMonitor.h"
#include "DeskUtilities.h"
#include "Theme.h"
#include "DynamicSkinManager.h"
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
    g_skinMgr.begin();

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

    // 6. BOOT Button (GPIO 0) — Short press (<1s) = Toggle App Launcher Overlay, Long press (3s) = Recalibrate Touch
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
            if (bootBtnWasPressed) {
                unsigned long dur = millis() - bootBtnPressStart;
                if (dur >= 40 && dur < 1000) {
                    display.toggleAppLauncher(); // Toggle System Overlay Menu!
                    hardware.playBeep(2400, 40);
                    Serial.println("[System] BOOT button pressed -> Toggled App Launcher Overlay");
                }
                bootBtnWasPressed = false;
            }
        }
    }

    // 7. Process Touch Coordinates & Gestures
    //    (During calibration, touch.update() handles calibration internally)
    TouchEvent evt = touch.update();

    if (!touch.isCalibrating() && evt.gesture != GESTURE_NONE) {
        if (display.isModalOpen()) {
            if (display.getModalType() == MODAL_BEEP_VOLUME) {
                if (evt.y >= 160) {
                    // SAVE & CLOSE (Bottom Button)
                    display.closeDetailModal();
                    hardware.playBeep(2000, 40);
                    Serial.println("[Touch] Beep Volume Modal Closed & Saved");
                } else if (evt.y >= 115 && evt.y <= 155) {
                    // 5 Preset Buttons (MUTE, 25%, 50%, 75%, 100%)
                    static const uint8_t presets[] = { 0, 25, 50, 75, 100 };
                    for (int i = 0; i < 5; i++) {
                        int bx = 24 + i * 55;
                        if (evt.x >= bx && evt.x <= bx + 48) {
                            hardware.setSoundVolume(presets[i]);
                            hardware.playBeep(2000, 60);
                            Serial.printf("[Touch] Volume Preset Selected: %d%%\n", presets[i]);
                            break;
                        }
                    }
                } else if (evt.y >= 70 && evt.y <= 110) {
                    // Slider Track Tap / Drag
                    uint8_t vol = (uint8_t)constrain((evt.x - 30) * 100 / 260, 0, 100);
                    hardware.setSoundVolume(vol);
                    hardware.playBeep(2000, 60);
                    Serial.printf("[Touch] Volume Slider Tapped: %d%%\n", vol);
                }
            } else if (display.getModalType() == MODAL_SET_ALARM) {
                if (evt.y >= 140) {
                    if (evt.x < 160) {
                        // CANCEL (Left Button)
                        display.closeDetailModal();
                        Serial.println("[Touch] Alarm modal cancelled");
                    } else {
                        // SAVE & ENABLE ALARM (Right Button)
                        deskUtils.setAlarm(display.getTempAlarmHour(), display.getTempAlarmMin(), true);
                        display.closeDetailModal();
                        Serial.printf("[Touch] Alarm set to %02d:%02d ON\n", display.getTempAlarmHour(), display.getTempAlarmMin());
                    }
                } else if (evt.x < 160) {
                    // Hour Box
                    if (evt.y < 95) {
                        display.adjustTempAlarmHour(1);
                    } else {
                        display.adjustTempAlarmHour(-1);
                    }
                } else {
                    // Minute Box
                    if (evt.y < 95) {
                        display.adjustTempAlarmMin(5);
                    } else {
                        display.adjustTempAlarmMin(-5);
                    }
                }
            } else if (evt.gesture == GESTURE_TAP || evt.gesture == GESTURE_SWIPE_LEFT || evt.gesture == GESTURE_SWIPE_RIGHT) {
                display.closeDetailModal();
                Serial.println("[Touch] Detail modal closed");
            }

        } else if (display.isAppLauncherActive()) {
            // App Launcher System Overlay Mode -> Tap App Tile jumps to feature page 0..7 & closes overlay
            if (evt.gesture == GESTURE_HOLD || (evt.y < 28 && evt.x >= 25 && evt.x <= 240)) {
                display.closeAppLauncher();
                hardware.playBeep(1800, 30);
            } else if (evt.y >= 30 && evt.y <= 230) {
                for (int i = 0; i < 8; i++) {
                    int col = i % 3;
                    int row = i / 3;
                    int bx = 11 + col * 102;
                    int by = 34 + row * 66;
                    if (evt.x >= bx && evt.x <= bx + 94 && evt.y >= by && evt.y <= by + 60) {
                        display.setCurrentPage(i); // Jump to feature page 0..7
                        display.closeAppLauncher(); // Close overlay!
                        hardware.playBeep(2200, 40);
                        Serial.printf("[Touch] App Launcher -> Opened Page %d\n", i);
                        break;
                    }
                }
            }

        } else if (evt.gesture == GESTURE_SWIPE_LEFT) {
            display.nextPage();
            Serial.printf("[Touch] Swiped Left -> Page %d\n", display.getCurrentPage());

        } else if (evt.gesture == GESTURE_SWIPE_RIGHT) {
            display.previousPage();
            Serial.printf("[Touch] Swiped Right -> Page %d\n", display.getCurrentPage());

        } else if (evt.gesture == GESTURE_HOLD) {
            // Quick Action 1: Long-press screen anywhere -> Open App Launcher Overlay!
            display.toggleAppLauncher();
            hardware.playBeep(2200, 60);
            Serial.println("[Touch] Long press detected -> Toggled App Launcher Overlay");

        } else if (evt.gesture == GESTURE_TAP || evt.gesture == GESTURE_DOUBLE_TAP) {
            Serial.printf("[Touch] Touch at (%d, %d) Page=%d Gesture=%d\n", evt.x, evt.y, display.getCurrentPage(), evt.gesture);

            if (deskUtils.isAlarmRinging()) {
                deskUtils.dismissAlarm();

            } else if (evt.y < 28 && evt.x >= 25 && evt.x <= 240) {
                // Quick Action 2: Tap Header Title Bar -> Open App Launcher Overlay!
                display.toggleAppLauncher();
                hardware.playBeep(2000, 40);
                Serial.println("[Touch] Header Title Tapped -> Toggled App Launcher Overlay");

            } else if (evt.y < 25 && evt.x > 250) {
                // Top-Right corner: Cycle Theme
                nextTheme();
                Serial.println("[Touch] Theme cycled");

            } else if (evt.y < 25 && evt.x < 80) {
                // Top-Left corner: Go to Home (Page 0)
                display.setCurrentPage(0);
                Serial.println("[Touch] Home");

            } else if (display.getCurrentPage() == 2 && evt.x >= 180 && evt.x <= 310 && evt.y >= 54 && evt.y <= 134) {
                // Page 2: Tap Gold Chart -> Open SJC Gold Fullscreen Detail Chart
                display.openDetailModal(MODAL_GOLD_SJC);
                Serial.println("[Touch] Finance -> Opened SJC Gold Detail Chart Modal");

            } else if (display.getCurrentPage() == 2 && evt.x >= 170 && evt.x <= 310 && evt.y >= 155 && evt.y <= 186) {
                // Page 2: Tap Currency 1 Chart -> Open Currency 1 Detail Chart
                display.openDetailModal(MODAL_CURRENCY_1);
                Serial.println("[Touch] Finance -> Opened Currency 1 Detail Chart Modal");

            } else if (display.getCurrentPage() == 2 && evt.x >= 170 && evt.x <= 310 && evt.y >= 187 && evt.y <= 220) {
                // Page 2: Tap Currency 2 Chart -> Open Currency 2 Detail Chart
                display.openDetailModal(MODAL_CURRENCY_2);
                Serial.println("[Touch] Finance -> Opened Currency 2 Detail Chart Modal");

            } else if (display.getCurrentPage() == 1 && evt.y >= 28 && evt.y <= 60) {
                // Page 1: Month navigation row
                if (evt.x < 110) {
                    display.prevCalendarMonth();
                } else if (evt.x > 210) {
                    display.nextCalendarMonth();
                } else {
                    display.resetCalendarMonth();
                }

            } else if (display.getCurrentPage() == 5) {
                // Top Alarm Bar (y = 34..76)
                if (evt.y >= 34 && evt.y <= 76) {
                    if (evt.x >= 210) {
                        // Tap right side pill -> Toggle Alarm ON/OFF
                        deskUtils.toggleAlarm();
                        Serial.printf("[Touch] DeskUtils -> Toggle Alarm: %s\n", deskUtils.isAlarmEnabled() ? "ON" : "OFF");
                    } else {
                        // Tap Alarm digits / text -> Open Set Alarm Modal
                        display.initTempAlarm(deskUtils.getAlarmHour(), deskUtils.getAlarmMinute());
                        display.openDetailModal(MODAL_SET_ALARM);
                        Serial.println("[Touch] DeskUtils -> Open Set Alarm Modal");
                    }
                }
                // Expanded Center Hero Pomodoro Circle (cx = 160, cy = 155, r = 68)
                else if ((int32_t)(evt.x - 160)*(evt.x - 160) + (int32_t)(evt.y - 155)*(evt.y - 155) <= 68*68) {
                    if (evt.gesture == GESTURE_HOLD) {
                        // Hold inside Pomodoro circle -> Reset Pomodoro to 25:00
                        deskUtils.resetPomodoro();
                        Serial.println("[Touch] DeskUtils -> Reset Pomodoro");
                    } else {
                        // Single Tap inside Pomodoro circle -> Start / Pause Pomodoro
                        deskUtils.togglePomodoro();
                        Serial.println("[Touch] DeskUtils -> Toggle Pomodoro");
                    }
                }
                // Outside Circle -> Page Navigation
                else {
                    if (evt.x < 160) {
                        display.previousPage();
                    } else {
                        display.nextPage();
                    }
                    Serial.printf("[Touch] DeskUtils -> Page %d\n", display.getCurrentPage());
                }

            } else if (display.getCurrentPage() == 6) {
                // Media Control Page (Page 6)
                if (evt.x < 32 || (evt.y < 35 && evt.x < 160)) {
                    display.previousPage();
                } else if (evt.x > 288 || (evt.y < 35 && evt.x >= 160)) {
                    display.nextPage();
                } else if (evt.y >= 48 && evt.y <= 130) {
                    if (evt.x >= 34 && evt.x <= 110) {
                        network.triggerMediaAction("prev");
                        hardware.playBeep(1200, 40);
                    } else if (evt.x >= 117 && evt.x <= 203) {
                        display.togglePlayState();
                        network.triggerMediaAction("play_pause");
                        hardware.playBeep(1500, 40);
                    } else if (evt.x >= 210 && evt.x <= 286) {
                        network.triggerMediaAction("next");
                        hardware.playBeep(1200, 40);
                    }
                } else if (evt.y >= 134 && evt.y <= 220) {
                    if (evt.x >= 34 && evt.x <= 110) {
                        network.triggerMediaAction("vol_down");
                        hardware.playBeep(900, 40);
                    } else if (evt.x >= 117 && evt.x <= 203) {
                        network.triggerMediaAction("skip_ad");
                        hardware.playBeep(1800, 50);
                    } else if (evt.x >= 210 && evt.x <= 286) {
                        network.triggerMediaAction("vol_up");
                        hardware.playBeep(1400, 40);
                    }
                }

            } else if (display.getCurrentPage() == 7) {
                // Settings Page (Page 7 - ALWAYS LAST FEATURE PAGE)
                if (evt.x < 32 || (evt.y < 33 && evt.x < 160)) {
                    display.previousPage();
                } else if (evt.x > 288 || (evt.y < 33 && evt.x >= 160)) {
                    display.nextPage();
                } else if (evt.y >= 33 && evt.y <= 59) {
                    if (evt.x >= 34 && evt.x <= 155) {
                        display.setSettingsTab(0);
                        hardware.playBeep(1200, 30);
                    } else if (evt.x >= 165 && evt.x <= 286) {
                        display.setSettingsTab(1);
                        hardware.playBeep(1200, 30);
                    }
                } else if (display.getSettingsTab() == 0 && evt.y >= 60 && evt.y <= 225) {
                    if (evt.y >= 60 && evt.y <= 84) {
                        touch.startCalibration();
                        Serial.println("[Touch] Settings -> Calibrate Touch");
                    } else if (evt.y >= 86 && evt.y <= 110) {
                        hardware.setAutoBrightnessEnabled(!hardware.isAutoBrightnessEnabled());
                        if (!hardware.isAutoBrightnessEnabled()) hardware.setBacklight(85);
                        hardware.playBeep(1200, 30);
                        Serial.printf("[Touch] Settings -> Auto Brightness: %s\n",
                                      hardware.isAutoBrightnessEnabled() ? "ON" : "OFF");
                    } else if (evt.y >= 112 && evt.y <= 136) {
                        display.openDetailModal(MODAL_BEEP_VOLUME);
                        hardware.playBeep(1400, 40);
                        Serial.println("[Touch] Settings -> Opened Beep Volume Modal");
                    } else {
                        if (evt.x < 160) display.previousPage();
                        else display.nextPage();
                    }
                } else if (display.getSettingsTab() == 1 && evt.y >= 60 && evt.y <= 225) {
                    int col = (evt.x >= 160) ? 1 : 0;
                    int row = (evt.y - 63) / 52;
                    int idx = row * 2 + col;
                    if (idx >= 0 && idx < 6) {
                        switch (idx) {
                            case 0: applyOceanDarkTheme(); break;
                            case 1: applyCyberpunkTheme(); break;
                            case 2: applyForestTheme(); break;
                            case 3: applyCherryTheme(); break;
                            case 4: applyLightDayTheme(); break;
                            case 5: applyRetroGreenTheme(); break;
                        }
                        hardware.playBeep(2000, 40);
                        Serial.printf("[Touch] Settings -> Theme Preset %d applied\n", idx);
                    }
                }
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
