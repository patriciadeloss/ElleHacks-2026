from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import google.genai as genai
from elevenlabs import ElevenLabs, Voice, VoiceSettings
import os
import json
from dotenv import load_dotenv
import asyncio
from tempfile import NamedTemporaryFile
import base64
#from presage import Presage

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Town Economy Game", version="1.0")

# Serve static files (HTML, CSS, JS)
app.mount("/_static", StaticFiles(directory="_static"), name="_static")

# Configure APIs
genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# Initialize ElevenLabs client using API key from .env
eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
if eleven_api_key:
    eleven_client = ElevenLabs(api_key=eleven_api_key)
    print("✅ ElevenLabs API initialized successfully")
else:
    eleven_client = None
    print("⚠️ ElevenLabs API key not found. Running in mock mode.")

# Initialize Presage (predictive typing)
#presage = Presage()

# Game state
game_state = {
    "budget": 1000,
    "happiness": 50,
    "day": 0,
    "town_state": {
        "school": "needs_pizza",
        "city_hall": "needs_repair",
        "park": "damaged",
        "dog": "lost"
    }
}

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("_static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Generate all 3 scenarios at once using Gemini AI
@app.get("/api/scenarios")
async def get_all_scenarios():
    try:
        import random
        import re
        
        # Initialize Gemini client
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        scenarios = []
        
        # Theme prompts for Gemini
        theme_prompts = [
            {
                "theme": "pizza",
                "emoji": "🍕",
                "prompt": """Create a pizza ordering scenario for a town mayor game. Include:
- A specific event (school celebration, sports team win, etc.)
- Number of people (50-100) and slices needed (2-3 per person)
- Option A: A premium pizza vendor with a creative name and compelling benefits
- Option B: A budget pizza vendor with a creative name and clear drawbacks
- Make it engaging and teach opportunity cost

Format your response EXACTLY like this:
EVENT: [describe the event in one sentence]
PEOPLE: [number]
SLICES_PER_PERSON: [number]
OPTION_A_NAME: [vendor name]
OPTION_A_DETAILS: [one sentence about quality/benefits]
OPTION_B_NAME: [vendor name]
OPTION_B_DETAILS: [one sentence about drawbacks]"""
            },
            {
                "theme": "playground",
                "emoji": "🎪",
                "prompt": """Create a playground repair scenario for a town mayor game. Include:
- A specific crisis (storm damage, safety violation, vandalism, etc.)
- Area needing repair (500-1000 sq ft)
- Option A: A premium contractor with a creative name and strong guarantees
- Option B: A budget contractor with a creative name and concerning issues
- Make it engaging and teach long-term vs short-term thinking

Format your response EXACTLY like this:
EVENT: [describe the crisis in one sentence]
AREA: [number between 500-1000]
OPTION_A_NAME: [contractor name]
OPTION_A_DETAILS: [one sentence about quality/warranty]
OPTION_B_NAME: [contractor name]
OPTION_B_DETAILS: [one sentence about problems/risks]"""
            },
            {
                "theme": "city_hall",
                "emoji": "🏛️",
                "prompt": """Create a City Hall emergency repair scenario for a town mayor game. Include:
- A specific emergency (roof leak, electrical issue, structural damage, etc.)
- Repair area needed (200-400 sq ft)
- Option A: A professional contractor with a creative name and credentials
- Option B: A sketchy handyman with a creative name and red flags
- Make it engaging and teach quality vs savings trade-offs

Format your response EXACTLY like this:
EVENT: [describe the emergency in one sentence]
AREA: [number between 200-400]
OPTION_A_NAME: [contractor name]
OPTION_A_DETAILS: [one sentence about professionalism/credentials]
OPTION_B_NAME: [contractor name]
OPTION_B_DETAILS: [one sentence about risks/concerns]"""
            }
        ]
        
        # Generate each scenario using Gemini
        for theme_data in theme_prompts:
            try:
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=theme_data["prompt"]
                )
                
                ai_text = response.text
                
                # Parse the AI response
                event_match = re.search(r'EVENT:\s*(.+)', ai_text)
                
                if theme_data["theme"] == "pizza":
                    people_match = re.search(r'PEOPLE:\s*(\d+)', ai_text)
                    slices_match = re.search(r'SLICES_PER_PERSON:\s*(\d+)', ai_text)
                    num_people = int(people_match.group(1)) if people_match else random.randint(50, 100)
                    slices_per = int(slices_match.group(1)) if slices_match else random.randint(2, 3)
                    total_units = num_people * slices_per
                    unit_label = "per slice"
                    description = f"{event_match.group(1).strip()} Need {total_units} slices for {num_people} people ({slices_per} slices each)." if event_match else f"School celebration needs {total_units} pizza slices."
                    price_a = round(random.uniform(2.50, 3.50), 2)
                    price_b = round(price_a * random.uniform(0.60, 0.75), 2)
                    
                elif theme_data["theme"] == "playground":
                    area_match = re.search(r'AREA:\s*(\d+)', ai_text)
                    total_units = int(area_match.group(1)) if area_match else random.randint(500, 1000)
                    unit_label = "per sq ft"
                    description = f"{event_match.group(1).strip()} Need to replace {total_units} sq ft of equipment." if event_match else f"Playground damage requires {total_units} sq ft repairs."
                    price_a = round(random.uniform(15, 20), 2)
                    price_b = round(price_a * random.uniform(0.50, 0.70), 2)
                    
                else:  # city_hall
                    area_match = re.search(r'AREA:\s*(\d+)', ai_text)
                    total_units = int(area_match.group(1)) if area_match else random.randint(200, 400)
                    unit_label = "per sq ft"
                    description = f"{event_match.group(1).strip()} Emergency repairs needed for {total_units} sq ft." if event_match else f"City Hall emergency requires {total_units} sq ft repairs."
                    price_a = round(random.uniform(25, 35), 2)
                    price_b = round(price_a * random.uniform(0.40, 0.60), 2)
                
                # Extract option details
                opt_a_name = re.search(r'OPTION_A_NAME:\s*(.+)', ai_text)
                opt_a_details = re.search(r'OPTION_A_DETAILS:\s*(.+)', ai_text)
                opt_b_name = re.search(r'OPTION_B_NAME:\s*(.+)', ai_text)
                opt_b_details = re.search(r'OPTION_B_DETAILS:\s*(.+)', ai_text)
                
                total_a = price_a * total_units
                total_b = price_b * total_units
                
                title_prefix = theme_data["emoji"] + " "
                if theme_data["theme"] == "pizza":
                    title_prefix += "PIZZA PARTY DECISION!"
                elif theme_data["theme"] == "playground":
                    title_prefix += "PLAYGROUND CRISIS!"
                else:
                    title_prefix += "CITY HALL EMERGENCY!"
                
                scenarios.append({
                    "theme": theme_data["theme"],
                    "title": title_prefix,
                    "description": description,
                    "optionA": {
                        "name": opt_a_name.group(1).strip() if opt_a_name else "Premium Option",
                        "price": price_a,
                        "details": opt_a_details.group(1).strip() if opt_a_details else "High quality service",
                        "total": round(total_a, 2),
                        "unit_label": unit_label
                    },
                    "optionB": {
                        "name": opt_b_name.group(1).strip() if opt_b_name else "Budget Option",
                        "price": price_b,
                        "details": opt_b_details.group(1).strip() if opt_b_details else "Lower quality, potential issues",
                        "total": round(total_b, 2),
                        "unit_label": unit_label
                    },
                    "savings": round(total_a - total_b, 2)
                })
                
            except Exception as theme_error:
                print(f"Error generating {theme_data['theme']} scenario: {theme_error}")
                # Fallback to a basic scenario if AI fails
                scenarios.append({
                    "theme": theme_data["theme"],
                    "title": f"{theme_data['emoji']} Town Decision",
                    "description": "A decision needs to be made for the town.",
                    "optionA": {"name": "Premium Choice", "price": 100, "details": "High quality", "total": 1000},
                    "optionB": {"name": "Budget Choice", "price": 60, "details": "Lower quality", "total": 600},
                    "savings": 400
                })
        
        return {"scenarios": scenarios}
        
    except Exception as e:
        print(f"Error in get_all_scenarios: {e}")
        return {"error": str(e), "scenarios": []}

