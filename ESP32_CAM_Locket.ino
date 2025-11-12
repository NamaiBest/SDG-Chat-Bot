/*
 * ESP32-CAM AI Locket - Simplified (Video Only)
 * 
 * Features:
 * - Video recording (10 seconds) triggered by phone
 * - HTTP communication with server
 * - Phone handles ALL audio (input via mic, output via TTS)
 * - Auto-registration with user account
 * - Heartbeat for connection status
 * 
 * Hardware: ESP32-CAM AI Thinker module
 * 
 * Required Libraries:
 * - ESP32-CAM (built-in)
 * - WiFi (built-in)
 * - HTTPClient (built-in)
 * - ArduinoJson (install from Library Manager)
 * 
 * Pin Connections:
 * - Camera: Default ESP32-CAM pins only
 * - No microphone needed (phone handles audio)
 * 
 * Setup Instructions:
 * 1. Install ESP32 board support in Arduino IDE
 * 2. Install ArduinoJson library
 * 3. Update WiFi credentials below
 * 4. Update SERVER_URL to your local IP or Railway URL
 * 5. Set your USERNAME and PASSWORD (registered account)
 * 6. Upload to ESP32-CAM
 * 7. Open locket control page on phone
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "base64.h"
#include <WebServer.h>
#include "esp_system.h"

// ============================================
// Configuration - CHANGE THESE VALUES
// ============================================

// WiFi Configuration
const char* WIFI_SSID = "Stark Tech";        // Your WiFi network name
const char* WIFI_PASSWORD = "12345678"; // Your WiFi password

// Server Configuration
// For LOCAL TESTING: Use your computer's local IP address (e.g., "https://192.xxx.x.xxx:8000")
//   - Find IP: Mac/Linux: ifconfig | grep inet, Windows: ipconfig
//   - Must be on same WiFi network as ESP32
//   - Port 8000 is FastAPI default (or use your custom port like 8080)
//   - NOTE: Using HTTPS (not HTTP) for microphone access on phones
// For PRODUCTION: Use your Railway deployment URL (e.g., "https://your-app.up.railway.app")

// CHANGE THIS BASED ON WHERE YOU WANT TO CONNECT:
// LOCAL: const char* SERVER_URL = "https://192.168.x.x:8000";
// RAILWAY: const char* SERVER_URL = "https://sdg-chat-bot-production-95ea.up.railway.app";
const char* SERVER_URL = "https://sdg-chat-bot-production-95ea.up.railway.app";  // Currently: RAILWAY

// User Authentication - Use your chat app credentials
const char* USERNAME = "Sam";             // Your registered username
const char* PASSWORD = "123456";     // Your account password

// Device will auto-generate ID from MAC address
String DEVICE_ID = "";  // Will be set automatically in setup()

// Recording configuration
const int VIDEO_DURATION = 10;  // seconds (matches phone audio duration)

// Heartbeat configuration (to show "Locket Connected" status)
unsigned long lastHeartbeat = 0;
const int HEARTBEAT_INTERVAL = 5000;  // Send heartbeat every 5 seconds

// ============================================
// CAMERA PINS (AI Thinker ESP32-CAM)
// ============================================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ============================================
// GLOBAL VARIABLES
// ============================================
WebServer server(80);  // Local web server for heartbeat
bool isRecording = false;
bool recordingTriggered = false;  // Triggered by server command

// Video frame storage (streaming mode)
#define MAX_FRAMES 5  // Keep only 5 frames in buffer for retry/smoothing
struct VideoFrame {
  uint8_t* data;
  size_t size;
};
VideoFrame videoFrames[MAX_FRAMES];
int frameCount = 0;
String currentSessionId = "";  // Track current recording session
int totalFramesSent = 0;  // Track total frames uploaded in session

unsigned long recordingStartTime = 0;

// ============================================
// FUNCTION DECLARATIONS
// ============================================
void initCamera();
void initLocalServer();
void connectWiFi();
bool registerDevice();
bool sendHeartbeat();
void checkServerCommands();
void recordVideo();
bool startRecordingSession();
bool sendFrameToServer(uint8_t* frameData, size_t frameSize, int frameNumber);
bool endRecordingSession(int totalFrames);
bool sendToServer(String sessionId);  // Deprecated - keeping for reference
String encodeBase64(uint8_t* data, size_t length);

// ============================================
// SETUP
// ============================================
void setup() {
  Serial.begin(115200);
  delay(1000);  // Give serial time to initialize
  Serial.println("\n\n=================================");
  Serial.println("ESP32-CAM AI Locket Starting...");
  Serial.println("=================================\n");
  
  // Generate unique Device ID from MAC address
  Serial.println("Step 1: Generating Device ID...");
  uint8_t mac[6];
  WiFi.macAddress(mac);  // Use WiFi.macAddress() instead of esp_read_mac()
  DEVICE_ID = "ESP32CAM_" + String(mac[0], HEX) + String(mac[1], HEX) + 
              String(mac[2], HEX) + String(mac[3], HEX) + 
              String(mac[4], HEX) + String(mac[5], HEX);
  DEVICE_ID.toUpperCase();
  Serial.println("Device ID: " + DEVICE_ID);
  
  // Initialize camera
  Serial.println("\nStep 2: Initializing camera...");
  initCamera();
  
  // Connect to WiFi
  Serial.println("\nStep 3: Connecting to WiFi...");
  connectWiFi();
  
  // Initialize local web server for heartbeat
  Serial.println("\nStep 4: Initializing local server...");
  initLocalServer();
  
  // Register device with server (using username/password)
  Serial.println("\nStep 5: Registering device with server...");
  bool registered = false;
  int retryCount = 0;
  const int maxRetries = 5;  // Try 5 times
  
  while (!registered && retryCount < maxRetries) {
    if (retryCount > 0) {
      Serial.println("Retrying registration in 10 seconds... (Attempt " + String(retryCount + 1) + "/" + String(maxRetries) + ")");
      delay(10000);  // Wait 10 seconds before retry
    }
    
    registered = registerDevice();
    
    if (registered) {
      Serial.println("✓ Device registered successfully!");
    } else {
      retryCount++;
      if (retryCount >= maxRetries) {
        Serial.println("✗ Device registration failed after " + String(maxRetries) + " attempts.");
        Serial.println("  The device will continue running and retry on next heartbeat.");
      }
    }
  }
  
  Serial.println("\n=================================");
  Serial.println("System Ready!");
  Serial.println("Waiting for phone commands...");
  Serial.println("=================================\n");
}

// ============================================
// MAIN LOOP
// ============================================
void loop() {
  // Handle local web server requests
  server.handleClient();
  
  // Send heartbeat to server periodically
  if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
    sendHeartbeat();
    lastHeartbeat = millis();
  }
  
  // Check for server commands (phone triggered recording)
  checkServerCommands();
  
  delay(100);  // Small delay to prevent CPU overload
}

// ============================================
// CAMERA INITIALIZATION
// ============================================
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // VGA quality with faster frame rate for better locket experience
  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;  // 640x480
    config.jpeg_quality = 12;  // 0-63, lower = better quality
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_VGA;  // Force VGA even without PSRAM
    config.jpeg_quality = 15;  // Slightly lower quality without PSRAM
    config.fb_count = 1;
  }
  
  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    ESP.restart();
  }
  
  Serial.println("✓ Camera initialized");
}

// ============================================
// LOCAL WEB SERVER HANDLERS (defined before initLocalServer)
// ============================================
void handleStatus() {
  String response = "{\"status\":\"online\",\"device_id\":\"" + DEVICE_ID + 
                   "\",\"recording\":" + (isRecording ? "true" : "false") + "}";
  server.send(200, "application/json", response);
}

void handleStart() {
  if (!isRecording) {
    recordingTriggered = true;
    server.send(200, "application/json", "{\"success\":true}");
  } else {
    server.send(409, "application/json", "{\"success\":false,\"error\":\"Already recording\"}");
  }
}

// ============================================
// LOCAL WEB SERVER INITIALIZATION
// ============================================
void initLocalServer() {
  Serial.println("  - Setting up /status endpoint...");
  // Simple status endpoint
  server.on("/status", HTTP_GET, handleStatus);
  
  Serial.println("  - Setting up /start endpoint...");
  // Start recording endpoint (triggered by phone/server)
  server.on("/start", HTTP_POST, handleStart);
  
  Serial.println("  - Starting server...");
  server.begin();
  Serial.println("✓ Local server started on port 80");
  Serial.print("  Access at: http://");
  Serial.println(WiFi.localIP());
}

// ============================================
// SEND HEARTBEAT TO SERVER
// ============================================
bool sendHeartbeat() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/esp32/heartbeat";
  
  // For HTTPS, use WiFiClientSecure without certificate validation
  WiFiClientSecure *client = new WiFiClientSecure;
  if(client) {
    client->setInsecure();  // Skip certificate verification
    http.begin(*client, url);
  } else {
    http.begin(url);  // Fallback to regular HTTP client
  }
  http.addHeader("Content-Type", "application/json");
  
  // Build JSON manually to avoid memory issues
  String payload = "{\"device_id\":\"" + DEVICE_ID + 
                  "\",\"status\":\"online\",\"recording\":" + 
                  (isRecording ? "true" : "false") + "}";
  
  int httpCode = http.POST(payload);
  
  if (httpCode == 200) {
    String response = http.getString();
    
    // Debug: Print response
    Serial.println("[DEBUG] Heartbeat response: " + response);
    
    // Check if server sent a command (more flexible parsing)
    if (response.indexOf("start_recording") > 0) {
      Serial.println("\n📱 Server command: START RECORDING!");
      recordingTriggered = true;
      
      // Extract session_id from response
      int sessionStart = response.indexOf("session_id") + 13;
      int sessionEnd = response.indexOf("\"", sessionStart);
      if (sessionStart > 12 && sessionEnd > sessionStart) {
        currentSessionId = response.substring(sessionStart, sessionEnd);
        Serial.println("  Session ID: " + currentSessionId);
      }
    }
    
    http.end();
    return true;
  } else {
    Serial.println("[ERROR] Heartbeat failed, code: " + String(httpCode));
  }
  
  http.end();
  return false;
}

// ============================================
// CHECK FOR SERVER COMMANDS
// ============================================
void checkServerCommands() {
  // If recording was triggered remotely
  if (recordingTriggered && !isRecording) {
    Serial.println("\n📱 Phone triggered recording!");
    recordingTriggered = false;
    recordVideo();
  }
}

// ============================================
// WIFI CONNECTION
// ============================================
void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected");
    Serial.print("  IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n✗ WiFi connection failed!");
    ESP.restart();
  }
}

// ============================================
// REGISTER DEVICE WITH SERVER
// ============================================
bool registerDevice() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    return false;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/esp32/register";
  
  // For HTTPS, use WiFiClientSecure without certificate validation
  WiFiClientSecure *client = new WiFiClientSecure;
  if(client) {
    client->setInsecure();  // Skip certificate verification
    http.begin(*client, url);
  } else {
    http.begin(url);  // Fallback to regular HTTP client
  }
  http.addHeader("Content-Type", "application/json");
  
  // Get MAC address
  String macAddress = WiFi.macAddress();
  
  // Build JSON payload manually to avoid memory issues
  String payload = "{\"device_id\":\"" + DEVICE_ID + 
                  "\",\"username\":\"" + String(USERNAME) + 
                  "\",\"password\":\"" + String(PASSWORD) +
                  "\",\"device_name\":\"ESP32-CAM Locket\"" +
                  ",\"mac_address\":\"" + macAddress + "\"}";
  
  Serial.println("Sending registration request...");
  Serial.println("Device ID: " + DEVICE_ID);
  Serial.println("Username: " + String(USERNAME));
  
  int httpCode = http.POST(payload);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("Server response: " + response);
    
    if (httpCode == 200) {
      http.end();
      return true;
    }
  } else {
    Serial.printf("Registration failed, error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
  return false;
}

// ============================================
// RECORD VIDEO ONLY (Phone handles audio) - OPTIMIZED STREAMING
// ============================================
void recordVideo() {
  isRecording = true;
  recordingStartTime = millis();
  totalFramesSent = 0;
  
  Serial.println("📹 Recording video for " + String(VIDEO_DURATION) + " seconds...");
  Serial.println("💬 Phone is capturing audio...");
  Serial.println("📊 Target: 2-3 FPS | Resolution: VGA (640x480)");
  Serial.println("🎬 STREAMING MODE: Real-time upload for fast response!");
  
  // Start recording session on server
  if (!startRecordingSession()) {
    Serial.println("✗ Failed to start recording session on server");
    isRecording = false;
    return;
  }
  
  // Stream frames with realistic timing
  camera_fb_t* fb = NULL;
  int failedFrames = 0;
  unsigned long lastCaptureTime = 0;
  const int minFrameInterval = 350;  // Minimum 350ms between frames (~2.8 FPS max)
  
  Serial.println("🚀 Starting capture loop...\n");
  
  while ((millis() - recordingStartTime) < (VIDEO_DURATION * 1000)) {
    unsigned long now = millis();
    
    // Only capture if enough time has passed
    if (now - lastCaptureTime >= minFrameInterval) {
      lastCaptureTime = now;
      
      fb = esp_camera_fb_get();
      
      if (fb) {
        Serial.print("  📸 Frame " + String(totalFramesSent + 1) + ": ");
        Serial.print("Size=" + String(fb->len / 1024) + "KB, ");
        
        // Send frame immediately to server
        bool sent = sendFrameToServer(fb->buf, fb->len, totalFramesSent);
        
        if (sent) {
          totalFramesSent++;
          float elapsed = (millis() - recordingStartTime) / 1000.0;
          float actualFPS = totalFramesSent / elapsed;
          Serial.println("✅ Sent! (FPS: " + String(actualFPS, 1) + ")");
        } else {
          failedFrames++;
          Serial.println("❌ Failed!");
        }
        
        esp_camera_fb_return(fb);
        
        // Print summary every 10 frames
        if (totalFramesSent > 0 && totalFramesSent % 10 == 0) {
          float elapsed = (millis() - recordingStartTime) / 1000.0;
          float actualFPS = totalFramesSent / elapsed;
          Serial.println("  � Progress: " + String(totalFramesSent) + " frames in " + 
                        String(elapsed, 1) + "s (Avg: " + String(actualFPS, 1) + " FPS)\n");
        }
      } else {
        Serial.println("  ⚠️ Failed to capture frame");
      }
    }
    
    // Small delay to prevent tight loop
    delay(10);
  }
  
  Serial.println("\n✓ Recording complete!");
  Serial.println("  Total frames sent: " + String(totalFramesSent) + " frames");
  Serial.println("  Failed frames: " + String(failedFrames));
  Serial.println("  Duration: " + String((millis() - recordingStartTime) / 1000.0) + " seconds");
  float avgFPS = totalFramesSent / (VIDEO_DURATION * 1.0);
  Serial.println("  Average FPS: " + String(avgFPS, 2) + " FPS");
  
  // Notify server that recording is complete
  endRecordingSession(totalFramesSent);
  
  isRecording = false;
  
  Serial.println("✅ Video uploaded! AI is now processing your request...");
  Serial.println("\n🎧 Ready for next command...\n");
}

// ============================================
// START RECORDING SESSION
// ============================================
bool startRecordingSession() {
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/esp32/start-session";
  
  // For HTTPS, use WiFiClientSecure without certificate validation
  WiFiClientSecure *client = new WiFiClientSecure;
  if(client) {
    client->setInsecure();  // Skip certificate verification
    http.begin(*client, url);
  } else {
    http.begin(url);  // Fallback to regular HTTP client
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);
  
  String payload = "{\"device_id\":\"" + DEVICE_ID + "\"}";
  
  int httpCode = http.POST(payload);
  
  if (httpCode == 200) {
    String response = http.getString();
    // Extract session_id from response (simple JSON parsing)
    int sessionStart = response.indexOf("\"session_id\":\"") + 14;
    int sessionEnd = response.indexOf("\"", sessionStart);
    currentSessionId = response.substring(sessionStart, sessionEnd);
    
    Serial.println("✅ Recording session started: " + currentSessionId);
    http.end();
    return true;
  }
  
  Serial.println("✗ Failed to start recording session");
  http.end();
  return false;
}

// ============================================
// SEND SINGLE FRAME TO SERVER
// ============================================
bool sendFrameToServer(uint8_t* frameData, size_t frameSize, int frameNumber) {
  if (WiFi.status() != WL_CONNECTED) return false;
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/esp32/stream-frame";
  
  // For HTTPS, use WiFiClientSecure without certificate validation
  WiFiClientSecure *client = new WiFiClientSecure;
  if(client) {
    client->setInsecure();  // Skip certificate verification
    http.begin(*client, url);
  } else {
    http.begin(url);  // Fallback to regular HTTP client
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(2000);  // Short timeout for streaming
  
  // Encode frame to base64
  String frameBase64 = encodeBase64(frameData, frameSize);
  
  String payload = "{\"device_id\":\"" + DEVICE_ID + 
                  "\",\"session_id\":\"" + currentSessionId +
                  "\",\"frame_number\":" + String(frameNumber) +
                  ",\"data\":\"data:image/jpeg;base64," + frameBase64 + "\"" +
                  ",\"size\":" + String(frameSize) + "}";
  
  int httpCode = http.POST(payload);
  http.end();
  
  return (httpCode == 200);
}

// ============================================
// END RECORDING SESSION
// ============================================
bool endRecordingSession(int totalFrames) {
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/esp32/end-session";
  
  // For HTTPS, use WiFiClientSecure without certificate validation
  WiFiClientSecure *client = new WiFiClientSecure;
  if(client) {
    client->setInsecure();  // Skip certificate verification
    http.begin(*client, url);
  } else {
    http.begin(url);  // Fallback to regular HTTP client
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);
  
  String payload = "{\"device_id\":\"" + DEVICE_ID + 
                  "\",\"session_id\":\"" + currentSessionId +
                  "\",\"total_frames\":" + String(totalFrames) + "}";
  
  int httpCode = http.POST(payload);
  
  if (httpCode == 200) {
    Serial.println("✅ Recording session ended. Total frames: " + String(totalFrames));
    http.end();
    return true;
  }
  
  Serial.println("✗ Failed to end recording session");
  http.end();
  return false;
}

// ============================================
// OLD BATCH SEND (DEPRECATED - KEEPING FOR REFERENCE)
// ============================================
bool sendToServer(String sessionId) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi not connected");
    return false;
  }
  
  Serial.println("📡 Uploading video frames to server...");
  
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/esp32/upload";
  
  // For HTTPS, use WiFiClientSecure without certificate validation
  WiFiClientSecure *client = new WiFiClientSecure;
  if(client) {
    client->setInsecure();  // Skip certificate verification
    http.begin(*client, url);
  } else {
    http.begin(url);  // Fallback to regular HTTP client
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(60000);  // 60 second timeout for multiple frames
  
  // Build JSON with multiple frames
  Serial.println("  📊 Encoding " + String(frameCount) + " frames to base64...");
  
  String payload = "{\"device_id\":\"" + DEVICE_ID + 
                  "\",\"session_id\":\"" + sessionId +
                  "\",\"frame_count\":" + String(frameCount) +
                  ",\"fps\":15" +
                  ",\"frames\":[";
  
  // Encode each frame
  for (int i = 0; i < frameCount; i++) {
    if (i > 0) payload += ",";
    
    String frameBase64 = encodeBase64(videoFrames[i].data, videoFrames[i].size);
    payload += "{\"data\":\"data:image/jpeg;base64," + frameBase64 + "\"";
    payload += ",\"size\":" + String(videoFrames[i].size) + "}";
    
    // Print progress every 30 frames
    if ((i + 1) % 30 == 0) {
      Serial.println("    Encoded " + String(i + 1) + "/" + String(frameCount) + " frames...");
    }
  }
  
  payload += "]}";
  
  Serial.println("  📦 Total payload size: " + String(payload.length()) + " bytes");
  Serial.println("  🚀 Sending to " + url + "...");
  
  int httpCode = http.POST(payload);
  
  if (httpCode > 0) {
    String response = http.getString();
    Serial.println("  📬 Server response code: " + String(httpCode));
    
    if (httpCode == 200) {
      Serial.println("  ✅ Server confirmed receipt of all " + String(frameCount) + " frames!");
      Serial.println("  📝 Response: " + response);
      http.end();
      return true;
    } else {
      Serial.println("  ❌ Server error response: " + response);
    }
  } else {
    Serial.printf("  ❌ HTTP error: %s\n", http.errorToString(httpCode).c_str());
  }
  
  http.end();
  return false;
}

// ============================================
// BASE64 ENCODING
// ============================================
String encodeBase64(uint8_t* data, size_t length) {
  String encoded = base64::encode(data, length);
  return encoded;
}