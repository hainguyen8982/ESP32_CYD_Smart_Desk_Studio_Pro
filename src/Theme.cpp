// ═══════════════════════════════════════════════════════════════════════
//  Theme.cpp — Runtime theme implementation
// ═══════════════════════════════════════════════════════════════════════
#include "Theme.h"
#include <stdlib.h>

// Global theme instance — default is Ocean Dark
ThemeColors theme;

// ─────────────────────────────────────────────────────────────────────
//  Color Conversion Utilities
// ─────────────────────────────────────────────────────────────────────
uint16_t hexToRGB565(const char* hex) {
    if (!hex) return 0x0000;
    if (hex[0] == '#') hex++;
    uint32_t rgb = strtoul(hex, nullptr, 16);
    uint8_t r = (rgb >> 16) & 0xFF;
    uint8_t g = (rgb >>  8) & 0xFF;
    uint8_t b = (rgb >>  0) & 0xFF;
    return ((uint16_t)(r >> 3) << 11) |
           ((uint16_t)(g >> 2) <<  5) |
           ((uint16_t)(b >> 3));
}

void rgb565ToHex(uint16_t color, char* buf) {
    uint8_t r5 = (color >> 11) & 0x1F;
    uint8_t g6 = (color >>  5) & 0x3F;
    uint8_t b5 = (color >>  0) & 0x1F;
    // Expand to 8-bit
    uint8_t r = (r5 << 3) | (r5 >> 2);
    uint8_t g = (g6 << 2) | (g6 >> 4);
    uint8_t b = (b5 << 3) | (b5 >> 2);
    snprintf(buf, 8, "#%02X%02X%02X", r, g, b);
}

// ─────────────────────────────────────────────────────────────────────
//  NVS Persistence
// ─────────────────────────────────────────────────────────────────────
static Preferences prefs;

void saveTheme() {
    prefs.begin("theme", false);
    prefs.putBool("valid",    true);
    prefs.putUShort("bg",     theme.bg);
    prefs.putUShort("card",   theme.card);
    prefs.putUShort("hdr",    theme.hdr);
    prefs.putUShort("cyan",   theme.cyan);
    prefs.putUShort("orange", theme.orange);
    prefs.putUShort("green",  theme.green);
    prefs.putUShort("yellow", theme.yellow);
    prefs.putUShort("red",    theme.red);
    prefs.putUShort("purple", theme.purple);
    prefs.putUShort("white",  theme.white);
    prefs.putUShort("dim",    theme.dim);
    prefs.putUShort("vdim",   theme.vdim);
    prefs.putUShort("trace",  theme.trace);
    prefs.end();
    Serial.println("[Theme] Saved to NVS");
}

void loadTheme() {
    applyOceanDarkTheme();  // set defaults first
    prefs.begin("theme", true);
    if (prefs.isKey("valid") && prefs.getBool("valid", false)) {
        theme.bg     = prefs.getUShort("bg",     theme.bg);
        theme.card   = prefs.getUShort("card",   theme.card);
        theme.hdr    = prefs.getUShort("hdr",    theme.hdr);
        theme.cyan   = prefs.getUShort("cyan",   theme.cyan);
        theme.orange = prefs.getUShort("orange", theme.orange);
        theme.green  = prefs.getUShort("green",  theme.green);
        theme.yellow = prefs.getUShort("yellow", theme.yellow);
        theme.red    = prefs.getUShort("red",    theme.red);
        theme.purple = prefs.getUShort("purple", theme.purple);
        theme.white  = prefs.getUShort("white",  theme.white);
        theme.dim    = prefs.getUShort("dim",    theme.dim);
        theme.vdim   = prefs.getUShort("vdim",   theme.vdim);
        theme.trace  = prefs.getUShort("trace",  theme.trace);
        
        // Safety check: if bg is white or card equals bg, fallback to Ocean Dark
        if (theme.bg == 0xFFFF || theme.bg == theme.white) {
            applyOceanDarkTheme();
        }
        Serial.println("[Theme] Loaded from NVS");
    } else {
        Serial.println("[Theme] No valid saved theme, using Ocean Dark default");
    }
    prefs.end();
}

// ─────────────────────────────────────────────────────────────────────
//  Built-in Preset Themes
// ─────────────────────────────────────────────────────────────────────

// 🌊 Ocean Dark — dark navy + cyan + orange (matches the mockup)
void applyOceanDarkTheme() {
    theme.bg     = hexToRGB565("#080C18");  // deep dark navy
    theme.card   = hexToRGB565("#0D1F3C");  // dark navy card (visible in 16-bit)
    theme.hdr    = hexToRGB565("#060E20");  // darkest header
    theme.cyan   = hexToRGB565("#00D4FF");  // bright cyan
    theme.orange = hexToRGB565("#FF6B35");  // vibrant orange
    theme.green  = hexToRGB565("#00E676");  // neon green
    theme.yellow = hexToRGB565("#FFD740");  // gold yellow
    theme.red    = hexToRGB565("#FF5252");  // bright red
    theme.purple = hexToRGB565("#BB86FC");  // soft purple
    theme.white  = hexToRGB565("#E8EAF6");  // warm white
    theme.dim    = hexToRGB565("#546E7A");  // blue-gray dim
    theme.vdim   = hexToRGB565("#2D3748");  // very dark gray
    theme.trace  = hexToRGB565("#111B2E");  // gauge track
}

