import os
import logging
import asyncio
from io import BytesIO
from typing import Optional
import requests
from PIL import Image

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7265809612:AAHaUYkYPAuPoH6SHuWMZoiK5x--_gJDK3s"
HUGGING_FACE = os.getenv("HUGGING_FACE_TOKEN") or ""
MODEL_URL = "https://api-inference.huggingface.co/models/eimiss/EimisAnimeDiffusion_2.0v"

# Default generation parameters
DEFAULT_PARAMS = {
    "guidance_scale": 7.5,
    "num_inference_steps": 50,
    "width": 512,
    "height": 512
}

def get_headers():
    """Get API headers with authorization."""
    return {"Authorization": f"Bearer {HUGGING_FACE}"}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    welcome_message = (
        "🎨 <b>Welcome to AI Image Generator Bot!</b>\n\n"
        "I can generate beautiful anime-style images using AI.\n\n"
        "<b>Commands:</b>\n"
        "• <code>/generate &lt;prompt&gt;</code> - Generate an image\n"
        "• <code>/settings</code> - Adjust generation parameters\n"
        "• <code>/help</code> - Show this help message\n\n"
        "<b>Quick Start:</b>\n"
        "Just type <code>/generate a beautiful anime girl with blue hair</code> to begin!"
    )
    
    keyboard = [[InlineKeyboardButton("🎨 Generate Sample", callback_data="sample")]]
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
        "<b>Settings:</b>\n"
        "Use <code>/settings</code> to adjust image quality and size."
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /settings command."""
    user_id = update.effective_user.id
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    
    settings_text = (
        "⚙️ <b>Current Settings:</b>\n\n"
        f"📐 Size: {user_settings['width']}x{user_settings['height']}\n"
        f"🎯 Guidance Scale: {user_settings['guidance_scale']}\n"
        f"🔄 Inference Steps: {user_settings['num_inference_steps']}\n\n"
        "<b>Adjust your preferences:</b>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("512x512", callback_data="size_512"),
            InlineKeyboardButton("768x768", callback_data="size_768")
        ],
        [
            InlineKeyboardButton("Quality: Fast", callback_data="quality_fast"),
            InlineKeyboardButton("Quality: High", callback_data="quality_high")
        ],
        [InlineKeyboardButton("🔄 Reset to Default", callback_data="reset_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        settings_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /generate command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a prompt!\n\n"
            "Example: <code>/generate anime girl with blue hair</code>",
            parse_mode=ParseMode.HTML
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

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str) -> None:
    """Generate an image based on the given prompt."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    
    # Send initial message
    status_message = await update.message.reply_text(
        f"🎨 <b>Generating image...</b>\n\n"
        f"<b>Prompt:</b> {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
        f"<b>Settings:</b> {user_settings['width']}x{user_settings['height']}, "
        f"{user_settings['num_inference_steps']} steps",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Prepare request payload
        payload = {
            "inputs": prompt,
            "parameters": user_settings
        }
        
        # Make request to Hugging Face API
        response = await make_api_request(payload)
        
        if response.status_code == 200:
            # Convert response to image
            image_bytes = BytesIO(response.content)
            
            # Send the generated image
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_bytes,
                caption=f"🎨 <b>Generated Image</b>\n\n<b>Prompt:</b> {prompt}",
                parse_mode=ParseMode.HTML
            )
            
            # Delete status message
            await status_message.delete()
            
        elif response.status_code == 503:
            await status_message.edit_text(
                "⏳ <b>Model is loading...</b>\n\n"
                "The AI model is currently starting up. Please try again in 30-60 seconds.",
                parse_mode=ParseMode.HTML
            )
        else:
            await status_message.edit_text(
                f"❌ <b>Generation failed</b>\n\n"
                f"Error code: {response.status_code}\n"
                f"Please try again with a different prompt.",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        await status_message.edit_text(
            "❌ <b>An error occurred</b>\n\n"
            "Please try again later or contact support.",
            parse_mode=ParseMode.HTML
        )

async def make_api_request(payload: dict) -> requests.Response:
    """Make async API request to Hugging Face."""
    loop = asyncio.get_event_loop()
    
    def sync_request():
        return requests.post(
            MODEL_URL,
            headers=get_headers(),
            json=payload,
            timeout=60
        )
    
    return await loop.run_in_executor(None, sync_request)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    
    if data == "sample":
        await generate_image(update, context, "beautiful anime girl with long blue hair, detailed art")
    
    elif data.startswith("size_"):
        size = int(data.split("_")[1])
        user_settings['width'] = size
        user_settings['height'] = size
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            f"✅ <b>Size updated to {size}x{size}</b>\n\n"
            "You can now generate images with the new size!",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "quality_fast":
        user_settings['num_inference_steps'] = 25
        user_settings['guidance_scale'] = 5.0
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            "✅ <b>Quality set to Fast</b>\n\n"
            "Images will generate faster but with lower quality.",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "quality_high":
        user_settings['num_inference_steps'] = 75
        user_settings['guidance_scale'] = 10.0
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            "✅ <b>Quality set to High</b>\n\n"
            "Images will take longer but have better quality.",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "reset_settings":
        context.user_data['settings'] = DEFAULT_PARAMS.copy()
        
        await query.edit_message_text(
            "✅ <b>Settings reset to default</b>\n\n"
            "All parameters have been restored to their default values.",
            parse_mode=ParseMode.HTML
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An unexpected error occurred. Please try again."
        )

def main():
    """Main function to run the bot."""
    # Bot tokens are now hardcoded with environment variable fallback
    logger.info(f"Starting bot with token: {BOT_TOKEN[:10]}...")
    logger.info("Hugging Face API token configured")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
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
