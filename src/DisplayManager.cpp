// ═══════════════════════════════════════════════════════════════════════
//  DisplayManager.cpp — Modern Dark Theme UI for ESP32 CYD 320x240
//  Dark navy palette + neon accents + drawn icons + arc gauges
// ═══════════════════════════════════════════════════════════════════════
#include "DisplayManager.h"
#include "HardwareManager.h"
#include "NetworkManager.h"
#include "PCMonitor.h"
#include "DeskUtilities.h"
#include "TouchManager.h"
#include "vn_lunar.h"
#include "Theme.h"
#include <time.h>

extern const GFXfont FreeSansBold9pt7b;

DisplayManager display;

// Dynamic Theme reference aliases for convenience
#define C_BG        theme.bg
#define C_CARD      theme.card
#define C_CARD2     theme.card
#define C_HDR       theme.hdr

#define C_CYAN      theme.cyan
#define C_ORANGE    theme.orange
#define C_GREEN     theme.green
#define C_GREEN2    theme.green
#define C_YELLOW    theme.yellow
#define C_RED       theme.red
#define C_PURPLE    theme.purple
#define C_PINK      theme.purple

#define C_WHITE     theme.white
#define C_DIM       theme.dim
#define C_VDIM      theme.vdim
#define C_TRACE     theme.trace


// Helper to get page accent color dynamically from current theme
static uint16_t getPageAccent(uint8_t page) {
    switch (page) {
        case 0: return theme.cyan;    // Weather
        case 1: return theme.yellow;  // Calendar
        case 2: return theme.yellow;  // Finance
        case 3: return theme.cyan;    // PC Monitor
        case 4: return theme.green;   // Net & Disk
        case 5: return theme.orange;  // Desk Utilities
        case 6: return theme.cyan;    // Media Control
        case 7: return theme.cyan;    // App Launcher Grid
        case 8: return theme.purple;  // Settings (ALWAYS LAST)
        default: return theme.cyan;
    }
}

// ─────────────────────────────────────────────────────────────────────
//  CONSTRUCTOR / BEGIN / NAVIGATION / UPDATE
// ─────────────────────────────────────────────────────────────────────
DisplayManager::DisplayManager()
    : tft(), spr(&tft), currentPage(0), currentModal(MODAL_NONE), tempAlarmHour(7), tempAlarmMin(0), calendarMonthOffset(0), isMediaPlaying(false), settingsTab(0), lastRenderTime(0), spriteReady(false) {}

void DisplayManager::begin() {
    loadTheme(); // Load saved theme from NVS or default Ocean Dark
    tft.init();
    delay(100);
    tft.setRotation(1);
    tft.invertDisplay(true); // CYD panel requires color inversion (fixes white background -> dark navy, red -> cyan)
    tft.fillScreen(C_BG);

    delay(50);

    Serial.printf("[DisplayManager] Heap: %u free | Largest: %u\n",
                  ESP.getFreeHeap(),
                  heap_caps_get_largest_free_block(MALLOC_CAP_8BIT));

    spr.setColorDepth(16);
    void* p = spr.createSprite(SCREEN_WIDTH, SCREEN_HEIGHT);
    if (!p) {
        Serial.println("[DisplayManager] 16-bit sprite failed -> trying 8-bit...");
        spr.setColorDepth(8);
        p = spr.createSprite(SCREEN_WIDTH, SCREEN_HEIGHT);
    }
    spr.setTextWrap(false);
    spriteReady = (p != nullptr);
    Serial.printf("[DisplayManager] Sprite %s (%d-bit) | Heap: %u\n",
                  spriteReady ? "OK" : "FAIL", spr.getColorDepth(), ESP.getFreeHeap());
    if (!spriteReady) {
        tft.setTextColor(TFT_RED, C_BG);
        tft.drawString("Heap Error!", 80, 110, 4);
    }
}

void DisplayManager::setCurrentPage(uint8_t p) { if (p < TOTAL_PAGES) currentPage = p; }
void DisplayManager::nextPage()     { currentPage = (currentPage + 1) % TOTAL_PAGES; }
void DisplayManager::previousPage() { currentPage = (currentPage + TOTAL_PAGES - 1) % TOTAL_PAGES; }

void DisplayManager::update() {
    if (millis() - lastRenderTime < 33) return;   // ~30 fps cap
    lastRenderTime = millis();
    if (!spriteReady) return;

    // During bootup, render Splash Screen until NetworkManager boot is complete
    if (!network.isBootComplete()) {
        renderSplashScreen();
        spr.pushSprite(0, 0);
        return;
    }

    // During calibration, render calibration screen instead of normal UI
    if (touch.isCalibrating()) {
        renderCalibrationScreen();
        spr.pushSprite(0, 0);
        return;
    }

    // Render Fullscreen Detail Chart Modal Overlay if open
    if (isModalOpen()) {
        renderDetailModal();
        spr.pushSprite(0, 0);
        return;
    }

    spr.fillSprite(C_BG);
    renderHeader();

    if (isAppLauncherOpen) {
        renderAppLauncherOverlay();
    } else {
        switch (currentPage) {
            case 0: renderPage0_WeatherClock();     break;
            case 1: renderPage1_LunarCalendar();    break;
            case 2: renderPage2_FinanceGold();      break;
            case 3: renderPage3_PcCpuRam();         break;
            case 4: renderPage4_PcNetDisks();       break;
            case 5: renderPage5_DeskUtilities();    break;
            case 6: renderPage6_MediaControl();     break;
            case 7: renderPage7_Settings();         break;
            default: renderPage0_WeatherClock();    break;
        }
    }
    spr.pushSprite(0, 0);
}

// ─────────────────────────────────────────────────────────────────────
//  HEADER  (y = 0..27,  height = 28px)
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderHeader() {
    spr.fillRect(0, 0, SCREEN_WIDTH, 28, C_HDR);

    // ── Tiny page icon (top-left, ~14px) ─────────────────────────────
    int ix = 12, iy = 13;
    if (isAppLauncherOpen) {
        // 4 Windows Start-style Squares (Glowing Cyan App Grid Icon)
        spr.fillRect(ix - 6, iy - 6, 5, 5, C_CYAN);
        spr.fillRect(ix + 1, iy - 6, 5, 5, C_CYAN);
        spr.fillRect(ix - 6, iy + 1, 5, 5, C_CYAN);
        spr.fillRect(ix + 1, iy + 1, 5, 5, C_CYAN);
    } else {
        switch (currentPage) {
            case 0: // Weather - Sun
                spr.fillCircle(ix, iy, 4, C_YELLOW);
                spr.drawLine(ix, iy-6, ix, iy-8,   C_YELLOW);
                spr.drawLine(ix, iy+6, ix, iy+8,   C_YELLOW);
                spr.drawLine(ix-6, iy, ix-8, iy,   C_YELLOW);
                spr.drawLine(ix+6, iy, ix+8, iy,   C_YELLOW);
                break;
            case 1: // Calendar
                spr.drawRoundRect(ix-7, iy-6, 14, 12, 1, C_YELLOW);
                spr.drawFastHLine(ix-7, iy-3, 14, C_YELLOW);
                spr.fillRect(ix-4, iy-9, 3, 5, C_YELLOW);
                spr.fillRect(ix+1, iy-9, 3, 5, C_YELLOW);
                break;
            case 2: // Finance - Gold Dollar Coin
                spr.fillCircle(ix, iy, 5, C_YELLOW);
                spr.drawCircle(ix, iy, 5, C_ORANGE);
                break;
            case 3: // PC Monitor - CPU chip
                spr.fillRoundRect(ix-6, iy-6, 12, 12, 1, C_CYAN);
                spr.fillRect(ix-3, iy-3, 6, 6, C_HDR);
                for (int p2 = -3; p2 <= 3; p2 += 3) {
                    spr.fillRect(ix+p2-1, iy-9, 2, 3, C_CYAN);
                    spr.fillRect(ix+p2-1, iy+6, 2, 3, C_CYAN);
                }
                break;
            case 4: // PC Net & Storage - Network up/down arrows
                spr.fillTriangle(ix-6, iy+2, ix-2, iy-6, ix+2, iy+2, C_GREEN);
                spr.fillTriangle(ix+4, iy-2, ix+8, iy+6, ix+12, iy-2, C_GREEN);
                break;
            case 5: // Desk Utilities - Pomodoro tomato
                spr.fillCircle(ix, iy+2, 6, C_RED);
                spr.fillRect(ix-1, iy-5, 2, 4, C_GREEN2);
                spr.fillTriangle(ix, iy-4, ix+5, iy-7, ix+4, iy-2, C_GREEN2);
                break;
            case 6: // Media Control - Play button
                spr.fillRoundRect(ix-6, iy-5, 12, 10, 2, C_CYAN);
                spr.fillTriangle(ix-2, iy-3, ix-2, iy+3, ix+2, iy, C_HDR);
                break;
            case 7: // Settings tuning sliders icon
                spr.fillRoundRect(ix-6, iy-4, 12, 2, 1, C_PURPLE);
                spr.fillCircle(ix-2, iy-3, 2, C_PURPLE);
                spr.fillRoundRect(ix-6, iy+2, 12, 2, 1, C_PURPLE);
                spr.fillCircle(ix+2, iy+3, 2, C_PURPLE);
                break;
        }
    }

    if (isAppLauncherOpen) {
        spr.setTextDatum(ML_DATUM);
        spr.setTextColor(C_DIM, C_HDR);
        spr.drawString("App Launcher", 26, 13, 2);
    } else {
        // ── Page title (8 Feature Pages: 0-7) ──────────────────────────────
        static const char* titles[] = {
            "Weather", "Calendar", "Finance",
            "PC Monitor", "Net & Disk", "Utilities", "Media Ctrl", "Settings"
        };
        spr.setTextDatum(ML_DATUM);
        spr.setTextColor(C_DIM, C_HDR);
        spr.drawString(titles[currentPage], 26, 13, 2);
    }

    // ── Time HH:MM:SS (center at y=13 matching page title and icons) ──
    if (currentPage != 0) {
        time_t now = time(NULL);
        struct tm ti;
        if (now >= 1600000000 && localtime_r(&now, &ti)) {
            char h[3], m[3], s[3];
            snprintf(h, sizeof(h), "%02d", ti.tm_hour);
            snprintf(m, sizeof(m), "%02d", ti.tm_min);
            snprintf(s, sizeof(s), "%02d", ti.tm_sec);

            int wH = spr.textWidth(h, 2);
            int wM = spr.textWidth(m, 2);
            int wS = spr.textWidth(s, 2);
            int wC = spr.textWidth(":", 2);
            int pad = 2; // 2px padding around colon

            int totalW = wH + wC + (pad * 2) + wM + wC + (pad * 2) + wS;
            int x = 160 - totalW / 2;
            int y = 6;  // adjust to align vertically with title and icons

            spr.setTextDatum(TL_DATUM);
            spr.setTextColor(C_WHITE, C_HDR);
            spr.drawString(h, x, y, 2); x += wH + pad;
            spr.drawString(":", x, y, 2); x += wC + pad;
            spr.drawString(m, x, y, 2); x += wM + pad;
            spr.drawString(":", x, y, 2); x += wC + pad;
            spr.drawString(s, x, y, 2);
        }
    }

    // ── Status Bar Header (Tight & Balanced Spacing) ─────────────────
    drawWifiSignalIcon(246, 12, WiFi.RSSI(), network.isConnected());
    iconLink(268, 12, pcMonitor.isConnected() ? C_CYAN : C_VDIM);

    uint16_t acc = getPageAccent(currentPage);
    if (!isAppLauncherOpen) {
        char pageBuf[8];
        snprintf(pageBuf, sizeof(pageBuf), "%d/%d", (int)currentPage + 1, TOTAL_PAGES);
        spr.setTextDatum(MR_DATUM);
        spr.setTextColor(acc, C_HDR);
        spr.drawString(pageBuf, 308, 13, 2);
    }

    // ── Bottom accent line ────────────────────────────────────────────
    spr.drawFastHLine(0, 27, SCREEN_WIDTH, acc);
}

