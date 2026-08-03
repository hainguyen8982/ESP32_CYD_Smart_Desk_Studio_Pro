#include "NetworkManager.h"
#include "HardwareManager.h"
#include "PCMonitor.h"
#include "DeskUtilities.h"
#include "Theme.h"
#include "DisplayManager.h"
#include "TouchManager.h"

extern DisplayManager display;

NetworkManager network;

NetworkManager::NetworkManager()
    : server(80),
      lastWeatherFetch(0),
      lastGoldFetch(0),
      remotePage(-1) {
    memset(&weather, 0, sizeof(weather));
    memset(&gold, 0, sizeof(gold));
    memset(&exchange, 0, sizeof(exchange));
    snprintf(weather.city, sizeof(weather.city), DEFAULT_CITY);
}

void NetworkManager::begin() {
    Serial.println("[NetworkManager] Connecting WiFi via WiFiManager...");
    
    WiFiManager wm;
    wm.setConfigPortalTimeout(180); // 3 minutes timeout if no AP config
    wm.setBreakAfterConfig(true);

    if (!wm.autoConnect("ESP32_CYD_Desk_Setup")) {
        Serial.println("[NetworkManager] Failed to connect WiFi, running AP mode");
        hardware.setRGBColor(COLOR_YELLOW);
    } else {
        Serial.print("[NetworkManager] WiFi Connected! IP: ");
        Serial.println(WiFi.localIP());
        hardware.setRGBColor(COLOR_GREEN);
    }

    // Configure NTP Time (Vietnam GMT+7)
    configTime(7 * 3600, 0, "vn.pool.ntp.org", "time.google.com", "pool.ntp.org");

    // Load saved Weather City from NVS
    Preferences prefs;
    prefs.begin("weather", true);
    if (prefs.isKey("city")) {
        String savedCity = prefs.getString("city", DEFAULT_CITY);
        snprintf(weather.city, sizeof(weather.city), "%s", savedCity.c_str());
    }
    prefs.end();

    setupWebRoutes();
    server.begin();
    Serial.println("[NetworkManager] AsyncWebServer Started on Port 80");

    fetchWeather();
    fetchGoldAndExchange();
}

void NetworkManager::setCity(const char* newCity) {
    if (!newCity || newCity[0] == '\0') return;
    snprintf(weather.city, sizeof(weather.city), "%s", newCity);
    Preferences prefs;
    prefs.begin("weather", false);
    prefs.putString("city", weather.city);
    prefs.end();
    Serial.printf("[NetworkManager] Weather City changed to: %s\n", weather.city);
    fetchWeather();
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
        String jsonStr = String((char*)data).substring(0, len);
        if (pcMonitor.parseJsonData(jsonStr.c_str())) {
            sendCORSResponse(request, 200, "{\"status\":\"ok\"}");
        } else {
            sendCORSResponse(request, 400, "{\"status\":\"invalid json\"}");
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
        if (request->hasParam("name")) {
            String c = request->getParam("name")->value();
            setCity(c.c_str());
            sendCORSResponse(request, 200, "{\"status\":\"ok\",\"city\":\"" + c + "\"}");
            return;
        }
        sendCORSResponse(request, 200, "{\"city\":\"" + String(weather.city) + "\"}");
    });

    server.on("/api/weather/city", HTTP_POST, [this](AsyncWebServerRequest *request) {}, NULL,
        [this](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, data, len);
            if (!err && doc.containsKey("city")) {
                const char* c = doc["city"];
                setCity(c);
                sendCORSResponse(request, 200, "{\"status\":\"ok\",\"city\":\"" + String(c) + "\"}");
                return;
            }
            sendCORSResponse(request, 400, "{\"status\":\"invalid request\"}");
        });

    // Theme API - GET current theme JSON
    server.on("/api/theme", HTTP_GET, [](AsyncWebServerRequest *request) {
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
            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, data, len);
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

    // Exchange Selection API - POST { "cur1": "USD", "cur2": "EUR" }
    server.on("/api/exchange", HTTP_POST, [](AsyncWebServerRequest *request) {}, NULL,
        [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            JsonDocument doc;
            if (!deserializeJson(doc, data, len)) {
                ExchangeData& ex = network.getExchangeMutable();
                if (!doc["cur1"].isNull()) {
                    strncpy(ex.cur1Code, doc["cur1"], 7);
                }
                if (!doc["cur2"].isNull()) {
                    strncpy(ex.cur2Code, doc["cur2"], 7);
                }
                if (!doc["cur3"].isNull()) {
                    strncpy(ex.cur3Code, doc["cur3"], 7);
                }
                // Recalculate exchange rates immediately for selected currencies
                float baseVnd = ex.cur1Rate > 0 ? 26180.0f : 26180.0f;
                ex.cur1Rate = calcCurrencyRate(ex.cur1Code, baseVnd);
                ex.cur2Rate = calcCurrencyRate(ex.cur2Code, baseVnd);
                ex.cur3Rate = calcCurrencyRate(ex.cur3Code, baseVnd);

                sendCORSResponse(request, 200, "{\"status\":\"ok\"}");
                return;
            }
            sendCORSResponse(request, 400, "{\"status\":\"invalid json\"}");
        });
}

