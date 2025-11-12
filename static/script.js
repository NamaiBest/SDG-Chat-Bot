const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const welcomeScreen = document.getElementById('welcome-screen');
const chatInterface = document.getElementById('chat-interface');
const usernameInput = document.getElementById('username');
const startChatBtn = document.getElementById('start-chat');
const userDisplayName = document.getElementById('user-display-name');
const modeToggle = document.getElementById('mode-toggle');
const mainTitle = document.getElementById('main-title');
const mainSubtitle = document.getElementById('main-subtitle');
const backToMainBtn = document.getElementById('back-to-main');

// Input elements
const sustainabilityInput = document.getElementById('sustainability-input');
const assistantInput = document.getElementById('assistant-input');
const assistantUsernameInput = document.getElementById('assistant-username');
const startAssistantChatBtn = document.getElementById('start-assistant-chat');

// Debug: Check if elements are found
console.log('DOM elements check:');
console.log('usernameInput:', usernameInput);
console.log('startChatBtn:', startChatBtn);
console.log('userDisplayName:', userDisplayName);

// Media elements
const toggleCameraBtn = document.getElementById('toggle-camera');
const recordVideoBtn = document.getElementById('record-video');
const captureImageBtn = document.getElementById('capture-image');
const startRecordingBtn = document.getElementById('start-recording');
const stopRecordingBtn = document.getElementById('stop-recording');
const clearMediaBtn = document.getElementById('clear-media');
const fileUploadInput = document.getElementById('file-upload');
const micBtn = document.getElementById('mic-btn');

const cameraVideo = document.getElementById('camera-video');
const cameraCanvas = document.getElementById('camera-canvas');
const cameraContainer = document.getElementById('camera-container');
const mediaPreviewContainer = document.getElementById('media-preview-container');
const previewImage = document.getElementById('preview-image');
const previewVideo = document.getElementById('preview-video');
const mediaNote = document.getElementById('media-note');
const videoContextWrap = document.getElementById('video-context-wrap');
const videoContextInput = document.getElementById('video-context');
const clearVideoBtn = document.getElementById('clear-video');
const smallVideoPreview = document.getElementById('small-video-preview');
const recordingStatus = document.getElementById('recording-status');
const recordingTimer = document.getElementById('recording-timer');

// New camera overlay elements
const cameraOverlay = document.getElementById('camera-overlay');
const overlayCameraVideo = document.getElementById('overlay-camera-video');
const captureConfirmBtn = document.getElementById('capture-confirm');
const cameraCancelBtn = document.getElementById('camera-cancel');
const mediaPreviewCorner = document.getElementById('media-preview-corner');
const removeCornerMediaBtn = document.getElementById('remove-corner-media');

let currentUsername = '';
let sessionId = localStorage.getItem('sdg_session_id') || generateSessionId();
let cameraStream = null;
let isCameraOn = false;

// Mode state
let isPersonalAssistantMode = true; // Default to Personal Assistant mode
// Environment memory now handled by backend detailed memory system
let isRecording = false;
let mediaRecorder = null;
let recordedChunks = [];
let currentMediaData = null;
let currentMediaType = null;
let recordingStartTime = null;
let recordingInterval = null;

// Audio recording variables
let isAudioRecording = false;
let audioMediaRecorder = null;
let audioRecordedChunks = [];
let audioStream = null;

function generateSessionId() {
    const id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('sdg_session_id', id);
    return id;
}

// Media Functions
async function toggleCamera() {
    try {
        console.log('Opening camera overlay for photo...');
        console.log('User agent:', navigator.userAgent);
        console.log('Is HTTPS:', location.protocol === 'https:');
        console.log('Is localhost:', location.hostname === 'localhost' || location.hostname === '127.0.0.1');
        
        // Check if getUserMedia is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('getUserMedia is not supported in this browser');
        }
        
        // Get camera stream
            cameraStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 }, 
                height: { ideal: 480 },
                facingMode: 'user'
            },
                audio: false
        });
        
        // Show camera overlay
        overlayCameraVideo.srcObject = cameraStream;
        cameraOverlay.style.display = 'flex';
        
        // Set up for photo mode
        updateOverlayForPhotoMode();
        
        // Blur the background
        document.body.classList.add('chat-blurred');
        
        isCameraOn = true;
        
    } catch (error) {
        console.error('Camera error:', error);
        alert('Camera access denied or not available. Please check your browser permissions and try again.');
    }
}

// Function to close camera overlay
function closeCameraOverlay() {
    console.log('Closing camera overlay...');
    
    // Stop any ongoing recording
    if (isRecording && mediaRecorder && mediaRecorder.state === 'recording') {
        console.log('Stopping recording before closing...');
        mediaRecorder.stop();
        isRecording = false;
    }
    
    // Hide overlay
    cameraOverlay.style.display = 'none';
    document.body.classList.remove('chat-blurred');
    
    // Stop camera stream
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => {
            console.log('Stopping track:', track.kind);
            track.stop();
        });
        cameraStream = null;
    }
    
    // Clear recording timer
    if (recordingInterval) {
        clearInterval(recordingInterval);
        recordingInterval = null;
    }
    
    // Reset overlay controls
    resetOverlayControls();
    
    // Reset states
    isCameraOn = false;
    isRecording = false;
    recordingStartTime = null;
    
    console.log('Camera overlay closed successfully');
}

// New function to capture from overlay
function captureFromOverlay() {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = overlayCameraVideo.videoWidth;
    canvas.height = overlayCameraVideo.videoHeight;
    
    context.drawImage(overlayCameraVideo, 0, 0);
    
    canvas.toBlob((blob) => {
        const reader = new FileReader();
        reader.onload = function() {
            currentMediaData = reader.result;
            currentMediaType = 'image';
            
            // Show in corner preview
            showCornerPreview(reader.result, 'image');
            
            // Close overlay
            closeCameraOverlay();
        };
        reader.readAsDataURL(blob);
    }, 'image/jpeg', 0.9);
}

// Show media preview in corner
function showCornerPreview(data, type) {
    console.log('Showing corner preview for:', type);
    
    if (type === 'image') {
        mediaPreviewCorner.innerHTML = `
            <img src="${data}" alt="Captured image" style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">
            <button class="remove-btn" onclick="removeCornerMedia()">×</button>
        `;
    } else if (type === 'video') {
        mediaPreviewCorner.innerHTML = `
            <video src="${data}" muted autoplay loop style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;"></video>
            <button class="remove-btn" onclick="removeCornerMedia()">×</button>
        `;
    }
    
    mediaPreviewCorner.style.display = 'block';
    console.log('Corner preview displayed successfully');
}

// Remove corner media preview
function removeCornerMedia() {
    mediaPreviewCorner.style.display = 'none';
    currentMediaData = null;
    currentMediaType = null;
    // Hide video context area and tag if present
    if (videoContextWrap) {
        videoContextWrap.style.display = 'none';
        const tag = document.getElementById('video-saved-tag');
        if (tag) tag.style.display = 'none';
    }
    if (smallVideoPreview) {
        smallVideoPreview.src = '';
    }
    if (videoContextInput) {
        videoContextInput.value = '';
    }
}



async function recordVideo() {
    try {
        console.log('Opening camera for video recording...');
        
        // Get camera stream for video recording
            const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 }, 
                height: { ideal: 480 },
                facingMode: 'user'
            },
                audio: true
        });
        
        // Show camera preview with start recording option
        showCameraPreview(stream);
        
    } catch (error) {
        console.error('Camera error:', error);
        alert('Camera access error: ' + error.message);
    }
}

// Show camera preview with start recording button
function showCameraPreview(stream) {
    // Create camera preview overlay
    const previewOverlay = document.createElement('div');
    previewOverlay.id = 'camera-preview-overlay';
    previewOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
    `;
    
    previewOverlay.innerHTML = `
        <div style="text-align: center;">
            <video id="camera-preview" autoplay muted playsinline style="
                width: 480px;
                height: 360px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            "></video>
            <div style="display: flex; gap: 20px; align-items: center; justify-content: center;">
                <button id="start-recording-btn" style="
                    background: #ff4444;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 25px;
                    font-size: 1.1em;
                    cursor: pointer;
                    font-weight: bold;
                    box-shadow: 0 4px 12px rgba(255, 68, 68, 0.3);
                ">🔴 Start Recording</button>
                <button id="cancel-camera-btn" style="
                    background: #666;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 25px;
                    font-size: 1.1em;
                    cursor: pointer;
                    font-weight: bold;
                ">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(previewOverlay);
    
    // Set up video preview
    const videoPreview = document.getElementById('camera-preview');
    videoPreview.srcObject = stream;
    
    // Start recording button
    document.getElementById('start-recording-btn').onclick = () => {
        document.body.removeChild(previewOverlay);
        startVideoRecording(stream);
    };
    
    // Cancel button
    document.getElementById('cancel-camera-btn').onclick = () => {
        // Stop camera stream
        stream.getTracks().forEach(track => track.stop());
        document.body.removeChild(previewOverlay);
    };
}