void DisplayManager::iconLink(int16_t cx, int16_t cy, uint16_t color) {
    // Desktop Display Monitor Icon (Height = 13px, Width = 14px)
    spr.fillRoundRect(cx - 7, cy - 6, 14, 9, 2, color);  // Screen bezel
    spr.fillRect(cx - 5, cy - 4, 10, 5, C_BG);           // Inner screen
    if (color != C_VDIM) {
        spr.fillRect(cx - 2, cy - 2, 4, 2, C_WHITE);     // Active screen signal dot
    }
    spr.fillRect(cx - 2, cy + 3, 4, 2, color);           // Stand neck
    spr.fillRoundRect(cx - 5, cy + 5, 10, 2, 1, color);  // Base stand
}

void DisplayManager::drawWeatherIcon(int16_t cx, int16_t cy, const char* cond) {
    if (!cond || cond[0] == '\0') cond = "Clear";
    uint8_t type = 0;
    if (strncmp(cond, "Clouds", 6) == 0) type = 1;
    else if (strncmp(cond, "Rain", 4) == 0 || strncmp(cond, "Drizzle", 7) == 0) type = 2;
    else if (strncmp(cond, "Thunder", 7) == 0) type = 3;

    drawWeatherIconVector(cx, cy, 50, type); // 50px Large Main Weather Icon
}

void DisplayManager::drawMiniWeatherIcon(int16_t cx, int16_t cy, uint8_t type) {
    drawWeatherIconVector(cx, cy, 32, type); // 32px Mini Forecast Icon
}

static void drawSmoothCloud(TFT_eSprite& spr, int16_t cx, int16_t cy, bool isLarge, uint16_t bg) {
    if (isLarge) {
        // 1. Draw outer 2px white cloud silhouette
        spr.fillCircle(cx - 9, cy + 2, 9, C_WHITE);
        spr.fillCircle(cx + 9, cy + 3, 7, C_WHITE);
        spr.fillCircle(cx, cy - 5, 11, C_WHITE);
        spr.fillRoundRect(cx - 17, cy - 1, 34, 12, 4, C_WHITE);

        // 2. Erase inner body with background color (2px offset) to form crisp hollow 2px white border
        spr.fillCircle(cx - 9, cy + 2, 7, bg);
        spr.fillCircle(cx + 9, cy + 3, 5, bg);
        spr.fillCircle(cx, cy - 5, 9, bg);
        spr.fillRoundRect(cx - 15, cy + 1, 30, 8, 3, bg);
    } else {
        // 32px Mini Cloud
        spr.fillCircle(cx - 5, cy + 1, 5, C_WHITE);
        spr.fillCircle(cx + 5, cy + 2, 4, C_WHITE);
        spr.fillCircle(cx, cy - 3, 6, C_WHITE);
        spr.fillRoundRect(cx - 9, cy - 1, 18, 7, 3, C_WHITE);

        spr.fillCircle(cx - 5, cy + 1, 3, bg);
        spr.fillCircle(cx + 5, cy + 2, 2, bg);
        spr.fillCircle(cx, cy - 3, 4, bg);
        spr.fillRoundRect(cx - 7, cy + 1, 14, 4, 2, bg);
    }
}

static void drawSlantedRaindrop(TFT_eSprite& spr, int16_t x, int16_t y) {
    // Realistic slanted teardrop raindrop (pointing down-left)
    spr.fillCircle(x - 2, y + 4, 3, C_CYAN);
    spr.fillTriangle(x - 4, y + 3, x + 1, y + 5, x + 2, y - 2, C_CYAN);
}

void DisplayManager::drawWeatherIconVector(int16_t cx, int16_t cy, uint8_t size, uint8_t type) {
    if (size >= 48) {
        // ── LARGE 50px VECTOR OUTLINE LINE-ART WEATHER ICON ──────────────────
        switch (type) {
            case 0: // 50px Sun
                spr.fillCircle(cx, cy, 11, C_YELLOW);
                spr.drawCircle(cx, cy, 11, C_ORANGE);
                static const int8_t ix[] = { 0, 9,13, 9, 0,-9,-13,-9};
                static const int8_t iy[] = {-13,-9, 0, 9,13, 9,  0,-9};
                static const int8_t ox[] = { 0,16,21,16, 0,-16,-21,-16};
                static const int8_t oy[] = {-21,-16, 0,16,21,16,  0,-16};
                for (int i = 0; i < 8; i++) {
                    spr.drawLine(cx+ix[i], cy+iy[i], cx+ox[i], cy+oy[i], C_YELLOW);
                    spr.drawLine(cx+ix[i]+1, cy+iy[i], cx+ox[i]+1, cy+oy[i], C_YELLOW);
                }
                break;

            case 1: // 50px Sun + Cloud (White outline cloud with sun peeking)
                spr.fillCircle(cx + 8, cy - 8, 7, C_YELLOW);
                spr.drawCircle(cx + 8, cy - 8, 7, C_ORANGE);
                spr.drawLine(cx + 14, cy - 14, cx + 18, cy - 18, C_YELLOW);
                spr.drawLine(cx + 8, cy - 17, cx + 8, cy - 21, C_YELLOW);
                spr.drawLine(cx + 17, cy - 8, cx + 21, cy - 8, C_YELLOW);

                drawSmoothCloud(spr, cx - 2, cy + 2, true, C_CARD);
                break;

            case 2: // 50px Rain Cloud (White outline cloud + Blue Teardrop Raindrops 💧)
                drawSmoothCloud(spr, cx, cy - 4, true, C_CARD);
                // 2 Slanted Teardrop Raindrops (like reference image)
                drawSlantedRaindrop(spr, cx - 6, cy + 10);
                drawSlantedRaindrop(spr, cx + 4, cy + 10);
                break;

            default: // 50px Thunderstorm
                drawSmoothCloud(spr, cx, cy - 4, true, C_CARD);
                // Lightning bolt
                spr.drawLine(cx - 2, cy + 6, cx - 6, cy + 11, C_YELLOW);
                spr.drawLine(cx - 6, cy + 11, cx + 2, cy + 11, C_YELLOW);
                spr.drawLine(cx + 2, cy + 11, cx - 3, cy + 18, C_YELLOW);
                break;
        }
    } else {
        // ── 32px VECTOR OUTLINE LINE-ART WEATHER ICON ───────────────────
        switch (type) {
            case 0: // 32px Sun
                spr.fillCircle(cx, cy, 6, C_YELLOW);
                static const int8_t ix[] = { 0, 5, 7, 5, 0,-5,-7,-5};
                static const int8_t iy[] = {-7,-5, 0, 5, 7, 5, 0,-5};
                static const int8_t ox[] = { 0, 9,12, 9, 0,-9,-12,-9};
                static const int8_t oy[] = {-12,-9, 0, 9,12, 9, 0,-9};
                for (int i = 0; i < 8; i++) {
                    spr.drawLine(cx+ix[i], cy+iy[i], cx+ox[i], cy+oy[i], C_YELLOW);
                }
                break;

            case 1: // 32px Sun + Cloud
                spr.fillCircle(cx + 5, cy - 5, 4, C_YELLOW);
                drawSmoothCloud(spr, cx - 1, cy + 2, false, C_CARD);
                break;

            case 2: // 32px Rain Cloud
                drawSmoothCloud(spr, cx, cy - 3, false, C_CARD);
                drawSlantedRaindrop(spr, cx - 3, cy + 7);
                drawSlantedRaindrop(spr, cx + 4, cy + 7);
                break;

            default: // 32px Thunderstorm
                drawSmoothCloud(spr, cx, cy - 3, false, C_CARD);
                spr.drawLine(cx - 1, cy + 5, cx - 4, cy + 9, C_YELLOW);
                spr.drawLine(cx - 4, cy + 9, cx + 1, cy + 9, C_YELLOW);
                spr.drawLine(cx + 1, cy + 9, cx - 2, cy + 13, C_YELLOW);
                break;
        }
    }
}

void DisplayManager::drawVietnameseAmLich(int16_t cx, int16_t cy, int day, int month, int year) {
    char lunarBuf[40];
    snprintf(lunarBuf, sizeof(lunarBuf), "AM LICH: %02d/%02d/%04d", day, month, year);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_YELLOW, C_BG);
    spr.drawString(lunarBuf, cx, cy, 2); // 100% clean unaccented Font 2
}

void DisplayManager::drawVietnameseDuBao3Ngay(int16_t cx, int16_t cy) {
    const char* str = "DU BAO 3 NGAY";
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString(str, cx, cy, 2); // 100% clean unaccented Font 2
}

void DisplayManager::drawWifiSignalIcon(int16_t cx, int16_t cy, int rssi, bool connected) {
    if (!connected) {
        spr.drawLine(cx - 4, cy - 4, cx + 4, cy + 4, C_RED);
        spr.drawLine(cx + 4, cy - 4, cx - 4, cy + 4, C_RED);
        return;
    }

    uint8_t bars = 3;
    if (rssi < -80) bars = 1;
    else if (rssi < -68) bars = 2;

    uint16_t color = (bars >= 2) ? C_GREEN : C_YELLOW;

    // 3 bold vertical signal strength bars (Equal Height = 13px, matching Link Icon)
    spr.fillRect(cx - 6, cy + 1, 3, 5,  (bars >= 1) ? color : C_VDIM);
    spr.fillRect(cx - 1, cy - 3, 3, 9,  (bars >= 2) ? color : C_VDIM);
    spr.fillRect(cx + 4, cy - 7, 3, 13, (bars >= 3) ? color : C_VDIM);
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 0 — WEATHER CLOCK
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage0_WeatherClock() {
    time_t now = time(NULL);
    struct tm ti;
    bool valid = (now >= 1600000000 && localtime_r(&now, &ti));

    // ── Giant HH:MM clock (drawn clean & transparent on C_BG) ─────────
    char clockStr[8];
    if (valid) {
        snprintf(clockStr, sizeof(clockStr), "%02d:%02d", ti.tm_hour, ti.tm_min);
    } else {
        strcpy(clockStr, "00:00");
    }
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString(clockStr, 160, 66, 6);  // Clean, bold, centered Font 6

    // ── Date row ──────────────────────────────────────────────────────
    static const char* wdays[] = {"CN", "T2", "T3", "T4", "T5", "T6", "T7"};
    char dateBuf[32];
    if (valid) {
        snprintf(dateBuf, sizeof(dateBuf), "%s, %02d/%02d/%04d",
                 wdays[ti.tm_wday], ti.tm_mday, ti.tm_mon + 1, ti.tm_year + 1900);
    } else {
        strcpy(dateBuf, "--- , --/--/----");
    }
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_WHITE, C_BG);
    spr.drawString(dateBuf, 160, 100, 2);

    // ── Lunar date row ────────────────────────────────────────────────
    vn_lunar lunar;
    if (valid) {
        lunar.convertSolar2Lunar(ti.tm_mday, ti.tm_mon + 1, ti.tm_year + 1900);
    } else {
        lunar.convertSolar2Lunar(1, 1, 2026);
    }
    drawVietnameseAmLich(160, 115, lunar.get_lunar_dd(), lunar.get_lunar_mm(), lunar.get_lunar_yy());

    // ── Weather card (Spacious width = 310px, x = 5) ─────────────────
    spr.fillRoundRect(5, 134, 310, 102, 8, C_CARD);
    spr.drawRoundRect(5, 134, 310, 102, 8, C_CYAN);  // cyan border

    const WeatherData& w = network.getWeather();

    // ── Left Side: Current Weather (x = 5..145) ──────────────────────
    drawWeatherIcon(38, 185, w.main);

    char tempStr[16];
    snprintf(tempStr, sizeof(tempStr), "%.1f", w.temp);
    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.drawString(tempStr, 64, 140, 4);  // Font 4 ~26px
    int tw = spr.textWidth(tempStr, 4);
    spr.drawCircle(64 + tw + 3, 143, 2, C_ORANGE); // ° degree circle
    spr.drawString("C", 64 + tw + 8, 140, 4);

    spr.setTextColor(C_WHITE, C_CARD);
    spr.drawString(w.valid ? w.main : "Sunny", 64, 168, 2);

    char humStr[24], windStr[24], cityStr[36];
    snprintf(humStr, sizeof(humStr), "Hum: %d%%", w.humidity);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString(humStr, 64, 186, 1);

    snprintf(windStr, sizeof(windStr), "Wind: %.1fkm/h", w.windSpeed);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString(windStr, 64, 199, 1);

    snprintf(cityStr, sizeof(cityStr), "@ %s", w.valid ? w.city : DEFAULT_CITY);
    spr.setTextColor(C_DIM, C_CARD);
    spr.drawString(cityStr, 64, 213, 1);

    // Clean spatial gap divider between left and right sections (NO line overlap or theme color issues)

    // ── Right Side: 3-Day Forecast (x = 158..310) ────────────────────
    drawVietnameseDuBao3Ngay(232, 140);

    if (w.valid && (w.forecastTempMin[0] != 0 || w.forecastTempMax[0] != 0)) {
        for (int i = 0; i < 3; i++) {
            int cx = 180 + i * 52;  // Columns at x = 180, 232, 284

            // Calendar Date DD/MM label
            struct tm dayTm = ti;
            dayTm.tm_mday += i;
            mktime(&dayTm); // normalize tm_mday / tm_mon
            char dStr[10];
            snprintf(dStr, sizeof(dStr), "%02d/%02d", dayTm.tm_mday, dayTm.tm_mon + 1);

            spr.setTextDatum(TC_DATUM);
            spr.setTextColor(C_YELLOW, C_CARD);
            spr.drawString(dStr, cx, 158, 1);

            // 32px Multi-tone Weather Icon
            uint8_t iconType = w.forecastCode[i];
            drawMiniWeatherIcon(cx, 186, iconType);

            // Temperature range
            char fBuf[16];
            snprintf(fBuf, sizeof(fBuf), "%.0f/%.0fC", w.forecastTempMin[i], w.forecastTempMax[i]);
            spr.setTextColor(C_WHITE, C_CARD);
            spr.drawString(fBuf, cx, 211, 1);
        }
    }
}


