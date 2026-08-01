#ifndef DESK_UTILITIES_H
#define DESK_UTILITIES_H

#include <Arduino.h>

enum PomodoroState {
    POMODORO_STOPPED,
    POMODORO_WORK,
    POMODORO_BREAK,
    POMODORO_PAUSED
};

class DeskUtilities {
public:
    DeskUtilities();
    void begin();
    void update();

    // Pomodoro Timer API
    void togglePomodoro();
    void resetPomodoro();
    PomodoroState getPomodoroState() const { return pomState; }
    uint16_t getPomodoroRemainingSeconds() const { return remainingSeconds; }
    const char* getPomodoroStateString() const;

    // Alarm Clock API
    void setAlarm(uint8_t hour, uint8_t minute, bool enable);
    bool isAlarmEnabled() const { return alarmEnabled; }
    uint8_t getAlarmHour() const { return alarmHour; }
    uint8_t getAlarmMinute() const { return alarmMinute; }
    bool isAlarmRinging() const { return alarmRinging; }
    void dismissAlarm();
    void checkAlarm(uint8_t currentHour, uint8_t currentMinute, uint8_t currentSecond);

    // Desk Note
    void setNoteText(const char* note);
    const char* getNoteText() const { return noteText; }

private:
    // Pomodoro internal
    PomodoroState pomState;
    PomodoroState previousStateBeforePause;
    uint16_t workDurationSec;
    uint16_t breakDurationSec;
    uint16_t remainingSeconds;
    unsigned long lastTimerTick;

    // Alarm internal
    uint8_t alarmHour;
    uint8_t alarmMinute;
    bool alarmEnabled;
    bool alarmRinging;

    // Desk Note internal
    char noteText[128];
};

extern DeskUtilities deskUtils;

#endif // DESK_UTILITIES_H