# Gemini API endpoint
# Mock Gemini API endpoint (for testing)
@app.get("/api/gemini")
async def get_gemini_response(prompt: str = "Create a welcome message for a town mayor"):
    try:
        import random
        
        # Dictionary of responses based on prompt keywords
        prompt_lower = prompt.lower()
        
        # Generate random scenarios for the three themes
        if "random" in prompt_lower or "scenario" in prompt_lower:
            themes = ["pizza", "playground", "city_hall"]
            theme = random.choice(themes)
            
            if theme == "pizza":
                num_kids = random.randint(50, 100)
                slices_per_kid = random.randint(2, 3)
                total_slices = num_kids * slices_per_kid
                
                # Option A: Better quality, higher price
                price_a = round(random.uniform(2.50, 3.50), 2)
                total_a = price_a * total_slices
                
                # Option B: Lower quality, lower price (60-75% of Option A)
                price_b = round(price_a * random.uniform(0.60, 0.75), 2)
                total_b = price_b * total_slices
                
                response = f"🍕 PIZZA PARTY DECISION!\n\nThe school needs {total_slices} pizza slices for {num_kids} kids ({slices_per_kid} slices each).\n\n" \
                          f"Option A - Premium Pizza Palace:\n${price_a} per slice | Fresh ingredients, hot delivery | Total: ${total_a:.2f}\n\n" \
                          f"Option B - Budget Bargain Pizza:\n${price_b} per slice | Reheated, slower service | Total: ${total_b:.2f}\n\n" \
                          f"Savings if you choose B: ${total_a - total_b:.2f}\n\n" \
                          f"What's your choice, Mayor? Quality or savings?"
            
            elif theme == "playground":
                area_sqft = random.randint(500, 1000)
                
                # Option A: High-quality materials, long-lasting
                price_per_sqft_a = round(random.uniform(15, 20), 2)
                total_a = price_per_sqft_a * area_sqft
                
                # Option B: Cheaper materials (50-70% of Option A)
                price_per_sqft_b = round(price_per_sqft_a * random.uniform(0.50, 0.70), 2)
                total_b = price_per_sqft_b * area_sqft
                
                response = f"🎪 PLAYGROUND RENOVATION DECISION!\n\n" \
                          f"The community playground needs repairs ({area_sqft} sq ft).\n\n" \
                          f"Option A - Premium Play Systems:\n${price_per_sqft_a}/sq ft | 10-year warranty, safety certified | Total: ${total_a:.2f}\n\n" \
                          f"Option B - Standard Equipment:\n${price_per_sqft_b}/sq ft | 2-year warranty, may need repairs | Total: ${total_b:.2f}\n\n" \
                          f"Savings if you choose B: ${total_a - total_b:.2f}\n\n" \
                          f"Consider: Will cheaper equipment cost more in the long run?"
            
            else:  # city_hall
                repair_area = random.randint(200, 400)
                
                # Option A: Complete professional fix
                price_per_unit_a = round(random.uniform(25, 35), 2)
                total_a = price_per_unit_a * repair_area
                
                # Option B: Quick patch job (40-60% of Option A)
                price_per_unit_b = round(price_per_unit_a * random.uniform(0.40, 0.60), 2)
                total_b = price_per_unit_b * repair_area
                
                response = f"🏛️ CITY HALL ROOF REPAIR DECISION!\n\n" \
                          f"City Hall's roof is leaking ({repair_area} sq ft damaged).\n\n" \
                          f"Option A - Complete Professional Repair:\n${price_per_unit_a}/sq ft | 15-year guarantee, energy efficient | Total: ${total_a:.2f}\n\n" \
                          f"Option B - Quick Patch Solution:\n${price_per_unit_b}/sq ft | Temporary fix, might fail in 1-2 years | Total: ${total_b:.2f}\n\n" \
                          f"Savings if you choose B: ${total_a - total_b:.2f}\n\n" \
                          f"Think long-term: Will you end up paying twice?"
            
            return {"response": response}
        
        # Fallback responses for specific keywords
        elif "pizza" in prompt_lower:
            response = "🍕 PIZZA PARTY DECISION: School needs pizza for 67 kids. Shop A: $2 per slice. Shop B: $1.50 per slice. Which will you choose, Mayor?"
        elif "roof" in prompt_lower or "repair" in prompt_lower or "city" in prompt_lower:
            response = "🏛️ ROOF REPAIR DECISION: City Hall's roof is leaking! Option A: $1000 for permanent fix. Option B: $400 for temporary patch (might fail later). What's your choice?"
        elif "playground" in prompt_lower or "park" in prompt_lower:
            response = "🎪 PLAYGROUND DECISION: After the storm, the playground needs repairs. Option A: $800 for premium equipment. Option B: $500 for standard equipment that may break sooner."
        elif "welcome" in prompt_lower:
            response = "🎉 Welcome Mayor! Our town has 1,000 citizens and a budget of $1000. Your decisions will shape our future! Drag the cat to explore buildings."
        else:
            response = f"🤖 AI RESPONSE TO: '{prompt[:50]}...' - As Mayor, consider both budget and happiness in your decision."
        
        return {"response": response}
    except Exception as e:
        return {"response": "Welcome to the town! Let's make wise decisions together."}

