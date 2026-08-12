// CYD Smart Desk Dashboard - Background YouTube Ad Skipper Content Script
(function() {
    console.log("[CYD Extension]: YouTube Background Ad Skipper Active!");

    function trySkipAd() {
        const skipBtnSelectors = [
            '.ytp-ad-skip-button',
            '.ytp-ad-skip-button-modern',
            '.ytp-skip-ad-button',
            'button.ytp-ad-skip-button-hover',
            '.ytp-ad-skip-button-container button'
        ];
        
        let skipped = false;
        for (const selector of skipBtnSelectors) {
            const btn = document.querySelector(selector);
            if (btn && btn.offsetParent !== null) {
                console.log("[CYD Extension]: Clicking Skip Ad Button:", selector);
                btn.click();
                skipped = true;
                break;
            }
        }

        const adPlayerOverlay = document.querySelector('.ytp-ad-player-overlay, .ytp-ad-text');
        const video = document.querySelector('video');
        if (!skipped && adPlayerOverlay && video && !isNaN(video.duration) && video.duration > 0) {
            console.log("[CYD Extension]: Fast-forwarding Unskippable Ad to completion...");
            video.currentTime = video.duration - 0.1;
            skipped = true;
        }
        return skipped;
    }

    async function pollCYDServer() {
        try {
            const response = await fetch('http://127.0.0.1:18888/poll', { method: 'GET', cache: 'no-store' });
            if (response.ok) {
                const data = await response.json();
                if (data.skip === true) {
                    console.log("[CYD Extension]: Received Skip Ad Command from CYD Dashboard!");
                    trySkipAd();
                }
            }
        } catch (e) {
            // Python server idle or offline
        }
    }

    setInterval(pollCYDServer, 350);
})();
