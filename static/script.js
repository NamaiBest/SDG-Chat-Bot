const chatWindow = document.getElementById('chat-window');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const welcomeScreen = document.getElementById('welcome-screen');
const chatInterface = document.getElementById('chat-interface');
const usernameInput = document.getElementById('username');
const startChatBtn = document.getElementById('start-chat');
const userDisplayName = document.getElementById('user-display-name');

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
        
        // Get camera stream
        cameraStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 }, 
                height: { ideal: 480 },
                facingMode: 'user'
            },
            audio: true
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
            audio: false
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
        // Send video button
        document.getElementById('send-video-btn').onclick = () => {
            const getVideoData = window.currentRecordedVideo;
            if (getVideoData && getVideoData()) {
                // Stop camera stream
                stream.getTracks().forEach(track => track.stop());
                document.body.removeChild(overlay);
                sendVideoToGemini(getVideoData());
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
            <video id="recording-preview" autoplay muted playsinline style="
                width: 480px;
                height: 360px;
                border-radius: 15px;
                margin-bottom: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            "></video>
            <div style="font-size: 1.5em; margin-bottom: 30px; display: flex; align-items: center; justify-content: center; gap: 10px;">
                <div style="width: 12px; height: 12px; background: #ff4444; border-radius: 50%; animation: pulse 1s infinite;"></div>
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
        console.log('Stopping recording');
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
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: "Please analyze this video and provide insights related to sustainability, ethics, or environmental topics.",
                username: currentUsername,
                session_id: sessionId,
                video: videoData
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        chatWindow.removeChild(typingDiv);
        
        appendMessage('bot', data.reply);
        
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
    
    if (type === 'image') {
        previewImage.src = typeof mediaSrc === 'string' ? mediaSrc : URL.createObjectURL(mediaSrc);
        previewImage.style.display = 'block';
        mediaNote.textContent = '✅ Image ready! Ask me questions about what you see.';
    } else if (type === 'video') {
        previewVideo.src = typeof mediaSrc === 'string' ? mediaSrc : URL.createObjectURL(mediaSrc);
        previewVideo.style.display = 'block';
        mediaNote.textContent = '✅ Video ready! Ask me questions about what you see.';
    }
}

function hideMediaPreview() {
    mediaPreviewContainer.style.display = 'none';
    previewImage.style.display = 'none';
    previewVideo.style.display = 'none';
    clearMediaBtn.style.display = 'none';
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

function appendMessage(role, text, animate = true) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    
    const msgDiv = document.createElement('div');
    msgDiv.className = role === 'user' ? 'user-msg' : 'bot-msg';
    
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

async function loadConversationHistory() {
    try {
        const response = await fetch(`/conversation/${sessionId}`);
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                appendMessage('user', msg.user_message, false);
                appendMessage('bot', msg.bot_response, false);
            });
        }
    } catch (error) {
        console.log('No previous conversation found');
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
                            session_id: sessionId
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.text) {
                        // Put transcribed text in input and auto-send
                        userInput.value = result.text;
                        userInput.placeholder = 'AI transcribed your audio! Sending...';
                        
                        // Show success message
                        showTemporaryMessage(`🎤 Transcribed: "${result.text}"`, '#4caf50');
                        
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
toggleCameraBtn.addEventListener('click', toggleCamera);
recordVideoBtn.addEventListener('click', recordVideo);
captureImageBtn.addEventListener('click', captureImage);
clearMediaBtn.addEventListener('click', clearMedia);
fileUploadInput.addEventListener('change', handleFileUpload);
micBtn.addEventListener('click', toggleAudioRecording);

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
    if (!message) return;
    
    // Stop any ongoing speech when sending a new message
    stopSpeaking();
    
    appendMessage('user', message);
    userInput.value = '';
    
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
            session_id: sessionId
        };
        
        // Add media data if available
        if (currentMediaData) {
            if (currentMediaType === 'image') {
                requestData.image = currentMediaData;
            } else if (currentMediaType === 'video') {
                requestData.video = currentMediaData;
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
    
    if (savedUsername) {
        usernameInput.value = savedUsername;
        if (headerMessage) headerMessage.textContent = `Hello ${savedUsername}! Ask me about ethics, sustainability, or SDG goals.`;
    } else {
        // Set default text when no username is saved
        if (headerMessage) headerMessage.textContent = 'Ask me about ethics, sustainability, or SDG goals.';
    }
    usernameInput.focus();
    
    // Initialize speech synthesis voices
    initializeSpeechSynthesis();
});