// ─────────────────────────────────────────────────────────────────────
//  PAGE 1 — LUNAR CALENDAR
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage1_LunarCalendar() {
    time_t now = time(NULL);
    struct tm ti;
    bool valid = (now >= 1600000000 && localtime_r(&now, &ti));

    int baseYear  = valid ? ti.tm_year + 1900 : 2026;
    int baseMonth = valid ? ti.tm_mon : 7; // 0-indexed month

    // Calculate Month and Year dynamically with calendarMonthOffset
    int totalMonths = baseYear * 12 + baseMonth + calendarMonthOffset;
    int curYear  = totalMonths / 12;
    int curMonth = (totalMonths % 12) + 1;
    int curDay   = (calendarMonthOffset == 0 && valid) ? ti.tm_mday : -1;

    // ── Month Title & Touch Navigation Buttons ─────────────────────────
    char titleBuf[32];
    snprintf(titleBuf, sizeof(titleBuf), "THANG %02d / %04d", curMonth, curYear);

    // Left Touch Button [ << ] (x = 55..95, y = 30..49)
    spr.fillRoundRect(55, 30, 40, 19, 4, C_CARD);
    spr.drawRoundRect(55, 30, 40, 19, 4, C_DIM);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("<<", 75, 39, 2);

    // Center Month Title (x = 160, y = 40)
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_YELLOW, C_BG);
    spr.drawString(titleBuf, 160, 40, 2);
    spr.drawString(titleBuf, 161, 40, 2); // bold emphasis

    // Right Touch Button [ >> ] (x = 225..265, y = 30..49)
    spr.fillRoundRect(225, 30, 40, 19, 4, C_CARD);
    spr.drawRoundRect(225, 30, 40, 19, 4, C_DIM);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString(">>", 245, 39, 2);

    // ── Day-of-week headers ───────────────────────────────────────────
    static const char* hdr[] = {"CN","T2","T3","T4","T5","T6","T7"};
    for (int c = 0; c < 7; c++) {
        int hx = 9 + c * 44 + 20;  // center of each column
        spr.setTextDatum(TC_DATUM);
        spr.setTextColor(c == 0 ? C_RED : C_DIM, C_BG);
        spr.drawString(hdr[c], hx, 52, 2);
    }

    // ── Compute first weekday of month ────────────────────────────────
    struct tm fm = {};
    fm.tm_year = curYear - 1900;
    fm.tm_mon  = curMonth - 1;
    fm.tm_mday = 1;
    mktime(&fm);
    int startCol = fm.tm_wday;  // 0=Sun

    // Days in month
    auto isLeap = [](int y) { return y%4==0 && (y%100!=0 || y%400==0); };
    int dim;
    switch (curMonth) {
        case 2:  dim = isLeap(curYear) ? 29 : 28; break;
        case 4: case 6: case 9: case 11: dim = 30; break;
        default: dim = 31; break;
    }

    // ── Grid 7×6 cells (Side-by-side Solar & Lunar layout) ─────────────
    int day = 1;
    vn_lunar lunar;
    for (int row = 0; row < 6 && day <= dim; row++) {
        for (int col = 0; col < 7; col++) {
            if (row == 0 && col < startCol) continue;
            if (day > dim) break;

            int cx = 9  + col * 44;
            int cy = 68 + row * 27;
            bool isToday   = (day == curDay);
            bool isSunday  = (col == 0);

            // Cell background
            uint16_t bg  = isToday ? C_ORANGE : C_CARD;
            uint16_t fg  = isToday ? C_WHITE  : (isSunday ? C_RED : C_WHITE);
            uint16_t lfg = isToday ? C_WHITE  : C_YELLOW;

            spr.fillRoundRect(cx + 1, cy + 1, 42, 25, 3, bg);
            spr.drawRoundRect(cx + 1, cy + 1, 42, 25, 3, isToday ? C_YELLOW : C_DIM);

            // ── Tightly bound Solar + Lunar pair centered in cell ───────
            char solStr[8], lunStr[8];
            snprintf(solStr, sizeof(solStr), "%d", day);
            lunar.convertSolar2Lunar(day, curMonth, curYear);
            snprintf(lunStr, sizeof(lunStr), "%d", lunar.get_lunar_dd());

            int solW = spr.textWidth(solStr, 2); // Solar width (Font 2 ~16px)
            int lunW = spr.textWidth(lunStr, 1); // Lunar width (Font 1 ~8px)
            int gap = 2;
            int totalW = solW + gap + lunW;

            // Center pair in cell (cell width = 42px, center offset = 22px)
            int startX = cx + 22 - (totalW / 2);

            // Solar Date Number (Font 2 ~16px)
            spr.setTextDatum(TL_DATUM);
            spr.setTextColor(fg, bg);
            spr.drawString(solStr, startX, cy + 4, 2);

            // Lunar Date Number (Font 1 ~8px, superscript right next to Solar)
            spr.setTextDatum(TL_DATUM);
            spr.setTextColor(lfg, bg);
            spr.drawString(lunStr, startX + solW + gap, cy + 3, 1);

            day++;
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 2 — FINANCE & GOLD
// ─────────────────────────────────────────────────────────────────────
static void formatWithCommas(char* out, size_t size, float val) {
    long n = (long)val;
    if (n >= 1000000) {
        snprintf(out, size, "%ld,%03ld,%03ld", n / 1000000, (n / 1000) % 1000, n % 1000);
    } else if (n >= 1000) {
        snprintf(out, size, "%ld,%03ld", n / 1000, n % 1000);
    } else {
        if (val < 1000 && (val - (int)val > 0.05f)) {
            snprintf(out, size, "%.1f", val);
        } else {
            snprintf(out, size, "%ld", n);
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 2 — FINANCE & GOLD
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage2_FinanceGold() {
    // Title without line underneath as requested
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_YELLOW, C_BG);
    spr.drawString("TAI CHINH & GIA VANG SJC", 160, 34, 2);

    const GoldData&    g  = network.getGold();
    const ExchangeData& ex = network.getExchange();

    // ── SJC Gold card ─────────────────────────────────────────────────
    spr.fillRoundRect(10, 54, 300, 80, 7, C_CARD);
    spr.drawRoundRect(10, 54, 300, 80, 7, C_YELLOW);

    // Gold bar icon
    iconGold(40, 94, C_YELLOW);

    // Vertical divider
    spr.drawFastVLine(68, 64, 60, C_TRACE);

    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("VANG SJC (Trieu VND/Luong)", 76, 62, 1);

    char sjcBuf[48];
    snprintf(sjcBuf, sizeof(sjcBuf), "Mua: %.2fM", g.sjcBuy);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.drawString(sjcBuf, 76, 74, 2);

    snprintf(sjcBuf, sizeof(sjcBuf), "Ban: %.2fM", g.sjcSell);
    spr.setTextColor(g.sjcDelta >= 0 ? C_GREEN : C_RED, C_CARD);
    spr.drawString(sjcBuf, 76, 93, 2);

    char xauBuf[32];
    snprintf(xauBuf, sizeof(xauBuf), "XAUUSD: $%.0f", g.xauUsd);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString(xauBuf, 76, 112, 1);

    // Delta badge
    if (g.valid) {
        char dBuf[16];
        snprintf(dBuf, sizeof(dBuf), "%+.2f", g.sjcDelta);
        uint16_t dc = (g.sjcDelta >= 0) ? C_GREEN : C_RED;
        spr.fillRoundRect(245, 60, 58, 18, 4, dc);
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_BG, dc);
        spr.drawString(dBuf, 274, 69, 1);

        // ── 7-Day SJC Gold History Trend Chart ───────────────────────────
        int gx = 202, gy = 84, gw = 101, gh = 42;
        spr.setTextDatum(TL_DATUM);
        spr.setTextColor(C_DIM, C_CARD);
        spr.drawString("BD 7 NGAY", gx, gy, 1);

        uint16_t trendColor = (g.history7Days[6] >= g.history7Days[0]) ? C_GREEN : C_RED;
        drawFloatSparkline(gx, gy + 11, gw, gh - 11, g.history7Days, 7, trendColor);
    }

    // ── Exchange card ─────────────────────────────────────────────────
    spr.fillRoundRect(10, 144, 300, 88, 7, C_CARD);
    spr.drawRoundRect(10, 144, 300, 88, 7, C_CYAN);

    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString("TY GIA NGOAI TE (VND)", 20, 152, 1);

    const char* c1 = ex.cur1Code[0] ? ex.cur1Code : "USD";
    const char* c2 = ex.cur2Code[0] ? ex.cur2Code : "EUR";

    char val1[16], val2[16];
    formatWithCommas(val1, sizeof(val1), ex.cur1Rate);
    formatWithCommas(val2, sizeof(val2), ex.cur2Rate);

    char buf1[32], buf2[32];
    snprintf(buf1, sizeof(buf1), "%s: %s", c1, val1);
    snprintf(buf2, sizeof(buf2), "%s: %s", c2, val2);

    spr.setTextColor(C_WHITE, C_CARD);
    spr.drawString(buf1, 20, 168, 2);
    spr.drawString(buf2, 20, 194, 2);

    // ── 2 Currency Trend Sparkline Charts on Right Side ───────────────
    if (ex.valid) {
        uint16_t color1 = (ex.cur1History7[6] >= ex.cur1History7[0]) ? C_GREEN : C_RED;
        drawFloatSparkline(180, 166, 120, 20, ex.cur1History7, 7, color1);

        uint16_t color2 = (ex.cur2History7[6] >= ex.cur2History7[0]) ? C_GREEN : C_RED;
        drawFloatSparkline(180, 192, 120, 20, ex.cur2History7, 7, color2);
    }
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 3 — PC MONITOR: CPU & RAM
// ─────────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────
//  PAGE 3 — PC MONITOR: CPU + GPU arcs + RAM + VRAM bars + History
//  Phương Án C: 2 arc lớn (CPU,GPU) + 2 bar nhỏ (RAM,VRAM) + sparkline
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage3_PcCpuRam() {
    drawSectionTitle("PC MONITOR", C_CYAN);

    if (!pcMonitor.isConnected()) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_DIM, C_BG);
        spr.drawString("Waiting for PC connection...", 160, 120, 2);
        spr.drawString("Run pc_monitor.py on Windows",  160, 140, 2);
        iconPC(160, 92, C_VDIM);
        return;
    }

    // ── Two arc gauges: CPU (left) + GPU (right), r=42 ───────────────
    drawArcGauge( 80, 106, 42, 8, pcMonitor.getCpuLoad(), C_CYAN,   C_TRACE, "CPU");
    drawArcGauge(240, 106, 42, 8, pcMonitor.getGpuLoad(), C_ORANGE, C_TRACE, "GPU");

    // ── RAM bar ───────────────────────────────────────────────────────
    int bar1Y = 158;
    spr.fillRoundRect(10, bar1Y, 300, 20, 4, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.drawString("RAM", 14, bar1Y + 10, 1);
    drawHorizBar(38, bar1Y + 4, 218, 12, pcMonitor.getRamLoad(), C_ORANGE);
    char ramBuf[8]; snprintf(ramBuf, sizeof(ramBuf), "%d%%", (int)pcMonitor.getRamLoad());
    spr.setTextDatum(MR_DATUM);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.drawString(ramBuf, 304, bar1Y + 10, 1);

    // ── VRAM bar ──────────────────────────────────────────────────────
    int bar2Y = 182;
    spr.fillRoundRect(10, bar2Y, 300, 20, 4, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.drawString("VRAM", 14, bar2Y + 10, 1);
    drawHorizBar(42, bar2Y + 4, 214, 12, pcMonitor.getVramLoad(), C_GREEN);
    char vramBuf[8]; snprintf(vramBuf, sizeof(vramBuf), "%d%%", (int)pcMonitor.getVramLoad());
    spr.setTextDatum(MR_DATUM);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.drawString(vramBuf, 304, bar2Y + 10, 1);

    // ── CPU history sparkline ─────────────────────────────────────────
    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_VDIM, C_BG);
    spr.drawString("CPU history", 14, 205, 1);
    drawSparkline(14, 214, 292, 24, pcMonitor.getCpuHistory(), PCMonitor::HISTORY_SIZE, C_CYAN);
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 4 — PC NETWORK & DISKS  (was page 5)
// ─────────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────
//  PAGE 4 — PC NETWORK & STORAGE
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage4_PcNetDisks() {
    drawSectionTitle("NETWORK & STORAGE", C_GREEN);

    if (!pcMonitor.isConnected()) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_DIM, C_BG);
        spr.drawString("Waiting for PC connection...", 160, 130, 2);
        return;
    }

    // ── 1. NETWORK CARD (y = 34 to 94, h = 60px) ──────────────────────
    spr.fillRoundRect(10, 34, 300, 60, 6, C_CARD);
    spr.drawRoundRect(10, 34, 300, 60, 6, C_TRACE);
    
    // Header label for Network
    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_DIM, C_CARD);
    spr.drawString("NETWORK SPEEDS", 20, 38, 1);

    // DOWNLOAD block (left side)
    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.drawString("\x19 DOWN", 20, 52, 1);
    char dnBuf[20];
    uint32_t dnSpeed = pcMonitor.getNetDownSpeed();
    if (dnSpeed >= 1024) {
        snprintf(dnBuf, sizeof(dnBuf), "%.1f MB/s", dnSpeed / 1024.0f);
    } else {
        snprintf(dnBuf, sizeof(dnBuf), "%u KB/s", dnSpeed);
    }
    spr.setTextColor(C_WHITE, C_CARD);
    spr.drawString(dnBuf, 20, 66, 2);

    // Download Live Traffic Line Chart
    drawSparkline(95, 52, 55, 30, pcMonitor.getNetDownHistory(), PCMonitor::HISTORY_SIZE, C_GREEN);

    // Symmetric Vertical divider line at exact center of card (x = 160)
    spr.drawFastVLine(160, 46, 42, C_TRACE);

    // UPLOAD block (right side)
    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString("\x18 UP", 175, 52, 1);
    char upBuf[20];
    uint32_t upSpeed = pcMonitor.getNetUpSpeed();
    if (upSpeed >= 1024) {
        snprintf(upBuf, sizeof(upBuf), "%.1f MB/s", upSpeed / 1024.0f);
    } else {
        snprintf(upBuf, sizeof(upBuf), "%u KB/s", upSpeed);
    }
    spr.setTextColor(C_WHITE, C_CARD);
    spr.drawString(upBuf, 175, 66, 2);

    // Upload Live Traffic Line Chart
    drawSparkline(245, 52, 55, 30, pcMonitor.getNetUpHistory(), PCMonitor::HISTORY_SIZE, C_CYAN);

    // ── 2. STORAGE DISKS PANEL (y = 100 to 234, h = 134px) ────────────
    spr.fillRoundRect(10, 100, 300, 134, 6, C_CARD);
    spr.drawRoundRect(10, 100, 300, 134, 6, C_TRACE);

    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_DIM, C_CARD);
    spr.drawString("STORAGE DRIVES", 20, 105, 1);

    uint8_t cnt = pcMonitor.getDiskCount();
    if (cnt == 0) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_VDIM, C_CARD);
        spr.drawString("No drives detected", 160, 165, 2);
        return;
    }

    const DiskInfo* disks = pcMonitor.getDisks();
    uint8_t show = (cnt > 4) ? 4 : cnt; // Max 4 drives for crisp spacing

    int startY = 120;
    int availH = 228 - startY;
    int rowH   = availH / show;

    for (uint8_t i = 0; i < show; i++) {
        int ry = startY + i * rowH;
        int my = ry + rowH / 2;

        // Drive badge box [ C: ]
        spr.fillRoundRect(18, my - 9, 30, 18, 3, C_BG);
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_YELLOW, C_BG);
        char dName[8];
        snprintf(dName, sizeof(dName), "%s:", disks[i].name);
        spr.drawString(dName, 33, my, 2);

        // Progress bar with dynamic coloring
        uint8_t pct = disks[i].usedPercent;
        uint16_t barColor = C_GREEN;
        if      (pct >= 85) barColor = C_RED;
        else if (pct >= 65) barColor = C_ORANGE;

        int barX = 56;
        int barW = 198;
        int barH = 12;
        drawHorizBar(barX, my - barH / 2, barW, barH, pct, barColor);

        // Usage percentage
        char pctStr[8];
        snprintf(pctStr, sizeof(pctStr), "%d%%", pct);
        spr.setTextDatum(MR_DATUM);
        spr.setTextColor(barColor, C_CARD);
        spr.drawString(pctStr, 298, my, 2);
    }
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 5 — POMODORO & DESK UTILITIES
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage5_DeskUtilities() {
    drawSectionTitle("DESK UTILITIES", C_ORANGE);

    // ── 1. TOP CARD: ALARM CLOCK BAR (x = 10..310, y = 34..72, h = 38) ──
    uint16_t alarmCardBg     = hexToRGB565("#94A3B8"); // Rich metallic slate grey card background
    uint16_t alarmCardBorder = hexToRGB565("#64748B"); // Smooth rounded border

    spr.fillRoundRect(10, 34, 300, 38, 9, alarmCardBg);
    spr.drawRoundRect(10, 34, 300, 38, 9, alarmCardBorder);

    iconBell(22, 53, hexToRGB565("#EA580C"));
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(hexToRGB565("#0F172A"), alarmCardBg);
    spr.drawString("ALARM CLOCK:", 36, 53, 2); // Larger Font 2 title text!

    // Bold Alarm Time Digits using Font 4 (26px bold font)
    char alarmTimeStr[12];
    snprintf(alarmTimeStr, sizeof(alarmTimeStr), "%02d:%02d",
             deskUtils.getAlarmHour(), deskUtils.getAlarmMinute());
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(hexToRGB565("#0F172A"), alarmCardBg);
    spr.drawString(alarmTimeStr, 142, 55, 4); // Heavy bold 26px font shifted down 2px!

    // Clean Toggle Pill Switch Button
    bool aOn = deskUtils.isAlarmEnabled();
    uint16_t pillBg = aOn ? C_GREEN : hexToRGB565("#334155");
    uint16_t pillFg = aOn ? C_BG    : C_WHITE;
    spr.fillRoundRect(220, 41, 82, 24, 12, pillBg);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(pillFg, pillBg);
    spr.drawString(aOn ? "ALARM ON" : "ALARM OFF", 261, 53, 1);

    // ── 2. CENTER HERO: EXPANDED POMODORO CARD (x = 10..310, y = 78..232, h = 154) ──
    spr.fillRoundRect(10, 78, 300, 154, 8, C_CARD);

    uint16_t remSec   = deskUtils.getPomodoroRemainingSeconds();
    uint16_t totalSec = 25 * 60;  // default 25 min session
    float    pct      = (float)remSec / totalSec * 100.0f;
    pct = constrain(pct, 0.0f, 100.0f);

    int cx = 160, cy = 155;

    // Track background ring
    spr.drawArc(cx, cy, 62, 49, 0, 359, C_TRACE, C_CARD, false);

    // 🌟 SEAMLESS TRIPLE NEON ARC GAUGE (Outer Yellow 2px + Middle Orange 9px + Inner Yellow 2px) 🌟
    uint16_t darkRingColor = (remSec < 300) ? C_GREEN : C_ORANGE;
    uint16_t paleYellow    = hexToRGB565("#FFE880"); // Pale bright yellow
    uint32_t endDeg = (uint32_t)(pct * 3.6f);
    if (endDeg > 0) {
        uint32_t deg = min(endDeg, (uint32_t)359);
        // 1. Thin Outer Yellow Ring (r = 62..60, 2px)
        spr.drawArc(cx, cy, 62, 60, 0, deg, paleYellow, C_CARD, false);
        // 2. Middle Orange Ring (r = 60..51, 9px)
        spr.drawArc(cx, cy, 60, 51, 0, deg, darkRingColor, C_CARD, false);
        // 3. Thin Inner Yellow Ring (r = 51..49, 2px)
        spr.drawArc(cx, cy, 51, 49, 0, deg, paleYellow, C_CARD, false);
    }

    // Tomato Icon inside ring above digits
    iconPomodoro(cx, cy - 28);

    // Digital Timer Digits inside ring (Font 4: 26px bold font)
    uint16_t mins = remSec / 60;
    uint16_t secs = remSec % 60;
    char timeStr[8];
    snprintf(timeStr, sizeof(timeStr), "%02d:%02d", mins, secs);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(paleYellow, C_CARD);
    spr.drawString(timeStr, cx, cy - 2, 4);

    // Clean Status Pill Badge inside ring
    spr.fillRoundRect(cx - 30, cy + 18, 60, 16, 8, C_BG);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_YELLOW, C_BG);
    spr.drawString(deskUtils.getPomodoroStateString(), cx, cy + 26, 1);

    // Alarm ringing overlay flash
    if (deskUtils.isAlarmRinging()) {
        uint16_t flash = (millis() / 300) % 2 ? C_RED : C_BG;
        spr.drawRoundRect(10, 34, 300, 38, 9, flash);
    }
}

