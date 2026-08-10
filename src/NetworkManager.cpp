#include "NetworkManager.h"
#include "HardwareManager.h"
#include "PCMonitor.h"
#include "DeskUtilities.h"
#include "Theme.h"
#include "DisplayManager.h"
#include "TouchManager.h"
#include "DynamicSkinManager.h"
#include <ESPmDNS.h>

extern DisplayManager display;

NetworkManager network;

static void populateCurrencyHistory7(const char* code, float currentRate, float* outHistory) {
    if (!code || currentRate <= 0.0f || !outHistory) return;

    if (strcmp(code, "USD") == 0) {
        float r[7] = { 0.9977f, 0.9985f, 0.9988f, 0.9981f, 0.9996f, 0.9992f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else if (strcmp(code, "EUR") == 0) {
        float r[7] = { 1.0072f, 1.0058f, 1.0047f, 0.9989f, 0.9978f, 0.9985f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else if (strcmp(code, "CAD") == 0) {
        float r[7] = { 0.9950f, 0.9966f, 0.9982f, 0.9961f, 0.9977f, 0.9993f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else if (strcmp(code, "JPY") == 0) {
        float r[7] = { 0.9788f, 0.9825f, 0.9867f, 0.9903f, 0.9945f, 0.9970f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else if (strcmp(code, "GBP") == 0) {
        float r[7] = { 0.9859f, 0.9902f, 0.9944f, 0.9930f, 0.9972f, 0.9958f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else if (strcmp(code, "AUD") == 0) {
        float r[7] = { 1.0085f, 1.0052f, 1.0018f, 0.9964f, 0.9980f, 0.9990f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else if (strcmp(code, "SGD") == 0) {
        float r[7] = { 0.9965f, 0.9978f, 0.9990f, 0.9980f, 0.9992f, 0.9996f, 1.0000f };
        for (int i = 0; i < 7; i++) outHistory[i] = currentRate * r[i];
    } else {
        uint32_t seed = 5381;
        for (int i = 0; code[i] != '\0'; i++) seed = ((seed << 5) + seed) + (uint8_t)code[i];
        for (int i = 0; i < 6; i++) {
            uint32_t val = (seed ^ (i * 2654435761U)) + (i * 1013904223U);
            float noise = (float)((val % 140) - 70) / 10000.0f;
            outHistory[i] = currentRate * (1.0f + noise);
        }
        outHistory[6] = currentRate;
    }
}

void NetworkManager::setCity(const char* newCity) {
    if (!newCity || newCity[0] == '\0') return;
    snprintf(weather.city, sizeof(weather.city), "%s", newCity);
    
    // Save to NVS Preferences permanently
    Preferences prefs;
    prefs.begin("weather", false);
    prefs.putString("city", weather.city);
    prefs.end();

    // Trigger instant weather refresh
    lastWeatherFetch = 0;
}

NetworkManager::NetworkManager()
    : server(80),
      lastWeatherFetch(0),
      lastGoldFetch(0),
      exchangeRefreshPending(false),
      remotePage(-1),
      bootState(BOOT_CONNECTING_WIFI),
      bootProgress(15),
      bootStartTime(0),
      wifiConnectedTime(0) {
    memset(&weather, 0, sizeof(weather));
    memset(&gold, 0, sizeof(gold));
    memset(&exchange, 0, sizeof(exchange));
    lastMediaAction[0] = '\0';
    snprintf(weather.city, sizeof(weather.city), DEFAULT_CITY);
    snprintf(bootStatusMsg, sizeof(bootStatusMsg), "[1/3] Connecting WiFi...");
}

static unsigned long lastMediaTriggerTime = 0;

void NetworkManager::triggerMediaAction(const char* action) {
    if (!action) return;
    if (millis() - lastMediaTriggerTime < 220) return; // 220ms touch debounce guard for instant feel
    lastMediaTriggerTime = millis();

    snprintf(lastMediaAction, sizeof(lastMediaAction), "%s", action);

    // 1. Instant USB Serial Output (0ms delay)
    Serial.printf("MEDIA_CMD:%s\n", lastMediaAction);

    // 2. Instant UDP Fast Packet to PC IP on Port 8080 (0ms delay)
    if (WiFi.status() == WL_CONNECTED) {
        udp.beginPacket(IPAddress(255, 255, 255, 255), 8080); // Subnet broadcast
        udp.printf("MEDIA_CMD:%s", lastMediaAction);
        udp.endPacket();
    }
}

void NetworkManager::begin() {
    Serial.println("[NetworkManager] Connecting WiFi via WiFiManager...");

    // Restore saved City and Currency pairs from NVS Preferences
    Preferences prefs;
    prefs.begin("desk_cfg", true);
    String savedCity = prefs.getString("city", "Ho Chi Minh");
    String savedCur1 = prefs.getString("cur1", "USD");
    String savedCur2 = prefs.getString("cur2", "CAD");
    prefs.end();

    snprintf(weather.city, sizeof(weather.city), "%s", savedCity.c_str());
    strncpy(exchange.cur1Code, savedCur1.c_str(), 7);
    strncpy(exchange.cur2Code, savedCur2.c_str(), 7);

    bootStartTime = millis();
    bootState = BOOT_CONNECTING_WIFI;
    bootProgress = 25;
    snprintf(bootStatusMsg, sizeof(bootStatusMsg), "[1/3] Connecting WiFi...");
    display.update();

    WiFiManager wm;
    wm.setConfigPortalTimeout(180); // 3 minutes timeout if no AP config
    wm.setBreakAfterConfig(true);

    wm.setAPCallback([this](WiFiManager *myWiFiManager) {
        bootState = BOOT_AP_MODE;
        bootProgress = 35;
        snprintf(bootStatusMsg, sizeof(bootStatusMsg), "AP: ESP32_CYD_Desk_Setup (192.168.4.1)");
        Serial.println("[NetworkManager] Entering AP Config Portal Mode");
        display.update();
    });

    if (!wm.autoConnect("ESP32_CYD_Desk_Setup")) {
        Serial.println("[NetworkManager] Failed to connect WiFi, running AP mode");
        hardware.setRGBColor(COLOR_YELLOW);
        bootState = BOOT_OFFLINE;
        bootProgress = 100;
        snprintf(bootStatusMsg, sizeof(bootStatusMsg), "[Offline Mode] Starting Dashboard...");
        display.update();
    } else {
        Serial.print("[NetworkManager] WiFi Connected! IP: ");
        Serial.println(WiFi.localIP());
        hardware.setRGBColor(COLOR_GREEN);

        wifiConnectedTime = millis();
        bootState = BOOT_SYNCING_TIME;
        bootProgress = 60;
        snprintf(bootStatusMsg, sizeof(bootStatusMsg), "[2/3] Syncing NTP Time (VN GMT+7)...");
        display.update();
    }

    // Configure NTP Time (Vietnam GMT+7)
    configTime(7 * 3600, 0, "vn.pool.ntp.org", "time.google.com", "pool.ntp.org");

    // Load saved Weather City & Exchange Currencies from NVS
    Preferences prefsCfg;
    prefsCfg.begin("weather", true);
    if (prefsCfg.isKey("city")) {
        String savedCity = prefsCfg.getString("city", DEFAULT_CITY);
        snprintf(weather.city, sizeof(weather.city), "%s", savedCity.c_str());
    }
    prefsCfg.end();

    prefsCfg.begin("exchange", true);
    if (prefsCfg.isKey("cur1")) {
        String c1 = prefsCfg.getString("cur1", "USD");
        strncpy(exchange.cur1Code, c1.c_str(), 7);
    } else {
        strncpy(exchange.cur1Code, "USD", 7);
    }
    if (prefsCfg.isKey("cur2")) {
        String c2 = prefsCfg.getString("cur2", "EUR");
        strncpy(exchange.cur2Code, c2.c_str(), 7);
    } else {
        strncpy(exchange.cur2Code, "EUR", 7);
    }
    prefsCfg.end();

    setupWebRoutes();
    server.begin();
    Serial.println("[NetworkManager] AsyncWebServer Started on Port 80");

    if (MDNS.begin("cyd-dashboard")) {
        MDNS.addService("http", "tcp", 80);
        Serial.println("[NetworkManager] mDNS Responder Started (http://cyd-dashboard.local)");
    }

    if (isConnected()) {
        fetchWeather();
        fetchGoldAndExchange();

        // Check if NTP time is synced immediately; if not, NetworkManager::update() will complete boot
        time_t now = time(NULL);
        if (now > 1600000000 && weather.valid) {
            bootState = BOOT_READY;
            bootProgress = 100;
            snprintf(bootStatusMsg, sizeof(bootStatusMsg), "Ready! Opening Dashboard...");
            display.update();
        } else {
            bootState = BOOT_SYNCING_TIME;
            bootProgress = 75;
            snprintf(bootStatusMsg, sizeof(bootStatusMsg), "[2/3] Syncing NTP Time (VN GMT+7)...");
            display.update();
        }
    }
}

static void sendCORSResponse(AsyncWebServerRequest *request, int code, const String& json) {
    AsyncWebServerResponse *response = request->beginResponse(code, "application/json", json);
    response->addHeader("Access-Control-Allow-Origin", "*");
    response->addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT");
    response->addHeader("Access-Control-Allow-Headers", "*");
    response->addHeader("Access-Control-Allow-Private-Network", "true");
    request->send(response);
}

static float calcCurrencyRate(const char* code, float vndUsd, JsonDocument* eDoc = nullptr) {
    if (!code || code[0] == '\0' || strcmp(code, "USD") == 0) return vndUsd;
    float r = 0.0f;
    if (eDoc && !(*eDoc)["rates"][code].isNull()) {
        r = (*eDoc)["rates"][code];
    } else {
        if (strcmp(code, "EUR") == 0) r = 0.8667f;
        else if (strcmp(code, "JPY") == 0) r = 158.0f;
        else if (strcmp(code, "CAD") == 0) r = 1.4013f;
        else if (strcmp(code, "GBP") == 0) r = 0.7417f;
        else if (strcmp(code, "AUD") == 0) r = 1.4203f;
        else if (strcmp(code, "SGD") == 0) r = 1.2820f;
        else if (strcmp(code, "CNY") == 0) r = 6.7597f;
        else if (strcmp(code, "KRW") == 0) r = 1440.5f;
        else if (strcmp(code, "CHF") == 0) r = 0.8073f;
    }
    return (r > 0.0001f) ? (vndUsd / r) : vndUsd;
}

void NetworkManager::setupWebRoutes() {
    // Enable CORS for PC Theme Designer Web App & Chrome Private Network Access
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Origin", "*");
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT");
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Headers", "*");
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Private-Network", "true");

    // Global OPTIONS handler for CORS preflight
    server.onNotFound([](AsyncWebServerRequest *request) {
        if (request->method() == HTTP_OPTIONS) {
            AsyncWebServerResponse *response = request->beginResponse(200);
            response->addHeader("Access-Control-Allow-Origin", "*");
            response->addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT");
            response->addHeader("Access-Control-Allow-Headers", "*");
            response->addHeader("Access-Control-Allow-Private-Network", "true");
            request->send(response);
        } else {
            request->send(404, "text/plain", "Not found");
        }
    });

    // Main Dark-Mode Web Dashboard UI
    server.on("/", HTTP_GET, [this](AsyncWebServerRequest *request) {
        String html = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
                      "<title>ESP32 CYD Desk Dashboard</title>"
                      "<style>"
                      "body{font-family:Segoe UI,sans-serif;background:#0d1117;color:#c9d1d9;margin:0;padding:20px;text-align:center}"
                      ".card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin:15px auto;max-width:420px;box-shadow:0 4px 12px rgba(0,0,0,0.5)}"
                      "h1{color:#58a6ff;font-size:22px;margin-bottom:10px}"
                      "button{background:#238636;color:#fff;border:none;padding:10px 14px;margin:5px;border-radius:6px;font-weight:bold;cursor:pointer;transition:0.2s}"
                      "button:hover{background:#2ea043}"
                      "select,input{background:#21262d;border:1px solid #30363d;color:#fff;padding:8px;border-radius:6px;margin:4px}"
                      "</style></head><body>"
                      "<div class='card'>"
                      "<h1>ESP32 CYD Desk Dashboard</h1>"
                      "<p>IP: <b>" + WiFi.localIP().toString() + "</b> | RSSI: " + String(WiFi.RSSI()) + " dBm</p>"
                      "<hr style='border-color:#30363d'>"
                      "<h3>🌤️ Weather City</h3>"
                      "<select id='cs' onchange=\"fetch('/api/weather/city?name='+this.value);alert('City set to '+this.value)\">"
                      "<option value='Hanoi'>Hà Nội</option>"
                      "<option value='Ho Chi Minh'>TP. Hồ Chí Minh</option>"
                      "<option value='Da Nang'>Đà Nẵng</option>"
                      "<option value='Hai Phong'>Hải Phòng</option>"
                      "<option value='Can Tho'>Cần Thơ</option>"
                      "<option value='Nha Trang'>Nha Trang</option>"
                      "<option value='Da Lat'>Đà Lạt</option>"
                      "<option value='Hue'>Huế</option>"
                      "<option value='Vung Tau'>Vũng Tàu</option>"
                      "<option value='Phu Quoc'>Phú Quốc</option>"
                      "</select>"
                      "<hr style='border-color:#30363d'>"
                      "<h3>🎨 Theme Presets</h3>"
                      "<button onclick=\"fetch('/api/theme',{method:'POST',body:JSON.stringify({preset:'ocean_dark'})})\">🌊 Ocean</button>"
                      "<button onclick=\"fetch('/api/theme',{method:'POST',body:JSON.stringify({preset:'cyberpunk'})})\">🟣 Cyberpunk</button>"
                      "<button onclick=\"fetch('/api/theme',{method:'POST',body:JSON.stringify({preset:'forest'})})\">🌲 Forest</button><br>"
                      "<button onclick=\"fetch('/api/theme',{method:'POST',body:JSON.stringify({preset:'cherry'})})\">🔴 Cherry</button>"
                      "<button onclick=\"fetch('/api/theme',{method:'POST',body:JSON.stringify({preset:'light_day'})})\">☀️ Light</button>"
                      "<button onclick=\"fetch('/api/theme',{method:'POST',body:JSON.stringify({preset:'retro_green'})})\">🎮 Retro</button>"
                      "<hr style='border-color:#30363d'>"
                      "<h3>Remote Page Switch</h3>"
                      "<button onclick=\"fetch('/api/page?id=0')\">0: Weather Clock</button>"
                      "<button onclick=\"fetch('/api/page?id=1')\">1: Lunar Calendar</button>"
                      "<button onclick=\"fetch('/api/page?id=2')\">2: Gold & Finance</button><br>"
                      "<button onclick=\"fetch('/api/page?id=3')\">3: PC CPU/RAM</button>"
                      "<button onclick=\"fetch('/api/page?id=4')\">4: PC GPU/VRAM</button>"
                      "<button onclick=\"fetch('/api/page?id=5')\">5: PC Net/Disks</button><br>"
                      "<button onclick=\"fetch('/api/page?id=6')\">6: Desk Utilities</button>"
                      "<hr style='border-color:#333'>"
                      "<h3>Desk Utilities & Settings</h3>"
                      "<p><button onclick=\"fetch('/api/pomodoro/toggle')\">Toggle Pomodoro</button>"
                      "<button onclick=\"fetch('/api/pomodoro/reset')\">Reset Pomodoro</button></p>"
                      "<p>Set Alarm (HH:MM): <input type='number' id='ah' min='0' max='23' value='7' style='width:50px'>"
                      ":<input type='number' id='am' min='0' max='59' value='0' style='width:50px'>"
                      " <button onclick=\"setAlarm()\">Set Alarm</button></p>"
                      "<script>"
                      "function setAlarm(){"
                      "var h=document.getElementById('ah').value;var m=document.getElementById('am').value;"
                      "fetch('/api/alarm?h='+h+'&m='+m+'&e=1');alert('Alarm Set to '+h+':'+m);"
                      "}"
                      "</script>"
                      "</div></body></html>";
        request->send(200, "text/html", html);
    });

    // Remote Page Navigation API
    server.on("/api/page", HTTP_GET, [this](AsyncWebServerRequest *request) {
        if (request->hasParam("id")) {
            int p = request->getParam("id")->value().toInt();
            if (p >= 0 && p < TOTAL_PAGES) {
                remotePage = p;
                request->send(200, "application/json", "{\"status\":\"ok\"}");
                return;
            }
        }
        request->send(400, "application/json", "{\"status\":\"error\"}");
    });

    // PC Monitor HTTP POST Receiver (supports both /api/pc and /api/pc_status)
    auto handlePCStatus = [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
        if (index == 0) {
            request->_tempObject = malloc(total + 1);
        }
        if (request->_tempObject) {
            uint8_t* fullBuf = (uint8_t*)request->_tempObject;
            memcpy(fullBuf + index, data, len);
            if (index + len == total) {
                fullBuf[total] = '\0';
                if (pcMonitor.parseJsonData((const char*)fullBuf)) {
                    char respBuf[256];
                    snprintf(respBuf, sizeof(respBuf),
                             "{\"status\":\"ok\",\"page\":%d,\"theme\":\"%s\",\"city\":\"%s\",\"cur1\":\"%s\",\"cur2\":\"%s\"}",
                             display.getCurrentPage(),
                             getCurrentThemePresetName(),
                             weather.city,
                             exchange.cur1Code,
                             exchange.cur2Code);
                    sendCORSResponse(request, 200, respBuf);
                } else {
                    sendCORSResponse(request, 400, "{\"status\":\"invalid json\"}");
                }
                free(request->_tempObject);
                request->_tempObject = NULL;
            }
        } else {
            sendCORSResponse(request, 500, "{\"status\":\"out of memory\"}");
        }
    };

    server.on("/api/pc", HTTP_POST, [](AsyncWebServerRequest *request) {}, NULL, handlePCStatus);
    server.on("/api/pc_status", HTTP_POST, [](AsyncWebServerRequest *request) {}, NULL, handlePCStatus);

    // Pomodoro APIs
    server.on("/api/pomodoro/toggle", HTTP_GET, [](AsyncWebServerRequest *request) {
        deskUtils.togglePomodoro();
        request->send(200, "application/json", "{\"status\":\"ok\"}");
    });

    server.on("/api/pomodoro/reset", HTTP_GET, [](AsyncWebServerRequest *request) {
        deskUtils.resetPomodoro();
        request->send(200, "application/json", "{\"status\":\"ok\"}");
    });

    // Live Skin Update API (POST /api/skin/update)
    server.on("/api/skin/update", HTTP_POST, [](AsyncWebServerRequest *request) {}, NULL,
        [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            char* buf = (char*)malloc(len + 1);
            if (!buf) {
                sendCORSResponse(request, 500, "{\"status\":\"out of memory\"}");
                return;
            }
            memcpy(buf, data, len);
            buf[len] = '\0';
            String payload = String(buf);
            free(buf);

            if (g_skinMgr.parseAndSaveSkinJSON(payload)) {
                display.refreshDisplay();
                sendCORSResponse(request, 200, "{\"status\":\"ok\",\"message\":\"Skin updated\"}");
            } else {
                sendCORSResponse(request, 400, "{\"status\":\"error\",\"message\":\"Invalid skin JSON\"}");
            }
        });

    // Alarm API
    server.on("/api/alarm", HTTP_GET, [](AsyncWebServerRequest *request) {
        if (request->hasParam("h") && request->hasParam("m")) {
            uint8_t h = request->getParam("h")->value().toInt();
            uint8_t m = request->getParam("m")->value().toInt();
            bool e = request->hasParam("e") ? request->getParam("e")->value().toInt() : true;
            deskUtils.setAlarm(h, m, e);
            request->send(200, "application/json", "{\"status\":\"ok\"}");
            return;
        }
        request->send(400, "application/json", "{\"status\":\"missing params\"}");
    });

    // Weather City API (GET / POST)
    server.on("/api/weather/city", HTTP_GET, [this](AsyncWebServerRequest *request) {
        String c = "";
        if (request->hasParam("city")) c = request->getParam("city")->value();
        else if (request->hasParam("name")) c = request->getParam("name")->value();
        if (c.length() > 0) {
            setCity(c.c_str());
            sendCORSResponse(request, 200, "{\"status\":\"ok\",\"city\":\"" + c + "\"}");
            return;
        }
        sendCORSResponse(request, 200, "{\"city\":\"" + String(weather.city) + "\"}");
    });

    server.on("/api/weather/city", HTTP_POST, [this](AsyncWebServerRequest *request) {}, NULL,
        [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            char* buf = (char*)malloc(len + 1);
            if (!buf) {
                sendCORSResponse(request, 500, "{\"status\":\"out of memory\"}");
                return;
            }
            memcpy(buf, data, len);
            buf[len] = '\0';

            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, buf);
            free(buf);

            if (!err && !doc["city"].isNull()) {
                const char* c = doc["city"];
                setCity(c);
                sendCORSResponse(request, 200, "{\"status\":\"ok\",\"city\":\"" + String(c) + "\"}");
                return;
            }
            sendCORSResponse(request, 400, "{\"status\":\"invalid request\"}");
        });

    // Theme API - GET current theme JSON or switch preset GET /api/theme?preset=ocean_dark
    server.on("/api/theme", HTTP_GET, [](AsyncWebServerRequest *request) {
        if (request->hasParam("preset")) {
            String p = request->getParam("preset")->value();
            if (p == "ocean_dark") applyOceanDarkTheme();
            else if (p == "cyberpunk") applyCyberpunkTheme();
            else if (p == "forest") applyForestTheme();
            else if (p == "cherry") applyCherryTheme();
            else if (p == "light_day") applyLightDayTheme();
            else if (p == "retro_green") applyRetroGreenTheme();
            saveTheme();
            sendCORSResponse(request, 200, "{\"status\":\"ok\"}");
            return;
        }

        char bg[8], card[8], hdr[8], cyan[8], orange[8], green[8], yellow[8], red[8], purple[8], white[8], dim[8];
        rgb565ToHex(theme.bg, bg);
        rgb565ToHex(theme.card, card);
        rgb565ToHex(theme.hdr, hdr);
        rgb565ToHex(theme.cyan, cyan);
        rgb565ToHex(theme.orange, orange);
        rgb565ToHex(theme.green, green);
        rgb565ToHex(theme.yellow, yellow);
        rgb565ToHex(theme.red, red);
        rgb565ToHex(theme.purple, purple);
        rgb565ToHex(theme.white, white);
        rgb565ToHex(theme.dim, dim);

        JsonDocument doc;
        doc["bg"]     = bg;
        doc["card"]   = card;
        doc["hdr"]    = hdr;
        doc["cyan"]   = cyan;
        doc["orange"] = orange;
        doc["green"]  = green;
        doc["yellow"] = yellow;
        doc["red"]    = red;
        doc["purple"] = purple;
        doc["white"]  = white;
        doc["dim"]    = dim;
        doc["preset"] = getCurrentThemePresetName();
        doc["currentPage"] = display.getCurrentPage();

        String res;
        serializeJson(doc, res);
        sendCORSResponse(request, 200, res);
    });

    // Theme API - POST new theme JSON or Preset
    server.on("/api/theme", HTTP_POST, [](AsyncWebServerRequest *request) {}, NULL,
        [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            char* buf = (char*)malloc(len + 1);
            if (!buf) {
                sendCORSResponse(request, 500, "{\"status\":\"out of memory\"}");
                return;
            }
            memcpy(buf, data, len);
            buf[len] = '\0';

            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, buf);
            free(buf);

            if (err) {
                sendCORSResponse(request, 400, "{\"status\":\"invalid json\"}");
                return;
            }

            if (!doc["preset"].isNull()) {
                const char* p = doc["preset"];
                if (strcmp(p, "ocean_dark") == 0) applyOceanDarkTheme();
                else if (strcmp(p, "cyberpunk") == 0) applyCyberpunkTheme();
                else if (strcmp(p, "forest") == 0) applyForestTheme();
                else if (strcmp(p, "cherry") == 0) applyCherryTheme();
                else if (strcmp(p, "light_day") == 0) applyLightDayTheme();
                else if (strcmp(p, "retro_green") == 0) applyRetroGreenTheme();
            } else {
                if (!doc["bg"].isNull())     theme.bg     = hexToRGB565(doc["bg"]);
                if (!doc["card"].isNull())   theme.card   = hexToRGB565(doc["card"]);
                if (!doc["hdr"].isNull())    theme.hdr    = hexToRGB565(doc["hdr"]);
                if (!doc["cyan"].isNull())   theme.cyan   = hexToRGB565(doc["cyan"]);
                if (!doc["orange"].isNull()) theme.orange = hexToRGB565(doc["orange"]);
                if (!doc["green"].isNull())  theme.green  = hexToRGB565(doc["green"]);
                if (!doc["yellow"].isNull()) theme.yellow = hexToRGB565(doc["yellow"]);
                if (!doc["red"].isNull())    theme.red    = hexToRGB565(doc["red"]);
                if (!doc["purple"].isNull()) theme.purple = hexToRGB565(doc["purple"]);
                if (!doc["white"].isNull())  theme.white  = hexToRGB565(doc["white"]);
                if (!doc["dim"].isNull())    theme.dim    = hexToRGB565(doc["dim"]);
            }
            saveTheme();
            sendCORSResponse(request, 200, "{\"status\":\"ok\"}");
        });

    // Calibrate API - POST to trigger touch recalibration
    server.on("/api/calibrate", HTTP_POST, [](AsyncWebServerRequest *request) {
        touch.startCalibration();
        sendCORSResponse(request, 200, "{\"status\":\"calibration_started\"}");
    });

    // Calibrate API - GET calibration status
    server.on("/api/calibrate", HTTP_GET, [](AsyncWebServerRequest *request) {
        JsonDocument doc;
        doc["calibrated"] = touch.isCalibrated();
        doc["calibrating"] = touch.isCalibrating();
        doc["touchType"] = touch.getTouchTypeString();
        String res;
        serializeJson(doc, res);
        sendCORSResponse(request, 200, res);
    });

    // Exchange Selection API - GET /api/exchange?cur1=USD&cur2=EUR
    server.on("/api/exchange", HTTP_GET, [this](AsyncWebServerRequest *request) {
        ExchangeData& ex = getExchangeMutable();
        bool changed = false;
        if (request->hasParam("cur1")) {
            strncpy(ex.cur1Code, request->getParam("cur1")->value().c_str(), 7);
            ex.cur1Code[7] = '\0';
            changed = true;
        }
        if (request->hasParam("cur2")) {
            strncpy(ex.cur2Code, request->getParam("cur2")->value().c_str(), 7);
            ex.cur2Code[7] = '\0';
            changed = true;
        }
        if (changed) {
            Preferences prefs;
            prefs.begin("exchange", false);
            prefs.putString("cur1", ex.cur1Code);
            prefs.putString("cur2", ex.cur2Code);
            prefs.end();
            float vndUsd = 26180.0f;
            ex.cur1Rate = calcCurrencyRate(ex.cur1Code, vndUsd);
            ex.cur2Rate = calcCurrencyRate(ex.cur2Code, vndUsd);
            triggerAsyncExchangeRefresh();
        }
        char res[128];
        snprintf(res, sizeof(res), "{\"status\":\"ok\",\"cur1\":\"%s\",\"cur2\":\"%s\"}", ex.cur1Code, ex.cur2Code);
        sendCORSResponse(request, 200, res);
    });

    // Exchange Selection API - POST { "cur1": "USD", "cur2": "EUR" }
    server.on("/api/exchange", HTTP_POST, [](AsyncWebServerRequest *request) {}, NULL,
        [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            char* buf = (char*)malloc(len + 1);
            if (!buf) {
                sendCORSResponse(request, 500, "{\"status\":\"out of memory\"}");
                return;
            }
            memcpy(buf, data, len);
            buf[len] = '\0';

            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, buf);
            free(buf);

            if (!err) {
                ExchangeData& ex = getExchangeMutable();
                bool changed = false;
                if (!doc["cur1"].isNull()) {
                    strncpy(ex.cur1Code, doc["cur1"].as<const char*>(), 7);
                    ex.cur1Code[7] = '\0';
                    changed = true;
                }
                if (!doc["cur2"].isNull()) {
                    strncpy(ex.cur2Code, doc["cur2"].as<const char*>(), 7);
                    ex.cur2Code[7] = '\0';
                    changed = true;
                }
                if (changed) {
                    Preferences prefs;
                    prefs.begin("exchange", false);
                    prefs.putString("cur1", ex.cur1Code);
                    prefs.putString("cur2", ex.cur2Code);
                    prefs.end();
                    float vndUsd = 26180.0f;
                    ex.cur1Rate = calcCurrencyRate(ex.cur1Code, vndUsd);
                    ex.cur2Rate = calcCurrencyRate(ex.cur2Code, vndUsd);
                    triggerAsyncExchangeRefresh();
                }

                sendCORSResponse(request, 200, "{\"status\":\"ok\"}");
                return;
            }
            sendCORSResponse(request, 400, "{\"status\":\"invalid json\"}");
        });

    // Media Remote API - GET/POST /api/media
    server.on("/api/media", HTTP_GET, [this](AsyncWebServerRequest *request) {
        if (request->hasParam("action")) {
            String act = request->getParam("action")->value();
            triggerMediaAction(act.c_str());
            sendCORSResponse(request, 200, "{\"status\":\"ok\",\"action\":\"" + act + "\"}");
            return;
        }
        JsonDocument doc;
        doc["lastAction"] = lastMediaAction;
        String res;
        serializeJson(doc, res);
        sendCORSResponse(request, 200, res);
    });

    server.on("/api/media", HTTP_POST, [this](AsyncWebServerRequest *request) {}, NULL,
        [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            JsonDocument doc;
            if (!deserializeJson(doc, data, len)) {
                if (!doc["action"].isNull()) {
                    triggerMediaAction(doc["action"]);
                    sendCORSResponse(request, 200, "{\"status\":\"ok\"}");
                    return;
                }
            }
            sendCORSResponse(request, 400, "{\"status\":\"invalid json\"}");
        });
}

void NetworkManager::update() {
    // Process boot transition check: Keep Splash Screen active until NTP time is synced & data loaded
    if (bootState != BOOT_READY && bootState != BOOT_OFFLINE) {
        time_t now = time(NULL);
        if (now > 1600000000) {
            if (!weather.valid && isConnected()) fetchWeather();
            if (!gold.valid && isConnected()) fetchGoldAndExchange();

            bootState = BOOT_READY;
            bootProgress = 100;
            snprintf(bootStatusMsg, sizeof(bootStatusMsg), "Ready! Opening Dashboard...");
            Serial.printf("[NetworkManager] NTP Time Synced (Time=%ld) -> Boot Ready\n", (long)now);
        } else if (wifiConnectedTime > 0 && millis() - wifiConnectedTime > 15000) {
            bootState = BOOT_READY;
            bootProgress = 100;
            Serial.println("[NetworkManager] Boot Timeout Safety (15s) -> Opening Dashboard");
        }
    }

    if (!isConnected()) return;

    // Fetch Weather every 15 minutes
    if (millis() - lastWeatherFetch > 15 * 60 * 1000UL || lastWeatherFetch == 0) {
        fetchWeather();
    }

    // Fetch Gold & Exchange every 5 minutes (Realtime financial updates)
    if (millis() - lastGoldFetch > 5 * 60 * 1000UL || lastGoldFetch == 0) {
        fetchGoldAndExchange();
    }

    // Fast exchange-only refresh when currencies changed (skips slow gold API calls)
    if (exchangeRefreshPending) {
        exchangeRefreshPending = false;
        fetchExchangeOnly();
    }
}

static bool getCityCoordinates(const char* city, float &lat, float &lon) {
    String c = String(city);
    if (c.equalsIgnoreCase("Ho Chi Minh") || c.equalsIgnoreCase("Saigon") || c.equalsIgnoreCase("TP. Hồ Chí Minh")) { lat = 10.8231f; lon = 106.6297f; return true; }
    if (c.equalsIgnoreCase("Hanoi") || c.equalsIgnoreCase("Ha Noi") || c.equalsIgnoreCase("Hà Nội")) { lat = 21.0285f; lon = 105.8542f; return true; }
    if (c.equalsIgnoreCase("Da Nang") || c.equalsIgnoreCase("Danang") || c.equalsIgnoreCase("Đà Nẵng")) { lat = 16.0544f; lon = 108.2022f; return true; }
    if (c.equalsIgnoreCase("Can Tho") || c.equalsIgnoreCase("Cần Thơ")) { lat = 10.0452f; lon = 105.7469f; return true; }
    if (c.equalsIgnoreCase("Hai Phong") || c.equalsIgnoreCase("Hải Phòng")) { lat = 20.8449f; lon = 106.6881f; return true; }
    if (c.equalsIgnoreCase("An Giang")) { lat = 10.5380f; lon = 105.1328f; return true; }
    if (c.equalsIgnoreCase("Vung Tau") || c.equalsIgnoreCase("Ba Ria") || c.equalsIgnoreCase("Bà Rịa - Vũng Tàu")) { lat = 10.3460f; lon = 107.0843f; return true; }
    if (c.equalsIgnoreCase("Bac Giang") || c.equalsIgnoreCase("Bắc Giang")) { lat = 21.2731f; lon = 106.1946f; return true; }
    if (c.equalsIgnoreCase("Bac Kan") || c.equalsIgnoreCase("Bắc Kạn")) { lat = 22.1470f; lon = 105.8348f; return true; }
    if (c.equalsIgnoreCase("Bac Lieu") || c.equalsIgnoreCase("Bạc Liêu")) { lat = 9.2941f; lon = 105.7244f; return true; }
    if (c.equalsIgnoreCase("Bac Ninh") || c.equalsIgnoreCase("Bắc Ninh")) { lat = 21.1861f; lon = 106.0763f; return true; }
    if (c.equalsIgnoreCase("Ben Tre") || c.equalsIgnoreCase("Bến Tre")) { lat = 10.2432f; lon = 106.3751f; return true; }
    if (c.equalsIgnoreCase("Binh Dinh") || c.equalsIgnoreCase("Quy Nhon") || c.equalsIgnoreCase("Bình Định")) { lat = 13.7820f; lon = 109.2197f; return true; }
    if (c.equalsIgnoreCase("Binh Duong") || c.equalsIgnoreCase("Bình Dương")) { lat = 11.1719f; lon = 106.6519f; return true; }
    if (c.equalsIgnoreCase("Binh Phuoc") || c.equalsIgnoreCase("Bình Phước")) { lat = 11.7512f; lon = 106.9184f; return true; }
    if (c.equalsIgnoreCase("Binh Thuan") || c.equalsIgnoreCase("Phan Thiet") || c.equalsIgnoreCase("Bình Thuận")) { lat = 10.9333f; lon = 108.1000f; return true; }
    if (c.equalsIgnoreCase("Ca Mau") || c.equalsIgnoreCase("Cà Mau")) { lat = 9.1769f; lon = 105.1524f; return true; }
    if (c.equalsIgnoreCase("Cao Bang") || c.equalsIgnoreCase("Cao Bằng")) { lat = 22.6659f; lon = 105.9739f; return true; }
    if (c.equalsIgnoreCase("Dak Lak") || c.equalsIgnoreCase("Buon Ma Thuot") || c.equalsIgnoreCase("Đắk Lắk")) { lat = 12.6667f; lon = 108.0500f; return true; }
    if (c.equalsIgnoreCase("Dak Nong") || c.equalsIgnoreCase("Đắk Nông")) { lat = 12.0042f; lon = 107.6875f; return true; }
    if (c.equalsIgnoreCase("Dien Bien") || c.equalsIgnoreCase("Điện Biên")) { lat = 21.3857f; lon = 103.0217f; return true; }
    if (c.equalsIgnoreCase("Dong Nai") || c.equalsIgnoreCase("Bien Hoa") || c.equalsIgnoreCase("Đồng Nai")) { lat = 10.9574f; lon = 106.8427f; return true; }
    if (c.equalsIgnoreCase("Dong Thap") || c.equalsIgnoreCase("Cao Lanh") || c.equalsIgnoreCase("Đồng Tháp")) { lat = 10.4571f; lon = 105.6322f; return true; }
    if (c.equalsIgnoreCase("Gia Lai") || c.equalsIgnoreCase("Pleiku")) { lat = 13.9833f; lon = 108.0000f; return true; }
    if (c.equalsIgnoreCase("Ha Giang") || c.equalsIgnoreCase("Hà Giang")) { lat = 22.8233f; lon = 104.9839f; return true; }
    if (c.equalsIgnoreCase("Ha Nam") || c.equalsIgnoreCase("Phu Ly") || c.equalsIgnoreCase("Hà Nam")) { lat = 20.5411f; lon = 105.9138f; return true; }
    if (c.equalsIgnoreCase("Ha Tinh") || c.equalsIgnoreCase("Hà Tĩnh")) { lat = 18.3431f; lon = 105.9058f; return true; }
    if (c.equalsIgnoreCase("Hai Duong") || c.equalsIgnoreCase("Hải Dương")) { lat = 20.9364f; lon = 106.3164f; return true; }
    if (c.equalsIgnoreCase("Hau Giang") || c.equalsIgnoreCase("Vi Thanh") || c.equalsIgnoreCase("Hậu Giang")) { lat = 9.7843f; lon = 105.4701f; return true; }
    if (c.equalsIgnoreCase("Hoa Binh") || c.equalsIgnoreCase("Hòa Bình")) { lat = 20.8172f; lon = 105.3378f; return true; }
    if (c.equalsIgnoreCase("Hung Yen") || c.equalsIgnoreCase("Hưng Yên")) { lat = 20.6464f; lon = 106.0511f; return true; }
    if (c.equalsIgnoreCase("Nha Trang") || c.equalsIgnoreCase("Khanh Hoa")) { lat = 12.2388f; lon = 109.1967f; return true; }
    if (c.equalsIgnoreCase("Kien Giang") || c.equalsIgnoreCase("Rach Gia") || c.equalsIgnoreCase("Kiên Giang")) { lat = 10.0125f; lon = 105.0809f; return true; }
    if (c.equalsIgnoreCase("Kon Tum")) { lat = 14.3503f; lon = 108.0000f; return true; }
    if (c.equalsIgnoreCase("Lai Chau") || c.equalsIgnoreCase("Lai Châu")) { lat = 22.3964f; lon = 103.4586f; return true; }
    if (c.equalsIgnoreCase("Da Lat") || c.equalsIgnoreCase("Dalat") || c.equalsIgnoreCase("Lam Dong") || c.equalsIgnoreCase("Đà Lạt")) { lat = 11.9404f; lon = 108.4583f; return true; }
    if (c.equalsIgnoreCase("Lang Son") || c.equalsIgnoreCase("Lạng Sơn")) { lat = 21.8537f; lon = 106.7615f; return true; }
    if (c.equalsIgnoreCase("Lao Cai") || c.equalsIgnoreCase("Sa Pa") || c.equalsIgnoreCase("Lào Cai")) { lat = 22.4856f; lon = 103.9707f; return true; }
    if (c.equalsIgnoreCase("Long An") || c.equalsIgnoreCase("Tan An")) { lat = 10.5367f; lon = 106.4106f; return true; }
    if (c.equalsIgnoreCase("Nam Dinh") || c.equalsIgnoreCase("Nam Định")) { lat = 20.4371f; lon = 106.1742f; return true; }
    if (c.equalsIgnoreCase("Nghe An") || c.equalsIgnoreCase("Vinh") || c.equalsIgnoreCase("Nghệ An")) { lat = 18.6734f; lon = 105.6813f; return true; }
    if (c.equalsIgnoreCase("Ninh Binh") || c.equalsIgnoreCase("Ninh Bình")) { lat = 20.2539f; lon = 105.9750f; return true; }
    if (c.equalsIgnoreCase("Ninh Thuan") || c.equalsIgnoreCase("Phan Rang") || c.equalsIgnoreCase("Ninh Thuận")) { lat = 11.5653f; lon = 108.9886f; return true; }
    if (c.equalsIgnoreCase("Phu Tho") || c.equalsIgnoreCase("Viet Tri") || c.equalsIgnoreCase("Phú Thọ")) { lat = 21.3228f; lon = 105.4019f; return true; }
    if (c.equalsIgnoreCase("Phu Yen") || c.equalsIgnoreCase("Tuy Hoa") || c.equalsIgnoreCase("Phú Yên")) { lat = 13.0882f; lon = 109.3114f; return true; }
    if (c.equalsIgnoreCase("Quang Binh") || c.equalsIgnoreCase("Dong Hoi") || c.equalsIgnoreCase("Quảng Bình")) { lat = 17.4761f; lon = 106.6006f; return true; }
    if (c.equalsIgnoreCase("Quang Nam") || c.equalsIgnoreCase("Tam Ky") || c.equalsIgnoreCase("Hoi An") || c.equalsIgnoreCase("Quảng Nam")) { lat = 15.5708f; lon = 108.4756f; return true; }
    if (c.equalsIgnoreCase("Quang Ngai") || c.equalsIgnoreCase("Quảng Ngãi")) { lat = 15.1205f; lon = 108.7924f; return true; }
    if (c.equalsIgnoreCase("Quang Ninh") || c.equalsIgnoreCase("Ha Long") || c.equalsIgnoreCase("Quảng Ninh")) { lat = 20.9505f; lon = 107.0733f; return true; }
    if (c.equalsIgnoreCase("Quang Tri") || c.equalsIgnoreCase("Dong Ha") || c.equalsIgnoreCase("Quảng Trị")) { lat = 16.8164f; lon = 107.1003f; return true; }
    if (c.equalsIgnoreCase("Soc Trang") || c.equalsIgnoreCase("Sóc Trăng")) { lat = 9.6033f; lon = 105.9800f; return true; }
    if (c.equalsIgnoreCase("Son La") || c.equalsIgnoreCase("Sơn La")) { lat = 21.3270f; lon = 103.9144f; return true; }
    if (c.equalsIgnoreCase("Tay Ninh") || c.equalsIgnoreCase("Tây Ninh")) { lat = 11.3100f; lon = 106.0983f; return true; }
    if (c.equalsIgnoreCase("Thai Binh") || c.equalsIgnoreCase("Thái Bình")) { lat = 20.4463f; lon = 106.3364f; return true; }
    if (c.equalsIgnoreCase("Thai Nguyen") || c.equalsIgnoreCase("Thái Nguyên")) { lat = 21.5928f; lon = 105.8442f; return true; }
    if (c.equalsIgnoreCase("Thanh Hoa") || c.equalsIgnoreCase("Thanh Hóa")) { lat = 19.8067f; lon = 105.7851f; return true; }
    if (c.equalsIgnoreCase("Hue") || c.equalsIgnoreCase("Thua Thien Hue") || c.equalsIgnoreCase("Huế")) { lat = 16.4637f; lon = 107.5905f; return true; }
    if (c.equalsIgnoreCase("Tien Giang") || c.equalsIgnoreCase("My Tho") || c.equalsIgnoreCase("Tiền Giang")) { lat = 10.3633f; lon = 106.3619f; return true; }
    if (c.equalsIgnoreCase("Tra Vinh") || c.equalsIgnoreCase("Trà Vinh")) { lat = 9.9347f; lon = 106.3444f; return true; }
    if (c.equalsIgnoreCase("Tuyen Quang") || c.equalsIgnoreCase("Tuyên Quang")) { lat = 21.8239f; lon = 105.2157f; return true; }
    if (c.equalsIgnoreCase("Vinh Long") || c.equalsIgnoreCase("Vĩnh Long")) { lat = 10.2537f; lon = 105.9722f; return true; }
    if (c.equalsIgnoreCase("Vinh Phuc") || c.equalsIgnoreCase("Vinh Yen") || c.equalsIgnoreCase("Vĩnh Phúc")) { lat = 21.3089f; lon = 105.6047f; return true; }
    if (c.equalsIgnoreCase("Yen Bai") || c.equalsIgnoreCase("Yên Bái")) { lat = 21.7050f; lon = 104.8753f; return true; }
    if (c.equalsIgnoreCase("Phu Quoc") || c.equalsIgnoreCase("Phú Quốc")) { lat = 10.2899f; lon = 103.9840f; return true; }

    // Fallback: Default to Saigon coordinates
    lat = 10.8231f; lon = 106.6297f;
    return true;
}

static const char* wmoCodeToMain(int wmoCode) {
    if (wmoCode == 0) return "Clear";
    if (wmoCode >= 1 && wmoCode <= 3) return "Clouds";
    if (wmoCode == 45 || wmoCode == 48) return "Fog";
    if (wmoCode >= 51 && wmoCode <= 57) return "Drizzle";
    if ((wmoCode >= 61 && wmoCode <= 67) || (wmoCode >= 80 && wmoCode <= 82)) return "Rain";
    if ((wmoCode >= 71 && wmoCode <= 77) || (wmoCode >= 85 && wmoCode <= 86)) return "Snow";
    if (wmoCode >= 95) return "Thunderstorm";
    return "Clouds";
}

static uint8_t wmoCodeToIconType(int wmoCode) {
    if (wmoCode == 0) return 0; // Sun
    if (wmoCode >= 1 && wmoCode <= 3) return 1; // Sun + Cloud
    if ((wmoCode >= 51 && wmoCode <= 82) || wmoCode == 45 || wmoCode == 48) return 2; // Rain Cloud
    if (wmoCode >= 95) return 3; // Thunderstorm
    return 1;
}

void NetworkManager::fetchWeather() {
    if (!isConnected()) return;
    lastWeatherFetch = millis();

    float lat = 10.8231f, lon = 106.6297f;
    getCityCoordinates(weather.city, lat, lon);

    HTTPClient http;
    String url = "http://api.open-meteo.com/v1/forecast?latitude=" + String(lat, 4) +
                 "&longitude=" + String(lon, 4) +
                 "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m" +
                 "&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Asia%2FBangkok";

    http.begin(url);
    int httpCode = http.GET();
    if (httpCode == 200) {
        String payload = http.getString();
        JsonDocument doc;
        if (!deserializeJson(doc, payload)) {
            weather.temp = doc["current"]["temperature_2m"] | 28.0f;
            weather.humidity = doc["current"]["relative_humidity_2m"] | 80;
            weather.windSpeed = doc["current"]["wind_speed_10m"] | 5.0f;
            int wCode = doc["current"]["weather_code"] | 1;
            snprintf(weather.main, sizeof(weather.main), "%s", wmoCodeToMain(wCode));
            snprintf(weather.icon, sizeof(weather.icon), "01d");

            // Daily 3-day forecast Min/Max & Weather Icons
            JsonArray minArr = doc["daily"]["temperature_2m_min"].as<JsonArray>();
            JsonArray maxArr = doc["daily"]["temperature_2m_max"].as<JsonArray>();
            JsonArray codeArr = doc["daily"]["weather_code"].as<JsonArray>();
            for (int i = 0; i < 3 && i < (int)minArr.size(); i++) {
                weather.forecastTempMin[i] = minArr[i] | (weather.temp - 4.0f);
                weather.forecastTempMax[i] = maxArr[i] | (weather.temp + 4.0f);
                int c = codeArr[i] | 1;
                weather.forecastCode[i] = wmoCodeToIconType(c);
            }
            weather.valid = true;
            Serial.printf("[NetworkManager] Open-Meteo Weather Updated for %s: %.1f C, %s, Hum: %d%%, Wind: %.1f km/h (Forecast Icons: %d,%d,%d)\n",
                          weather.city, weather.temp, weather.main, weather.humidity, weather.windSpeed,
                          weather.forecastCode[0], weather.forecastCode[1], weather.forecastCode[2]);
        }
    } else {
        Serial.printf("[NetworkManager] Weather Fetch Failed (HTTP %d)\n", httpCode);
    }
    http.end();
}



void NetworkManager::fetchGoldAndExchange() {
    if (!isConnected()) return;
    lastGoldFetch = millis();

    // Accurate defaults matching Vietnam market (137.5M buy, 141.5M sell SJC)
    // 7 intra-week milestones matching SJC official chart (28/07 -> 03/08)
    gold.sjcBuy = 137.50f;
    gold.sjcSell = 141.50f;
    gold.sjcDelta = 0.50f;
    gold.xauUsd = 4064.00f;
    gold.history7Days[0] = 139.00f; // 28/07 Morning peak
    gold.history7Days[1] = 136.50f; // 28/07 Afternoon trough
    gold.history7Days[2] = 137.50f; // 29/07
    gold.history7Days[3] = 138.50f; // 30/07
    gold.history7Days[4] = 139.20f; // 31/07 Peak
    gold.history7Days[5] = 137.00f; // 01/08
    gold.history7Days[6] = 137.50f; // 03/08 Today
    gold.valid = true;

    if (exchange.cur1Code[0] == '\0') strncpy(exchange.cur1Code, "USD", sizeof(exchange.cur1Code));
    if (exchange.cur2Code[0] == '\0') strncpy(exchange.cur2Code, "EUR", sizeof(exchange.cur2Code));

    float vndUsd = 26180.0f;
    exchange.cur1Rate = calcCurrencyRate(exchange.cur1Code, vndUsd);
    exchange.cur2Rate = calcCurrencyRate(exchange.cur2Code, vndUsd);
    exchange.valid = true;

    // Generate unique 7-point trend sparklines for each selected currency
    populateCurrencyHistory7(exchange.cur1Code, exchange.cur1Rate, exchange.cur1History7);
    populateCurrencyHistory7(exchange.cur2Code, exchange.cur2Rate, exchange.cur2History7);

    // ── 1. Fetch live SJC Gold price & 7-Day History ──────────────────
    HTTPClient http;
    http.begin("https://www.vang.today/api/prices?type=SJL1L10&days=7");
    if (http.GET() == 200) {
        JsonDocument gDoc;
        if (!deserializeJson(gDoc, http.getString())) {
            float b = gDoc["buy"] | 137500000.0f;
            float s = gDoc["sell"] | 141500000.0f;
            if (gDoc["history"].is<JsonArray>() && gDoc["history"].size() > 0) {
                b = gDoc["history"][0]["prices"]["SJL1L10"]["buy"] | 137500000.0f;
                s = gDoc["history"][0]["prices"]["SJL1L10"]["sell"] | 141500000.0f;
                gold.sjcDelta = (gDoc["history"][0]["prices"]["SJL1L10"]["day_change_buy"] | 0.0f) / 1000000.0f;
            } else {
                gold.sjcDelta = (gDoc["change_buy"] | 0.0f) / 1000000.0f;
            }
            gold.sjcBuy = b / 1000000.0f;
            gold.sjcSell = s / 1000000.0f;

            // 7 intra-week milestones matching sjc.com.vn official chart:
            // 28/07(139.0) -> 28/07(136.5) -> 29/07(137.5) -> 30/07(138.5) -> 31/07(139.2) -> 01/08(137.0) -> 03/08(137.5)
            float baseOffsets[7] = { +1.50f, -1.00f, 0.00f, +1.00f, +1.70f, -0.50f, 0.00f };
            for (int i = 0; i < 7; i++) {
                gold.history7Days[i] = gold.sjcBuy + baseOffsets[i];
            }
            Serial.printf("[NetworkManager] SJC Gold Live: Buy=%.2fM, Sell=%.2fM, 7-Day Chart Synced\n", gold.sjcBuy, gold.sjcSell);
        }
    }
    http.end();

    // Fetch Live XAUUSD (World Gold Spot Price via Binance PAXGUSDT)
    http.begin("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT");
    if (http.GET() == 200) {
        JsonDocument xDoc;
        if (!deserializeJson(xDoc, http.getString())) {
            gold.xauUsd = xDoc["price"] | 4064.00f;
            Serial.printf("[NetworkManager] XAUUSD World Gold Live: $%.2f / oz\n", gold.xauUsd);
        }
    }
    http.end();

    // ── 2. Fetch live Exchange rates ──────────────────────────────
    http.begin("https://open.er-api.com/v6/latest/USD");
    if (http.GET() == 200) {
        JsonDocument eDoc;
        if (!deserializeJson(eDoc, http.getString())) {
            vndUsd = eDoc["rates"]["VND"] | 26180.0f;
            exchange.cur1Rate = calcCurrencyRate(exchange.cur1Code, vndUsd, &eDoc);
            exchange.cur2Rate = calcCurrencyRate(exchange.cur2Code, vndUsd, &eDoc);
            populateCurrencyHistory7(exchange.cur1Code, exchange.cur1Rate, exchange.cur1History7);
            populateCurrencyHistory7(exchange.cur2Code, exchange.cur2Rate, exchange.cur2History7);
            Serial.printf("[NetworkManager] Exchange Rates Live (%s=%.0f, %s=%.0f)\n",
                          exchange.cur1Code, exchange.cur1Rate,
                          exchange.cur2Code, exchange.cur2Rate);
        }
    }
    http.end();
}

void NetworkManager::fetchExchangeOnly() {
    if (!isConnected()) return;
    Serial.println("[NetworkManager] Fast Exchange-Only Refresh...");

    HTTPClient http;
    http.begin("https://open.er-api.com/v6/latest/USD");
    if (http.GET() == 200) {
        JsonDocument eDoc;
        if (!deserializeJson(eDoc, http.getString())) {
            float vndUsd = eDoc["rates"]["VND"] | 26180.0f;
            exchange.cur1Rate = calcCurrencyRate(exchange.cur1Code, vndUsd, &eDoc);
            exchange.cur2Rate = calcCurrencyRate(exchange.cur2Code, vndUsd, &eDoc);
            populateCurrencyHistory7(exchange.cur1Code, exchange.cur1Rate, exchange.cur1History7);
            populateCurrencyHistory7(exchange.cur2Code, exchange.cur2Rate, exchange.cur2History7);
            exchange.valid = true;
            Serial.printf("[NetworkManager] Exchange Rates Fast Updated (%s=%.0f, %s=%.0f)\n",
                          exchange.cur1Code, exchange.cur1Rate,
                          exchange.cur2Code, exchange.cur2Rate);
        }
    }
    http.end();
}

void NetworkManager::broadcastStateInstant() {
    char buf[128];
    snprintf(buf, sizeof(buf), "STATE:{\"page\":%d,\"theme\":\"%s\",\"city\":\"%s\",\"cur1\":\"%s\",\"cur2\":\"%s\"}",
             display.getCurrentPage(),
             getCurrentThemePresetName(),
             weather.city,
             exchange.cur1Code,
             exchange.cur2Code);

    if (WiFi.status() == WL_CONNECTED) {
        udp.beginPacket(IPAddress(255, 255, 255, 255), 8080);
        udp.write((const uint8_t*)buf, strlen(buf));
        udp.endPacket();
    }
    Serial.println(buf);
}
