import telebot
from PIL import Image
import cv2
import numpy as np
from ultralytics import YOLO
import config
import io
import os
import tempfile
from database import init_db, add_entry, get_daily_report, get_weekly_report, set_user_norms
from logic import find_product, calculate_nutrition, format_daily_report, format_weekly_report
from recognition import recognize
import database

import os
if not os.path.exists('nutrition.db'):
    print("⚠️ Database not found, creating new one...")
    init_db()
else:
    print("✅ Database found")
    
init_db()
bot = telebot.TeleBot(config.API_TOKEN)
CUSTOM_MODEL_PATH = "yolo26n.pt"

model = YOLO("yolo26n.pt")

FOOD_NUTRITION = {
    "samosa": {"calories": 262, "protein": 4.5, "fat": 17, "carbs": 24},
    "dosa": {"calories": 168, "protein": 3.9, "fat": 6, "carbs": 26},
    "banana": {"calories": 105, "protein": 1.3, "fat": 0.4, "carbs": 27},
    "pizza": {"calories": 285, "protein": 12, "fat": 10, "carbs": 36},
}

# Keyboard setup from main.py
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

hide_keyboard = ReplyKeyboardRemove()
cancel_button = 'Отмена'

def gen_markup(rows):
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row_width = 1
    for row in rows:
        markup.add(KeyboardButton(row))
    markup.add(KeyboardButton(cancel_button))
    return markup

def main_markup():
    return gen_markup(['Добавить запись', 'Отчет за день', 'Отчет за неделю', 'Установить норму'])

def send_menu(message, text='Выбери действие:'):
    bot.send_message(message.chat.id, text, reply_markup=main_markup())

# Command handlers from main.py
@bot.message_handler(commands=['start'])
def send_welcome(message):
    send_menu(message, 'Привет! Я помогу отслеживать калории.')


# @bot.message_handler(commands=['check'])
# def check_database(message):
#     """Simple command to check what's in the database today"""
#     from database import get_daily_report
#     entries, totals = get_daily_report(message.chat.id)
    
#     if entries:
#         response = " **Today's entries:**\n\n"
#         for entry in entries:
#             name, grams, cal, prot, fat, carbs = entry
#             response += f"• {name}: {grams}g = {cal} kcal\n"
        
#         cal, prot, fat, carbs = totals
#         response += f"\n**Total:** {cal} kcal |  {prot}g |  {fat}g |  {carbs}g"
#         bot.reply_to(message, response, parse_mode='Markdown')
#     else:
#         bot.reply_to(message, " No entries in database for today.")
        
@bot.message_handler(func=lambda m: m.text == 'Добавить запись')
def add_entry_menu(message): 
    bot.send_message(message.chat.id, 'Как добавить продукт?', reply_markup=gen_markup(['Вручную', 'По фото']))
    bot.register_next_step_handler(message, step_choose_method)

def step_choose_method(message):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    if message.text == 'По фото':
        bot.send_message(message.chat.id, 'Отправь фото продукта:', reply_markup=gen_markup([]))
        bot.register_next_step_handler(message, step_photo)
    else:
        bot.send_message(message.chat.id, 'Введи название продукта (apple, banana, chicken, rice...):', reply_markup=gen_markup([]))
        bot.register_next_step_handler(message, step_product_name)

def step_photo(message):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    if not message.photo:
        bot.send_message(message.chat.id, 'Нужно именно фото. Попробуй ещё раз:')
        bot.register_next_step_handler(message, step_photo)
        return
    bot.send_message(message.chat.id, 'Анализирую...')
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(downloaded)
        tmp_path = tmp.name
    name = recognize(tmp_path)
    os.remove(tmp_path)
    if not name:
        bot.send_message(message.chat.id, 'Не смог распознать. Введи название вручную:')
        bot.register_next_step_handler(message, step_product_name)
        return
    product = find_product(name)
    if not product:
        bot.send_message(message.chat.id, 'Не смог распознать. Введи название вручную:')
        bot.register_next_step_handler(message, step_product_name)
        return
    bot.send_message(message.chat.id, f'Нашёл: {product[1]}\n\nСколько граммов?')
    bot.register_next_step_handler(message, step_grams, product=product)

def step_product_name(message):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    product = find_product(message.text.lower())
    if not product:
        bot.send_message(message.chat.id, 'Не знаю такой продукт. Попробуй: apple, banana, chicken, rice, bread...')
        bot.register_next_step_handler(message, step_product_name)
        return
    bot.send_message(message.chat.id, f'Нашёл: {product[1]}\n\nСколько граммов?')
    bot.register_next_step_handler(message, step_grams, product=product)

def step_grams(message, product):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    try:
        grams = float(message.text)
        if grams <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, 'Введи число больше нуля, например: 150 или 150.5')
        bot.register_next_step_handler(message, step_grams, product=product)
        return
    n = calculate_nutrition(product, grams)
    add_entry(message.chat.id, n['product_id'], n['product_name'], grams,
              n['calories'], n['protein'], n['fat'], n['carbs'])
    send_menu(message,
              f"Записано!\n\n"
              f"{n['product_name']}: {grams}г\n"
              f"Калории: {n['calories']} kcal\n"
              f"Б: {n['protein']}г  Ж: {n['fat']}г  У: {n['carbs']}г")

@bot.message_handler(func=lambda m: m.text == 'Отчет за день')
def daily_report(message):
    entries, totals = get_daily_report(message.chat.id)
    if not entries:
        bot.send_message(message.chat.id, 'Нет записей за сегодня.', reply_markup=main_markup())
    else:
        bot.send_message(message.chat.id, format_daily_report(entries, totals, message.chat.id), reply_markup=main_markup())

@bot.message_handler(func=lambda m: m.text == 'Отчет за неделю')
def weekly_report(message):
    entries, totals = get_weekly_report(message.chat.id)
    if not entries:
        bot.send_message(message.chat.id, 'Нет записей за неделю.', reply_markup=main_markup())
    else:
        bot.send_message(message.chat.id, format_weekly_report(entries, totals, message.chat.id), reply_markup=main_markup())

@bot.message_handler(func=lambda m: m.text == 'Установить норму')
def set_norms_start(message):
    bot.send_message(message.chat.id, 'Сколько граммов белков в день?', reply_markup=gen_markup([]))
    bot.register_next_step_handler(message, step_protein)

def step_protein(message):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    try:
        v = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'Введи число (граммы белков):')
        bot.register_next_step_handler(message, step_protein)
        return
    bot.send_message(message.chat.id, 'Сколько граммов жиров?')
    bot.register_next_step_handler(message, step_fat, protein=v)

def step_fat(message, protein):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    try:
        v = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'Введи число (граммы жиров):')
        bot.register_next_step_handler(message, step_fat, protein=protein)
        return
    bot.send_message(message.chat.id, 'Сколько граммов углеводов?')
    bot.register_next_step_handler(message, step_carbs, protein=protein, fat=v)

def step_carbs(message, protein, fat):
    if message.text == cancel_button:
        send_menu(message, 'Отменено.')
        return
    try:
        v = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, 'Введи число (граммы углеводов):')
        bot.register_next_step_handler(message, step_carbs, protein=protein, fat=fat)
        return
    set_user_norms(message.chat.id, protein, fat, v)
    send_menu(message, f'Норма установлена:\nБелки: {protein}г  Жиры: {fat}г  Углеводы: {v}г')

@bot.message_handler(func=lambda m: True)
def other_messages(message):
    send_menu(message)

if __name__ == '__main__':
    print('Бот запущен')
bot.infinity_polling()