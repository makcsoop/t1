import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler
)
import psycopg2
from dotenv import load_dotenv
import schedule
import time
import threading

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "8328066857:AAH9cheGTamRTWrg7IVVdv7zopLEEjhs7xY"  # ВСТАВЬТЕ ВАШ ТОКЕН ЗДЕСЬ
DATABASE_URL = "postgresql://username:password@localhost:5432/sites_monitoring"

# Состояния для ConversationHandler
ENTER_URL, SELECT_FAVORITE = range(2)  # УПРОСТИЛИ диапазон состояний


def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sites (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id SERIAL PRIMARY KEY,
            site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE,
            uptime REAL,
            lcp REAL,
            inp REAL,
            cls REAL,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE,
            UNIQUE(user_id, site_id)
        )
        ''')

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")


def execute_query(query, params=None, fetch=False, fetchall=False):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(query, params or ())

        if fetch:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None

        conn.commit()
        return result

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


# Главное меню
def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("Проверить сайт"), KeyboardButton("Упр. избранным")],

        # Вторая строка: 2 кнопки
        [KeyboardButton("Подробный отчет"), KeyboardButton("Уведомления")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Меню проверки сайта
def get_check_site_keyboard():
    keyboard = [
        [InlineKeyboardButton("Ввести ссылку на сайт", callback_data="enter_url")],
        [InlineKeyboardButton("Из избранного", callback_data="check_favorite")],
        [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Меню управления избранным
def get_favorites_keyboard():
    keyboard = [
        [InlineKeyboardButton("Список избранного", callback_data="list_favorites")],
        [InlineKeyboardButton("Добавить в избранное", callback_data="add_to_favorites")],
        [InlineKeyboardButton("Удалить из избранного", callback_data="remove_from_favorites")],
        [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Меню подробного отчета
def get_max_site_keyboard():
    keyboard = [
        [InlineKeyboardButton("Полноценный отчёт", callback_data="full_report")],
        [InlineKeyboardButton("Экспорт в Excel", callback_data="export_excel")],
        [InlineKeyboardButton("Графики", callback_data="show_charts")],
        [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Меню для одного сайта
def get_single_site_keyboard():
    keyboard = [
        [InlineKeyboardButton("История проверок", callback_data="check_history")],
        [InlineKeyboardButton("Быстрая проверка", callback_data="quick_check")],
        [InlineKeyboardButton("Планирование", callback_data="schedule_check")],
        [InlineKeyboardButton("Сохранить в список", callback_data="save_to_list")],
        [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Меню для многих сайтов
def get_multi_site_keyboard():
    keyboard = [
        [InlineKeyboardButton("Сводная таблица", callback_data="summary_table")],
        [InlineKeyboardButton("Список сайтов", callback_data="sites_list")],
        [InlineKeyboardButton("Проверить все", callback_data="check_all")],
        [InlineKeyboardButton("Групповой экспорт", callback_data="batch_export")],
        [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Меню уведомлений
def get_notifications_keyboard():
    keyboard = [
        [InlineKeyboardButton("Настройка уведомлений", callback_data="setup_notifications")],
        [InlineKeyboardButton("Планировщик", callback_data="scheduler")],
        [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Обработчик ввода URL
async def enter_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    await perform_site_check(update, url)
    return ConversationHandler.END


# Отмена ввода
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ввод отменен.",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


# Обработчик главного меню
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Старт":
        await update.message.reply_text(
            "Добро пожаловать в мониторинг сайтов!\n\n"
            "Выберите действие из меню:",
            reply_markup=get_main_menu_keyboard()
        )

    elif text == "Проверить сайт":
        await update.message.reply_text(
            "Проверить сайт\n\n"
            "Выберите способ проверки:",
            reply_markup=get_check_site_keyboard()
        )

    elif text == "Управление избранным":
        await update.message.reply_text(
            "Управление избранным\n\n"
            "Выберите действие:",
            reply_markup=get_favorites_keyboard()
        )

    elif text == "Подробный отчёт":
        await update.message.reply_text(
            "Подробные отчеты\n\n"
            "Выберите тип отчета:",
            reply_markup=get_max_site_keyboard()
        )

    elif text == "Настройка уведомлений":
        await update.message.reply_text(
            "Настройка уведомлений\n\n"
            "Управление уведомлениями:",
            reply_markup=get_notifications_keyboard()
        )

    elif text == "Если 1 сайт":
        await update.message.reply_text(
            "Управление одним сайтом\n\n"
            "Выберите действие:",
            reply_markup=get_single_site_keyboard()
        )

    elif text == "Если много сайтов":
        await update.message.reply_text(
            "Управление множеством сайтов\n\n"
            "Выберите действие:",
            reply_markup=get_multi_site_keyboard()
        )


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я — PingTower, твой личный ассистент по мониторингу сайтов.\n\n"
        "Я отслеживаю:\n"
"🟢 Uptime и доступность\n"
"⚡️ Скорость загрузки (LCP, FCP, SI)\n"
"🖱 Отзывчивость (INP, TBT)\n"
"🧱 Визуальную стабильность (CLS)\n"
"🔐 SSL и DNS",
        reply_markup=get_main_menu_keyboard()
    )


# Обработчик callback кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        await query.edit_message_text(
          #  "Главное меню:",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выберите опцию:",
            reply_markup=get_main_menu_keyboard()
        )
    

    elif query.data == "enter_url":
        await query.edit_message_text(
            "Введите сссылку на сайт для проверки:\n\n"
            "Пример: https://example.com\n\n"
            "Для отмены введите /cancel",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩Назад", callback_data="check_site_back")]])
        )
        return ENTER_URL

    elif query.data == "check_favorite":
        user_id = query.from_user.id
        favorites = execute_query(
            "SELECT s.id, s.name FROM sites s JOIN user_favorites uf ON s.id = uf.site_id WHERE uf.user_id = %s",
            (user_id,),
            fetchall=True
        )

        if not favorites:
            await query.edit_message_text(
                "У вас нет избранных сайтов.",
                reply_markup=get_check_site_keyboard()
            )
            return

        keyboard = []
        for site_id, name in favorites:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"check_fav_{site_id}")])
        keyboard.append([InlineKeyboardButton("↩Назад", callback_data="check_site_back")])

        await query.edit_message_text(
            "Выберите сайт из избранного:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("check_fav_"):
        site_id = int(query.data.split("_")[2])
        result = execute_query("SELECT url FROM sites WHERE id = %s", (site_id,), fetch=True)
        if result:
            await perform_site_check(query, result[0], site_id)

    elif query.data == "check_site_back":
        await query.edit_message_text(
            "Проверить сайт\n\nВыберите способ проверки:",
            reply_markup=get_check_site_keyboard()
        )

    elif query.data == "list_favorites":
        user_id = query.from_user.id
        favorites = execute_query(
            "SELECT s.name, s.url FROM sites s JOIN user_favorites uf ON s.id = uf.site_id WHERE uf.user_id = %s",
            (user_id,),
            fetchall=True
        )

        if not favorites:
            await query.edit_message_text(
                "У вас нет избранных сайтов.",
                reply_markup=get_favorites_keyboard()
            )
            return

        message = "Ваши избранные сайты:\n\n"
        for name, url in favorites:
            message += f"• {name} ({url})\n"

        await query.edit_message_text(
            message,
            reply_markup=get_favorites_keyboard()
        )

    elif query.data == "add_to_favorites":
        sites = execute_query("SELECT id, name FROM sites", fetchall=True)

        if not sites:
            await query.edit_message_text(
                "Нет сайтов для добавления.",
                reply_markup=get_favorites_keyboard()
            )
            return

        keyboard = []
        for site_id, name in sites:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"add_fav_{site_id}")])
        keyboard.append([InlineKeyboardButton("↩Назад", callback_data="favorites_back")])

        await query.edit_message_text(
            "Выберите сайт для добавления в избранное:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("add_fav_"):
        site_id = int(query.data.split("_")[2])
        user_id = query.from_user.id

        execute_query(
            "INSERT INTO user_favorites (user_id, site_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, site_id)
        )

        await query.edit_message_text(
            "Сайт добавлен в избранное!",
            reply_markup=get_favorites_keyboard()
        )

    elif query.data == "favorites_back":
        await query.edit_message_text(
            "Управление избранным\n\nВыберите действие:",
            reply_markup=get_favorites_keyboard()
        )

    elif query.data == "full_report":
        await generate_full_report(query)

    elif query.data == "export_excel":
        await export_to_excel(query)

    elif query.data == "check_history":
        await show_check_history(query)

    elif query.data == "quick_check":
        await quick_site_check(query)

    elif query.data == "summary_table":
        await show_summary_table(query)

    elif query.data == "check_all":
        await check_all_sites(query)

    else:
        await query.edit_message_text(
            "Команда не распознана.",
            reply_markup=get_main_menu_keyboard()
        )


# Функция проверки сайта
async def perform_site_check(update, url, site_id=None):
    try:
        # Заглушка для проверки
        import random
        metrics = {
            'uptime': round(random.uniform(99.5, 100.0), 2),
            'lcp': round(random.uniform(0.5, 3.0), 1),
            'inp': random.randint(50, 200),
            'cls': round(random.uniform(0.01, 0.2), 2)
        }

        if site_id:
            execute_query(
                "INSERT INTO metrics (site_id, uptime, lcp, inp, cls) VALUES (%s, %s, %s, %s, %s)",
                (site_id, metrics['uptime'], metrics['lcp'], metrics['inp'], metrics['cls'])
            )

        report = f" {url}\n"
        report += f"Время проверки: {datetime.now().strftime('%H:%M')}\n"
        report += f"Uptime: {metrics['uptime']}%\n"
        report += f"LCP: {metrics['lcp']}s\n"
        report += f"INP: {metrics['inp']}ms\n"
        report += f"CLS: {metrics['cls']}\n"

        keyboard = [
            [InlineKeyboardButton("Добавить в избранное", callback_data=f"add_fav_{site_id or 'new'}")],
            [InlineKeyboardButton("Подробный отчет", callback_data="full_report")],
            [InlineKeyboardButton("↩Назад", callback_data="main_menu")]
        ]

        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(report, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(f"Error in site check: {e}")


# Дополнительные функции
async def generate_full_report(query):
    await query.edit_message_text(
        "Генерирую полный отчет...",
        reply_markup=get_max_site_keyboard()
    )


async def export_to_excel(query):
    await query.edit_message_text(
        "Экспортирую в Excel...",
        reply_markup=get_max_site_keyboard()
    )


async def show_check_history(query):
    await query.edit_message_text(
        "История проверок...",
        reply_markup=get_single_site_keyboard()
    )


async def quick_site_check(query):
    await query.edit_message_text(
        "Быстрая проверка...",
        reply_markup=get_single_site_keyboard()
    )


async def show_summary_table(query):
    await query.edit_message_text(
        "Сводная таблица...",
        reply_markup=get_multi_site_keyboard()
    )


async def check_all_sites(query):
    await query.edit_message_text(
        "Проверяю все сайты...",
        reply_markup=get_multi_site_keyboard()
    )


def main():
    # Проверка конфигурации
    if not BOT_TOKEN:
        print("ОШИБКА: Установите BOT_TOKEN в .env файле!")
        return

    try:
        # Пробуем инициализировать БД, но не падаем при ошибке
        try:
            init_db()
        except Exception as e:
            print(f"⚠️  Предупреждение: Не удалось инициализировать БД: {e}")
            print("⚠️  Бот запустится без функционала базы данных")

        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()

        # Настройка ConversationHandler для ввода URL
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_handler, pattern='^enter_url$')],
            states={
                ENTER_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_url)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        application.add_handler(CommandHandler("start", start))
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))

        print("Бот запускается с расширенным меню...")
        application.run_polling()

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == '__main__':
    main()
