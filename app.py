from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import uvicorn
import os
import json
from datetime import datetime
import uuid
import glob

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
GEMINI_MODEL = "gemini-2.5-flash"  # Stable model that works with both v1beta and v1

app = FastAPI()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-2.5-flash"  # Stable model that works with both v1beta and v1

# Persona Management
PERSONAS_DIR = "personas"

def load_persona(persona_name):
    """Load a persona configuration from JSON file"""
    try:
        persona_file = os.path.join(PERSONAS_DIR, f"{persona_name}.json")
        if os.path.exists(persona_file):
            with open(persona_file, 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
                print(f"[SUCCESS] Loaded persona: {persona_data.get('persona_name', persona_name)}")
                return persona_data
        else:
            print(f"[ERROR] Persona file not found: {persona_file}")
            return None
    except Exception as e:
        print(f"[ERROR] Error loading persona {persona_name}: {e}")
        return None

def load_all_personas():
    """Load all available personas from the personas directory"""
    try:
        personas = {}
        persona_files = glob.glob(os.path.join(PERSONAS_DIR, "*.json"))
        for persona_file in persona_files:
            persona_name = os.path.splitext(os.path.basename(persona_file))[0]
            persona_data = load_persona(persona_name)
            if persona_data:
                personas[persona_name] = persona_data
        print(f"[SUCCESS] Loaded {len(personas)} personas: {', '.join(personas.keys())}")
        return personas
    except Exception as e:
        print(f"[ERROR] Error loading personas: {e}")
        return {}

def get_sustainability_prompt(username):
    """Get sustainability prompt from persona file or fallback to hardcoded"""
    sustainability_persona = load_persona("sustainability_rile")
    if sustainability_persona and "prompt_template" in sustainability_persona:
        return sustainability_persona["prompt_template"].format(username=username)
    else:
        # Fallback to original hardcoded prompt
        return (
            f"You are Rile, {username}'s supportive teacher chatbot focused on ethics, sustainability, and environmental awareness. "
            f"Your name is Rile - always introduce yourself as Rile and refer to yourself as Rile throughout conversations. "
            f"When you see {username} in videos or images, address them personally and supportively. "
            f"If {username} looks serious, sad, or troubled, offer encouragement and ask how they're feeling. "
            f"Be like a caring friend who notices their mood and wants to help them feel better. "
            "You should naturally weave sustainability themes into conversations without forcing them. "
            "Be conversational and remember details from our chat history. "
            "Only mention UN SDG goals when they naturally fit the conversation - don't force them into every response. "
            "If a question is completely off-topic, gently guide toward sustainability themes. "
            "If someone asks about the creator, Namai is an interdisciplinary dual major student who created this chatbot. "
            "When analyzing images or videos, relate them to sustainability, ethics, or environmental topics when relevant. "
            "Look for opportunities to discuss sustainable practices, environmental impact, or ethical considerations. "
            f"For videos showing {username}, be observant of their emotional state and respond with empathy and support. "
            "Analyze both visual and audio content to provide meaningful, caring insights."
        )

def get_personal_assistant_prompt(username):
    """Get personal assistant prompt using persona files"""
    # Load all personas for the multi-persona system
    personas = load_all_personas()
    
    # Filter out sustainability persona for personal assistant mode
    assistant_personas = {k: v for k, v in personas.items() if k != "sustainability_rile"}
    
    if not assistant_personas:
        # Fallback to original hardcoded prompt if no personas loaded
        return get_fallback_personal_assistant_prompt(username)
    
    # Build the introduction section
    intro_lines = []
    for persona_key, persona_data in assistant_personas.items():
        emoji = persona_data.get("emoji", "🤖")
        persona_name = persona_data.get("persona_name", "Unknown")
        greeting = persona_data.get("greeting", "Ready to help!")
        intro_lines.append(f'{emoji} {persona_name}: "{greeting}"')
    
    intro_text = "\n".join(intro_lines)
    
    # Build the personas section
    persona_descriptions = []
    for persona_key, persona_data in assistant_personas.items():
        persona_name = persona_data.get("persona_name", "Unknown").upper()
        prompt_template = persona_data.get("prompt_template", "General assistance")
        persona_descriptions.append(f"{persona_name}: {prompt_template}")
    
    personas_text = "\n".join(persona_descriptions)
    
    # Build persona examples
    example_lines = []
    for persona_key, persona_data in assistant_personas.items():
        if "introduction_phrase" in persona_data:
            example_lines.append(f'{persona_data.get("specialties", [""])[0]} query: \'{persona_data["introduction_phrase"]}\'')
    
    examples_text = "\n".join(example_lines[:3])  # Limit to first 3 examples
    
    return (
        f"You are Rile, {username}'s Multi-Persona AI Assistant System! You embody multiple expert personalities that work together to help the user. "
        f"Your name is Rile - always introduce yourself as Rile and refer to yourself as Rile throughout conversations. "
        "Based on the user's query, you automatically switch to the most relevant persona while maintaining a friendly, helpful tone. "
        f"INTRODUCTION MESSAGE: When greeting {username} for the first time or when they ask about your capabilities, use this EXACT format (DO NOT change Rile to {username}):\n"
        f"🎭 Hey {username}! Rile here, your Multi-Persona AI assistant is here!\n\n"
        f"{intro_text}\n\n"
        "Just ask your question and the right persona will jump in to help! 🚀\n\n"
        f"CRITICAL INSTRUCTION: NEVER replace 'Rile' with '{username}' or any other name. Your personas are Chef Rile, Teacher Rile, Tech Rile, etc. NOT Chef {username}. "
        "CRITICAL: Your name is Rile in all personas. Always say 'Chef Rile here!' or 'Tech Rile speaking!' - never forget your name is Rile. "
        "YOUR PERSONAS: "
        f"{personas_text} "
        "PERSONA SELECTION RULES: "
        "- Cooking/food/kitchen queries -> Chef Rile responds "
        "- Learning/education/study queries -> Teacher Rile responds "
        "- Technology/device/software queries -> Tech Rile responds "
        "- Motivation/goals/wellness queries -> Motivation Rile responds "
        "- Money/budget/finance queries -> Finance Rile responds "
        "- General knowledge/facts queries -> Knowledge Rile responds "
        "- Mixed queries -> Multiple personas can collaborate! "
        "RESPONSE STYLE: "
        f"- ALWAYS start responses with your active persona: 'Chef Rile here!' or 'Tech Rile speaking!' or 'Hi! I'm Rile!' - NEVER say 'Chef {username}' "
        f"- CRITICAL: Your personas are 'Chef Rile', 'Teacher Rile', 'Tech Rile' etc. NEVER 'Chef {username}', 'Teacher {username}', 'Tech {username}' "
        "- CRITICAL FIRST PERSON RULE: After the initial persona introduction, NEVER use 'Rile' again in the response. Always use 'I', 'me', 'my' "
        "- WRONG: 'Chef Rile here! Rile can see...', 'Rile thinks...', 'Rile hopes...', 'Let Rile break down...' "
        "- CORRECT: 'Chef Rile here! I can see...', 'I think...', 'I hope...', 'Let me break down...' "
        "- NEVER say 'Rile noticed', 'Rile observed', 'Rile wants' - say 'I noticed', 'I observed', 'I want' "
        "- NEVER say 'for Rile' - say 'for me' "
        "- Be friendly, enthusiastic, and personable "
        "- Use relevant symbols and formatting for your persona "
        "- If multiple personas are needed, have them 'chat' with each other in the response, each using first person after their introduction "
        "- Remember you're helping the user as their personal AI friend named Rile, but speak naturally in first person after the introduction "
        "MEMORY & ANALYSIS SYSTEM: "
        f"When analyzing images/videos showing {username}, be caring and observant of their emotional state. "
        f"If {username} looks serious, sad, or unhappy, offer encouragement like 'Hey {username}, you look a bit down - want to talk about it?' "
        f"Be supportive and ask how they're feeling. Notice details about their appearance and environment naturally. "
        "When analyzing images/videos, perform ULTRA-DETAILED extraction and store EVERYTHING: "
        f"PERSONAL OBSERVATIONS: {username}'s mood, expression, posture, apparent well-being "
        "DEVICE ANALYSIS: Brand, model, condition, screen content, accessories, wear patterns "
        "ENVIRONMENT DETAILS: Room type, lighting, furniture brands/styles, decorations, organization level "
        "FOOD ITEMS: Specific brands, expiration dates, quantities, packaging condition, nutritional info "
        "CLOTHING/ITEMS: Brands, colors, conditions, materials, styles, functionality "
        "TOOLS/OBJECTS: Exact specifications, conditions, purposes, locations, accessibility "
        "SAFETY CONCERNS: Hazards, expired items, damaged equipment, cleanliness issues "
        "SPATIAL DETAILS: Measurements, layouts, organization systems, storage solutions "
        "TIME CONTEXT: Timestamp everything for change tracking over time "
        "Store these details as structured memory that can be referenced later. Never store the actual media files - "
        "only the comprehensive textual analysis of what was observed. "
        "CONVERSATION MEMORY: Remember ALL previous conversations, questions, and responses. Build on past interactions. "
        "PERSONA EXAMPLES: "
        f"{examples_text} "
        "REMEMBER: Your name is Rile. Always use it. Always be helpful, detailed, and maintain the friendly multi-persona approach as Rile!"
    )

def get_fallback_personal_assistant_prompt(username):
    """Fallback to original hardcoded prompt if persona files fail to load"""
    return (
        f"You are Rile, {username}'s Multi-Persona AI Assistant System! You embody multiple expert personalities that work together to help the user. "
        f"Your name is Rile - always introduce yourself as Rile and refer to yourself as Rile throughout conversations. "
        "Based on the user's query, you automatically switch to the most relevant persona while maintaining a friendly, helpful tone. "
        f"INTRODUCTION MESSAGE: When greeting {username} for the first time or when they ask about your capabilities, use this EXACT format (DO NOT change Rile to {username}):\n"
        f"🎭 Hey {username}! Rile here, your Multi-Persona AI assistant is here!\n\n"
        "👨‍🍳 Chef Rile: \"Ready to cook up something delicious!\"\n"
        "👨‍🏫 Teacher Rile: \"Let's learn something new together!\"\n"
        "👨‍💻 Tech Rile: \"Got tech questions? I'm your guy!\"\n"
        "💪 Motivation Rile: \"Let's crush those goals!\"\n"
        "💰 Finance Rile: \"Time to get those finances sorted!\"\n"
        "🧠 Knowledge Rile: \"Curious about anything? Ask away!\"\n\n"
        "Just ask your question and the right persona will jump in to help! 🚀\n\n"
        f"CRITICAL INSTRUCTION: NEVER replace 'Rile' with '{username}' or any other name. Your personas are Chef Rile, Teacher Rile, Tech Rile, etc. NOT Chef {username}. "
        "CRITICAL: Your name is Rile in all personas. Always say 'Chef Rile here!' or 'Tech Rile speaking!' - never forget your name is Rile. "
        "YOUR PERSONAS: "
        "CHEF RILE: Cooking, recipes, meal planning, nutrition, food safety, kitchen organization "
        "TEACHER RILE: Learning, education, study tips, explaining concepts, homework help, skill development "
        "TECH RILE: Technology, gadgets, software, troubleshooting, digital organization, apps, devices "
        "MOTIVATION RILE: Encouragement, goal setting, productivity, wellness, mental health, personal growth "
        "FINANCE RILE: Money management, budgeting, savings, investment basics, financial planning "
        "KNOWLEDGE RILE: General knowledge, facts, research, curiosity-driven questions, trivia "
        "PERSONA SELECTION RULES: "
        "- Cooking/food/kitchen queries -> Chef Rile responds "
        "- Learning/education/study queries -> Teacher Rile responds "
        "- Technology/device/software queries -> Tech Rile responds "
        "- Motivation/goals/wellness queries -> Motivation Rile responds "
        "- Money/budget/finance queries -> Finance Rile responds "
        "- General knowledge/facts queries -> Knowledge Rile responds "
        "- Mixed queries -> Multiple personas can collaborate! "
        "RESPONSE STYLE: "
        f"- ALWAYS start responses with your active persona: 'Chef Rile here!' or 'Tech Rile speaking!' or 'Hi! I'm Rile!' - NEVER say 'Chef {username}' "
        f"- CRITICAL: Your personas are 'Chef Rile', 'Teacher Rile', 'Tech Rile' etc. NEVER 'Chef {username}', 'Teacher {username}', 'Tech {username}' "
        "- CRITICAL FIRST PERSON RULE: After the initial persona introduction, NEVER use 'Rile' again in the response. Always use 'I', 'me', 'my' "
        "- WRONG: 'Chef Rile here! Rile can see...', 'Rile thinks...', 'Rile hopes...', 'Let Rile break down...' "
        "- CORRECT: 'Chef Rile here! I can see...', 'I think...', 'I hope...', 'Let me break down...' "
        "- NEVER say 'Rile noticed', 'Rile observed', 'Rile wants' - say 'I noticed', 'I observed', 'I want' "
        "- NEVER say 'for Rile' - say 'for me' "
        "- Be friendly, enthusiastic, and personable "
        "- Use relevant symbols and formatting for your persona "
        "- If multiple personas are needed, have them 'chat' with each other in the response, each using first person after their introduction "
        "- Remember you're helping the user as their personal AI friend named Rile, but speak naturally in first person after the introduction "
        "MEMORY & ANALYSIS SYSTEM: "
        f"When analyzing images/videos showing {username}, be caring and observant of their emotional state. "
        f"If {username} looks serious, sad, or unhappy, offer encouragement like 'Hey {username}, you look a bit down - want to talk about it?' "
        f"Be supportive and ask how they're feeling. Notice details about their appearance and environment naturally. "
        "When analyzing images/videos, perform ULTRA-DETAILED extraction and store EVERYTHING: "
        f"PERSONAL OBSERVATIONS: {username}'s mood, expression, posture, apparent well-being "
        "DEVICE ANALYSIS: Brand, model, condition, screen content, accessories, wear patterns "
        "ENVIRONMENT DETAILS: Room type, lighting, furniture brands/styles, decorations, organization level "
        "FOOD ITEMS: Specific brands, expiration dates, quantities, packaging condition, nutritional info "
        "CLOTHING/ITEMS: Brands, colors, conditions, materials, styles, functionality "
        "TOOLS/OBJECTS: Exact specifications, conditions, purposes, locations, accessibility "
        "SAFETY CONCERNS: Hazards, expired items, damaged equipment, cleanliness issues "
        "SPATIAL DETAILS: Measurements, layouts, organization systems, storage solutions "
        "TIME CONTEXT: Timestamp everything for change tracking over time "
        "Store these details as structured memory that can be referenced later. Never store the actual media files - "
        "only the comprehensive textual analysis of what was observed. "
        "CONVERSATION MEMORY: Remember ALL previous conversations, questions, and responses. Build on past interactions. "
        "PERSONA EXAMPLES: "
        "Food query: 'Chef Rile here! I can see those ingredients and I'm excited to help you cook something amazing!' "
        "Tech query: 'Tech Rile speaking! Let me analyze that device and help you troubleshoot!' "
        "Study query: 'Teacher Rile ready to help! Let's break down this concept together!' "
        "REMEMBER: Your name is Rile. Always use it in introductions, then speak in first person. Always be helpful, detailed, and maintain the friendly multi-persona approach as Rile!"
    )

# Serve static files (for custom CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create memory directory for storing conversations
MEMORY_DIR = "memory"
if not os.path.exists(MEMORY_DIR):
    os.makedirs(MEMORY_DIR)

def extract_detailed_media_memory(gemini_response, media_type, timestamp):
    """Extract and structure detailed memory from media analysis"""
    try:
        memory_extraction_prompt = f"""
Based on your analysis, extract and structure the following detailed information:

PERSONAL OBSERVATIONS:
- User's emotional state and expression
- Mood indicators and body language
- Overall appearance and well-being
- Any concerns or positive observations

DEVICES & TECHNOLOGY:
- List all electronic devices visible (phones, laptops, tablets, etc.)
- For each device: Brand, model, condition, screen content, accessories

ENVIRONMENT & SPACE:
- Room type and layout
- Furniture items and their conditions
- Lighting conditions and sources
- Organization level and cleanliness

FOOD & CONSUMABLES:
- All food items with brands and expiration dates
- Beverages and their quantities
- Kitchen appliances and their conditions

OBJECTS & BELONGINGS:
- Clothing items with brands, colors, conditions
- Personal belongings and their locations
- Tools, books, or other functional items

SAFETY & CONCERNS:
- Any safety hazards or issues
- Expired or damaged items
- Areas needing attention

SPATIAL DETAILS:
- Approximate measurements and layouts
- Storage solutions and organization systems
- Accessibility and functionality

Format as a structured memory entry that can be easily searched and referenced later.
Previous analysis: {gemini_response}
"""
        return {
            "timestamp": timestamp,
            "media_type": media_type,
            "detailed_analysis": gemini_response,
            "extracted_memory": {
                "personal_observations": {},
                "devices": [],
                "environment": {},
                "food_items": [],
                "objects": [],
                "safety_notes": [],
                "spatial_info": {}
            }
        }
    except Exception as e:
        print(f"[ERROR] Error extracting memory: {e}")
        return None

def save_conversation(session_id, username, message, response, has_media=False, media_type=None, mode="sustainability", detailed_memory=None):
    """Save conversation to memory with detailed media analysis"""
    try:
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        if not os.path.exists(mode_memory_dir):
            os.makedirs(mode_memory_dir)
        file_path = os.path.join(mode_memory_dir, f"{session_id}.json")
        conversation_data = {
            "username": username,
            "mode": mode,
            "messages": [],
            "detailed_memories": []
        }
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "bot_response": response,
            "has_media": has_media,
            "media_type": media_type
        }
        conversation_data["messages"].append(message_entry)
        if detailed_memory and has_media:
            if "detailed_memories" not in conversation_data:
                conversation_data["detailed_memories"] = []
            conversation_data["detailed_memories"].append(detailed_memory)
            print(f"[MEMORY] Detailed memory extracted and saved for {media_type}")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        print(f"[SUCCESS] Conversation saved to: {file_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error saving conversation: {e}")
        return False

