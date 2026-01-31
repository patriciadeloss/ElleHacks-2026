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
import random
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Town Economy Game", version="1.0")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ Gemini API initialized successfully")
    except Exception as e:
        print(f"❌ Gemini initialization error: {e}")
        genai_client = None
else:
    genai_client = None
    print("⚠️ Gemini API key not found. Running in mock mode.")

# Initialize ElevenLabs
eleven_api_key = os.getenv("ELEVENLABS_API_KEY")
if eleven_api_key:
    eleven_client = ElevenLabs(api_key=eleven_api_key)
    print("✅ ElevenLabs API initialized successfully")
else:
    eleven_client = None
    print("⚠️ ElevenLabs API key not found. Running in mock mode.")

# Game state with your specific buildings
game_state = {
    "budget": 1000,
    "happiness": 50,
    "day": 0,
    "scenario_day": 1,
    "town_state": {
        "townhall": {"status": "needs_repair", "roof_damage": "leaking"},
        "pizza_area": {"status": "ready_for_party", "pizza_needed": True},
        "townhouse": {"status": "new_families_moving_in", "families_count": 3},
        "playground": {"status": "needs_upgrade", "equipment_broken": True}
    },
    "decisions": [],
    "previous_choices": {},
    "game_phase": "introduction"  # introduction, exploration, day1, day2, day3, final
}

