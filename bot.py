import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import yt_dlp
import asyncio
import logging

log = logging.getLogger(__name__)

#log.info("Starting MusicBot. Logged in as %s", self.user)
log.info("Discord.py version: %s", discord.version_info)
print(discord.version_info)

ytdl_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume = 0.5):
        super().__init__(source, volume)
        # self.requester = 

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    # Pull a URL with ytdl and return an FFmpeg audio source for use with Discord
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Get our guild ID configured
load_dotenv()
CURRENT_GUILD = discord.Object(int(os.getenv('GUILD')))


class MusicBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

        # Use a CommandTree for storing application commands
        self.tree = app_commands.CommandTree(self)
        self.current_vc = None

    # sync app commands to one guild (squadgang) so they show up to users
    async def setup_hook(self):
        self.tree.copy_global_to(guild=CURRENT_GUILD)
        await self.tree.sync(guild=CURRENT_GUILD)

intents = discord.Intents.default()
client = MusicBot(intents=intents)

# Basic logging - end of setup tasks
@client.event
async def on_ready():
    log.info("Starting MusicBot. Logged in as %s", client.user)
    log.info("Discord.py version: %s", discord.version_info)

# Register commands
@client.tree.command()
async def hello(interaction: discord.Interaction):
    """ Says hi back to user """
    await interaction.response.send_message(f'Hi there, {interaction.user.mention}!')

# Join the user's current voice channel
@client.tree.command()
async def join(interaction : discord.Interaction):
    """ Join the current voice channel of the user """
    if(interaction.user.voice):
        await interaction.response.send_message(f"Joining channel {interaction.user.voice.channel.name}...")
        client.current_vc = await interaction.user.voice.channel.connect()
    else:
        await interaction.response.send_message(f"You aren't currently in a channel!")

# Play audio track from specified URL
@client.tree.command()
@app_commands.describe(
    url="URL to play"
)
async def play(interaction: discord.Interaction, url: str):
    """ plays a url """
    #await interaction.response.send_message(f"Attempting to play {url}")
    if(client.current_vc == None):
        pass

    if(client.current_vc):
        await interaction.response.send_message(f"Attempting to play {url}")
        player = await YTDLSource.from_url(url, stream=True)
        guild = interaction.guild
        guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
    else:
        await interaction.response.send_message(f"Not currently in a voice channel.")

# Pause the current audio stream
@client.tree.command()
async def pause(interaction: discord.Interaction):
    """ Pauses the current audio """
    if(client.current_vc):
        if(client.current_vc.is_paused()):
            await interaction.response.send_message(f"Audio is already paused.")
            return
        client.current_vc.pause()
        await interaction.response.send_message(f"Audio paused.")
    else:
        await interaction.response.send_message("Not currently in a voice channel.")

# Resume the audio stream if paused
@client.tree.command()
async def resume(interaction: discord.Interaction):
    """ Resumes the current audio """
    if(client.current_vc):
        if(client.current_vc.is_paused()):
            await interaction.response.send_message(f"Resuming audio...")
            client.current_vc.resume()
        else:
            await interaction.response.send_message(f"Audio is not paused.")
    else:
        await interaction.response.send_message("Not currently in a voice channel.")

# Leave the user's current voice channel
@client.tree.command()
async def leave(interaction: discord.Interaction):
    """ Leave the user's current voice channel """
    if(client.current_vc):
        await client.current_vc.disconnect()
        await interaction.response.send_message(f"Leaving channel...")
        client.current_vc = None
    else:
        await interaction.response.send_message(f"Not currently in a voice channel.")

# Actually run the bot
client.run(os.getenv('BOT_TOKEN'))