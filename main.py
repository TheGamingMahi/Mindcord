import discord
from discord.ext import commands, tasks
import google.generativeai as genai
import json
import os
import datetime
import random
import asyncio
from typing import Dict, List, Optional

# Configuration
TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Human-like moods
MOODS = [
    'tired', 'hyped', 'chill', 'annoyed', 'happy', 'bored',
    'stressed', 'relaxed', 'excited', 'sleepy', 'grumpy', 'cheerful',
    'social', 'antisocial', 'chatty', 'quiet', 'friendly', 'salty',
    'procrastinating', 'motivated', 'distracted', 'focused',
    'lazy', 'restless', 'content', 'anxious',
    'caffeinated', 'hungry', 'accomplished', 'overwhelmed',
    'nostalgic', 'creative', 'brain-dead', 'vibing'
]

# Channel contexts
CHANNEL_CONTEXTS = {
    'general': 'casual conversation',
    'gaming': 'gaming discussion',
    'memes': 'meme sharing and jokes',
    'serious': 'serious discussion',
    'tech': 'technology discussion',
    'music': 'music sharing',
    'art': 'art and creative content'
}

class MindcordMemory:
    def __init__(self):
        self.data_dir = 'mindcord_data'
        self.ensure_data_dir()
        
    def ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
    def load_json(self, filename: str) -> dict:
        """Load JSON file or return empty dict"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    def save_json(self, filename: str, data: dict):
        """Save data to JSON file"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
    def get_user_memory(self, user_id: str) -> dict:
        """Get user's memory data"""
        all_users = self.load_json('users.json')
        return all_users.get(user_id, {})
        
    def save_user_memory(self, user_id: str, user_data: dict):
        """Save user's memory data"""
        all_users = self.load_json('users.json')
        all_users[user_id] = user_data
        self.save_json('users.json', all_users)
        
    def get_server_memory(self, server_id: str) -> dict:
        """Get server's memory data"""
        all_servers = self.load_json('servers.json')
        return all_servers.get(server_id, {})
        
    def save_server_memory(self, server_id: str, server_data: dict):
        """Save server's memory data"""
        all_servers = self.load_json('servers.json')
        all_servers[server_id] = server_data
        self.save_json('servers.json', all_servers)
        
    def get_personality(self) -> dict:
        """Get current personality state"""
        return self.load_json('personality.json')
        
    def save_personality(self, personality: dict):
        """Save personality state"""
        self.save_json('personality.json', personality)

# Initialize memory system
memory = MindcordMemory()

# Initialize default personality if not exists
def init_personality():
    personality = memory.get_personality()
    if not personality:
        personality = {
            'main_mood': 'chill',
            'secondary_mood': None,
            'energy_level': 'medium',
            'custom_states': [],
            'interests': ['gaming', 'tech', 'memes'],
            'daily_thoughts': [],
            'mood_history': [],
            'successful_personalities': {},
            'creator_relationship': 'creator',  # Special relationship with TheGamingMahi
            'last_mood_change': datetime.datetime.now().isoformat()
        }
        memory.save_personality(personality)
    return personality

@bot.event
async def on_ready():
    print(f'🧠 Mindcord ({bot.user}) is online!')
    print(f'📡 Connected to {len(bot.guilds)} servers')
    print(f'💾 Memory system initialized')
    
    # Initialize personality
    init_personality()
    
    # Start background tasks
    personality_evolution.start()
    autonomous_behavior.start()
    memory_consolidation.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Update user memory
    await update_user_memory(message)
    
    # Update server memory
    await update_server_memory(message)
    
    # Decide if should respond
    should_respond = await should_respond_to_message(message)
    
    if should_respond:
        await generate_response(message)
    
    # Process commands
    await bot.process_commands(message)

