#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <Arduino.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include "Config.h"

enum DetailModalType {
    MODAL_NONE = 0,
    MODAL_GOLD_SJC,
    MODAL_CURRENCY_1,
    MODAL_CURRENCY_2,
    MODAL_SET_ALARM,
    MODAL_BEEP_VOLUME
};

class DisplayManager {
public:
    DisplayManager();
    void begin();
    void update();
    void setCurrentPage(uint8_t page);
    uint8_t getCurrentPage() const { return currentPage; }
    void nextPage();
    void previousPage();

    // Fullscreen Chart / Setting Detail Modal
    void openDetailModal(DetailModalType type) { currentModal = type; }
    void closeDetailModal() { currentModal = MODAL_NONE; }
    bool isModalOpen() const { return currentModal != MODAL_NONE; }
    DetailModalType getModalType() const { return currentModal; }

    // Alarm Setting Modal state
    uint8_t getTempAlarmHour() const { return tempAlarmHour; }
    uint8_t getTempAlarmMin() const { return tempAlarmMin; }
    void initTempAlarm(uint8_t h, uint8_t m) { tempAlarmHour = h; tempAlarmMin = m; }
    void adjustTempAlarmHour(int8_t delta) {
        int16_t h = (int16_t)tempAlarmHour + delta;
        if (h < 0) h = 23;
        if (h > 23) h = 0;
        tempAlarmHour = (uint8_t)h;
    }
    void adjustTempAlarmMin(int8_t delta) {
        int16_t m = (int16_t)tempAlarmMin + delta;
        if (m < 0) m = 55;
        if (m > 55) m = 0;
        tempAlarmMin = (uint8_t)m;
    }

    // Month browsing helpers
    void nextCalendarMonth() { calendarMonthOffset++; }
    void prevCalendarMonth() { calendarMonthOffset--; }
    void resetCalendarMonth() { calendarMonthOffset = 0; }
    int16_t getCalendarMonthOffset() const { return calendarMonthOffset; }

    // Media Play/Pause State & Track Info
    bool getMediaPlaying() const { return isMediaPlaying; }
    void togglePlayState() { isMediaPlaying = !isMediaPlaying; }
    void setMediaPlaying(bool p) { isMediaPlaying = p; }
    void setMediaInfo(const char* title, const char* artist) {
        if (title && strlen(title) > 0) snprintf(mediaTitle, sizeof(mediaTitle), "%s", title);
        if (artist && strlen(artist) > 0) snprintf(mediaArtist, sizeof(mediaArtist), "%s", artist);
    }

    // App Launcher Overlay Menu Mode
    void openAppLauncher() { isAppLauncherOpen = true; }
    void closeAppLauncher() { isAppLauncherOpen = false; }
    void toggleAppLauncher() { isAppLauncherOpen = !isAppLauncherOpen; }
    bool isAppLauncherActive() const { return isAppLauncherOpen; }

    // Settings Tab State (0 = System, 1 = Themes)
    uint8_t getSettingsTab() const { return settingsTab; }
    void setSettingsTab(uint8_t tab) { settingsTab = tab; }

private:
    // ── Page renderers ───────────────────────────────────────
    void renderHeader();
    void renderPage0_WeatherClock();
    void renderPage1_LunarCalendar();
    void renderPage2_FinanceGold();
    void renderPage3_PcCpuRam();
    void renderPage4_PcNetDisks();
    void renderPage5_DeskUtilities();
    void renderPage6_MediaControl();
    void renderPage7_Settings();           // Settings ALWAYS last feature page (7)
    void renderAppLauncherOverlay();       // Separate System Overlay Grid Menu
    void renderCalibrationScreen();
    void renderDetailModal();
    void renderSplashScreen();

    // ── UI Widgets ───────────────────────────────────────────
    void drawArcGauge(int16_t cx, int16_t cy, int16_t r, int16_t thick,
                      float pct, uint16_t fg, uint16_t track, const char* label);
    void drawSparkline(int16_t x, int16_t y, int16_t w, int16_t h,
                       const uint8_t* data, uint8_t cnt, uint16_t color);
    void drawFloatSparkline(int16_t x, int16_t y, int16_t w, int16_t h,
                            const float* data, uint8_t cnt, uint16_t color);
    void drawHorizBar(int16_t x, int16_t y, int16_t w, int16_t h,
                      float pct, uint16_t fg);
    void drawSectionTitle(const char* title, uint16_t color);

    // ── Icon drawing (small ~14px, drawn at center cx,cy) ────
    void iconSun(int16_t cx, int16_t cy, uint16_t color);
    void iconCloud(int16_t cx, int16_t cy, uint16_t color);
    void iconRain(int16_t cx, int16_t cy, uint16_t color);
    void iconStorm(int16_t cx, int16_t cy, uint16_t color);
    void iconSnow(int16_t cx, int16_t cy, uint16_t color);
    void iconMist(int16_t cx, int16_t cy, uint16_t color);
    void iconCPU(int16_t cx, int16_t cy, uint16_t color);
    void iconGPU(int16_t cx, int16_t cy, uint16_t color);
    void iconBell(int16_t cx, int16_t cy, uint16_t color);
    void iconGold(int16_t cx, int16_t cy, uint16_t color);
    void iconCal(int16_t cx, int16_t cy, uint16_t color);
    void iconNet(int16_t cx, int16_t cy, uint16_t color);
    void iconPomodoro(int16_t cx, int16_t cy);
    void iconPC(int16_t cx, int16_t cy, uint16_t color);
    void iconLink(int16_t cx, int16_t cy, uint16_t color);

    // Status bar icons & widgets
    void drawWifiSignalIcon(int16_t cx, int16_t cy, int rssi, bool connected);
    void drawWeatherIcon(int16_t cx, int16_t cy, const char* cond);
    void drawMiniWeatherIcon(int16_t cx, int16_t cy, uint8_t type);
    void drawWeatherIconVector(int16_t cx, int16_t cy, uint8_t size, uint8_t type);
    void drawVietnameseAmLich(int16_t cx, int16_t cy, int day, int month, int year);
    void drawVietnameseDuBao3Ngay(int16_t cx, int16_t cy);

    void renderModalSetAlarm();
    void renderModalBeepVolume();

    // ── State ────────────────────────────────────────────────
    TFT_eSPI    tft;
    TFT_eSprite spr;       // Off-screen sprite double-buffer
    uint8_t     currentPage;
    DetailModalType currentModal;
    uint8_t     tempAlarmHour;
    uint8_t     tempAlarmMin;
    int16_t     calendarMonthOffset;
    bool        isMediaPlaying;
    char        mediaTitle[64];
    char        mediaArtist[64];
    int         marqueeOffset;
    bool        isAppLauncherOpen;
    uint8_t     settingsTab;
    unsigned long lastRenderTime;
    bool        spriteReady;
};

extern DisplayManager display;

#endif // DISPLAY_MANAGER_H
