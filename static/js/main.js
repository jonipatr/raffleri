function initApp() {
    const urlTypeVideo = document.getElementById('url-type-video');
    const urlTypeChannel = document.getElementById('url-type-channel');
    const isTestingPage = urlTypeVideo !== null && urlTypeChannel !== null;

    const streamSelectContainer = document.getElementById('stream-selection-container');
    const streamSelect = document.getElementById('stream-select');

    startKeepAlivePing();

    if (isTestingPage) {
        const urlInput = document.getElementById('video-url');
        const urlLabel = document.getElementById('url-label');
        const urlHelpText = document.getElementById('url-help-text');
        const runRaffleBtn = document.getElementById('run-raffle-btn');

        if (!urlInput || !urlLabel || !urlHelpText || !runRaffleBtn || !streamSelectContainer || !streamSelect) {
            return;
        }

        urlTypeVideo.addEventListener('change', () => {
            if (urlTypeVideo.checked) {
                urlLabel.textContent = 'YouTube Live Stream URL';
                urlInput.placeholder = 'https://www.youtube.com/watch?v=...';
                urlHelpText.textContent = 'Enter a URL for an active YouTube live stream';
                streamSelectContainer.classList.add('hidden');
                urlInput.value = '';
            }
        });

        urlTypeChannel.addEventListener('change', () => {
            if (urlTypeChannel.checked) {
                urlLabel.textContent = 'YouTube Channel URL';
                urlInput.placeholder = 'https://www.youtube.com/@channelname';
                urlHelpText.textContent = 'Enter a channel URL to find active live streams';
                streamSelectContainer.classList.add('hidden');
                urlInput.value = '';
            }
        });

        runRaffleBtn.addEventListener('click', async () => {
            const inputUrl = urlInput.value.trim();
            const isChannelUrl = urlTypeChannel.checked;

            if (!inputUrl) {
                showError('Please enter a URL');
                return;
            }

            document.getElementById('results-container').classList.add('hidden');
            document.getElementById('error-container').classList.add('hidden');
            streamSelectContainer.classList.add('hidden');

            try {
                let videoUrl = inputUrl;

                if (isChannelUrl) {
                    showLoadingAnimation();
                    const loadingText = document.getElementById('animation-text');
                    loadingText.textContent = 'Checking for active live streams...';

                    const streamsResponse = await fetch('/api/youtube/channel/streams', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            channel_url: inputUrl
                        })
                    });

                    const streamsData = await streamsResponse.json();
                    updateChannelStats(streamsData.channel);

                    if (!streamsResponse.ok) {
                        throw new Error(streamsData.detail || 'Failed to fetch active streams');
                    }

                    if (streamsData.streams.length === 0) {
                        hideLoadingAnimation();
                        throw new Error('No active live streams found for this channel');
                    }

                    if (streamsData.streams.length > 1) {
                        hideLoadingAnimation();

                        streamSelect.innerHTML = '<option value="">Select a stream...</option>';
                        streamsData.streams.forEach((stream, index) => {
                            const option = document.createElement('option');
                            option.value = stream.video_url;
                            option.textContent = stream.title || `Stream ${index + 1}`;
                            streamSelect.appendChild(option);
                        });

                        streamSelectContainer.classList.remove('hidden');

                        return new Promise((resolve) => {
                            streamSelect.addEventListener('change', async function onStreamSelect() {
                                const selectedUrl = streamSelect.value;
                                if (selectedUrl) {
                                    streamSelect.removeEventListener('change', onStreamSelect);
                                    videoUrl = selectedUrl;
                                    streamSelectContainer.classList.add('hidden');
                                    await runRaffle(videoUrl);
                                    resolve();
                                }
                            });
                        });
                    } else {
                        videoUrl = streamsData.streams[0].video_url;
                    }
                }

                await runRaffle(videoUrl);
            } catch (error) {
                hideLoadingAnimation();
                hideRaffleAnimation();
                if (error.name === 'AbortError') {
                    showError('Request timed out. The stream may have too many messages. Please try with a smaller stream or wait a moment and try again.');
                } else {
                    showError(error.message || 'An error occurred while processing the raffle');
                }
            }
        });

        const startCollectingBtn = document.getElementById('start-collecting-btn');
        if (startCollectingBtn) {
            startCollectingBtn.addEventListener('click', async () => {
                const inputUrl = urlInput.value.trim();
                if (!inputUrl) {
                    showError('Please enter a URL');
                    return;
                }

                try {
                    if (urlTypeChannel.checked) {
                        const streamsResponse = await fetch('/api/youtube/channel/streams', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ channel_url: inputUrl })
                        });
                        const streamsData = await streamsResponse.json();
                        if (!streamsResponse.ok) {
                            throw new Error(streamsData.detail || 'Failed to fetch active streams');
                        }
                        if (!streamsData.streams || streamsData.streams.length === 0) {
                            throw new Error('No active live streams found for this channel');
                        }
                        await setCollectorSession(streamsData.streams[0], 'testing', inputUrl);
                        await startCollector();
                    } else {
                        const lcRes = await fetch('/api/youtube/livechatid', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ video_url: inputUrl })
                        });
                        const lcData = await lcRes.json();
                        if (!lcRes.ok) {
                            throw new Error(lcData.detail || 'Failed to resolve live chat id');
                        }
                        await setCollectorSession({
                            live_chat_id: lcData.live_chat_id,
                            video_id: lcData.video_id,
                            video_url: inputUrl
                        }, 'testing', null);
                        await startCollector();
                    }
                } catch (e) {
                    showError(e.message || 'Failed to start collecting');
                }
            });
        }
    } else {
        const CHANNEL_URL = window.RAFFLERI_CHANNEL_URL;
        if (!CHANNEL_URL) {
            showError('CHANNEL_URL is not configured');
            return;
        }
        const statusText = document.getElementById('main-status-text');
        const startRaffleBtn = document.getElementById('start-raffle-btn');

        if (!streamSelectContainer || !streamSelect || !startRaffleBtn) {
            return;
        }

        startRaffleBtn.disabled = true;
        showStatusInAnimation('Etsitään livelähetystä...');

        (async () => {
            try {
                showLoadingAnimation('Etsitään livelähetystä...');
                const streamsResponse = await fetch('/api/youtube/channel/streams', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        channel_url: CHANNEL_URL
                    })
                });
                const streamsData = await streamsResponse.json();
                updateChannelStats(streamsData.channel);

                if (!streamsResponse.ok) {
                    hideLoadingAnimation();
                    if (statusText) {
                        statusText.textContent = '';
                    }
                    showError(streamsData.detail || 'Failed to fetch active streams');
                    return;
                }

                if (!streamsData.streams || streamsData.streams.length === 0) {
                    // Small delay so the check doesn't look like nothing happened
                    await new Promise((resolve) => setTimeout(resolve, 800));
                    showNotReadyInAnimation();
                    startRaffleBtn.disabled = true;
                    return;
                }

                hideLoadingAnimation();
                showReadyInAnimation();

                let selectedVideoUrl = null;

                if (streamsData.streams.length > 1) {
                    streamSelect.innerHTML = '<option value="">Select a stream...</option>';
                    streamsData.streams.forEach((stream, index) => {
                        const option = document.createElement('option');
                        option.value = stream.video_url;
                        option.textContent = stream.title || `Stream ${index + 1}`;
                        streamSelect.appendChild(option);
                    });

                    streamSelectContainer.classList.remove('hidden');

                    streamSelect.addEventListener('change', async () => {
                        const selectedUrl = streamSelect.value;
                        if (selectedUrl) {
                            selectedVideoUrl = selectedUrl;
                            startRaffleBtn.disabled = false;
                            const stream = streamsData.streams.find((s) => s.video_url === selectedUrl);
                            if (stream) {
                                const lc = await resolveLiveChatId(selectedUrl);
                                await setCollectorSession({
                                    live_chat_id: lc.live_chat_id,
                                    video_id: lc.video_id,
                                    video_url: selectedUrl
                                }, 'main', CHANNEL_URL);
                                await startCollector();
                            }
                        } else {
                            startRaffleBtn.disabled = true;
                            showReadyInAnimation();
                        }
                    });
                } else {
                    selectedVideoUrl = streamsData.streams[0].video_url;
                    startRaffleBtn.disabled = false;
                    showReadyInAnimation();
                    const lc = await resolveLiveChatId(selectedVideoUrl);
                    await setCollectorSession({
                        live_chat_id: lc.live_chat_id,
                        video_id: lc.video_id,
                        video_url: selectedVideoUrl
                    }, 'main', CHANNEL_URL);
                    await startCollector();
                }

                startRaffleBtn.addEventListener('click', async () => {
                    const urlToUse = selectedVideoUrl || streamSelect.value;
                    if (urlToUse) {
                        await runRaffle(urlToUse);
                    }
                });
            } catch (error) {
                hideLoadingAnimation();
                showError(error.message || 'An error occurred while checking for live streams');
                startRaffleBtn.disabled = true;
                showStatusInAnimation('Unable to check live streams right now.');
            }
        })();
    }
}