// Start the actual video recording
function startVideoRecording(stream) {
    // Create MediaRecorder
    const mediaRecorder = new MediaRecorder(stream);
    const recordedChunks = [];
    let recordedVideoData = null;
    
    // Set up recording event handlers
    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            recordedChunks.push(event.data);
        }
    };
    
    mediaRecorder.onstop = () => {
        // Process video but don't send yet
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        const reader = new FileReader();
        reader.onload = function() {
            recordedVideoData = reader.result;
            console.log('Video processed, waiting for user choice');
        };
        reader.readAsDataURL(blob);
    };
    
    // Start recording
    mediaRecorder.start();
    console.log('Recording started');
    
    // Show recording UI
    showRecordingUI(mediaRecorder, stream, () => recordedVideoData);
}

// Show options after recording is complete
function showRecordingCompleted(overlay, stream) {
    // Clear countdown timer if it exists
    if (overlay.countdownInterval) {
        clearInterval(overlay.countdownInterval);
    }
    
    const container = overlay.querySelector('div');
    
    // Replace only the recording status and button, keep the video preview
    const videoElement = container.querySelector('#recording-preview');
    container.innerHTML = `
        <div style="text-align: center;">
            ${videoElement.outerHTML}
            <div style="font-size: 1.3em; margin-bottom: 20px; color: #4CAF50;">
                ✅ Recording Complete!
            </div>
            <div style="display: flex; gap: 15px; align-items: center; justify-content: center;">
                <button id="send-video-btn" style="
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 25px;
                    font-size: 1em;
                    cursor: pointer;
                    font-weight: bold;
                    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
                ">📤 Send Video</button>
                <button id="rerecord-btn" style="
                    background: #ff4444;
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 25px;
                    font-size: 1em;
                    cursor: pointer;
                    font-weight: bold;
                    box-shadow: 0 4px 12px rgba(255, 68, 68, 0.3);
                ">🔄 Re-record</button>
                <button id="cancel-video-btn" style="
                    background: #666;
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 25px;
                    font-size: 1em;
                    cursor: pointer;
                    font-weight: bold;
                ">❌ Cancel</button>
            </div>
        </div>
    `;
    
    // Reconnect the video stream to the new element
    const newVideoElement = container.querySelector('#recording-preview');
    newVideoElement.srcObject = stream;
    
    // Wait a moment for video processing to complete
    setTimeout(() => {
        // Send video button - store video and show only context input
        document.getElementById('send-video-btn').onclick = () => {
            const getVideoData = window.currentRecordedVideo;
            if (getVideoData && getVideoData()) {
                // Stop camera stream
                stream.getTracks().forEach(track => track.stop());
                document.body.removeChild(overlay);

                // Store video data but don't show full media preview
                currentMediaData = getVideoData();
                currentMediaType = 'video';

                // Show video in corner preview so user can see it was recorded
                showCornerPreview(currentMediaData, 'video');

                // Show only the video context input at the bottom
                if (videoContextWrap) {
                    videoContextWrap.style.display = 'block';
                    // Show the tag
                    const tag = document.getElementById('video-saved-tag');
                    if (tag) tag.style.display = 'flex';
                    // Show the recorded video in the small preview
                    if (smallVideoPreview) {
                        smallVideoPreview.src = currentMediaData;
                    }
                    if (videoContextInput) {
                        videoContextInput.value = '';
                        videoContextInput.placeholder = "(Optional) Add a description/context for this video...";
                        videoContextInput.required = false;
                        videoContextInput.focus();
                    }
                }
            } else {
                alert('Video not ready yet, please wait a moment and try again');
            }
        };

        // Re-record button
        document.getElementById('rerecord-btn').onclick = () => {
            document.body.removeChild(overlay);
            startVideoRecording(stream);
        };

        // Cancel button
        document.getElementById('cancel-video-btn').onclick = () => {
            // Stop camera stream
            stream.getTracks().forEach(track => track.stop());
            document.body.removeChild(overlay);
        };
    }, 500);
}



// Simple recording UI with preview
function showRecordingUI(mediaRecorder, stream, getVideoData) {
    // Store video data getter globally for access in completion handler
    window.currentRecordedVideo = getVideoData;
    
    // Create recording overlay
    const recordingOverlay = document.createElement('div');
    recordingOverlay.id = 'recording-overlay';
    recordingOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
    `;
    
    recordingOverlay.innerHTML = `
        <div style="text-align: center;">
            <div style="position: relative; display: inline-block; margin-bottom: 20px;">
                <video id="recording-preview" autoplay muted playsinline style="
                    width: 480px;
                    height: 360px;
                    border-radius: 15px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                "></video>
                <div id="countdown-timer" style="
                    position: absolute;
                    bottom: 15px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(255, 255, 255, 0.95);
                    color: #2c5530;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-size: 1.1em;
                    font-weight: bold;
                    font-family: monospace;
                    border: 2px solid #4caf50;
                    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
                    backdrop-filter: blur(10px);
                    z-index: 10;
                ">30s</div>
            </div>
            <div style="font-size: 1.5em; margin-bottom: 30px; display: flex; align-items: center; justify-content: center; gap: 10px;">
                <div style="width: 12px; height: 12px; background: #4caf50; border-radius: 50%; animation: pulse 1s infinite;"></div>
                Recording Video...
            </div>
            <button id="stop-recording-btn" style="
                background: #ff4444;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 1.1em;
                cursor: pointer;
                font-weight: bold;
                box-shadow: 0 4px 12px rgba(255, 68, 68, 0.3);
            ">⏹️ Stop Recording</button>
        </div>
    `;
    
    document.body.appendChild(recordingOverlay);
    
    // Set up video preview
    const videoPreview = document.getElementById('recording-preview');
    videoPreview.srcObject = stream;
    
    // Countdown timer functionality
    let timeLeft = 30;
    const countdownElement = document.getElementById('countdown-timer');
    console.log('Countdown element found:', countdownElement); // Debug log
    
    if (!countdownElement) {
        console.error('Countdown timer element not found!');
        return;
    }
    
    let countdownInterval = setInterval(() => {
        timeLeft--;
        countdownElement.textContent = `${timeLeft}s`;
        console.log('Countdown updated:', timeLeft); // Debug log
        
        // Change color when time is running out
        if (timeLeft <= 10) {
            countdownElement.style.border = '2px solid #ff9800';
            countdownElement.style.background = 'rgba(255, 152, 0, 0.1)';
            countdownElement.style.color = '#e65100';
        }
        if (timeLeft <= 5) {
            countdownElement.style.border = '2px solid #f44336';
            countdownElement.style.background = 'rgba(244, 67, 54, 0.1)';
            countdownElement.style.color = '#c62828';
            countdownElement.style.animation = 'pulse 0.5s infinite';
        }
        
        // Auto-stop recording when timer reaches 0
        if (timeLeft <= 0) {
            clearInterval(countdownInterval);
            console.log('Recording time limit reached - auto stopping');
            mediaRecorder.stop();
            showRecordingCompleted(recordingOverlay, stream);
        }
    }, 1000);
    
    // Store interval ID for cleanup
    recordingOverlay.countdownInterval = countdownInterval;
    
    // Add pulsing animation for recording dot
    if (!document.getElementById('pulse-style')) {
        const style = document.createElement('style');
        style.id = 'pulse-style';
        style.textContent = `
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.3; }
                100% { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
    

    
    // Stop recording button
    document.getElementById('stop-recording-btn').onclick = () => {
        console.log('Stopping recording manually');
        
        // Clear countdown timer
        if (recordingOverlay.countdownInterval) {
            clearInterval(recordingOverlay.countdownInterval);
        }
        
        mediaRecorder.stop();
        
        // Show recording completed options
        showRecordingCompleted(recordingOverlay, stream);
    };
}

// Send video to Gemini
async function sendVideoToGemini(videoData) {
    console.log('Sending video to Gemini...');
    
    appendMessage('user', '🎥 Video recorded');
    
    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message-container typing-indicator';
    typingDiv.innerHTML = '<div class="bot-msg">🤔 Analyzing your video...</div>';
    chatWindow.appendChild(typingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    
    try {
        // Get optional video context
        const contextValue = (videoContextInput && videoContextWrap && videoContextWrap.style.display !== 'none') ? (videoContextInput.value || '') : '';
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: "Please analyze this video and provide insights related to sustainability, ethics, or environmental topics.",
                username: currentUsername,
                session_id: sessionId,
                video: videoData,
                video_context: contextValue,
                mode: isPersonalAssistantMode ? 'personal-assistant' : 'sustainability'
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        chatWindow.removeChild(typingDiv);

        appendMessage('bot', data.reply);

        // After sending, hide optional context UI and reset
        if (videoContextWrap) {
            videoContextWrap.style.display = 'none';
            const tag = document.getElementById('video-saved-tag');
            if (tag) tag.style.display = 'none';
        }
        if (smallVideoPreview) {
            smallVideoPreview.src = '';
        }
        if (videoContextInput) {
            videoContextInput.value = '';
        }

        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem('sdg_session_id', sessionId);
        }
    } catch (error) {
        chatWindow.removeChild(typingDiv);
        appendMessage('bot', 'Sorry, I encountered an error analyzing your video. Please try again.');
        console.error('Error:', error);
    }
}



