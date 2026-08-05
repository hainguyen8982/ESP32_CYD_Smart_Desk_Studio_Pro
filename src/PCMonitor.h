#ifndef PC_MONITOR_H
#define PC_MONITOR_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "Config.h"

struct DiskInfo {
    char name[4];
    uint8_t usedPercent;
};

class PCMonitor {
public:
    PCMonitor();
    void begin();
    void update();
    bool parseJsonData(const char* jsonStr);
    
    bool isConnected() const;
    unsigned long getLastDataTime() const { return lastDataTime; }

    // Stats Accessors
    uint8_t getCpuLoad() const { return cpuLoad; }
    uint8_t getCpuTemp() const { return cpuTemp; }
    uint8_t getRamLoad() const { return ramLoad; }
    uint8_t getGpuLoad() const { return gpuLoad; }
    uint8_t getGpuTemp() const { return gpuTemp; }
    uint8_t getVramLoad() const { return vramLoad; }
    uint32_t getNetDownSpeed() const { return netDown; }
    uint32_t getNetUpSpeed() const { return netUp; }

    // History for Sparkline / Line Charts
    static const int HISTORY_SIZE = 24;
    const uint8_t* getCpuHistory() const { return cpuHistory; }
    const uint8_t* getGpuHistory() const { return gpuHistory; }
    const uint8_t* getNetDownHistory() const { return netDownHistory; }
    const uint8_t* getNetUpHistory() const { return netUpHistory; }

    uint8_t getDiskCount() const { return diskCount; }
    const DiskInfo* getDisks() const { return disks; }

private:
    uint8_t cpuLoad;
    uint8_t cpuTemp;
    uint8_t ramLoad;
    uint8_t gpuLoad;
    uint8_t gpuTemp;
    uint8_t vramLoad;
    uint32_t netDown;
    uint32_t netUp;

    DiskInfo disks[4];
    uint8_t diskCount;

    uint8_t cpuHistory[HISTORY_SIZE];
    uint8_t gpuHistory[HISTORY_SIZE];
    uint8_t netDownHistory[HISTORY_SIZE];
    uint8_t netUpHistory[HISTORY_SIZE];

    unsigned long lastDataTime;
};

extern PCMonitor pcMonitor;

#endif // PC_MONITOR_H