function startKeepAlivePing() {
    const fiveMinutes = 5 * 60 * 1000;
    setInterval(() => {
        fetch('/health', { method: 'GET', cache: 'no-store' }).catch(() => {});
    }, fiveMinutes);
}

let collectorStatusInterval = null;

async function setCollectorSession(stream, origin, channelUrl) {
    try {
        const res = await fetch('/api/collector/set_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                live_chat_id: stream.live_chat_id,
                video_id: stream.video_id,
                video_url: stream.video_url,
                origin: origin,
                channel_url: channelUrl || null
            })
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || 'Failed to set collector session');
        }
    } catch (_) {}
}

async function startCollector() {
    try {
        const res = await fetch('/api/collector/start', { method: 'POST' });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.detail || 'Failed to start collector');
        }
        startCollectorStatusPolling();
    } catch (e) {
        showError(e.message || 'Failed to start collecting');
        // Still poll status: server may have auto-started or may report last_error
        startCollectorStatusPolling();
    }
}

async function resolveLiveChatId(videoUrl) {
    const res = await fetch('/api/youtube/livechatid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_url: videoUrl })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.detail || 'Failed to resolve live chat id');
    }
    return data;
}

async function stopCollector() {
    try {
        await fetch('/api/collector/stop', { method: 'POST' });
    } catch (_) {}
    stopCollectorStatusPolling();
    setCollectorUI({ collecting: false, total_comments: 0 });
}

