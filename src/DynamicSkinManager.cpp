#include "DynamicSkinManager.h"
#include "NetworkManager.h"
#include "vn_lunar.h"
#include <time.h>

DynamicSkinManager g_skinMgr;

DynamicSkinManager::DynamicSkinManager()
    : _isSkinLoaded(false), _bgColor(TFT_BLACK), _cachedPageIdx(255) {
}

bool DynamicSkinManager::begin() {
    if (!LittleFS.begin(true)) {
        Serial.println("[SkinMgr] LittleFS Mount Failed");
        return false;
    }
    resetToDefaultSkin();
    return true;
}

void DynamicSkinManager::resetToDefaultSkin() {
    if (LittleFS.exists("/active_skin.json")) {
        LittleFS.remove("/active_skin.json");
    }
    _cachedElements.clear();
    _cachedPageIdx = 255;
    _isSkinLoaded = false;
    Serial.println("[SkinMgr] Reset to default native C++ UI!");
}

uint16_t DynamicSkinManager::parseHexColor(const char* hexStr) {
    if (!hexStr || hexStr[0] == '\0') return TFT_WHITE;
    if (hexStr[0] == '#') hexStr++;
    uint32_t rgb = strtoul(hexStr, NULL, 16);
    uint8_t r = (rgb >> 16) & 0xFF;
    uint8_t g = (rgb >> 8) & 0xFF;
    uint8_t b = rgb & 0xFF;
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

bool DynamicSkinManager::parseAndSaveSkinJSON(const String& jsonPayload) {
    File f = LittleFS.open("/active_skin.json", "w");
    if (!f) {
        Serial.println("[SkinMgr] Failed to open /active_skin.json for writing");
        return false;
    }

    f.print(jsonPayload);
    f.close();
    Serial.println("[SkinMgr] Skin payload saved to Flash LittleFS!");

    _cachedPageIdx = 255; // Reset page cache
    _cachedElements.clear();
    _isSkinLoaded = true;

    return loadElementsForPage(0);
}

bool DynamicSkinManager::loadActiveSkinFromFlash() {
    if (!LittleFS.exists("/active_skin.json")) {
        return false;
    }

    _cachedPageIdx = 255;
    _cachedElements.clear();
    _isSkinLoaded = true;
    Serial.println("[SkinMgr] Custom skin detected on Flash LittleFS!");
    return loadElementsForPage(0);
}

bool DynamicSkinManager::loadElementsForPage(uint8_t pageIdx) {
    if (!_isSkinLoaded || pageIdx >= 8) return false;
    if (_cachedPageIdx == pageIdx) return true; // Already cached in RAM!

    File f = LittleFS.open("/active_skin.json", "r");
    if (!f) return false;

    String content = f.readString();
    f.close();

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, content);

    if (err) {
        Serial.printf("[SkinMgr] Page Parse JSON Error: %s (len=%d)\n", err.c_str(), (int)content.length());
        return false;
    }

    _skinName = doc["skin_name"] | "Custom Skin";
    _bgColor = parseHexColor(doc["canvas"]["bg_color"] | "#000000");

    _cachedElements.clear();
    _cachedPageIdx = pageIdx;

    JsonObject pages = doc["pages"].as<JsonObject>();
    if (!pages.isNull()) {
        for (JsonPair p : pages) {
            int pIdx = atoi(p.key().c_str());
            if (pIdx == (int)pageIdx) {
                JsonArray elements = p.value()["elements"].as<JsonArray>();
                for (JsonObject el : elements) {
                    DynamicElement de;
                    de.id = el["id"] | "";
                    de.name = el["name"] | "";
                    de.type = el["type"] | "text";
                    de.content = el["content"] | "";
                    de.fontStyle = el["font_style"] | "default";
                    de.x = el["x"] | 0;
                    de.y = el["y"] | 0;
                    de.w = el["w"] | 50;
                    de.h = el["h"] | 20;
                    de.color = parseHexColor(el["color"] | "#FFFFFF");
                    de.fontSize = el["font_size"] | 12;
                    _cachedElements.push_back(de);
                }
                break;
            }
        }
    }

    Serial.printf("[SkinMgr] Loaded Page %d (%d elements) into RAM cache! Heap: %u\n",
                  pageIdx, (int)_cachedElements.size(), ESP.getFreeHeap());
    return true;
}

