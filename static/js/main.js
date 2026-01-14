// Platform selection
let selectedPlatform = 'youtube';

document.querySelectorAll('.platform-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const platform = btn.dataset.platform;
        if (platform === 'youtube') {
            selectedPlatform = 'youtube';
            document.getElementById('platform-youtube').classList.add('bg-red-600', 'hover:bg-red-700');
            document.getElementById('platform-youtube').classList.remove('bg-gray-400');
        }
    });
});

// Run raffle button
document.getElementById('run-raffle-btn').addEventListener('click', async () => {
    const videoUrl = document.getElementById('video-url').value.trim();
    
    if (!videoUrl) {
        showError('Please enter a video URL');
        return;
    }
    
    // Hide previous results and errors
    document.getElementById('results-container').classList.add('hidden');
    document.getElementById('error-container').classList.add('hidden');
    
    // Show animation
    showAnimation();
    
    try {
        let endpoint;
        if (selectedPlatform === 'youtube') {
            endpoint = '/api/youtube/entries';
        } else {
            endpoint = '/api/tiktok/entries';
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_url: videoUrl,
                winners: 1
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'An error occurred');
        }
        
        // Wait for animation to complete (2-3 seconds)
        await new Promise(resolve => setTimeout(resolve, 2500));
        
        // Hide animation and show results
        hideAnimation();
        showResults(data);
        
    } catch (error) {
        hideAnimation();
        showError(error.message);
    }
});

function showAnimation() {
    const container = document.getElementById('animation-container');
    const text = document.getElementById('animation-text');
    
    container.classList.remove('hidden');
    
    // Countdown effect
    let countdown = 3;
    const countdownInterval = setInterval(() => {
        if (countdown > 0) {
            text.textContent = `Drawing winner... ${countdown}`;
            text.classList.add('countdown-animation');
            setTimeout(() => {
                text.classList.remove('countdown-animation');
            }, 500);
            countdown--;
        } else {
            clearInterval(countdownInterval);
            text.textContent = 'Selecting winner...';
        }
    }, 800);
}

function hideAnimation() {
    document.getElementById('animation-container').classList.add('hidden');
}

function showResults(data) {
    const container = document.getElementById('results-container');
    const winnerUsername = document.getElementById('winner-username');
    const winnerEntries = document.getElementById('winner-entries');
    const totalEntries = document.getElementById('total-entries');
    const totalParticipants = document.getElementById('total-participants');
    
    winnerUsername.textContent = data.winner.username;
    winnerEntries.textContent = data.winner.entries;
    totalEntries.textContent = data.total_entries;
    totalParticipants.textContent = data.total_participants;
    
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
