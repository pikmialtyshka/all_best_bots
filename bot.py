import os
import sqlite3
import logging
import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ========== НАСТРОЙКИ ==========
os.environ['TZ'] = 'Europe/Moscow'

# Токен переходника
SWITCHER_TOKEN = '8692515951:AAFoPto-22C9rilnMJHAif36bXvUDm08nP4'

# ТОКЕНЫ ДЛЯ 9 МОТИВИШНЫХ БОТОВ
BOT_TOKENS = [
    "8633809924:AAGLwVQSfBDzQUNU3GKhceMUV_pzNtpcAHA",  # CS2 ПРАЙМ
    "8315119156:AAE6dIIYMsE80f7TVAyby_qMxKtqdzm5EOo",  # CS2 СКИНЫ
    "8583713671:AAEeKGKmZBzQ0rqsiDShGXjOnijN6G-32-w",  # РОБУКСЫ
    "8445466695:AAGORyjHM8ghSs2jhKblwwrO0-aJNp6Zuq8",  # СТЕНДОФФ2 ГОЛДА
    "8408906854:AAH1o9LAf9kKKMh6mmZj0BGAlsE670DjslA",  # ТГ НФТ
    "8622662261:AAFfT6Ye6tB8O01QhjYRYinHrxpr9ZykvOw",  # ТГ ЗВЁЗДЫ
    "8562359492:AAFWc3XXKAtCkCh_Y8uznLcY6lFZFdI7gn0",  # КИНОПОИСК/PREMIER
    "8644384412:AAFi1bGQdE9dm9rLnCi51lvpLaXphdUyx0s",  # BRAWL STARS ГЕМЫ
    "8784577185:AAEsqS036U2aWV4ElydYvBAM-bSiHwWhFGI",  # ТГ ПРЕМИУМ
]

# НАЗВАНИЯ БОТОВ
BOT_NAMES = [
    "🎮 CS2 ПРАЙМ",
    "🔫 CS2 СКИНЫ",
    "⭐ БЕСПЛАТНЫЕ РОБУКСЫ",
    "💀 СТЕНДОФФ2 ГОЛДА",
    "🖼️ ТГ НФТ",
    "✨ ТГ ЗВЁЗДЫ",
    "🎬 КИНОПОИСК/PREMIER",
    "💎 BRAWL STARS ГЕМЫ",
    "⭐ ТГ ПРЕМИУМ"
]

# Админы
ADMINS = [
    'annaapanfilova1',
    'PepeChilI',
    'CH4EBYRAHKA',
    'dmitriiiy_22'
]

# Пользователи, которые НЕ увидят кнопку "Глаз Чебурашки"
EXCLUDED_FROM_CHEBURASHKA = [
    'ch4ebyrahka',
    'annaapanfilova1',
    'kyrsanik',
    'pepechili'
]

