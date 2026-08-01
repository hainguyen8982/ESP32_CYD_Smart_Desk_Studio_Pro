#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Hardware Pinout Definitions for ESP32 CYD (ESP32-2432S028)
#define PIN_TFT_BL          21      // Backlight PWM Output
#define PIN_LDR             34      // Light Dependent Resistor (Analog In)
#define PIN_SPEAKER         26      // Onboard Speaker / Buzzer
#define PIN_RGB_RED         4       // RGB LED Red Channel
#define PIN_RGB_GREEN       16      // RGB LED Green Channel
#define PIN_RGB_BLUE        17      // RGB LED Blue Channel

// Touchscreen Pinout (Resistive SPI XPT2046 fallback)
#define PIN_TOUCH_CS        33      // Touch Chip Select SPI
#define PIN_TOUCH_IRQ       36      // Touch Interrupt Input (Low on press)

// Physical Buttons
#define PIN_BOOT_BTN        0       // BOOT button (GPIO 0, active LOW)

// Screen Dimensions
#define SCREEN_WIDTH        320
#define SCREEN_HEIGHT       240

// Number of Dashboard Pages
#define TOTAL_PAGES         8       // Pages 0-6 = Dashboard, Page 7 = Settings

// System Constants
#define PC_MONITOR_TIMEOUT_MS 6000   // Switch from PC Monitor mode if no data for 6s
#define LDR_CHECK_INTERVAL_MS 500    // LDR Auto-brightness interval

// Default Settings
#define DEFAULT_CITY        "Hanoi"
#define DEFAULT_OPENWEATHER_KEY "bd5e378503939ddaee5f12d250261283" // Public OWM key or customizable

#endif // CONFIG_H
