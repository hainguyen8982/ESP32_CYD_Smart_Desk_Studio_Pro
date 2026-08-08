#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <WiFiManager.h>
#include <ESPAsyncWebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "Config.h"

struct WeatherData {
    float temp;
    uint8_t humidity;
    float windSpeed;
    char icon[8];
    char main[32];
    char city[32];
    float forecastTempMin[3];
    float forecastTempMax[3];
    char forecastIcons[3][8];
    uint8_t forecastCode[3];
    bool valid;
};

struct GoldData {
    float sjcBuy;
    float sjcSell;
    float sjcDelta;
    float xauUsd;
    float history7Days[7];
    bool valid;
};

struct ExchangeData {
    char cur1Code[8];
    float cur1Rate;
    float cur1History7[7];
    char cur2Code[8];
    float cur2Rate;
    float cur2History7[7];
    bool valid;
};

enum BootState {
    BOOT_CONNECTING_WIFI = 0,
    BOOT_AP_MODE,
    BOOT_SYNCING_TIME,
    BOOT_FETCHING_DATA,
    BOOT_READY,
    BOOT_OFFLINE
};

class NetworkManager {
public:
    NetworkManager();
    void begin();
    void update();

    bool isConnected() const { return WiFi.status() == WL_CONNECTED; }
    IPAddress getLocalIP() const { return WiFi.localIP(); }
    int8_t getRSSI() const { return WiFi.RSSI(); }

    // Boot progress status for Splash Screen
    BootState getBootState() const { return bootState; }
    const char* getBootStatusMsg() const { return bootStatusMsg; }
    uint8_t getBootProgressPct() const { return bootProgress; }
    bool isBootComplete() const { return bootState == BOOT_READY || bootState == BOOT_OFFLINE; }

    void fetchWeather();
    void fetchGoldAndExchange();
    void triggerAsyncExchangeRefresh() { lastGoldFetch = 0; }
    void setCity(const char* newCity);
    
    const WeatherData& getWeather() const { return weather; }
    const GoldData& getGold() const { return gold; }
    const ExchangeData& getExchange() const { return exchange; }
    ExchangeData& getExchangeMutable() { return exchange; }

    // Remote navigation request from Web Portal
    int getRemoteRequestedPage() const { return remotePage; }
    void clearRemoteRequestedPage() { remotePage = -1; }

    // Media Control Action Dispatcher
    void triggerMediaAction(const char* action);
    const char* getLastMediaAction() const { return lastMediaAction; }
    void clearLastMediaAction() { lastMediaAction[0] = '\0'; }

private:
    void setupWebRoutes();
    
    WeatherData weather;
    GoldData gold;
    ExchangeData exchange;

    AsyncWebServer server;
    WiFiUDP udp;
    unsigned long lastWeatherFetch;
    unsigned long lastGoldFetch;
    int remotePage;
    char lastMediaAction[32];

    BootState bootState;
    char bootStatusMsg[64];
    uint8_t bootProgress;
    unsigned long bootStartTime;
    unsigned long wifiConnectedTime;
};

extern NetworkManager network;

#endif // NETWORK_MANAGER_H
