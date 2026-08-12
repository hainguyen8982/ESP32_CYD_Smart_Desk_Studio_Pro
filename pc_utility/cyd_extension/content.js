// Content script injected into YouTube tabs
console.log("[CYD Extension Content]: YouTube Background Ad Skipper Loaded!");

function executeAdSkip() {
    console.log("[CYD Extension Content]: Executing Ad Skip...");
    
    // 1. All modern YouTube Skip Ad button CSS selectors
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
            if (btn) {
                console.log("[CYD Extension Content]: Clicking Skip Button:", sel);
                btn.click();
                clicked = true;
            }
        });
    }

    // 2. Fast-forward video element if an ad is currently playing
    const isAdPlaying = document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-player-overlay, .ytp-ad-module');
    const video = document.querySelector('video');
    if (video && (isAdPlaying || !clicked)) {
        console.log("[CYD Extension Content]: Fast-forwarding Ad video currentTime to end!");
        if (!isNaN(video.duration) && video.duration > 0) {
            video.currentTime = video.duration - 0.05;
        } else {
            video.currentTime = 99999;
        }
    }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "click_skip") {
        console.log("[CYD Extension Content]: Received click_skip command from background!");
        executeAdSkip();
    }
});