// Update overlay controls for photo mode
function updateOverlayForPhotoMode() {
    // Update buttons for photo capture
    captureConfirmBtn.textContent = '📸 Capture';
    captureConfirmBtn.onclick = captureFromOverlay;
    captureConfirmBtn.disabled = false;
    captureConfirmBtn.style.display = 'block';
    
    cameraCancelBtn.textContent = 'Cancel';
    cameraCancelBtn.onclick = closeCameraOverlay;
    
    // Hide recording status
    const recordingStatus = document.getElementById('overlay-recording-status');
    if (recordingStatus) {
        recordingStatus.style.display = 'none';
    }
}



function captureImage() {
    console.log('Capturing image...');
    const canvas = cameraCanvas;
    const context = canvas.getContext('2d');
    
    // Set canvas size to match video
    canvas.width = cameraVideo.videoWidth;
    canvas.height = cameraVideo.videoHeight;
    
    // Draw the video frame to canvas
    context.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64 JPEG
    currentMediaData = canvas.toDataURL('image/jpeg', 0.8);
    currentMediaType = 'image';
    
    // Show preview
    showMediaPreview(currentMediaData, 'image');
    
    // Turn off camera after capture
    stopCamera();
    
    console.log('Image captured successfully');
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    console.log('File selected:', file.name, file.type);
    
    const reader = new FileReader();
    reader.onload = (e) => {
        currentMediaData = e.target.result;
        
        if (file.type.startsWith('image/')) {
            currentMediaType = 'image';
            showMediaPreview(currentMediaData, 'image');
        } else if (file.type.startsWith('video/')) {
            currentMediaType = 'video';
            showMediaPreview(currentMediaData, 'video');
        }
    };
    reader.readAsDataURL(file);
    
    // Reset file input
    event.target.value = '';
}

function showMediaPreview(mediaSrc, type) {
    hideMediaPreview();
    
    mediaPreviewContainer.style.display = 'block';
    clearMediaBtn.style.display = 'inline-block';
    
    // Check if we're in personal assistant mode
    const isPersonalAssistant = document.getElementById('mode-toggle').checked;
    
    if (type === 'image') {
        previewImage.src = typeof mediaSrc === 'string' ? mediaSrc : URL.createObjectURL(mediaSrc);
        previewImage.style.display = 'block';
        
        // Hide video context for images
        if (videoContextWrap) {
            videoContextWrap.style.display = 'none';
            if (videoContextInput) videoContextInput.value = '';
        }
        
        if (isPersonalAssistant) {
            mediaNote.innerHTML = '✅ Image ready! <strong>💡 Tip:</strong> Add specific context to your message for better analysis (e.g., "Check my form", "Analyze the cooking technique", "What\'s wrong with this setup?").';
        } else {
            mediaNote.textContent = '✅ Image ready! Ask me questions about what you see.';
        }
    } else if (type === 'video') {
        previewVideo.src = typeof mediaSrc === 'string' ? mediaSrc : URL.createObjectURL(mediaSrc);
        previewVideo.style.display = 'block';
        
        // Show video context input for videos
        if (videoContextWrap) {
            videoContextWrap.style.display = 'block';
        }
        
        if (isPersonalAssistant) {
            mediaNote.innerHTML = '✅ Video ready! <strong>💡 Tip:</strong> Add specific context to your message for better analysis (e.g., "Review my presentation skills", "Analyze the workout form", "What can I improve?").';
        } else {
            mediaNote.textContent = '✅ Video ready! Ask me questions about what you see.';
        }
    }
    
    // Update input placeholder to reflect media context capability
    updateInputPlaceholder();
}

function hideMediaPreview() {
    mediaPreviewContainer.style.display = 'none';
    previewImage.style.display = 'none';
    previewVideo.style.display = 'none';
    clearMediaBtn.style.display = 'none';
    
    // Hide and clear video context input
    if (videoContextWrap) {
        videoContextWrap.style.display = 'none';
        if (videoContextInput) videoContextInput.value = '';
        if (smallVideoPreview) smallVideoPreview.src = '';
    }
    
    updateInputPlaceholder();
}