# People database for exploration - matching your buildings
town_people = [
    {"name": "Mayor Mouse", "building": "townhall", "description": "The helpful assistant mayor who loves cheese"},
    {"name": "Town Clerk", "building": "townhall", "description": "Keeps track of all town papers and records"},
    {"name": "Pizza Chef", "building": "pizza_area", "description": "Makes the cheesiest, most delicious pizzas in town"},
    {"name": "Hungry Kid", "building": "pizza_area", "description": "Always ready for a pizza party with friends"},
    {"name": "New Family", "building": "townhouse", "description": "Just moved in and needs help settling"},
    {"name": "Friendly Neighbor", "building": "townhouse", "description": "Knows everyone and helps new people feel welcome"},
    {"name": "Playful Pup", "building": "playground", "description": "Loves chasing balls and playing fetch"},
    {"name": "Swings Expert", "building": "playground", "description": "Can swing higher than anyone else!"}
]

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# Gemini API endpoint - Enhanced with dynamic scenarios
@app.get("/api/gemini/scenario")
async def get_gemini_scenario(
    phase: str = None,
    building: str = None,
    person: str = None,
    previous_decision: str = None
):
    try:
        # If no specific phase provided, use current game phase
        if not phase:
            phase = game_state["game_phase"]
        
        # Generate dynamic numbers for scenarios
        pizza_slices_needed = random.randint(40, 60)
        pizza_price_a = round(random.uniform(1.5, 2.0), 2)  # Kid-friendly prices
        pizza_price_b = round(random.uniform(1.0, 1.5), 2)
        roof_cost_quality = random.randint(600, 800)
        roof_cost_cheap = random.randint(200, 350)
        playground_upgrade_cost = random.randint(300, 500)
        townhouse_welcome_cost = random.randint(150, 250)
        
        # Build creative prompts for Gemini with kid-friendly language
        if phase == "introduction":
            prompt = f"""Create a fun welcome message for Mayor Cat, who just became mayor of Kitty Town!
            The town has 1,000 animal citizens. Starting budget: ${game_state['budget']}, starting happiness: {game_state['happiness']}%.
            Tell Mayor Cat they can drag their character to visit different places around town.
            Make it exciting and friendly for kids aged 7-12. Use animal sounds and fun words!
            The message should be about 6-9 sentences long. Start with a big welcome, then explain the game.
            Talk about the four main places: townhall, pizza area, townhouse, and playground.
            End with encouragement to start exploring. Keep sentences short and easy to read."""

        elif phase == "exploration":
            person_desc = ""
            if person:
                for p in town_people:
                    if p["name"] == person:
                        person_desc = p["description"]
                        break
            
            if person:
                prompt = f"""Describe Mayor Cat visiting the {building} and meeting {person}.
                {person} is {person_desc}.
                Create a fun, friendly interaction for kids aged 7-12, about 6-9 sentences.
                Start by describing what the building looks like and sounds like.
                Then describe meeting the character and having a conversation.
                Include something fun or silly that happens during the visit.
                Maybe they play a game or share a snack or tell a funny story.
                Use simple words and make it feel like a cartoon adventure!
                End with Mayor Cat learning something about the town or the person."""
            else:
                prompt = f"""Describe Mayor Cat exploring the {building if building else 'town square'}.
                Write 6-9 sentences for kids aged 7-12 about what they discover.
                Describe what the place looks like - colors, sounds, smells.
                Tell about the animal citizens who live or work there.
                Mention something fun you can do at this place.
                Describe something interesting or surprising Mayor Cat finds.
                Use words like 'awesome', 'cool', 'fun', 'exciting', 'amazing'.
                Make it colorful and lively like a Saturday morning cartoon!"""

        elif phase == "day1":
            prompt = f"""Create a fun pizza party dilemma for Mayor Cat!
            
            FACTS:
            - Number of slices needed: {pizza_slices_needed}
            - Pizza Place A: ${pizza_price_a} per slice (super cheesy and delicious!)
            - Pizza Place B: ${pizza_price_b} per slice (only 30 slices available)
            
            Present this as Mayor Cat's first big decision. Write 6-9 sentences.
            Start by describing all the excited animal kids waiting for pizza party.
            Describe Pizza Place A - maybe it has fancy toppings but costs more.
            Describe Pizza Place B - maybe it's plainer but cheaper and limited.
            Explain that Mayor Cat needs to choose where to buy the pizza.
            Talk about how this teaches about comparing prices and making choices.
            Ask what Mayor Cat should do - get the fancy pizza or the cheaper one?
            Make it feel like a party! Use words like "yummy", "cheesy", "party time", "celebration".
            End with a clear question about what choice to make."""

        elif phase == "day2":
            prompt = f"""Create a townhall roof problem for Mayor Cat to solve!
            
            FACTS:
            - Good fix: ${roof_cost_quality} (will last for many years)
            - Quick fix: ${roof_cost_cheap} (might need fixing again soon)
            
            Write 6-9 sentences for kids aged 7-12 about this problem.
            Describe how rain is coming into the townhall during a meeting.
            Papers are getting wet, and everyone is getting dripped on!
            Two repair animals come to help - give them fun names and personalities.
            One offers a really good fix that costs more but will last a long time.
            The other offers a cheaper fix that might not last as long.
            Explain that this is about quality versus saving money now.
            Ask Mayor Cat to choose between doing it right or doing it fast.
            Make it funny - maybe the rain makes silly sounds or the repair animals have funny tools.
            End with asking Mayor Cat what repair to choose."""

        elif phase == "day3":
            prompt = f"""Create a tough choice between helping the playground or the new families!
            
            FACTS:
            - Playground upgrade: ${playground_upgrade_cost} (new slide, swings, and monkey bars)
            - Welcome new families: ${townhouse_welcome_cost} (welcome baskets with treats)
            - The town budget can only afford ONE of these things right now
            
            Write 6-9 sentences about this difficult decision for kids aged 7-12.
            Start by describing the playground - it's old and needs new equipment.
            The kids really want new swings and slides to play on.
            Then describe the new families who just moved into the townhouse.
            They feel nervous and would love welcome gifts to feel at home.
            Explain that Mayor Cat wants to help everyone but can only pick one.
            This teaches about making hard choices when you can't do everything.
            Ask Mayor Cat: Should we make the playground awesome or welcome new friends?
            Make it emotional but kid-friendly - show that both choices are good.
            End with asking which help to provide first."""

        elif phase == "final":
            current_budget = game_state["budget"]
            current_happiness = game_state["happiness"]
            
            prompt = f"""Create a big final celebration decision for the end of Mayor Cat's week!
            
            FACTS:
            - Current budget: ${current_budget}
            - Current happiness: {current_happiness}%
            - The town wants to celebrate a great week with Mayor Cat
            
            Write 6-9 sentences about this celebration choice for kids aged 7-12.
            Describe how it's Friday and everyone has had a fun week.
            The animal citizens want to throw a big party to celebrate.
            But parties cost money, and the town needs to save for future needs.
            Talk about how sometimes you celebrate successes, and sometimes you save.
            Ask Mayor Cat: Should we have an awesome party or save our money?
            Explain that this is the last decision of the week.
            Remind Mayor Cat of all the good choices they made.
            End with asking about the party decision and wishing them luck!"""
        else:
            prompt = "Welcome Mayor Cat! What fun adventure awaits today in our town?"

        # Add kid-friendly instruction for all prompts
        prompt += "\n\nIMPORTANT: Write for kids aged 7-12. Use simple words they can understand. Make it fun like a cartoon or storybook. Include exclamation points! Write 6-9 sentences total. Each sentence should be short and easy to read."
            
        # Use Gemini if available, otherwise use mock responses
        if genai_client:
            try:
                response = genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[{"text": prompt}]
                )
                ai_text = response.text
            except Exception as gemini_error:
                print(f"Gemini API error: {gemini_error}")
                # Try with 2.0-flash if 2.5 fails
                try:
                    response = genai_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[{"text": prompt}]
                    )
                    ai_text = response.text
                except Exception as e2:
                    print(f"Second Gemini attempt failed: {e2}")
                    ai_text = generate_kid_friendly_mock_response(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                                                roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                                                townhouse_welcome_cost)
        else:
            ai_text = generate_kid_friendly_mock_response(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                                        roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                                        townhouse_welcome_cost)
            
        # Store scenario data for frontend
        scenario_data = {
            "response": ai_text,
            "phase": phase,
            "dynamic_data": {
                "pizza_slices_needed": pizza_slices_needed,
                "pizza_price_a": pizza_price_a,
                "pizza_price_b": pizza_price_b,
                "roof_cost_quality": roof_cost_quality,
                "roof_cost_cheap": roof_cost_cheap,
                "playground_upgrade_cost": playground_upgrade_cost,
                "townhouse_welcome_cost": townhouse_welcome_cost
            },
            "options": get_kid_friendly_options_for_phase(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                                        roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                                        townhouse_welcome_cost)
        }
        
        return scenario_data
        
    except Exception as e:
        print(f"❌ Scenario generation error: {e}")
        return {
            "response": "Hi Mayor Cat! Ready for some fun decisions? Let's make our town awesome! Today we have important choices to make. Remember to think about what's best for everyone. Your decisions help our animal friends feel happy and safe. Let's start our adventure!",
            "phase": "error",
            "dynamic_data": {},
            "options": []
        }

