#include "PCMonitor.h"

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

        // Handshake protocol support
        if (line == "PING_DASHBOARD" || line == "PING") {
            Serial.println("PONG_DASHBOARD");
            return;
        }

        if (line.startsWith("{") && line.endsWith("}")) {
            parseJsonData(line.c_str());
        }
    }
}

bool PCMonitor::parseJsonData(const char* jsonStr) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, jsonStr);
    if (error) {
        return false;
    }

    if (doc.containsKey("cpu")) cpuLoad = doc["cpu"].as<uint8_t>();
    if (doc.containsKey("cputemp")) cpuTemp = doc["cputemp"].as<uint8_t>();
    if (doc.containsKey("ram")) ramLoad = doc["ram"].as<uint8_t>();
    if (doc.containsKey("gpu")) gpuLoad = doc["gpu"].as<uint8_t>();
    if (doc.containsKey("gputemp")) gpuTemp = doc["gputemp"].as<uint8_t>();
    if (doc.containsKey("vram")) vramLoad = doc["vram"].as<uint8_t>();
    if (doc.containsKey("net_down")) netDown = doc["net_down"].as<uint32_t>();
    if (doc.containsKey("net_up")) netUp = doc["net_up"].as<uint32_t>();

    // Shift history for line charts
    for (int i = 0; i < HISTORY_SIZE - 1; i++) {
        cpuHistory[i] = cpuHistory[i + 1];
        gpuHistory[i] = gpuHistory[i + 1];
    }
    cpuHistory[HISTORY_SIZE - 1] = cpuLoad;
    gpuHistory[HISTORY_SIZE - 1] = gpuLoad;

    // Parse Disks Array
    if (doc.containsKey("disks") && doc["disks"].is<JsonArray>()) {
        JsonArray diskArr = doc["disks"].as<JsonArray>();
        diskCount = 0;
        for (JsonObject d : diskArr) {
            if (diskCount >= 4) break;
            const char* dName = d["name"] | "C";
            snprintf(disks[diskCount].name, sizeof(disks[diskCount].name), "%s", dName);
            disks[diskCount].usedPercent = d["used"] | 0;
            diskCount++;
        }
    }

    lastDataTime = millis();
    return true;
}