// 🟣 Cyberpunk — pure black + magenta + electric blue
void applyCyberpunkTheme() {
    theme.bg     = hexToRGB565("#0A0012");
    theme.card   = hexToRGB565("#12002A");
    theme.hdr    = hexToRGB565("#08000F");
    theme.cyan   = hexToRGB565("#00F5FF");
    theme.orange = hexToRGB565("#FF00CC");  // hot pink/magenta
    theme.green  = hexToRGB565("#39FF14");  // neon green
    theme.yellow = hexToRGB565("#FFE000");
    theme.red    = hexToRGB565("#FF003C");
    theme.purple = hexToRGB565("#CC00FF");  // electric purple
    theme.white  = hexToRGB565("#F0F0FF");
    theme.dim    = hexToRGB565("#6633AA");
    theme.vdim   = hexToRGB565("#220044");
    theme.trace  = hexToRGB565("#150025");
}

// 🌲 Forest — dark green + lime + amber
void applyForestTheme() {
    theme.bg     = hexToRGB565("#051008");
    theme.card   = hexToRGB565("#0A2010");
    theme.hdr    = hexToRGB565("#030C05");
    theme.cyan   = hexToRGB565("#39FF14");  // lime green
    theme.orange = hexToRGB565("#FFB300");  // amber
    theme.green  = hexToRGB565("#00E676");
    theme.yellow = hexToRGB565("#F9A825");
    theme.red    = hexToRGB565("#FF5252");
    theme.purple = hexToRGB565("#69F0AE");  // teal
    theme.white  = hexToRGB565("#E8F5E9");
    theme.dim    = hexToRGB565("#4CAF50");
    theme.vdim   = hexToRGB565("#1B5E20");
    theme.trace  = hexToRGB565("#071A09");
}

// 🔴 Cherry — dark charcoal + crimson + rose
void applyCherryTheme() {
    theme.bg     = hexToRGB565("#120008");
    theme.card   = hexToRGB565("#200010");
    theme.hdr    = hexToRGB565("#0A0005");
    theme.cyan   = hexToRGB565("#FF3D6B");  // rose red as primary
    theme.orange = hexToRGB565("#FF8A00");
    theme.green  = hexToRGB565("#69F0AE");
    theme.yellow = hexToRGB565("#FFD600");
    theme.red    = hexToRGB565("#D50000");
    theme.purple = hexToRGB565("#FF80AB");  // pink
    theme.white  = hexToRGB565("#FFF0F3");
    theme.dim    = hexToRGB565("#AD1457");
    theme.vdim   = hexToRGB565("#3E0020");
    theme.trace  = hexToRGB565("#180010");
}

// ☀️ Light Day — clean white + blue + orange
void applyLightDayTheme() {
    theme.bg     = hexToRGB565("#EEF2FF");
    theme.card   = hexToRGB565("#FFFFFF");
    theme.hdr    = hexToRGB565("#DCE4F8");  // Crisp light blue-grey header background
    theme.cyan   = hexToRGB565("#1D4ED8");  // Vivid blue
    theme.orange = hexToRGB565("#EA580C");
    theme.green  = hexToRGB565("#15803D");
    theme.yellow = hexToRGB565("#D97706");  // Warm amber yellow for high contrast
    theme.red    = hexToRGB565("#DC2626");
    theme.purple = hexToRGB565("#7E22CE");
    theme.white  = hexToRGB565("#0F172A");  // Dark slate navy text for maximum legibility
    theme.dim    = hexToRGB565("#475569");
    theme.vdim   = hexToRGB565("#94A3B8");
    theme.trace  = hexToRGB565("#CBD5E1");
}

// 🎮 Retro Green — black + phosphor green (CRT terminal)
void applyRetroGreenTheme() {
    theme.bg     = hexToRGB565("#001100");
    theme.card   = hexToRGB565("#002200");
    theme.hdr    = hexToRGB565("#000900");
    theme.cyan   = hexToRGB565("#00FF41");  // matrix green
    theme.orange = hexToRGB565("#00CC33");
    theme.green  = hexToRGB565("#33FF33");
    theme.yellow = hexToRGB565("#AAFF00");  // yellow-green
    theme.red    = hexToRGB565("#FF3300");
    theme.purple = hexToRGB565("#00FF99");  // teal green
    theme.white  = hexToRGB565("#AAFFAA");
    theme.dim    = hexToRGB565("#006600");
    theme.vdim   = hexToRGB565("#003300");
    theme.trace  = hexToRGB565("#001A00");
}

static uint8_t currentThemeIdx = 0;
static const char* themePresetNames[] = {
    "ocean_dark", "cyberpunk", "forest", "cherry", "light_day", "retro_green"
};

const char* getCurrentThemePresetName() {
    if (currentThemeIdx < 6) return themePresetNames[currentThemeIdx];
    return "ocean_dark";
}

void nextTheme() {
    currentThemeIdx = (currentThemeIdx + 1) % 6;
    switch (currentThemeIdx) {
        case 0: applyOceanDarkTheme(); break;
        case 1: applyCyberpunkTheme(); break;
        case 2: applyForestTheme(); break;
        case 3: applyCherryTheme(); break;
        case 4: applyLightDayTheme(); break;
        case 5: applyRetroGreenTheme(); break;
    }
    saveTheme();
}