function updateInputPlaceholder() {
    const userInput = document.getElementById('user-input');
    const isPersonalAssistant = document.getElementById('mode-toggle').checked;
    const hasMedia = currentMediaData !== null;
    
    if (hasMedia && isPersonalAssistant) {
        userInput.placeholder = 'Add context for analysis (e.g., "Check my form", "Review technique", "What can I improve?")...';
    } else if (hasMedia) {
        userInput.placeholder = 'Ask questions about your media...';
    } else if (isPersonalAssistant) {
        userInput.placeholder = 'Chat with your AI personas or upload media for analysis...';
    } else {
        userInput.placeholder = 'Type your question here (with or without media)...';
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    cameraContainer.style.display = 'none';
    toggleCameraBtn.textContent = '📷 Camera';
    recordVideoBtn.textContent = '🎥 Record Video';
    isCameraOn = false;
    
    // Reset recording controls
    captureImageBtn.style.display = 'flex';
    startRecordingBtn.style.display = 'none';
    stopRecordingBtn.style.display = 'none';
    recordingStatus.style.display = 'none';
}

function clearMedia() {
    console.log('Clearing media...');
    currentMediaData = null;
    currentMediaType = null;
    hideMediaPreview();
    // Also hide any video context UI and reset
    if (videoContextWrap) {
        videoContextWrap.style.display = 'none';
        const tag = document.getElementById('video-saved-tag');
        if (tag) tag.style.display = 'none';
    }
    if (smallVideoPreview) {
        smallVideoPreview.src = '';
    }
    if (videoContextInput) {
        videoContextInput.value = '';
    }
    
    // Revoke object URLs to prevent memory leaks
    if (previewImage.src.startsWith('blob:')) {
        URL.revokeObjectURL(previewImage.src);
    }
    if (previewVideo.src.startsWith('blob:')) {
        URL.revokeObjectURL(previewVideo.src);
    }
}

function convertMarkdownToHtml(text) {
    // Convert **bold** to <strong>bold</strong>
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert *italic* to <em>italic</em>
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Convert line breaks to <br>
    text = text.replace(/\n/g, '<br>');
    return text;
}

function appendMessage(role, text, animate = true, isLocket = false) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    
    const msgDiv = document.createElement('div');
    msgDiv.className = role === 'user' ? 'user-msg' : 'bot-msg';
    
    // Add locket indicator if this is a locket message
    if (isLocket) {
        msgDiv.classList.add('locket-message');
    }
    
    if (role === 'bot') {
        // Create speaker button for bot messages
        const speakerBtn = document.createElement('button');
        speakerBtn.className = 'speaker-btn';
        speakerBtn.innerHTML = '🔊';
        speakerBtn.title = 'Listen to this message';
        speakerBtn.onclick = () => speakText(text, speakerBtn);
        
        // Create content wrapper for the message text
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = convertMarkdownToHtml(text);
        
        // Add speaker button and content to message
        msgDiv.appendChild(speakerBtn);
        msgDiv.appendChild(contentDiv);
    } else {
        msgDiv.textContent = text;
    }
    
    messageContainer.appendChild(msgDiv);
    chatWindow.appendChild(messageContainer);
    
    if (animate) {
        msgDiv.style.opacity = '0';
        msgDiv.style.transform = 'translateY(20px)';
        setTimeout(() => {
            msgDiv.style.transition = 'all 0.3s ease';
            msgDiv.style.opacity = '1';
            msgDiv.style.transform = 'translateY(0)';
        }, 50);
    }
    
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function startChat() {
    console.log('startChat function called!');
    const username = usernameInput.value.trim();
    console.log('Username entered:', username);
    if (!username) {
        console.log('No username entered, focusing input');
        usernameInput.focus();
        return;
    }
    
    console.log('Setting username and updating displays...');
    currentUsername = username;
    
    // Check if userDisplayName exists before setting it
    if (userDisplayName) {
        userDisplayName.textContent = username;
        console.log('Updated userDisplayName');
    } else {
        console.log('userDisplayName element not found!');
    }
    
    // Update header message too
    const headerMessage = document.getElementById('header-message');
    if (headerMessage) {
        headerMessage.textContent = `Hello ${username}! Ask me about ethics, sustainability, or SDG goals.`;
        console.log('Updated header message');
    }
    localStorage.setItem('sdg_username', username);
    
    console.log('Switching from welcome screen to chat interface...');
    console.log('welcomeScreen element:', welcomeScreen);
    console.log('chatInterface element:', chatInterface);
    
    welcomeScreen.style.display = 'none';
    chatInterface.style.display = 'block';
    // Show the input area when chat starts
    document.getElementById('input-area').style.display = 'block';
    
    console.log('Loading conversation history...');
    // Load previous conversation if exists
    loadConversationHistory();
    
    console.log('Setting up welcome message...');
    // Welcome message
    setTimeout(() => {
        appendMessage('bot', `Hello ${username}! 🌱 I'm your SDG Teacher. I'm here to help you learn about ethics, sustainability, and the UN Sustainable Development Goals. What would you like to explore today?`);
    }, 500);
    
    userInput.focus();
    console.log('startChat function completed');
}

function startAssistantChat() {
    console.log('startAssistantChat function called!');
    const username = assistantUsernameInput.value.trim();
    console.log('Username entered:', username);
    if (!username) {
        console.log('No username entered, focusing input');
        assistantUsernameInput.focus();
        return;
    }
    
    console.log('Setting username for multi-persona assistant...');
    currentUsername = username;
    
    // Update header message for assistant mode
    const headerMessage = document.getElementById('header-message');
    if (headerMessage) {
        headerMessage.textContent = `Hello ${username}! Your AI personas are ready to help!`;
        console.log('Updated header message for assistant mode');
    }
    
    localStorage.setItem('sdg_username', username);
    
    console.log('Showing chat interface...');
    showChatInterface();
    
    console.log('Setting up multi-persona welcome message...');
    // Multi-persona welcome message
    setTimeout(() => {
        const welcomeMsg = `🎭 Hey ${username}! Rile here, your Multi-Persona AI assistant is here!\n\n` +
            `👨‍🍳 **Chef Rile**: "Ready to cook up something delicious!"\n` +
            `👨‍🏫 **Teacher Rile**: "Let's learn something new together!"\n` +
            `👨‍💻 **Tech Rile**: "Got tech questions? I'm your guy!"\n` +
            `💪 **Motivation Rile**: "Let's crush those goals!"\n` +
            `💰 **Finance Rile**: "Time to get those finances sorted!"\n` +
            `🧠 **Knowledge Rile**: "Curious about anything? Ask away!"\n\n` +
            `Just ask your question and the right persona will jump in to help! 🚀`;
        
        appendMessage('bot', welcomeMsg);
    }, 500);
    
    userInput.focus();
    console.log('startAssistantChat function completed');
}

async function showChatInterface() {
    console.log('showChatInterface called for user:', currentUsername);
    
    // Update display name if element exists
    if (userDisplayName) {
        userDisplayName.textContent = currentUsername;
    }
    
    // Update header message
    const headerMessage = document.getElementById('header-message');
    if (headerMessage) {
        const headerText = isPersonalAssistantMode 
            ? `Hello ${currentUsername}! Ready to analyze your environment.`
            : `Hello ${currentUsername}! Ask me about ethics, sustainability, or SDG goals.`;
        headerMessage.textContent = headerText;
    }
    
    console.log('Switching to chat interface...');
    welcomeScreen.style.display = 'none';
    chatInterface.style.display = 'block';
    document.getElementById('input-area').style.display = 'block';
    
    // Show back button
    if (backToMainBtn) {
        backToMainBtn.style.display = 'block';
    }
    
    // Load conversation history first
    const hasHistory = await loadConversationHistory();
    
    // Only show welcome message if no previous conversation history
    if (!hasHistory) {
        setTimeout(() => {
            const welcomeMessage = isPersonalAssistantMode 
                ? `🤖 Hello ${currentUsername}! I'm Rile, your multi-persona AI assistant. How can I help you today?`
                : `👋 Hello ${currentUsername}! I'm Rile, your sustainability teacher. What would you like to learn about today?`;
            appendMessage('bot', welcomeMessage);
        }, 500);
    }
    
    userInput.focus();
    console.log('showChatInterface completed');
}

function goBackToMain() {
    console.log('Going back to main page');
    
    // Hide chat interface
    chatInterface.style.display = 'none';
    document.getElementById('input-area').style.display = 'none';
    
    // Hide back button
    if (backToMainBtn) {
        backToMainBtn.style.display = 'none';
    }
    
    // Reset header message
    const headerMessage = document.getElementById('header-message');
    if (headerMessage) {
        headerMessage.textContent = 'Ask me about ethics, sustainability, or SDG goals.';
    }
    
    // Show welcome screen
    welcomeScreen.style.display = 'block';
    
    // Clear chat window
    chatWindow.innerHTML = '';
    
    // Clear any media
    clearMedia();
    
    console.log('Returned to main page');
}

async function loadConversationHistory() {
    try {
        // Use authenticated username instead of session ID
        const userForHistory = authenticatedUsername || currentUsername;
        console.log('Loading conversation history for user:', userForHistory);
        
        if (!userForHistory) {
            console.log('No username available for loading history');
            return;
        }
        
        // Load conversations from both modes for this user
        const [sustainabilityResponse, personalAssistantResponse] = await Promise.all([
            fetch(`/conversation/sustainability/${userForHistory}`).catch(() => ({ json: () => ({ messages: [] }) })),
            fetch(`/conversation/personal-assistant/${userForHistory}`).catch(() => ({ json: () => ({ messages: [] }) }))
        ]);
        
        const sustainabilityData = await sustainabilityResponse.json();
        const personalAssistantData = await personalAssistantResponse.json();
        
        // Combine all messages from both modes
        const allMessages = [];
        
        if (sustainabilityData.messages && sustainabilityData.messages.length > 0) {
            allMessages.push(...sustainabilityData.messages.map(msg => ({ ...msg, mode: 'sustainability' })));
            console.log(`Loaded ${sustainabilityData.messages.length} messages from sustainability mode`);
        }
        
        if (personalAssistantData.messages && personalAssistantData.messages.length > 0) {
            allMessages.push(...personalAssistantData.messages.map(msg => ({ ...msg, mode: 'personal-assistant' })));
            console.log(`Loaded ${personalAssistantData.messages.length} messages from personal-assistant mode`);
        }
        
        if (allMessages.length > 0) {
            // Sort messages by timestamp to get chronological order
            allMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            
            console.log(`Displaying ${allMessages.length} messages in chronological order`);
            
            // Display all messages in chronological order
            allMessages.forEach((msg, index) => {
                // Check if this is a locket message
                const isLocket = msg.locket === true;
                
                // Handle different message formats
                // Format 1: Regular chat (user_message + bot_response)
                if (msg.user_message) {
                    appendMessage('user', msg.user_message, false, isLocket);
                    if (msg.bot_response) {
                        appendMessage('bot', msg.bot_response, false, isLocket);
                    }
                }
                // Format 2: Locket messages (role + content)
                else if (msg.role === 'user' && msg.content) {
                    appendMessage('user', msg.content, false, isLocket);
                } else if (msg.role === 'assistant' && msg.content) {
                    appendMessage('bot', msg.content, false, isLocket);
                }
            });
            return true; // Found conversation history
        } else {
            console.log('No previous conversation history found');
            return false; // No conversation history
        }
    } catch (error) {
        console.log('Error loading conversation history:', error);
        return false; // Error, treat as no history
    }
}

// Text-to-Speech Functions
let currentSpeechUtterance = null;
let isSpeaking = false;

function speakText(text, speakerBtn) {
    // Stop any ongoing speech
    if (isSpeaking && currentSpeechUtterance) {
        stopSpeaking();
        return;
    }
    
    // Check for browser support
    if (!('speechSynthesis' in window)) {
        alert('Text-to-speech not supported in your browser. Please try Chrome, Edge, or Safari.');
        return;
    }
    
    // Clean the text (remove markdown and HTML tags)
    const cleanText = text
        .replace(/[*_`#]/g, '') // Remove markdown
        .replace(/<[^>]*>/g, '') // Remove HTML tags
        .replace(/\n/g, ' ') // Replace newlines with spaces
        .trim();
    
    if (!cleanText) {
        alert('No text to read.');
        return;
    }
    
    try {
        // Create speech utterance
        currentSpeechUtterance = new SpeechSynthesisUtterance(cleanText);
        
        // Configure speech settings
        currentSpeechUtterance.rate = 0.9; // Slightly slower for clarity
        currentSpeechUtterance.pitch = 1.0;
        currentSpeechUtterance.volume = 0.8;
        
        // Try to use a natural-sounding voice
        const voices = speechSynthesis.getVoices();
        const preferredVoice = voices.find(voice => 
            voice.lang.startsWith('en') && 
            (voice.name.includes('Natural') || voice.name.includes('Enhanced') || voice.name.includes('Premium'))
        ) || voices.find(voice => voice.lang.startsWith('en')) || voices[0];
        
        if (preferredVoice) {
            currentSpeechUtterance.voice = preferredVoice;
        }
        
        // Event handlers
        currentSpeechUtterance.onstart = () => {
            isSpeaking = true;
            speakerBtn.classList.add('speaking');
            speakerBtn.innerHTML = '⏸️';
            speakerBtn.title = 'Stop reading';
            console.log('Started speaking:', cleanText.substring(0, 50) + '...');
        };
        
        currentSpeechUtterance.onend = () => {
            resetSpeakerButton(speakerBtn);
            console.log('Finished speaking');
        };
        
        currentSpeechUtterance.onerror = (event) => {
            console.error('Speech error:', event.error);
            resetSpeakerButton(speakerBtn);
            
            // Don't show alerts for normal user interruptions
            if (event.error === 'interrupted' || event.error === 'canceled') {
                return;
            }
            
            if (event.error === 'not-allowed') {
                alert('Speech synthesis permission denied. Please check your browser settings.');
            }
        };
        
        currentSpeechUtterance.onpause = () => {
            resetSpeakerButton(speakerBtn);
        };
        
        currentSpeechUtterance.oncancel = () => {
            resetSpeakerButton(speakerBtn);
        };
        
        // Start speaking
        speechSynthesis.speak(currentSpeechUtterance);
        
    } catch (error) {
        console.error('Error starting speech synthesis:', error);
        alert('Failed to start speech synthesis. Please try again.');
        resetSpeakerButton(speakerBtn);
    }
}

function stopSpeaking() {
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
    }
    isSpeaking = false;
    currentSpeechUtterance = null;
    
    // Reset all speaker buttons
    document.querySelectorAll('.speaker-btn.speaking').forEach(btn => {
        resetSpeakerButton(btn);
    });
}

function resetSpeakerButton(speakerBtn) {
    isSpeaking = false;
    speakerBtn.classList.remove('speaking');
    speakerBtn.innerHTML = '🔊';
    speakerBtn.title = 'Listen to this message';
}

// Initialize speech synthesis voices
function initializeSpeechSynthesis() {
    if ('speechSynthesis' in window) {
        // Load voices - some browsers need this event
        speechSynthesis.onvoiceschanged = () => {
            console.log('Speech synthesis voices loaded:', speechSynthesis.getVoices().length);
        };
        
        // Try to load voices immediately (works in some browsers)
        const voices = speechSynthesis.getVoices();
        if (voices.length > 0) {
            console.log('Speech synthesis voices loaded immediately:', voices.length);
        }
    } else {
        console.warn('Speech synthesis not supported in this browser');
    }
}

// Audio Recording Functions
async function toggleAudioRecording() {
    if (isAudioRecording) {
        stopAudioRecording();
    } else {
        startAudioRecording();
    }
}

async function startAudioRecording() {
    try {
        console.log('Starting audio recording...');
        console.log('User agent:', navigator.userAgent);
        console.log('Is HTTPS:', location.protocol === 'https:');
        console.log('Is localhost:', location.hostname === 'localhost' || location.hostname === '127.0.0.1');
        
        // Check if getUserMedia is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('getUserMedia is not supported in this browser');
        }
        
        // Get microphone access
        audioStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });
        
        // Create MediaRecorder for audio
        audioMediaRecorder = new MediaRecorder(audioStream, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
        });
        
        audioRecordedChunks = [];
        
        audioMediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                audioRecordedChunks.push(event.data);
                console.log('Audio chunk recorded:', event.data.size, 'bytes');
            }
        };
        
        audioMediaRecorder.onstop = async () => {
            console.log('Audio recording stopped, processing...');
            
            if (audioRecordedChunks.length === 0) {
                alert('No audio recorded. Please try again.');
                resetMicButton();
                return;
            }
            
            const audioBlob = new Blob(audioRecordedChunks, { 
                type: audioMediaRecorder.mimeType || 'audio/webm' 
            });
            
            console.log('Audio blob created:', audioBlob.size, 'bytes');
            
            // Convert to base64 and send to Gemini
            const reader = new FileReader();
            reader.onload = async () => {
                try {
                    micBtn.innerHTML = '⏳';
                    micBtn.disabled = true;
                    userInput.placeholder = 'Processing audio with AI...';
                    
                    const response = await fetch('/audio-to-text', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            audio: reader.result,
                            username: currentUsername,
                            session_id: sessionId,
                            mode: isPersonalAssistantMode ? 'personal-assistant' : 'sustainability',

                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.text) {
                        // Put transcribed text in input and auto-send
                        userInput.value = result.text;
                        userInput.placeholder = 'AI transcribed your audio! Sending...';
                        
                        // Show success message with environmental context if available
                        let message = `🎤 Transcribed: "${result.text}"`;
                        if (result.environmental_context && isPersonalAssistantMode) {
                            message += `\n🔊 Audio Context: ${result.environmental_context}`;
                            
                            // Update environment memory with audio context
                            // Environment memory now handled by backend
                        }
                        
                        showTemporaryMessage(message, '#4caf50');
                        
                        // Auto-send the message
                        setTimeout(() => {
                            chatForm.dispatchEvent(new Event('submit'));
                        }, 1000);
                        
                    } else {
                        alert('Could not transcribe audio: ' + (result.error || 'Unknown error'));
                        userInput.placeholder = 'Type your question here (with or without media)...';
                    }
                    
                } catch (error) {
                    console.error('Error processing audio:', error);
                    alert('Failed to process audio. Please try again.');
                    userInput.placeholder = 'Type your question here (with or without media)...';
                }
                
                resetMicButton();
            };
            
            reader.readAsDataURL(audioBlob);
        };
        
        audioMediaRecorder.onerror = (event) => {
            console.error('Audio MediaRecorder error:', event.error);
            alert('Audio recording error: ' + event.error);
            resetMicButton();
        };
        
        // Start recording
        audioMediaRecorder.start();
        isAudioRecording = true;
        
        // Update UI
        micBtn.classList.add('recording');
        micBtn.innerHTML = '⏹️';
        micBtn.title = 'Stop recording';
        userInput.placeholder = 'Recording audio... Click mic to stop';
        
        console.log('Audio recording started successfully');
        
    } catch (error) {
        console.error('Error starting audio recording:', error);
        
        let errorMessage = 'Unable to access microphone: ';
        if (error.name === 'NotAllowedError') {
            errorMessage += 'Permission denied. Please allow microphone access.';
        } else if (error.name === 'NotFoundError') {
            errorMessage += 'No microphone found.';
        } else {
            errorMessage += error.message;
        }
        
        alert(errorMessage);
        resetMicButton();
    }
}

function stopAudioRecording() {
    if (audioMediaRecorder && audioMediaRecorder.state !== 'inactive') {
        audioMediaRecorder.stop();
    }
    
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
        audioStream = null;
    }
    
    isAudioRecording = false;
    console.log('Audio recording stopped');
}

function resetMicButton() {
    isAudioRecording = false;
    micBtn.classList.remove('recording');
    micBtn.innerHTML = '🎤';
    micBtn.title = 'Record audio message';
    micBtn.disabled = false;
    userInput.placeholder = 'Type your question here (with or without media)...';
}

function showTemporaryMessage(text, color) {
    const tempMessage = document.createElement('div');
    tempMessage.style.cssText = `
        position: fixed;
        top: 60px;
        left: 50%;
        transform: translateX(-50%);
        background: ${color};
        color: white;
        padding: 10px 20px;
        border-radius: 20px;
        z-index: 10002;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        font-size: 0.9em;
        max-width: 80%;
        text-align: center;
        animation: fadeInOut 4s ease-in-out;
    `;
    tempMessage.innerHTML = text;
    document.body.appendChild(tempMessage);
    
    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
            15% { opacity: 1; transform: translateX(-50%) translateY(0); }
            85% { opacity: 1; transform: translateX(-50%) translateY(0); }
            100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
        }
    `;
    document.head.appendChild(style);
    
    // Remove after animation
    setTimeout(() => {
        document.body.removeChild(tempMessage);
        document.head.removeChild(style);
    }, 4000);
}

// Event Listeners
console.log('Setting up event listeners');
console.log('startChatBtn found:', startChatBtn);
startChatBtn.addEventListener('click', startChat);
startAssistantChatBtn.addEventListener('click', startAssistantChat);
toggleCameraBtn.addEventListener('click', toggleCamera);
recordVideoBtn.addEventListener('click', recordVideo);
captureImageBtn.addEventListener('click', captureImage);
clearMediaBtn.addEventListener('click', clearMedia);
fileUploadInput.addEventListener('change', handleFileUpload);
micBtn.addEventListener('click', toggleAudioRecording);
backToMainBtn.addEventListener('click', goBackToMain);

// Clear video button event listener
if (clearVideoBtn) {
    clearVideoBtn.addEventListener('click', () => {
        // Clear video data
        currentMediaData = null;
        currentMediaType = null;
        
        // Hide video context wrap
        if (videoContextWrap) {
            videoContextWrap.style.display = 'none';
            const tag = document.getElementById('video-saved-tag');
            if (tag) tag.style.display = 'none';
        }
        
        // Clear video context input
        if (videoContextInput) {
            videoContextInput.value = '';
        }
        
        // Clear small video preview
        if (smallVideoPreview) {
            smallVideoPreview.src = '';
        }
        
        console.log('Video cleared');
    });
}

// Add event listener for clear video button
if (clearVideoBtn) {
    clearVideoBtn.addEventListener('click', () => {
        // Clear video data and hide context input
        currentMediaData = null;
        currentMediaType = null;
        if (videoContextWrap) {
            videoContextWrap.style.display = 'none';
            const tag = document.getElementById('video-saved-tag');
            if (tag) tag.style.display = 'none';
            if (videoContextInput) videoContextInput.value = '';
        }
        
        // Show confirmation
        const tempMessage = document.createElement('div');
        tempMessage.style.cssText = `
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: #666;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            z-index: 10002;
            font-size: 0.9em;
        `;
        tempMessage.textContent = 'Video cleared';
        document.body.appendChild(tempMessage);
        
        setTimeout(() => {
            if (document.body.contains(tempMessage)) {
                document.body.removeChild(tempMessage);
            }
        }, 2000);
    });
}

// New camera overlay event listeners
captureConfirmBtn.addEventListener('click', captureFromOverlay);
cameraCancelBtn.addEventListener('click', closeCameraOverlay);

usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        startChat();
    }
});

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    // Allow empty message if a recorded/uploaded video or image exists
    if (!message && !currentMediaData) return;
    
    // Stop any ongoing speech when sending a new message
    stopSpeaking();
    
    if (message) {
        appendMessage('user', message);
        userInput.value = '';
    } else if (currentMediaData && currentMediaType === 'video') {
        appendMessage('user', '🎥 Sent a video');
    } else if (currentMediaData && currentMediaType === 'image') {
        appendMessage('user', '🖼️ Sent an image');
    }
    
    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message-container typing-indicator';
    typingDiv.innerHTML = '<div class="bot-msg">🤔 Thinking...</div>';
    chatWindow.appendChild(typingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    
    try {
        const requestData = { 
            message, 
            username: currentUsername,
            session_id: sessionId,
            mode: isPersonalAssistantMode ? 'personal-assistant' : 'sustainability'
        };
        
        // Debug logging
        console.log('🔍 Chat Request Debug:', {
            mode: requestData.mode,
            isPersonalAssistantMode,
            currentUsername,
            sessionId
        });
        
        // Add media data if available
        if (currentMediaData) {
            if (currentMediaType === 'image') {
                requestData.image = currentMediaData;
            } else if (currentMediaType === 'video') {
                requestData.video = currentMediaData;
                // Include optional video context if provided
                if (videoContextInput && videoContextWrap && videoContextWrap.style.display !== 'none' && videoContextInput.value.trim()) {
                    requestData.video_context = videoContextInput.value.trim();
                }
            }
        }
        
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        const data = await res.json();
        
        // Remove typing indicator
        chatWindow.removeChild(typingDiv);
        
        appendMessage('bot', data.reply);
        
        // Clear media and optional context UI after successful send
        clearMedia();
        const tag = document.getElementById('video-saved-tag');
        if (tag) tag.style.display = 'none';
        
        // Update session ID if new one was created
        if (data.session_id) {
            sessionId = data.session_id;
            localStorage.setItem('sdg_session_id', sessionId);
        }
    } catch (error) {
        chatWindow.removeChild(typingDiv);
        appendMessage('bot', 'Sorry, I encountered an error. Please try again.');
    }
});

