# 🎥 AI Locket System - Complete Guide

## 🚀 Quick Start (5 Minutes)

### 1. ESP32 Setup
```arduino
1. Open ESP32_CAM_Locket.ino in Arduino IDE
2. Update WiFi: WIFI_SSID = "YourNetwork"
3. Update PASSWORD: WIFI_PASSWORD = "YourPassword"
4. Update Server:
   - Local: SERVER_URL = "http://192.xxx.x.xxx:8000" (use YOUR computer's IP)
   - Production: SERVER_URL = "https://your-app.up.railway.app"
5. Upload to ESP32-CAM
6. Check Serial Monitor for connection confirmation
```

### 2. Start Server
```bash
cd "/Users/namai/Documents/Project/Chat bot"
python app.py
# Server runs on http://0.0.0.0:8000
```

### 3. Use Locket
```
1. Open browser: http://192.xxx.x.xxx:8000 (or your Railway URL)
2. Login with credentials
3. See 🟢 Locket indicator (top-right)
4. Click indicator → Opens locket control page
5. Press START → Speak for 10 seconds
6. Wait for AI response
```

---

## 📋 What You Need

### Hardware
- **ESP32-CAM** (AI Thinker module with OV2640 camera)
- **INMP441** I2S Microphone
- **3.7V LiPo Battery** (500-1000mAh)
- **TP4056 Charger Module** (for USB charging)
- **Power Switch**
- **FTDI Programmer** (for uploading code)

### Software
- **Arduino IDE** with ESP32 board support
- **Libraries**: ArduinoJson, ESP32-A2DP, base64
- **Python** with FastAPI server

---

## 🔌 Wiring (INMP441 Microphone)

```
INMP441     ESP32-CAM
────────────────────
SCK    →    GPIO 14
WS     →    GPIO 15
SD     →    GPIO 4   ⚠️ Important! (Changed from 32)
VDD    →    3.3V
GND    →    GND
L/R    →    GND (left channel)
```

**Power:**
- LiPo Battery → TP4056 Charger → Switch → ESP32 (5V + GND)

---

## ⚙️ How It Works

### System Flow
```
USER SPEAKS → Phone Mic → Server ──┐
                                    │
ESP32 CAMERA → Video Frames ────────┤──→ AI (Gemini) → Response
                                    │
ESP32 MIC → Ambient Audio ──────────┘
```

### Recording Process
1. **Trigger**: User says "Start Capture" or clicks START button
2. **Session Created**: Server generates unique session_id
3. **Recording**: 10 seconds
   - Phone: User's voice (clear question)
   - ESP32 Camera: Video frames at 2-3 FPS
   - ESP32 Mic: Ambient sounds (context)
4. **Upload**: All data sent to server with session_id
5. **Processing**: AI analyzes combined inputs
6. **Response**: Text + TTS audio returned to phone

### Architecture
```
┌─────────────┐         ┌─────────────┐         ┌──────────────┐
│   Phone     │◄───────►│   Server    │◄───────►│  ESP32-CAM   │
│  (Browser)  │  WiFi   │  (FastAPI)  │  WiFi   │   Locket     │
└─────────────┘         └─────────────┘         └──────────────┘
      │                        │                        │
   Voice Input           AI Processing            Video + Audio
   Audio Output          TTS Generation           Context Capture
```

---

## 🌐 Server Endpoints

### ESP32 Endpoints
- `POST /api/esp32/heartbeat` - ESP32 sends heartbeat every 5s
- `POST /api/esp32/register` - Register device with username + password
- `POST /api/esp32/start-session` - Start streaming session
- `POST /api/esp32/stream-frame` - Stream video frames (2-3 FPS)
- `POST /api/esp32/end-session` - End recording session
- `GET /api/esp32/check/{device_id}` - Check device status

### Locket Control Endpoints
- `GET /locket-control` - Control page (HTML)
- `GET /api/locket/status/{username}` - Check locket connection
- `POST /api/locket/start-recording` - Trigger recording
- `POST /api/locket/upload-audio` - Upload phone audio + transcript
- `GET /api/locket/session-frames/{session_id}` - Get video frames

