document.addEventListener('DOMContentLoaded', function() {
    const progressContainer = document.getElementById('progress-container');
    
    if (progressContainer) {
        startProgressChecking();
    }

    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
            } else {
                const downloadBtn = document.querySelector('.download-btn');
                if (downloadBtn) {
                    downloadBtn.innerHTML = '<span class="loading"></span> Starting Download...';
                    downloadBtn.disabled = true;
                }
            }
        });
    }
});

function startProgressChecking() {
    const progressFill = document.getElementById('progress-fill');
    const percentageEl = document.getElementById('percentage');
    const speedEl = document.getElementById('speed');
    const etaEl = document.getElementById('eta');
    const statusTitle = document.getElementById('status-title');
    const errorMessage = document.getElementById('error-message');
    const completedActions = document.getElementById('completed-actions');
    const openBtn = document.getElementById('open-btn');
    const downloadBtn = document.getElementById('download-btn');
    const videoTitleEl = document.getElementById('video-title');
    const backToHomeBtn = document.getElementById('back-to-home-btn');

    let isCompleted = false;

    function checkProgress() {
        if (isCompleted) return;

        fetch('/progress')
            .then(response => response.json())
            .then(data => {
                const percentage = Math.round(data.percentage || 0);
                progressFill.style.width = `${percentage}%`;
                percentageEl.textContent = `${percentage}%`;
                
                speedEl.textContent = data.speed ? `Speed: ${data.speed}` : 'Speed: -';
                etaEl.textContent = data.eta ? `ETA: ${data.eta}` : 'ETA: -';
                
                if (data.title && videoTitleEl) {
                    videoTitleEl.textContent = data.title;
                    videoTitleEl.style.display = 'block';
                }
                
                if (data.status === 'completed') {
                    isCompleted = true;
                    statusTitle.textContent = 'Download Complete!';
                    statusTitle.style.color = '#34a853';
                    statusTitle.className = 'status-completed';
                    
                    document.querySelector('.progress-info').style.display = 'none';
                    completedActions.style.display = 'block';
                    
                    if (data.filename) {
                        // Automatically trigger browser download
                        window.location.href = `/download_file/${encodeURIComponent(data.filename)}`;
                        
                        openBtn.href = `/open_file/${encodeURIComponent(data.filename)}`;
                        openBtn.style.display = 'inline-block';
                        openBtn.onclick = function(e) {
                            e.preventDefault();
                            window.open(this.href, '_blank');
                        };
                    }
                    
                    if (backToHomeBtn) {
                        backToHomeBtn.onclick = function(e) {
                            e.preventDefault();
                            window.location.href = '/';
                        };
                    }
                    
                } else if (data.status === 'failed') {
                    isCompleted = true;
                    statusTitle.textContent = 'Download Failed';
                    statusTitle.style.color = '#ea4335';
                    statusTitle.className = 'status-failed';
                    
                    document.querySelector('.progress-info').style.display = 'none';
                    errorMessage.textContent = data.error || 'Download failed. Please try again.';
                    errorMessage.style.display = 'block';
                    
                    const backToHomeContainer = document.createElement('div');
                    backToHomeContainer.className = 'action-buttons';
                    backToHomeContainer.innerHTML = `
                        <a href="/" class="action-btn secondary">
                            <span class="icon">🏠</span>
                            <span>Back to Home</span>
                        </a>
                    `;
                    completedActions.appendChild(backToHomeContainer);
                    completedActions.style.display = 'block';
                    
                } else if (data.status === 'downloading') {
                    statusTitle.textContent = 'Downloading Video...';
                    statusTitle.style.color = '#4285f4';
                    statusTitle.className = 'status-downloading';
                    setTimeout(checkProgress, 1000);
                } else {
                    statusTitle.textContent = 'Initializing Download...';
                    statusTitle.style.color = '#4285f4';
                    statusTitle.className = 'status-downloading';
                    setTimeout(checkProgress, 1000);
                }
            })
            .catch(error => {
                console.error('Error fetching progress:', error);
                errorMessage.textContent = 'Error fetching progress. Please try again.';
                errorMessage.style.display = 'block';
                setTimeout(checkProgress, 3000);
            });
    }

    checkProgress();
}

function validateForm() {
    const urlInput = document.querySelector('input[name="video_url"]');
    const url = urlInput.value.trim();
    
    if (!url) {
        alert('Please enter a video URL');
        return false;
    }
    
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    if (!youtubeRegex.test(url)) {
        alert('Please enter a valid YouTube URL');
        return false;
    }
    
    return true;
}