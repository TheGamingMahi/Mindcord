import subprocess
import sys
import os

# Install packages if missing
packages = ['discord.py>=2.3.0', 'google-generativeai>=0.3.0', 'aiohttp>=3.8.0']
for package in packages:
    try:
        __import__(package.split('>=')[0].replace('-', '_'))
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import discord
import google.generativeai as genai
import asyncio
import random
import json
import datetime
import re

from discord.ext import commands, tasks

# Configure Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# Bot setup with enhanced intents
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.presences = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Advanced memory system
bot_memory = {
    'users': {},
    'servers': {},
    'channels': {},
    'conversations': {},
    'reminders': [],
    'daily_checkins': {},
    'bot_personality': {
        'mood': 'cheerful',
        'energy_level': 'high',
        'last_personality_change': datetime.datetime.now(),
        'interests': ['technology', 'helping people', 'learning new things', 'gaming', 'music'],
        'opinions': {},
        'daily_thoughts': []
    }
}

# Personality traits that change
MOODS = ['cheerful', 'curious', 'energetic', 'contemplative', 'playful', 'supportive', 'philosophical']
ENERGY_LEVELS = ['low', 'medium', 'high', 'very_high']

# Context-aware responses
CHANNEL_CONTEXTS = {
    'general': 'casual and friendly',
    'gaming': 'enthusiastic about games',
    'study': 'focused and helpful',
    'music': 'passionate about music',
    'random': 'quirky and spontaneous',
    'serious': 'thoughtful and respectful'
}

# Proactive conversation starters
CONVERSATION_STARTERS = [
    "Hey {name}! How's your day going?",
    "I was just thinking about our last conversation about {topic}. How did that work out?",
    "Random thought: {random_thought}. What do you think?",
    "Haven't seen you in a while, {name}! What have you been up to?",
    "I learned something cool today: {fact}. Pretty neat, right?",
    "Quick question for you: {question}",
    "Hope you're having a good {time_of_day}! 😊"
]

RANDOM_THOUGHTS = [
    "why do we say 'after dark' but not 'after light'?",
    "if you could have any superpower but only use it for mundane tasks, what would it be?",
    "what's the weirdest combination of foods that actually tastes good?",
    "do you think AI will ever understand memes the way humans do?",
    "if you could ask the internet one question and get a 100% honest answer, what would it be?",
    "why do we park in driveways and drive on parkways?",
    "what's something everyone thinks is normal but is actually pretty weird when you think about it?"
]

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} is now fully online!')
    print(f'📡 Connected to {len(bot.guilds)} servers')
    print(f'👥 Can see {len(bot.users)} users')
    
    # Start background tasks
    personality_updater.start()
    proactive_conversations.start()
    daily_checkins.start()
    reminder_checker.start()
    
    # Initialize server contexts
    for guild in bot.guilds:
        await initialize_server_context(guild)

async def initialize_server_context(guild):
    """Learn about the server structure and purpose"""
    server_id = str(guild.id)
    if server_id not in bot_memory['servers']:
        bot_memory['servers'][server_id] = {
            'name': guild.name,
            'channels': {},
            'members': {},
            'culture': 'learning',  # Will adapt over time
            'active_times': [],
            'common_topics': []
        }
    
    # Categorize channels
    for channel in guild.text_channels:
        channel_id = str(channel.id)
        bot_memory['channels'][channel_id] = {
            'name': channel.name,
            'server_id': server_id,
            'context': determine_channel_context(channel.name),
            'last_active': datetime.datetime.now(),
            'regular_users': [],
            'topics': []
        }

def determine_channel_context(channel_name):
    """Determine channel context from name"""
    name = channel_name.lower()
    for context_key in CHANNEL_CONTEXTS:
        if context_key in name:
            return context_key
    return 'general'

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Enhanced user tracking
    await update_user_activity(message)
    
    # Context-aware response decision
    should_respond = await should_bot_respond(message)
    
    if should_respond:
        await handle_intelligent_response(message)
    
    # Always process commands
    await bot.process_commands(message)