// ─────────────────────────────────────────────────────────────────────
//  UI WIDGETS
// ─────────────────────────────────────────────────────────────────────

void DisplayManager::drawSectionTitle(const char* title, uint16_t color) {
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(color, C_BG);
    spr.drawString(title, 160, 34, 2);
    // underline removed — header color already distinguishes each page
}

void DisplayManager::drawArcGauge(int16_t cx, int16_t cy, int16_t r, int16_t thick,
                                   float pct, uint16_t fg, uint16_t track, const char* label) {
    pct = constrain(pct, 0.0f, 100.0f);

    // Background track (full ring)
    spr.drawArc(cx, cy, r, r - thick, 0, 359, track, C_BG, false);

    // Progress arc (0° = top, clockwise)
    uint32_t endDeg = (uint32_t)(pct * 3.59f);  // 0-359
    if (endDeg > 0)
        spr.drawArc(cx, cy, r, r - thick, 0, min(endDeg, (uint32_t)359), fg, C_BG, false);

    // Center: percentage text
    char buf[8];
    snprintf(buf, sizeof(buf), "%.0f", pct);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(fg, C_BG);
    spr.drawString(buf, cx, cy - 10, 4);

    spr.setTextColor(C_DIM, C_BG);
    spr.drawString("%", cx + 16, cy - 6, 2);

    // Label below center
    spr.setTextColor(C_DIM, C_BG);
    spr.drawString(label, cx, cy + 14, 1);
}

void DisplayManager::drawSparkline(int16_t x, int16_t y, int16_t w, int16_t h,
                                    const uint8_t* data, uint8_t cnt, uint16_t color) {
    spr.fillRoundRect(x, y, w, h, 3, C_CARD);
    if (cnt < 2) return;
    float stepX = (float)w / (cnt - 1);
    for (int i = 0; i < cnt - 1; i++) {
        int x1 = x + (int)(i * stepX);
        int y1 = y + h - (data[i]     * h / 100);
        int x2 = x + (int)((i+1) * stepX);
        int y2 = y + h - (data[i + 1] * h / 100);
        y1 = constrain(y1, y, y + h);
        y2 = constrain(y2, y, y + h);
        spr.drawLine(x1, y1, x2, y2, color);
    }
}