def generate_kid_friendly_mock_response(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                      roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                      townhouse_welcome_cost):
    """Generate kid-friendly mock responses with 6-9 sentences"""
    
    responses_by_phase = {
        "introduction": [
            f"""🎉 MEOW! Mayor Cat is here! Welcome to Kitty Town with 1,000 animal friends! 
            You are now the mayor of this amazing town. We have ${game_state['budget']} to spend on making our town better.
            Our happiness level is {game_state['happiness']}%, which means most animals are pretty happy.
            You can drag Mayor Cat to visit four special places: townhall, pizza area, townhouse, and playground.
            Each place has friends to meet and problems to solve. Your job is to make good choices with our money.
            Good choices make animals happier, but they also cost money. You'll need to think carefully!
            Are you ready for your first day as mayor? Let's start by exploring our wonderful town!
            Drag Mayor Cat around to see what's happening in Kitty Town today!""",
            
            f"""🐱 Paws up for Mayor Cat! Our town needs your help to become the best ever.
            You start with ${game_state['budget']} in our town budget. That's money we can use for important things.
            Right now, our animal citizens are {game_state['happiness']}% happy. Your choices can make them even happier!
            There are four main places in our town: the townhall, pizza area, townhouse, and playground.
            You can visit these places by dragging Mayor Cat to them. Each place has its own story.
            Some places need repairs, some need parties, and some need welcome gifts for new friends.
            Every decision you make will change our budget and happiness. Think about what's best for everyone!
            Ready to begin? Let's see what's happening in Kitty Town right now!"""
        ],
        
        "exploration": [
            f"""You visit the {random.choice(['townhall', 'pizza area', 'townhouse', 'playground'])}! 
            It's a bright and colorful place with happy animal sounds everywhere.
            You see {random.choice(['puppies chasing balls', 'kittens playing with yarn', 'birds singing songs', 'rabbits hopping around'])}.
            The air smells like {random.choice(['fresh cookies', 'warm pizza', 'spring flowers', 'clean rain'])}.
            Animal friends wave hello as Mayor Cat walks by. Everyone seems excited to see you!
            You notice something interesting about this place that makes it special.
            Maybe it's a funny sign, a secret hiding spot, or a new decoration.
            Exploring helps you understand what your town needs and what makes animals happy.
            Where should Mayor Cat visit next? There's so much to discover!""",
            
            f"""Wow! Mayor Cat arrives at the {random.choice(['townhall with its shiny roof', 'pizza area smelling delicious', 'playground with laughter everywhere', 'townhouse with pretty gardens'])}!
            This place is buzzing with activity and fun. You can hear happy animal voices all around.
            Look over there! {random.choice(['A squirrel is doing acrobatics!', 'A mouse is telling a funny joke!', 'A bird is teaching a song!', 'A rabbit is showing magic tricks!'])}
            The colors here are so bright - {random.choice(['red and yellow flowers', 'blue and green decorations', 'rainbow flags waving', 'sparkling lights everywhere'])}.
            You meet some animal citizens who tell you about their day and what they love about this place.
            They share stories and maybe even a small gift or a secret handshake.
            Exploring helps Mayor Cat learn what's important to the animals who live here.
            Every place in town has its own special magic and friends to meet!"""
        ],
        
        "day1": [
            f"""🍕 PIZZA TIME! It's lunchtime at the pizza area and {pizza_slices_needed} hungry animal kids want pizza!
            The kids are jumping with excitement, their tails wagging and wings flapping happily.
            Pizza Place A has the cheesiest, most delicious pizza you've ever seen! It costs ${pizza_price_a} per slice.
            Pizza Place B has good pizza too, but it's simpler. It costs ${pizza_price_b} per slice, but they only have 30 slices left.
            Mayor Cat needs to decide: Should we buy all the pizza from Place A? Should we mix from both places?
            Or should we buy less pizza to save money for other important things?
            This is your first big decision as mayor! Think about what makes the most animal friends happy.
            Remember, good pizza makes everyone smile, but we also need to watch our budget.
            What should Mayor Cat choose for the pizza party?""",
            
            f"""🎂 Party alert! All the animal kids are gathered for a pizza celebration!
            There are exactly {pizza_slices_needed} hungry mouths waiting for delicious pizza slices.
            Chef Bear runs Pizza Place A. His pizza is amazing with extra cheese! Each slice costs ${pizza_price_a}.
            Chef Rabbit runs Pizza Place B. Her pizza is tasty too and costs only ${pizza_price_b} per slice, but she only made 30 slices today.
            Mayor Cat, you need to make a choice about our pizza order. This teaches about comparing prices and quality.
            Sometimes the best choice isn't the cheapest or the most expensive - it's the one that makes most animals happy!
            Think about how many slices we need and what we can afford with our town budget.
            Your decision will show how you make choices as our new mayor.
            So, what's the pizza plan for our hungry animal friends?"""
        ],
        
        "day2": [
            f"""💦 Oh no! It's raining inside the townhall! The roof has a leak right over important papers.
            Every time it rains, drips fall on the town records. The papers are getting wet and wrinkled!
            Benny Beaver offers to fix the roof properly for ${roof_cost_quality}. His fix will last for many, many years.
            Sammy Squirrel offers a quicker fix for ${roof_cost_cheap}. It might work, but it could need fixing again soon.
            Mayor Cat needs to decide: Should we pay more for a fix that lasts? Or save money with a temporary fix?
            This is about quality versus saving money now. Sometimes spending more now saves money later.
            Think about what's best for the town in the long run. We don't want wet papers every time it rains!
            Your choice will show how you think about solving problems for our town.
            What kind of roof repair should Mayor Cat choose?""",
            
            f"""🌧️ Drip drip drip! There's a leak in the townhall roof during an important meeting!
            Water is splashing on the meeting table, and everyone is getting little showers!
            Two repair experts have come to help. Mr. Owl says he can do a perfect fix for ${roof_cost_quality} that will last forever.
            Mrs. Fox says she can patch it up for ${roof_cost_cheap}, but it might need fixing again next year.
            Mayor Cat, this is a test of your leadership. Do you choose the best solution or the cheapest one?
            Sometimes it's worth spending more money to get something that works really well.
            But sometimes we need to save money for other important town needs.
            Think about what choice helps our town the most in the long run.
            Which roof repair should we go with, Mayor Cat?"""
        ],
        
        "day3": [
            f"""🤔 Tough choice time! Mayor Cat faces a difficult decision today.
            The playground needs upgrading! For ${playground_upgrade_cost}, we can get new swings, a slide, and monkey bars.
            All the kids are excited about this! They really want a better place to play.
            But wait! Three new families just moved into the townhouse. They need welcome baskets!
            For ${townhouse_welcome_cost}, we can make special welcome baskets with treats and gifts.
            This would help the new families feel welcome and happy in our town.
            Here's the problem: We only have enough money in our budget for ONE of these things right now.
            Mayor Cat must choose: Upgrade the playground or welcome the new families?
            This teaches about making hard choices when you can't do everything you want.
            What should Mayor Cat choose to do first?""",
            
            f"""⚖️ Balance time! Mayor Cat has two important requests today.
            First, the playground equipment is old and needs upgrading. New fun equipment costs ${playground_upgrade_cost}.
            The animal kids really want new things to play on! They've been asking for months.
            Second, new families moved into the townhouse yesterday. Welcome baskets cost ${townhouse_welcome_cost}.
            These baskets would help the new animals feel at home in Kitty Town.
            Our budget can only handle one of these projects right now. We have to choose!
            Sometimes being mayor means you can't make everyone happy at once.
            You have to think about what's most important for the town right now.
            Should we make the playground awesome or welcome our new neighbors first?
            What's your decision, Mayor Cat?"""
        ],
        
        "final": [
            f"""🎊 Celebration time! Mayor Cat has completed a whole week as our mayor!
            We have ${game_state['budget']} left in our town budget. Our happiness level is {game_state['happiness']}%!
            The animal citizens want to throw a big party to celebrate your first week.
            A really awesome party would cost about $300 for decorations, music, and treats.
            But we could also save that money for future town needs that might come up.
            This is your final decision of the week: Big celebration party or save our money?
            Parties are fun and make everyone feel happy and connected.
            Saving money is smart because we might need it for unexpected problems.
            Think about what you've learned this week about making good choices.
            What should we do for our Friday celebration, Mayor Cat?""",
            
            f"""🏆 Amazing job, Mayor Cat! You've made it through your first week as mayor!
            Our town budget has ${game_state['budget']} remaining. Animal happiness is at {game_state['happiness']}%.
            Everyone is talking about throwing a celebration party to end the week.
            A fantastic party would cost $300 for food, games, and fun decorations.
            But being responsible might mean saving that money for tomorrow's needs.
            This is about balancing fun today with being ready for tomorrow.
            What have you learned about spending and saving from your other decisions?
            Your choice will show what kind of mayor you want to be.
            Should we have an awesome party or save our money for the future?
            Make your final decision, Mayor Cat!"""
        ]
    }
    
    responses = responses_by_phase.get(phase, ["Welcome to Kitty Town adventures! Let's explore our wonderful town together. There's so much to see and do here. Every day brings new friends to meet and decisions to make. Remember to think about what's best for all our animal citizens. Have fun being our mayor!"])
    return random.choice(responses)

