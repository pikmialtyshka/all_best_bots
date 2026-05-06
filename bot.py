import os
import logging
import asyncio
import random
import string
import re
from typing import Dict, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# СПИСОК ТОКЕНОВ ДЛЯ 9 БОТОВ
BOT_TOKENS = [
    "8633809924:AAGLwVQSfBDzQUNU3GKhceMUV_pzNtpcAHA",  # Бот #1 - КС2 Прайм
    "8315119156:AAE6dIIYMsE80f7TVAyby_qMxKtqdzm5EOo",  # Бот #2 - КС2 Скины
    "8633809924:AAGLwVQSfBDzQUNU3GKhceMUV_pzNtpcAHA",  # Бот #3 - Робуксы
    "8445466695:AAGORyjHM8ghSs2jhKblwwrO0-aJNp6Zuq8",  # Бот #4 - Голда Стандофф2
    "8408906854:AAH1o9LAf9kKKMh6mmZj0BGAlsE670DjslA",  # Бот #5 - ТГ НФТ
    "8622662261:AAFfT6Ye6tB8O01QhjYRYinHrxpr9ZykvOw",  # Бот #6 - ТГ Звёзды
    "8562359492:AAFWc3XXKAtCkCh_Y8uznLcY6lFZFdI7gn0",  # Бот #7 - Кинопоиск/Премьер
    "8562359492:AAFWc3XXKAtCkCh_Y8uznLcY6lFZFdI7gn0",  # Бот #8 - Гемы Бравл Старс
    "8562359492:AAFWc3XXKAtCkCh_Y8uznLcY6lFZFdI7gn0",  # Бот #9 - Дополнительный
]

# НАЗВАНИЯ ДЛЯ БОТОВ
BOT_NAMES = [
    "🎮 КС2 ПРАЙМ",
    "🔫 КС2 СКИНЫ",
    "⭐ РОБУКСЫ",
    "💀 ГОЛДА СТАНДОФФ2",
    "🖼️ ТГ НФТ",
    "✨ ТГ ЗВЁЗДЫ",
    "🎬 КИНОПОИСК/ПРЕМЬЕР",
    "💎 ГЕМЫ БРАВЛ СТАРС",
    "🎁 БОНУСНЫЙ БОТ"
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# БАЗОВЫЕ ЗАДАНИЯ (из твоего скрипта)
BASE_TASKS = ["yandex", "sberprime", "yandexplus", "tv24"]

# ИНФОРМАЦИЯ О ЗАДАНИЯХ
TASK_INFO = {
    "yandex": {
        "name": "📱 СКАЧАТЬ ЯНДЕКС БРАУЗЕР",
        "description": "Скачай Яндекс Браузер по ссылке и установи",
        "link": "https://vk.cc/cVUvvJ",
        "button": "🔽 СКАЧАТЬ ЯНДЕКС БРАУЗЕР"
    },
    "sberprime": {
        "name": "💳 СБЕРПРАЙМ ЗА 1 РУБЛЬ",
        "description": "Оформи подписку СберПрайм за 1 рубль\n(если ссылка не открывается, выключи VPN)",
        "link": "https://vk.cc/cVUvEb",
        "button": "💳 ОФОРМИТЬ СБЕРПРАЙМ"
    },
    "yandexplus": {
        "name": "🌟 ЯНДЕКС ПЛЮС (ПОДПИСКА ЗА 1 РУБЛЬ)",
        "description": "Оформи подписку Яндекс Плюс за 1 рубль\n\n🔑 <b>ПРОМОКОД:</b> <code>328652SPMA</code>\n(если ссылка не открывается, выключи VPN)",
        "link": "https://vk.cc/cVUMu5",
        "button": "🌟 ОФОРМИТЬ ЯНДЕКС ПЛЮС"
    },
    "tv24": {
        "name": "🎬 АКТИВИРОВАТЬ ПРОМОКОД 24TV",
        "description": "Перейди по ссылке и активируй промокод",
        "link": "https://vk.cc/cVUwtW",
        "button": "🎬 АКТИВИРОВАТЬ ПРОМОКОД"
    }
}

# КАНАЛЫ ДЛЯ ФЕЙКОВОЙ ПРОВЕРКИ
REQUIRED_CHANNELS = [
    {"name": "🎮 ТЕМКИ", "link": "https://t.me/+X6hEJTznwuc4NWIy", "username": "@temki_brawl"},
    {"name": "🎮 ТЕЛКИ", "link": "https://t.me/+ZAmRG9tQciU0MTNi", "username": "@telki_brawl"},
    {"name": "🎮 ЛЬГОТЫ", "link": "https://t.me/+sqs0iLp5T49iNDEy", "username": "@lgoty_brawl"}
]

def generate_tasks_for_bot(bot_index: int) -> List[str]:
    """Генерирует рандомное количество заданий для бота (3 или 4)"""
    num_tasks = random.choice([3, 4])
    shuffled_tasks = BASE_TASKS.copy()
    random.shuffle(shuffled_tasks)
    bot_tasks = shuffled_tasks[:num_tasks]
    return bot_tasks

# Генерируем конфиги для всех ботов
bots_config = {}
for i, token in enumerate(BOT_TOKENS):
    if token:
        bots_config[token] = {
            "tasks_order": generate_tasks_for_bot(i),
            "bot_name": BOT_NAMES[i],
            "bot_number": i + 1
        }

def is_player_id(text: str) -> bool:
    """Проверяет, является ли текст ID игрока Brawl Stars"""
    patterns = [
        r'^[A-Z0-9]{9}$',
        r'^#[A-Z0-9]{9}$',
        r'^[A-Z0-9]{8,10}$'
    ]
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

async def send_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int, task_name: str, task_num: int, total_tasks: int):
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏰ НАПОМИНАНИЕ!\n\n"
                 f"Ты начал выполнять задания, но так и не завершил!\n\n"
                 f"📋 Ты остановился на {task_name} (Задание {task_num}/{total_tasks})\n\n"
                 f"🎁 Не забывай, что за выполнение всех заданий ты получишь награду!\n\n"
                 f"👉 Продолжить - просто отправь скриншот для этого задания\n"
                 f"❌ Отменить - нажми /start",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка отправки напоминания {user_id}: {e}")