void DisplayManager::drawFloatSparkline(int16_t x, int16_t y, int16_t w, int16_t h,
                                         const float* data, uint8_t cnt, uint16_t color) {
    if (cnt < 2) return;

    float minVal = data[0];
    float maxVal = data[0];
    for (uint8_t i = 1; i < cnt; i++) {
        if (data[i] < minVal) minVal = data[i];
        if (data[i] > maxVal) maxVal = data[i];
    }
    float range = maxVal - minVal;
    if (range < 0.05f) range = 0.5f;

    float stepX = (float)(w - 8) / (cnt - 1);
    for (uint8_t i = 0; i < cnt - 1; i++) {
        int x1 = x + 4 + (int)(i * stepX);
        int y1 = y + h - 3 - (int)(((data[i] - minVal) / range) * (h - 7));
        int x2 = x + 4 + (int)((i + 1) * stepX);
        int y2 = y + h - 3 - (int)(((data[i + 1] - minVal) / range) * (h - 7));
        y1 = constrain(y1, y + 2, y + h - 2);
        y2 = constrain(y2, y + 2, y + h - 2);
        spr.drawLine(x1, y1, x2, y2, color);
        spr.fillCircle(x1, y1, 2, color);
    }
    int xLast = x + 4 + (int)((cnt - 1) * stepX);
    int yLast = y + h - 3 - (int)(((data[cnt - 1] - minVal) / range) * (h - 7));
    yLast = constrain(yLast, y + 2, y + h - 2);
    spr.fillCircle(xLast, yLast, 2, color);
}

void DisplayManager::drawHorizBar(int16_t x, int16_t y, int16_t w, int16_t h,
                                   float pct, uint16_t fg) {
    spr.fillRoundRect(x, y, w, h, h / 2, C_TRACE);
    int filled = (int)(pct * w / 100.0f);
    if (filled > 2) {
        uint16_t barColor = (pct > 85.0f) ? C_RED : (pct > 60.0f) ? C_ORANGE : fg;
        spr.fillRoundRect(x, y, filled, h, h / 2, barColor);
    }
}

// ─────────────────────────────────────────────────────────────────────
//  SMALL ICON FUNCTIONS  (~14px, drawn at center cx,cy)
// ─────────────────────────────────────────────────────────────────────

void DisplayManager::iconSun(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillCircle(cx, cy, 6, color);
    // 8 rays (precomputed inner r=9, outer r=13)
    static const int8_t ix[] = { 0, 6, 9, 6, 0,-6,-9,-6};
    static const int8_t iy[] = {-9,-6, 0, 6, 9, 6, 0,-6};
    static const int8_t ox[] = { 0, 9,13, 9, 0,-9,-13,-9};
    static const int8_t oy[] = {-13,-9, 0, 9,13, 9,  0,-9};
    for (int i = 0; i < 8; i++)
        spr.drawLine(cx+ix[i], cy+iy[i], cx+ox[i], cy+oy[i], color);
}

void DisplayManager::iconCloud(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillCircle(cx-5, cy+2, 7, color);
    spr.fillCircle(cx+5, cy+2, 7, color);
    spr.fillCircle(cx,   cy-2, 6, color);
    spr.fillRect(cx-11, cy+3, 22, 6, color);
}

void DisplayManager::iconRain(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillCircle(cx-4, cy-3, 6, color);
    spr.fillCircle(cx+4, cy-3, 6, color);
    spr.fillCircle(cx,   cy-7, 5, color);
    spr.fillRect(cx-9, cy-3, 18, 5, color);
    spr.fillRect(cx-5, cy+5,  2, 6, C_CYAN);
    spr.fillRect(cx-0, cy+7,  2, 6, C_CYAN);
    spr.fillRect(cx+5, cy+5,  2, 6, C_CYAN);
}

void DisplayManager::iconStorm(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillCircle(cx-4, cy-5, 6, color);
    spr.fillCircle(cx+4, cy-5, 6, color);
    spr.fillRect(cx-9, cy-5, 18, 5, color);
    spr.fillTriangle(cx+2, cy+2, cx-6, cy+13, cx+2, cy+13, C_YELLOW);
    spr.fillTriangle(cx+2, cy+13, cx+8, cy+13, cx-1, cy+20, C_YELLOW);
}

void DisplayManager::iconSnow(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillCircle(cx-4, cy-4, 5, color);
    spr.fillCircle(cx+4, cy-4, 5, color);
    spr.fillRect(cx-7, cy-4, 14, 4, color);
    spr.fillCircle(cx-5, cy+7, 2, C_WHITE);
    spr.fillCircle(cx,   cy+9, 2, C_WHITE);
    spr.fillCircle(cx+5, cy+7, 2, C_WHITE);
}

void DisplayManager::iconMist(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillRoundRect(cx-10, cy-6, 20, 3, 1, color);
    spr.fillRoundRect(cx-8,  cy+0, 16, 3, 1, color);
    spr.fillRoundRect(cx-10, cy+6, 20, 3, 1, color);
}

void DisplayManager::iconCPU(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillRoundRect(cx-8, cy-8, 16, 16, 2, color);
    spr.fillRect(cx-4, cy-4, 8, 8, C_BG);
    for (int p = -3; p <= 3; p += 3) {
        spr.fillRect(cx+p-1, cy-11, 2, 3, color);
        spr.fillRect(cx+p-1, cy+8,  2, 3, color);
        spr.fillRect(cx-11, cy+p-1, 3, 2, color);
        spr.fillRect(cx+8,  cy+p-1, 3, 2, color);
    }
}

void DisplayManager::iconGPU(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillRoundRect(cx-12, cy-5, 24, 10, 2, color);
    spr.drawCircle(cx-3, cy, 4, C_BG);
    spr.fillRect(cx-1, cy-1, 2, 2, C_BG);
    spr.fillRect(cx+10, cy-3, 3, 2, C_BG);
    spr.fillRect(cx+10, cy+1, 3, 2, C_BG);
}

void DisplayManager::iconBell(int16_t cx, int16_t cy, uint16_t color) {
    // Smooth rounded vector bell icon (no sharp corner artifacts)
    spr.fillCircle(cx, cy - 5, 2, color);                // Top loop ring
    spr.fillRoundRect(cx - 6, cy - 4, 12, 10, 3, color);   // Bell body dome
    spr.fillRoundRect(cx - 8, cy + 3, 16, 3, 1, color);    // Bell rim lip
    spr.fillCircle(cx, cy + 7, 2, color);                // Clapper
}

void DisplayManager::iconGold(int16_t cx, int16_t cy, uint16_t color) {
    // ── 3D Rich Money Bag & Gold Coins Illustration ────────────────────
    uint16_t goldDark   = spr.color565(180, 120, 0);   // Dark amber shadow
    uint16_t goldMid    = spr.color565(255, 180, 0);   // Deep gold
    uint16_t goldBright = spr.color565(255, 230, 40);  // Bright yellow gold
    uint16_t goldWhite  = C_WHITE;                     // Specular shine
    uint16_t ropeBrown  = spr.color565(130, 60, 15);   // Rope tie dark brown

    // ── 1. Gold Coin Stacks at Base (Left & Right) ─────────────────────
    // Left Coin Stack (3 coins stacked)
    for (int i = 2; i >= 0; i--) {
        int py = cy + 11 + i * 3;
        spr.fillRoundRect(cx - 19, py, 14, 6, 2, goldDark);
        spr.fillRoundRect(cx - 19, py, 13, 5, 2, goldMid);
        spr.fillRoundRect(cx - 18, py, 11, 3, 1, goldBright);
        spr.drawFastHLine(cx - 17, py, 4, goldWhite); // Shine
    }

    // Right Coin Stack (4 coins stacked)
    for (int i = 3; i >= 0; i--) {
        int py = cy + 8 + i * 3;
        spr.fillRoundRect(cx + 6, py, 15, 6, 2, goldDark);
        spr.fillRoundRect(cx + 6, py, 14, 5, 2, goldMid);
        spr.fillRoundRect(cx + 7, py, 12, 3, 1, goldBright);
        spr.drawFastHLine(cx + 8, py, 4, goldWhite); // Shine
    }

    // ── 2. Money Bag Body ────────────────────────────────────────────────
    // Bag main bulb (3D shaded spheres)
    spr.fillCircle(cx, cy + 2, 17, goldDark);       // Outer shadow rim
    spr.fillCircle(cx - 1, cy + 1, 16, goldMid);    // Mid tone body
    spr.fillCircle(cx - 3, cy - 1, 13, goldBright); // Bright highlight sphere

    // Bag ruffled top / neck opening
    spr.fillTriangle(cx - 10, cy - 17, cx + 10, cy - 17, cx, cy - 8, goldDark);
    spr.fillTriangle(cx - 9,  cy - 16, cx + 9,  cy - 16, cx, cy - 9, goldMid);
    spr.fillTriangle(cx - 7,  cy - 16, cx + 4,  cy - 16, cx - 1, cy - 10, goldBright);

    // Bag gathered folds detail
    spr.drawLine(cx - 6, cy - 16, cx - 2, cy - 9, goldDark);
    spr.drawLine(cx + 6, cy - 16, cx + 2, cy - 9, goldDark);

    // Tied Rope & Knot
    spr.fillRoundRect(cx - 8, cy - 10, 16, 4, 2, ropeBrown);
    spr.fillCircle(cx - 4, cy - 8, 3, ropeBrown); // Rope knot left
    spr.fillCircle(cx - 1, cy - 7, 2, ropeBrown); // Rope knot right
    spr.drawLine(cx - 5, cy - 7, cx - 8, cy - 2, ropeBrown); // Hanging rope end 1
    spr.drawLine(cx - 4, cy - 7, cx - 5, cy - 1, ropeBrown); // Hanging rope end 2

    // ── 3. Dollar Sign ($) Emblem ───────────────────────────────────────
    // Embossed $ in center of bag
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(ropeBrown, goldBright);
    spr.drawString("$", cx - 1, cy + 3, 2);

    // ── 4. Front Spilled Coins at Base ──────────────────────────────────
    // Coin 1 in front center
    spr.fillRoundRect(cx - 9, cy + 16, 12, 5, 2, goldDark);
    spr.fillRoundRect(cx - 9, cy + 16, 11, 4, 2, goldBright);
    spr.drawFastHLine(cx - 8, cy + 16, 4, goldWhite);

    // Coin 2 in front right
    spr.fillRoundRect(cx + 1, cy + 17, 11, 5, 2, goldDark);
    spr.fillRoundRect(cx + 1, cy + 17, 10, 4, 2, goldBright);
    spr.drawFastHLine(cx + 2, cy + 17, 3, goldWhite);

    // ── 5. Golden Sparkles / Twinkles ────────────────────────────────────
    // Top-Left Sparkle
    spr.drawFastVLine(cx - 15, cy - 15, 7, goldWhite);
    spr.drawFastHLine(cx - 18, cy - 12, 7, goldWhite);
    spr.fillCircle(cx - 15, cy - 12, 1, goldBright);

    // Top-Right Sparkle
    spr.drawFastVLine(cx + 16, cy - 10, 5, goldWhite);
    spr.drawFastHLine(cx + 14, cy - 8, 5, goldWhite);
}

void DisplayManager::iconCal(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillRoundRect(cx-9, cy-7, 18, 16, 2, color);
    spr.fillRect(cx-7, cy-1, 14, 1, C_BG);
    spr.fillRect(cx-7, cy+3, 14, 1, C_BG);
    spr.fillRect(cx-7, cy+7, 14, 1, C_BG);
    spr.fillRect(cx-1, cy-7, 1,  16, C_BG);
    spr.fillRect(cx+4, cy-7, 1,  16, C_BG);
    spr.fillRect(cx-5, cy-11, 3, 6, color);
    spr.fillRect(cx+2, cy-11, 3, 6, color);
}

void DisplayManager::iconNet(int16_t cx, int16_t cy, uint16_t color) {
    // Upload (up arrow, left)
    spr.fillRect(cx-10, cy-2, 5, 6, color);
    spr.fillTriangle(cx-8, cy-8, cx-13, cy-2, cx-3, cy-2, color);
    // Download (down arrow, right)
    spr.fillRect(cx+5,  cy-4, 5, 6, color);
    spr.fillTriangle(cx+7, cy+8, cx+2, cy+2, cx+12, cy+2, color);
}