def get_kid_friendly_options_for_phase(phase, pizza_slices_needed, pizza_price_a, pizza_price_b, 
                                     roof_cost_quality, roof_cost_cheap, playground_upgrade_cost, 
                                     townhouse_welcome_cost):
    """Generate kid-friendly decision options"""
    if phase == "day1":
        cost_all_a = pizza_slices_needed * pizza_price_a
        cost_mix = (30 * pizza_price_b) + ((pizza_slices_needed - 30) * pizza_price_a)
        
        return [
            {"id": "pizza_all_a", "label": f"All from Pizza Place A (${cost_all_a:.2f})", 
             "cost": cost_all_a, "happiness": 20},
            {"id": "pizza_mix", "label": f"Mix from both places (${cost_mix:.2f})", 
             "cost": cost_mix, "happiness": 15},
            {"id": "pizza_less", "label": f"Buy less pizza (save ${150})", 
             "cost": 150, "happiness": -10}
        ]
    elif phase == "day2":
        return [
            {"id": "roof_quality", "label": f"Quality fix (${roof_cost_quality})", 
             "cost": roof_cost_quality, "happiness": 15},
            {"id": "roof_cheap", "label": f"Quick fix (${roof_cost_cheap})", 
             "cost": roof_cost_cheap, "happiness": 5}
        ]
    elif phase == "day3":
        return [
            {"id": "upgrade_playground", "label": f"Upgrade playground (${playground_upgrade_cost})", 
             "cost": playground_upgrade_cost, "happiness": 25},
            {"id": "welcome_families", "label": f"Welcome new families (${townhouse_welcome_cost})", 
             "cost": townhouse_welcome_cost, "happiness": 20}
        ]
    elif phase == "final":
        party_cost = 300
        return [
            {"id": "big_party", "label": f"Throw big party! (${party_cost})", 
             "cost": party_cost, "happiness": 30},
            {"id": "save_money", "label": "Save money for future", 
             "cost": 0, "happiness": -15}
        ]
    return []

