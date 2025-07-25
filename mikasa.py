import os
import logging
import asyncio
from io import BytesIO
from typing import Optional
import requests
from PIL import Image
import base64
import json

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
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_TELEGRAM_BOT_TOKEN_HERE"
HUGGING_FACE = os.getenv("HUGGING_FACE_TOKEN") or "YOUR_HUGGING_FACE_TOKEN_HERE"

# Multiple AI service configurations with detailed models
API_SERVICES = {
    "huggingface": {
        "name": "🤗 Hugging Face",
        "models": {
            "flux": {
                "name": "FLUX.1-dev (Best Quality)",
                "url": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
                "description": "Latest high-quality model"
            },
            "sdxl": {
                "name": "Stable Diffusion XL",
                "url": "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
                "description": "High resolution, great quality"
            },
            "sd15": {
                "name": "Stable Diffusion v1.5",
                "url": "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
                "description": "Fast and reliable"
            },
            "anime": {
                "name": "Anime Diffusion",
                "url": "https://api-inference.huggingface.co/models/Ojimi/anime-kawai-diffusion",
                "description": "Specialized for anime art"
            }
        }
    },
    "pollinations": {
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
            }
        }
    }
}

# Default generation parameters
DEFAULT_PARAMS = {
    "guidance_scale": 7.5,
    "num_inference_steps": 50,
    "width": 512,
    "height": 512,
    "seed": None,
    "service": "pollinations",
    "model": "flux"
}