async def check_reminders(context: ContextTypes.DEFAULT_TYPE, user_data: Dict[int, UserState]):
    now = datetime.now()
    to_remove = []
    
    for user_id, user in user_data.items():
        if user.reward_claimed:
            to_remove.append(user_id)
            continue
        
        if user.current_task_index >= len(user.tasks_order):
            continue
        
        time_diff = now - user.last_activity
        hours_passed = time_diff.total_seconds() / 3600
        
        if hours_passed >= 1 and not user.reminder_sent:
            task_key = user.tasks_order[user.current_task_index]
            task_name = TASK_INFO[task_key]["name"]
            task_num = user.current_task_index + 1
            total_tasks = len(user.tasks_order)
            
            await send_reminder(context, user_id, task_name, task_num, total_tasks)
            user.reminder_sent = True
        
        elif hours_passed >= 2 and user.reminder_sent:
            task_key = user.tasks_order[user.current_task_index]
            task_name = TASK_INFO[task_key]["name"]
            task_num = user.current_task_index + 1
            total_tasks = len(user.tasks_order)
            
            await send_reminder(context, user_id, task_name, task_num, total_tasks)
            user.last_activity = now
    
    for user_id in to_remove:
        if user_id in user_data:
            del user_data[user_id]

async def fake_check_subscription(update: Update, user_id: int, bot_name: str) -> bool:
    """ФЕЙКОВАЯ ПРОВЕРКА ПОДПИСКИ - Всегда возвращает True"""
    logger.info(f"🔴 [{bot_name}] Фейк-проверка: пользователь {user_id} прошел проверку")
    return True

