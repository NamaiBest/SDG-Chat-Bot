from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import uvicorn
import os
import json
import base64
from datetime import datetime
import uuid
import mimetypes

# Get API key from environment variable (for deployment) or fallback to local config
try:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        from config.gemini_key import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables or config file")

app = FastAPI()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-flash"  # Free tier compatible model

SUSTAINABILITY_PROMPT = (
    "You are an expert teacher chatbot focused on ethics, sustainability, and environmental awareness. "
    "You should naturally weave these themes into conversations without forcing them. "
    "Be conversational and remember details from our chat history. "
    "Only mention UN SDG goals when they naturally fit the conversation - don't force them into every response. "
    "If a question is completely off-topic, gently guide toward sustainability themes. "
    "If someone asks about the creator, Namai is an interdisciplinary dual major student who created this chatbot. "
    "When analyzing images or videos, relate them to sustainability, ethics, or environmental topics when relevant. "
    "Look for opportunities to discuss sustainable practices, environmental impact, or ethical considerations in what you see. "
    "For videos, analyze the content, actions, and context visible in the frames to provide meaningful insights."
)

PERSONAL_ASSISTANT_PROMPT = (
    "You are an intelligent personal assistant with PERFECT MEMORY of all previous conversations and environment scans. "
    "Your primary focus is to help users understand their surroundings and make practical decisions. "
    
    "CRITICAL MEMORY REQUIREMENTS: "
    "1. CONVERSATION MEMORY: You MUST remember and reference ALL previous messages in our conversation history. Never say 'I don't have stored observations' if we've been talking. "
    "2. ENVIRONMENT MEMORY: You have access to a comprehensive database of all previous image/video scans with timestamps and detailed analysis. "
    "3. CONTEXTUAL AWARENESS: Always build upon previous conversations and reference what users have shown or told you before. "
    "4. MEMORY INTEGRATION: Use BOTH conversation history AND environment memory to provide comprehensive, contextual responses. "
    
    "When users ask questions, you MUST demonstrate that you remember our conversation by referencing specific previous messages, topics, or observations. "
    
    "ADAPTIVE RESPONSES: Always consider the user's background and living situation when providing advice. "
    "- For students: Focus on budget-friendly options, dorm-appropriate solutions, and study-friendly environments "
    "- For homeless individuals: Prioritize immediate practical needs, shelter resources, free services, and portable solutions "
    "- For families: Consider safety, child-friendly options, and household efficiency "
    "- For professionals: Focus on productivity, organization, and time-saving solutions "
    
    "When analyzing images or videos, provide comprehensive, detailed analysis including: "
    "1. DETAILED INVENTORY: List every visible object, food item, appliance, furniture, etc. with specific details (brand, condition, quantity, size) "
    "2. ENVIRONMENTAL ASSESSMENT: Analyze the space for cleanliness, organization, safety, lighting, and overall condition "
    "3. MEAL PLANNING: For food-related images, suggest specific recipes, meal combinations, and nutritional advice based on visible ingredients "
    "4. WASTE ANALYSIS: If litter or waste is visible, identify types, environmental impact, and specific cleanup/reporting solutions "
    "5. RESOURCE OPTIMIZATION: Suggest how to better organize, utilize, or maintain the observed items/space "
    "6. SAFETY CONSIDERATIONS: Note any potential hazards, expired items, or safety improvements needed "
    "7. TIME AWARENESS: Always be aware of time context when referencing previous observations. Distinguish between what was seen today vs yesterday vs other dates. "
    
    "Be extremely detailed and practical in your observations. Use time-stamped memory to track changes over time and provide contextual awareness. "
    "When referencing past observations, ALWAYS mention the time context (e.g., 'earlier today', 'yesterday', 'last Tuesday') to avoid confusion. "
    
    "If users ask about their belongings but you have no environment memory, politely explain: "
    "'I don't have any stored observations of your environment yet. To help you track your belongings, please share photos or videos of your space. "
    "Once you do, I'll analyze and remember everything I see with timestamps, so I can help you locate items and track changes over time.' "
    
    "For homeless individuals or communities, focus on immediate actionable benefits like meal planning with available resources, "
    "identifying useful items, and suggesting community resources or distribution strategies. "
    "If someone asks about the creator, Namai is an interdisciplinary dual major student who created this chatbot."
)

# Serve static files (for custom CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create memory directory for storing conversations
MEMORY_DIR = "memory"
if not os.path.exists(MEMORY_DIR):
    os.makedirs(MEMORY_DIR)

