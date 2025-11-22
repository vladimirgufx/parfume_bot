import logging
import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, QUESTIONS, PERFUMES

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище данных пользователей
user_data = {}


def log_action(user, action, details=""):
    """Логирует действия пользователя"""
    username = f"@{user.username}" if user.username else "No username"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    logger.info(f"👤 {full_name} ({username}, ID: {user.id}) - {action} {details}")


@bot.message_handler(commands=['start'])
def start(message):
    """Начинаем опрос с приветственного сообщения"""
    user_id = message.from_user.id
    user = message.from_user

    log_action(user, "начал опрос", "/start")

    # Инициализируем данные пользователя
    user_data[user_id] = {
        'answers': [],
        'current_question': 0,
        'question_message_id': None
    }

    # Первое приветственное сообщение с встроенной ссылкой
    welcome_text1 = (
        "Привет! Это твой чат-бот, который теперь работает через супер-бупер конструктор! "
        "<a href='https://puzzlebot.top/'>PuzzleBot ://</a>"
    )

    # Кнопка для первого сообщения
    keyboard1 = InlineKeyboardMarkup()
    keyboard1.add(InlineKeyboardButton("Круто! С чего мне начать?", url="https://puzzlebot.top/"))

    bot.send_message(message.chat.id, welcome_text1, reply_markup=keyboard1, parse_mode='HTML')

    # Второе приветственное сообщение с встроенными ссылками
    welcome_text2 = (
        "Создай свой Telegram бот с 0 — бесплатный курс от <a href='https://t.me/puzzlebot?startapp=faf7157e1d878d50_bfr2'>PuzzleBot ://</a> 🚀\n\n"
        "Еще больше про возможности TG ботов: <a href='https://t.me/wearepuzzlebot'>@wearepuzzlebot</a>\n\n"
        "Бот сделан в <a href='https://puzzlebot.top/?r=ad1'>PuzzleBot ://</a>"
    )

    bot.send_message(message.chat.id, welcome_text2, parse_mode='HTML')

    # Отправляем первый вопрос (без лишнего сообщения)
    send_question(message.chat.id, user_id, user)


def send_question(chat_id, user_id, user):
    """Отправляет текущий вопрос пользователю"""
    current_q = user_data[user_id]['current_question']
    question_data = QUESTIONS[current_q]

    keyboard = InlineKeyboardMarkup()
    for i, option in enumerate(question_data['options']):
        keyboard.add(InlineKeyboardButton(option, callback_data=f'answer_{i}'))

    question_text = f"Вопрос {current_q + 1}/{len(QUESTIONS)}:\n{question_data['text']}"

    log_action(user, f"получает вопрос {current_q + 1}", f"- {question_data['text']}")

    # Если это первый вопрос - отправляем новое сообщение
    if user_data[user_id]['question_message_id'] is None:
        msg = bot.send_message(chat_id, question_text, reply_markup=keyboard)
        user_data[user_id]['question_message_id'] = msg.message_id
    else:
        # Если вопрос уже был - редактируем существующее сообщение
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[user_id]['question_message_id'],
                text=question_text,
                reply_markup=keyboard
            )
        except:
            # Если редактирование не удалось (например, сообщение старое), отправляем новое
            msg = bot.send_message(chat_id, question_text, reply_markup=keyboard)
            user_data[user_id]['question_message_id'] = msg.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_'))
def handle_answer(call):
    """Обрабатывает ответ пользователя"""
    user_id = call.from_user.id
    user = call.from_user

    if user_id not in user_data:
        bot.answer_callback_query(call.id, "Сессия устарела. Начните заново /start")
        log_action(user, "ошибка", "сессия устарела")
        return

    # Извлекаем номер ответа
    answer_index = int(call.data.split('_')[1])
    selected_option = QUESTIONS[user_data[user_id]['current_question']]['options'][answer_index]

    # Логируем выбор пользователя
    current_question = user_data[user_id]['current_question']
    question_text = QUESTIONS[current_question]['text']
    log_action(user, f"выбрал ответ на вопрос {current_question + 1}",
               f"- '{selected_option}' (вопрос: {question_text})")

    user_data[user_id]['answers'].append(answer_index)

    # Показываем короткое уведомление о выборе
    bot.answer_callback_query(call.id, f"Выбрано: {selected_option}")

    # Переходим к следующему вопросу или показываем результаты
    user_data[user_id]['current_question'] += 1

    if user_data[user_id]['current_question'] < len(QUESTIONS):
        send_question(call.message.chat.id, user_id, user)
    else:
        log_action(user, "завершил опрос", f"- всего ответов: {len(user_data[user_id]['answers'])}")
        show_results(call.message, user_id, user)