function startCollectorStatusPolling() {
    stopCollectorStatusPolling();
    collectorStatusInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/collector/status', { cache: 'no-store' });
            if (!res.ok) return;
            const status = await res.json();
            setCollectorUI(status);
        } catch (_) {}
    }, 2000);
}

function stopCollectorStatusPolling() {
    if (collectorStatusInterval) {
        clearInterval(collectorStatusInterval);
        collectorStatusInterval = null;
    }
}

function setCollectorUI(status) {
    const container = document.getElementById('collector-status');
    const countEl = document.getElementById('collector-comment-count');
    const statusTextEl = document.getElementById('collector-status-text');
    if (!container || !countEl) return;

    const hasError = status && status.last_error;
    if (status && (status.collecting || hasError)) {
        container.classList.remove('hidden');
        countEl.textContent = status.total_comments ?? 0;
        if (statusTextEl) {
            statusTextEl.textContent = hasError ? `TEMP: Collector error: ${status.last_error}` : 'Live käynnissä! Kerätään kommentteja...';
        }
    } else {
        container.classList.add('hidden');
    }
}

function safeInitApp() {
    if (window.__raffleriInitRan) {
        return;
    }
    window.__raffleriInitRan = true;
    initApp();
}

window.addEventListener('error', (event) => {
    const statusText = document.getElementById('main-status-text');
    if (statusText) {
        statusText.textContent = `Error: ${event.message}`;
    }
});

