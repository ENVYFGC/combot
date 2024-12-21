import discord
from discord.ext import commands
from discord.ui import View, Button
from googleapiclient.discovery import build
from dotenv import load_dotenv
import re
import json
import os

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Intents and bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Combo data structure
combo_data = {}
COMBO_FILE = "combo_data.json"

# Load combos from file
def load_combos():
    global combo_data
    if os.path.exists(COMBO_FILE):
        with open(COMBO_FILE, "r") as file:
            combo_data = json.load(file)
    else:
        combo_data = {}

# Save combos to file
def save_combos():
    with open(COMBO_FILE, "w") as file:
        json.dump(combo_data, file, indent=4)

# Function to fetch videos from a YouTube playlist
def fetch_playlist_videos(playlist_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=50
    )
    response = request.execute()
    videos = []

    for item in response['items']:
        video_id = item['snippet']['resourceId']['videoId']
        title = item['snippet']['title']
        description = item['snippet']['description']
        link = f"https://www.youtube.com/watch?v={video_id}"
        videos.append({
            "title": title,
            "description": description,
            "link": link
        })

    return videos

# Function to parse the description for notation and notes
def parse_description(description):
    notation_match = re.search(r"(?i)notation:\s*(.+)", description)
    notes_match = re.search(r"(?i)note(?:s)?:\s*(.+)", description)
    
    notation = notation_match.group(1).replace(",", " >") if notation_match else "Unknown Notation"
    notes = notes_match.group(1).strip() if notes_match else "No Notes Provided"
    
    notes = notes.split("\n")[0]  # Capture only the first line of notes
    
    return {
        "notation": notation,
        "notes": notes
    }

# Function to update combo data dynamically
def update_combo_data(playlist_id, starter):
    videos = fetch_playlist_videos(playlist_id)
    combo_data[starter] = []

    for video in videos:
        parsed_data = parse_description(video['description'])
        combo_data[starter].append({
            "notation": parsed_data["notation"],
            "notes": parsed_data["notes"],
            "link": video["link"]
        })

    # Save updated combo data to file
    save_combos()

# Pagination for combo listing
class PaginationView(View):
    def __init__(self, combos, starter, user):
        super().__init__(timeout=None)
        self.combos = combos
        self.page = 0
        self.starter = starter
        self.user = user

    async def update_embed(self):
        start = self.page * 10
        end = start + 10
        combo_page = self.combos[start:end]

        embed = discord.Embed(
            title=f"Combos for {self.starter} (Page {self.page + 1}/{(len(self.combos) + 9) // 10})",
            description="Here are the available combos:",
            color=discord.Color.blue()
        )

        for i, combo in enumerate(combo_page, start=start):
            notation = combo["notation"]
            notes = combo["notes"]
            embed.add_field(
                name=f"**{i + 1}. {notation}**",
                value=f"**Notes**: {notes}" if notes != "No Notes Provided" else "No additional notes.",
                inline=False,
            )

        embed.set_footer(text="Reply with a combo number to get the link.")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You can't interact with this pagination view.", ephemeral=True)
            return

        if self.page > 0:
            self.page -= 1
            embed = await self.update_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("You can't interact with this pagination view.", ephemeral=True)
            return

        if (self.page + 1) * 10 < len(self.combos):
            self.page += 1
            embed = await self.update_embed()
            await interaction.response.edit_message(embed=embed, view=self)

# Command to list combos for a starter
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.isdigit():
        combo_index = int(message.content) - 1
        for starter, combos in combo_data.items():
            if 0 <= combo_index < len(combos):
                combo = combos[combo_index]
                await message.channel.send(combo['link'])
                await message.delete()  # Delete the user's response
                return

    await bot.process_commands(message)

class StarterView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for starter in combo_data.keys():
            button = Button(label=starter, style