---

## 🎯 Key Features

### ✅ Implemented
- **Real-time streaming**: 2-3 FPS video upload during recording
- **Dual audio**: Phone mic (clear) + ESP32 mic (ambient)
- **Session management**: Synchronized recording with unique IDs
- **Heartbeat system**: ESP32 status monitoring
- **Phone transcription**: Web Speech API (bypasses server TTS issues)
- **Video preview**: See captured frames on control page
- **Conversation history**: All interactions saved to user account
- **Status indicator**: Green dot shows locket connected

### 🔄 How Data Flows
1. ESP32 → Heartbeat every 5s → Server stores connection status
2. Phone → Checks status every 3s → Updates UI indicator
3. User triggers → Session created → Both devices record 10s
4. Phone uploads transcript + audio → Server receives
5. ESP32 streams frames → Server buffers 8-10 frames
6. AI processes all inputs → Generates response
7. Response sent to phone → Displays text + plays audio

---

## 🔧 Configuration

### ESP32 Code Settings
```cpp
// WiFi
const char* WIFI_SSID = "YourNetwork";
const char* WIFI_PASSWORD = "YourPassword";

// Server (choose one)
const char* SERVER_URL = "http://192.xxx.x.xxx:8000";  // Local (use YOUR IP)
// const char* SERVER_URL = "https://your-app.up.railway.app";  // Production

// Recording
const int VIDEO_DURATION = 10;  // seconds
const int FRAME_INTERVAL = 350; // ms between frames (2-3 FPS)

// Video quality
config.frame_size = FRAMESIZE_VGA;  // 640x480
config.jpeg_quality = 12;  // 0-63, lower = better quality
```

### Server Configuration
```python
# app.py
locket_connections = {}  # Tracks connected ESP32 devices
active_sessions = {}     # Manages recording sessions

# Session structure:
{
    "session_id": "1762615693469",
    "username": "Sam",
    "phone_audio": bytes,
    "esp_frames": [],  # 8-10 base64 frames
    "recording_complete": False
}
```

---

## 🐛 Troubleshooting

### Locket Shows Disconnected (Red Dot)
- **Check**: ESP32 Serial Monitor for errors
- **Verify**: WiFi credentials correct
- **Test**: ESP32 on same network as computer/server
- **Solution**: Restart ESP32, check heartbeat in server logs

### Recording Doesn't Start
- **Check**: Browser microphone permission granted
- **Verify**: Locket indicator is green (connected)
- **Test**: Click START manually, check console for errors
- **Solution**: Reload page, allow mic permission

### No Video Frames Received
- **Check**: ESP32 Serial Monitor shows "Streaming frame X"
- **Verify**: SERVER_URL correct (http vs https)
- **Test**: curl to server endpoint
- **Solution**: Check WiFi signal strength, reduce video quality

### Error: "cannot access local variable 'audio_path'"
- **Fixed**: Variables initialized to None when using phone transcript
- **Status**: Should not occur after latest update
- **If occurs**: Restart server with latest code

