#ifndef DYNAMIC_SKIN_MANAGER_H
#define DYNAMIC_SKIN_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <FS.h>
#include <LittleFS.h>

struct DynamicElement {
    String id;
    String name;
    String type;
    String content;
    String fontStyle;
    uint16_t x;
    uint16_t y;
    uint16_t w;
    uint16_t h;
    uint16_t color;
};

class DynamicSkinManager {
public:
    DynamicSkinManager();
    bool begin();
    bool parseAndSaveSkinJSON(const String& jsonPayload);
    bool loadActiveSkinFromFlash();
    void renderCurrentPageSkin(TFT_eSPI& tft, uint8_t currentPage);

    bool isCustomSkinActive() const { return _isSkinLoaded; }

private:
    bool _isSkinLoaded;
    String _skinName;
    uint16_t _bgColor;
    // Map page_index (0..7) to list of elements
    std::vector<DynamicElement> _pageElements[8];

    uint16_t parseHexColor(const char* hexStr);
    void drawDotMatrixText(TFT_eSPI& tft, const String& text, uint16_t x, uint16_t y, uint16_t color);
    void draw7SegmentText(TFT_eSPI& tft, const String& text, uint16_t x, uint16_t y, uint16_t color);
    void drawPixelSun(TFT_eSPI& tft, uint16_t x, uint16_t y, uint16_t color);
    void drawPixelSunrise(TFT_eSPI& tft, uint16_t x, uint16_t y, uint16_t color);
};

extern DynamicSkinManager g_skinMgr;

#endif // DYNAMIC_SKIN_MANAGER_H