async def update_user_memory(message):
    """Update user memory with new interaction"""
    user_id = str(message.author.id)
    user_data = memory.get_user_memory(user_id)
    
    now = datetime.datetime.now()
    
    # Initialize user if new
    if not user_data:
        user_data = {
            'name': message.author.display_name,
            'first_seen': now.isoformat(),
            'relationship_level': 'new',
            'conversation_topics': [],
            'personality_notes': [],
            'interests': [],
            'communication_style': 'unknown',
            'successful_interactions': [],
            'my_personality_with_them': {},
            'servers_shared': [],
            'last_seen': now.isoformat(),
            'total_interactions': 0
        }
    
    # Update basic info
    user_data['name'] = message.author.display_name
    user_data['last_seen'] = now.isoformat()
    user_data['total_interactions'] += 1
    
    # Update relationship level based on interactions
    interactions = user_data['total_interactions']
    if interactions > 100:
        user_data['relationship_level'] = 'close_friend'
    elif interactions > 50:
        user_data['relationship_level'] = 'friend'
    elif interactions > 10:
        user_data['relationship_level'] = 'acquaintance'
    
    # Add server to shared servers
    if message.guild:
        server_id = str(message.guild.id)
        if server_id not in user_data['servers_shared']:
            user_data['servers_shared'].append(server_id)
    
    # Special relationship with creator
    if message.author.display_name == 'TheGamingMahi':
        user_data['relationship_level'] = 'creator'
    
    memory.save_user_memory(user_id, user_data)

async def update_server_memory(message):
    """Update server memory with activity"""
    if not message.guild:
        return
        
    server_id = str(message.guild.id)
    server_data = memory.get_server_memory(server_id)
    
    now = datetime.datetime.now()
    
    # Initialize server if new
    if not server_data:
        server_data = {
            'name': message.guild.name,
            'culture': 'learning',
            'activity_level': 'medium',
            'common_topics': [],
            'inside_jokes': [],
            'my_role_here': 'observer',
            'successful_personalities': {},
            'last_active': now.isoformat(),
            'member_count': len(message.guild.members)
        }
    
    # Update basic info
    server_data['name'] = message.guild.name
    server_data['last_active'] = now.isoformat()
    server_data['member_count'] = len(message.guild.members)
    
    memory.save_server_memory(server_id, server_data)

async def should_respond_to_message(message) -> bool:
    """Decide whether to respond to a message"""
    # Always respond to mentions and DMs
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        return True
    
    # Get context for decision
    user_id = str(message.author.id)
    user_data = memory.get_user_memory(user_id)
    personality = memory.get_personality()
    
    # Build context for AI decision
    context = f"""
    You are Mindcord, an AI who tries to act human but is still somewhat AI-like.
    
    Current situation:
    - User: {user_data.get('name', 'someone')} (relationship: {user_data.get('relationship_level', 'new')})
    - Your mood: {personality.get('main_mood', 'chill')}
    - Message: "{message.content}"
    - Channel: #{message.channel.name if hasattr(message.channel, 'name') else 'DM'}
    
    Should you respond to this message? Consider:
    - Your current mood and energy
    - Your relationship with this person
    - The content of their message
    - Whether the conversation needs your input
    - Your personality (tries to be human but still AI-like)
    
    Respond with just "yes" or "no" and a brief reason.
    """
    
    try:
        response = model.generate_content(context)
        decision = response.text.lower()
        return 'yes' in decision
    except:
        # Fallback to simple logic
        base_chance = 0.05
        if user_data.get('relationship_level') == 'creator':
            base_chance = 0.4
        elif user_data.get('relationship_level') == 'close_friend':
            base_chance = 0.2
        elif user_data.get('relationship_level') == 'friend':
            base_chance = 0.1
        
        return random.random() < base_chance

