#include "DeskUtilities.h"
#include "HardwareManager.h"

DeskUtilities deskUtils;

DeskUtilities::DeskUtilities()
    : pomState(POMODORO_STOPPED),
      previousStateBeforePause(POMODORO_WORK),
      workDurationSec(25 * 60),
      breakDurationSec(5 * 60),
      remainingSeconds(25 * 60),
      lastTimerTick(0),
      alarmHour(7),
      alarmMinute(0),
      alarmEnabled(false),
      alarmRinging(false) {
    snprintf(noteText, sizeof(noteText), "Work hard, stay focused!");
}

void DeskUtilities::begin() {
    // Initialized
}

const char* DeskUtilities::getPomodoroStateString() const {
    switch (pomState) {
        case POMODORO_WORK:    return "FOCUSING";
        case POMODORO_BREAK:   return "RESTING";
        case POMODORO_PAUSED:  return "PAUSED";
        case POMODORO_STOPPED:
        default:               return "READY";
    }
}

void DeskUtilities::togglePomodoro() {
    if (pomState == POMODORO_STOPPED) {
        pomState = POMODORO_WORK;
        remainingSeconds = workDurationSec;
        hardware.setRGBColor(COLOR_GREEN);
    } else if (pomState == POMODORO_WORK || pomState == POMODORO_BREAK) {
        previousStateBeforePause = pomState;
        pomState = POMODORO_PAUSED;
        hardware.setRGBColor(COLOR_YELLOW);
    } else if (pomState == POMODORO_PAUSED) {
        pomState = previousStateBeforePause;
        hardware.setRGBColor(pomState == POMODORO_WORK ? COLOR_GREEN : COLOR_CYAN);
    }
    lastTimerTick = millis();
}

void DeskUtilities::resetPomodoro() {
    pomState = POMODORO_STOPPED;
    remainingSeconds = workDurationSec;
    hardware.setRGBColor(COLOR_OFF);
}

void DeskUtilities::update() {
    if (pomState == POMODORO_WORK || pomState == POMODORO_BREAK) {
        if (millis() - lastTimerTick >= 1000) {
            lastTimerTick = millis();
            if (remainingSeconds > 0) {
                remainingSeconds--;
            } else {
                // Switch session
                if (pomState == POMODORO_WORK) {
                    pomState = POMODORO_BREAK;
                    remainingSeconds = breakDurationSec;
                    hardware.playAlarmTune();
                    hardware.setRGBColor(COLOR_CYAN);
                } else {
                    pomState = POMODORO_STOPPED;
                    remainingSeconds = workDurationSec;
                    hardware.playAlarmTune();
                    hardware.setRGBColor(COLOR_OFF);
                }
            }
        }
    }

    if (alarmRinging) {
        static unsigned long lastChime = 0;
        if (millis() - lastChime > 1200) {
            lastChime = millis();
            hardware.playAlarmTune();
            hardware.setRGBColor(COLOR_RED);
        }
    }
}

void DeskUtilities::setAlarm(uint8_t hour, uint8_t minute, bool enable) {
    alarmHour = hour;
    alarmMinute = minute;
    alarmEnabled = enable;
    alarmRinging = false;
}

void DeskUtilities::toggleAlarm() {
    if (alarmRinging) {
        dismissAlarm();
    } else {
        setAlarm(alarmHour, alarmMinute, !alarmEnabled);
    }
}

void DeskUtilities::checkAlarm(uint8_t currentHour, uint8_t currentMinute, uint8_t currentSecond) {
    if (!alarmEnabled) return;
    if (currentHour == alarmHour && currentMinute == alarmMinute && currentSecond == 0) {
        alarmRinging = true;
    }
}

void DeskUtilities::dismissAlarm() {
    alarmRinging = false;
    hardware.stopSound();
    hardware.setRGBColor(COLOR_OFF);
}

void DeskUtilities::setNoteText(const char* note) {
    if (note) {
        snprintf(noteText, sizeof(noteText), "%s", note);
    }
}
