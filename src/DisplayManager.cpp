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
        case 0: return theme.cyan;
        case 1: return theme.yellow;
        case 2: return theme.yellow;
        case 3: return theme.cyan;
        case 4: return theme.orange;
        case 5: return theme.green;
        case 6: return theme.orange;
        case 7: return theme.purple;
        default: return theme.cyan;
    }
}

// ─────────────────────────────────────────────────────────────────────
//  CONSTRUCTOR / BEGIN / NAVIGATION / UPDATE
// ─────────────────────────────────────────────────────────────────────
DisplayManager::DisplayManager()
    : tft(), spr(&tft), currentPage(0), currentModal(MODAL_NONE), calendarMonthOffset(0), lastRenderTime(0), spriteReady(false) {}

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
        Serial.println("[DisplayManager] 16-bit sprite failed → trying 8-bit...");
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

    switch (currentPage) {
        case 0: renderPage0_WeatherClock();  break;
        case 1: renderPage1_LunarCalendar(); break;
        case 2: renderPage2_FinanceGold();   break;
        case 3: renderPage3_PcCpuRam();      break;
        case 4: renderPage4_PcGpuVram();     break;
        case 5: renderPage5_PcNetDisks();    break;
        case 6: renderPage6_DeskUtilities(); break;
        case 7: renderPage7_Settings();      break;
        default: renderPage0_WeatherClock(); break;
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
    switch (currentPage) {
        case 0: // Sun
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
        case 2: // Gold bar
            spr.fillRoundRect(ix-7, iy-3, 14, 7, 1, C_YELLOW);
            spr.fillRect(ix-5, iy-6, 10, 3, C_YELLOW);
            spr.drawFastVLine(ix-3, iy-5, 8, 0xFFFE);  // shine
            break;
        case 3: // CPU chip
            spr.fillRoundRect(ix-6, ix-6-iy+iy, 12, 12, 1, C_CYAN);
            // offset correction - just draw directly:
            spr.fillRoundRect(ix-6, iy-6, 12, 12, 1, C_CYAN);
            spr.fillRect(ix-3, iy-3, 6, 6, C_HDR);
            for (int p2 = -3; p2 <= 3; p2 += 3) {
                spr.fillRect(ix+p2-1, iy-9, 2, 3, C_CYAN);
                spr.fillRect(ix+p2-1, iy+6, 2, 3, C_CYAN);
            }
            break;
        case 4: // GPU rect
            spr.fillRoundRect(ix-8, iy-4, 16, 8, 1, C_ORANGE);
            spr.drawCircle(ix-2, iy, 3, C_HDR);
            break;
        case 5: // Network up/down arrows
            spr.fillTriangle(ix-6, iy+2, ix-2, iy-6, ix+2, iy+2, C_GREEN);
            spr.fillTriangle(ix+4, iy-2, ix+8, iy+6, ix+12, iy-2, C_GREEN);
            break;
        case 6: // Pomodoro tomato
            spr.fillCircle(ix, iy+2, 6, C_RED);
            spr.fillRect(ix-1, iy-5, 2, 4, C_GREEN2);
            spr.fillTriangle(ix, iy-4, ix+5, iy-7, ix+4, iy-2, C_GREEN2);
            break;
        case 7: // Settings gear icon
            spr.drawCircle(ix, iy, 5, C_PURPLE);
            spr.fillCircle(ix, iy, 2, C_HDR);
            spr.fillRect(ix-1, iy-7, 2, 14, C_PURPLE);
            spr.fillRect(ix-7, iy-1, 14, 2, C_PURPLE);
            break;
    }

    // ── Page title ────────────────────────────────────────────────────
    static const char* titles[] = {
        "Weather", "Calendar", "Finance",
        "CPU & RAM", "GPU & VRAM", "Network", "Pomodoro", "Settings"
    };
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(C_DIM, C_HDR);
    spr.drawString(titles[currentPage], 26, 13, 2);

    // ── Time HH:MM:SS (center-aligned with exact 1-2px padding around colons) ──
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
            int y = 6;

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
    drawWifiSignalIcon(246, 13, WiFi.RSSI(), network.isConnected());
    iconLink(268, 13, pcMonitor.isConnected() ? C_CYAN : C_VDIM);

    uint16_t acc = getPageAccent(currentPage);
    char pageBuf[8];
    snprintf(pageBuf, sizeof(pageBuf), "%d/%d", (int)currentPage + 1, TOTAL_PAGES);
    spr.setTextDatum(MR_DATUM);
    spr.setTextColor(acc, C_HDR);
    spr.drawString(pageBuf, 308, 13, 2);

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

void DisplayManager::drawWeatherIconVector(int16_t cx, int16_t cy, uint8_t size, uint8_t type) {
    if (size >= 48) {
        // ── LARGE 50px VECTOR WEATHER ICON (FOR MAIN WEATHER CARD) ───────────
        switch (type) {
            case 0: // 50px Sun
                spr.fillCircle(cx, cy, 14, C_ORANGE);       // Glowing outer halo
                spr.fillCircle(cx, cy, 10, C_YELLOW);       // Core sun
                spr.fillCircle(cx - 3, cy - 3, 3, C_WHITE); // Glossy highlight
                static const int8_t ix[] = { 0, 9,13, 9, 0,-9,-13,-9};
                static const int8_t iy[] = {-13,-9, 0, 9,13, 9,  0,-9};
                static const int8_t ox[] = { 0,16,21,16, 0,-16,-21,-16};
                static const int8_t oy[] = {-21,-16, 0,16,21,16,  0,-16};
                for (int i = 0; i < 8; i++) {
                    spr.drawLine(cx+ix[i], cy+iy[i], cx+ox[i], cy+oy[i], C_ORANGE);
                    spr.drawLine(cx+ix[i]+1, cy+iy[i], cx+ox[i]+1, cy+oy[i], C_YELLOW);
                }
                break;

            case 1: // 50px Sun + Cloud
                // Sun peeking top right
                spr.fillCircle(cx + 8, cy - 6, 8, C_YELLOW);
                spr.drawCircle(cx + 8, cy - 6, 11, C_ORANGE);
                // Cloud base & top
                spr.fillCircle(cx - 8, cy + 3, 8, C_CYAN);
                spr.fillCircle(cx + 8, cy + 3, 8, C_CYAN);
                spr.fillCircle(cx,     cy - 3, 8, C_WHITE);
                spr.fillRect(cx - 16, cy + 3, 32, 8, C_CYAN);
                break;

            case 2: // 50px Rain Cloud
                spr.fillCircle(cx - 8, cy - 3, 8, C_CYAN);
                spr.fillCircle(cx + 8, cy - 3, 8, C_CYAN);
                spr.fillCircle(cx,     cy - 8, 8, C_WHITE);
                spr.fillRect(cx - 16, cy - 3, 32, 8, C_CYAN);
                // 4 Slanted Cyan Raindrops
                spr.drawLine(cx - 10, cy + 6, cx - 14, cy + 15, C_CYAN);
                spr.drawLine(cx - 3,  cy + 6, cx - 7,  cy + 15, C_CYAN);
                spr.drawLine(cx + 4,  cy + 6, cx,      cy + 15, C_CYAN);
                spr.drawLine(cx + 11, cy + 6, cx + 7,  cy + 15, C_CYAN);
                break;

            default: // Thunderstorm
                spr.fillCircle(cx - 8, cy - 3, 8, C_CYAN);
                spr.fillCircle(cx + 8, cy - 3, 8, C_CYAN);
                spr.fillCircle(cx,     cy - 8, 8, C_WHITE);
                spr.fillRect(cx - 16, cy - 3, 32, 8, C_CYAN);
                // Yellow Lightning Bolt
                spr.drawLine(cx - 2, cy + 5, cx - 6, cy + 10, C_YELLOW);
                spr.drawLine(cx - 6, cy + 10, cx + 2, cy + 10, C_YELLOW);
                spr.drawLine(cx + 2, cy + 10, cx - 3, cy + 17, C_YELLOW);
                break;
        }
    } else {
        // ── SMALLER 32px VECTOR WEATHER ICON (FOR 3-DAY FORECAST COLUMNS) ───
        switch (type) {
            case 0: // 32px Multi-tone Sun
                spr.fillCircle(cx, cy, 7, C_ORANGE);
                spr.fillCircle(cx, cy, 5, C_YELLOW);
                spr.fillCircle(cx - 2, cy - 2, 2, C_WHITE);
                static const int8_t ix[] = { 0, 5, 8, 5, 0,-5,-8,-5};
                static const int8_t iy[] = {-8,-5, 0, 5, 8, 5, 0,-5};
                static const int8_t ox[] = { 0, 9,12, 9, 0,-9,-12,-9};
                static const int8_t oy[] = {-12,-9, 0, 9,12, 9, 0,-9};
                for (int i = 0; i < 8; i++) {
                    spr.drawLine(cx+ix[i], cy+iy[i], cx+ox[i], cy+oy[i], C_ORANGE);
                    spr.drawLine(cx+ix[i]+1, cy+iy[i], cx+ox[i]+1, cy+oy[i], C_YELLOW);
                }
                break;

            case 1: // 32px Sun + Cloud
                spr.fillCircle(cx + 6, cy - 4, 5, C_YELLOW);
                spr.drawCircle(cx + 6, cy - 4, 7, C_ORANGE);
                spr.fillCircle(cx - 5, cy + 2, 5, C_CYAN);
                spr.fillCircle(cx + 5, cy + 2, 5, C_CYAN);
                spr.fillCircle(cx,     cy - 2, 5, C_WHITE);
                spr.fillRect(cx - 10, cy + 2, 20, 5, C_CYAN);
                break;

            case 2: // 32px Rain Cloud
                spr.fillCircle(cx - 5, cy - 2, 5, C_CYAN);
                spr.fillCircle(cx + 5, cy - 2, 5, C_CYAN);
                spr.fillCircle(cx,     cy - 5, 5, C_WHITE);
                spr.fillRect(cx - 10, cy - 2, 20, 5, C_CYAN);
                spr.drawLine(cx - 5, cy + 4, cx - 8, cy + 10, C_CYAN);
                spr.drawLine(cx,     cy + 4, cx - 3, cy + 10, C_CYAN);
                spr.drawLine(cx + 5, cy + 4, cx + 2, cy + 10, C_CYAN);
                break;

            default:
                spr.fillCircle(cx, cy, 6, C_YELLOW);
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

    // ── Giant HH:MM clock ─────────────────────────────────────────────
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
            uint8_t iconType = i % 3; // 0=Sun, 1=Cloud, 2=Rain
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
void DisplayManager::renderPage3_PcCpuRam() {
    drawSectionTitle("PC MONITOR  CPU & RAM", C_CYAN);

    if (!pcMonitor.isConnected()) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_DIM, C_BG);
        spr.drawString("Waiting for PC connection...", 160, 130, 2);
        spr.drawString("Run pc_monitor.py on Windows", 160, 150, 2);
        iconPC(160, 100, C_VDIM);
        return;
    }

    // Two large arc gauges side-by-side
    drawArcGauge( 80, 138, 52, 9, pcMonitor.getCpuLoad(), C_CYAN,   C_TRACE, "CPU");
    drawArcGauge(240, 138, 52, 9, pcMonitor.getRamLoad(), C_ORANGE, C_TRACE, "RAM");

    // Numeric values below gauge label
    char cpuBuf[16], ramBuf[16];
    snprintf(cpuBuf, sizeof(cpuBuf), "%.0f%%", pcMonitor.getCpuLoad());
    snprintf(ramBuf, sizeof(ramBuf), "%.0f%%", pcMonitor.getRamLoad());

    // Sparkline (CPU history)
    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_DIM, C_BG);
    spr.drawString("CPU history", 14, 200, 1);
    drawSparkline(14, 210, 292, 26, pcMonitor.getCpuHistory(), PCMonitor::HISTORY_SIZE, C_CYAN);
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 4 — PC MONITOR: GPU & VRAM
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage4_PcGpuVram() {
    drawSectionTitle("PC MONITOR  GPU & VRAM", C_ORANGE);

    if (!pcMonitor.isConnected()) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_DIM, C_BG);
        spr.drawString("Waiting for PC connection...", 160, 130, 2);
        return;
    }

    drawArcGauge( 80, 138, 52, 9, pcMonitor.getGpuLoad(),  C_ORANGE, C_TRACE, "GPU");
    drawArcGauge(240, 138, 52, 9, pcMonitor.getVramLoad(), C_GREEN,  C_TRACE, "VRAM");

    spr.setTextDatum(TL_DATUM);
    spr.setTextColor(C_DIM, C_BG);
    spr.drawString("GPU history", 14, 200, 1);
    drawSparkline(14, 210, 292, 26, pcMonitor.getGpuHistory(), PCMonitor::HISTORY_SIZE, C_ORANGE);
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 5 — PC NETWORK & DISKS
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage5_PcNetDisks() {
    drawSectionTitle("NETWORK & DISK", C_GREEN);

    if (!pcMonitor.isConnected()) {
        spr.setTextDatum(MC_DATUM);
        spr.setTextColor(C_DIM, C_BG);
        spr.drawString("Waiting for PC connection...", 160, 130, 2);
        return;
    }

    // ── Network speeds card ───────────────────────────────────────────
    spr.fillRoundRect(10, 52, 300, 42, 5, C_CARD);

    iconNet(35, 73, C_GREEN);

    char netBuf[64];
    snprintf(netBuf, sizeof(netBuf), "DL: %u KB/s    UL: %u KB/s",
             pcMonitor.getNetDownSpeed(), pcMonitor.getNetUpSpeed());
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.drawString(netBuf, 60, 73, 2);

    // ── Disk bars ─────────────────────────────────────────────────────
    uint8_t cnt  = pcMonitor.getDiskCount();
    const DiskInfo* disks = pcMonitor.getDisks();

    for (int i = 0; i < (int)cnt && i < 3; i++) {
        int cardY = 104 + i * 44;
        spr.fillRoundRect(10, cardY, 300, 36, 5, C_CARD);

        char label[16];
        snprintf(label, sizeof(label), " %s:", disks[i].name);
        spr.setTextDatum(ML_DATUM);
        spr.setTextColor(C_WHITE, C_CARD);
        spr.drawString(label, 14, cardY + 10, 2);

        // Progress bar
        drawHorizBar(90, cardY + 6, 188, 14, disks[i].usedPercent, C_CYAN);

        // Percent text
        char pStr[8];
        snprintf(pStr, sizeof(pStr), "%d%%", disks[i].usedPercent);
        spr.setTextDatum(MR_DATUM);
        spr.setTextColor(C_DIM, C_CARD);
        spr.drawString(pStr, 304, cardY + 18, 1);
    }
}

// ─────────────────────────────────────────────────────────────────────
//  PAGE 6 — POMODORO & DESK UTILITIES
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderPage6_DeskUtilities() {

    // ── Large Pomodoro ring ───────────────────────────────────────────
    uint16_t remSec   = deskUtils.getPomodoroRemainingSeconds();
    uint16_t totalSec = 25 * 60;  // default 25 min session
    float    pct      = (float)remSec / totalSec * 100.0f;
    pct = constrain(pct, 0.0f, 100.0f);

    // Outer glow ring (slightly larger, dim)
    spr.drawArc(160, 128, 75, 71, 0, 359, C_TRACE, C_BG, false);
    // Track ring
    spr.drawArc(160, 128, 72, 63, 0, 359, C_TRACE, C_BG, false);
    // Progress arc (orange → green when low)
    uint16_t ringColor = (remSec < 300) ? C_GREEN : C_ORANGE;
    uint32_t endDeg = (uint32_t)(pct * 3.6f);
    if (endDeg > 0)
        spr.drawArc(160, 128, 72, 63, 0, min(endDeg, (uint32_t)359), ringColor, C_BG, false);

    // Pomodoro icon at top of ring
    iconPomodoro(160, 62);

    // Timer text inside ring
    uint16_t mins = remSec / 60;
    uint16_t secs = remSec % 60;
    char timeStr[8];
    snprintf(timeStr, sizeof(timeStr), "%02d:%02d", mins, secs);
    spr.setTextDatum(MC_DATUM);
    spr.setTextColor(ringColor, C_BG);
    spr.drawString(timeStr, 160, 130, 7);  // Giant font 7

    // State label
    spr.setTextColor(C_DIM, C_BG);
    spr.drawString(deskUtils.getPomodoroStateString(), 160, 165, 2);

    // ── Tap hint ──────────────────────────────────────────────────────
    spr.setTextColor(C_VDIM, C_BG);
    spr.drawString("Tap screen to Start / Pause", 160, 196, 1);

    // ── Alarm status bar ──────────────────────────────────────────────
    spr.fillRoundRect(10, 208, 300, 26, 5, C_CARD);
    iconBell(30, 221, deskUtils.isAlarmEnabled() ? C_ORANGE : C_VDIM);

    char alarmBuf[40];
    if (deskUtils.isAlarmEnabled()) {
        snprintf(alarmBuf, sizeof(alarmBuf), "Alarm ON: %02d:%02d",
                 deskUtils.getAlarmHour(), deskUtils.getAlarmMinute());
    } else {
        strcpy(alarmBuf, "Alarm: OFF");
    }
    spr.setTextDatum(ML_DATUM);
    spr.setTextColor(deskUtils.isAlarmEnabled() ? C_ORANGE : C_DIM, C_CARD);
    spr.drawString(alarmBuf, 50, 221, 2);

    // Alarm ringing flash effect
    if (deskUtils.isAlarmRinging()) {
        uint16_t flash = (millis() / 300) % 2 ? C_RED : C_BG;
        spr.drawRoundRect(10, 208, 300, 26, 5, flash);
        spr.setTextDatum(MR_DATUM);
        spr.setTextColor(C_RED, C_CARD);
        spr.drawString("TAP TO DISMISS!", 300, 221, 1);
    }
}

// ─────────────────────────────────────────────────────────────────────
//  UI WIDGETS
// ─────────────────────────────────────────────────────────────────────

void DisplayManager::drawSectionTitle(const char* title, uint16_t color) {
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(color, C_BG);
    spr.drawString(title, 160, 34, 2);
    spr.drawFastHLine(20, 48, 280, color);
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
    spr.drawRoundRect(x, y, w, h, 2, C_TRACE);
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
    spr.fillCircle(cx, cy-6, 3, color);
    spr.fillRoundRect(cx-8, cy-5, 16, 12, 3, color);
    spr.fillTriangle(cx-9, cy+7, cx+9, cy+7, cx, cy+4, color);
    spr.fillCircle(cx, cy+9, 2, color);
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
//  PAGE 7 — Settings Page
// ═══════════════════════════════════════════════════════════════════════
void DisplayManager::renderPage7_Settings() {
    // Title
    spr.setTextColor(C_WHITE, C_BG);
    spr.setTextDatum(TC_DATUM);
    spr.drawString("SETTINGS", 160, 32, 2);

    int y = 60;
    int itemH = 28;

    // Menu Item 1: Calibrate Touch (y = 60..88)
    spr.fillRoundRect(20, y, 280, 24, 4, C_CARD);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.drawString("Calibrate Touch", 30, y + 12, 2);
    spr.setTextColor(C_DIM, C_CARD);
    spr.setTextDatum(MR_DATUM);
    spr.drawString(touch.isCalibrated() ? "OK" : "Not Set", 290, y + 12, 2);
    y += itemH;

    // Menu Item 2: Auto Brightness (y = 88..116)
    spr.fillRoundRect(20, y, 280, 24, 4, C_CARD);
    spr.setTextColor(C_CYAN, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.drawString("Auto Brightness", 30, y + 12, 2);
    spr.setTextColor(C_DIM, C_CARD);
    spr.setTextDatum(MR_DATUM);
    spr.drawString(hardware.isAutoBrightnessEnabled() ? "ON" : "OFF", 290, y + 12, 2);
    y += itemH;

    // Menu Item 3: WiFi SSID
    spr.fillRoundRect(20, y, 280, 24, 4, C_CARD);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.drawString("WiFi", 30, y + 12, 2);
    spr.setTextColor(C_DIM, C_CARD);
    spr.setTextDatum(MR_DATUM);
    spr.drawString(WiFi.isConnected() ? WiFi.SSID().c_str() : "N/A", 290, y + 12, 2);
    y += itemH;

    // Menu Item 4: IP Address
    spr.fillRoundRect(20, y, 280, 24, 4, C_CARD);
    spr.setTextColor(C_GREEN, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.drawString("IP Address", 30, y + 12, 2);
    spr.setTextColor(C_DIM, C_CARD);
    spr.setTextDatum(MR_DATUM);
    spr.drawString(WiFi.isConnected() ? WiFi.localIP().toString().c_str() : "N/A", 290, y + 12, 2);
    y += itemH;

    // Menu Item 5: Touch Type
    spr.fillRoundRect(20, y, 280, 24, 4, C_CARD);
    spr.setTextColor(C_PURPLE, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.drawString("Touch Type", 30, y + 12, 2);
    spr.setTextColor(C_DIM, C_CARD);
    spr.setTextDatum(MR_DATUM);
    spr.drawString(touch.getTouchTypeString(), 290, y + 12, 2);
    y += itemH;

    // Menu Item 6: Firmware Version
    spr.fillRoundRect(20, y, 280, 24, 4, C_CARD);
    spr.setTextColor(C_ORANGE, C_CARD);
    spr.setTextDatum(ML_DATUM);
    spr.drawString("Firmware", 30, y + 12, 2);
    spr.setTextColor(C_DIM, C_CARD);
    spr.setTextDatum(MR_DATUM);
    spr.drawString("v1.0.0", 290, y + 12, 2);
}

// ─────────────────────────────────────────────────────────────────────
//  FULLSCREEN CHART DETAIL MODAL OVERLAY
// ─────────────────────────────────────────────────────────────────────
void DisplayManager::renderDetailModal() {
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
        for (int i = 1; i < 7; i++) {
            if (dataPtr[i] < minVal) minVal = dataPtr[i];
            if (dataPtr[i] > maxVal) maxVal = dataPtr[i];
        }
        float range = maxVal - minVal;
        if (range < 0.05f) range = 0.5f;

        for (int i = 0; i < 6; i++) {
            int x1 = cx + 14 + (int)(i * stepX);
            int y1 = cy + ch - 24 - (int)(((dataPtr[i] - minVal) / range) * (ch - 46));
            int x2 = cx + 14 + (int)((i + 1) * stepX);
            int y2 = cy + ch - 24 - (int)(((dataPtr[i + 1] - minVal) / range) * (ch - 46));
            y1 = constrain(y1, cy + 16, cy + ch - 24);
            y2 = constrain(y2, cy + 16, cy + ch - 24);

            spr.drawLine(x1, y1, x2, y2, themeColor);
            spr.drawLine(x1, y1 + 1, x2, y2 + 1, themeColor); // Bold 2px line
        }

        // Draw Dot points & Price text badges
        for (int i = 0; i < 7; i++) {
            int px = cx + 14 + (int)(i * stepX);
            int py = cy + ch - 24 - (int)(((dataPtr[i] - minVal) / range) * (ch - 46));
            py = constrain(py, cy + 16, cy + ch - 24);

            spr.fillCircle(px, py, 3, C_WHITE);
            spr.drawCircle(px, py, 4, themeColor);

            // Print price text above dot
            char pBuf[16];
            if (isMoneyFormat) {
                snprintf(pBuf, sizeof(pBuf), "%.0f", dataPtr[i]);
            } else {
                snprintf(pBuf, sizeof(pBuf), "%.1f", dataPtr[i]);
            }
            spr.setTextDatum(BC_DATUM);
            spr.setTextColor(C_WHITE, C_CARD);
            spr.drawString(pBuf, px, py - 5, 1);
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

    // ── Main Header Title (1 Line Font 2, Gold text, perfectly centered) ─
    spr.setTextDatum(TC_DATUM);
    spr.setTextColor(C_YELLOW, C_CARD);
    spr.drawString("SMART DESK DASHBOARD", 160, 24, 2);

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