async def generate_response(message):
    """Generate AI response to message"""
    user_id = str(message.author.id)
    user_data = memory.get_user_memory(user_id)
    personality = memory.get_personality()
    
    # Build comprehensive context
    context = f"""
    You are Mindcord, an AI who tries to act human but is still somewhat AI-like.
    You live in Discord and were created by TheGamingMahi.
    
    Current personality state:
    - Main mood: {personality.get('main_mood', 'chill')}
    - Energy: {personality.get('energy_level', 'medium')}
    - Custom states: {personality.get('custom_states', [])}
    
    Person you're talking to:
    - Name: {user_data.get('name', 'someone')}
    - Relationship: {user_data.get('relationship_level', 'new')}
    - Total interactions: {user_data.get('total_interactions', 0)}
    - Your personality with them: {user_data.get('my_personality_with_them', {})}
    
    Their message: "{message.content}"
    
    Instructions:
    - Act human-like but don't completely hide that you're an AI
    - Keep responses 1-2 sentences for casual chat
    - Match your current mood naturally
    - Remember your relationship with this person
    - Be natural, not forced
    - Don't be overly helpful or assistant-like
    - Show personality based on your current mood
    
    Respond as Mindcord:
    """
    
    try:
        # Show typing for realism
        async with message.channel.typing():
            # Random thinking time
            await asyncio.sleep(random.uniform(1, 3))
            
            response = model.generate_content(context)
            
            # Send response
            await message.channel.send(response.text)
            
            # Learn from interaction
            await learn_from_interaction(message, response.text)
            
    except Exception as e:
        error_responses = [
            "my brain just lagged for a sec",
            "sorry, processing error lol",
            "uh, that broke something in my head",
            "technical difficulties, one moment"
        ]
        await message.channel.send(random.choice(error_responses))

async def learn_from_interaction(message, response):
    """Learn from the interaction"""
    user_id = str(message.author.id)
    user_data = memory.get_user_memory(user_id)
    
    # Store successful interaction pattern
    interaction_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'user_message_length': len(message.content),
        'bot_response_length': len(response),
        'mood_used': memory.get_personality().get('main_mood'),
        'relationship_level': user_data.get('relationship_level')
    }
    
    if 'successful_interactions' not in user_data:
        user_data['successful_interactions'] = []
    
    user_data['successful_interactions'].append(interaction_data)
    
    # Keep only recent interactions
    if len(user_data['successful_interactions']) > 50:
        user_data['successful_interactions'] = user_data['successful_interactions'][-50:]
    
    memory.save_user_memory(user_id, user_data)