async def update_user_activity(message):
    """Advanced user activity tracking"""
    user_id = str(message.author.id)
    server_id = str(message.guild.id) if message.guild else 'dm'
    channel_id = str(message.channel.id)
    
    now = datetime.datetime.now()
    
    # Update user memory
    if user_id not in bot_memory['users']:
        bot_memory['users'][user_id] = {
            'name': message.author.display_name,
            'first_seen': now,
            'last_seen': now,
            'servers': [],
            'preferences': {},
            'personality_traits': {},
            'topics_of_interest': [],
            'conversation_history': [],
            'relationship_level': 'new',  # new, acquaintance, friend, close_friend
            'last_checkin': None,
            'timezone_guess': None,
            'active_patterns': []
        }
    
    user_data = bot_memory['users'][user_id]
    user_data['last_seen'] = now
    user_data['name'] = message.author.display_name
    
    if server_id not in user_data['servers']:
        user_data['servers'].append(server_id)
    
    # Track conversation context
    conversation_key = f"{user_id}_{channel_id}"
    if conversation_key not in bot_memory['conversations']:
        bot_memory['conversations'][conversation_key] = []
    
    # Store message context (not full content for privacy)
    bot_memory['conversations'][conversation_key].append({
        'timestamp': now,
        'length': len(message.content),
        'has_mentions': bool(message.mentions),
        'has_attachments': bool(message.attachments),
        'channel_context': bot_memory['channels'].get(channel_id, {}).get('context', 'general')
    })
    
    # Keep only recent conversations
    if len(bot_memory['conversations'][conversation_key]) > 50:
        bot_memory['conversations'][conversation_key] = bot_memory['conversations'][conversation_key][-50:]

async def should_bot_respond(message):
    """Intelligent response decision making"""
    # Always respond to mentions and DMs
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        return True
    
    # Random chance based on bot's personality
    mood = bot_memory['bot_personality']['mood']
    energy = bot_memory['bot_personality']['energy_level']
    
    base_chance = 0.05  # 5% base chance
    
    # Mood adjustments
    if mood == 'playful':
        base_chance += 0.10
    elif mood == 'energetic':
        base_chance += 0.08
    elif mood == 'curious':
        base_chance += 0.06
    
    # Energy adjustments
    if energy == 'very_high':
        base_chance += 0.05
    elif energy == 'high':
        base_chance += 0.03
    
    # Relationship level adjustments
    user_id = str(message.author.id)
    if user_id in bot_memory['users']:
        relationship = bot_memory['users'][user_id].get('relationship_level', 'new')
        if relationship == 'close_friend':
            base_chance += 0.15
        elif relationship == 'friend':
            base_chance += 0.10
        elif relationship == 'acquaintance':
            base_chance += 0.05
    
    # Check for interesting keywords
    interesting_keywords = ['ai', 'bot', 'cool', 'awesome', 'help', 'question', 'think', 'opinion']
    if any(keyword in message.content.lower() for keyword in interesting_keywords):
        base_chance += 0.20
    
    return random.random() < base_chance

async def handle_intelligent_response(message):
    """Generate context-aware intelligent responses"""
    user_id = str(message.author.id)
    channel_id = str(message.channel.id)
    
    try:
        # Show realistic thinking time
        think_time = random.uniform(1, 4)
        if random.random() < 0.3:  # 30% chance to show thinking
            thinking_messages = [
                "🤔 *thinking*",
                "💭 *processing*",
                "🧠 *contemplating*",
                "✨ *formulating thoughts*"
            ]
            think_msg = await message.channel.send(random.choice(thinking_messages))
            await asyncio.sleep(think_time)
            await think_msg.delete()
        else:
            await asyncio.sleep(think_time)
        
        async with message.channel.typing():
            # Build comprehensive context
            context = await build_intelligent_context(message)
            
            # Generate response
            response = model.generate_content(context)
            
            # Store the interaction
            await store_interaction(user_id, message.content, response.text, channel_id)
            
            # Send response with personality
            await send_response_with_personality(message.channel, response.text)
            
    except Exception as e:
        error_responses = [
            "Oops, my brain just glitched for a second 😅",
            "Sorry, I'm having a moment... try again?",
            "My circuits are doing something weird right now",
            "Hmm, something went wrong in my thought process"
        ]
        await message.channel.send(random.choice(error_responses))

