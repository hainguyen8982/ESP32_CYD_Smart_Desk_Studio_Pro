// Content script injected into YouTube tabs
console.log("[CYD Extension Content]: YouTube Background Ad Skipper Active!");

function trySkipAd() {
    const skipBtnSelectors = [
        '.ytp-ad-skip-button',
        '.ytp-ad-skip-button-modern',
        '.ytp-skip-ad-button',
        'button.ytp-ad-skip-button-hover',
        '.ytp-ad-skip-button-container button',
        '.ytp-ad-skip-button-slot'
    ];
    
    let skipped = false;
    for (const selector of skipBtnSelectors) {
        const btn = document.querySelector(selector);
        if (btn && btn.offsetParent !== null) {
            console.log("[CYD Extension Content]: Clicking Skip Ad Button:", selector);
            btn.click();
            skipped = true;
            break;
        }
    }

    const adPlayerOverlay = document.querySelector('.ytp-ad-player-overlay, .ytp-ad-text');
    const video = document.querySelector('video');
    if (!skipped && adPlayerOverlay && video && !isNaN(video.duration) && video.duration > 0) {
        console.log("[CYD Extension Content]: Fast-forwarding Unskippable Ad to completion...");
        video.currentTime = video.duration - 0.1;
        skipped = true;
    }
    return skipped;
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "click_skip") {
        console.log("[CYD Extension Content]: Triggering Skip Ad DOM Action!");
        trySkipAd();
    }
});
