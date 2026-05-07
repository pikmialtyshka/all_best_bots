import os
import sqlite3
from datetime import datetime, timedelta
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
os.environ['TZ'] = 'Europe/Moscow'
TOKEN = '8692515951:AAFoPto-22C9rilnMJHAif36bXvUDm08nP4'

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

# ========== 9 МОТИВИШНЫХ БОТОВ ==========
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

# ========== ВЕБ-СЕРВЕР (FLASK) ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'Бот работает! 🤖'

def run_flask():
    port = int(os.environ.get('PORT', 3000))
    flask_app.run(host='0.0.0.0', port=port)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('./users.db')
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
    print('✅ База данных готова')

def save_user(user_id, username, first_name):
    try:
        conn = sqlite3.connect('./users.db')
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
        print(f'Ошибка сохранения: {e}')

def get_total_users():
    conn = sqlite3.connect('./users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM users')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_today_users():
    conn = sqlite3.connect('./users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE DATE(last_seen) = DATE('now', 'localtime')
    ''')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_week_users():
    conn = sqlite3.connect('./users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE last_seen >= datetime('now', 'localtime', '-7 days')
    ''')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_month_users():
    conn = sqlite3.connect('./users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) as count FROM users 
        WHERE last_seen >= datetime('now', 'localtime', '-30 days')
    ''')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_recent_users():
    conn = sqlite3.connect('./users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, first_name, last_seen 
        FROM users 
        ORDER BY last_seen DESC 
        LIMIT 5
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows or []

def is_admin(username):
    if not username:
        return False
    return username.lower() in [a.lower() for a in ADMINS]

def should_hide_cheburashka(username):
    if not username:
        return False
    return username.lower() in [e.lower() for e in EXCLUDED_FROM_CHEBURASHKA]

# ========== КНОПКИ ==========
def get_main_menu(is_admin_user, hide_cheburashka):
    keyboard = []
    
    # ===== ОСНОВНЫЕ ПРОДУКТЫ (сначала) =====
    keyboard.append([InlineKeyboardButton('👻 Дyxлec | Поиск по номеру 📱', url='https://t.me/Karmarseebot?start=r_G5Z95D57TN')])
    keyboard.append([InlineKeyboardButton('🕵️‍♂️ Шepлok | Поиск по фото 👁', url='https://t.me/kisankanatop_bot?start=_ref_yalLl8WEx_Ipg17UPFM')])
    keyboard.append([InlineKeyboardButton('🔐 RuVPN | Безопасный VPN 🌐', url='https://t.me/ruvpn?start=partner_1860340689')])
    keyboard.append([InlineKeyboardButton('👗 Раздеватор | AI раздевалка 🔥', url='https://t.me/razdevator_bot?start=ref')])  # Раздеватор
    keyboard.append([
        InlineKeyboardButton('📸 Инcтa Шnuoн', url='https://instashpion.ru?p=9cd42aee57cb325637213b895e815200'),
        InlineKeyboardButton('👥 BK Шnuoн', url='https://kogdavseti.ru/?p=0e11c1032d9ed026dcf04fdedad15355')
    ])
    keyboard.append([InlineKeyboardButton('🎲 Генератор потеx 🎭', url='https://gratzbot.app/?start=ref-de2e2b04')])
    
    # Кнопка "Глаз Чебурашки"
    if not hide_cheburashka:
        keyboard.append([InlineKeyboardButton('👁 Глаз Чебурашки 🔍', url='https://t.me/search_ot_cheburashki_bot?start=_ref_kGDGyBSDx_kN7fr6pCO')])
    
    # ===== МОТИВИШНЫЕ БОТЫ (после основных) =====
    keyboard.append([InlineKeyboardButton('⭐ ⭐ ⭐ ПОЛЕЗНЫЕ БОТЫ ⭐ ⭐ ⭐', callback_data='noop')])
    
    # 9 мотивишных ботов (по 2 в ряд)
    for i in range(0, len(MOTIVATION_BOTS), 2):
        row = []
        bot1 = MOTIVATION_BOTS[i]
        row.append(InlineKeyboardButton(bot1['name'], url=bot1['url']))
        
        if i + 1 < len(MOTIVATION_BOTS):
            bot2 = MOTIVATION_BOTS[i + 1]
            row.append(InlineKeyboardButton(bot2['name'], url=bot2['url']))
        
        keyboard.append(row)
    
    # Админ-панель
    if is_admin_user:
        keyboard.append([InlineKeyboardButton('👑 АДМИН-ПАНЕЛЬ 👑', callback_data='admin_panel')])
    
    return InlineKeyboardMarkup(keyboard)

# ========== ОБРАБОТЧИКИ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Сохраняем пользователя
    save_user(user.id, user.username, user.first_name)
    
    # Проверяем, нужно ли скрыть кнопку Чебурашки
    hide_cheburashka = should_hide_cheburashka(user.username)
    
    text = f"""
🔍 <b>ВЫБЕРИТЕ НУЖНЫЙ СЕРВИС</b> 🔍

Привет, {user.first_name or 'друг'}! 👋

<b>🔹 ОСНОВНЫЕ СЕРВИСЫ:</b>
👻 Дyxлec - поиск по номеру
🕵️‍♂️ Шepлok - поиск по фото
🔐 RuVPN - безопасный VPN
👗 Раздеватор - AI раздевалка
📸 Инcтa Шпион - Instagram
👥 BK Шпион - ВКонтакте
🎲 Генератор потеx - генератор

<b>🔸 БЕСПЛАТНЫЕ НАГРАДЫ:</b>
💎 9 ботов для получения подарков

👇 <b>Нажми на кнопку:</b>
    """
    
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_main_menu(is_admin(user.username), hide_cheburashka))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    hide_cheburashka = should_hide_cheburashka(user.username)
    await update.message.reply_text(
        '📚 /start - Главное меню\n/help - Помощь',
        reply_markup=get_main_menu(is_admin(user.username), hide_cheburashka)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    chat_id = query.message.chat_id
    data = query.data
    
    if data == 'noop':
        await query.answer('⬇️ Боты ниже ⬇️', show_alert=False)
    
    elif data == 'admin_panel':
        # Проверка админа
        if not is_admin(user.username):
            await query.answer('⛔ Только для админов', show_alert=True)
            return
        
        # Получаем статистику
        total = get_total_users()
        today = get_today_users()
        week = get_week_users()
        month = get_month_users()
        recent = get_recent_users()
        
        # Формируем время (МСК)
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        time_str = now.strftime('%d.%m %H:%M')
        
        text = f"👑 <b>АДМИН-ПАНЕЛЬ</b> (МСК {time_str})\n\n"
        text += f"📊 <b>СТАТИСТИКА:</b>\n"
        text += f"• Всего пользователей: <b>{total}</b>\n"
        text += f"• За сегодня: <b>{today}</b>\n"
        text += f"• За неделю: <b>{week}</b>\n"
        text += f"• За месяц: <b>{month}</b>\n\n"
        
        text += f"🕐 <b>Последние 5 пользователей (МСК):</b>\n"
        if not recent:
            text += "   Пока нет пользователей\n"
        else:
            for i, row in enumerate(recent, 1):
                username, first_name, last_seen = row
                name = first_name or 'Без имени'
                username_str = f"@{username}" if username else 'нет username'
                try:
                    last_seen_date = datetime.strptime(last_seen, '%Y-%m-%d %H:%M:%S')
                    last_seen_date = msk_tz.localize(last_seen_date)
                    date_str = last_seen_date.strftime('%d.%m %H:%M')
                except:
                    date_str = last_seen
                text += f"{i}. {name} ({username_str})\n   🕐 {date_str}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('🔄 Обновить', callback_data='admin_panel')],
            [InlineKeyboardButton('◀️ Назад', callback_data='back')]
        ])
        
        try:
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
        except:
            await query.message.reply_text(text, parse_mode='HTML', reply_markup=keyboard)
    
    elif data == 'back':
        hide_cheburashka = should_hide_cheburashka(user.username)
        try:
            await query.delete_message()
            await context.bot.send_message(
                chat_id,
                "🔍 <b>ВЫБЕРИТЕ НУЖНЫЙ СЕРВИС</b> 🔍\n\n👇 Нажми на кнопку:",
                parse_mode='HTML',
                reply_markup=get_main_menu(is_admin(user.username), hide_cheburashka)
            )
        except Exception as e:
            print(f'Ошибка: {e}')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработка обычных сообщений (не команд)
    user = update.effective_user
    save_user(user.id, user.username, user.first_name)

# ========== ЗАПУСК ==========
def main():
    # Инициализируем БД
    init_db()
    
    # Запускаем Flask в отдельном потоке
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Создаем приложение бота
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Запускаем бота (polling)
    print('🤖 Бот-переходник запущен!')
    print('=' * 50)
    print('🔹 ОСНОВНЫЕ ПРОДУКТЫ:')
    print('   👻 Дyxлec - поиск по номеру')
    print('   🕵️ Шepлok - поиск по фото')
    print('   🔐 RuVPN - VPN')
    print('   👗 Раздеватор - AI раздевалка')
    print('   📸 Инста Шпион')
    print('   👥 ВК Шпион')
    print('   🎲 Генератор потеx')
    print('=' * 50)
    print('🔸 МОТИВИШНЫЕ БОТЫ (9 шт):')
    for i, bot in enumerate(MOTIVATION_BOTS, 1):
        print(f'   {i}. {bot["name"]}')
    print('=' * 50)
    print('👑 Админы:', ', '.join(ADMINS))
    print('🚫 Исключения для Чебурашки:', ', '.join(EXCLUDED_FROM_CHEBURASHKA))
    print('=' * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()