// Initialize
window.addEventListener('load', () => {
    const savedUsername = localStorage.getItem('sdg_username');
    const headerMessage = document.getElementById('header-message');
    
    // On login screen, don't show username - just show generic message
    if (headerMessage) {
        headerMessage.textContent = 'Welcome! Please log in to continue.';
    }
    
    // Don't pre-fill username on login screen for security
    // usernameInput.focus();
    
    // Initialize speech synthesis voices
    initializeSpeechSynthesis();
    
    // Initialize mode toggle
    initializeModeToggle();
    
    // Initialize profile system
    initializeProfileSystem();
});

function initializeProfileSystem() {
    if (selectProfileBtn) {
        selectProfileBtn.addEventListener('click', () => {
            const selectedUsername = profileSelect.value;
            console.log('Profile selected:', selectedUsername);
            if (selectedUsername) {
                currentUsername = selectedUsername;
                environmentMemory = getProfileMemory(selectedUsername);
                
                // Keep existing session ID for conversation continuity
                // Only generate new if none exists
                if (!sessionId) {
                    sessionId = generateSessionId();
                    localStorage.setItem('sdg_session_id', sessionId);
                }
                
                console.log('Starting chat with profile:', currentUsername);
                console.log('Loaded environment memory:', environmentMemory.length, 'observations');
                
                // Show memory status to user
                if (environmentMemory.length > 0) {
                    showTemporaryMessage(`🧠 Loaded ${environmentMemory.length} previous environment observations for ${currentUsername}`, '#2196f3');
                } else {
                    showTemporaryMessage(`👋 Welcome ${currentUsername}! Upload images/videos to build your environment memory.`, '#2196f3');
                }
                
                showChatInterface();
            } else {
                console.log('No profile selected');
                alert('Please select a profile first');
            }
        });
    } else {
        console.log('selectProfileBtn not found');
    }
    
    if (createProfileBtn) {
        createProfileBtn.addEventListener('click', () => {
            const newUsername = newUsernameInput.value.trim();
            
            if (newUsername) {
                // Show the modal
                profileModal.style.display = 'flex';
                // Focus on the background textarea after modal animation
                setTimeout(() => profileBackgroundInput.focus(), 300);
            } else {
                showTemporaryMessage('Please enter your name first', '#f44336');
            }
        });
    }
    
    // Handle modal close
    if (modalClose) {
        modalClose.addEventListener('click', () => {
            profileModal.style.display = 'none';
        });
    }
    
    // Close modal when clicking outside
    if (profileModal) {
        profileModal.addEventListener('click', (e) => {
            if (e.target === profileModal) {
                profileModal.style.display = 'none';
            }
        });
    }
    
    // Handle skip details button
    if (skipDetailsBtn) {
        skipDetailsBtn.addEventListener('click', () => {
            const newUsername = newUsernameInput.value.trim();
            profileModal.style.display = 'none';
            createProfileWithDetails(newUsername, '', '');
        });
    }
    
    // Handle save and start button
    if (saveAndStartBtn) {
        saveAndStartBtn.addEventListener('click', () => {
            const newUsername = newUsernameInput.value.trim();
            const background = profileBackgroundInput?.value.trim() || '';
            const livingSituation = livingSituationSelect?.value || '';
            profileModal.style.display = 'none';
            createProfileWithDetails(newUsername, background, livingSituation);
        });
    }
}

