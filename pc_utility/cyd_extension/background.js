// Service worker runs in background extension context
console.log("[CYD Extension Background]: Service Worker Active!");

function executeAdSkipInTab() {
    console.log("[CYD Extension Scripting]: Executing Ad Skip in Tab...");
    
    // 1. Click all YouTube Skip Ad buttons
    const skipSelectors = [
        '.ytp-ad-skip-button',
        '.ytp-ad-skip-button-modern',
        '.ytp-skip-ad-button',
        'button.ytp-ad-skip-button-hover',
        '.ytp-ad-skip-button-container button',
        '.ytp-ad-skip-button-slot',
        'button[id^="skip-button"]',
        '.ytp-ad-skip-button-text',
        '.ytp-ad-preview-container'
    ];

    let clicked = false;
    for (const sel of skipSelectors) {
        const btns = document.querySelectorAll(sel);
        btns.forEach(btn => {
            if (btn && btn.offsetParent !== null) {
                console.log("[CYD Extension Scripting]: Clicking Skip Button:", sel);
                btn.click();
                clicked = true;
            }
        });
    }

    // 2. Fast-forward video element if an ad is currently playing
    const isAdPlaying = document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-player-overlay, .ytp-ad-module');
    const video = document.querySelector('video');
    if (video && (isAdPlaying || !clicked)) {
        console.log("[CYD Extension Scripting]: Fast-forwarding Ad video currentTime to end!");
        if (!isNaN(video.duration) && video.duration > 0) {
            video.currentTime = video.duration - 0.05;
        } else {
            video.currentTime = 99999;
        }
    }
}

async function pollCYDServer() {
    try {
        const response = await fetch('http://127.0.0.1:18888/poll', { method: 'GET', cache: 'no-store' });
        if (response.ok) {
            const data = await response.json();
            if (data.skip === true) {
                console.log("[CYD Extension Background]: Received Skip Ad Command from CYD Dashboard!");
                const tabs = await chrome.tabs.query({});
                tabs.forEach(tab => {
                    if (tab.url && tab.url.includes("youtube.com")) {
                        console.log("[CYD Extension Background]: Dynamically executing script in tab:", tab.id, tab.title);
                        chrome.tabs.sendMessage(tab.id, { action: "click_skip" }).catch(() => {});
                        chrome.scripting.executeScript({
                            target: { tabId: tab.id },
                            func: executeAdSkipInTab
                        }).catch(err => console.log("Scripting error:", err));
                    }
                });
            }
        }
    } catch (e) {
        // Python server idle
    }
}

setInterval(pollCYDServer, 250);
