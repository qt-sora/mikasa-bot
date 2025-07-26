import os
import logging
import asyncio
import random
from io import BytesIO
from typing import Optional
import requests
from PIL import Image
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# Bot configuration links
BOT_LINKS = {
    "updates_channel": "https://t.me/YOUR_CHANNEL",
    "support_group": "https://t.me/YOUR_GROUP",
    "developer": "https://t.me/YOUR_USERNAME"
}

# Bot commands dictionary
BOT_COMMANDS = {
    "start": {
        "command": "start",
        "description": "🏠 Start the bot and see main menu"
    },
    "generate": {
        "command": "generate", 
        "description": "🎨 Generate an image from text prompt"
    },
    "help": {
        "command": "help",
        "description": "❓ Show help and usage guide"
    },
    "settings": {
        "command": "settings",
        "description": "⚙️ Manage bot settings"
    }
}

# Random photos for start command captions
RANDOM_PHOTOS = [
    "https://i.postimg.cc/RhtZR0sF/New-Project-235-28-ED42-B.png",
    "https://i.postimg.cc/k4z5KSyz/New-Project-235-8-AFAF2-A.png",
    "https://i.postimg.cc/N0NFGS2g/New-Project-235-09-DD635.png",
    "https://i.postimg.cc/6pfTgy94/New-Project-235-3-D5-D3-F1.png",
    "https://i.postimg.cc/dVYL58KK/New-Project-235-4235-F6-E.png",
    "https://i.postimg.cc/tCPsdBw5/New-Project-235-3459944.png",
    "https://i.postimg.cc/8k7Jcpbx/New-Project-235-3079612.png",
    "https://i.postimg.cc/MXk8KbYZ/New-Project-235-9-A5-CAF0.png",
    "https://i.postimg.cc/qRRrm7Rr/New-Project-235-FE6-E983.png",
    "https://i.postimg.cc/zfp5Shqp/New-Project-235-5-B71865.png",
    "https://i.postimg.cc/BvJ4KpfX/New-Project-235-739-D6-D5.png",
    "https://i.postimg.cc/t439JffK/New-Project-235-B98-C0-D6.png",
    "https://i.postimg.cc/pLb22x0Q/New-Project-235-28-F28-CA.png",
    "https://i.postimg.cc/MHgzf8zS/New-Project-235-AB8-F78-F.png",
    "https://i.postimg.cc/wvfqHmP3/New-Project-235-5952549.png",
    "https://i.postimg.cc/mrSZXqyY/New-Project-235-D231974.png",
    "https://i.postimg.cc/vmyHvMf8/New-Project-235-0-BC9-C74.png",
    "https://i.postimg.cc/J4ynrpR8/New-Project-235-88-BC2-D0.png",
    "https://i.postimg.cc/HnNk0y4F/New-Project-235-7462142.png",
    "https://i.postimg.cc/tT2TTf1q/New-Project-235-CE958-B1.png",
    "https://i.postimg.cc/Xv6XD9Sb/New-Project-235-0-E24-C88.png",
    "https://i.postimg.cc/RhpNP89s/New-Project-235-FC3-A4-AD.png",
    "https://i.postimg.cc/x841BwFW/New-Project-235-FFA9646.png",
    "https://i.postimg.cc/5NC7HwSV/New-Project-235-A06-DD7-A.png",
    "https://i.postimg.cc/HnPqpdm9/New-Project-235-9-E45-B87.png",
    "https://i.postimg.cc/1tSPTmRg/New-Project-235-AB394-C0.png",
    "https://i.postimg.cc/8ct1M2S7/New-Project-235-9-CAE309.png",
    "https://i.postimg.cc/TYtwDDdt/New-Project-235-2-F658-B0.png",
    "https://i.postimg.cc/xdwqdVfY/New-Project-235-68-BAF06.png",
    "https://i.postimg.cc/hPczxn9t/New-Project-235-9-E9-A004.png",
    "https://i.postimg.cc/jjFPQ1Rk/New-Project-235-A1-E7-CC1.png",
    "https://i.postimg.cc/TPqJV0pz/New-Project-235-CA65155.png",
    "https://i.postimg.cc/wBh0WHbb/New-Project-235-89799-CD.png",
    "https://i.postimg.cc/FKdQ1fzk/New-Project-235-C377613.png",
    "https://i.postimg.cc/rpKqWnnm/New-Project-235-CFD2548.png",
    "https://i.postimg.cc/g0kn7HMF/New-Project-235-C4-A32-AC.png",
    "https://i.postimg.cc/XY6jRkY1/New-Project-235-28-DCBC9.png",
    "https://i.postimg.cc/SN32J9Nc/New-Project-235-99-D1478.png",
    "https://i.postimg.cc/8C86n62T/New-Project-235-F1556-B9.png",
    "https://i.postimg.cc/RCGwVqHT/New-Project-235-5-BBB339.png",
    "https://i.postimg.cc/pTfYBZyN/New-Project-235-17-D796-A.png",
    "https://i.postimg.cc/zGgdgJJc/New-Project-235-165-FE5-A.png"
]