function createProfileWithDetails(username, background, livingSituation) {
    currentUsername = username;
    
    // Keep existing session ID for conversation continuity
    // Only generate new if none exists
    if (!sessionId) {
        sessionId = generateSessionId();
        localStorage.setItem('sdg_session_id', sessionId);
    }
    
    // Save new profile with background information
    saveProfile(username, sessionId, background, livingSituation);
    environmentMemory = [];
    
    // Show background info confirmation
    if (background || livingSituation) {
        const situationText = livingSituation ? ` (${livingSituation})` : '';
        showTemporaryMessage(`✅ Profile created with background info${situationText}`, '#2196f3');
    } else {
        showTemporaryMessage(`✅ Profile created for ${username}`, '#2196f3');
    }
    
    showChatInterface();
}

// Mode Toggle Functions
function initializeModeToggle() {
    if (modeToggle) {
        modeToggle.addEventListener('change', toggleMode);
        
        // Load saved mode preference or use default (Personal Assistant)
        const savedMode = localStorage.getItem('sdg_chat_mode');
        if (savedMode === 'personal-assistant' || !savedMode) {
            // Default to Personal Assistant if no saved preference
            modeToggle.checked = true;
            toggleMode();
        } else {
            // Sustainability mode
            modeToggle.checked = false;
            toggleMode();
        }
    }
}

function toggleMode() {
    isPersonalAssistantMode = modeToggle.checked;
    
    // Update UI theme and input sections
    if (isPersonalAssistantMode) {
        document.body.classList.add('personal-assistant-mode');
        mainTitle.innerHTML = '🤖 Welcome to Personal Assistant';
        mainSubtitle.innerHTML = 'Your intelligent companion for environment analysis and meal planning!';
        sustainabilityInput.style.display = 'none';
        assistantInput.style.display = 'block';
        loadUserProfiles();
        localStorage.setItem('sdg_chat_mode', 'personal-assistant');
    } else {
        document.body.classList.remove('personal-assistant-mode');
        mainTitle.innerHTML = '🌱 Welcome to SDG Teacher Chatbot';
        mainSubtitle.innerHTML = 'Your personal guide to ethics, sustainability, and UN SDG goals!';
        sustainabilityInput.style.display = 'block';
        assistantInput.style.display = 'none';
        localStorage.setItem('sdg_chat_mode', 'sustainability');
    }
    
    // Update input placeholder if chat interface is active
    const chatInterface = document.getElementById('chat-interface');
    if (chatInterface.style.display !== 'none') {
        updateInputPlaceholder();
    }
    
    console.log('Mode switched to:', isPersonalAssistantMode ? 'Personal Assistant' : 'Sustainability Teacher');
}