void DynamicSkinManager::renderCurrentPageSkin(TFT_eSprite& spr, uint8_t currentPage) {
    if (!_isSkinLoaded || currentPage >= 8) return;

    if (_cachedPageIdx != currentPage) {
        loadElementsForPage(currentPage);
    }

    spr.fillSprite(_bgColor);

    // Render containers first
    for (const auto& el : _cachedElements) {
        if (el.type == "rectangle" || el.type == "box") {
            uint16_t borderCol = (el.color == parseHexColor("#1E293B")) ? TFT_CYAN : parseHexColor("#1F2937");
            spr.fillRoundRect(el.x, el.y, el.w, el.h, 6, el.color);
            spr.drawRoundRect(el.x, el.y, el.w, el.h, 6, borderCol);
        } else if (el.type == "circle") {
            spr.fillCircle(el.x + el.w / 2, el.y + el.h / 2, el.w / 2, el.color);
        } else if (el.type == "line") {
            spr.drawFastHLine(el.x, el.y, el.w, el.color);
        } else if (el.type == "dot_matrix_divider") {
            for (int dx = el.x; dx < el.x + el.w; dx += 6) {
                spr.fillCircle(dx, el.y + el.h / 2, 1, el.color);
            }
        } else if (el.type == "line_chart") {
            spr.fillRoundRect(el.x, el.y, el.w, el.h, 4, parseHexColor("#050811"));
            spr.drawRoundRect(el.x, el.y, el.w, el.h, 4, parseHexColor("#1F2937"));
            for (int i = 0; i < el.w - 10; i += 8) {
                int py1 = el.y + el.h - 8 - (int)(sin(i * 0.2) * (el.h * 0.35) + (el.h * 0.35));
                int py2 = el.y + el.h - 8 - (int)(sin((i + 8) * 0.2) * (el.h * 0.35) + (el.h * 0.35));
                spr.drawLine(el.x + 5 + i, py1, el.x + 5 + i + 8, py2, el.color);
            }
        }
    }

    // Render icons, badges, and text on top
    for (const auto& el : _cachedElements) {
        if (el.type == "rectangle" || el.type == "box" || el.type == "circle" || el.type == "line" || el.type == "dot_matrix_divider" || el.type == "line_chart") {
            continue; // Already rendered in container pass
        }

        if (el.type == "pixel_sun") {
            drawPixelSun(spr, el.x, el.y, el.color);
        } else if (el.type == "pixel_sunrise") {
            drawPixelSunrise(spr, el.x, el.y, el.color);
        } else if (el.type == "status_time") {
            struct tm timeinfo;
            char timeStr[16] = "17:29:17";
            if (getLocalTime(&timeinfo)) {
                strftime(timeStr, sizeof(timeStr), "%H:%M:%S", &timeinfo);
            }
            spr.setTextColor(el.color, _bgColor);
            spr.setTextDatum(ML_DATUM);
            spr.drawString(timeStr, el.x, el.y + el.h / 2, 2);
            spr.setTextDatum(TL_DATUM);
        } else if (el.type == "status_serial") {
            spr.setTextColor(el.color, _bgColor);
            spr.setTextDatum(ML_DATUM);
            spr.drawString("COM4", el.x, el.y + el.h / 2, 2);
            spr.setTextDatum(TL_DATUM);
        } else if (el.type == "page_counter") {
            char pStr[10];
            snprintf(pStr, sizeof(pStr), "%d/8", currentPage + 1);
            spr.setTextColor(el.color, _bgColor);
            spr.setTextDatum(ML_DATUM);
            spr.drawString(pStr, el.x, el.y + el.h / 2, 2);
            spr.setTextDatum(TL_DATUM);
        } else if (el.type == "wifi_signal") {
            spr.setTextColor(el.color, _bgColor);
            spr.setTextDatum(ML_DATUM);
            spr.drawString(el.content.length() > 0 ? el.content.c_str() : "-54dBm", el.x, el.y + el.h / 2, 1);
            spr.setTextDatum(TL_DATUM);
        } else if (el.fontStyle == "dot_matrix" || el.type == "matrix_text") {
            drawDotMatrixText(spr, el.content, el.x, el.y, el.w, el.h, el.color);
        } else if (el.fontStyle == "segment7") {
            draw7SegmentText(spr, el.content, el.x, el.y, el.color);
        } else {
            String text = el.content;

            // Live Dynamic Token Replacement
            if (text.indexOf("Mon 10/08/2026") != -1 || text.indexOf("18/07 Lunar") != -1 || text.indexOf("Solar:") != -1) {
                struct tm timeinfo;
                if (getLocalTime(&timeinfo)) {
                    static const char* days[] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};
                    char buf[64];
                    vn_lunar lunar;
                    lunar.convertSolar2Lunar(timeinfo.tm_mday, timeinfo.tm_mon + 1, timeinfo.tm_year + 1900);
                    snprintf(buf, sizeof(buf), "%s %02d/%02d/%04d • %02d/%02d Lunar",
                             days[timeinfo.tm_wday], timeinfo.tm_mday, timeinfo.tm_mon + 1, timeinfo.tm_year + 1900,
                             lunar.get_lunar_dd(), lunar.get_lunar_mm());
                    text = String(buf);
                }
            } else if (text.indexOf("28°C Hanoi") != -1 || text.indexOf("28C Hanoi") != -1) {
                WeatherData w = network.getWeather();
                if (w.valid) {
                    char wBuf[32];
                    snprintf(wBuf, sizeof(wBuf), "%.0fC %s", w.temp, w.city[0] ? w.city : "Hanoi");
                    text = String(wBuf);
                }
            }

            uint8_t fontNum = 2;
            if (el.fontSize >= 24) fontNum = 6;
            else if (el.fontSize >= 18) fontNum = 4;
            else if (el.fontSize >= 14) fontNum = 2;
            else fontNum = 2;

            spr.setTextColor(el.color, _bgColor);
            bool isCentered = (el.w >= 40 && text.length() <= 8 && text.indexOf('\n') == -1);
            if (isCentered) {
                spr.setTextDatum(MC_DATUM);
                spr.drawString(text, el.x + el.w / 2, el.y + el.h / 2, fontNum);
                spr.setTextDatum(TL_DATUM);
            } else {
                spr.setTextDatum(ML_DATUM);
                spr.drawString(text, el.x, el.y + el.h / 2, fontNum);
                spr.setTextDatum(TL_DATUM);
            }
        }
    }
}

