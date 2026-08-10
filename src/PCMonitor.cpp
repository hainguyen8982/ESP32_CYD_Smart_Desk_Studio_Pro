#include "PCMonitor.h"
#include "DisplayManager.h"
#include "NetworkManager.h"
#include "DeskUtilities.h"
#include "Theme.h"
#include "DynamicSkinManager.h"
#include <Preferences.h>

PCMonitor pcMonitor;

PCMonitor::PCMonitor()
    : cpuLoad(0), cpuTemp(0), ramLoad(0),
      gpuLoad(0), gpuTemp(0), vramLoad(0),
      netDown(0), netUp(0), diskCount(0),
      lastDataTime(0) {
    memset(cpuHistory, 0, sizeof(cpuHistory));
    memset(gpuHistory, 0, sizeof(gpuHistory));
    memset(disks, 0, sizeof(disks));
}

void PCMonitor::begin() {
    Serial.println("[PCMonitor] Serial Listener Initialized at 115200 bps");
}

bool PCMonitor::isConnected() const {
    return (millis() - lastDataTime < PC_MONITOR_TIMEOUT_MS);
}

void PCMonitor::update() {
    // Read JSON string from Serial if available
    if (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();

        // Handshake protocol support with real-time state query
        if (line == "PING_DASHBOARD" || line == "PING") {
            Serial.printf("PONG_DASHBOARD {\"page\":%d,\"theme\":\"%s\"}\n",
                          display.getCurrentPage(),
                          getCurrentThemePresetName());
            return;
        }

        if (line.startsWith("SKIN_JSON:")) {
            String payload = line.substring(10);
            if (g_skinMgr.parseAndSaveSkinJSON(payload)) {
                Serial.println("SKIN_SYNC_SUCCESS");
                display.refreshDisplay();
            }
            return;
        }

        if (line.startsWith("{") && line.endsWith("}")) {
            parseJsonData(line.c_str());
        }
    }
}