// User Profile Management
function loadUserProfiles() {
    const profiles = getStoredProfiles();
    const profileSelect = document.getElementById('profile-select');
    
    // Clear existing options except the first one
    while (profileSelect.children.length > 1) {
        profileSelect.removeChild(profileSelect.lastChild);
    }
    
    if (profiles.length > 0) {
        profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.username;
            option.textContent = `${profile.username} (${profile.sessionsCount} sessions)`;
            profileSelect.appendChild(option);
        });
        existingProfiles.style.display = 'block';
    } else {
        existingProfiles.style.display = 'none';
    }
}

function getStoredProfiles() {
    const profiles = localStorage.getItem('assistant_profiles');
    return profiles ? JSON.parse(profiles) : [];
}

function saveProfile(username, sessionId, background = '', livingSituation = '') {
    const profiles = getStoredProfiles();
    const existingProfile = profiles.find(p => p.username === username);
    
    if (existingProfile) {
        existingProfile.sessionsCount++;
        existingProfile.lastSession = sessionId;
        existingProfile.lastAccess = new Date().toISOString();
        // Update background info if provided
        if (background) existingProfile.background = background;
        if (livingSituation) existingProfile.livingSituation = livingSituation;
    } else {
        profiles.push({
            username: username,
            sessionsCount: 1,
            lastSession: sessionId,
            createdAt: new Date().toISOString(),
            lastAccess: new Date().toISOString(),
            environmentMemory: [],
            background: background || '',
            livingSituation: livingSituation || ''
        });
    }
    
    localStorage.setItem('assistant_profiles', JSON.stringify(profiles));
}

function getProfileMemory(username) {
    const profiles = getStoredProfiles();
    const profile = profiles.find(p => p.username === username);
    return profile ? profile.environmentMemory || [] : [];
}

function updateProfileMemory(username, memory) {
    const profiles = getStoredProfiles();
    const profile = profiles.find(p => p.username === username);
    
    if (profile) {
        profile.environmentMemory = memory;
        localStorage.setItem('assistant_profiles', JSON.stringify(profiles));
    }
}

function detectTourContent(userMessage, response) {
    // Detect if this is a comprehensive tour/overview
    const tourKeywords = [
        'tour', 'show you', 'look at my', 'everything on', 'all my', 'around my', 
        'my space', 'my room', 'my table', 'my desk', 'my kitchen', 'my belongings',
        'what do you see', 'analyze my', 'inventory', 'scan my'
    ];
    
    const isTour = tourKeywords.some(keyword => 
        userMessage.toLowerCase().includes(keyword) || 
        response.toLowerCase().includes('comprehensive') ||
        response.toLowerCase().includes('detailed inventory') ||
        response.length > 1000 // Long detailed response indicates tour
    );
    
    return isTour;
}

function updateEnvironmentMemoryFromResponse(response, userMessage = '') {
    // Extract key observations from AI response
    const observations = [];
    const isTour = detectTourContent(userMessage, response);
    
    // Enhanced patterns for tour detection and item extraction
    const patterns = [
        /(?:I (?:see|notice|observe|identify)|Visible items?:|Items? present:|Objects? identified?:|DETAILED INVENTORY:)(.*?)(?:\n|$)/gi,
        /(?:Food items?:|Ingredients?:|Supplies?:|Groceries?:)(.*?)(?:\n|$)/gi,
        /(?:Environment:|Room condition:|Space analysis:|ENVIRONMENTAL ASSESSMENT:)(.*?)(?:\n|$)/gi,
        /(?:Safety concerns?:|Hazards?:|Issues?:|SAFETY CONSIDERATIONS:)(.*?)(?:\n|$)/gi,
        /(?:Electronics?:|Devices?:|Technology:)(.*?)(?:\n|$)/gi,
        /(?:Furniture:|Organization:|Storage:)(.*?)(?:\n|$)/gi
    ];
    
    patterns.forEach(pattern => {
        let match;
        while ((match = pattern.exec(response)) !== null) {
            const observation = match[1].trim();
            if (observation && observation.length > 10) {
                observations.push(`${new Date().toLocaleDateString()}: ${observation}`);
            }
        }
    });
    
    // Add observations to environment memory
    if (observations.length > 0) {
        environmentMemory.push(...observations);
        
        // Keep only last 50 observations to prevent excessive memory usage
        if (environmentMemory.length > 50) {
            environmentMemory = environmentMemory.slice(-50);
        }
        
        // Update profile memory
        if (currentUsername) {
            updateProfileMemory(currentUsername, environmentMemory);
        }
        
        console.log('Updated environment memory with', observations.length, 'new observations');
    }
}

function updateEnvironmentMemoryFromAudio(audioContext) {
    if (!fisPersonalAssistantMode || !audioContext) return;
    
    const now = new Date();
    const observation = {
        timestamp: now.toISOString(),
        date: now.toLocaleDateString(),
        time: now.toLocaleTimeString(),
        day: now.toLocaleDateString('en-US', { weekday: 'long' }),
        type: 'audio',
        context: audioContext,
        fullResponse: `Audio Environmental Analysis: ${audioContext}`, // Store as full response
        summary: `Audio environment: ${audioContext}`,
        items: extractSpecificItems(audioContext) // Extract any items mentioned in audio context
    };
    
    environmentMemory.push(observation);
    
    // Keep only last 50 observations
    if (environmentMemory.length > 50) {
        environmentMemory = environmentMemory.slice(-50);
    }
    
    // Update profile memory
    if (currentUsername) {
        updateProfileMemory(currentUsername, environmentMemory);
    }
    
    console.log('Environment memory updated with audio context:', {
        audioContext: audioContext,
        itemsFound: observation.items.length
    });
}

// Environment Memory Functions
function updateEnvironmentMemory(response, mediaType, userMessage = '') {
    if (!isPersonalAssistantMode) return;
    
    // Store the complete AI response as memory database
    const now = new Date();
    const isTour = detectTourContent(userMessage, response);
    
    const observation = {
        timestamp: now.toISOString(),
        date: now.toLocaleDateString(),
        time: now.toLocaleTimeString(),
        day: now.toLocaleDateString('en-US', { weekday: 'long' }),
        type: mediaType,
        isTour: isTour, // Mark comprehensive tours for priority reference
        userMessage: userMessage, // Store user's request for context
        fullResponse: response, // Store complete AI response
        summary: generateMemorySummary(response), // Generate concise summary for quick reference
        items: extractSpecificItems(response) // Extract specific items mentioned
    };
    
    environmentMemory.push(observation);
    
    // Keep only last 50 observations to manage memory
    if (environmentMemory.length > 50) {
        environmentMemory = environmentMemory.slice(-50);
    }
    
    // Update profile memory
    if (currentUsername) {
        updateProfileMemory(currentUsername, environmentMemory);
    }
    
    // Save to localStorage
    localStorage.setItem('environment_memory', JSON.stringify(environmentMemory));
    
    console.log('Environment memory updated with full response:', {
        type: mediaType,
        responseLength: response.length,
        itemsFound: observation.items.length
    });
}

function generateMemorySummary(response) {
    // Create a concise summary from the AI response
    const lines = response.split('\n');
    const importantLines = [];
    
    for (const line of lines) {
        const trimmed = line.trim();
        // Look for inventory sections, key findings, and important observations
        if (trimmed.match(/^(DETAILED INVENTORY|ENVIRONMENTAL ASSESSMENT|VISIBLE|I can see|Items observed|Electronics|Cables)/i) ||
            trimmed.match(/^[\d\-\*•]/) || // List items
            trimmed.includes('visible:') || trimmed.includes('observed:') || trimmed.includes('found:') ||
            trimmed.length > 30 && trimmed.length < 150) { // Substantive sentences
            importantLines.push(trimmed);
        }
    }
    
    return importantLines.slice(0, 8).join(' | '); // Top 8 key points
}

function extractSpecificItems(response) {
    // Extract specific items, brands, and objects mentioned
    const items = [];
    const lines = response.split('\n');
    
    // Common item patterns
    const itemPatterns = [
        /\b(USB|HDMI|ethernet|power|charging|cable|cord|wire)\b/gi,
        /\b(watch|phone|laptop|computer|tablet|keyboard|mouse|monitor|screen)\b/gi,
        /\b(charger|adapter|connector|hub|speaker|headphones|earbuds)\b/gi,
        /\b(Apple|Samsung|Dell|HP|Sony|Microsoft|Google|Nintendo|PlayStation|Xbox)\b/gi,
        /\b(iPhone|iPad|MacBook|Surface|Galaxy|Pixel)\b/gi
    ];
    
    for (const line of lines) {
        for (const pattern of itemPatterns) {
            const matches = line.match(pattern);
            if (matches) {
                items.push(...matches.map(m => m.toLowerCase()));
            }
        }
    }
    
    // Remove duplicates and return unique items
    return [...new Set(items)];
}