// 5x7 Dot Matrix Font bitmaps for digits 0-9 and colon :
static const uint8_t PROGMEM matrix_font_5x7[][5] = {
    {0x3E, 0x51, 0x49, 0x45, 0x3E}, // 0
    {0x00, 0x42, 0x7F, 0x40, 0x00}, // 1
    {0x42, 0x61, 0x51, 0x49, 0x46}, // 2
    {0x21, 0x41, 0x45, 0x4B, 0x31}, // 3
    {0x18, 0x14, 0x12, 0x7F, 0x10}, // 4
    {0x27, 0x45, 0x45, 0x45, 0x39}, // 5
    {0x3C, 0x4A, 0x49, 0x49, 0x30}, // 6
    {0x01, 0x71, 0x09, 0x05, 0x03}, // 7
    {0x36, 0x49, 0x49, 0x49, 0x36}, // 8
    {0x06, 0x49, 0x49, 0x29, 0x1E}, // 9
    {0x00, 0x36, 0x36, 0x00, 0x00}  // :
};

void DynamicSkinManager::drawDotMatrixText(TFT_eSprite& spr, const String& rawText, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color) {
    String text = rawText;
    if (text.indexOf(":") != -1 || text == "14:35:08" || text == "17:29:17") {
        struct tm timeinfo;
        if (getLocalTime(&timeinfo)) {
            char timeBuf[16];
            strftime(timeBuf, sizeof(timeBuf), "%H:%M:%S", &timeinfo);
            text = String(timeBuf);
        }
    }

    uint16_t dotRadius = 2;
    uint16_t pitch = 6;

    // Calculate total rendered width of dot matrix text
    uint16_t totalW = 0;
    for (size_t i = 0; i < text.length(); i++) {
        char c = text[i];
        if ((c >= '0' && c <= '9') || c == ':') {
            totalW += 5 * pitch + 6;
        } else {
            totalW += 16;
        }
    }
    if (totalW > 6) totalW -= 6; // Remove last trailing gap

    // Center horizontally and vertically inside element bounding box [x, y, w, h]
    uint16_t startX = (w > totalW) ? (x + (w - totalW) / 2) : x;
    uint16_t startY = (h > 42) ? (y + (h - 42) / 2) : y;

    uint16_t curX = startX;

    for (size_t i = 0; i < text.length(); i++) {
        char c = text[i];
        int fontIdx = -1;
        if (c >= '0' && c <= '9') fontIdx = c - '0';
        else if (c == ':') fontIdx = 10;

        if (fontIdx >= 0) {
            for (int col = 0; col < 5; col++) {
                uint8_t colData = pgm_read_byte(&matrix_font_5x7[fontIdx][col]);
                for (int row = 0; row < 7; row++) {
                    if (colData & (1 << row)) {
                        spr.fillCircle(curX + col * pitch + dotRadius, startY + row * pitch + dotRadius, dotRadius, color);
                    } else {
                        spr.fillCircle(curX + col * pitch + dotRadius, startY + row * pitch + dotRadius, 1, parseHexColor("#121212"));
                    }
                }
            }
            curX += 5 * pitch + 6;
        } else {
            spr.setTextColor(color, _bgColor);
            spr.drawString(String(c), curX, startY, 4);
            curX += 16;
        }
    }
}

void DynamicSkinManager::draw7SegmentText(TFT_eSprite& spr, const String& text, uint16_t x, uint16_t y, uint16_t color) {
    spr.setTextColor(color, _bgColor);
    spr.drawString(text, x, y, 7);
}

void DynamicSkinManager::drawPixelSun(TFT_eSprite& spr, uint16_t x, uint16_t y, uint16_t color) {
    static const uint8_t PROGMEM sun_grid[6][6] = {
        {0, 1, 1, 1, 1, 0},
        {1, 1, 1, 1, 1, 1},
        {1, 1, 1, 1, 1, 1},
        {1, 1, 1, 1, 1, 1},
        {1, 1, 1, 1, 1, 1},
        {0, 1, 1, 1, 1, 0}
    };
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (sun_grid[r][c]) {
                spr.fillCircle(x + c * 6 + 3, y + r * 6 + 3, 2, color);
            }
        }
    }
}

void DynamicSkinManager::drawPixelSunrise(TFT_eSprite& spr, uint16_t x, uint16_t y, uint16_t color) {
    spr.fillCircle(x + 12, y + 12, 8, color);
    spr.drawFastHLine(x, y + 20, 24, color);
}