bool PCMonitor::parseJsonData(const char* jsonStr) {
    if (!jsonStr) return false;
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, jsonStr);
    if (error) {
        Serial.printf("[PCMonitor] JSON Parse Error: %s\n", error.c_str());
        return false;
    }

    if (!doc["cpu"].isNull())         cpuLoad  = doc["cpu"].as<uint8_t>();
    else if (!doc["cpuLoad"].isNull()) cpuLoad  = doc["cpuLoad"].as<uint8_t>();

    if (!doc["cputemp"].isNull())     cpuTemp  = doc["cputemp"].as<uint8_t>();
    else if (!doc["cpuTemp"].isNull()) cpuTemp  = doc["cpuTemp"].as<uint8_t>();

    if (!doc["ram"].isNull())         ramLoad  = doc["ram"].as<uint8_t>();
    else if (!doc["ramLoad"].isNull()) ramLoad  = doc["ramLoad"].as<uint8_t>();

    if (!doc["gpu"].isNull())         gpuLoad  = doc["gpu"].as<uint8_t>();
    else if (!doc["gpuLoad"].isNull()) gpuLoad  = doc["gpuLoad"].as<uint8_t>();

    if (!doc["gputemp"].isNull())     gpuTemp  = doc["gputemp"].as<uint8_t>();
    else if (!doc["gpuTemp"].isNull()) gpuTemp  = doc["gpuTemp"].as<uint8_t>();

    if (!doc["vram"].isNull())        vramLoad = doc["vram"].as<uint8_t>();
    else if (!doc["vramLoad"].isNull()) vramLoad = doc["vramLoad"].as<uint8_t>();

    if (!doc["net_down"].isNull())    netDown  = doc["net_down"].as<uint32_t>();
    else if (!doc["netDown"].isNull()) netDown  = doc["netDown"].as<uint32_t>();

    if (!doc["net_up"].isNull())      netUp    = doc["net_up"].as<uint32_t>();
    else if (!doc["netUp"].isNull())   netUp    = doc["netUp"].as<uint32_t>();

    if (!doc["isMediaPlaying"].isNull()) {
        display.setMediaPlaying(doc["isMediaPlaying"].as<bool>());
    }

    if (!doc["mediaTitle"].isNull()) {
        display.setMediaInfo(doc["mediaTitle"].as<const char*>(), doc["mediaArtist"] | "");
    }

    if (!doc["page"].isNull()) {
        uint8_t p = doc["page"].as<uint8_t>();
        if (p < TOTAL_PAGES) {
            display.setCurrentPage(p);
        }
    }

    if (!doc["preset"].isNull()) {
        const char* p = doc["preset"].as<const char*>();
        if (p) {
            if (strcmp(p, "ocean_dark") == 0) applyOceanDarkTheme();
            else if (strcmp(p, "cyberpunk") == 0) applyCyberpunkTheme();
            else if (strcmp(p, "forest") == 0) applyForestTheme();
            else if (strcmp(p, "cherry") == 0) applyCherryTheme();
            else if (strcmp(p, "light_day") == 0) applyLightDayTheme();
            else if (strcmp(p, "retro_green") == 0) applyRetroGreenTheme();
            saveTheme();
        }
    }

    if (!doc["city"].isNull()) {
        const char* c = doc["city"].as<const char*>();
        if (c) {
            network.setCity(c);
        }
    }

    if (!doc["alarm_h"].isNull() && !doc["alarm_m"].isNull()) {
        uint8_t ah = doc["alarm_h"].as<uint8_t>();
        uint8_t am = doc["alarm_m"].as<uint8_t>();
        bool en = doc["alarm_enable"] | true;
        deskUtils.setAlarm(ah, am, en);
    }

    if (!doc["cur1"].isNull() || !doc["cur2"].isNull()) {
        ExchangeData& ex = network.getExchangeMutable();
        bool changed = false;
        if (!doc["cur1"].isNull()) {
            const char* c1 = doc["cur1"].as<const char*>();
            if (c1 && strcmp(ex.cur1Code, c1) != 0) {
                strncpy(ex.cur1Code, c1, 7);
                ex.cur1Code[7] = '\0';
                changed = true;
            }
        }
        if (!doc["cur2"].isNull()) {
            const char* c2 = doc["cur2"].as<const char*>();
            if (c2 && strcmp(ex.cur2Code, c2) != 0) {
                strncpy(ex.cur2Code, c2, 7);
                ex.cur2Code[7] = '\0';
                changed = true;
            }
        }
        if (changed) {
            Preferences prefs;
            prefs.begin("exchange", false);
            prefs.putString("cur1", ex.cur1Code);
            prefs.putString("cur2", ex.cur2Code);
            prefs.end();
            network.triggerAsyncExchangeRefresh();
        }
    }

    // Shift history for line charts
    for (int i = 0; i < HISTORY_SIZE - 1; i++) {
        cpuHistory[i] = cpuHistory[i + 1];
        gpuHistory[i] = gpuHistory[i + 1];
        netDownHistory[i] = netDownHistory[i + 1];
        netUpHistory[i] = netUpHistory[i + 1];
    }
    cpuHistory[HISTORY_SIZE - 1] = cpuLoad;
    gpuHistory[HISTORY_SIZE - 1] = gpuLoad;
    netDownHistory[HISTORY_SIZE - 1] = (uint8_t)constrain(netDown / 100, 0, 100);
    netUpHistory[HISTORY_SIZE - 1] = (uint8_t)constrain(netUp / 50, 0, 100);

    // Parse Disks Array or disk1Load/disk2Load fallback
    if (!doc["disks"].isNull() && doc["disks"].is<JsonArray>()) {
        JsonArray diskArr = doc["disks"].as<JsonArray>();
        diskCount = 0;
        for (JsonObject d : diskArr) {
            if (diskCount >= 4) break;
            const char* dName = d["name"] | "C";
            snprintf(disks[diskCount].name, sizeof(disks[diskCount].name), "%s", dName);
            disks[diskCount].usedPercent = d["used"] | 0;
            diskCount++;
        }
    } else if (!doc["disk1Load"].isNull()) {
        diskCount = 1;
        snprintf(disks[0].name, sizeof(disks[0].name), "C");
        disks[0].usedPercent = doc["disk1Load"].as<uint8_t>();
        if (!doc["disk2Load"].isNull() && doc["disk2Load"].as<uint8_t>() > 0) {
            snprintf(disks[1].name, sizeof(disks[1].name), "D");
            disks[1].usedPercent = doc["disk2Load"].as<uint8_t>();
            diskCount = 2;
        }
    }

    lastDataTime = millis();
    // Send current state back to PC app for bidirectional sync
    Serial.printf("STATE:{\"page\":%d,\"theme\":\"%s\",\"city\":\"%s\",\"cur1\":\"%s\",\"cur2\":\"%s\"}\n",
                  display.getCurrentPage(),
                  getCurrentThemePresetName(),
                  network.getWeather().city,
                  network.getExchange().cur1Code,
                  network.getExchange().cur2Code);
    return true;
}
