#include "DynamicSkinManager.h"

DynamicSkinManager g_skinMgr;

DynamicSkinManager::DynamicSkinManager() : _isSkinLoaded(false), _bgColor(TFT_BLACK) {
}

bool DynamicSkinManager::begin() {
    if (!LittleFS.begin(true)) {
        Serial.println("[SkinMgr] LittleFS Mount Failed");
        return false;
    }
    return loadActiveSkinFromFlash();
}

uint16_t DynamicSkinManager::parseHexColor(const char* hexStr) {
    if (!hexStr || hexStr[0] == '\0') return TFT_WHITE;
    if (hexStr[0] == '#') hexStr++;
    uint32_t rgb = strtoul(hexStr, NULL, 16);
    uint8_t r = (rgb >> 16) & 0xFF;
    uint8_t g = (rgb >> 8) & 0xFF;
    uint8_t b = rgb & 0xFF;
    // Convert 24-bit RGB888 to 16-bit RGB565 for TFT_eSPI
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

bool DynamicSkinManager::parseAndSaveSkinJSON(const String& jsonPayload) {
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, jsonPayload);
    if (err) {
        Serial.printf("[SkinMgr] JSON Parse Error: %s\n", err.c_str());
        return false;
    }

    _skinName = doc["skin_name"] | "Custom Skin";
    _bgColor = parseHexColor(doc["canvas"]["bg_color"] | "#000000");

    // Clear existing page elements
    for (int i = 0; i < 8; i++) {
        _pageElements[i].clear();
    }

    JsonObject pages = doc["pages"].as<JsonObject>();
    for (JsonPair p : pages) {
        int pageIdx = atoi(p.key().c_str());
        if (pageIdx < 0 || pageIdx >= 8) continue;

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
            _pageElements[pageIdx].push_back(de);
        }
    }

    _isSkinLoaded = true;

    // Save payload to LittleFS for persistence across reboots
    File f = LittleFS.open("/active_skin.json", "w");
    if (f) {
        f.print(jsonPayload);
        f.close();
        Serial.println("[SkinMgr] Skin payload saved to /active_skin.json");
    }

    return true;
}

bool DynamicSkinManager::loadActiveSkinFromFlash() {
    if (!LittleFS.exists("/active_skin.json")) {
        return false;
    }
    File f = LittleFS.open("/active_skin.json", "r");
    if (!f) return false;
    String content = f.readString();
    f.close();
    return parseAndSaveSkinJSON(content);
}

void DynamicSkinManager::renderCurrentPageSkin(TFT_eSPI& tft, uint8_t currentPage) {
    if (!_isSkinLoaded || currentPage >= 8) return;

    tft.fillScreen(_bgColor);

    for (const auto& el : _pageElements[currentPage]) {
        if (el.type == "pixel_sun") {
            drawPixelSun(tft, el.x, el.y, el.color);
        } else if (el.type == "pixel_sunrise") {
            drawPixelSunrise(tft, el.x, el.y, el.color);
        } else if (el.fontStyle == "dot_matrix" || el.type == "matrix_text") {
            drawDotMatrixText(tft, el.content, el.x, el.y, el.color);
        } else if (el.fontStyle == "segment7") {
            draw7SegmentText(tft, el.content, el.x, el.y, el.color);
        } else {
            tft.setTextColor(el.color, _bgColor);
            tft.drawString(el.content, el.x, el.y);
        }
    }
}

void DynamicSkinManager::drawDotMatrixText(TFT_eSPI& tft, const String& text, uint16_t x, uint16_t y, uint16_t color) {
    tft.setTextColor(color, _bgColor);
    tft.drawString(text, x, y, 2);
}

void DynamicSkinManager::draw7SegmentText(TFT_eSPI& tft, const String& text, uint16_t x, uint16_t y, uint16_t color) {
    tft.setTextColor(color, _bgColor);
    tft.drawString(text, x, y, 4);
}

void DynamicSkinManager::drawPixelSun(TFT_eSPI& tft, uint16_t x, uint16_t y, uint16_t color) {
    tft.fillCircle(x + 12, y + 12, 10, color);
}

void DynamicSkinManager::drawPixelSunrise(TFT_eSPI& tft, uint16_t x, uint16_t y, uint16_t color) {
    tft.fillCircle(x + 12, y + 12, 8, color);
    tft.drawFastHLine(x, y + 20, 24, color);
}