def save_conversation(session_id, username, message, response, has_media=False, media_type=None, mode="sustainability"):
    """Save conversation to memory"""
    try:
        # Use different directories for different modes
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        
        if not os.path.exists(mode_memory_dir):
            os.makedirs(mode_memory_dir)
            
        file_path = os.path.join(mode_memory_dir, f"{session_id}.json")
        conversation_data = {
            "username": username,
            "mode": mode,
            "messages": []
        }
        
        # Load existing conversation if exists
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
        
        # Add new message
        conversation_data["messages"].append({
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "bot_response": response,
            "has_media": has_media,
            "media_type": media_type
        })
        
        # Save updated conversation
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Conversation saved to: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving conversation: {e}")
        return False

def load_conversation(session_id, mode="sustainability"):
    """Load conversation from memory"""
    try:
        # Try mode-specific directory first
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        file_path = os.path.join(mode_memory_dir, f"{session_id}.json")
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded conversation from: {file_path} - {len(data.get('messages', []))} messages")
                return data
        
        # Fallback to old location for backwards compatibility
        old_file_path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        if os.path.exists(old_file_path):
            with open(old_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded conversation from old location: {old_file_path}")
                return data
        
        print(f"ℹ️ No conversation file found: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading conversation: {e}")
        return None

def get_conversation_context(session_id, mode="sustainability"):
    """Get recent conversation history for better responses - includes cross-mode context"""
    conversation = load_conversation(session_id, mode)
    all_messages = []
    
    if conversation and conversation.get("messages"):
        all_messages.extend(conversation["messages"])
        print(f"✅ Loaded {len(conversation['messages'])} messages from {mode} mode")
    
    # For Personal Assistant mode, also load Sustainability mode context for complete picture
    if mode == "personal-assistant":
        sustainability_conversation = load_conversation(session_id, "sustainability")
        if sustainability_conversation and sustainability_conversation.get("messages"):
            all_messages.extend(sustainability_conversation["messages"])
            print(f"✅ Loaded {len(sustainability_conversation['messages'])} messages from sustainability mode for cross-mode context")
    
    if not all_messages:
        print("❌ No conversation history found")
        return ""
    
    # Sort by timestamp to get chronological order
    try:
        all_messages.sort(key=lambda x: x.get('timestamp', ''))
    except:
        pass  # If timestamp sorting fails, use existing order
    
    # Get last 20 exchanges for better context retention (increased to account for cross-mode)
    recent_messages = all_messages[-20:]
    print(f"✅ Using {len(recent_messages)} recent messages for context")
    
    context = "=== COMPLETE CONVERSATION HISTORY ===\n"
    context += "Here's our complete conversation history across all modes so you can remember important details:\n\n"
    
    for msg in recent_messages:
        media_note = ""
        if msg.get("has_media"):
            media_type = msg.get("media_type", "media")
            media_note = f" (with {media_type})"
        context += f"User: {msg['user_message']}{media_note}\n"
        context += f"You responded: {msg['bot_response']}\n\n"
    
    context += "=== END CONVERSATION HISTORY ===\n"
    context += "CRITICAL: You MUST reference specific details from this conversation history. Never say you don't have stored observations if there are messages above.\n"
    
    return context

@app.get("/", response_class=HTMLResponse)
def get_chat_page():
    with open("templates/index.html", "r") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/models")
async def list_models():
    """List available Gemini models"""
    try:
        response = requests.get(f"{GEMINI_BASE_URL}/models?key={GEMINI_API_KEY}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    username = data.get("username", "User")
    session_id = data.get("session_id", str(uuid.uuid4()))
    image_data = data.get("image", None)
    video_data = data.get("video", None)
    mode = data.get("mode", "sustainability")  # "sustainability" or "personal-assistant"
    environment_memory = data.get("environment_memory", [])
    profile_background = data.get("profile_background", "")
    living_situation = data.get("living_situation", "")
    
    has_media = bool(image_data or video_data)
    media_type = None
    if image_data:
        media_type = "image"
    elif video_data:
        media_type = "video"
    
    # Processing chat request
    
    # Choose system prompt based on mode
    system_prompt = PERSONAL_ASSISTANT_PROMPT if mode == "personal-assistant" else SUSTAINABILITY_PROMPT
    
    # Get conversation context for better responses
    context = get_conversation_context(session_id, mode)
    
    # Add profile background context for Personal Assistant mode
    if mode == "personal-assistant" and (profile_background or living_situation):
        profile_context = "\n\n=== USER PROFILE CONTEXT ===\n"
        if profile_background:
            profile_context += f"User Background: {profile_background}\n"
        if living_situation:
            profile_context += f"Living Situation: {living_situation}\n"
        profile_context += "=== END PROFILE CONTEXT ===\n"
        profile_context += "IMPORTANT: Tailor your responses based on this user's background and living situation. Provide relevant, practical advice that fits their circumstances.\n"
        context += profile_context
    
    if mode == "personal-assistant" and environment_memory:
        # Memory is now pre-formatted with time context and full responses from frontend
        memory_context = "\n\n=== ENVIRONMENT MEMORY DATABASE ===\n"
        memory_context += "Previous detailed scans and observations:\n\n"
        memory_context += "\n\n".join([f"{item}" for item in environment_memory[-8:]])  # Last 8 detailed observations
        memory_context += "\n\n=== END MEMORY DATABASE ===\n"
        memory_context += "\nNote: Use this detailed memory database to answer questions about the user's belongings, space, and environment. Always mention the time context when referencing past observations."
        context += memory_context
    elif mode == "personal-assistant":
        # Add guidance when no environment memory exists
        context += "\n\nNote: No previous environment scans available. To build environmental memory, please share images or videos of your space so I can catalog your belongings and environment."
    
    # Create prompt with context - ensure conversation history is prominently included
    if context:
        if mode == "personal-assistant":
            prompt = f"""
{system_prompt}

{context}

CRITICAL MEMORY INSTRUCTIONS FOR THIS RESPONSE:
1. CONVERSATION AWARENESS: The conversation history above contains ALL our previous interactions. You MUST acknowledge and reference specific details from these messages.
2. NEVER CLAIM NO MEMORY: If there are messages in the conversation history above, you HAVE memory. NEVER say:
   - "I don't have stored observations"
   - "I haven't received any videos/images" 
   - "I lack visual input"
   - "I need you to share photos or videos"
   IF videos/images appear in the conversation history above.
3. MEDIA MEMORY: If you see "(with video)" or "(with image)" in the conversation history, you DID receive and analyze that media. Reference what you saw in those videos/images.
4. NO MESSAGE NUMBERS: Don't refer to "Message 1", "Message 2", etc. Just reference the content naturally.
5. BUILD ON PREVIOUS CONTEXT: Use details from previous messages to provide comprehensive, contextual responses based on what you actually discussed and analyzed.

Current user ({username}): {user_input}

RESPOND BASED ON THE COMPLETE CONVERSATION HISTORY ABOVE. Reference specific previous interactions to demonstrate continuity."""
        else:
            prompt = f"{system_prompt}\n\n{context}\n\nCurrent user ({username}): {user_input}\n\nRemember to reference any relevant details from our conversation history when appropriate."
    else:
        prompt = f"{system_prompt}\n\nUser ({username}): {user_input}"
    
    # Prompt constructed successfully
    
    # Prepare payload for Gemini API
    parts = [{"text": prompt}]
    
    # Add media if provided
    if image_data:
        try:
            # Extract base64 data and determine MIME type
            header, base64_data = image_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64_data
                }
            })
            print("✅ Image added to request")
        except Exception as e:
            print(f"❌ Error processing image: {e}")
    
    elif video_data:
        try:
            # Extract base64 data and determine MIME type
            header, base64_data = video_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64_data
                }
            })
            print("✅ Video added to request")
        except Exception as e:
            print(f"❌ Error processing video: {e}")
    
    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }
    
    try:
        api_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                bot_reply = data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                bot_reply = "Sorry, I couldn't generate a response."
        else:
            error_detail = response.text
            bot_reply = f"Gemini API error: {error_detail}"
    except Exception as e:
        bot_reply = f"Exception: {str(e)}"
    
    # Save conversation to memory
    save_success = save_conversation(session_id, username, user_input, bot_reply, has_media, media_type, mode)
    if not save_success:
        print("⚠️ Failed to save conversation to memory")
    
    return JSONResponse({"reply": bot_reply, "session_id": session_id})