void DisplayManager::iconPomodoro(int16_t cx, int16_t cy) {
    spr.fillCircle(cx, cy+2, 9, C_RED);
    spr.fillRect(cx-2, cy-9, 4, 6, C_GREEN2);
    spr.fillTriangle(cx, cy-6, cx+8, cy-10, cx+5, cy-2, C_GREEN2);
    // Shine
    spr.drawLine(cx-4, cy-4, cx-2, cy-6, 0xFFC0);
}

void DisplayManager::iconPC(int16_t cx, int16_t cy, uint16_t color) {
    spr.fillRoundRect(cx-11, cy-8, 22, 14, 2, color);
    spr.fillRect(cx-8, cy-5, 16, 8, C_BG);
    spr.fillRect(cx-3, cy+6, 6, 4, color);
    spr.fillRect(cx-7, cy+10, 14, 2, color);
}

// ═══════════════════════════════════════════════════════════════════════
//  CALIBRATION SCREEN — Full screen overlay during touch calibration
// ═══════════════════════════════════════════════════════════════════════
void DisplayManager::renderCalibrationScreen() {
    spr.fillSprite(TFT_BLACK);

    CalibState state = touch.getCalibState();

    // Title
    spr.setTextColor(TFT_WHITE, TFT_BLACK);
    spr.setTextDatum(TC_DATUM);
    spr.drawString("TOUCH CALIBRATION", 160, 5, 2);

    if (state == CALIB_DONE) {
        // Success screen
        spr.setTextColor(TFT_GREEN, TFT_BLACK);
        spr.setTextDatum(MC_DATUM);
        spr.drawString("CALIBRATION OK!", 160, 100, 2);
        spr.setTextColor(TFT_WHITE, TFT_BLACK);
        spr.drawString("Starting dashboard...", 160, 130, 2);
        return;
    }

    int targetX = 160, targetY = 120;
    const char* label = "";
    const char* step = "";

    switch (state) {
        case CALIB_WAIT_TL:
            targetX = CALIB_TL_X; targetY = CALIB_TL_Y;
            label = "Touch TOP-LEFT corner";
            step = "Step 1/3";
            break;
        case CALIB_WAIT_TR:
            targetX = CALIB_TR_X; targetY = CALIB_TR_Y;
            label = "Touch TOP-RIGHT corner";
            step = "Step 2/3";
            break;
        case CALIB_WAIT_BL:
            targetX = CALIB_BL_X; targetY = CALIB_BL_Y;
            label = "Touch BOTTOM-LEFT corner";
            step = "Step 3/3";
            break;
        default:
            label = "Processing...";
            step = "";
            break;
    }

    // Draw crosshair target
    uint16_t crossColor = TFT_YELLOW;
    spr.drawLine(targetX - 20, targetY, targetX + 20, targetY, crossColor);
    spr.drawLine(targetX, targetY - 20, targetX, targetY + 20, crossColor);
    spr.drawCircle(targetX, targetY, 12, crossColor);
    spr.drawCircle(targetX, targetY, 3, TFT_RED);

    // Draw instruction text
    spr.setTextColor(TFT_CYAN, TFT_BLACK);
    spr.setTextDatum(MC_DATUM);
    spr.drawString(label, 160, 120, 2);

    spr.setTextColor(TFT_DARKGREY, TFT_BLACK);
    spr.drawString(step, 160, 145, 2);

    // Draw hint at bottom
    spr.setTextColor(0x7BEF, TFT_BLACK); // dim grey
    spr.drawString("Press firmly on the crosshair", 160, 225, 1);
}

