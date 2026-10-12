#ifndef DYNAMIC_SKIN_MANAGER_H
#define DYNAMIC_SKIN_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>
#include <FS.h>
#include <LittleFS.h>
#include <vector>

using fs::File;

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
    uint8_t fontSize;
};

class DynamicSkinManager {
public:
    DynamicSkinManager();
    bool begin();
    bool saveSkinJSONChunked(File& file, const String& jsonPayload);
    bool parseAndSaveSkinJSON(const String& jsonPayload);
    bool loadActiveSkinFromFlash();
    void resetToDefaultSkin();
    void renderCurrentPageSkin(TFT_eSprite& spr, uint8_t currentPage);

    bool isCustomSkinActive() const { return _isSkinLoaded; }

private:
    bool _isSkinLoaded;
    String _skinName;
    uint16_t _bgColor;
    uint8_t _cachedPageIdx;
    std::vector<DynamicElement> _cachedElements;

    bool loadElementsForPage(uint8_t pageIdx);
    uint16_t parseHexColor(const char* hexStr);
    void drawDotMatrixText(TFT_eSprite& spr, const String& text, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color);
    void draw7SegmentText(TFT_eSprite& spr, const String& text, uint16_t x, uint16_t y, uint16_t color);
    void drawPixelSun(TFT_eSprite& spr, uint16_t x, uint16_t y, uint16_t color);
    void drawPixelSunrise(TFT_eSprite& spr, uint16_t x, uint16_t y, uint16_t color);
};

extern DynamicSkinManager g_skinMgr;

#endif // DYNAMIC_SKIN_MANAGER_H