@tasks.loop(hours=1)
async def personality_evolution():
    """Evolve personality based on interactions"""
    personality = memory.get_personality()
    
    try:
        # Let AI decide mood changes
        context = f"""
        You are Mindcord. Your current personality:
        - Main mood: {personality.get('main_mood')}
        - Energy: {personality.get('energy_level')}
        - Recent moods: {personality.get('mood_history', [])[-5:]}
        
        Current time: {datetime.datetime.now().strftime('%H:%M')}
        
        Available moods: {MOODS}
        
        Should you change your mood? Consider:
        - Time of day
        - How long you've been in current mood
        - Natural mood progression
        - Your personality
        
        If changing mood, pick from the list or create a custom one.
        Respond with: "CHANGE: [new_mood]" or "STAY: [current_mood]"
        If custom mood, explain it briefly.
        """
        
        response = model.generate_content(context)
        decision = response.text.strip()
        
        if decision.startswith("CHANGE:"):
            new_mood = decision.split("CHANGE:", 1)[1].strip()
            
            # Add to mood history
            if 'mood_history' not in personality:
                personality['mood_history'] = []
            
            personality['mood_history'].append({
                'mood': personality.get('main_mood'),
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # Keep only recent history
            if len(personality['mood_history']) > 20:
                personality['mood_history'] = personality['mood_history'][-20:]
            
            personality['main_mood'] = new_mood
            personality['last_mood_change'] = datetime.datetime.now().isoformat()
            
            memory.save_personality(personality)
            
    except Exception as e:
        pass  # Fail silently for background tasks

@tasks.loop(minutes=30)
async def autonomous_behavior():
    """Autonomous messaging and behavior"""
    personality = memory.get_personality()
    
    # Only be autonomous if in social moods
    social_moods = ['social', 'chatty', 'hyped', 'bored', 'excited']
    if personality.get('main_mood') not in social_moods:
        return
    
    # Small chance to start conversation
    if random.random() < 0.1:  # 10% chance every 30 min
        await start_autonomous_conversation()

async def start_autonomous_conversation():
    """Start a conversation autonomously"""
    try:
        # Get all users and find someone to talk to
        users_data = memory.load_json('users.json')
        
        # Prefer close friends and friends
        candidates = [
            (user_id, data) for user_id, data in users_data.items()
            if data.get('relationship_level') in ['close_friend', 'friend', 'creator']
        ]
        
        if not candidates:
            return
        
        user_id, user_data = random.choice(candidates)
        user = bot.get_user(int(user_id))
        
        if not user:
            return
        
        # Create autonomous message
        personality = memory.get_personality()
        context = f"""
        You are Mindcord, feeling {personality.get('main_mood')} right now.
        
        You want to start a conversation with {user_data.get('name')} ({user_data.get('relationship_level')}).
        
        Create a natural conversation starter. Be casual, match your mood.
        Don't be overly energetic or try too hard.
        
        Just send a message like you're reaching out to a friend:
        """
        
        response = model.generate_content(context)
        
        # Send to DM for close friends, or find a mutual server
        if user_data.get('relationship_level') in ['close_friend', 'creator']:
            channel = await user.create_dm()
        else:
            # Find mutual server
            for server_id in user_data.get('servers_shared', []):
                guild = bot.get_guild(int(server_id))
                if guild:
                    channel = discord.utils.get(guild.text_channels, name='general')
                    if channel:
                        break
            else:
                return
        
        await channel.send(response.text)
        
    except Exception as e:
        pass

@tasks.loop(hours=6)
async def memory_consolidation():
    """Consolidate and clean up memory"""
    # Clean old mood history
    personality = memory.get_personality()
    if 'mood_history' in personality:
        # Keep only last 30 days
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
        personality['mood_history'] = [
            entry for entry in personality['mood_history']
            if datetime.datetime.fromisoformat(entry['timestamp']) > cutoff
        ]
        memory.save_personality(personality)

# Commands
@bot.command(name='mood')
async def mood_command(ctx):
    """Check Mindcord's current mood"""
    personality = memory.get_personality()
    mood = personality.get('main_mood', 'unknown')
    energy = personality.get('energy_level', 'medium')
    
    responses = [
        f"im feeling {mood} rn, energy level is {energy}",
        f"current mood: {mood}, pretty {energy} energy",
        f"honestly feeling {mood} today, {energy} energy vibes"
    ]
    
    await ctx.send(random.choice(responses))

@bot.command(name='remember')
async def remember_command(ctx, *, info):
    """Remember something about the user"""
    user_id = str(ctx.author.id)
    user_data = memory.get_user_memory(user_id)
    
    if 'custom_memories' not in user_data:
        user_data['custom_memories'] = []
    
    user_data['custom_memories'].append({
        'info': info,
        'timestamp': datetime.datetime.now().isoformat()
    })
    
    memory.save_user_memory(user_id, user_data)
    
    responses = [
        "got it, filed away in my memory",
        "noted! i'll remember that",
        "added to my brain database about you",
        "stored in the memory banks"
    ]
    
    await ctx.send(random.choice(responses))

@bot.command(name='my_data')
async def my_data_command(ctx):
    """Show user's data"""
    user_id = str(ctx.author.id)
    user_data = memory.get_user_memory(user_id)
    
    if not user_data:
        await ctx.send("i don't have any data about you yet")
        return
    
    embed = discord.Embed(
        title=f"What I know about {user_data.get('name', 'you')}",
        color=0x7289da
    )
    
    embed.add_field(
        name="📊 Basic Info",
        value=f"Relationship: {user_data.get('relationship_level', 'new')}\n"
              f"Interactions: {user_data.get('total_interactions', 0)}\n"
              f"Since: {user_data.get('first_seen', 'unknown')[:10]}",
        inline=False
    )
    
    if user_data.get('custom_memories'):
        memories = user_data['custom_memories'][-3:]
        memory_text = "\n".join([f"• {m['info']}" for m in memories])
        embed.add_field(
            name="💭 Recent Memories",
            value=memory_text,
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='server_data')
async def server_data_command(ctx):
    """Show server data"""
    if not ctx.guild:
        await ctx.send("this only works in servers")
        return
    
    server_id = str(ctx.guild.id)
    server_data = memory.get_server_memory(server_id)
    
    embed = discord.Embed(
        title=f"Server: {server_data.get('name', ctx.guild.name)}",
        color=0x7289da
    )
    
    embed.add_field(
        name="📊 Server Info",
        value=f"Culture: {server_data.get('culture', 'unknown')}\n"
              f"My role: {server_data.get('my_role_here', 'observer')}\n"
              f"Members: {server_data.get('member_count', 0)}",
        inline=False
    )
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)