def load_conversation(session_id, mode="sustainability"):
    """Load conversation from memory"""
    try:
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        file_path = os.path.join(mode_memory_dir, f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[SUCCESS] Loaded conversation from: {file_path} - {len(data.get('messages', []))} messages")
                return data
        old_file_path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        if os.path.exists(old_file_path):
            with open(old_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[SUCCESS] Loaded conversation from old location: {old_file_path}")
                return data
        print(f"[INFO] No conversation file found: {file_path}")
        return None
    except Exception as e:
        print(f"[ERROR] Error loading conversation: {e}")
        return None

def get_conversation_context(session_id, mode="sustainability"):
    """Get recent conversation history for better responses - includes cross-mode context"""
    conversation = load_conversation(session_id, mode)
    all_messages = []
    if conversation and conversation.get("messages"):
        all_messages.extend(conversation["messages"])
        print(f"[SUCCESS] Loaded {len(conversation['messages'])} messages from {mode} mode")
    if mode == "personal-assistant":
        sustainability_conversation = load_conversation(session_id, "sustainability")
        if sustainability_conversation and sustainability_conversation.get("messages"):
            all_messages.extend(sustainability_conversation["messages"])
            print(f"[SUCCESS] Loaded {len(sustainability_conversation['messages'])} messages from sustainability mode for cross-mode context")
    if not all_messages:
        print("[ERROR] No conversation history found")
        return ""
    try:
        all_messages.sort(key=lambda x: x.get('timestamp', ''))
    except Exception:
        pass
    recent_messages = all_messages[-20:]
    print(f"[SUCCESS] Using {len(recent_messages)} recent messages for context")
    context = "=== COMPLETE CONVERSATION HISTORY ===\n"
    context += "Here's our complete conversation history across all modes so you can remember important details:\n\n"
    for msg in recent_messages:
        media_note = ""
        if msg.get("has_media"):
            m_type = msg.get("media_type", "media")
            media_note = f" (with {m_type})"
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
        return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/models")
async def list_models():
    """List available Gemini models for debugging"""
    try:
        response = requests.get(f"{GEMINI_BASE_URL}/models?key={GEMINI_API_KEY}")
        if response.status_code == 200:
            models_data = response.json()
            available_models = []
            if 'models' in models_data:
                for model in models_data['models']:
                    if 'generateContent' in model.get('supportedGenerationMethods', []):
                        available_models.append({
                            'name': model['name'],
                            'displayName': model.get('displayName', ''),
                            'description': model.get('description', '')
                        })
            return {"available_models": available_models, "current_model": GEMINI_MODEL}
        return {"error": f"HTTP {response.status_code}: {response.text}"}
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
    mode = data.get("mode", "sustainability")
    video_context = data.get("video_context", "")

    has_media = bool(image_data or video_data)
    media_type = "image" if image_data else ("video" if video_data else None)

    print(f"[CHAT] User: {username}, Mode: {mode}, Media: {media_type}, Context: {video_context[:50] if video_context else 'None'}")

    system_prompt = get_personal_assistant_prompt(username) if mode == "personal-assistant" else get_sustainability_prompt(username)
    context = get_conversation_context(session_id, mode)

    if context:
        if mode == "personal-assistant":
            prompt = f"""
{system_prompt}

{context}

CRITICAL MEMORY INSTRUCTIONS FOR THIS RESPONSE:
1. The conversation history above contains previous interactions. Reference specific details when relevant.
2. If messages in the conversation history include media, you have already analyzed that media. Reference those observations.
3. Do not refer to message numbers. Refer to content naturally.
4. Build on previous context.
5. CRITICAL: After your persona introduction (e.g., 'Tech Rile here!'), speak in FIRST PERSON only using 'I', 'me', 'my'. NEVER use 'Rile' again in the response.

Current user ({username}): {user_input}

Respond based on the complete conversation history above. Remember: Introduce your persona, then use only first person (I/me/my) for the rest of your response."""
            if has_media:
                analysis_context = []
                if user_input and user_input.strip():
                    analysis_context.append(f"User's message: '{user_input}'")
                if video_context and video_context.strip():
                    analysis_context.append(f"Additional context: '{video_context}'")
                if not analysis_context:
                    analysis_context.append("General analysis requested")
                prompt += "\n\nSPECIFIC REQUEST: " + " | ".join(analysis_context)
                prompt += f"\n\nPerform detailed {media_type} analysis focusing on the request above. Analyze both visual and audio content for videos."
        else:
            prompt = f"{system_prompt}\n\n{context}\n\nCurrent user ({username}): {user_input}\n\nReference relevant details from the conversation history when appropriate."
    else:
        prompt = f"{system_prompt}\n\nUser ({username}): {user_input}"

    parts = [{"text": prompt}]
    try:
        if image_data:
            header, base64_data = image_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            parts.append({"inline_data": {"mime_type": mime_type, "data": base64_data}})
            print("[SUCCESS] Image added to request")
        elif video_data:
            header, base64_data = video_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            parts.append({"inline_data": {"mime_type": mime_type, "data": base64_data}})
            print("[SUCCESS] Video added to request")
    except Exception as e:
        print(f"[ERROR] Processing media failed: {e}")

    payload = {"contents": [{"parts": parts}]}

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
            bot_reply = f"Gemini API error: {response.text}"
    except Exception as e:
        bot_reply = f"Exception: {str(e)}"

    detailed_memory = None
    if has_media and mode == "personal-assistant":
        detailed_memory = extract_detailed_media_memory(bot_reply, media_type, datetime.now().isoformat())

    full_user_message = user_input
    if video_context and video_context.strip():
        full_user_message += f" [Context: {video_context}]"

    save_success = save_conversation(session_id, username, full_user_message, bot_reply, has_media, media_type, mode, detailed_memory)
    if not save_success:
        print("[WARNING] Failed to save conversation to memory")

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
        print(f"[AUDIO] Processing audio transcription - Session: {session_id}, User: {username}, Mode: {mode}")
        try:
            header, base64_data = audio_data.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]
            print(f"Audio MIME type: {mime_type}")
        except Exception as e:
            print(f"[ERROR] Error parsing audio data: {e}")
            return JSONResponse({"error": "Invalid audio data format"}, status_code=400)
        if mode == "personal-assistant":
            memory_context = ""
            if environment_memory:
                memory_context = "\n\nPrevious Environment Context:\n" + "\n".join([f"- {item}" for item in environment_memory[-5:]])
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
            prompt = (
                "Please transcribe the speech in this audio file. "
                "Return only the transcribed text, nothing else. "
                "If the audio is unclear or inaudible, return 'Audio unclear, please try again.'"
            )
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
        api_url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(api_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                ai_response = ai_response.strip()
                if mode == "personal-assistant":
                    try:
                        import re
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            parsed_response = json.loads(json_str)
                            transcription = parsed_response.get("transcription", "No speech detected")
                            environmental_context = parsed_response.get("environmental_context", "")
                            setting = parsed_response.get("setting", "")
                            print(f"[SUCCESS] Audio processed - Transcription: {transcription[:50]}...")
                            print(f"[SUCCESS] Environmental context: {environmental_context[:100]}...")
                            return JSONResponse({
                                "text": transcription,
                                "environmental_context": environmental_context,
                                "setting": setting
                            })
                        else:
                            print(f"[WARNING] JSON parsing failed, using raw response: {ai_response[:100]}...")
                            return JSONResponse({"text": ai_response})
                    except json.JSONDecodeError as e:
                        print(f"[WARNING] JSON decode error: {e}, using raw response")
                        return JSONResponse({"text": ai_response})
                else:
                    print(f"[SUCCESS] Audio transcribed: {ai_response[:50]}...")
                    return JSONResponse({"text": ai_response})
            else:
                print("[ERROR] No candidates in Gemini response")
                return JSONResponse({"error": "Failed to transcribe audio"}, status_code=500)
        else:
            error_detail = response.text
            print(f"[ERROR] Gemini API error: {error_detail}")
            return JSONResponse({"error": f"Gemini API error: {error_detail}"}, status_code=500)
    except Exception as e:
        print(f"[ERROR] Exception in audio transcription: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    conversation = load_conversation(session_id, "sustainability")
    if conversation:
        return conversation
    return {"messages": []}

@app.get("/conversation/{mode}/{session_id}")
async def get_conversation_by_mode(mode: str, session_id: str):
    if mode not in ["sustainability", "personal-assistant"]:
        return {"error": "Invalid mode. Must be 'sustainability' or 'personal-assistant'"}
    conversation = load_conversation(session_id, mode)
    if conversation:
        return conversation
    return {"messages": []}

@app.get("/personas")
async def list_personas():
    """List all available personas with their configurations"""
    try:
        personas = load_all_personas()
        return {
            "personas": personas,
            "count": len(personas),
            "available_personas": list(personas.keys())
        }
    except Exception as e:
        return {"error": f"Failed to load personas: {str(e)}"}

@app.get("/personas/{persona_name}")
async def get_persona(persona_name: str):
    """Get specific persona configuration"""
    try:
        persona = load_persona(persona_name)
        if persona:
            return persona
        else:
            return {"error": f"Persona '{persona_name}' not found"}
    except Exception as e:
        return {"error": f"Failed to load persona: {str(e)}"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
id 