// Stop background collector + UI polling when navigating away / refreshing.
// Main page will auto-start again on load.
window.addEventListener('pagehide', () => {
    try {
        stopCollectorStatusPolling();
    } catch (_) {}
    try {
        fetch('/api/collector/stop', { method: 'POST', keepalive: true }).catch(() => {});
    } catch (_) {}
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', safeInitApp);
    // Fallback in case DOMContentLoaded already fired before listener attached
    setTimeout(safeInitApp, 0);
} else {
    safeInitApp();
}

let pendingWinnerData = null;
let awaitingReveal = false;

async function runRaffle(videoUrl) {
    try {
        // Show loading animation while fetching
        showLoadingAnimation();
        
        // Add timeout to prevent hanging (60 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);
        
        const response = await fetch('/api/youtube/entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_url: videoUrl,
                winners: 1
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'An error occurred');
        }

        // Show a short preparation countdown before allowing reveal
        await showPreparationCountdown(3);
        hideLoadingAnimation();
        pendingWinnerData = data;
        awaitingReveal = true;
        const startRaffleBtn = document.getElementById('start-raffle-btn');
        const runRaffleBtn = document.getElementById('run-raffle-btn');
        if (startRaffleBtn) {
            startRaffleBtn.disabled = true;
        }
        if (runRaffleBtn) {
            runRaffleBtn.disabled = true;
        }
        showRaffleAnimation();
        
    } catch (error) {
        hideLoadingAnimation();
        hideRaffleAnimation();
        if (error.name === 'AbortError') {
            showError('Request timed out. The stream may have too many messages. Please try with a smaller stream or wait a moment and try again.');
        } else {
            showError(error.message || 'An error occurred while processing the raffle');
        }
    }
}

