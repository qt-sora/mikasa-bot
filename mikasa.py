import os
import logging
import asyncio
from io import BytesIO
from typing import Optional
import requests
from PIL import Image
import base64
import json

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
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_TELEGRAM_BOT_TOKEN_HERE"

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
    """Handle the /start command."""
    welcome_message = (
        "🎨 <b>Welcome to AI Image Generator Bot!</b>\n\n"
        "I can generate stunning images using Pollinations AI. "
        "Create anime art, realistic photos, fantasy scenes, and much more!\n\n"
        "<b>✨ Features:</b>\n"
        "• Multiple FLUX models available\n"
        "• High-quality image generation\n"
        "• Completely free and unlimited\n"
        "• Fast generation (10-30 seconds)\n\n"
        "<b>🚀 Quick Start:</b>\n"
        "Just type your prompt or use /generate command!"
    )
    
    # Only first three inline buttons as requested
    keyboard = [
        [
            InlineKeyboardButton("📢 Updates", url="https://t.me/YOUR_CHANNEL"),
            InlineKeyboardButton("💬 Support", url="https://t.me/YOUR_GROUP")
        ],
        [
            InlineKeyboardButton("➕ Add Me To Your Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    help_text = (
        "🤖 <b>AI Image Generator Bot Help</b>\n\n"
        "<b>Basic Usage:</b>\n"
        "<code>/generate &lt;your prompt here&gt;</code>\n\n"
        "<b>Example Prompts:</b>\n"
        "• <code>anime girl with purple hair and green eyes</code>\n"
        "• <code>cyberpunk city at night, neon lights</code>\n"
        "• <code>fantasy landscape with mountains and dragons</code>\n\n"
        "<b>Tips for Better Results:</b>\n"
        "• Be specific and descriptive\n"
        "• Include art style keywords (anime, realistic, cartoon)\n"
        "• Mention colors, lighting, and mood\n"
        "• Keep prompts under 200 characters\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/generate</code> - Create image from prompt\n"
        "• <code>/help</code> - Show this help message\n"
        "• <code>/start</code> - Return to main menu\n\n"
        "<b>Service:</b>\n"
        "Powered by Pollinations AI - Free and unlimited!"
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /generate command with all functionality."""
    if not context.args:
        # Show generate menu with options
        generate_menu_text = (
            "🎨 <b>AI Image Generator</b>\n\n"
            "Choose an option or provide a prompt:\n\n"
            "<b>Usage:</b> <code>/generate your prompt here</code>\n\n"
            "<b>Example:</b> <code>/generate anime girl with blue hair</code>"
        )
        
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
            generate_menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return
    
    prompt = " ".join(context.args)
    await generate_image(update, context, prompt)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages as image generation prompts."""
    prompt = update.message.text
    
    # Skip if message starts with /
    if prompt.startswith('/'):
        return
        
    await generate_image(update, context, prompt)

async def generate_image_pollinations(prompt: str, settings: dict) -> Optional[bytes]:
    """Generate image using Pollinations AI."""
    try:
        import random
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
    
    # Send simple emoji status message
    if chat_id:
        status_message = await send_method(
            chat_id=chat_id,
            text="🌺"
        )
    else:
        status_message = await send_method("🌺")
    
    try:
        image_bytes = await generate_image_pollinations(prompt, user_settings)
        
        if image_bytes:
            # Edit the emoji message with the generated image
            image_stream = BytesIO(image_bytes)
            
            # Get clean prompt (remove style suffix for display)
            clean_prompt = prompt
            if context.user_data.get('style_suffix'):
                clean_prompt = prompt.replace(', ' + context.user_data.get('style_suffix'), '')
            
            await context.bot.edit_message_media(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id,
                media=InputMediaPhoto(
                    media=image_stream,
                    caption=f"🎨 <b>Generated Image</b>\n\n<b>Prompt:</b> {clean_prompt}",
                    parse_mode=ParseMode.HTML
                )
            )
            
        else:
            # Generation failed - edit the emoji message with error
            error_message = (
                "❌ <b>Generation failed</b>\n\n"
                "The image generation service is currently unavailable. This might be due to:\n"
                "• Service maintenance\n"
                "• Network issues\n"
                "• Server overload\n\n"
                "<b>Solutions:</b>\n"
                "• Try again in a few minutes\n"
                "• Try with a different prompt\n"
                "• Use /generate to try different settings"
            )
            
            await status_message.edit_text(error_message, parse_mode=ParseMode.HTML)
            
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        try:
            await status_message.edit_text(
                "❌ <b>An error occurred</b>\n\n"
                "Please try again later or contact support.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ <b>An error occurred</b>\n\n"
                     "Please try again later or contact support.",
                parse_mode=ParseMode.HTML
            )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    
    if data == "sample":
        await generate_image(update, context, "beautiful anime girl with long blue hair, detailed art")
    
    elif data == "select_model":
        await model_selection_menu(update, context)
    
    elif data == "settings_menu":
        await settings_menu_callback(update, context)
    
    elif data == "help_menu":
        await help_menu_callback(update, context)
    
    elif data == "style_presets":
        await style_presets_menu(update, context)
    
    elif data == "random_prompt":
        import random
        random_prompts = [
            "futuristic cyberpunk cityscape at night with neon lights",
            "magical forest with glowing mushrooms and fairy lights",
            "steampunk airship floating above clouds",
            "cute anime cat girl with colorful hair",
            "epic dragon flying over medieval castle",
            "abstract cosmic nebula with stars and galaxies",
            "vintage car in rain-soaked city street",
            "peaceful mountain lake at sunset"
        ]
        random_prompt = random.choice(random_prompts)
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
        
        await query.edit_message_text(
            f"✅ <b>Model Selected</b>\n\n"
            f"<b>Service:</b> {API_SERVICE['name']}\n"
            f"<b>Model:</b> {model_name}\n"
            f"<b>Description:</b> {model_info.get('description', 'No description available')}\n\n"
            "You can now generate images with this model!",
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
        
        await query.edit_message_text(
            f"✅ <b>Size updated to {width}x{height}</b>\n\n"
            "You can now generate images with the new size!",
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
        style_prompts = {
            "anime": "anime style, detailed anime art, vibrant colors",
            "realistic": "photorealistic, high detail, professional photography",
            "fantasy": "fantasy art, magical, ethereal, mystical",
            "cyberpunk": "cyberpunk style, neon lights, futuristic, dark atmosphere",
            "cartoon": "cartoon style, colorful, playful, animated",
            "oil_painting": "oil painting style, classical art, brush strokes"
        }
        
        if style in style_prompts:
            context.user_data['style_suffix'] = style_prompts[style]
            await query.edit_message_text(
                f"🎨 <b>Style Applied: {style.replace('_', ' ').title()}</b>\n\n"
                f"<b>Style modifier:</b> {style_prompts[style]}\n\n"
                "This will be added to your prompts automatically!",
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
            "🔄 <b>Settings Reset</b>\n\n"
            "All settings restored to default values:\n"
            "• Service: Pollinations AI\n"
            "• Model: FLUX\n"
            "• Size: 512x512\n"
            "• Style: None\n\n"
            "Ready to generate!",
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
        generate_menu_text = (
            "🎨 <b>AI Image Generator</b>\n\n"
            "Choose an option or provide a prompt:\n\n"
            "<b>Usage:</b> <code>/generate your prompt here</code>\n\n"
            "<b>Example:</b> <code>/generate anime girl with blue hair</code>"
        )
        
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
            generate_menu_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

async def model_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show AI model selection menu."""
    current_model = context.user_data.get('model', 'flux')
    
    model_text = (
        "🤖 <b>AI Model Selection</b>\n\n"
        f"<b>Current Service:</b> {API_SERVICE['name']}\n"
        f"<b>Current Model:</b> {current_model.upper()}\n\n"
        "Choose your preferred AI model:"
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
    
    settings_text = (
        "⚙️ <b>Settings Menu</b>\n\n"
        f"<b>Service:</b> {API_SERVICE['name']}\n"
        f"<b>Model:</b> {current_model.upper()}\n"
        f"<b>Size:</b> {user_settings['width']}x{user_settings['height']}\n\n"
        "Customize your generation settings:"
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
    help_text = (
        "❓ <b>Help & Guide</b>\n\n"
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
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🎨 Try Sample", callback_data="sample"),
            InlineKeyboardButton("🤖 Select Model", callback_data="select_model")
        ],
        [InlineKeyboardButton("⬅️ Back to Generate", callback_data="back_to_generate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def style_presets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show style presets menu."""
    current_style = context.user_data.get('style_suffix', 'None')
    
    style_text = (
        "🌟 <b>Style Presets</b>\n\n"
        f"<b>Current Style:</b> {current_style}\n\n"
        "Choose a style to automatically enhance your prompts:"
    )
    
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
    
    size_text = (
        "📊 <b>Image Size Options</b>\n\n"
        f"<b>Current Size:</b> {current_size}\n\n"
        "Choose your preferred image dimensions:"
    )
    
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
                text="❌ An unexpected error occurred. Please try again."
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {str(e)}")

async def setup_bot_commands(application: Application) -> None:
    """Setup bot commands menu."""
    commands = [
        ("start", "🏠 Start the bot and see main menu"),
        ("generate", "🎨 Generate an image from text prompt"),
        ("help", "❓ Show help and usage guide"),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands menu registered successfully")

def main():
    """Main function to run the bot."""
    logger.info(f"Starting bot with token: {BOT_TOKEN[:10]}...")
    
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