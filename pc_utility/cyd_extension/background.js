// Service worker runs in background extension context (bypasses Mixed Content Security restrictions)
console.log("[CYD Extension Background]: Service Worker Active!");

async function pollCYDServer() {
    try {
        const response = await fetch('http://127.0.0.1:18888/poll', { method: 'GET', cache: 'no-store' });
        if (response.ok) {
            const data = await response.json();
            if (data.skip === true) {
                console.log("[CYD Extension Background]: Received Skip Ad Command from CYD Dashboard!");
                const tabs = await chrome.tabs.query({ url: "https://www.youtube.com/*" });
                tabs.forEach(tab => {
                    chrome.tabs.sendMessage(tab.id, { action: "click_skip" }).catch(() => {});
                });
            }
        }
    } catch (e) {
        // Python server idle
    }
}

setInterval(pollCYDServer, 350);
