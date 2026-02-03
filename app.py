from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import google.genai as genai
from elevenlabs import ElevenLabs, Voice, VoiceSettings
import os
import json
import random
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
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    "budget": 2400,
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
    with open("static/titlepage.html", "r", encoding="utf-8") as f:
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
                "prompt": """Create a pizza ordering scenario for a town mayor game with 5 to 7 sentences. Include:
                - A specific event (school celebration, sports team win, etc.)
                - Number of people (50-100) and slices needed (2-3 per person)
                - Option A: A premium pizza vendor with a creative name and compelling benefits
                - Option B: A budget pizza vendor with a creative name and clear drawbacks
                - Make it engaging and teach opportunity cost

                Format your response EXACTLY like this:
                EVENT: [describe the event in one sentence]
                PEOPLE: [number in one sentence]
                SLICES_PER_PERSON: [number in another sentence]
                OPTION_A_DETAILS: [one sentence about first vendor name and quality/benefits]
                OPTION_B_DETAILS: [one sentence about second vendor name and drawbacks]"""
            },
            {
                "theme": "city_hall",
                "emoji": "🏛️",
                "prompt": """Create a City Hall emergency repair scenario for a town mayor game with 5 to 7 sentences. Include:
                - A specific emergency (roof leak, electrical issue, structural damage, etc.)
                - Repair area needed (200-400 sq ft)
                - Option A: A professional contractor with a creative name and credentials
                - Option B: A sketchy handyman with a creative name and red flags
                - Make it engaging and teach quality vs savings trade-offs

                Format your response EXACTLY like this:
                EVENT: [describe the emergency in one sentence]
                AREA: [number between 200-400] 
                OPTION_A_DETAILS: [one sentence about contractor A and professionalism/credentials]
                OPTION_B_DETAILS: [one sentence about contractor B and risks/concerns]"""
            },
            {
                "theme": "grandma_vs_playground",
                "emoji": "👵",
                "prompt": """Create a scenario where the player chooses between playground upgrade and helping grandma. Include:
                - Playground upgrade: new swings and equipment for kids
                - Help grandma find her lost dog
                - Budget only allows one choice
                - Make it kid-friendly and teach prioritization.

                Format your response EXACTLY like this:
                OPTION_A_DETAILS: [one sentence about playground and kids wanting new swings]
                OPTION_B_DETAILS: [one sentence about grandma and her lost dog]"""
            }
        ]
        
        # Generate each scenario using Gemini
        # Use current budget to scale prices so scenarios 1 and 2 remain affordable together
        current_budget = game_state.get("budget", 2400)
        # Allocate up to 45% of budget for each of the first two scenarios (worst-case each)
        max_share_first_two = 0.45
        for idx, theme_data in enumerate(theme_prompts):
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
                    event_text = event_match.group(1).strip() if event_match else "A school celebration"
                    base_description = f"{event_text} We need {total_units} pizza slices for {num_people} people."
                    # Compute price bounds so total does not exceed a safe share of budget
                    max_total_for_pizza = max(100, int(current_budget * max_share_first_two))
                    # price per slice to keep total <= max_total_for_pizza
                    max_price_per_slice = max_total_for_pizza / max(1, total_units)
                    # Cap realistic pizza price at $4 per slice
                    allowed_max_price = min(max_price_per_slice, 4.0)
                    # Ensure lower bound does not exceed upper bound
                    lower_bound = max(0.5, allowed_max_price * 0.5)
                    if lower_bound > allowed_max_price:
                        lower_bound = allowed_max_price
                    price_a = round(random.uniform(lower_bound, allowed_max_price), 2)
                    price_b = round(price_a * random.uniform(0.60, 0.85), 2)
                    total_a = round(price_a * total_units, 2)
                    total_b = round(price_b * total_units, 2)
                    description = f"{base_description} Option A costs ${price_a} per slice. Option B costs ${price_b} per slice. What's your choice, Mayor?"
                    
                elif theme_data["theme"] == "city_hall":
                    area_match = re.search(r'AREA:\s*(\d+)', ai_text)
                    total_units = int(area_match.group(1)) if area_match else random.randint(200, 400)
                    unit_label = "per sq ft"
                    event_text = event_match.group(1).strip() if event_match else "City Hall has an emergency"
                    base_description = f"{event_text} We need to fix {total_units} square feet of damage right away."
                    # For city_hall scenario, make it expensive so scenario 3 has just 200-400 left
                    # Scenario 1 takes ~45% of budget, scenario 2 should take ~50-60% to leave only 200-400 for scenario 3
                    spent_so_far = current_budget * max_share_first_two
                    target_for_city_hall = current_budget - spent_so_far - random.randint(200, 400)
                    target_for_city_hall = max(1500, min(target_for_city_hall, current_budget * 0.60))
                    # Create two options with this budget in mind
                    total_a = round(target_for_city_hall * random.uniform(0.85, 1.0), 2)
                    total_b = round(total_a * random.uniform(0.50, 0.75), 2)
                    price_a = round(total_a / max(1, total_units), 2)
                    price_b = round(total_b / max(1, total_units), 2)
                    description = f"{base_description} Option A costs ${price_a} per square foot. Option B costs ${price_b} per square foot. What will you do, Mayor?"
                
                else:  # grandma_vs_playground
                    unit_label = "flat cost"
                    base_description = "Two important things need money right now."
                    # Price these competing needs to consume most/all remaining budget
                    # Should have ~200-400 left from scenarios 1 and 2
                    remaining_budget = max(200, int(current_budget * 0.08))
                    # Option A: Playground upgrade (larger)
                    total_a = round(random.uniform(remaining_budget * 0.5, remaining_budget * 0.75), 2)
                    # Option B: Help grandma (smaller but similar range so both are tempting)
                    total_b = round(random.uniform(remaining_budget * 0.55, remaining_budget * 0.85), 2)
                    price_a = total_a
                    price_b = total_b
                    description = f"{base_description} Option A: Playground upgrade with new swings costs ${price_a:.2f}. Option B: Helping grandma find her lost dog costs ${price_b:.2f}. Budget for only one. Mayor, which will it be?"
                
                # Extract option details
                opt_a_name = re.search(r'OPTION_A_NAME:\s*(.+)', ai_text)
                opt_a_details = re.search(r'OPTION_A_DETAILS:\s*(.+)', ai_text)
                opt_b_name = re.search(r'OPTION_B_NAME:\s*(.+)', ai_text)
                opt_b_details = re.search(r'OPTION_B_DETAILS:\s*(.+)', ai_text)
                
                title_prefix = theme_data["emoji"] + " "
                if theme_data["theme"] == "pizza":
                    title_prefix += "PIZZA PARTY DECISION!"
                elif theme_data["theme"] == "city_hall":
                    title_prefix += "CITY HALL EMERGENCY!"
                else:  # grandma_vs_playground
                    title_prefix += "A TOUGH CHOICE!"
                
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
                pizza_slices_needed = random.randint(40, 60)
                pizza_price_a = round(random.uniform(1.5, 2.0), 2)  # Kid-friendly prices
                pizza_price_b = round(random.uniform(1.0, 1.5), 2)
                total_a = pizza_price_a * pizza_slices_needed
                total_b = pizza_price_b * pizza_slices_needed
                
                response = f"The townhall is hosting a pizza party and {pizza_slices_needed} kids want pizza! " \
                          f"Option A costs ${pizza_price_a} per slice. " \
                          f"Option B costs ${pizza_price_b} per slice. " \
                          f"What's your choice, Mayor?"
            
            elif theme == "playground":
                area_sqft = random.randint(500, 1000)
                
                # Option A: High-quality materials, long-lasting
                price_per_sqft_a = round(random.uniform(15, 20), 2)
                total_a = price_per_sqft_a * area_sqft
                
                # Option B: Cheaper materials (50-70% of Option A)
                price_per_sqft_b = round(price_per_sqft_a * random.uniform(0.50, 0.70), 2)
                total_b = price_per_sqft_b * area_sqft
                
                response = f"The playground needs repairs! We need to fix {area_sqft} square feet of equipment. " \
                          f"Option A costs ${price_per_sqft_a} per square foot. " \
                          f"Option B costs ${price_per_sqft_b} per square foot. " \
                          f"Which one do you pick?"
            
            else:  # city_hall
                repair_area = random.randint(200, 400)
                
                # Option A: Complete professional fix
                price_per_unit_a = round(random.uniform(25, 35), 2)
                total_a = price_per_unit_a * repair_area
                
                # Option B: Quick patch job (40-60% of Option A)
                price_per_unit_b = round(price_per_unit_a * random.uniform(0.40, 0.60), 2)
                total_b = price_per_unit_b * repair_area
                
                response = f"City Hall's roof is leaking and we need to repair {repair_area} square feet. " \
                          f"Option A costs ${price_per_unit_a} per square foot. " \
                          f"Option B costs ${price_per_unit_b} per square foot. " \
                          f"What will you do, Mayor?"
            
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
                "audio_url": "/static/audio/mock.mp3", 
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
            "audio_url": "/static/audio/mock.mp3", 
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
    option = decision.get("option")  # A or B
    cost = decision.get("cost", 0)
    
    # Deduct cost from budget
    game_state["budget"] -= cost
    game_state["budget"] = max(0, game_state["budget"])  # Don't go below 0
    
    # Update happiness based on option choice
    # Premium option (A) increases happiness more
    if option == "A":
        game_state["happiness"] += random.randint(5, 15)
    else:  # Budget option (B)
        game_state["happiness"] += random.randint(2, 8)
    
    game_state["happiness"] = min(100, game_state["happiness"])  # Cap at 100
    game_state["day"] += 1
    
    return {"message": "Decision recorded", "state": game_state}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