void NetworkManager::update() {
    if (!isConnected()) return;

    // Fetch Weather every 15 minutes
    if (millis() - lastWeatherFetch > 15 * 60 * 1000UL || lastWeatherFetch == 0) {
        fetchWeather();
    }

    // Fetch Gold & Exchange every 30 minutes
    if (millis() - lastGoldFetch > 30 * 60 * 1000UL || lastGoldFetch == 0) {
        fetchGoldAndExchange();
    }
}

void NetworkManager::fetchWeather() {
    if (!isConnected()) return;
    lastWeatherFetch = millis();

    HTTPClient http;
    String url = "http://api.openweathermap.org/data/2.5/weather?q=" + String(weather.city) +
                 "&units=metric&appid=" + String(DEFAULT_OPENWEATHER_KEY);

    http.begin(url);
    int httpCode = http.GET();
    if (httpCode == 200) {
        String payload = http.getString();
        JsonDocument doc;
        if (!deserializeJson(doc, payload)) {
            weather.temp = doc["main"]["temp"] | 28.5f;
            weather.humidity = doc["main"]["humidity"] | 75;
            weather.windSpeed = (doc["wind"]["speed"] | 3.5f) * 3.6f; // m/s to km/h
            snprintf(weather.main, sizeof(weather.main), "%s", doc["weather"][0]["main"] | "Clear");
            snprintf(weather.icon, sizeof(weather.icon), "%s", doc["weather"][0]["icon"] | "01d");
            weather.valid = true;
            Serial.printf("[NetworkManager] Weather Updated for %s: %.1f C, %s, Wind: %.1f km/h\n", weather.city, weather.temp, weather.main, weather.windSpeed);
        }
    } else {
        // Fallback city-specific weather lookup if offline or using dummy API key
        String c = String(weather.city);
        if (c.equalsIgnoreCase("Da Lat") || c.equalsIgnoreCase("Dalat")) {
            weather.temp = 18.5f; weather.humidity = 85; weather.windSpeed = 8.5f;
            snprintf(weather.main, sizeof(weather.main), "Drizzle");
            weather.forecastTempMin[0] = 14.0f; weather.forecastTempMax[0] = 22.0f;
            weather.forecastTempMin[1] = 13.0f; weather.forecastTempMax[1] = 21.0f;
            weather.forecastTempMin[2] = 15.0f; weather.forecastTempMax[2] = 23.0f;
        } else if (c.equalsIgnoreCase("Ho Chi Minh") || c.equalsIgnoreCase("Saigon")) {
            weather.temp = 33.5f; weather.humidity = 78; weather.windSpeed = 14.2f;
            snprintf(weather.main, sizeof(weather.main), "Rain");
            weather.forecastTempMin[0] = 26.0f; weather.forecastTempMax[0] = 34.0f;
            weather.forecastTempMin[1] = 25.0f; weather.forecastTempMax[1] = 33.0f;
            weather.forecastTempMin[2] = 25.0f; weather.forecastTempMax[2] = 32.0f;
        } else if (c.equalsIgnoreCase("Da Nang") || c.equalsIgnoreCase("Danang")) {
            weather.temp = 31.2f; weather.humidity = 72; weather.windSpeed = 16.0f;
            snprintf(weather.main, sizeof(weather.main), "Clouds");
            weather.forecastTempMin[0] = 25.0f; weather.forecastTempMax[0] = 33.0f;
            weather.forecastTempMin[1] = 26.0f; weather.forecastTempMax[1] = 34.0f;
            weather.forecastTempMin[2] = 24.0f; weather.forecastTempMax[2] = 32.0f;
        } else if (c.equalsIgnoreCase("Nha Trang")) {
            weather.temp = 30.0f; weather.humidity = 75; weather.windSpeed = 15.0f;
            snprintf(weather.main, sizeof(weather.main), "Sunny");
            weather.forecastTempMin[0] = 25.0f; weather.forecastTempMax[0] = 32.0f;
            weather.forecastTempMin[1] = 26.0f; weather.forecastTempMax[1] = 33.0f;
            weather.forecastTempMin[2] = 24.0f; weather.forecastTempMax[2] = 31.0f;
        } else if (c.equalsIgnoreCase("Sapa") || c.equalsIgnoreCase("Sa Pa")) {
            weather.temp = 16.0f; weather.humidity = 88; weather.windSpeed = 6.0f;
            snprintf(weather.main, sizeof(weather.main), "Mist");
            weather.forecastTempMin[0] = 12.0f; weather.forecastTempMax[0] = 19.0f;
            weather.forecastTempMin[1] = 11.0f; weather.forecastTempMax[1] = 18.0f;
            weather.forecastTempMin[2] = 13.0f; weather.forecastTempMax[2] = 20.0f;
        } else if (c.equalsIgnoreCase("Hue")) {
            weather.temp = 27.5f; weather.humidity = 82; weather.windSpeed = 11.0f;
            snprintf(weather.main, sizeof(weather.main), "Rain");
            weather.forecastTempMin[0] = 22.0f; weather.forecastTempMax[0] = 29.0f;
            weather.forecastTempMin[1] = 23.0f; weather.forecastTempMax[1] = 30.0f;
            weather.forecastTempMin[2] = 21.0f; weather.forecastTempMax[2] = 28.0f;
        } else {
            weather.temp = 29.0f; weather.humidity = 70; weather.windSpeed = 12.5f;
            snprintf(weather.main, sizeof(weather.main), "Sunny");
            weather.forecastTempMin[0] = 25.0f; weather.forecastTempMax[0] = 33.0f;
            weather.forecastTempMin[1] = 24.0f; weather.forecastTempMax[1] = 32.0f;
            weather.forecastTempMin[2] = 26.0f; weather.forecastTempMax[2] = 34.0f;
        }
        snprintf(weather.icon, sizeof(weather.icon), "01d");
        weather.valid = true;
    }
    http.end();

    // ── 3-Day Forecast Fetch / Populating ─────────────────────────────
    String forecastUrl = "http://api.openweathermap.org/data/2.5/forecast?q=" + String(weather.city) +
                         "&units=metric&cnt=24&appid=" + String(DEFAULT_OPENWEATHER_KEY);
    http.begin(forecastUrl);
    int fcCode = http.GET();
    if (fcCode == 200) {
        String fcPayload = http.getString();
        JsonDocument fcDoc;
        if (!deserializeJson(fcDoc, fcPayload)) {
            JsonArray list = fcDoc["list"];
            int idx = 0;
            for (size_t i = 0; i < list.size() && idx < 3; i += 8) {
                weather.forecastTempMin[idx] = list[i]["main"]["temp_min"] | (weather.temp - 3.0f + idx);
                weather.forecastTempMax[idx] = list[i]["main"]["temp_max"] | (weather.temp + 4.0f + idx);
                idx++;
            }
        }
    } else {
        // Fallback 3-day forecast temperatures relative to current temp
        weather.forecastTempMin[0] = weather.temp - 4.0f;
        weather.forecastTempMax[0] = weather.temp + 4.0f;
        weather.forecastTempMin[1] = weather.temp - 5.0f;
        weather.forecastTempMax[1] = weather.temp + 3.0f;
        weather.forecastTempMin[2] = weather.temp - 3.0f;
        weather.forecastTempMax[2] = weather.temp + 5.0f;
    }
    http.end();
}