# 9 МОТИВИШНЫХ БОТОВ ДЛЯ ПЕРЕХОДНИКА
MOTIVATION_BOTS = [
    {"name": "💰 ПОЛУЧИТЬ ROBUX", "username": "@Poluchitrobux_bot", "url": "https://t.me/Poluchitrobux_bot?start=ref"},
    {"name": "🥇 СТЕНДОФФ2 ГОЛДА", "username": "@Goldsstandoff2fbot", "url": "https://t.me/Goldsstandoff2fbot?start=ref"},
    {"name": "💎 BRAWL STARS ГЕМЫ", "username": "@Brawlgemhalyvabot", "url": "https://t.me/Brawlgemhalyvabot?start=ref"},
    {"name": "🎬 КИНОПОИСК/PREMIER", "username": "@TRIALS_for_free_bot", "url": "https://t.me/TRIALS_for_free_bot?start=ref"},
    {"name": "🛒 KUPER ALIEXPRESS", "username": "@Kuper_Aliexpress_bot", "url": "https://t.me/Kuper_Aliexpress_bot?start=ref"},
    {"name": "🔫 CS2 ХАЛЯВНЫЕ СКИНЫ", "username": "@Cs2skinsorbit_bot", "url": "https://t.me/Cs2skinsorbit_bot?start=ref"},
    {"name": "⭐ TG STARS | NFT | PREMIUM", "username": "@Tg_stars_NFT_Tg_premium_bot", "url": "https://t.me/Tg_stars_NFT_Tg_premium_bot?start=ref"},
    {"name": "💳 СБЕРПРАЙМ ЗА РУБЛЬ", "username": "@SberPrime_Za_rub_bot", "url": "https://t.me/SberPrime_Za_rub_bot?start=ref"},
    {"name": "🎮 CS2 ПРАЙМ СТАТУС", "username": "@Cs2primestatus_bot", "url": "https://t.me/Cs2primestatus_bot?start=ref"},
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ФУНКЦИИ ДЛЯ БД (ОТДЕЛЬНАЯ ДЛЯ КАЖДОГО БОТА) ==========
def get_db_name(bot_name: str) -> str:
    """Возвращает имя файла БД для конкретного бота"""
    # Убираем эмодзи и пробелы из имени
    clean_name = ''.join(c for c in bot_name if c.isalnum() or c == '_')
    return f'./users_{clean_name}.db'

def init_bot_db(db_name: str):
    """Инициализация БД для конкретного бота"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            last_seen DATETIME DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    conn.commit()
    conn.close()

def save_user_to_bot_db(db_name: str, user_id, username, first_name):
    """Сохраняет пользователя в БД конкретного бота"""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_seen)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_seen = datetime('now', 'localtime')
        ''', (user_id, username or '', first_name or ''))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'Ошибка сохранения в {db_name}: {e}')

def get_bot_stats(db_name: str):
    """Получает статистику для конкретного бота"""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM users')
        total = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) as count FROM users 
            WHERE DATE(last_seen) = DATE('now', 'localtime')
        ''')
        today = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) as count FROM users 
            WHERE last_seen >= datetime('now', 'localtime', '-7 days')
        ''')
        week = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) as count FROM users 
            WHERE last_seen >= datetime('now', 'localtime', '-30 days')
        ''')
        month = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT username, first_name, last_seen 
            FROM users 
            ORDER BY last_seen DESC 
            LIMIT 5
        ''')
        recent = cursor.fetchall()
        
        conn.close()
        return total, today, week, month, recent
    except Exception as e:
        print(f'Ошибка получения статистики из {db_name}: {e}')
        return 0, 0, 0, 0, []

def is_admin(username):
    if not username:
        return False
    return username.lower() in [a.lower() for a in ADMINS]

def should_hide_cheburashka(username):
    if not username:
        return False
    return username.lower() in [e.lower() for e in EXCLUDED_FROM_CHEBURASHKA]

# ========== ВЕБ-СЕРВЕР (FLASK) ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'Боты работают! 🤖'

def run_flask():
    port = int(os.environ.get('PORT', 3000))
    flask_app.run(host='0.0.0.0', port=port)

# ========== ЗАДАНИЯ ДЛЯ МОТИВИШНЫХ БОТОВ ==========
BASE_TASKS = ["yandex", "sberprime", "yandexplus", "tv24"]

TASK_INFO = {
    "yandex": {
        "name": "📱 СКАЧАТЬ ЯНДЕКС БРАУЗЕР",
        "description": "Скачай Яндекс Браузер по ссылке и установи",
        "link": "https://vk.cc/cVUvvJ",
        "button": "🔽 СКАЧАТЬ"
    },
    "sberprime": {
        "name": "💳 СБЕРПРАЙМ ЗА 1 РУБЛЬ",
        "description": "Оформи подписку СберПрайм за 1 рубль",
        "link": "https://vk.cc/cVUvEb",
        "button": "💳 ОФОРМИТЬ"
    },
    "yandexplus": {
        "name": "🌟 ЯНДЕКС ПЛЮС",
        "description": "Оформи подписку за 1 рубль\nПРОМОКОД: 328652SPMA",
        "link": "https://vk.cc/cVUMu5",
        "button": "🌟 ОФОРМИТЬ"
    },
    "tv24": {
        "name": "🎬 ПРОМОКОД 24TV",
        "description": "Активируй промокод",
        "link": "https://vk.cc/cVUwtW",
        "button": "🎬 АКТИВИРОВАТЬ"
    }
}

REQUIRED_CHANNELS = [
    {"name": "🎮 ТЕМКИ", "link": "https://t.me/+X6hEJTznwuc4NWIy"},
    {"name": "🎮 ТЕЛКИ", "link": "https://t.me/+ZAmRG9tQciU0MTNi"},
    {"name": "🎮 ЛЬГОТЫ", "link": "https://t.me/+sqs0iLp5T49iNDEy"}
]

def generate_tasks_for_bot():
    num_tasks = random.choice([3, 4])
    shuffled = BASE_TASKS.copy()
    random.shuffle(shuffled)
    return shuffled[:num_tasks]

def is_player_id(text: str) -> bool:
    patterns = [r'^[A-Z0-9]{9}$', r'^#[A-Z0-9]{9}$', r'^[A-Z0-9]{8,10}$']
    for pattern in patterns:
        if re.match(pattern, text.strip().upper()):
            return True
    return False

class UserState:
    def __init__(self, user_id: int, username: str, tasks_order: List[str]):
        self.user_id = user_id
        self.username = username
        self.tasks_order = tasks_order
        self.current_task_index = 0
        self.waiting_for_screenshot = False
        self.current_task_key = None
        self.reward_claimed = False
        self.player_id = None
        self.completed_tasks = []
        self.last_activity = datetime.now()
        self.reminder_sent = False
        self.waiting_for_player_id = False
        self.subscriptions_verified = False

async def fake_check_subscription(update: Update, user_id: int, bot_name: str) -> bool:
    logger.info(f"🔴 [{bot_name}] Фейк-проверка: пользователь {user_id} прошел")
    return True

# ========== ПЕРЕХОДНИК (SWITCHER BOT) ==========
def get_switcher_menu(is_admin_user, hide_cheburashka):
    keyboard = []
    
    keyboard.append([InlineKeyboardButton('👻 Дyxлec | Поиск по номеру 📱', url='https://t.me/Karmarseebot?start=r_G5Z95D57TN')])
    keyboard.append([InlineKeyboardButton('🕵️‍♂️ Шepлok | Поиск по фото 👁', url='https://t.me/kisankanatop_bot?start=_ref_yalLl8WEx_Ipg17UPFM')])
    keyboard.append([InlineKeyboardButton('🔐 RuVPN | Безопасный VPN 🌐', url='https://t.me/ruvpn?start=partner_1860340689')])
    keyboard.append([InlineKeyboardButton('👗 Раздеватор | AI раздевалка 🔥', url='https://t.me/razdevator_bot?start=ref')])
    keyboard.append([
        InlineKeyboardButton('📸 Инcтa Шnuoн', url='https://instashpion.ru?p=9cd42aee57cb325637213b895e815200'),
        InlineKeyboardButton('👥 BK Шnuoн', url='https://kogdavseti.ru/?p=0e11c1032d9ed026dcf04fdedad15355')
    ])
    keyboard.append([InlineKeyboardButton('🎲 Генератор потеx 18+ 🔞🍓', url='https://gratzbot.app/?start=ref-de2e2b04')])
    
    if not hide_cheburashka:
        keyboard.append([InlineKeyboardButton('👁 Глаз Чебурашки 🔍', url='https://t.me/search_ot_cheburashki_bot?start=_ref_kGDGyBSDx_kN7fr6pCO')])
    
    keyboard.append([InlineKeyboardButton('⭐ ⭐ ⭐ ПОЛЕЗНЫЕ БОТЫ ⭐ ⭐ ⭐', callback_data='noop')])
    
    for i in range(0, len(MOTIVATION_BOTS), 2):
        row = []
        row.append(InlineKeyboardButton(MOTIVATION_BOTS[i]['name'], url=MOTIVATION_BOTS[i]['url']))
        if i + 1 < len(MOTIVATION_BOTS):
            row.append(InlineKeyboardButton(MOTIVATION_BOTS[i + 1]['name'], url=MOTIVATION_BOTS[i + 1]['url']))
        keyboard.append(row)
    
    if is_admin_user:
        keyboard.append([InlineKeyboardButton('👑 АДМИН-ПАНЕЛЬ 👑', callback_data='admin_panel')])
    
    return InlineKeyboardMarkup(keyboard)

# Своя БД для переходника
SWITCHER_DB = './users_switcher.db'

async def switcher_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_to_bot_db(SWITCHER_DB, user.id, user.username, user.first_name)
    hide_cheburashka = should_hide_cheburashka(user.username)
    
    text = f"""
🔍 <b>ВЫБЕРИТЕ НУЖНЫЙ СЕРВИС</b> 🔍

Привет, {user.first_name or 'друг'}! 👋

👇 <b>Нажми на кнопку:</b>
    """
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_switcher_menu(is_admin(user.username), hide_cheburashka))

async def switcher_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if query.data == 'admin_panel':
        if not is_admin(user.username):
            await query.answer('⛔ Только для админов', show_alert=True)
            return
        
        total, today, week, month, recent = get_bot_stats(SWITCHER_DB)
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        
        text = f"👑 <b>АДМИН-ПАНЕЛЬ [ПЕРЕХОДНИК]</b>\nМСК {now.strftime('%d.%m %H:%M')}\n\n"
        text += f"📊 Всего: {total} | Сегодня: {today} | Неделя: {week} | Месяц: {month}\n\n🕐 <b>Последние 5:</b>\n"
        for i, row in enumerate(recent, 1):
            username, first_name, last_seen = row
            name = first_name or 'Без имени'
            username_str = f"@{username}" if username else 'нет username'
            text += f"{i}. {name} ({username_str})\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('🔄 Обновить', callback_data='admin_panel')],
            [InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')]
        ])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
    
    elif query.data == 'back_to_menu':
        hide_cheburashka = should_hide_cheburashka(user.username)
        await query.edit_message_text(
            "🔍 <b>ВЫБЕРИТЕ НУЖНЫЙ СЕРВИС</b> 🔍\n\n👇 Нажми на кнопку:",
            parse_mode='HTML',
            reply_markup=get_switcher_menu(is_admin(user.username), hide_cheburashka)
        )
    
    elif query.data == 'noop':
        await query.answer('⬇️ Боты ниже ⬇️', show_alert=False)

async def run_switcher():
    """Запуск бота-переходника"""
    print("🚀 ПЕРЕХОДНИК ЗАПУСКАЕТСЯ...")
    init_bot_db(SWITCHER_DB)
    
    application = Application.builder().token(SWITCHER_TOKEN).build()
    
    application.add_handler(CommandHandler("start", switcher_start))
    application.add_handler(CallbackQueryHandler(switcher_button_callback))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("✅ ПЕРЕХОДНИК ЗАПУЩЕН!")
    
    while True:
        await asyncio.sleep(1)

# ========== ЗАПУСК МОТИВИШНОГО БОТА ==========
async def run_motivation_bot(bot_token: str, bot_name: str, bot_number: int):
    """Запуск одного мотивишного бота со СВОЕЙ БД"""
    tasks_order = generate_tasks_for_bot()
    user_data: Dict[int, UserState] = {}
    user_data["__tasks_order__"] = tasks_order
    
    # СВОЯ БД ДЛЯ КАЖДОГО БОТА
    bot_db = get_db_name(bot_name)
    init_bot_db(bot_db)
    
    print(f"🚀 МОТИВИШНЫЙ БОТ #{bot_number} ЗАПУСКАЕТСЯ: {bot_name} ({len(tasks_order)} заданий)")
    print(f"   📁 БД: {bot_db}")
    
    application = Application.builder().token(bot_token).build()
    
    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        save_user_to_bot_db(bot_db, user.id, user.username, user.first_name)
        
        keyboard = [[InlineKeyboardButton("🎁 ПОЛУЧИТЬ НАГРАДУ", callback_data="start_tasks")]]
        if is_admin(update.effective_user.username):
            keyboard.append([InlineKeyboardButton("👑 АДМИН-ПАНЕЛЬ", callback_data="admin_panel")])
        await update.message.reply_text(
            f"🎮 {bot_name} 🎮\n\nПривет! Выполни задания и получи награду!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = query.from_user
        
        if not is_admin(user.username):
            await query.answer('⛔ Только для админов', show_alert=True)
            return
        
        total, today, week, month, recent = get_bot_stats(bot_db)
        
        text = f"👑 <b>АДМИН-ПАНЕЛЬ [{bot_name}]</b>\n\n"
        text += f"📊 Всего пользователей: <b>{total}</b>\n"
        text += f"• За сегодня: <b>{today}</b>\n"
        text += f"• За неделю: <b>{week}</b>\n"
        text += f"• За месяц: <b>{month}</b>\n\n"
        
        text += f"🕐 <b>Последние 5:</b>\n"
        for i, row in enumerate(recent, 1):
            username, first_name, last_seen = row
            name = first_name or 'Без имени'
            username_str = f"@{username}" if username else 'нет username'
            text += f"{i}. {name} ({username_str})\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('🔄 Обновить', callback_data='admin_panel')],
            [InlineKeyboardButton('◀️ Назад', callback_data='back_to_menu')]
        ])
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
    
    async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data == "admin_panel":
            await admin_panel_callback(update, context)
        elif data == "back_to_menu":
            keyboard = [[InlineKeyboardButton("🎁 ПОЛУЧИТЬ НАГРАДУ", callback_data="start_tasks")]]
            if is_admin(query.from_user.username):
                keyboard.append([InlineKeyboardButton("👑 АДМИН-ПАНЕЛЬ", callback_data="admin_panel")])
            await query.edit_message_text(
                f"🎮 {bot_name} 🎮\n\nПривет! Выполни задания и получи награду!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif data == "start_tasks":
            user_id = query.from_user.id
            if user_id in user_data and user_data[user_id].reward_claimed:
                await query.edit_message_text("❌ Ты уже получил награду!")
                return
            
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"📢 {channel['name']}", url=channel['link'])])
            keyboard.append([InlineKeyboardButton("✅ ПРОВЕРИТЬ", callback_data="verify")])
            keyboard.append([InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel")])
            await query.edit_message_text(
                "🔔 ПОДПИШИСЬ НА КАНАЛЫ!\n\nПосле подписки нажми «ПРОВЕРИТЬ»",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif data == "verify":
            user_id = query.from_user.id
            await fake_check_subscription(update, user_id, bot_name)
            if user_id in user_data and not isinstance(user_data[user_id], list):
                user = user_data[user_id]
            else:
                user = UserState(user_id, query.from_user.username, tasks_order)
                user_data[user_id] = user
            user.subscriptions_verified = True
            user.current_task_index = 0
            user.last_activity = datetime.now()
            await show_task(query, user)
        elif data == "cancel":
            user_id = query.from_user.id
            if user_id in user_data:
                del user_data[user_id]
            await start_handler(update, context)
    
    async def show_task(query, user):
        if user.current_task_index >= len(user.tasks_order):
            user.waiting_for_player_id = True
            await query.edit_message_text("✅ ВСЕ ЗАДАНИЯ ВЫПОЛНЕНЫ!\n\nОтправь свой ID:")
            return
        
        task_key = user.tasks_order[user.current_task_index]
        task = TASK_INFO[task_key]
        current = user.current_task_index + 1
        total = len(user.tasks_order)
        
        text = f"📋 ЗАДАНИЕ {current}/{total}\n\n{task['name']}\n\n{task['description']}\n\n🔗 <a href='{task['link']}'>👉 {task['button']} 👈</a>\n\n📸 Отправь скриншот!"
        user.waiting_for_screenshot = True
        user.current_task_key = task_key
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in user_data or not user_data[user_id].waiting_for_screenshot:
            await update.message.reply_text("❌ Сначала нажми /start")
            return
        
        user = user_data[user_id]
        user.waiting_for_screenshot = False
        await update.message.reply_text("⏳ ПРОВЕРКА...")
        await asyncio.sleep(5)
        
        user.completed_tasks.append(user.current_task_key)
        user.current_task_index += 1
        
        if user.current_task_index >= len(user.tasks_order):
            await update.message.reply_text("✅ ВСЕ ЗАДАНИЯ ВЫПОЛНЕНЫ! Отправь свой ID:")
            user.waiting_for_player_id = True
        else:
            await update.message.reply_text(f"✅ ЗАДАНИЕ {user.current_task_index}/{len(user.tasks_order)} ВЫПОЛНЕНО!")
            await asyncio.sleep(1)
    
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in user_data and user_data[user_id].waiting_for_player_id:
            user = user_data[user_id]
            user.reward_claimed = True
            await update.message.reply_text(f"✅ ID ПРИНЯТ! Награда придет в течение 12 часов!")
            del user_data[user_id]
    
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print(f"✅ МОТИВИШНЫЙ БОТ #{bot_number} ({bot_name}) ЗАПУЩЕН!")
    
    while True:
        await asyncio.sleep(1)

# ========== ГЛАВНЫЙ ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🤖 ЗАПУСК ВСЕХ БОТОВ (ПЕРЕХОДНИК + 9 МОТИВИШНЫХ)")
    print("=" * 60)
    print("📁 Каждый бот имеет свою БД с отдельной статистикой!")
    print("=" * 60)
    
    # Запускаем Flask
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем переходник
    switcher_task = asyncio.create_task(run_switcher())
    
    # Запускаем 9 мотивишных ботов
    bot_tasks = []
    for i, (token, name) in enumerate(zip(BOT_TOKENS, BOT_NAMES)):
        if token:
            task = asyncio.create_task(run_motivation_bot(token, name, i + 1))
            bot_tasks.append(task)
            await asyncio.sleep(2)
    
    await asyncio.gather(switcher_task, *bot_tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 ВСЕ БОТЫ ОСТАНОВЛЕНЫ")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")