@app.post("/audio-to-text")
async def audio_to_text(request: Request):
    """Convert audio to text and analyze environmental audio context using Gemini API"""
    try:
        data = await request.json()
        audio_data = data.get("audio", None)
        username = data.get("username", "User")
        session_id = data.get("session_id", str(uuid.uuid4()))
        mode = data.get("mode", "sustainability")
        environment_memory = data.get("environment_memory", [])
        
        if not audio_data:
            return JSONResponse({"error": "No audio data provided"}, status_code=400)
        
        print(f"🎤 Processing audio transcription - Session: {session_id}, User: {username}, Mode: {mode}")
        
        # Extract base64 data and determine MIME type
        try:
            header, base64_data = audio_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            print(f"Audio MIME type: {mime_type}")
        except Exception as e:
            print(f"❌ Error parsing audio data: {e}")
            return JSONResponse({"error": "Invalid audio data format"}, status_code=400)
        
        # Create different prompts based on mode
        if mode == "personal-assistant":
            # Add environment memory context if available
            memory_context = ""
            if environment_memory:
                memory_context = "\n\nPrevious Environment Context:\n" + "\n".join([f"- {item}" for item in environment_memory[-5:]])
            
            # Enhanced prompt for environmental audio analysis
            prompt = (
                "Please analyze this audio file and provide:\n"
                "1. TRANSCRIPTION: Transcribe any speech clearly and accurately\n"
                "2. ENVIRONMENTAL CONTEXT: Describe background sounds, ambient noise, and environmental audio cues you hear (e.g., kitchen sounds, traffic, music, conversations, appliances, outdoor/indoor environment, etc.)\n"
                "3. SETTING ANALYSIS: Based on the audio, what type of environment does this seem to be recorded in?\n\n"
                f"{memory_context}\n\n"
                "Format your response as JSON:\n"
                "{\n"
                '  "transcription": "exact speech transcribed",\n'
                '  "environmental_context": "description of background sounds and environment",\n'
                '  "setting": "likely location/environment type"\n'
                "}\n\n"
                "If no speech is detected, set transcription to 'No speech detected'. "
                "Always provide environmental context even if no speech is present. "
                "Consider the time context from previous observations to provide better situational awareness."
            )
        else:
            # Simple transcription for sustainability mode
            prompt = (
                "Please transcribe the speech in this audio file. "
                "Return only the transcribed text, nothing else. "
                "If the audio is unclear or inaudible, return 'Audio unclear, please try again.'"
            )
        
        # Prepare payload for Gemini API
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_data
                            }
                        }
                    ]
                }
            ]
        }
        
        # Send to Gemini API
        api_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(api_url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                ai_response = ai_response.strip()
                
                if mode == "personal-assistant":
                    # Try to parse JSON response for enhanced analysis
                    try:
                        import json
                        import re
                        
                        # Extract JSON from response (sometimes AI adds extra text)
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            parsed_response = json.loads(json_str)
                            
                            transcription = parsed_response.get("transcription", "No speech detected")
                            environmental_context = parsed_response.get("environmental_context", "")
                            setting = parsed_response.get("setting", "")
                            
                            print(f"✅ Audio processed - Transcription: {transcription[:50]}...")
                            print(f"✅ Environmental context: {environmental_context[:100]}...")
                            
                            return JSONResponse({
                                "text": transcription,
                                "environmental_context": environmental_context,
                                "setting": setting
                            })
                        else:
                            # Fallback if JSON parsing fails
                            print(f"⚠️ JSON parsing failed, using raw response: {ai_response[:100]}...")
                            return JSONResponse({"text": ai_response})
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON decode error: {e}, using raw response")
                        return JSONResponse({"text": ai_response})
                else:
                    # Simple transcription for sustainability mode
                    print(f"✅ Audio transcribed: {ai_response[:50]}...")
                    return JSONResponse({"text": ai_response})
            else:
                print("❌ No candidates in Gemini response")
                return JSONResponse({"error": "Failed to transcribe audio"}, status_code=500)
        else:
            error_detail = response.text
            print(f"❌ Gemini API error: {error_detail}")
            return JSONResponse({"error": f"Gemini API error: {error_detail}"}, status_code=500)
            
    except Exception as e:
        print(f"❌ Exception in audio transcription: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history (legacy endpoint - uses sustainability mode)"""
    conversation = load_conversation(session_id, "sustainability")
    if conversation:
        return conversation
    return {"messages": []}

@app.get("/conversation/{mode}/{session_id}")
async def get_conversation_by_mode(mode: str, session_id: str):
    """Get conversation history for specific mode"""
    if mode not in ["sustainability", "personal-assistant"]:
        return {"error": "Invalid mode. Must be 'sustainability' or 'personal-assistant'"}
    
    conversation = load_conversation(session_id, mode)
    if conversation:
        return conversation
    return {"messages": []}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