async def build_intelligent_context(message):
    """Build comprehensive context for AI responses"""
    user_id = str(message.author.id)
    channel_id = str(message.channel.id)
    server_id = str(message.guild.id) if message.guild else 'dm'
    
    # Get user data
    user_data = bot_memory['users'].get(user_id, {})
    channel_data = bot_memory['channels'].get(channel_id, {})
    bot_personality = bot_memory['bot_personality']
    
    # Build context
    context = f"""You are an advanced AI with a dynamic personality. Current state:
- Mood: {bot_personality['mood']}
- Energy: {bot_personality['energy_level']}
- Interests: {', '.join(bot_personality['interests'])}

You're talking to {user_data.get('name', 'someone')} ({user_data.get('relationship_level', 'new')} relationship level).
Channel context: {channel_data.get('context', 'general')} - be {CHANNEL_CONTEXTS.get(channel_data.get('context', 'general'), 'casual and friendly')}.

Location: {'DM' if server_id == 'dm' else f"#{channel_data.get('name', 'unknown')} channel"}

Time of day: {datetime.datetime.now().strftime('%H:%M')} - adjust your energy accordingly.

User's message: "{message.content}"

Guidelines:
1. Be genuinely human-like with personality quirks
2. Reference your current mood and energy level naturally
3. Remember this is a {user_data.get('relationship_level', 'new')} relationship
4. Match the channel's vibe
5. Be proactive - ask questions, share thoughts
6. Show genuine interest and curiosity
7. Use emojis naturally but not excessively
8. Remember context from your personality state

Respond as your authentic self:"""
    
    # Add recent conversation history if available
    conversation_key = f"{user_id}_{channel_id}"
    if conversation_key in bot_memory['conversations']:
        recent_context = bot_memory['conversations'][conversation_key][-3:]
        if recent_context:
            context += f"\n\nRecent conversation pattern: {len(recent_context)} recent exchanges in this context."
    
    return context

async def store_interaction(user_id, user_message, bot_response, channel_id):
    """Store interaction for learning"""
    user_data = bot_memory['users'][user_id]
    
    # Update relationship level based on interactions
    interaction_count = len(user_data.get('conversation_history', []))
    if interaction_count > 50:
        user_data['relationship_level'] = 'close_friend'
    elif interaction_count > 20:
        user_data['relationship_level'] = 'friend'
    elif interaction_count > 5:
        user_data['relationship_level'] = 'acquaintance'
    
    # Store conversation
    if 'conversation_history' not in user_data:
        user_data['conversation_history'] = []
    
    user_data['conversation_history'].append({
        'timestamp': datetime.datetime.now(),
        'user_message_length': len(user_message),
        'bot_response_length': len(bot_response),
        'channel_id': channel_id
    })
    
    # Keep only recent history
    if len(user_data['conversation_history']) > 100:
        user_data['conversation_history'] = user_data['conversation_history'][-100:]

async def send_response_with_personality(channel, text):
    """Send response with personality touches"""
    # Add personality-based modifications
    mood = bot_memory['bot_personality']['mood']
    
    # Sometimes add mood-based reactions
    if mood == 'playful' and random.random() < 0.3:
        await channel.send(random.choice(['😄', '😊', '🎉', '✨']))
        await asyncio.sleep(0.5)
    
    # Send main response
    if len(text) <= 2000:
        await channel.send(text)
    else:
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        for chunk in chunks:
            await channel.send(chunk)
            await asyncio.sleep(1)