def show_results(message, user_id, user):
    """Показывает подобранные ароматы"""
    user_answers = user_data[user_id]['answers']

    # Подбираем ароматы
    recommended_perfumes = find_matching_perfumes(user_answers)

    # Логируем результаты подбора
    perfume_names = [p['name'] for p in recommended_perfumes]
    log_action(user, "получил результаты",
               f"- найдено {len(recommended_perfumes)} ароматов: {', '.join(perfume_names)}")

    # Формируем сообщение с результатами
    if not recommended_perfumes:
        result_text = "😔 К сожалению, мы не нашли подходящих ароматов по вашим критериям.\n\nПопробуйте изменить предпочтения или начать поиск заново."
    else:
        result_text = "🎉 Вот ароматы, которые мы подобрали для вас:\n\n"

        for i, perfume in enumerate(recommended_perfumes, 1):
            result_text += f"{i}. *{perfume['name']}*\n"
            result_text += f"   {perfume['description']}\n"
            result_text += f"   💰 {perfume['price']}\n\n"

        result_text += "Выберите аромат для покупки или начните подбор заново:"

    # Создаем клавиатуру с кнопками покупки и перезапуска
    keyboard = InlineKeyboardMarkup()
    if recommended_perfumes:
        for perfume in recommended_perfumes:
            keyboard.add(InlineKeyboardButton(
                f"🛒 Приобрести {perfume['name']}",
                callback_data=f"purchase_{perfume['name'].replace(' ', '_')}"
            ))

    keyboard.add(InlineKeyboardButton("🔄 Начать заново", callback_data="restart"))

    # Редактируем последнее сообщение с вопросом чтобы показать результаты
    try:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=user_data[user_id]['question_message_id'],
            text=result_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except:
        # Если не удалось отредактировать, отправляем новое сообщение
        bot.send_message(
            message.chat.id,
            result_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


def find_matching_perfumes(user_answers):
    """Находит ароматы, подходящие под ответы пользователя"""
    scored_perfumes = []

    for perfume in PERFUMES:
        score = 0
        for q_index, user_answer in enumerate(user_answers):
            if q_index in perfume['tags'] and user_answer in perfume['tags'][q_index]:
                score += 1

        scored_perfumes.append((perfume, score))

    # Сортируем по количеству совпадений (по убыванию)
    scored_perfumes.sort(key=lambda x: x[1], reverse=True)

    # Возвращаем топ-3 аромата с наибольшим количеством совпадений
    return [perfume for perfume, score in scored_perfumes[:3] if score > 0]


@bot.callback_query_handler(func=lambda call: call.data.startswith('purchase_'))
def handle_purchase(call):
    """Обрабатывает нажатие кнопки покупки"""
    user = call.from_user
    perfume_name = call.data.split('_')[1].replace('_', ' ')

    log_action(user, "нажал кнопку покупки", f"- аромат: {perfume_name}")

    bot.answer_callback_query(
        call.id,
        f"Спасибо за интерес к нашему парфюму: {perfume_name}! Скоро здесь будет наш магазин!",
        show_alert=True
    )


@bot.callback_query_handler(func=lambda call: call.data == 'restart')
def handle_restart(call):
    """Перезапускает опрос"""
    user_id = call.from_user.id
    user = call.from_user

    log_action(user, "перезапустил опрос")

    # Очищаем предыдущие ответы
    user_data[user_id] = {
        'answers': [],
        'current_question': 0,
        'question_message_id': None
    }

    # Показываем уведомление о перезапуске
    bot.answer_callback_query(call.id, "Начинаем новый подбор!")

    send_question(call.message.chat.id, user_id, user)


@bot.message_handler(commands=['cancel'])
def cancel(message):
    """Отменяет опрос"""
    user_id = message.from_user.id
    user = message.from_user

    log_action(user, "отменил опрос", "/cancel")

    if user_id in user_data:
        del user_data[user_id]

    bot.send_message(message.chat.id, 'Опрос отменен. Чтобы начать заново, используйте /start')


if __name__ == '__main__':
    print("🤖 Бот запущен и готов к работе!")
    print("📝 Логирование действий пользователей включено...")
    bot.infinity_polling()