void NetworkManager::fetchGoldAndExchange() {
    if (!isConnected()) return;
    lastGoldFetch = millis();

    // Accurate defaults matching Vietnam market (137M buy, 141M sell SJC)
    gold.sjcBuy = 137.00f;
    gold.sjcSell = 141.00f;
    gold.sjcDelta = 0.00f;
    gold.xauUsd = 2890.50f;
    gold.valid = true;

    if (exchange.cur1Code[0] == '\0') strncpy(exchange.cur1Code, "USD", sizeof(exchange.cur1Code));
    if (exchange.cur2Code[0] == '\0') strncpy(exchange.cur2Code, "EUR", sizeof(exchange.cur2Code));
    if (exchange.cur3Code[0] == '\0') strncpy(exchange.cur3Code, "JPY", sizeof(exchange.cur3Code));

    float vndUsd = 26180.0f;
    exchange.cur1Rate = calcCurrencyRate(exchange.cur1Code, vndUsd);
    exchange.cur2Rate = calcCurrencyRate(exchange.cur2Code, vndUsd);
    exchange.cur3Rate = calcCurrencyRate(exchange.cur3Code, vndUsd);
    exchange.valid = true;

    // ── 1. Fetch live SJC Gold price ─────────────────────────────────
    HTTPClient http;
    http.begin("https://www.vang.today/api/prices?type=SJL1L10");
    if (http.GET() == 200) {
        JsonDocument gDoc;
        if (!deserializeJson(gDoc, http.getString())) {
            float b = gDoc["buy"] | 137000000.0f;
            float s = gDoc["sell"] | 141000000.0f;
            gold.sjcBuy = b / 1000000.0f;
            gold.sjcSell = s / 1000000.0f;
            gold.sjcDelta = (gDoc["change_buy"] | 0.0f) / 1000000.0f;
            Serial.printf("[NetworkManager] SJC Gold Live: Buy=%.2fM, Sell=%.2fM\n", gold.sjcBuy, gold.sjcSell);
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
            exchange.cur3Rate = calcCurrencyRate(exchange.cur3Code, vndUsd, &eDoc);
            Serial.printf("[NetworkManager] Exchange Rates Live (%s=%.0f, %s=%.0f, %s=%.1f)\n",
                          exchange.cur1Code, exchange.cur1Rate,
                          exchange.cur2Code, exchange.cur2Rate,
                          exchange.cur3Code, exchange.cur3Rate);
        }
    }
    http.end();
}
