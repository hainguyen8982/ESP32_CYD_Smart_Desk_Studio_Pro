#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
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

class NetworkManager {
public:
    NetworkManager();
    void begin();
    void update();

    bool isConnected() const { return WiFi.status() == WL_CONNECTED; }
    IPAddress getLocalIP() const { return WiFi.localIP(); }
    int8_t getRSSI() const { return WiFi.RSSI(); }

    void fetchWeather();
    void fetchGoldAndExchange();
    void setCity(const char* newCity);
    
    const WeatherData& getWeather() const { return weather; }
    const GoldData& getGold() const { return gold; }
    const ExchangeData& getExchange() const { return exchange; }
    ExchangeData& getExchangeMutable() { return exchange; }

    // Remote navigation request from Web Portal
    int getRemoteRequestedPage() const { return remotePage; }
    void clearRemoteRequestedPage() { remotePage = -1; }

private:
    void setupWebRoutes();
    
    WeatherData weather;
    GoldData gold;
    ExchangeData exchange;

    AsyncWebServer server;
    unsigned long lastWeatherFetch;
    unsigned long lastGoldFetch;
    int remotePage;
};

extern NetworkManager network;

#endif // NETWORK_MANAGER_H