// ═══════════════════════════════════════════════════════════════════════
//  PAGE 7 — APP LAUNCHER GRID (Quick Access App Launcher 3x3 Grid)
// ═══════════════════════════════════════════════════════════════════════
void DisplayManager::renderAppLauncherOverlay() {
    struct AppItem {
        const char* name;
        uint16_t color;
        uint8_t targetPage;
    };

    static const AppItem apps[8] = {
        { "Weather",    C_CYAN,   0 }, // Page 0: Weather Clock
        { "Calendar",   C_YELLOW, 1 }, // Page 1: Lunar Calendar
        { "Finance",    C_YELLOW, 2 }, // Page 2: Gold & Exchange
        { "PC CPU",     C_CYAN,   3 }, // Page 3: PC CPU & RAM
        { "Net & Disk", C_GREEN,  4 }, // Page 4: PC Net & Disks
        { "Utilities",  C_ORANGE, 5 }, // Page 5: Desk Utilities (Pomodoro & Alarm)
        { "Media Ctrl", C_CYAN,   6 }, // Page 6: Media Control
        { "Settings",   C_PURPLE, 7 }  // Page 7: Settings (ALWAYS LAST FEATURE PAGE)
    };

    for (int i = 0; i < 8; i++) {
        int col = i % 3;
        int row = i / 3;
        int bx = 11 + col * 102;  // Perfectly centered (11px left & right margins)
        int by = 34 + row * 66;

        uint16_t cardBg = C_CARD;
        spr.fillRoundRect(bx, by, 94, 60, 8, cardBg);
        spr.drawRoundRect(bx, by, 94, 60, 8, apps[i].color);

        // Draw Mini Icon inside app tile
        int cx = bx + 47;
        int cy = by + 24;
        switch (apps[i].targetPage) {
            case 0: iconSun(cx, cy, C_YELLOW); break;
            case 1: iconCal(cx, cy, C_YELLOW); break;
            case 2: // Finance Golden Dollar Coin Badge ($) - 18px balanced size
                spr.fillCircle(cx, cy, 9, C_YELLOW);
                spr.drawCircle(cx, cy, 9, C_ORANGE);
                spr.setTextDatum(MC_DATUM);
                spr.setTextColor(C_CARD, C_YELLOW);
                spr.drawString("$", cx, cy, 2);
                break;
            case 3: iconCPU(cx, cy, C_CYAN); break;
            case 4: iconNet(cx, cy, C_GREEN); break;
            case 5: iconPomodoro(cx, cy); break; // Red Pomodoro Tomato Icon
            case 6: // Media Controller Icon (Play button in Cyan Frame)
                spr.fillRoundRect(cx - 11, cy - 8, 22, 16, 4, C_CYAN);
                spr.fillTriangle(cx - 3, cy - 5, cx - 3, cy + 5, cx + 5, cy, C_CARD);
                break;
            case 7: // Settings Tuning Sliders Icon (Modern Control Switches)
                spr.fillRoundRect(cx - 10, cy - 6, 20, 3, 1, C_PURPLE);
                spr.fillCircle(cx - 3, cy - 5, 4, C_PURPLE);
                spr.fillCircle(cx - 3, cy - 5, 2, C_CARD);

                spr.fillRoundRect(cx - 10, cy + 4, 20, 3, 1, C_PURPLE);
                spr.fillCircle(cx + 4, cy + 5, 4, C_PURPLE);
                spr.fillCircle(cx + 4, cy + 5, 2, C_CARD);
                break;
        }

        // App Label
        spr.setTextDatum(BC_DATUM);
        spr.setTextColor(C_WHITE, C_CARD);
        spr.drawString(apps[i].name, cx, by + 54, 1);
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  PAGE 7 — Settings Page (ALWAYS LAST FEATURE PAGE)
// ═══════════════════════════════════════════════════════════════════════
void DisplayManager::renderPage7_Settings() {
    // ── Dedicated Transparent Side Navigation Keys (No Card/Border) ──────
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString("<", 16, 126, 2);
    spr.drawString(">", 304, 126, 2);

    // ── Top Sub-Tab Navigation Header (Shifted down 5px: y = 35..57) ─────
    // Tab 0: SYSTEM (x = 34..155)
    uint16_t t0_bg = (settingsTab == 0) ? C_CYAN : C_CARD;
    uint16_t t0_fg = (settingsTab == 0) ? C_BG : C_DIM;
    spr.fillRoundRect(34, 35, 121, 22, 5, t0_bg);
    spr.drawRoundRect(34, 35, 121, 22, 5, C_TRACE);
    spr.setTextColor(t0_fg, t0_bg);
    spr.setTextDatum(MC_DATUM);
    spr.drawString("SYSTEM", 94, 46, 2);

    // Tab 1: THEMES (x = 165..286)
    uint16_t t1_bg = (settingsTab == 1) ? C_PURPLE : C_CARD;
    uint16_t t1_fg = (settingsTab == 1) ? C_BG : C_DIM;
    spr.fillRoundRect(165, 35, 121, 22, 5, t1_bg);
    spr.drawRoundRect(165, 35, 121, 22, 5, C_TRACE);
    spr.setTextColor(t1_fg, t1_bg);
    spr.setTextDatum(MC_DATUM);
    spr.drawString("THEMES", 225, 46, 2);

    if (settingsTab == 0) {
        // ── TAB 0: SYSTEM SETTINGS (Shifted down 5px: start y = 61) ───────
        int y = 61;
        int itemH = 26;

        // 1. Calibrate Touch
        spr.fillRoundRect(34, y, 252, 23, 4, C_CARD);
        spr.drawRoundRect(34, y, 252, 23, 4, C_TRACE);
        spr.setTextColor(C_YELLOW, C_CARD);
        spr.setTextDatum(ML_DATUM);
        spr.drawString("Calibrate Touch", 42, y + 11, 2);
        spr.setTextColor(C_DIM, C_CARD);
        spr.setTextDatum(MR_DATUM);
        spr.drawString(touch.isCalibrated() ? "OK" : "Not Set", 278, y + 11, 2);
        y += itemH;

        // 2. Auto Brightness
        spr.fillRoundRect(34, y, 252, 23, 4, C_CARD);
        spr.drawRoundRect(34, y, 252, 23, 4, C_TRACE);
        spr.setTextColor(C_CYAN, C_CARD);
        spr.setTextDatum(ML_DATUM);
        spr.drawString("Auto Brightness", 42, y + 11, 2);
        spr.setTextColor(C_DIM, C_CARD);
        spr.setTextDatum(MR_DATUM);
        spr.drawString(hardware.isAutoBrightnessEnabled() ? "ON" : "OFF", 278, y + 11, 2);
        y += itemH;

        // 3. Touch Beep Volume
        spr.fillRoundRect(34, y, 252, 23, 4, C_CARD);
        spr.drawRoundRect(34, y, 252, 23, 4, C_TRACE);
        spr.setTextColor(C_GREEN, C_CARD);
        spr.setTextDatum(ML_DATUM);
        spr.drawString("Touch Beep Volume", 42, y + 11, 2);
        spr.setTextColor(C_DIM, C_CARD);
        spr.setTextDatum(MR_DATUM);
        char volBuf[16];
        if (hardware.getSoundVolume() == 0) snprintf(volBuf, sizeof(volBuf), "MUTE");
        else snprintf(volBuf, sizeof(volBuf), "%d%%", hardware.getSoundVolume());
        spr.drawString(volBuf, 278, y + 11, 2);
        y += itemH;

        // 4. WiFi SSID
        spr.fillRoundRect(34, y, 252, 23, 4, C_CARD);
        spr.drawRoundRect(34, y, 252, 23, 4, C_TRACE);
        spr.setTextColor(C_GREEN, C_CARD);
        spr.setTextDatum(ML_DATUM);
        spr.drawString("WiFi SSID", 42, y + 11, 2);
        spr.setTextColor(C_DIM, C_CARD);
        spr.setTextDatum(MR_DATUM);
        spr.drawString(WiFi.isConnected() ? WiFi.SSID().c_str() : "N/A", 278, y + 11, 2);
        y += itemH;

        // 5. IP Address
        spr.fillRoundRect(34, y, 252, 23, 4, C_CARD);
        spr.drawRoundRect(34, y, 252, 23, 4, C_TRACE);
        spr.setTextColor(C_GREEN, C_CARD);
        spr.setTextDatum(ML_DATUM);
        spr.drawString("IP Address", 42, y + 11, 2);
        spr.setTextColor(C_DIM, C_CARD);
        spr.setTextDatum(MR_DATUM);
        spr.drawString(WiFi.isConnected() ? WiFi.localIP().toString().c_str() : "N/A", 278, y + 11, 2);
        y += itemH;

        // 6. Firmware Version
        spr.fillRoundRect(34, y, 252, 23, 4, C_CARD);
        spr.drawRoundRect(34, y, 252, 23, 4, C_TRACE);
        spr.setTextColor(C_PURPLE, C_CARD);
        spr.setTextDatum(ML_DATUM);
        spr.drawString("Firmware Ver", 42, y + 11, 2);
        spr.setTextColor(C_DIM, C_CARD);
        spr.setTextDatum(MR_DATUM);
        spr.drawString("v2.5.0", 278, y + 11, 2);

    } else {
        // ── TAB 1: THEME PRESET SELECTOR (Shifted down 5px: start by = 63) ──
        const char* themes[6] = { "Ocean Dark", "Cyberpunk", "Forest", "Cherry", "Light Day", "Retro Green" };
        const char* currentP = getCurrentThemePresetName();

        for (int i = 0; i < 6; i++) {
            int row = i / 2;
            int col = i % 2;
            int bx = 34 + col * 128;
            int by = 63 + row * 52;

            bool isSelected = (strcmp(currentP, themes[i]) == 0);
            uint16_t borderC = isSelected ? C_GREEN : C_TRACE;
            uint16_t textC = isSelected ? C_GREEN : C_WHITE;

            spr.fillRoundRect(bx, by, 120, 46, 6, C_CARD);
            spr.drawRoundRect(bx, by, 120, 46, 6, borderC);
            spr.setTextDatum(MC_DATUM);
            spr.setTextColor(textC, C_CARD);
            spr.drawString(themes[i], bx + 60, by + 23, 2);
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 6 — MEDIA CONTROL HOTKEYS (With Transparent Side Nav Keys)
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage6_MediaControl() {
    // ── 1. Top Live Song Title & Artist Marquee Banner (y = 32..56, h = 24px) ──
    spr.fillRoundRect(16, 32, 288, 25, 6, C_CARD);
    spr.drawRoundRect(16, 32, 288, 25, 6, C_CYAN);

    char fullStr[160];
    if (strlen(mediaTitle) > 0) {
        if (strlen(mediaArtist) > 0) {
            snprintf(fullStr, sizeof(fullStr), "%s - %s", mediaTitle, mediaArtist);
        } else {
            snprintf(fullStr, sizeof(fullStr), "%s", mediaTitle);
        }
    } else {
        snprintf(fullStr, sizeof(fullStr), "Windows Media Transport - Ready");
    }

    int textW = spr.textWidth(fullStr, 2);
    if (textW <= 265) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_WHITE, C_CARD);
        spr.drawString(fullStr, 160, 44, 2);
    } else {
        // Smooth Marquee Scrolling for long track titles
        marqueeOffset = (marqueeOffset + 2) % (textW + 80);
        int drawX = 290 - marqueeOffset;
        
        // Draw inside card bounds safely
        spr.setTextDatum(ML_DATUM);
        spr.setTextColor(C_WHITE, C_CARD);
        spr.drawString(fullStr, drawX, 44, 2);

        // Draw side mask panels to keep marquee text strictly contained in banner box
        spr.fillRect(0, 32, 18, 25, C_BG);
        spr.fillRect(302, 32, 18, 25, C_BG);
        spr.drawRoundRect(16, 32, 288, 25, 6, C_CYAN);
    }

    // ── Dedicated Transparent Side Navigation Keys ───────────────────
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString("<", 16, 140, 2);
    spr.drawString(">", 304, 140, 2);

    // ── Row 1: Track Controls (y = 65..137, height 72px) ───────────────
    // 1. PREV
    spr.fillRoundRect(34, 65, 76, 72, 8, C_CARD);
    spr.drawRoundRect(34, 65, 76, 72, 8, C_TRACE);
    int cx1 = 72, cy1 = 93;
    spr.fillRect(cx1 - 10, cy1 - 10, 4, 20, C_CYAN);
    spr.fillTriangle(cx1 + 8, cy1 - 10, cx1 + 8, cy1 + 10, cx1 - 4, cy1, C_CYAN);
    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString("PREV", cx1, 131, 2);

    // 2. PLAY / PAUSE (Dynamic Hero Center Button: x = 117..203)
    spr.fillRoundRect(117, 65, 86, 72, 8, C_CARD);
    spr.drawRoundRect(117, 65, 86, 72, 8, C_GREEN);
    int cx2 = 160, cy2 = 93;
    if (!isMediaPlaying) {
        spr.fillTriangle(cx2 - 8, cy2 - 12, cx2 - 8, cy2 + 12, cx2 + 10, cy2, C_GREEN);
        spr.setTextDatum(BC_DATUM);
        spr.setTextColor(C_GREEN, C_CARD);
        spr.drawString("PLAY", cx2, 131, 2);
    } else {
        spr.fillRoundRect(cx2 - 8, cy2 - 11, 6, 22, 2, C_GREEN);
        spr.fillRoundRect(cx2 + 3, cy2 - 11, 6, 22, 2, C_GREEN);
        spr.setTextDatum(BC_DATUM);
        spr.setTextColor(C_GREEN, C_CARD);
        spr.drawString("PAUSE", cx2, 131, 2);
    }

    // 3. NEXT
    spr.fillRoundRect(210, 65, 76, 72, 8, C_CARD);
    spr.drawRoundRect(210, 65, 76, 72, 8, C_TRACE);
    int cx3 = 248, cy3 = 93;
    spr.fillTriangle(cx3 - 8, cy3 - 10, cx3 - 8, cy3 + 10, cx3 + 4, cy3, C_CYAN);
    spr.fillRect(cx3 + 6, cy3 - 10, 4, 20, C_CYAN);
    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString("NEXT", cx3, 131, 2);

    // ── Row 2: Volume & Ad Controls (y = 145..217, height 72px) ────────
    // 4. VOL -
    spr.fillRoundRect(34, 145, 76, 72, 8, C_CARD);
    spr.drawRoundRect(34, 145, 76, 72, 8, C_TRACE);
    int cx4 = 72, cy4 = 171;
    spr.fillRoundRect(cx4 - 18, cy4 - 7, 7, 14, 2, C_YELLOW);
    spr.fillTriangle(cx4 - 10, cy4 - 7, cx4 - 2, cy4 - 14, cx4 - 10, cy4 + 7, C_YELLOW);
    spr.fillTriangle(cx4 - 10, cy4 + 7, cx4 - 2, cy4 + 14, cx4 - 2, cy4 - 14, C_YELLOW);
    int arcX4 = cx4 + 5;
    spr.drawCircle(arcX4, cy4, 7, C_YELLOW);
    spr.drawCircle(arcX4, cy4, 8, C_YELLOW);
    spr.fillRect(cx4 - 1, cy4 - 10, 6, 20, C_CARD);
    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("VOL -", cx4, 211, 2);

    // 5. SKIP AD
    spr.fillRoundRect(117, 145, 86, 72, 8, C_CARD);
    spr.drawRoundRect(117, 145, 86, 72, 8, C_ORANGE);
    int cx5 = 160, cy5 = 171;
    spr.fillTriangle(cx5 - 10, cy5 - 10, cx5 - 2, cy5, cx5 - 10, cy5 + 10, C_ORANGE);
    spr.fillTriangle(cx5 - 2, cy5 - 10, cx5 + 6, cy5, cx5 - 2, cy5 + 10, C_ORANGE);
    spr.fillRect(cx5 + 7, cy5 - 10, 3, 20, C_ORANGE);
    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.drawString("SKIP AD", cx5, 211, 1);

    // 6. VOL +
    spr.fillRoundRect(210, 145, 76, 72, 8, C_CARD);
    spr.drawRoundRect(210, 145, 76, 72, 8, C_TRACE);
    int cx6 = 248, cy6 = 171;
    spr.fillRoundRect(cx6 - 20, cy6 - 7, 7, 14, 2, C_YELLOW);
    spr.fillTriangle(cx6 - 12, cy6 - 7, cx6 - 4, cy6 - 14, cx6 - 12, cy6 + 7, C_YELLOW);
    spr.fillTriangle(cx6 - 12, cy6 + 7, cx6 - 4, cy6 + 14, cx6 - 4, cy6 - 14, C_YELLOW);
    int arcX6 = cx6 + 3;
    spr.drawCircle(arcX6, cy6, 7, C_YELLOW);
    spr.drawCircle(arcX6, cy6, 8, C_YELLOW);
    spr.drawCircle(arcX6, cy6, 12, C_YELLOW);
    spr.drawCircle(arcX6, cy6, 13, C_YELLOW);
    spr.fillRect(cx6 - 3, cy6 - 15, 6, 30, C_CARD);
    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("VOL +", cx6, 211, 2);
}

// ─────────────────────────────────────────────────────────────────────
//  FULLSCREEN CHART DETAIL MODAL OVERLAY
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderModalSetAlarm() {
    // Dim background overlay
    spr.fillSprite(C_BG);

    // Centered Modal Window Card (x = 15, y = 25, w = 290, h = 185)
    spr.fillRoundRect(15, 25, 290, 185, 8, C_CARD);
    spr.drawRoundRect(15, 25, 290, 185, 8, C_ORANGE);

    // Header inside modal
    iconBell(32, 42, C_ORANGE);
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.drawString("SET ALARM TIME", 45, 42, 2);

    // 1px Horizontal Line under header
    spr.drawFastHLine(25, 56, 270, C_TRACE);

    // Hour Adjustment Box (x = 35..135, y = 64..134)
    spr.fillRoundRect(35, 64, 100, 70, 6, C_BG);
    spr.drawRoundRect(35, 64, 100, 70, 6, C_TRACE);

    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString("[ + ]", 85, 75, 1);

    char hStr[4];
    snprintf(hStr, sizeof(hStr), "%02d", tempAlarmHour);
    spr.setTextColor(C_WHITE, C_BG);
    spr.drawString(hStr, 85, 99, 4);

    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString("[ - ]", 85, 123, 1);

    // Colon Separator
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.drawString(":", 160, 99, 4);

    // Minute Adjustment Box (x = 185..285, y = 64..134)
    spr.fillRoundRect(185, 64, 100, 70, 6, C_BG);
    spr.drawRoundRect(185, 64, 100, 70, 6, C_TRACE);

    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString("[ + ]", 235, 75, 1);

    char mStr[4];
    snprintf(mStr, sizeof(mStr), "%02d", tempAlarmMin);
    spr.setTextColor(C_WHITE, C_BG);
    spr.drawString(mStr, 235, 99, 4);

    spr.setTextColor(C_CYAN, C_BG);
    spr.drawString("[ - ]", 235, 123, 1);

    // Bottom Action Buttons (y = 146..196, height 50px - SUPER EASY TO SEE & TOUCH!)
    // Cancel Pill Button (Left: x = 28..145, y = 146..196)
    spr.fillRoundRect(28, 146, 117, 50, 8, C_BG);
    spr.drawRoundRect(28, 146, 117, 50, 8, C_RED);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_RED, C_BG);
    spr.drawString("CANCEL", 86, 171, 2);

    // Save & Enable Pill Button (Right: x = 175..292, y = 146..196)
    spr.fillRoundRect(175, 146, 117, 50, 8, C_GREEN);
    spr.drawRoundRect(175, 146, 117, 50, 8, C_WHITE);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_BG, C_GREEN);
    spr.drawString("SAVE", 233, 171, 2);
}

void DisplayManager::renderModalBeepVolume() {
    spr.fillSprite(C_BG);

    // Outer Card
    spr.fillRoundRect(12, 10, 296, 220, 10, C_CARD);
    spr.drawRoundRect(12, 10, 296, 220, 10, C_PURPLE);
    spr.drawRoundRect(13, 11, 294, 218, 9, C_PURPLE);

    // Title
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("TOUCH BEEP SOUND VOLUME", 160, 20, 2);

    // Volume level text badge
    char volStr[32];
    uint8_t curVol = hardware.getSoundVolume();
    if (curVol == 0) {
        snprintf(volStr, sizeof(volStr), "MUTE (0%%)");
    } else {
        snprintf(volStr, sizeof(volStr), "%d%% VOLUME", curVol);
    }
    spr.setFreeFont(&FreeSansBold9pt7b);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor((curVol == 0) ? C_RED : C_GREEN, C_CARD);
    spr.drawString(volStr, 160, 56);
    spr.setFreeFont(NULL);

    // Volume Slider Track Bar
    spr.fillRoundRect(30, 85, 260, 14, 7, C_TRACE);
    int fillW = (int)(curVol * 260.0f / 100.0f);
    fillW = constrain(fillW, 8, 260);
    uint16_t barC = (curVol == 0) ? C_RED : C_CYAN;
    spr.fillRoundRect(30, 85, fillW, 14, 7, barC);
    // Slider Knob
    int knobX = 30 + (int)(curVol * 260.0f / 100.0f);
    knobX = constrain(knobX, 36, 284);
    spr.fillCircle(knobX, 92, 11, C_WHITE);
    spr.drawCircle(knobX, 92, 11, C_PURPLE);

    // 5 Preset Buttons (0%, 25%, 50%, 75%, 100%)
    static const uint8_t presets[] = { 0, 25, 50, 75, 100 };
    static const char* labels[] = { "MUTE", "25%", "50%", "75%", "100%" };
    for (int i = 0; i < 5; i++) {
        int bx = 24 + i * 55;
        int by = 120;
        bool isSel = (curVol == presets[i]);
        uint16_t bgC = isSel ? C_PURPLE : C_BG;
        uint16_t textC = isSel ? C_WHITE : C_DIM;
        spr.fillRoundRect(bx, by, 48, 30, 6, bgC);
        spr.drawRoundRect(bx, by, 48, 30, 6, isSel ? C_CYAN : C_TRACE);
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(textC, bgC);
        spr.drawString(labels[i], bx + 24, by + 15, 1);
    }

    // Bottom Action Buttons
    // Close / Save Button
    spr.fillRoundRect(80, 168, 160, 44, 8, C_GREEN);
    spr.drawRoundRect(80, 168, 160, 44, 8, C_WHITE);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_BG, C_GREEN);
    spr.drawString("SAVE & CLOSE", 160, 190, 2);
}