# ElevenLabs endpoint
@app.post("/api/speak")
async def text_to_speech(request: dict):
    try:
        text_content = request.get('text', '')
        if not text_content:
            return {"error": "No text provided"}
        
        if not eleven_client:
            return {
                "audio_url": "/static/audio/mock.mp3", 
                "text": text_content,
                "status": "mock_mode"
            }
        
        print(f"🔊 Generating speech: '{text_content[:50]}...'")
        
        try:
            audio = eleven_client.text_to_speech.convert(
                text=text_content,
                voice_id="pNInz6obpgDQGcFmaJgB",
                model_id="eleven_multilingual_v2",
                voice_settings={
                    "stability": 0.71,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            )
        except Exception as inner_e:
            print(f"⚠️ Trying alternative: {inner_e}")
            audio = eleven_client.generate(
                text=text_content,
                voice="Rachel",  # Kid-friendly voice
                model="eleven_monolingual_v1"
            )
        
        with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            for chunk in audio:
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        with open(temp_file_path, "rb") as f:
            audio_content = f.read()
        
        os.unlink(temp_file_path)
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        return {
            "audio_url": f"data:audio/mp3;base64,{audio_base64}",
            "text": text_content,
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Speech error: {e}")
        return {
            "audio_url": "/static/audio/mock.mp3", 
            "text": text_content if 'text_content' in locals() else str(request),
            "status": "error"
        }

# Game endpoints
@app.get("/api/game/state")
async def get_game_state():
    return game_state

@app.get("/api/game/people")
async def get_town_people():
    return {"people": town_people}

@app.post("/api/game/decision")
async def make_decision(decision: dict):
    decision_id = decision.get("id")
    phase = decision.get("phase", game_state["game_phase"])
    
    # Get cost and happiness from options (simplified for kids)
    cost = 0
    happiness_change = 0
    
    if decision_id == "pizza_all_a":
        cost = 120
        happiness_change = 20
    elif decision_id == "pizza_mix":
        cost = 100
        happiness_change = 15
    elif decision_id == "pizza_less":
        cost = 80
        happiness_change = -10
    elif decision_id == "roof_quality":
        cost = 700
        happiness_change = 15
    elif decision_id == "roof_cheap":
        cost = 300
        happiness_change = 5
    elif decision_id == "upgrade_playground":
        cost = 400
        happiness_change = 25
    elif decision_id == "welcome_families":
        cost = 200
        happiness_change = 20
    elif decision_id == "big_party":
        cost = 300
        happiness_change = 30
    elif decision_id == "save_money":
        cost = 0
        happiness_change = -15
    
    # Apply decision
    game_state["budget"] -= cost
    game_state["happiness"] += happiness_change
    if happiness_change > 0:  # Don't let it go negative
        game_state["day"] += 1
    
    # Record decision
    game_state["decisions"].append({
        "day": game_state["day"],
        "decision": decision_id,
        "cost": cost,
        "happiness_change": happiness_change,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update game phase
    if phase == "day1":
        game_state["game_phase"] = "day2"
    elif phase == "day2":
        game_state["game_phase"] = "day3"
    elif phase == "day3":
        game_state["game_phase"] = "final"
    elif phase == "final":
        # Check ending - kid friendly outcomes
        if game_state["budget"] > 400 and game_state["happiness"] > 70:
            game_state["ending"] = "Super Star Mayor!"
        elif game_state["happiness"] > 75:
            game_state["ending"] = "Most Loved Mayor!"
        elif game_state["budget"] > 600:
            game_state["ending"] = "Money Smart Mayor!"
        else:
            game_state["ending"] = "Good Try Mayor!"
        game_state["game_phase"] = "completed"
    
    return {"message": "Great choice!", "state": game_state}

@app.post("/api/game/explore")
async def explore_building(exploration: dict):
    building = exploration.get("building")
    person = exploration.get("person")
    
    # Update game phase to exploration if not already in a day scenario
    if game_state["game_phase"] not in ["day1", "day2", "day3", "final", "completed"]:
        game_state["game_phase"] = "exploration"
    
    return {
        "message": f"Visiting {building} is fun!" + (f" Met {person}!" if person else ""),
        "building": building,
        "person": person
    }

# Reset game endpoint
@app.post("/api/game/reset")
async def reset_game():
    global game_state
    game_state = {
        "budget": 1000,
        "happiness": 50,
        "day": 0,
        "scenario_day": 1,
        "town_state": {
            "townhall": {"status": "needs_repair", "roof_damage": "leaking"},
            "pizza_area": {"status": "ready_for_party", "pizza_needed": True},
            "townhouse": {"status": "new_families_moving_in", "families_count": 3},
            "playground": {"status": "needs_upgrade", "equipment_broken": True}
        },
        "decisions": [],
        "previous_choices": {},
        "game_phase": "introduction"
    }
    return {"message": "New game started! Have fun!", "state": game_state}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