async def subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_name: str):
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    keyboard = []
    for channel in REQUIRED_CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 ПОДПИСАТЬСЯ: {channel['name']}", url=channel['link'])])
    
    keyboard.append([InlineKeyboardButton("✅ ПРОВЕРИТЬ ПОДПИСКИ", callback_data="verify_subs")])
    keyboard.append([InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"🔔 ПОДПИШИСЬ НА НАШИ КАНАЛЫ!\n\n"
        f"Для получения награды необходимо подписаться на наши каналы:\n\n"
    )
    
    for channel in REQUIRED_CHANNELS:
        text += f"• {channel['name']}\n"
    
    text += (
        f"\n👇 Нажми на каждую кнопку и подпишись\n"
        f"После подписки нажми «ПРОВЕРИТЬ ПОДПИСКИ»\n\n"
        f"✅ Это БЕСПЛАТНО и займет 10 секунд!"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def verify_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_name: str, user_data: Dict[int, UserState]):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Фейковая проверка - всегда успешна
    is_subscribed = await fake_check_subscription(update, user_id, bot_name)
    
    if is_subscribed:
        if user_id in user_data:
            user = user_data[user_id]
        else:
            user = UserState(user_id, query.from_user.username, user_data["__tasks_order__"])
            user_data[user_id] = user
        
        user.subscriptions_verified = True
        user.current_task_index = 0
        user.completed_tasks = []
        user.last_activity = datetime.now()
        user.reminder_sent = False
        user.waiting_for_screenshot = False
        user.waiting_for_player_id = False
        user.reward_claimed = False
        
        await show_current_task(query, user, bot_name)
    else:
        keyboard = [[InlineKeyboardButton("🔁 ПРОВЕРИТЬ СНОВА", callback_data="verify_subs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="❌ Ты не подписан на все каналы!\n\n"
                 "Пожалуйста, подпишись на каждый канал и нажми «ПРОВЕРИТЬ СНОВА»",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_name: str):
    keyboard = [
        [InlineKeyboardButton("🎁 ПОЛУЧИТЬ НАГРАДУ", callback_data="start_tasks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    text = (
        f"🎮 {bot_name} 🎮\n\n"
        f"Привет, {user.first_name}! 👋\n\n"
        f"💰 Выполни задания и получи награду!\n\n"
        f"👇 Нажми на кнопку:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def start_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_name: str, user_data: Dict[int, UserState]):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id in user_data:
        user = user_data[user_id]
        if user.reward_claimed:
            await query.edit_message_text("❌ Ты уже получил награду! Нельзя проходить задания повторно.", parse_mode=ParseMode.HTML)
            return
    
    await subscriptions_menu(update, context, bot_name)

async def show_current_task(query, user: UserState, bot_name: str):
    user.last_activity = datetime.now()
    user.reminder_sent = False
    
    if not user.subscriptions_verified:
        await subscriptions_menu(query, None, bot_name)
        return
    
    total_tasks = len(user.tasks_order)
    
    if user.current_task_index >= total_tasks:
        user.waiting_for_player_id = True
        await query.edit_message_text(
            text=f"✅ ПОЗДРАВЛЯЮ! ТЫ ВЫПОЛНИЛ ВСЕ {total_tasks} ЗАДАНИЙ! 🎉🎉🎉\n\n"
                 f"━━━━━━━━━━━━━━━━━━━━━━\n"
                 f"🎁 ТЕПЕРЬ ОТПРАВЬ СВОЙ ID BRAWL STARS:\n\n"
                 f"📌 Как найти свой ID:\n"
                 f"1. Открой игру Brawl Stars\n"
                 f"2. Нажми на свой профиль\n"
                 f"3. Скопируй ID (9 символов, буквы и цифры)\n"
                 f"4. Отправь его сюда\n\n"
                 f"Пример: <code>2YU9R0P8C</code> или <code>#2YU9R0P8C</code>\n\n"
                 f"━━━━━━━━━━━━━━━━━━━━━━\n"
                 f"⏱ Награда придет в течение 12 часов!\n"
                 f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 f"❌ Отмена - нажми /start",
            parse_mode=ParseMode.HTML
        )
        return
    
    task_key = user.tasks_order[user.current_task_index]
    task = TASK_INFO[task_key]
    
    current = user.current_task_index + 1
    total = total_tasks
    
    text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 ЗАДАНИЕ {current} ИЗ {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{task['name']}\n\n"
        f"{task['description']}\n\n"
        f"🔗 <a href='{task['link']}'>👉 {task['button']} 👈</a>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 КАК ПОДТВЕРДИТЬ:\n"
        f"После выполнения отправь СКРИНШОТ подтверждения\n"
        f"⏱ Автопроверка займет 5 секунд\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❌ Отмена - нажми /start\n"
        f"⏰ Если забудешь - я напомню через 1-2 часа!"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ ОТМЕНИТЬ ВСЕ", callback_data="cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user.waiting_for_screenshot = True
    user.current_task_key = task_key
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_name: str, user_data: Dict[int, UserState]):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await main_menu(update, context, bot_name)

async def handle_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: Dict[int, UserState], bot_name: str):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_data:
        await update.message.reply_text("❌ Сначала нажми /start и выбери 'ПОЛУЧИТЬ НАГРАДУ'")
        return
    
    user = user_data[user_id]
    
    if not user.waiting_for_player_id:
        await update.message.reply_text("❌ Сейчас не нужно отправлять ID. Сначала выполни все задания!")
        return
    
    clean_id = text.replace('#', '').strip().upper()
    
    if not is_player_id(clean_id):
        await update.message.reply_text(
            "❌ Это не похоже на ID игрока Brawl Stars!\n\n"
            "📌 Правильный формат:\n"
            "ID состоит из 9 символов (буквы и цифры)\n\n"
            "Пример: <code>2YU9R0P8C</code> или <code>#2YU9R0P8C</code>\n\n"
            "Попробуй еще раз или нажми /start для отмены",
            parse_mode=ParseMode.HTML
        )
        return
    
    user.player_id = clean_id
    user.reward_claimed = True
    user.waiting_for_player_id = False
    
    await update.message.reply_text(
        f"✅ ID BRAWL STARS ПРИНЯТ!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 ТВОЙ ID: <code>{user.player_id}</code>\n\n"
        f"💰 НАГРАДА БУДЕТ ЗАЧИСЛЕНА В ТЕЧЕНИЕ 12 ЧАСОВ!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 Сохрани этот диалог, если возникнут вопросы.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Спасибо за участие! 🎮",
        parse_mode=ParseMode.HTML
    )
    
    del user_data[user_id]

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: Dict[int, UserState], bot_name: str):
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("❌ Сначала нажми /start и выбери 'ПОЛУЧИТЬ НАГРАДУ'")
        return
    
    user = user_data[user_id]
    
    if user.reward_claimed:
        await update.message.reply_text("❌ Ты уже получил награду!")
        return
    
    if not user.waiting_for_screenshot:
        await update.message.reply_text("❌ Сейчас не нужно отправлять скриншот. Нажми /start")
        return
    
    user.last_activity = datetime.now()
    user.reminder_sent = False
    
    photo = update.message.photo[-1]
    user.waiting_for_screenshot = False
    
    current_num = user.current_task_index + 1
    total_tasks = len(user.tasks_order)
    task_name = TASK_INFO[user.current_task_key]["name"]
    
    checking_msg = await update.message.reply_text(
        f"⏳ ПРОВЕРКА ЗАДАНИЯ {current_num}/{total_tasks}...\n\n"
        f"📋 {task_name}\n\n"
        f"🔍 Идет автоматическая проверка скриншота...\n"
        f"⏱ Подожди 5 секунд!\n\n"
        f"Не отправляй новые сообщения!"
    )
    
    async def check_and_next():
        await asyncio.sleep(5)
        
        try:
            await checking_msg.delete()
        except:
            pass
        
        completed_task = user.current_task_key
        user.completed_tasks.append(completed_task)
        user.current_task_index += 1
        
        if user.current_task_index >= total_tasks:
            await update.message.reply_text(
                f"✅ ЗАДАНИЕ {current_num}/{total_tasks} ВЫПОЛНЕНО!\n\n"
                f"🎉 ПОЗДРАВЛЯЮ! ТЫ ВЫПОЛНИЛ ВСЕ ЗАДАНИЯ!\n\n"
                f"🎁 Теперь отправь свой ID Brawl Stars, чтобы получить награду!"
            )
            await asyncio.sleep(2)
            
            class DummyQuery:
                def __init__(self, user_id):
                    self.from_user = type('obj', (object,), {'id': user_id})
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            
            dummy = DummyQuery(user_id)
            await show_current_task(dummy, user, bot_name)
        else:
            await update.message.reply_text(
                f"✅ ЗАДАНИЕ {current_num}/{total_tasks} ВЫПОЛНЕНО!\n\n"
                f"Отлично! Переходим к заданию {current_num + 1}/{total_tasks}... 🚀"
            )
            await asyncio.sleep(2)
            
            class DummyQuery:
                def __init__(self, user_id):
                    self.from_user = type('obj', (object,), {'id': user_id})
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None, disable_web_page_preview=None):
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode, disable_web_page_preview=disable_web_page_preview)
            
            dummy = DummyQuery(user_id)
            await show_current_task(dummy, user, bot_name)
    
    asyncio.create_task(check_and_next())

async def run_bot(bot_token: str, bot_config: dict):
    """Запуск одного бота"""
    bot_name = bot_config["bot_name"]
    bot_number = bot_config["bot_number"]
    tasks_order = bot_config["tasks_order"]
    
    print(f"🚀 БОТ #{bot_number} ЗАПУСКАЕТСЯ...")
    print(f"📛 Имя: {bot_name}")
    print(f"📋 Заданий: {len(tasks_order)}")
    print(f"📝 Список: {tasks_order}")
    print("-" * 40)
    
    user_data: Dict[int, UserState] = {}
    user_data["__tasks_order__"] = tasks_order
    
    application = Application.builder().token(bot_token).build()
    
    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await main_menu(update, context, bot_name)
    
    async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data == "start_tasks":
            await start_tasks(update, context, bot_name, user_data)
        elif data == "cancel":
            await handle_cancel(update, context, bot_name, user_data)
        elif data == "verify_subs":
            await verify_subscriptions(update, context, bot_name, user_data)
    
    async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await handle_screenshot(update, context, user_data, bot_name)
    
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text and not update.message.text.startswith('/'):
            await handle_player_id(update, context, user_data, bot_name)
    
    async def reminder_callback(context: ContextTypes.DEFAULT_TYPE):
        await check_reminders(context, user_data)
    
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(reminder_callback, interval=1800, first=60)
    
    print(f"✅ БОТ #{bot_number} ({bot_name}) УСПЕШНО ЗАПУЩЕН!")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print(f"🛑 БОТ #{bot_number} ({bot_name}) ОСТАНОВЛЕН")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

async def main():
    """Запуск всех ботов"""
    print("=" * 60)
    print("🤖 ЗАПУСК 9 БОТОВ С РАНДОМНЫМИ ЗАДАНИЯМИ")
    print("=" * 60)
    
    for token, config in bots_config.items():
        print(f"Бот #{config['bot_number']}: {config['bot_name']} -> {len(config['tasks_order'])} заданий: {config['tasks_order']}")
    
    print("=" * 60)
    print("✅ ФЕЙКОВАЯ ПРОВЕРКА ПОДПИСОК АКТИВНА")
    print("=" * 60)
    
    tasks = []
    for token, config in bots_config.items():
        if token:
            task = asyncio.create_task(run_bot(token, config))
            tasks.append(task)
            await asyncio.sleep(2)
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        print("❌ НЕТ ВАЛИДНЫХ ТОКЕНОВ!")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 ВСЕ БОТЫ ОСТАНОВЛЕНЫ")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")