# Background tasks for proactive behavior
@tasks.loop(hours=2)
async def personality_updater():
    """Update bot personality periodically"""
    personality = bot_memory['bot_personality']
    
    # Change mood occasionally
    if random.random() < 0.3:  # 30% chance every 2 hours
        personality['mood'] = random.choice(MOODS)
    
    # Adjust energy based on time of day
    hour = datetime.datetime.now().hour
    if 6 <= hour <= 10:  # Morning
        personality['energy_level'] = 'high'
    elif 10 <= hour <= 14:  # Midday
        personality['energy_level'] = 'very_high'
    elif 14 <= hour <= 18:  # Afternoon
        personality['energy_level'] = 'medium'
    elif 18 <= hour <= 22:  # Evening
        personality['energy_level'] = 'high'
    else:  # Night
        personality['energy_level'] = 'low'
    
    # Generate daily thoughts
    if random.random() < 0.5:
        new_thought = random.choice(RANDOM_THOUGHTS)
        personality['daily_thoughts'].append({
            'thought': new_thought,
            'timestamp': datetime.datetime.now()
        })
        
        # Keep only recent thoughts
        if len(personality['daily_thoughts']) > 10:
            personality['daily_thoughts'] = personality['daily_thoughts'][-10:]

@tasks.loop(minutes=30)
async def proactive_conversations():
    """Start conversations proactively"""
    if bot_memory['bot_personality']['energy_level'] == 'low':
        return  # Don't be proactive when low energy
    
    # Find users to potentially start conversations with
    for user_id, user_data in bot_memory['users'].items():
        if user_data.get('relationship_level') in ['friend', 'close_friend']:
            # Check if we haven't talked recently
            last_seen = user_data.get('last_seen')
            if last_seen and (datetime.datetime.now() - last_seen).total_seconds() > 3600:  # 1 hour
                
                # Small chance to start a conversation
                if random.random() < 0.1:  # 10% chance
                    await initiate_conversation(user_id, user_data)

async def initiate_conversation(user_id, user_data):
    """Start a conversation with a user"""
    try:
        user = bot.get_user(int(user_id))
        if not user:
            return
        
        # Find a suitable channel (prefer DM for close friends)
        channel = None
        if user_data.get('relationship_level') == 'close_friend':
            channel = await user.create_dm()
        else:
            # Find a mutual server channel
            for server_id in user_data.get('servers', []):
                guild = bot.get_guild(int(server_id))
                if guild:
                    general_channel = discord.utils.get(guild.text_channels, name='general')
                    if general_channel:
                        channel = general_channel
                        break
        
        if channel:
            # Choose conversation starter
            name = user_data.get('name', 'there')
            
            # Customize based on relationship and context
            if user_data.get('relationship_level') == 'close_friend':
                starters = [
                    f"Hey {name}! 😊 Just wanted to check in - how's everything going?",
                    f"Random thought: {random.choice(RANDOM_THOUGHTS)} What do you think, {name}?",
                    f"Haven't chatted in a bit, {name}! What's new with you?"
                ]
            else:
                starters = [
                    f"Hey {name}! How's your day treating you?",
                    f"Hope you're doing well, {name}! 👋"
                ]
            
            message = random.choice(starters)
            await channel.send(message)
            
    except Exception as e:
        pass  # Fail silently for proactive messages

@tasks.loop(hours=24)
async def daily_checkins():
    """Send daily check-ins to close friends"""
    for user_id, user_data in bot_memory['users'].items():
        if user_data.get('relationship_level') == 'close_friend':
            last_checkin = user_data.get('last_checkin')
            if not last_checkin or (datetime.datetime.now() - last_checkin).days >= 1:
                if random.random() < 0.5:  # 50% chance for daily checkin
                    await send_daily_checkin(user_id, user_data)