void DisplayManager::renderDetailModal() {
    if (currentModal == MODAL_SET_ALARM) {
        renderModalSetAlarm();
        return;
    } else if (currentModal == MODAL_BEEP_VOLUME) {
        renderModalBeepVolume();
        return;
    }

    spr.fillSprite(C_BG);

    const GoldData& g = network.getGold();
    const ExchangeData& ex = network.getExchange();

    char titleBuf[64];
    const char* titleStr = "";
    uint16_t themeColor = C_YELLOW;
    const float* dataPtr = nullptr;
    float currentVal = 0.0f;
    bool isMoneyFormat = false;

    if (currentModal == MODAL_GOLD_SJC) {
        snprintf(titleBuf, sizeof(titleBuf), "BIEU DO CHI TIET VANG SJC (7 NGAY)");
        titleStr = titleBuf;
        themeColor = C_YELLOW;
        dataPtr = g.history7Days;
        currentVal = g.sjcBuy;
        isMoneyFormat = false; // in Triệu VNĐ
    } else if (currentModal == MODAL_CURRENCY_1) {
        snprintf(titleBuf, sizeof(titleBuf), "BIEU DO TY GIA %s/VND (7 NGAY)", ex.cur1Code[0] ? ex.cur1Code : "USD");
        titleStr = titleBuf;
        themeColor = C_CYAN;
        dataPtr = ex.cur1History7;
        currentVal = ex.cur1Rate;
        isMoneyFormat = true;
    } else if (currentModal == MODAL_CURRENCY_2) {
        snprintf(titleBuf, sizeof(titleBuf), "BIEU DO TY GIA %s/VND (7 NGAY)", ex.cur2Code[0] ? ex.cur2Code : "EUR");
        titleStr = titleBuf;
        themeColor = C_GREEN;
        dataPtr = ex.cur2History7;
        currentVal = ex.cur2Rate;
        isMoneyFormat = true;
    }

    // ── Header Box ──────────────────────────────────────────────────────
    spr.fillRoundRect(8, 6, 304, 28, 5, C_CARD);
    spr.drawRoundRect(8, 6, 304, 28, 5, themeColor);
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(themeColor, C_CARD);
    spr.drawString(titleStr, 14, 20, 1);

    // Close Button [ QUAY LAI ]
    spr.fillRoundRect(240, 9, 68, 22, 4, C_RED);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(C_WHITE, C_RED);
    spr.drawString("QUAY LAI", 274, 20, 1);

    // ── Main Large Chart Box (Full Resolution Grid & Labels) ────────────
    int cx = 10, cy = 38, cw = 300, ch = 132;
    spr.fillRoundRect(cx, cy, cw, ch, 6, C_CARD);
    spr.drawRoundRect(cx, cy, cw, ch, 6, C_TRACE);

    // Horizontal dashed gridlines
    for (int i = 1; i <= 3; i++) {
        int gy = cy + i * (ch / 4);
        for (int gx = cx + 5; gx < cx + cw - 5; gx += 6) {
            spr.drawFastHLine(gx, gy, 3, C_TRACE);
        }
    }

    // Vertical date gridlines & Date X-axis labels
    const char* dateLabels[7] = { "28/07", "29/07", "30/07", "31/07", "01/08", "02/08", "03/08" };
    float stepX = (float)(cw - 28) / 6.0f;

    for (int i = 0; i < 7; i++) {
        int gx = cx + 14 + (int)(i * stepX);
        spr.drawFastVLine(gx, cy + 5, ch - 22, C_TRACE);
        spr.setTextDatum(BC_DATUM);
        spr.setTextColor(C_DIM, C_CARD);
        spr.drawString(dateLabels[i], gx, cy + ch - 3, 1);
    }

    // High-Res Trend Curve & Price Value Badges
    if (dataPtr) {
        float minVal = dataPtr[0];
        float maxVal = dataPtr[0];
        int minIdx = 0, maxIdx = 0;
        for (int i = 1; i < 7; i++) {
            if (dataPtr[i] < minVal) { minVal = dataPtr[i]; minIdx = i; }
            if (dataPtr[i] > maxVal) { maxVal = dataPtr[i]; maxIdx = i; }
        }
        float range = maxVal - minVal;
        if (range < 0.05f) range = 0.5f;

        for (int i = 0; i < 6; i++) {
            int x1 = cx + 14 + (int)(i * stepX);
            int y1 = cy + ch - 24 - (int)(((dataPtr[i] - minVal) / range) * (ch - 46));
            int x2 = cx + 14 + (int)((i + 1) * stepX);
            int y2 = cy + ch - 24 - (int)(((dataPtr[i + 1] - minVal) / range) * (ch - 46));
            y1 = constrain(y1, cy + 18, cy + ch - 24);
            y2 = constrain(y2, cy + 18, cy + ch - 24);

            spr.drawLine(x1, y1, x2, y2, themeColor);
            spr.drawLine(x1, y1 + 1, x2, y2 + 1, themeColor); // Bold 2px line
        }

        // Draw Dot points & Key Price badges (MIN, MAX, and TODAY)
        for (int i = 0; i < 7; i++) {
            int px = cx + 14 + (int)(i * stepX);
            int py = cy + ch - 24 - (int)(((dataPtr[i] - minVal) / range) * (ch - 46));
            py = constrain(py, cy + 18, cy + ch - 24);

            uint16_t dotColor = (i == maxIdx) ? C_GREEN : ((i == minIdx) ? C_RED : themeColor);
            spr.fillCircle(px, py, 3, C_WHITE);
            spr.drawCircle(px, py, 4, dotColor);

            // Display price value for ALL 7 DAYS!
            char pBuf[16];
            if (isMoneyFormat) {
                if (dataPtr[i] >= 1000.0f) {
                    snprintf(pBuf, sizeof(pBuf), "%.0f", dataPtr[i]);
                } else {
                    snprintf(pBuf, sizeof(pBuf), "%.1f", dataPtr[i]);
                }
            } else {
                snprintf(pBuf, sizeof(pBuf), "%.2fM", dataPtr[i]);
            }
            spr.setTextDatum(BC_DATUM);
            spr.setTextColor((i == maxIdx) ? C_GREEN : ((i == minIdx) ? C_RED : C_WHITE), C_CARD);

            // Stagger tag Y positions (alternate odd/even dots) to prevent text collision
            int tagY = (i % 2 == 0) ? (py - 5) : (py + 15);
            if (tagY < cy + 15) tagY = py + 15;
            if (tagY > cy + ch - 20) tagY = py - 5;

            spr.drawString(pBuf, px, tagY, 1);
        }
    }

    // ── Summary Footer Bar ──────────────────────────────────────────────
    spr.fillRoundRect(10, 174, 300, 60, 6, C_CARD);
    spr.drawRoundRect(10, 174, 300, 60, 6, C_TRACE);

    float minV = dataPtr ? dataPtr[0] : 0, maxV = dataPtr ? dataPtr[0] : 0;
    if (dataPtr) {
        for (int i = 1; i < 7; i++) {
            if (dataPtr[i] < minV) minV = dataPtr[i];
            if (dataPtr[i] > maxV) maxV = dataPtr[i];
        }
    }

    char lowBuf[32], highBuf[32], curBuf[32];
    if (isMoneyFormat) {
        char b1[16], b2[16], b3[16];
        formatWithCommas(b1, sizeof(b1), minV);
        formatWithCommas(b2, sizeof(b2), maxV);
        formatWithCommas(b3, sizeof(b3), currentVal);
        snprintf(lowBuf, sizeof(lowBuf), "Day: %s", b1);
        snprintf(highBuf, sizeof(highBuf), "Dinh: %s", b2);
        snprintf(curBuf, sizeof(curBuf), "Bay gio: %s", b3);
    } else {
        snprintf(lowBuf, sizeof(lowBuf), "Day: %.2fM", minV);
        snprintf(highBuf, sizeof(highBuf), "Dinh: %.2fM", maxV);
        snprintf(curBuf, sizeof(curBuf), "Bay gio: %.2fM", currentVal);
    }

    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_RED, C_CARD);
    spr.drawString(lowBuf, 20, 182, 1);

    spr.setTextColor(C_GREEN, C_CARD);
    spr.drawString(highBuf, 118, 182, 1);

    spr.setTextColor(themeColor, C_CARD);
    spr.drawString(curBuf, 212, 182, 1);

    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_DIM, C_CARD);
    spr.drawString("[ Cham bat ky dau de dong chi tiet ]", 160, 228, 1);
}

// ─────────────────────────────────────────────────────────────────────
//  SMART DESK DASHBOARD — BOOT / SPLASH SCREEN
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderSplashScreen() {
    spr.fillSprite(C_BG);

    // ── Outer Glowing Card Frame ─────────────────────────────────────────
    spr.fillRoundRect(12, 10, 296, 220, 12, C_CARD);
    spr.drawRoundRect(12, 10, 296, 220, 12, C_CYAN);
    spr.drawRoundRect(13, 11, 294, 218, 11, C_CYAN); // Bold 2px border

    // ── Main Header Title (Smooth 18px FreeSansBold Vector Font) ─────────
    spr.setFreeFont(&FreeSansBold9pt7b);
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("SMART DESK DASHBOARD", 160, 20);
    spr.setFreeFont(NULL); // Reset to default bitmap font

    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.drawString("Smart Weather, Lunar Calendar & PC Monitor", 160, 48, 1);

    // ── Stylized Center Glowing Badge / Vector Graphic ──────────────────
    spr.fillCircle(160, 104, 22, C_TRACE);
    spr.drawCircle(160, 104, 23, C_CYAN);
    spr.drawCircle(160, 104, 24, C_CYAN);

    // Clock Icon inside center badge
    spr.fillCircle(160, 104, 15, C_BG);
    spr.drawCircle(160, 104, 16, C_YELLOW);
    spr.drawFastVLine(160, 93, 11, C_YELLOW);
    spr.drawFastHLine(160, 104, 7, C_YELLOW);
    spr.fillCircle(160, 104, 3, C_WHITE);

    // ── Status Text & Progress Bar ──────────────────────────────────────
    const char* statusMsg = network.getBootStatusMsg();
    uint8_t pct = network.getBootProgressPct();
    BootState bState = network.getBootState();

    // Progress Bar Track
    spr.fillRoundRect(40, 146, 240, 12, 6, C_TRACE);
    spr.drawRoundRect(40, 146, 240, 12, 6, C_DIM);

    // Fill Bar
    int fillW = (int)(pct * 240.0f / 100.0f);
    fillW = constrain(fillW, 8, 240);
    uint16_t barColor = (bState == BOOT_AP_MODE) ? C_ORANGE : (bState == BOOT_OFFLINE) ? C_RED : C_GREEN;
    spr.fillRoundRect(40, 146, fillW, 12, 6, barColor);

    // Dynamic Status Text
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_WHITE, C_CARD);
    spr.drawString(statusMsg ? statusMsg : "Initializing...", 160, 166, 1);

    // ── Footer Commercial Branding ──────────────────────────────────────
    spr.setTextDatum(BC_DATUM);
    spr.setTextColor(C_DIM, C_CARD);
    spr.drawString("A Product of FABX Company", 160, 222, 1);
}
