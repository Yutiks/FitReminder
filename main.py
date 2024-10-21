import telebot
from datetime import datetime, timedelta
import json
import time

token = '7867075831:AAECmnAQgeXsHecLlstDoPXczhIZz6OL-iQ'
bot = telebot.TeleBot(token)
user_data = {}
available_workouts = ["Бег", "Силовая тренировка", "Плавание", "Растяжка", "Велотренировка"]
user_deleting_workout = {}

try:
    with open('workouts.json', 'r') as file:
        pass
except FileNotFoundError:
    with open('workouts.json', 'w') as file:
        json.dump({}, file)

try:
    with open('journal.json', 'r') as file:
        pass
except FileNotFoundError:
    with open('journal.json', 'w') as file:
        json.dump({}, file)


@bot.message_handler(['add_workout'])
def add_workout(message):
    user_data[message.chat.id] = {'state': 'selecting_workout'}
    keyboard = telebot.types.InlineKeyboardMarkup()
    for workout in available_workouts:
        button = telebot.types.InlineKeyboardButton(workout, callback_data=f"workout_{workout}")
        keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите тренировку:", reply_markup=keyboard)


def is_workout_callback(call):
    return call.data.startswith("workout_")


@bot.callback_query_handler(func=is_workout_callback)
def handle_workout_selection(call):
    workout_name = call.data.split("_")[1]
    bot.send_message(call.message.chat.id,
                     f"Вы выбрали тренировку: {workout_name}. Теперь введите время (например: 19/10/24 18:57):")
    user_data[call.message.chat.id] = {'selected_workout': workout_name, 'state': 'setting_time'}


def is_setting_time(message):
    return user_data.get(message.chat.id, {}).get('state') == 'setting_time' and not message.text.startswith('/')


@bot.message_handler(func=is_setting_time)
def set_workout_time(request):
    try:
        workout_name = user_data[request.chat.id]['selected_workout']
        workout_datetime = datetime.strptime(request.text, '%d/%m/%y %H:%M')
        with open('workouts.json', 'r+') as json_file:
            data = json.load(json_file)
            if str(request.chat.id) not in data:
                data[str(request.chat.id)] = []
            data[str(request.chat.id)].append({
                'name': workout_name,
                'time': request.text
            })
            json_file.seek(0)
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        bot.send_message(request.chat.id, f"Тренировка '{workout_name}' в {request.text} добавлена!")
        notify_time = workout_datetime - timedelta(hours=1)
        if datetime.now() < notify_time:
            time.sleep((notify_time - datetime.now()).total_seconds())
            bot.send_message(request.chat.id, f"Напоминание: у вас скоро тренировка "
                                              f"'{workout_name}' в {workout_datetime.time().strftime('%H:%M')}!")
        elif workout_datetime > datetime.now() > notify_time:
            time.sleep((workout_datetime - datetime.now()).total_seconds())
            bot.send_message(request.chat.id, f"Напоминание: пора приступать к тренировке")
        user_data.pop(request.chat.id, None)
    except ValueError:
        bot.send_message(request.chat.id, "Неверный формат даты. Пожалуйста, введите дату и время в формате 'дд/мм/гг "
                                          "чч:мм'.")


@bot.message_handler(['delete_workout'])
def delete_workout(message):
    with open('workouts.json', 'r+') as json_file:
        data = json.load(json_file)
    if str(message.chat.id) not in data or len(data[str(message.chat.id)]) == 0:
        bot.send_message(message.chat.id, "У вас нет запланированных тренировок.")
    else:
        workouts = data[str(message.chat.id)]
        keyboard = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for workout in workouts:
            keyboard.add(workout['name'])
        bot.send_message(message.chat.id, "Выберите тренировку для удаления:", reply_markup=keyboard)
        user_deleting_workout[message.chat.id] = True


def is_remove(message):
    return not message.text.startswith('/') and user_deleting_workout


@bot.message_handler(content_types=['text'], func=is_remove)
def remove_workout(request):
    if request.chat.id in user_deleting_workout:
        workout_name = request.text
        with open('workouts.json', 'r+') as json_file:
            data = json.load(json_file)
        if str(request.chat.id) in data:
            user_workouts = data[str(request.chat.id)]
            updated_workouts = []
            workout_found = False
            for workout in user_workouts:
                if workout['name'] != workout_name:
                    updated_workouts.append(workout)
                else:
                    workout_found = True
            if workout_found:
                bot.send_message(request.chat.id, f"Тренировка '{workout_name}' удалена.")
            else:
                bot.send_message(request.chat.id, "Тренировка не найдена.")
            data[str(request.chat.id)] = updated_workouts
            with open('workouts.json', 'w') as jsonFile:
                json.dump(data, jsonFile, indent=4, ensure_ascii=False)
        del user_deleting_workout[request.chat.id]
    else:
        bot.send_message(request.chat.id, "Пожалуйста, используйте команду '/delete_workout' для удаления тренировки.")


@bot.message_handler(['write_journal'])
def write_journal(message):
    bot.send_message(message.chat.id,
                     "Опишите своё состояние и данные о весе после тренировки (например: 'Чувствую себя хорошо, "
                     "вес 60 кг').")

    @bot.message_handler(content_types=['text'])
    def receive_journal(request):
        date = datetime.today().strftime('%d.%m.%y %H:%M')
        with open('journal.json', 'r+') as json_file:
            journal_data = json.load(json_file)
            if str(request.chat.id) not in journal_data:
                journal_data[str(request.chat.id)] = []
            journal_data[str(request.chat.id)].append({
                'date': date,
                'entry': request.text
            })
            json_file.seek(0)
            json.dump(journal_data, json_file, indent=4, ensure_ascii=False)
            json_file.truncate()
        bot.send_message(request.chat.id, "Запись добавлена в дневник.")


@bot.message_handler(['read_journal'])
def read_journal(message):
    with open('journal.json', 'r') as json_file:
        journal_data = json.load(json_file)
    if str(message.chat.id) not in journal_data or len(journal_data[str(message.chat.id)]) == 0:
        bot.send_message(message.chat.id, "У вас нет записей в дневнике.")
    else:
        entries = journal_data[str(message.chat.id)]
        response = "Ваши записи в дневнике:\n"
        for i in entries:
            response += f"{i['date']}: {i['entry']}\n"
        bot.send_message(message.chat.id, response)


bot.polling()
