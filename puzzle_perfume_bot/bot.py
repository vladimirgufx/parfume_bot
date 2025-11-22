import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
from config import BOT_TOKEN, QUESTIONS, PERFUMES

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Стадии разговора
QUESTION, RESULTS = range(2)


class PerfumeBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                QUESTION: [CallbackQueryHandler(self.handle_answer, pattern='^answer_')],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CallbackQueryHandler(self.restart, pattern='^restart$'))
        self.application.add_handler(CallbackQueryHandler(self.purchase, pattern='^purchase_'))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начинаем опрос с приветственного сообщения"""
        user = update.message.from_user
        logger.info("Пользователь %s начал опрос", user.first_name)

        # Первое приветственное сообщение с встроенной ссылкой
        welcome_text1 = (
            "Привет! Это твой чат-бот, который теперь работает через супер-бупер конструктор! "
            "<a href='https://puzzlebot.top/'>PuzzleBot ://</a>"
        )

        # Кнопка для первого сообщения
        keyboard1 = [[InlineKeyboardButton("Круто! С чего мне начать?", url="https://puzzlebot.top/")]]
        reply_markup1 = InlineKeyboardMarkup(keyboard1)

        await update.message.reply_text(welcome_text1, reply_markup=reply_markup1, parse_mode='HTML')

        # Второе приветственное сообщение с встроенными ссылками
        welcome_text2 = (
            "Создай свой Telegram бот с 0 — бесплатный курс от <a href='https://t.me/puzzlebot?startapp=faf7157e1d878d50_bfr2'>PuzzleBot ://</a> 🚀\n\n"
            "Еще больше про возможности TG ботов: <a href='https://t.me/wearepuzzlebot'>@wearepuzzlebot</a>\n\n"
            "Бот сделан в <a href='https://puzzlebot.top/?r=ad1'>PuzzleBot ://</a>"
        )

        await update.message.reply_text(welcome_text2, parse_mode='HTML')
    

        # Инициализируем данные пользователя
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0

        # Затем отправляем первый вопрос
        await self.send_question(update, context)
        return QUESTION

    async def send_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет текущий вопрос пользователю"""
        current_q = context.user_data['current_question']
        question_data = QUESTIONS[current_q]

        keyboard = []
        for i, option in enumerate(question_data['options']):
            keyboard.append([InlineKeyboardButton(option, callback_data=f'answer_{i}')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Определяем, откуда отправлять сообщение
        if update.callback_query:
            query = update.callback_query
            await query.edit_message_text(
                text=f"Вопрос {current_q + 1}/{len(QUESTIONS)}:\n{question_data['text']}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=f"Вопрос {current_q + 1}/{len(QUESTIONS)}:\n{question_data['text']}",
                reply_markup=reply_markup
            )

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает ответ пользователя"""
        query = update.callback_query
        await query.answer()

        # Извлекаем номер ответа
        answer_index = int(query.data.split('_')[1])
        context.user_data['answers'].append(answer_index)

        # Переходим к следующему вопросу или показываем результаты
        context.user_data['current_question'] += 1

        if context.user_data['current_question'] < len(QUESTIONS):
            await self.send_question(update, context)
            return QUESTION
        else:
            await self.show_results(update, context)
            return ConversationHandler.END

    async def show_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает подобранные ароматы"""
        user_answers = context.user_data['answers']

        # Подбираем ароматы
        recommended_perfumes = self.find_matching_perfumes(user_answers)

        # Формируем сообщение с результатами
        if not recommended_perfumes:
            result_text = "😔 К сожалению, мы не нашли подходящих ароматов по вашим критериям.\n\nПопробуйте изменить предпочтения или начать поиск заново."
        else:
            result_text = "🎉 Вот ароматы, которые мы подобрали для вас:\n\n"

            for i, perfume in enumerate(recommended_perfumes, 1):
                result_text += f"{i}. **{perfume['name']}**\n"
                result_text += f"   {perfume['description']}\n"
                result_text += f"   💰 {perfume['price']}\n\n"

            result_text += "Выберите аромат для покупки или начните подбор заново:"

        # Создаем клавиатуру с кнопками покупки и перезапуска
        keyboard = []
        if recommended_perfumes:
            for perfume in recommended_perfumes:
                keyboard.append([InlineKeyboardButton(
                    f"🛒 Приобрести {perfume['name']}",
                    callback_data=f"purchase_{perfume['name'].replace(' ', '_')}"
                )])

        keyboard.append([InlineKeyboardButton("🔄 Начать заново", callback_data="restart")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query = update.callback_query
        await query.edit_message_text(
            text=result_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def find_matching_perfumes(self, user_answers):
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

    async def purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает нажатие кнопки покупки"""
        query = update.callback_query
        perfume_name = query.data.split('_')[1].replace('_', ' ')

        await query.answer(f"Спасибо за интерес к нашему парфюму: {perfume_name}! Скоро здесь будет наш магазин!",
                           show_alert=True)

    async def restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перезапускает опрос"""
        query = update.callback_query
        await query.answer()

        # Очищаем предыдущие ответы
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0

        await self.send_question(update, context)
        return QUESTION

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отменяет опрос"""
        user = update.message.from_user
        logger.info("Пользователь %s отменил опрос", user.first_name)
        await update.message.reply_text('Опрос отменен. Чтобы начать заново, используйте /start')
        return ConversationHandler.END

    def run(self):
        """Запускает бота"""
        self.application.run_polling()


if __name__ == '__main__':
    bot = PerfumeBot()
    bot.run()