# Welcome messages
WELCOME_MESSAGES = {
    "main": "🎨 <b>Welcome to AI Image Generator Bot!</b>\n\n"
            "I can generate stunning images using Pollinations AI. "
            "Create anime art, realistic photos, fantasy scenes, and much more!\n\n"
            "<b>✨ Features:</b>\n"
            "• Multiple FLUX models available\n"
            "• High-quality image generation\n"
            "• Completely free and unlimited\n"
            "• Fast generation (10-30 seconds)\n\n"
            "<b>🚀 Quick Start:</b>\n"
            "Just type your prompt or use /generate command!",
    
    "group": "🌸 <b>Hello everyone!</b>\n\n"
             "I'm your AI Image Generator Bot! In groups, use:\n\n"
             "<code>mikasa [your prompt here]</code>\n\n"
             "<b>Example:</b> <code>mikasa cute anime girl with blue hair</code>\n\n"
             "I'll generate amazing images for your group! 🎨",
    
    "private": "🎨 <b>Welcome to your personal AI Art Studio!</b>\n\n"
               "Here you can generate unlimited images completely free!\n\n"
               "<b>Just type any description and I'll create it for you!</b>\n\n"
               "Examples:\n"
               "• <code>anime girl with purple hair</code>\n"
               "• <code>cyberpunk city at night</code>\n"
               "• <code>cute cat in a garden</code>"
}

# Help messages
HELP_MESSAGES = {
    "basic": "🤖 <b>AI Image Generator Bot Help</b>\n\n"
             "<b>Quick Start:</b>\n"
             "• Private: Type any prompt\n"
             "• Groups: <code>mikasa [prompt]</code>\n"
             "• Commands: <code>/generate [prompt]</code>\n\n"
             "<b>Example:</b>\n"
             "<code>anime girl with blue hair</code>\n\n"
             "🌸 <b>Powered by Pollinations AI</b>",
    
    "expanded": "🤖 <b>AI Image Generator Bot - Complete Guide</b>\n\n"
                "<b>🎨 Basic Usage:</b>\n"
                "• Type any prompt directly (private chat only)\n"
                "• Use <code>/generate [prompt]</code> anywhere\n"
                "• Click buttons for quick actions\n\n"
                "<b>🌸 Group Usage:</b>\n"
                "• Type <code>mikasa [your prompt]</code> in groups\n"
                "• Example: <code>mikasa cute anime girl with blue hair</code>\n"
                "• Bot will reply to your message with generated image\n\n"
                "<b>💡 Advanced Prompt Tips:</b>\n"
                "• Be descriptive: 'anime girl with blue hair and green eyes'\n"
                "• Add art styles: 'realistic', 'cartoon', 'oil painting', 'watercolor'\n"
                "• Specify details: colors, lighting, mood, background\n"
                "• Use quality terms: 'detailed', 'high quality', '4k', 'masterpiece'\n"
                "• Include camera settings: 'close-up', 'wide shot', 'portrait'\n\n"
                "<b>🎯 Style Keywords:</b>\n"
                "• <code>anime, manga, kawaii</code> - Japanese animation style\n"
                "• <code>realistic, photorealistic</code> - Real photo look\n"
                "• <code>cyberpunk, futuristic, sci-fi</code> - Technology themes\n"
                "• <code>fantasy, magical, ethereal</code> - Fantasy elements\n"
                "• <code>vintage, retro, classic</code> - Old-style aesthetics\n\n"
                "<b>⚡ Available Commands:</b>\n"
                "• <code>/start</code> - Main menu and bot info\n"
                "• <code>/generate</code> - Full generation interface\n"
                "• <code>/help</code> - This help guide\n\n"
                "<b>🛠️ Features:</b>\n"
                "• 4 AI models (FLUX, Turbo, Realism, Anime)\n"
                "• Multiple image sizes (512x512 to 1024x1024)\n"
                "• Style presets for easy enhancement\n"
                "• Random prompt generator\n"
                "• Completely free and unlimited\n\n"
                "<b>🌟 Example Prompts:</b>\n"
                "• <code>cyberpunk city at night, neon lights, rain</code>\n"
                "• <code>cute cat sitting in a garden, watercolor style</code>\n"
                "• <code>fantasy dragon flying over mountains, detailed</code>\n"
                "• <code>beautiful anime girl, long purple hair, green eyes</code>\n"
                "• <code>futuristic robot, metallic, glowing blue eyes</code>\n\n"
                "<b>🔧 Powered by Pollinations AI</b>\n"
                "Fast, reliable, and completely free image generation!"
}

