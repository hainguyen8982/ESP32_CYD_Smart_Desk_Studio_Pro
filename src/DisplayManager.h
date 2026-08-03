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
    MODAL_CURRENCY_2
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

    // Fullscreen Chart Detail Modal
    void openDetailModal(DetailModalType type) { currentModal = type; }
    void closeDetailModal() { currentModal = MODAL_NONE; }
    bool isModalOpen() const { return currentModal != MODAL_NONE; }
    DetailModalType getModalType() const { return currentModal; }

    // Month browsing helpers
    void nextCalendarMonth() { calendarMonthOffset++; }
    void prevCalendarMonth() { calendarMonthOffset--; }
    void resetCalendarMonth() { calendarMonthOffset = 0; }
    int16_t getCalendarMonthOffset() const { return calendarMonthOffset; }

private:
    // ── Page renderers ───────────────────────────────────────
    void renderHeader();
    void renderPage0_WeatherClock();
    void renderPage1_LunarCalendar();
    void renderPage2_FinanceGold();
    void renderPage3_PcCpuRam();
    void renderPage4_PcGpuVram();
    void renderPage5_PcNetDisks();
    void renderPage6_DeskUtilities();
    void renderPage7_Settings();
    void renderCalibrationScreen();
    void renderDetailModal();

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

    // ── State ────────────────────────────────────────────────
    TFT_eSPI    tft;
    TFT_eSprite spr;       // Off-screen sprite double-buffer
    uint8_t     currentPage;
    DetailModalType currentModal;
    int16_t     calendarMonthOffset;
    unsigned long lastRenderTime;
    bool        spriteReady;
};

extern DisplayManager display;

#endif // DISPLAY_MANAGER_H