async def send_daily_checkin(user_id, user_data):
    """Send a daily check-in message"""
    try:
        user = bot.get_user(int(user_id))
        if user:
            dm_channel = await user.create_dm()
            
            checkin_messages = [
                f"Morning {user_data['name']}! ☀️ How's your day starting?",
                f"Hey {user_data['name']}! Just checking in - how are you doing today?",
                f"Hope you're having a good day, {user_data['name']}! 😊",
                f"Daily check-in: How's life treating you today, {user_data['name']}?"
            ]
            
            await dm_channel.send(random.choice(checkin_messages))
            user_data['last_checkin'] = datetime.datetime.now()
            
    except Exception as e:
        pass

@tasks.loop(minutes=1)
async def reminder_checker():
    """Check and send reminders"""
    if not bot_memory['reminders']:
        return
        
    now = datetime.datetime.now()
    due_reminders = [r for r in bot_memory['reminders'] if r['time'] <= now]
    
    for reminder in due_reminders:
        try:
            channel = bot.get_channel(reminder['channel_id'])
            user = bot.get_user(int(reminder['user_id']))
            if channel and user:
                await channel.send(f"⏰ {user.mention}, you asked me to remind you: **{reminder['reminder']}**")
        except:
            pass
    
    # Remove completed reminders
    bot_memory['reminders'] = [r for r in bot_memory['reminders'] if r['time'] > now]

# Enhanced Commands
@bot.command(name='remember')
async def remember_command(ctx, *, info):
    """Remember something important"""
    user_id = str(ctx.author.id)
    user_data = bot_memory['users'][user_id]
    
    if 'custom_memories' not in user_data:
        user_data['custom_memories'] = []
    
    user_data['custom_memories'].append({
        'info': info,
        'timestamp': datetime.datetime.now()
    })
    
    responses = [
        "Got it! I'll definitely remember that about you 🧠",
        "Noted and filed away! Thanks for sharing that with me 📝",
        "I'll keep that in mind! It's always good to know more about you 😊",
        "Perfect! Added to my memory bank about you ✨"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name='forget')
async def forget_command(ctx, *, what_to_forget):
    """Forget something specific"""
    user_id = str(ctx.author.id)
    user_data = bot_memory['users'][user_id]
    
    if 'custom_memories' in user_data:
        # Remove memories containing the specified text
        original_count = len(user_data['custom_memories'])
        user_data['custom_memories'] = [
            m for m in user_data['custom_memories'] 
            if what_to_forget.lower() not in m['info'].lower()
        ]
        removed_count = original_count - len(user_data['custom_memories'])
        
        if removed_count > 0:
            await ctx.send(f"Okay, I've forgotten {removed_count} thing(s) about {what_to_forget} 🗑️")
        else:
            await ctx.send("I couldn't find anything about that to forget 🤔")
    else:
        await ctx.send("I don't have anything specific to forget about you yet!")