# Status messages
STATUS_MESSAGES = {
    "generating": [
        "🌺", "🎨", "✨", "🌸", "🎭", "🖼️", "🌟", "💫", "🎪", "🎯"
    ],
    "processing": [
        "🔮 Creating magic...",
        "🎨 Painting your vision...",
        "✨ Generating artwork...",
        "🌟 Crafting your image...",
        "🖼️ Building masterpiece...",
        "🎭 Bringing art to life...",
        "💫 Weaving pixels...",
        "🌺 Blooming creation..."
    ]
}

# Error messages
ERROR_MESSAGES = {
    "generation_failed": "❌ <b>Generation failed</b>\n\n"
                        "The image generation service is currently unavailable. This might be due to:\n"
                        "• Service maintenance\n"
                        "• Network issues\n"
                        "• Server overload\n\n"
                        "<b>Solutions:</b>\n"
                        "• Try again in a few minutes\n"
                        "• Try with a different prompt\n"
                        "• Use /generate to try different settings",
    
    "general_error": "❌ <b>An error occurred</b>\n\n"
                    "Please try again later or contact support.",
    
    "no_prompt": "🌸 <b>Hey there!</b>\n\n"
                "I see you called me with 'mikasa'! To generate an image, use:\n\n"
                "<code>mikasa [your prompt here]</code>\n\n"
                "<b>Example:</b>\n"
                "<code>mikasa cute anime girl with blue hair</code>",
    
    "network_error": "🌐 <b>Network Error</b>\n\n"
                    "Cannot connect to the image generation service right now.\n"
                    "Please try again in a few moments.",
    
    "timeout_error": "⏰ <b>Request Timeout</b>\n\n"
                    "The generation took too long. This usually happens when:\n"
                    "• The service is overloaded\n"
                    "• Complex prompts need more time\n\n"
                    "Please try again or simplify your prompt."
}

# Success messages
SUCCESS_MESSAGES = {
    "image_generated": "🎨 <b>Generated Image</b>\n\n<b>Prompt:</b> {prompt}",
    "image_for_user": "🎨 <b>Generated for</b> @{username}\n\n<b>Prompt:</b> {prompt}",
    "model_selected": "✅ <b>Model Selected</b>\n\n<b>Service:</b> {service}\n<b>Model:</b> {model}\n<b>Description:</b> {description}\n\nYou can now generate images with this model!",
    "size_updated": "✅ <b>Size updated to {width}x{height}</b>\n\nYou can now generate images with the new size!",
    "style_applied": "🎨 <b>Style Applied: {style}</b>\n\n<b>Style modifier:</b> {modifier}\n\nThis will be added to your prompts automatically!",
    "settings_reset": "🔄 <b>Settings Reset</b>\n\nAll settings restored to default values:\n• Service: Pollinations AI\n• Model: FLUX\n• Size: 512x512\n• Style: None\n\nReady to generate!"
}