function loadEnvironmentMemory() {
    try {
        const saved = localStorage.getItem('environment_memory');
        if (saved) {
            environmentMemory = JSON.parse(saved);
            console.log('Loaded environment memory:', environmentMemory.length, 'observations');
        }
    } catch (error) {
        console.log('No previous environment memory found');
        environmentMemory = [];
    }
}

// Format memory with time context for AI
function formatMemoryForAI(memory) {
    if (!memory || memory.length === 0) return [];
    
    const now = new Date();
    const today = now.toLocaleDateString();
    const yesterday = new Date(now - 24 * 60 * 60 * 1000).toLocaleDateString();
    
    // Prioritize tours and comprehensive scans
    const sortedMemory = [...memory].sort((a, b) => {
        // Tours get priority
        if (a.isTour && !b.isTour) return -1;
        if (!a.isTour && b.isTour) return 1;
        // Then by recency
        return new Date(b.timestamp) - new Date(a.timestamp);
    });
    
    return sortedMemory.map(item => {
        // Handle legacy items without date/time fields
        if (!item.date && item.timestamp) {
            const itemDate = new Date(item.timestamp);
            item.date = itemDate.toLocaleDateString();
            item.time = itemDate.toLocaleTimeString();
            item.day = itemDate.toLocaleDateString('en-US', { weekday: 'long' });
        }
        
        let timeContext = '';
        if (item.date === today) {
            timeContext = `Today at ${item.time}`;
        } else if (item.date === yesterday) {
            timeContext = `Yesterday at ${item.time}`;
        } else {
            timeContext = `${item.day}, ${item.date} at ${item.time}`;
        }
        
        // Add tour indicator
        const tourIndicator = item.isTour ? ' [COMPREHENSIVE TOUR]' : '';
        
        // Use full response if available, otherwise fall back to summary/context
        let memoryContent = '';
        if (item.fullResponse) {
            // For tours, include user context
            const userContext = item.isTour && item.userMessage ? `User request: "${item.userMessage}" | ` : '';
            memoryContent = `${item.type} analysis${tourIndicator} - ${userContext}Summary: ${item.summary || 'Detailed scan performed'}`;
            if (item.items && item.items.length > 0) {
                memoryContent += ` | Items found: ${item.items.join(', ')}`;
            }
            // For tours, include more of the full response
            if (item.isTour) {
                memoryContent += `\n--- COMPREHENSIVE ANALYSIS ---\n${item.fullResponse}\n--- END ANALYSIS ---`;
            } else {
                memoryContent += `\n--- ANALYSIS ---\n${item.fullResponse.substring(0, 500)}...\n--- END ANALYSIS ---`;
            }
        } else {
            // Legacy format
            memoryContent = `${item.type}: ${item.summary || item.context}`;
        }
        
        return `${timeContext} - ${memoryContent}`;
    });
}

// ============================================
// Authentication System
// ============================================

// Get auth elements
const loginScreen = document.getElementById('login-screen');
const registerScreen = document.getElementById('register-screen');
const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginBtn = document.getElementById('login-btn');
const registerUsername = document.getElementById('register-username');
const registerPassword = document.getElementById('register-password');
const registerPasswordConfirm = document.getElementById('register-password-confirm');
const registerBtn = document.getElementById('register-btn');
const showRegisterBtn = document.getElementById('show-register-btn');
const showLoginBtn = document.getElementById('show-login-btn');
const authMessage = document.getElementById('auth-message');
const registerMessage = document.getElementById('register-message');

// Store authenticated username
let authenticatedUsername = null;

// Show message helper
function showAuthMessage(element, message, type) {
    element.textContent = message;
    element.className = `auth-message ${type}`;
    element.style.display = 'block';
}

// Hide message helper
function hideAuthMessage(element) {
    element.style.display = 'none';
}

// Switch to registration screen
showRegisterBtn.addEventListener('click', () => {
    loginScreen.style.display = 'none';
    registerScreen.style.display = 'block';
    hideAuthMessage(authMessage);
    hideAuthMessage(registerMessage);
});

// Switch to login screen
showLoginBtn.addEventListener('click', () => {
    registerScreen.style.display = 'none';
    loginScreen.style.display = 'block';
    hideAuthMessage(authMessage);
    hideAuthMessage(registerMessage);
});

// Handle login
loginBtn.addEventListener('click', async () => {
    const username = loginUsername.value.trim();
    const password = loginPassword.value.trim();
    
    if (!username || !password) {
        showAuthMessage(authMessage, 'Please enter both username and password', 'error');
        return;
    }
    
    loginBtn.disabled = true;
    loginBtn.textContent = 'Logging in...';
    hideAuthMessage(authMessage);
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            authenticatedUsername = data.username;
            showAuthMessage(authMessage, 'Login successful! Redirecting...', 'success');
            
            // Wait a moment then show welcome screen
            setTimeout(() => {
                loginScreen.style.display = 'none';
                welcomeScreen.style.display = 'block';
                // Pre-fill username in welcome screen
                if (usernameInput) usernameInput.value = authenticatedUsername;
                if (assistantUsernameInput) assistantUsernameInput.value = authenticatedUsername;
                // Start locket status monitoring
                startLocketMonitoring();
            }, 1000);
        } else {
            // Show specific error messages
            if (data.error === 'Username not registered') {
                showAuthMessage(authMessage, 
                    'Username not registered. Would you like to create a new account?', 
                    'error');
            } else if (data.error === 'Incorrect password') {
                showAuthMessage(authMessage, 'Incorrect password. Please try again.', 'error');
            } else {
                showAuthMessage(authMessage, data.error || 'Login failed', 'error');
            }
        }
    } catch (error) {
        console.error('Login error:', error);
        showAuthMessage(authMessage, 'Connection error. Please try again.', 'error');
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
});

// Handle registration
registerBtn.addEventListener('click', async () => {
    const username = registerUsername.value.trim();
    const password = registerPassword.value.trim();
    const passwordConfirm = registerPasswordConfirm.value.trim();
    
    if (!username || !password || !passwordConfirm) {
        showAuthMessage(registerMessage, 'Please fill in all fields', 'error');
        return;
    }
    
    if (password.length < 6) {
        showAuthMessage(registerMessage, 'Password must be at least 6 characters', 'error');
        return;
    }
    
    if (password !== passwordConfirm) {
        showAuthMessage(registerMessage, 'Passwords do not match', 'error');
        return;
    }
    
    registerBtn.disabled = true;
    registerBtn.textContent = 'Creating Account...';
    hideAuthMessage(registerMessage);
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            authenticatedUsername = data.username;
            showAuthMessage(registerMessage, 'Account created successfully! Redirecting...', 'success');
            
            // Wait a moment then show welcome screen
            setTimeout(() => {
                registerScreen.style.display = 'none';
                welcomeScreen.style.display = 'block';
                // Pre-fill username in welcome screen
                if (usernameInput) usernameInput.value = authenticatedUsername;
                if (assistantUsernameInput) assistantUsernameInput.value = authenticatedUsername;
            }, 1500);
        } else {
            if (data.error === 'Username already exists') {
                showAuthMessage(registerMessage, 
                    'Username already taken. Please choose a different username.', 
                    'error');
            } else {
                showAuthMessage(registerMessage, data.error || 'Registration failed', 'error');
            }
        }
    } catch (error) {
        console.error('Registration error:', error);
        showAuthMessage(registerMessage, 'Connection error. Please try again.', 'error');
    } finally {
        registerBtn.disabled = false;
        registerBtn.textContent = 'Create Account';
    }
});

// Allow Enter key to submit
loginPassword.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loginBtn.click();
});

registerPasswordConfirm.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') registerBtn.click();
});


// ============================================
// LOCKET STATUS MONITORING
// ============================================

const locketStatus = document.getElementById('locket-status');
let locketStatusInterval = null;

async function checkLocketStatus() {
    if (!authenticatedUsername) return;
    
    try {
        const response = await fetch(`/api/locket/status/${authenticatedUsername}`);
        const data = await response.json();
        
        if (data.connected) {
            locketStatus.classList.add('connected');
            locketStatus.title = 'AI Locket Connected - Click to control';
        } else {
            locketStatus.classList.remove('connected');
            locketStatus.title = 'AI Locket Disconnected';
        }
    } catch (error) {
        console.error('Locket status check error:', error);
    }
}

// Show locket status after login
function startLocketMonitoring() {
    if (locketStatus) {
        locketStatus.style.display = 'flex';
        checkLocketStatus();
        locketStatusInterval = setInterval(checkLocketStatus, 3000);
    }
}

// Stop monitoring on logout
function stopLocketMonitoring() {
    if (locketStatus) {
        locketStatus.style.display = 'none';
        clearInterval(locketStatusInterval);
    }
}

// Handle locket status click
if (locketStatus) {
    locketStatus.addEventListener('click', () => {
        // Store username for locket control page
        sessionStorage.setItem('username', authenticatedUsername);
        window.open('/locket-control', '_blank');
    });
}

// Start monitoring after successful login
// (Already handled in login function above, but ensure it's called)