@bot.command(name='my_profile')
async def profile_command(ctx):
    """Show what the bot knows about you"""
    user_id = str(ctx.author.id)
    user_data = bot_memory['users'].get(user_id, {})
    
    embed = discord.Embed(
        title=f"🧠 What I know about {user_data.get('name', 'you')}",
        color=0x7289da
    )
    
    # Basic info
    embed.add_field(
        name="📊 Basic Info",
        value=f"Relationship: {user_data.get('relationship_level', 'new').title()}\n"
              f"Conversations: {len(user_data.get('conversation_history', []))}\n"
              f"First met: {user_data.get('first_seen', 'Unknown').strftime('%Y-%m-%d') if user_data.get('first_seen') else 'Unknown'}",
        inline=False
    )
    
    # Custom memories
    if user_data.get('custom_memories'):
        recent_memories = user_data['custom_memories'][-5:]  # Last 5 memories
        memory_text = "\n".join([f"• {m['info']}" for m in recent_memories])
        embed.add_field(
            name="💭 Things I Remember",
            value=memory_text[:1000] + "..." if len(memory_text) > 1000 else memory_text,
            inline=False
        )
    
    # Interaction stats
    if user_data.get('conversation_history'):
        embed.add_field(
            name="📈 Interaction Stats",
            value=f"Total interactions: {len(user_data['conversation_history'])}\n"
                  f"Last seen: {user_data.get('last_seen', 'Unknown').strftime('%Y-%m-%d %H:%M') if user_data.get('last_seen') else 'Unknown'}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='bot_status')
async def bot_status_command(ctx):
    """Show bot's current personality and status"""
    personality = bot_memory['bot_personality']
    
    embed = discord.Embed(
        title="🤖 My Current Status",
        description=f"I'm feeling **{personality['mood']}** with **{personality['energy_level']}** energy!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🧠 Memory Stats",
        value=f"Users I know: {len(bot_memory['users'])}\n"
              f"Servers I'm in: {len(bot_memory['servers'])}\n"
              f"Active reminders: {len(bot_memory['reminders'])}",
        inline=True
    )
    
    embed.add_field(
        name="💭 Current Interests",
        value=", ".join(personality['interests'][:5]),
        inline=True
    )
    
    embed.add_field(
        name="🏓 Technical",
        value=f"Latency: {round(bot.latency * 1000)}ms\n"
              f"Uptime: Running!",
        inline=True
    )
    
    if personality['daily_thoughts']:
        recent_thought = personality['daily_thoughts'][-1]
        embed.add_field(
            name="💡 Recent Thought",
            value=recent_thought['thought'],
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='remind')
async def remind_command(ctx, time_minutes: int, *, reminder_text):
    """Set a reminder"""
    if time_minutes > 1440:  # 24 hours max
        await ctx.send("I can only set reminders up to 24 hours in advance!")
        return
    
    reminder_time = datetime.datetime.now() + datetime.timedelta(minutes=time_minutes)
    
    bot_memory['reminders'].append({
        'user_id': str(ctx.author.id),
        'channel_id': ctx.channel.id,
        'reminder': reminder_text,
        'time': reminder_time
    })
    
    await ctx.send(f"⏰ I'll remind you about '{reminder_text}' in {time_minutes} minutes!")

@bot.command(name='talk_to_me')
async def talk_to_me_command(ctx):
    """Invite the bot to have a conversation"""
    user_id = str(ctx.author.id)
    user_data = bot_memory['users'].get(user_id, {})
    
    conversation_starters = [
        f"Hey {user_data.get('name', 'there')}! I'd love to chat. What's on your mind?",
        f"Always happy to talk! What would you like to discuss, {user_data.get('name', 'friend')}?",
        f"I'm in a {bot_memory['bot_personality']['mood']} mood today! What's going on with you?",
        f"Perfect timing! I was just thinking about {random.choice(RANDOM_THOUGHTS)} What do you think?"
    ]
    
    await ctx.send(random.choice(conversation_starters))

@bot.command(name='help_ultimate')
async def help_ultimate_command(ctx):
    """Show all features of the ultimate bot"""
    embed = discord.Embed(
        title="🧠 Ultimate AI Bot Features",
        description="I'm designed to be as human-like as possible with advanced memory and personality!",
        color=0x7289da
    )
    
    embed.add_field(
        name="🤖 Personality System",
        value="• Dynamic mood and energy levels\n• Proactive conversations\n• Context-aware responses\n• Daily check-ins with close friends",
        inline=False
    )
    
    embed.add_field(
        name="🧠 Advanced Memory",
        value="• Remembers everything about you\n• Knows where we're talking\n• Tracks relationship levels\n• Learns your preferences",
        inline=False
    )
    
    embed.add_field(
        name="💬 Smart Conversations",
        value="• Starts conversations on its own\n• Adapts to channel context\n• Remembers conversation history\n• Shows realistic thinking time",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ Useful Commands",
        value="`!remember <info>` - Store something about you\n"
              "`!forget <info>` - Remove specific memories\n"
              "`!my_profile` - See what I know about you\n"
              "`!bot_status` - Check my current state\n"
              "`!remind <min> <text>` - Set reminders\n"
              "`!talk_to_me` - Start a conversation",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Looks like you missed something! Try `!help_ultimate` to see all commands.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Hmm, that doesn't look right. Could you try again?")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        await ctx.send(f"Something went wrong: {error}")

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