# Menu messages
MENU_MESSAGES = {
    "generate_menu": "🎨 <b>AI Image Generator</b>\n\n"
                    "Choose an option or provide a prompt:\n\n"
                    "<b>Usage:</b> <code>/generate your prompt here</code>\n\n"
                    "<b>Example:</b> <code>/generate anime girl with blue hair</code>",
    
    "model_selection": "🤖 <b>AI Model Selection</b>\n\n"
                      "<b>Current Service:</b> {service}\n"
                      "<b>Current Model:</b> {model}\n\n"
                      "Choose your preferred AI model:",
    
    "settings_menu": "⚙️ <b>Settings Menu</b>\n\n"
                    "<b>Service:</b> {service}\n"
                    "<b>Model:</b> {model}\n"
                    "<b>Size:</b> {width}x{height}\n\n"
                    "Customize your generation settings:",
    
    "style_presets": "🌟 <b>Style Presets</b>\n\n"
                    "<b>Current Style:</b> {style}\n\n"
                    "Choose a style to automatically enhance your prompts:",
    
    "size_options": "📊 <b>Image Size Options</b>\n\n"
                   "<b>Current Size:</b> {size}\n\n"
                   "Choose your preferred image dimensions:",
    
    "help_menu": "❓ <b>Help & Guide</b>\n\n"
                "<b>🎨 How to Generate:</b>\n"
                "• Type any text description\n"
                "• Use /generate [prompt]\n"
                "• Click 'Generate Sample'\n\n"
                "<b>💡 Prompt Tips:</b>\n"
                "• Be descriptive: 'anime girl with blue hair'\n"
                "• Add style: 'realistic', 'cartoon', 'oil painting'\n"
                "• Specify details: colors, lighting, mood\n"
                "• Use quality terms: 'detailed', 'high quality', '4k'\n\n"
                "<b>⚡ Commands:</b>\n"
                "• /generate - Create image\n"
                "• /help - Show this guide\n"
                "• /start - Return to main menu\n\n"
                "<b>🌟 Example Prompts:</b>\n"
                "• 'cyberpunk city at night, neon lights'\n"
                "• 'cute cat in a garden, watercolor style'\n"
                "• 'fantasy dragon, detailed digital art'"
}

# Random prompts for sample generation
RANDOM_PROMPTS = [
    "futuristic cyberpunk cityscape at night with neon lights",
    "magical forest with glowing mushrooms and fairy lights",
    "steampunk airship floating above clouds",
    "cute anime cat girl with colorful hair",
    "epic dragon flying over medieval castle",
    "abstract cosmic nebula with stars and galaxies",
    "vintage car in rain-soaked city street",
    "peaceful mountain lake at sunset",
    "beautiful anime girl with long flowing hair",
    "cyberpunk samurai in neon-lit alley",
    "fantasy castle on floating island",
    "cute robot companion with glowing eyes",
    "magical portal in enchanted forest",
    "space warrior with energy sword",
    "crystal cave with rainbow reflections",
    "steampunk laboratory with brass machinery",
    "anime schoolgirl in cherry blossom garden",
    "futuristic city with flying cars",
    "mystical phoenix rising from flames",
    "underwater palace with mermaids"
]

# Style presets dictionary
STYLE_PRESETS = {
    "anime": "anime style, detailed anime art, vibrant colors",
    "realistic": "photorealistic, high detail, professional photography",
    "fantasy": "fantasy art, magical, ethereal, mystical",
    "cyberpunk": "cyberpunk style, neon lights, futuristic, dark atmosphere",
    "cartoon": "cartoon style, colorful, playful, animated",
    "oil_painting": "oil painting style, classical art, brush strokes",
    "watercolor": "watercolor painting, soft colors, artistic",
    "digital_art": "digital art, concept art, detailed illustration",
    "vintage": "vintage style, retro, classic, nostalgic",
    "minimalist": "minimalist style, clean, simple, modern"
}

# HTTP Server for uptime monitoring
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sakura bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_dummy_server():
    logger.info("🌐 Starting HTTP health check server")
    port = int(os.environ.get("PORT", 5000))
    try:
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        logger.info(f"✅ HTTP server listening on 0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Failed to start HTTP server: {e}")
        raise

def start_uptime_server():
    """Start HTTP server for uptime monitoring"""
    port = int(os.environ.get('PORT', 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), UptimeHandler)
        logger.info(f"Starting uptime server on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start uptime server: {e}")
        # Try alternative port
        try:
            port = 3000
            server = HTTPServer(('0.0.0.0', port), UptimeHandler)
            logger.info(f"Starting uptime server on alternative port {port}")
            server.serve_forever()
        except Exception as e2:
            logger.error(f"Failed to start uptime server on alternative port: {e2}")

# Pollinations AI configuration
API_SERVICE = {
    "name": "🌸 Pollinations AI",
    "url": "https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&seed={seed}&model={model}",
    "models": {
        "flux": {
            "name": "FLUX (Recommended)",
            "model_param": "flux",
            "description": "High quality, best results"
        },
        "turbo": {
            "name": "Turbo (Fast)",
            "model_param": "turbo",
            "description": "Quick generation"
        },
        "flux-realism": {
            "name": "FLUX Realism",
            "model_param": "flux-realism",
            "description": "Realistic photos"
        },
        "flux-anime": {
            "name": "FLUX Anime",
            "model_param": "flux-anime", 
            "description": "Anime and manga style"
        }
    }
}