async function showPreparationCountdown(seconds) {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    const raffleImg = document.getElementById('raffle-spin-img');

    if (!container || !text || !spinner) {
        return;
    }

    container.classList.remove('hidden');
    if (raffleImg) {
        raffleImg.classList.add('hidden');
        raffleImg.classList.remove('raffle-spinning');
    }

    spinner.classList.remove('hidden');
    // Use the existing spinning animation during countdown
    spinner.classList.add('spinning');
    spinner.classList.remove('pulsing');
    spinner.style.borderColor = '#f97316';
    spinner.style.borderTopColor = 'transparent';

    // Prevent reveal click during countdown
    awaitingReveal = false;

    for (let i = seconds; i > 0; i--) {
        text.textContent = `Valmistellaan arvontaa... ${i}`;
        text.classList.add('countdown-animation');
        await new Promise((resolve) => setTimeout(resolve, 900));
        text.classList.remove('countdown-animation');
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    text.textContent = 'Valmistellaan arvontaa...';
}

function showLoadingAnimation(message) {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    const readyImg = document.getElementById('ready-to-raffle-img');
    const notReadyImg = document.getElementById('not-ready-img');
    const raffleImg = document.getElementById('raffle-spin-img');
    
    container.classList.remove('hidden');
    spinner.classList.remove('hidden');
    spinner.classList.add('spinning');
    spinner.style.borderColor = '#f97316';
    spinner.style.borderTopColor = 'transparent';
    if (readyImg) {
        readyImg.classList.add('hidden');
    }
    if (notReadyImg) {
        notReadyImg.classList.add('hidden');
    }
    if (raffleImg) {
        raffleImg.classList.add('hidden');
        raffleImg.classList.remove('raffle-spinning');
    }
    if (text) {
        text.classList.remove('hidden');
    }
    text.textContent = message || 'Haetaan kommentteja...';
}

function hideLoadingAnimation() {
    const spinner = document.getElementById('spinner');
    // Don't hide spinner, just change animation - it will be used for raffle animation
    spinner.classList.remove('spinning');
}

function showStatusInAnimation(message) {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    const readyImg = document.getElementById('ready-to-raffle-img');
    const notReadyImg = document.getElementById('not-ready-img');
    const raffleImg = document.getElementById('raffle-spin-img');

    container.classList.remove('hidden');
    spinner.classList.add('hidden');
    spinner.classList.remove('spinning');
    if (readyImg) {
        readyImg.classList.add('hidden');
    }
    if (notReadyImg) {
        notReadyImg.classList.add('hidden');
    }
    if (raffleImg) {
        raffleImg.classList.add('hidden');
        raffleImg.classList.remove('raffle-spinning');
    }
    if (text) {
        text.classList.remove('hidden');
    }
    text.textContent = message;
}

function showReadyInAnimation() {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    const readyImg = document.getElementById('ready-to-raffle-img');
    const notReadyImg = document.getElementById('not-ready-img');
    const raffleImg = document.getElementById('raffle-spin-img');

    container.classList.remove('hidden');
    spinner.classList.add('hidden');
    spinner.classList.remove('spinning');
    if (text) {
        text.textContent = '';
        text.classList.add('hidden');
    }
    if (readyImg) {
        readyImg.classList.remove('hidden');
    }
    if (notReadyImg) {
        notReadyImg.classList.add('hidden');
    }
    if (raffleImg) {
        raffleImg.classList.add('hidden');
        raffleImg.classList.remove('raffle-spinning');
    }
}

function showNotReadyInAnimation() {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    const readyImg = document.getElementById('ready-to-raffle-img');
    const notReadyImg = document.getElementById('not-ready-img');
    const raffleImg = document.getElementById('raffle-spin-img');

    container.classList.remove('hidden');
    spinner.classList.add('hidden');
    spinner.classList.remove('spinning');
    if (text) {
        text.textContent = 'Livestreamiä ei löytynyt';
        text.classList.remove('hidden');
    }
    if (readyImg) {
        readyImg.classList.add('hidden');
    }
    if (notReadyImg) {
        notReadyImg.classList.remove('hidden');
    }
    if (raffleImg) {
        raffleImg.classList.add('hidden');
        raffleImg.classList.remove('raffle-spinning');
    }
}

function showRaffleAnimation() {
    const text = document.getElementById('animation-text');
    const spinner = document.getElementById('spinner');
    const readyImg = document.getElementById('ready-to-raffle-img');
    const notReadyImg = document.getElementById('not-ready-img');
    const raffleImg = document.getElementById('raffle-spin-img');
    
    // Make sure spinner is visible and change to raffle animation
    spinner.classList.add('hidden');
    spinner.classList.remove('spinning');
    spinner.classList.remove('pulsing');
    if (readyImg) {
        readyImg.classList.add('hidden');
    }
    if (notReadyImg) {
        notReadyImg.classList.add('hidden');
    }
    if (text) {
        text.classList.remove('hidden');
        text.textContent = 'Klikkaa paljastaaksesi voittaja!';
    }
    if (raffleImg) {
        raffleImg.classList.remove('hidden');
        raffleImg.classList.add('raffle-spinning');
        raffleImg.style.animationDuration = '1.2s';
        startRaffleSpinCycle(raffleImg);
    }
}

function hideRaffleAnimation() {
    document.getElementById('animation-container').classList.add('hidden');
    const spinner = document.getElementById('spinner');
    const raffleImg = document.getElementById('raffle-spin-img');
    spinner.classList.remove('pulsing');
    if (raffleImg) {
        raffleImg.classList.add('hidden');
        raffleImg.classList.remove('raffle-spinning');
    }
    if (window.__raffleSpinInterval) {
        clearInterval(window.__raffleSpinInterval);
        window.__raffleSpinInterval = null;
    }
    if (window.__raffleSpinRaf) {
        cancelAnimationFrame(window.__raffleSpinRaf);
        window.__raffleSpinRaf = null;
    }
}

function startRaffleSpinCycle(raffleImg) {
    if (window.__raffleSpinInterval) {
        clearInterval(window.__raffleSpinInterval);
        window.__raffleSpinInterval = null;
    }
    if (window.__raffleSpinRaf) {
        cancelAnimationFrame(window.__raffleSpinRaf);
        window.__raffleSpinRaf = null;
    }

    const minDuration = 0.6;  // fastest (slower than before)
    const maxDuration = 1.9;  // slowest
    const range = maxDuration - minDuration;
    const cycleMs = 4200;
    const start = performance.now();

    const tick = (now) => {
        const elapsed = now - start;
        const phase = (elapsed % cycleMs) / cycleMs; // 0..1
        const smoothstep = (t) => t * t * (3 - 2 * t);

        let duration;
        if (phase < 0.15) {
            // accelerate to fast
            const t = smoothstep(phase / 0.15);
            duration = maxDuration - range * t;
        } else if (phase < 0.55) {
            // hold fast
            duration = minDuration;
        } else if (phase < 0.7) {
            // decelerate to slow
            const t = smoothstep((phase - 0.55) / 0.15);
            duration = minDuration + range * t;
        } else {
            // hold slow
            duration = maxDuration;
        }
        raffleImg.style.animationDuration = `${duration.toFixed(2)}s`;
        window.__raffleSpinRaf = requestAnimationFrame(tick);
    };

    window.__raffleSpinRaf = requestAnimationFrame(tick);
}

document.addEventListener('DOMContentLoaded', () => {
    const animationContainer = document.getElementById('animation-container');
    if (!animationContainer) {
        return;
    }
    animationContainer.addEventListener('click', () => {
        if (!awaitingReveal || !pendingWinnerData) {
            return;
        }
        awaitingReveal = false;
        hideRaffleAnimation();
        showResults(pendingWinnerData);
        pendingWinnerData = null;
        const startRaffleBtn = document.getElementById('start-raffle-btn');
        const runRaffleBtn = document.getElementById('run-raffle-btn');
        if (startRaffleBtn) {
            startRaffleBtn.disabled = false;
        }
        if (runRaffleBtn) {
            runRaffleBtn.disabled = false;
        }
    });
});

function showResults(data) {
    const container = document.getElementById('results-container');
    const winnerUsername = document.getElementById('winner-username');
    const winnerCommentText = document.getElementById('winner-comment-text');
    const winnerCommentDiv = document.getElementById('winner-comment');
    const totalEntries = document.getElementById('total-entries');
    const totalParticipants = document.getElementById('total-participants');
    
    winnerUsername.textContent = data.winner.username;
    totalEntries.textContent = data.total_comments;
    totalParticipants.textContent = data.total_participants;
    
    // Show comment text if available
    if (data.winner.comment_text) {
        winnerCommentText.textContent = data.winner.comment_text;
        winnerCommentDiv.classList.remove('hidden');
    } else {
        winnerCommentDiv.classList.add('hidden');
    }
    
    container.classList.remove('hidden');
    
    // Add reveal animation
    const winnerDisplay = document.getElementById('winner-display');
    winnerDisplay.classList.add('winner-reveal');
    setTimeout(() => {
        winnerDisplay.classList.remove('winner-reveal');
    }, 1500);
}

function showError(message) {
    const container = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    container.classList.remove('hidden');
}

function updateChannelStats(channel) {
    const statsContainer = document.getElementById('channel-stats');
    if (!statsContainer) {
        return;
    }

    if (!channel) {
        statsContainer.classList.add('hidden');
        return;
    }

    const title = document.getElementById('channel-title');
    const subscribers = document.getElementById('channel-subscribers');
    const podcasts = document.getElementById('channel-podcasts');
    const podcastsBlock = document.getElementById('channel-podcasts-block');

    const formatNumber = (value) => {
        if (value === null || value === undefined) {
            return '-';
        }
        return Number(value).toLocaleString('fi-FI');
    };

    if (title) {
        title.textContent = channel.title || 'Channel';
    }
    if (subscribers) {
        subscribers.textContent = formatNumber(channel.subscriber_count);
    }
    if (podcasts) {
        podcasts.textContent = formatNumber(channel.podcast_count);
    }

    const hasPodcasts = Array.isArray(channel.podcasts) && channel.podcasts.length > 0;
    if (podcastsBlock) {
        podcastsBlock.classList.toggle('hidden', !hasPodcasts);
    }

    statsContainer.classList.remove('hidden');
}