def get_headers():
    """Get API headers with authorization."""
    return {"Authorization": f"Bearer {HUGGING_FACE}"}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    welcome_message = (
        "🎨 <b>Welcome to AI Image Generator Bot!</b>\n\n"
        "I can generate stunning images using advanced AI models. "
        "Create anime art, realistic photos, fantasy scenes, and much more!\n\n"
        "<b>✨ Features:</b>\n"
        "• Multiple AI models (FLUX, Stable Diffusion, etc.)\n"
        "• High-quality image generation\n"
        "• Customizable settings & styles\n"
        "• Free and unlimited usage\n\n"
        "<b>🚀 Quick Start:</b>\n"
        "Just type your prompt or use the buttons below!"
    )
    
    # Create inline keyboard with requested buttons
    keyboard = [
        [
            InlineKeyboardButton("📢 Updates", url="https://t.me/YOUR_CHANNEL"),
            InlineKeyboardButton("💬 Support", url="https://t.me/YOUR_GROUP")
        ],
        [
            InlineKeyboardButton("➕ Add Me To Your Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("🤖 Select AI Model", callback_data="select_model"),
            InlineKeyboardButton("🎨 Generate Sample", callback_data="sample")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu"),
            InlineKeyboardButton("❓ Help", callback_data="help_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def model_selection_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show AI model selection menu."""
    current_service = context.user_data.get('service', 'pollinations')
    current_model = context.user_data.get('model', 'flux')
    
    model_text = (
        "🤖 <b>AI Model Selection</b>\n\n"
        f"<b>Current Service:</b> {API_SERVICES.get(current_service, {}).get('name', 'Unknown')}\n"
        f"<b>Current Model:</b> {current_model.upper()}\n\n"
        "Choose your preferred AI service and model:"
    )
    
    keyboard = []
    
    # Pollinations models
    keyboard.append([InlineKeyboardButton("🌸 Pollinations AI (Free)", callback_data="service_info_pollinations")])
    for model_key, model_info in API_SERVICES["pollinations"]["models"].items():
        status = "✅" if current_service == "pollinations" and current_model == model_key else ""
        keyboard.append([InlineKeyboardButton(
            f"  {status} {model_info['name']}", 
            callback_data=f"model_pollinations_{model_key}"
        )])
    
    # Hugging Face models
    keyboard.append([InlineKeyboardButton("🤗 Hugging Face", callback_data="service_info_huggingface")])
    for model_key, model_info in API_SERVICES["huggingface"]["models"].items():
        status = "✅" if current_service == "huggingface" and current_model == model_key else ""
        keyboard.append([InlineKeyboardButton(
            f"  {status} {model_info['name']}", 
            callback_data=f"model_huggingface_{model_key}"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")])
    
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
        "<b>Services:</b>\n"
        "• Use <code>/model</code> to switch between AI providers\n"
        "• Use <code>/settings</code> to adjust image quality and size"
    )
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /settings command."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_service = context.user_data.get('service', 'pollinations')
    current_model = context.user_data.get('model', 'flux')
    
    settings_text = (
        "⚙️ <b>Current Settings:</b>\n\n"
        f"🔄 Service: {API_SERVICES.get(current_service, {}).get('name', 'Unknown')}\n"
        f"🤖 Model: {current_model.upper()}\n"
        f"📐 Size: {user_settings['width']}x{user_settings['height']}\n"
        f"🎯 Guidance Scale: {user_settings['guidance_scale']}\n"
        f"🔄 Inference Steps: {user_settings['num_inference_steps']}\n\n"
        "<b>Adjust your preferences:</b>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("512x512", callback_data="size_512"),
            InlineKeyboardButton("768x768", callback_data="size_768"),
            InlineKeyboardButton("1024x1024", callback_data="size_1024")
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

async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings menu callback."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_service = context.user_data.get('service', 'pollinations')
    current_model = context.user_data.get('model', 'flux')
    
    settings_text = (
        "⚙️ <b>Settings Menu</b>\n\n"
        f"<b>Service:</b> {API_SERVICES.get(current_service, {}).get('name', 'Unknown')}\n"
        f"<b>Model:</b> {current_model.upper()}\n"
        f"<b>Size:</b> {user_settings['width']}x{user_settings['height']}\n"
        f"<b>Quality:</b> {user_settings['num_inference_steps']} steps\n"
        f"<b>Guidance:</b> {user_settings['guidance_scale']}\n\n"
        "Customize your generation settings:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("512x512", callback_data="size_512"),
            InlineKeyboardButton("768x768", callback_data="size_768"),
            InlineKeyboardButton("1024x1024", callback_data="size_1024")
        ],
        [
            InlineKeyboardButton("⚡ Fast", callback_data="quality_fast"),
            InlineKeyboardButton("⭐ Balanced", callback_data="quality_balanced"),
            InlineKeyboardButton("💎 High", callback_data="quality_high")
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data="reset_settings"),
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_start")
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
        "• /model - Switch AI model\n"
        "• /settings - Adjust parameters\n"
        "• /help - Show this guide\n\n"
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
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        help_text,
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

async def generate_image_pollinations(prompt: str, settings: dict) -> Optional[bytes]:
    """Generate image using Pollinations AI (Free service)."""
    try:
        import random
        seed = settings.get('seed') or random.randint(1, 1000000)
        model = settings.get('model', 'flux')
        model_param = API_SERVICES["pollinations"]["models"].get(model, {}).get('model_param', 'flux')
        
        # Format URL with parameters
        url = API_SERVICES["pollinations"]["url"].format(
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

async def generate_image_huggingface(prompt: str, settings: dict) -> Optional[bytes]:
    """Generate image using Hugging Face API."""
    try:
        model = settings.get('model', 'flux')
        model_info = API_SERVICES["huggingface"]["models"].get(model)
        
        if not model_info:
            # Fallback to first available model
            model_info = list(API_SERVICES["huggingface"]["models"].values())[0]
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "guidance_scale": settings.get('guidance_scale', 7.5),
                "num_inference_steps": settings.get('num_inference_steps', 50),
                "width": settings.get('width', 512),
                "height": settings.get('height', 512)
            },
            "options": {
                "wait_for_model": True,
                "use_cache": False
            }
        }
        
        try:
            response = requests.post(
                model_info["url"],
                headers=get_headers(),
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 402:
                # Quota exceeded, return None to trigger fallback
                return None
            elif response.status_code == 503:
                # Model loading, wait and try once more
                await asyncio.sleep(30)
                response = requests.post(
                    model_info["url"],
                    headers=get_headers(),
                    json=payload,
                    timeout=120
                )
                if response.status_code == 200:
                    return response.content
                    
        except Exception as e:
            logger.error(f"Error with model {model}: {str(e)}")
                
        return None
        
    except Exception as e:
        logger.error(f"Error with Hugging Face: {str(e)}")
        return None

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str) -> None:
    """Generate an image based on the given prompt."""
    user_settings = context.user_data.get('settings', DEFAULT_PARAMS.copy())
    current_service = context.user_data.get('service', 'pollinations')
    current_model = context.user_data.get('model', 'flux')
    
    # Update settings with current service and model
    user_settings['service'] = current_service
    user_settings['model'] = current_model
    
    # Determine which message object to use
    if update.callback_query:
        chat_id = update.effective_chat.id
        send_method = context.bot.send_message
    else:
        chat_id = None
        send_method = update.message.reply_text
    
    # Get model name for display
    model_display = current_model.upper()
    if current_service in API_SERVICES and "models" in API_SERVICES[current_service]:
        model_info = API_SERVICES[current_service]["models"].get(current_model, {})
        model_display = model_info.get("name", current_model.upper())
    
    # Send initial status message
    if chat_id:
        status_message = await send_method(
            chat_id=chat_id,
            text=f"🎨 <b>Generating image...</b>\n\n"
                 f"<b>Service:</b> {API_SERVICES.get(current_service, {}).get('name', 'Unknown')}\n"
                 f"<b>Model:</b> {model_display}\n"
                 f"<b>Prompt:</b> {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
                 f"<b>Size:</b> {user_settings['width']}x{user_settings['height']}",
            parse_mode=ParseMode.HTML
        )
    else:
        status_message = await send_method(
            f"🎨 <b>Generating image...</b>\n\n"
            f"<b>Service:</b> {API_SERVICES.get(current_service, {}).get('name', 'Unknown')}\n"
            f"<b>Model:</b> {model_display}\n"
            f"<b>Prompt:</b> {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
            f"<b>Size:</b> {user_settings['width']}x{user_settings['height']}",
            parse_mode=ParseMode.HTML
        )
    
    try:
        image_bytes = None
        service_used = current_service
        model_used = current_model
        
        # Try current service first
        if current_service == "pollinations":
            image_bytes = await generate_image_pollinations(prompt, user_settings)
        elif current_service == "huggingface":
            image_bytes = await generate_image_huggingface(prompt, user_settings)
        
        # If primary service fails, try fallbacks
        if not image_bytes:
            logger.info(f"Primary service {current_service} failed, trying fallbacks...")
            
            # Try Pollinations if not already tried
            if current_service != "pollinations":
                fallback_settings = user_settings.copy()
                fallback_settings['model'] = 'flux'
                image_bytes = await generate_image_pollinations(prompt, fallback_settings)
                if image_bytes:
                    service_used = "pollinations"
                    model_used = "flux"
            
            # Try Hugging Face if not already tried and we have a token
            if not image_bytes and current_service != "huggingface" and HUGGING_FACE != "YOUR_HUGGING_FACE_TOKEN_HERE":
                fallback_settings = user_settings.copy()
                fallback_settings['model'] = 'flux'
                image_bytes = await generate_image_huggingface(prompt, fallback_settings)
                if image_bytes:
                    service_used = "huggingface"
                    model_used = "flux"
        
        if image_bytes:
            # Get final model display name
            final_model_display = model_used.upper()
            if service_used in API_SERVICES and "models" in API_SERVICES[service_used]:
                model_info = API_SERVICES[service_used]["models"].get(model_used, {})
                final_model_display = model_info.get("name", model_used.upper())
            
            # Send the generated image
            image_stream = BytesIO(image_bytes)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_stream,
                caption=f"🎨 <b>Generated Image</b>\n\n"
                       f"<b>Service:</b> {API_SERVICES.get(service_used, {}).get('name', 'Unknown')}\n"
                       f"<b>Model:</b> {final_model_display}\n"
                       f"<b>Prompt:</b> {prompt}",
                parse_mode=ParseMode.HTML
            )
            
            # Delete status message
            await status_message.delete()
            
        else:
            # All services failed
            error_message = (
                "❌ <b>Generation failed</b>\n\n"
                "All available services are currently unavailable. This might be due to:\n"
                "• Quota limits exceeded\n"
                "• Service maintenance\n"
                "• Network issues\n\n"
                "<b>Solutions:</b>\n"
                "• Try again in a few minutes\n"
                "• Use /model to switch providers\n"
                "• For Hugging Face: Consider upgrading to PRO ($9/month)"
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
    
    elif data == "back_to_start":
        # Recreate start menu
        welcome_message = (
            "🎨 <b>Welcome to AI Image Generator Bot!</b>\n\n"
            "I can generate stunning images using advanced AI models. "
            "Create anime art, realistic photos, fantasy scenes, and much more!\n\n"
            "<b>✨ Features:</b>\n"
            "• Multiple AI models (FLUX, Stable Diffusion, etc.)\n"
            "• High-quality image generation\n"
            "• Customizable settings & styles\n"
            "• Free and unlimited usage\n\n"
            "<b>🚀 Quick Start:</b>\n"
            "Just type your prompt or use the buttons below!"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📢 Updates", url="https://t.me/YOUR_CHANNEL"),
                InlineKeyboardButton("💬 Support", url="https://t.me/YOUR_GROUP")
            ],
            [
                InlineKeyboardButton("➕ Add Me To Your Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("🤖 Select AI Model", callback_data="select_model"),
                InlineKeyboardButton("🎨 Generate Sample", callback_data="sample")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data.startswith("model_"):
        # Handle model selection: model_service_modelname
        parts = data.split("_", 2)
        if len(parts) >= 3:
            service = parts[1]
            model = parts[2]
            
            context.user_data['service'] = service
            context.user_data['model'] = model
            
            # Get model info for display
            model_info = API_SERVICES.get(service, {}).get("models", {}).get(model, {})
            model_name = model_info.get("name", model.upper())
            service_name = API_SERVICES.get(service, {}).get("name", service)
            
            await query.edit_message_text(
                f"✅ <b>Model Selected</b>\n\n"
                f"<b>Service:</b> {service_name}\n"
                f"<b>Model:</b> {model_name}\n"
                f"<b>Description:</b> {model_info.get('description', 'No description available')}\n\n"
                "You can now generate images with this model!",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                        InlineKeyboardButton("🤖 Change Model", callback_data="select_model")
                    ],
                    [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
                ])
            )
    
    elif data.startswith("service_info_"):
        service = data.split("_", 2)[2]
        
        if service == "pollinations":
            info_text = (
                "🌸 <b>Pollinations AI</b>\n\n"
                "<b>✅ Advantages:</b>\n"
                "• Completely free\n"
                "• No registration required\n"
                "• Fast generation (10-30 seconds)\n"
                "• Multiple models available\n"
                "• No rate limits\n\n"
                "<b>📝 Models:</b>\n"
                "• FLUX - Highest quality\n"
                "• Turbo - Fastest generation\n\n"
                "<b>💡 Best for:</b>\n"
                "General use, unlimited generation"
            )
        elif service == "huggingface":
            info_text = (
                "🤗 <b>Hugging Face</b>\n\n"
                "<b>✅ Advantages:</b>\n"
                "• Multiple specialized models\n"
                "• High-quality generation\n"
                "• Advanced customization\n\n"
                "<b>⚠️ Limitations:</b>\n"
                "• Monthly quota limits\n"
                "• May require PRO subscription\n\n"
                "<b>📝 Models:</b>\n"
                "• FLUX.1-dev - Latest & best\n"
                "• Stable Diffusion XL\n"
                "• Anime specialized models\n\n"
                "<b>💡 Best for:</b>\n"
                "High-quality, specialized generation"
            )
        await query.edit_message_text(
            info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Models", callback_data="select_model")]
            ])
        )
    
    elif data.startswith("size_"):
        size = int(data.split("_")[1])
        user_settings['width'] = size
        user_settings['height'] = size
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            f"✅ <b>Size updated to {size}x{size}</b>\n\n"
            "You can now generate images with the new size!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                    InlineKeyboardButton("⚙️ More Settings", callback_data="settings_menu")
                ],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
            ])
        )
    
    elif data == "quality_fast":
        user_settings['num_inference_steps'] = 20
        user_settings['guidance_scale'] = 5.0
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            "⚡ <b>Quality set to Fast</b>\n\n"
            "• 20 inference steps\n"
            "• 5.0 guidance scale\n"
            "• Faster generation (~10-15 seconds)\n\n"
            "Images will generate quickly with good quality.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Test Now", callback_data="sample"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")
                ],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
            ])
        )
    
    elif data == "quality_balanced":
        user_settings['num_inference_steps'] = 50
        user_settings['guidance_scale'] = 7.5
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            "⭐ <b>Quality set to Balanced</b>\n\n"
            "• 50 inference steps\n"
            "• 7.5 guidance scale\n"
            "• Moderate generation time (~20-30 seconds)\n\n"
            "Perfect balance of quality and speed.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Test Now", callback_data="sample"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")
                ],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
            ])
        )
    
    elif data == "quality_high":
        user_settings['num_inference_steps'] = 75
        user_settings['guidance_scale'] = 10.0
        context.user_data['settings'] = user_settings
        
        await query.edit_message_text(
            "💎 <b>Quality set to High</b>\n\n"
            "• 75 inference steps\n"
            "• 10.0 guidance scale\n"
            "• Longer generation time (~30-60 seconds)\n\n"
            "Maximum quality for detailed images.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Test Now", callback_data="sample"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")
                ],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
            ])
        )
    
    elif data == "reset_settings":
        context.user_data['settings'] = DEFAULT_PARAMS.copy()
        context.user_data['service'] = 'pollinations'
        context.user_data['model'] = 'flux'
        
        await query.edit_message_text(
            "🔄 <b>Settings Reset</b>\n\n"
            "All settings restored to default values:\n"
            "• Service: Pollinations AI\n"
            "• Model: FLUX\n"
            "• Size: 512x512\n"
            "• Quality: Balanced\n\n"
            "Ready to generate!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎨 Generate Sample", callback_data="sample"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu")
                ],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_start")]
            ])
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
        ("model", "🤖 Select AI model and service"),
        ("settings", "⚙️ Adjust generation settings"),
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
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("model", model_selection_menu))
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