# Default generation parameters
DEFAULT_PARAMS = {
    "width": 512,
    "height": 512,
    "seed": None,
    "model": "flux"
}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command with random photo."""
    # Select random photo
    random_photo = random.choice(RANDOM_PHOTOS)
    
    # Determine message based on chat type
    if update.effective_chat.type == 'private':
        welcome_message = WELCOME_MESSAGES["private"]
    else:
        welcome_message = WELCOME_MESSAGES["group"]
    
    # Keyboard with dynamic links
    keyboard = [
        [
            InlineKeyboardButton("📢 Updates", url=BOT_LINKS["updates_channel"]),
            InlineKeyboardButton("💬 Support", url=BOT_LINKS["support_group"])
        ],
        [
            InlineKeyboardButton("➕ Add Me To Your Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Try multiple methods to send photo
    photo_sent = False
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Method 1: Direct URL
            await update.message.reply_photo(
                photo=random_photo,
                caption=welcome_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30
            )
            photo_sent = True
            logger.info(f"✅ Photo sent successfully on attempt {attempt + 1}")
            break
            
        except Exception as e:
            logger.warning(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                # Try downloading and sending as bytes
                try:
                    response = requests.get(random_photo, timeout=20)
                    if response.status_code == 200:
                        photo_bytes = BytesIO(response.content)
                        photo_bytes.name = 'image.jpg'
                        
                        await update.message.reply_photo(
                            photo=photo_bytes,
                            caption=welcome_message,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            read_timeout=30,
                            write_timeout=30
                        )
                        photo_sent = True
                        logger.info(f"✅ Photo sent as bytes on attempt {attempt + 1}")
                        break
                except Exception as e2:
                    logger.warning(f"⚠️ Bytes method failed on attempt {attempt + 1}: {str(e2)}")
                    
                # Wait before retry
                await asyncio.sleep(1)
    
    # If all photo attempts failed, try with a different random photo
    if not photo_sent:
        try:
            # Try with a different random photo
            backup_photo = random.choice(RANDOM_PHOTOS)
            response = requests.get(backup_photo, timeout=15)
            if response.status_code == 200:
                photo_bytes = BytesIO(response.content)
                photo_bytes.name = 'backup.jpg'
                
                await update.message.reply_photo(
                    photo=photo_bytes,
                    caption=welcome_message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                logger.info("✅ Backup photo sent successfully")
                photo_sent = True
        except Exception as e:
            logger.error(f"❌ Backup photo also failed: {str(e)}")
    
    # If still no photo sent, send with a placeholder image URL (reliable)
    if not photo_sent:
        try:
            # Use a reliable placeholder service
            placeholder_url = "https://via.placeholder.com/512x512/FF69B4/FFFFFF?text=AI+Image+Generator"
            await update.message.reply_photo(
                photo=placeholder_url,
                caption=welcome_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            logger.info("✅ Placeholder photo sent successfully")
        except Exception as e:
            logger.error(f"❌ Even placeholder failed, this shouldn't happen: {str(e)}")
            # Last resort - send text (but this should never happen)
            await update.message.reply_text(
                f"🤖 {welcome_message}",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    keyboard = [
        [
            InlineKeyboardButton("📖 Expand Guide", callback_data="expand_guide")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        HELP_MESSAGES["basic"], 
        parse_mode=ParseMode.HTML, 
        reply_markup=reply_markup
    )

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /generate command with all functionality."""
    if not context.args:
        # Show generate menu with options
        keyboard = [
            [
                InlineKeyboardButton("🤖 Select Model", callback_data="select_model"),
                InlineKeyboardButton("🎨 Generate Sample", callback_data="sample")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ],
            [
                InlineKeyboardButton("🌟 Style Presets", callback_data="style_presets"),
                InlineKeyboardButton("🎲 Random Prompt", callback_data="random_prompt")
            ],
            [
                InlineKeyboardButton("📊 Image Sizes", callback_data="size_options"),
                InlineKeyboardButton("🔄 Reset Settings", callback_data="reset_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            MENU_MESSAGES["generate_menu"],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return
    
    prompt = " ".join(context.args)
    await generate_image(update, context, prompt)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages as image generation prompts."""
    message_text = update.message.text.strip()
    
    # Skip if message starts with /
    if message_text.startswith('/'):
        return
    
    # Check for mikasa keyword (case insensitive)
    if message_text.lower().startswith('mikasa'):
        await handle_mikasa_keyword(update, context, message_text)
        return
        
    # Regular prompt generation (only in private chats)
    if update.effective_chat.type == 'private':
        await generate_image(update, context, message_text)

async def handle_mikasa_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str) -> None:
    """Handle mikasa keyword in groups."""
    # Extract prompt after 'mikasa'
    parts = message_text.split(None, 1)  # Split on whitespace, max 1 split
    
    if len(parts) == 1:
        # Only "mikasa" was said, no prompt
        keyboard = [
            [
                InlineKeyboardButton("🗑️ Delete", callback_data="delete_message")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            ERROR_MESSAGES["no_prompt"],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        # mikasa with prompt - generate image
        prompt = parts[1]
        await generate_image_with_reply(update, context, prompt)

async def generate_image_with_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str) -> None:
    """Generate image and reply to the original message."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_model = context.user_data.get('model', 'flux')
    
    # Update settings with current model
    user_settings['model'] = current_model
    
    # Apply style suffix if available
    style_suffix = context.user_data.get('style_suffix', '')
    if style_suffix:
        prompt = f"{prompt}, {style_suffix}"
    
    # Send random status emoji
    status_emoji = random.choice(STATUS_MESSAGES["generating"])
    status_message = await update.message.reply_text(status_emoji)
    
    try:
        image_bytes = await generate_image_pollinations(prompt, user_settings)
        
        if image_bytes:
            # Edit the emoji message with the generated image
            image_stream = BytesIO(image_bytes)
            
            # Get clean prompt (remove style suffix for display)
            clean_prompt = prompt
            if context.user_data.get('style_suffix'):
                clean_prompt = prompt.replace(', ' + context.user_data.get('style_suffix'), '')
            
            username = update.effective_user.username or update.effective_user.first_name
            caption = SUCCESS_MESSAGES["image_for_user"].format(
                username=username,
                prompt=clean_prompt
            )
            
            await context.bot.edit_message_media(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                media=InputMediaPhoto(
                    media=image_stream,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            )
            
        else:
            # Generation failed - edit the emoji message with error
            await status_message.edit_text(
                ERROR_MESSAGES["generation_failed"], 
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        try:
            await status_message.edit_text(
                ERROR_MESSAGES["general_error"],
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

async def generate_image_pollinations(prompt: str, settings: dict) -> Optional[bytes]:
    """Generate image using Pollinations AI."""
    try:
        seed = settings.get('seed') or random.randint(1, 1000000)
        model = settings.get('model', 'flux')
        model_param = API_SERVICE["models"].get(model, {}).get('model_param', 'flux')
        
        # Format URL with parameters
        url = API_SERVICE["url"].format(
            prompt=requests.utils.quote(prompt),
            width=settings.get('width', 512),
            height=settings.get('height', 512),
            seed=seed,
            model=model_param
        )
        
        # Add style modifiers for better quality
        enhanced_prompt = f"{prompt}, detailed, high quality, 8k"
        url = url.replace(requests.utils.quote(prompt), requests.utils.quote(enhanced_prompt))
        
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Pollinations API error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error with Pollinations: {str(e)}")
        return None

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str) -> None:
    """Generate an image based on the given prompt."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_model = context.user_data.get('model', 'flux')
    
    # Update settings with current model
    user_settings['model'] = current_model
    
    # Apply style suffix if available
    style_suffix = context.user_data.get('style_suffix', '')
    if style_suffix:
        prompt = f"{prompt}, {style_suffix}"
    
    # Determine which message object to use
    if update.callback_query:
        chat_id = update.effective_chat.id
        send_method = context.bot.send_message
    else:
        chat_id = None
        send_method = update.message.reply_text
    
    # Send random status emoji or message
    status_text = random.choice(STATUS_MESSAGES["generating"])
    if chat_id:
        status_message = await send_method(
            chat_id=chat_id,
            text=status_text
        )
    else:
        status_message = await send_method(status_text)
    
    try:
        image_bytes = await generate_image_pollinations(prompt, user_settings)
        
        if image_bytes:
            # Edit the status message with the generated image
            image_stream = BytesIO(image_bytes)
            
            # Get clean prompt (remove style suffix for display)
            clean_prompt = prompt
            if context.user_data.get('style_suffix'):
                clean_prompt = prompt.replace(', ' + context.user_data.get('style_suffix'), '')
            
            caption = SUCCESS_MESSAGES["image_generated"].format(prompt=clean_prompt)
            
            await context.bot.edit_message_media(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                media=InputMediaPhoto(
                    media=image_stream,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            )
            
        else:
            # Generation failed - edit the status message with error
            await status_message.edit_text(
                ERROR_MESSAGES["generation_failed"], 
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        try:
            await status_message.edit_text(
                ERROR_MESSAGES["general_error"],
                parse_mode=ParseMode.HTML
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=ERROR_MESSAGES["general_error"],
                parse_mode=ParseMode.HTML
            )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    
    if data == "sample":
        sample_prompt = random.choice(RANDOM_PROMPTS)
        await generate_image(update, context, sample_prompt)
    
    elif data == "select_model":
        await model_selection_menu(update, context)
    
    elif data == "settings_menu":
        await settings_menu_callback(update, context)
    
    elif data == "help_menu":
        await help_menu_callback(update, context)
    
    elif data == "style_presets":
        await style_presets_menu(update, context)
    
    elif data == "random_prompt":
        random_prompt = random.choice(RANDOM_PROMPTS)
        await generate_image(update, context, random_prompt)
    
    elif data == "size_options":
        await size_options_menu(update, context)
    
    elif data.startswith("model_"):
        # Handle model selection: model_modelname
        model = data.split("_", 1)[1]
        context.user_data['model'] = model
        
        # Get model info for display
        model_info = API_SERVICE["models"].get(model, {})
        model_name = model_info.get("name", model.upper())
        
        success_text = SUCCESS_MESSAGES["model_selected"].format(
            service=API_SERVICE['name'],
            model=model_name,
            description=model_info.get('description', 'No description available')
        )
        
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                    InlineKeyboardButton("🤖 Change Model", callback_data="select_model")
                ],
                [InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")]
            ])
        )
    
    elif data.startswith("size_"):
        size_parts = data.split("_")
        if len(size_parts) == 3:
            width = int(size_parts[1])
            height = int(size_parts[2])
        else:
            size = int(size_parts[1])
            width = height = size
            
        user_settings['width'] = width
        user_settings['height'] = height
        context.user_data['settings'] = user_settings
        
        success_text = SUCCESS_MESSAGES["size_updated"].format(
            width=width,
            height=height
        )
        
        await query.edit_message_text(
            success_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                    InlineKeyboardButton("📊 More Sizes", callback_data="size_options")
                ],
                [InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")]
            ])
        )
    
    elif data.startswith("style_"):
        style = data.split("_", 1)[1]
        
        if style in STYLE_PRESETS:
            context.user_data['style_suffix'] = STYLE_PRESETS[style]
            
            success_text = SUCCESS_MESSAGES["style_applied"].format(
                style=style.replace('_', ' ').title(),
                modifier=STYLE_PRESETS[style]
            )
            
            await query.edit_message_text(
                success_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                        InlineKeyboardButton("🌟 Change Style", callback_data="style_presets")
                    ],
                    [InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")]
                ])
            )
    
    elif data == "reset_settings":
        context.user_data['settings'] = DEFAULT_PARAMS.copy()
        context.user_data['model'] = 'flux'
        context.user_data.pop('style_suffix', None)
        
        await query.edit_message_text(
            SUCCESS_MESSAGES["settings_reset"],
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")
                ],
                [InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")]
            ])
        )
    
    elif data == "back_to_generate":
        # Return to generate menu
        keyboard = [
            [
                InlineKeyboardButton("🤖 Select Model", callback_data="select_model"),
                InlineKeyboardButton("🎨 Generate Sample", callback_data="sample")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ],
            [
                InlineKeyboardButton("🌟 Style Presets", callback_data="style_presets"),
                InlineKeyboardButton("🎲 Random Prompt", callback_data="random_prompt")
            ],
            [
                InlineKeyboardButton("📊 Image Sizes", callback_data="size_options"),
                InlineKeyboardButton("🔄 Reset Settings", callback_data="reset_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MENU_MESSAGES["generate_menu"],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data == "expand_guide":
        keyboard = [
            [
                InlineKeyboardButton("📄 Minimize Guide", callback_data="minimize_guide")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            HELP_MESSAGES["expanded"],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data == "minimize_guide":
        keyboard = [
            [
                InlineKeyboardButton("📖 Expand Guide", callback_data="expand_guide")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            HELP_MESSAGES["basic"],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data == "delete_message":
        try:
            await query.message.delete()
        except Exception:
            await query.answer("Cannot delete this message.", show_alert=True)

async def model_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show AI model selection menu."""
    current_model = context.user_data.get('model', 'flux')
    
    model_text = MENU_MESSAGES["model_selection"].format(
        service=API_SERVICE['name'],
        model=current_model.upper()
    )
    
    keyboard = []
    
    # Pollinations models
    for model_key, model_info in API_SERVICE["models"].items():
        status = "✅" if current_model == model_key else ""
        keyboard.append([InlineKeyboardButton(
            f"{status} {model_info['name']}", 
            callback_data=f"model_{model_key}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            model_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            model_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings menu callback."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_model = context.user_data.get('model', 'flux')
    
    settings_text = MENU_MESSAGES["settings_menu"].format(
        service=API_SERVICE['name'],
        model=current_model.upper(),
        width=user_settings['width'],
        height=user_settings['height']
    )
    
    keyboard = [
        [
            InlineKeyboardButton("512x512", callback_data="size_512"),
            InlineKeyboardButton("768x768", callback_data="size_768"),
            InlineKeyboardButton("1024x1024", callback_data="size_1024")
        ],
        [
            InlineKeyboardButton("Portrait 512x768", callback_data="size_512_768"),
            InlineKeyboardButton("Landscape 768x512", callback_data="size_768_512")
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data="reset_settings"),
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_generate")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        settings_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def help_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help menu callback."""
    keyboard = [
        [
            InlineKeyboardButton("🎨 Try Sample", callback_data="sample"),
            InlineKeyboardButton("🤖 Select Model", callback_data="select_model")
        ],
        [InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        MENU_MESSAGES["help_menu"],
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def style_presets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show style presets menu."""
    current_style = context.user_data.get('style_suffix', 'None')
    
    style_text = MENU_MESSAGES["style_presets"].format(style=current_style)
    
    keyboard = [
        [
            InlineKeyboardButton("🎌 Anime", callback_data="style_anime"),
            InlineKeyboardButton("📸 Realistic", callback_data="style_realistic")
        ],
        [
            InlineKeyboardButton("🧙 Fantasy", callback_data="style_fantasy"),
            InlineKeyboardButton("🌆 Cyberpunk", callback_data="style_cyberpunk")
        ],
        [
            InlineKeyboardButton("🎨 Cartoon", callback_data="style_cartoon"),
            InlineKeyboardButton("🖼️ Oil Painting", callback_data="style_oil_painting")
        ],
        [
            InlineKeyboardButton("🌊 Watercolor", callback_data="style_watercolor"),
            InlineKeyboardButton("💻 Digital Art", callback_data="style_digital_art")
        ],
        [
            InlineKeyboardButton("📼 Vintage", callback_data="style_vintage"),
            InlineKeyboardButton("🔵 Minimalist", callback_data="style_minimalist")
        ],
        [
            InlineKeyboardButton("🔄 Clear Style", callback_data="reset_settings"),
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_generate")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        style_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def size_options_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show size options menu."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_size = f"{user_settings['width']}x{user_settings['height']}"
    
    size_text = MENU_MESSAGES["size_options"].format(size=current_size)
    
    keyboard = [
        [
            InlineKeyboardButton("512x512 (Square)", callback_data="size_512"),
            InlineKeyboardButton("768x768 (Square)", callback_data="size_768")
        ],
        [
            InlineKeyboardButton("1024x1024 (Square)", callback_data="size_1024"),
            InlineKeyboardButton("1024x768 (Wide)", callback_data="size_1024_768")
        ],
        [
            InlineKeyboardButton("512x768 (Portrait)", callback_data="size_512_768"),
            InlineKeyboardButton("768x512 (Landscape)", callback_data="size_768_512")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        size_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=ERROR_MESSAGES["general_error"],
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {str(e)}")

async def setup_bot_commands(application: Application) -> None:
    """Setup bot commands menu."""
    commands = [
        (BOT_COMMANDS["start"]["command"], BOT_COMMANDS["start"]["description"]),
        (BOT_COMMANDS["generate"]["command"], BOT_COMMANDS["generate"]["description"]),
        (BOT_COMMANDS["help"]["command"], BOT_COMMANDS["help"]["description"]),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands menu registered successfully")

def main():
    """Main function to run the bot."""
    logger.info(f"Starting bot with token: {BOT_TOKEN[:10]}...")
    
    # Start dummy server in a separate thread
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup commands menu
    application.job_queue.run_once(
        lambda context: asyncio.create_task(setup_bot_commands(application)), 
        when=1
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()