# ElevenLabs endpoint
# Mock ElevenLabs endpoint
# ElevenLabs endpoint
@app.post("/api/speak")
async def text_to_speech(request: dict):
    try:
        # Get text from request body
        text_content = request.get('text', '')
        if not text_content:
            return {"error": "No text provided"}
        
        # Check if we have ElevenLabs API key
        if not eleven_client:
            # Fall back to mock mode if no API key
            return {
                "audio_url": "/_static/audio/mock.mp3",
                "text": text_content,
                "status": "mock_mode",
                "message": "ElevenLabs API key not configured. Using mock voice."
            }
        
        # Generate audio using ElevenLabs API
        print(f"🔊 Generating speech for: '{text_content[:50]}...'")
        
        # CORRECTED: Use the correct parameters for the convert method
        try:
            # First, try the correct method signature
            audio = eleven_client.text_to_speech.convert(
                text=text_content,
                voice_id="XI7yFb9lCM3MFyKaM6ob", # Penny the Cat custom voice
                model_id="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.71,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            )
        except Exception as inner_e:
            # If that fails, try alternative parameter format
            print(f"⚠️ First approach failed: {inner_e}")
            print("🔄 Trying alternative approach...")
            
            # Alternative approach using generate method
            audio = eleven_client.generate(
                text=text_content,
                voice="Adam",  # Use voice name instead of ID
                model="eleven_monolingual_v1"
            )
        
        # Save audio to a temporary file
        with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            for chunk in audio:
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        # Read the file content
        with open(temp_file_path, "rb") as f:
            audio_content = f.read()
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        # Convert to base64 for easy frontend consumption
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        return {
            "audio_url": f"data:audio/mp3;base64,{audio_base64}",
            "text": text_content,
            "status": "success",
            "message": "Voice generated successfully"
        }
        
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        # Fall back to mock mode on error
        return {
            "audio_url": "/_static/audio/mock.mp3",
            "text": text_content if 'text_content' in locals() else str(request),
            "status": "error",
            "message": f"Failed to generate voice: {str(e)}"
        }
    
# Presage predictive typing
@app.get("/api/predict")
async def get_predictions(text: str):
    try:
        # predictions = presage.predict(text)
        # return {"predictions": predictions}
        return {"predictions": []}  # Placeholder
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Game endpoints
@app.get("/api/game/state")
async def get_game_state():
    return game_state

@app.post("/api/game/decision")
async def make_decision(decision: dict):
    # Update game state based on decision
    if decision.get("type") == "buy_pizza":
        game_state["budget"] -= decision.get("cost", 0)
        game_state["happiness"] += decision.get("happiness", 0)
        game_state["day"] += 1
    
    return {"message": "Decision made", "state": game_state}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)