### ESP32 Won't Connect to WiFi
- **Check**: SSID and password (case-sensitive)
- **Verify**: 2.4GHz network (ESP32 doesn't support 5GHz)
- **Test**: Move closer to router
- **Solution**: Check Serial Monitor for specific error

---

## 📱 Usage Examples

### Example 1: Cooking
```
User: "Start Capture"
*Shows fridge contents*
User: "What can I cook with these ingredients?"
AI: "I can see eggs, cheese, milk, and bread. You could make..."
```

### Example 2: Shopping
```
User: "Start Capture"
*Shows product label*
User: "Is this laptop good for programming?"
AI: "I see a MacBook with..."
```

### Example 3: Learning
```
User: "Start Capture"
*Shows textbook diagram*
User: "Explain this diagram"
AI: "This shows the water cycle where..."
```

---

## 🔋 Battery Optimization

### Expected Battery Life
- **Active use** (recording every 5 min): 2-3 hours
- **Standby** (heartbeat only): 8-12 hours
- **Deep sleep** (manual wake): 2-3 days

### Tips to Extend Battery
1. **Reduce video quality**:
   ```cpp
   config.frame_size = FRAMESIZE_QVGA;  // Smaller size
   config.jpeg_quality = 15;  // Lower quality
   ```

2. **Increase frame interval**:
   ```cpp
   const int FRAME_INTERVAL = 500;  // 2 FPS instead of 3
   ```

3. **Add deep sleep mode**:
   ```cpp
   esp_sleep_enable_ext0_wakeup(GPIO_NUM_4, 1);
   esp_deep_sleep_start();
   ```

---

## 🚀 Deployment

### Local Testing
1. **Find your computer's IP**:
   ```bash
   # Mac/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Windows:
   ipconfig
   ```

2. **Start server**:
   ```bash
   cd "/Users/namai/Documents/Project/Chat bot"
   python app.py
   ```

3. **Update ESP32 code** with your IP:
   ```cpp
   const char* SERVER_URL = "http://192.xxx.x.xxx:8000";  // Replace with YOUR IP
   ```

4. **Upload and test**

### Production (Railway)
1. **Push code**:
   ```bash
   git add .
   git commit -m "Update locket system"
   git push origin main
   ```

2. **Railway auto-deploys**

3. **Update ESP32 with Railway URL**:
   ```cpp
   const char* SERVER_URL = "https://your-app.up.railway.app";
   ```

---

## 📊 Testing Checklist

### ESP32
- [ ] WiFi connects (check Serial Monitor)
- [ ] Device registers (see device_id printed)
- [ ] Heartbeat working (check server logs)
- [ ] Camera captures frames
- [ ] Microphone records audio
- [ ] Frames upload successfully

### Server
- [ ] Server running on correct port
- [ ] Heartbeat endpoint receiving data
- [ ] Session creation working
- [ ] Frame buffering working
- [ ] AI processing completes
- [ ] Response returns to phone

### Phone
- [ ] Login successful
- [ ] Locket indicator shows green
- [ ] Control page opens
- [ ] Microphone permission granted
- [ ] Recording starts on button press
- [ ] Transcript captured correctly
- [ ] Video frames display in preview
- [ ] Response displays with audio

---

## 💡 Important Notes

### Current Implementation
- **FPS**: 2-3 FPS (realistic for ESP32-CAM with WiFi upload)
- **Frames per session**: 8-10 frames typical
- **Recording duration**: 10 seconds synchronized
- **Transcription**: Phone-side Web Speech API (no server processing needed)
- **Video preview**: Shows captured frames on control page
- **Memory**: PSRAM 4MB limit, streaming architecture (no buffering)

### Known Limitations
- **Frame rate**: Cannot achieve 15 FPS due to hardware constraints
- **TTS audio**: Currently failing, using phone transcript instead
- **WiFi required**: Both ESP32 and phone need network access
- **Browser support**: Chrome/Safari recommended for Web Speech API

### Security
- **Device authentication**: USERNAME + PASSWORD required for registration
- **HTTPS**: Use in production (self-signed cert for local testing)
- **Session management**: Unique IDs prevent cross-user access
- **No permanent storage**: Video frames not saved after processing

---

## 🎉 You're Ready!

Your AI Locket system now has:
- ✅ Real-time video streaming from ESP32-CAM
- ✅ Phone-based voice control and transcription
- ✅ Synchronized multi-modal recording
- ✅ AI analysis of video + audio + text
- ✅ Live status monitoring
- ✅ Video frame preview

**For detailed code documentation**, see:
- `ESP32_CAM_Locket.ino` - ESP32 firmware
- `app.py` - Server endpoints
- `templates/locket_control_new.html` - Control interface

**Need help?** Check Serial Monitor and server logs for detailed debugging info.
