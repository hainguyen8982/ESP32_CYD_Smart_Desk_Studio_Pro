// ═══════════════════════════════════════════════════════════════════════
//  Theme.h — Runtime color theme system for ESP32 CYD Dashboard
//  Colors stored as RGB565 (uint16_t), updatable via /api/theme HTTP API
// ═══════════════════════════════════════════════════════════════════════
#ifndef THEME_H
#define THEME_H

#include <Arduino.h>
#include <Preferences.h>

// ─── ThemeColors struct ───────────────────────────────────────────────
struct ThemeColors {
    uint16_t bg;      // Main background
    uint16_t card;    // Card / panel fill
    uint16_t hdr;     // Header strip
    uint16_t cyan;    // Primary accent (cyan/teal)
    uint16_t orange;  // Secondary accent (orange/warm)
    uint16_t green;   // Success / network
    uint16_t yellow;  // Gold / calendar / finance
    uint16_t red;     // Alert / alarm / error
    uint16_t purple;  // Tertiary accent
    uint16_t white;   // Primary text
    uint16_t dim;     // Secondary text
    uint16_t vdim;    // Tertiary text / inactive
    uint16_t trace;   // Gauge track / very dark bg
};

// ─── Global theme instance (used by DisplayManager.cpp) ───────────────
extern ThemeColors theme;

// ─── Utility functions ────────────────────────────────────────────────

// Convert web hex string "#RRGGBB" → RGB565 uint16_t
uint16_t hexToRGB565(const char* hex);

// Convert RGB565 → hex string "#RRGGBB" (buf must be ≥8 bytes)
void rgb565ToHex(uint16_t color, char* buf);

// Load theme from NVS flash (falls back to default if not set)
void loadTheme();

// Save current theme to NVS flash
void saveTheme();

// Set built-in "Ocean Dark" theme (default, matches mockup)
void applyOceanDarkTheme();

// Set built-in "Cyberpunk" theme
void applyCyberpunkTheme();

// Set built-in "Forest" theme
void applyForestTheme();

// Set built-in "Cherry" theme
void applyCherryTheme();

// Set built-in "Light Day" theme
void applyLightDayTheme();

// Set built-in "Retro Green" theme
void applyRetroGreenTheme();

// Cycle to next built-in preset theme
void nextTheme();

// Get current theme preset name string
const char* getCurrentThemePresetName();

#endif // THEME_H
