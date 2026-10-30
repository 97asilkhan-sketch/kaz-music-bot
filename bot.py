import json
import os
import telebot
from telebot import types

TOKEN = '9232349183:AAF55D9Sz0fPve8IcaFw8mWRVBwkgpFfsYk'
bot = telebot.TeleBot(TOKEN)

# Сіздің нақты Telegram ID-іңіз
ADMIN_ID = 652226072  

# Деректер сақталатын файл атауы (өшіп қалмау үшін)
DB_FILE = 'music_db.json'


# Деректерді файлдан оқу
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Бастапқы папкалар
    return {
        "хит 2025": [],
        "хит 2026": [],
        "қазақша": [],
        "зарубеж": [],
        "терме": []
    }


# Деректерді файлға сақтау
def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


music_db = load_db()


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('🎵 Музыкалар тізімі'))
    
    # Тек админге ғана музыка қосу батырмасы көрінеді
    if message.from_user.id == ADMIN_ID:
        markup.add(types.KeyboardButton('➕ Музыка қосу'))
        
    bot.send_message(
        message.chat.id,
        "Сәлем! Бұл музыка тыңдау және жүктеу боты. Төмендегі мәзірді пайдаланыңыз:",
        reply_markup=markup
    )


# 1. Админ музыка қосқысы келгенде бар папкалар түйме түрінде шығады
@bot.message_handler(func=lambda message: message.text == '➕ Музыка қосу' and message.from_user.id == ADMIN_ID)
def add_music_start(message):
    markup = types.InlineKeyboardMarkup()
    for folder in music_db.keys():
        markup.add(types.InlineKeyboardButton(text=f"📁 {folder}", callback_data=f"addtofolder_{folder}"))
    
    # Жаңа папка ашу батырмасы
    markup.add(types.InlineKeyboardButton(text="➕ Жаңа папка ашу", callback_data="create_new_folder"))

    bot.send_message(
        message.chat.id, 
        "Музыка қосқыңыз келетін папканы таңлаңыз немесе жаңасын ашыңыз:", 
        reply_markup=markup
    )


# Бар папканы таңдаған кезде
@bot.callback_query_handler(func=lambda call: call.data.startswith('addtofolder_'))
def callback_add_to_folder(call):
    folder = call.data.replace('addtofolder_', '', 1)
    msg = bot.send_message(
        call.message.chat.id, 
        f"Таңдалған папка: *{folder}*.\nЕнді `.mp3` форматындағы музыка файлын жіберіңіз:", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, lambda m: process_audio_file(m, folder))


# Жаңа папка ашу батырмасы басылғанда
@bot.callback_query_handler(func=lambda call: call.data == 'create_new_folder')
def callback_create_new_folder(call):
    msg = bot.send_message(
        call.message.chat.id,
        "📁 Жаңа папканың атын жазыңыз (мысалы: *Релакс* немесе *Хит 2027*):",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_new_folder_name)


def process_new_folder_name(message):
    folder = message.text.strip()
    if not folder:
        bot.send_message(message.chat.id, "Папка аты бос болмауы тиіс! Қайтадан көріңіз.")
        return

    if folder not in music_db:
        music_db[folder] = []
        save_db(music_db)

    msg = bot.send_message(
        message.chat.id, 
        f"Жаңа папка ашылды: *{folder}*.\nЕнді `.mp3` форматындағы музыка файлын жіберіңіз:", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, lambda m: process_audio_file(m, folder))


def process_audio_file(message, folder):
    if message.content_type != 'audio':
        bot.send_message(message.chat.id, "⚠️ Бұл аудио файл емес! Музыка қосу тоқтатылды.")
        return

    file_id = message.audio.file_id
    title = message.audio.title or message.audio.file_name or "Атауы жоқ трек"
    performer = message.audio.performer or "Белгісіз орындаушы"
    track_title = f"{performer} - {title}"

    if folder not in music_db:
        music_db[folder] = []

    music_db[folder].append({
        'file_id': file_id,
        'title': track_title
    })
    
    # Файлға сақтаймыз (өшіп қалмауы үшін)
    save_db(music_db)

    bot.send_message(
        message.chat.id, 
        f"✅ Музыка сәтті қосылды!\n📁 Папка: {folder}\n🎵 {track_title}"
    )


# 2. Музыкалар тізімін көрсету (Барлық папкалар)
@bot.message_handler(func=lambda message: message.text == '🎵 Музыкалар тізімі')
def show_folders(message):
    if not music_db:
        bot.send_message(message.chat.id, "Әзірге ешқандай папка жоқ.")
        return

    markup = types.InlineKeyboardMarkup()
    for folder, tracks in music_db.items():
        count = len(tracks)
        markup.add(types.InlineKeyboardButton(text=f"📁 {folder} ({count})", callback_data=f"showfolder_{folder}"))

    bot.send_message(message.chat.id, "Қолжетімді папкаларды таңлаңыз:", reply_markup=markup)


# 3. Папка таңдалғанда музыкаларды көрсету
@bot.callback_query_handler(func=lambda call: call.data.startswith('showfolder_'))
def callback_show_folder(call):
    folder = call.data.replace('showfolder_', '', 1)
    tracks = music_db.get(folder, [])

    if not tracks:
        bot.answer_callback_query(call.id, "Бұл папкада әзірге музыка жоқ!")
        return

    markup = types.InlineKeyboardMarkup()
    for idx, track in enumerate(tracks):
        btn_play = types.InlineKeyboardButton(text=f"🎵 {track['title']}", callback_data=f"play_{folder}_{idx}")
        markup.add(btn_play)

        if call.from_user.id == ADMIN_ID:
            btn_del = types.InlineKeyboardButton(text=f"❌ Өшіру: {track['title'][:20]}...", callback_data=f"del_{folder}_{idx}")
            markup.add(btn_del)

    markup.add(types.InlineKeyboardButton(text="⬅️ Артқа", callback_data="back_to_folders"))
    bot.edit_message_text(f"📁 {folder} папкасының музыкалары:", call.message.chat.id, call.message.message_id, reply_markup=markup)


# 4. Музыканы жүктеп алу (файл түрінде жіберу)
@bot.callback_query_handler(func=lambda call: call.data.startswith('play_'))
def callback_play(call):
    data_parts = call.data.split('_')
    idx = int(data_parts[-1])
    folder = "_".join(data_parts[1:-1])
    
    tracks = music_db.get(folder, [])
    if idx < len(tracks):
        track = tracks[idx]
        bot.send_document(
            call.message.chat.id, 
            track['file_id'], 
            caption=f"📁 {folder}\n📥 Жүктеп алу үшін файлды басыңыз!"
        )
    else:
        bot.answer_callback_query(call.id, "Музыка табылмады!")


# 5. Тек админ өшіре алатын функция
@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def callback_delete(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⚠️ Бұл әрекетті тек админ ғана жасай алады!", show_alert=True)
        return

    data_parts = call.data.split('_')
    idx = int(data_parts[-1])
    folder = "_".join(data_parts[1:-1])

    tracks = music_db.get(folder, [])
    if idx < len(tracks):
        deleted_track = tracks.pop(idx)
        save_db(music_db)  
        bot.answer_callback_query(call.id, f"✅ Өшірілді: {deleted_track['title']}")
        
        try:
            markup = types.InlineKeyboardMarkup()
            for i, track in enumerate(tracks):
                markup.add(types.InlineKeyboardButton(text=f"🎵 {track['title']}", callback_data=f"play_{folder}_{i}"))
                markup.add(types.InlineKeyboardButton(text=f"❌ Өшіру: {track['title'][:20]}...", callback_data=f"del_{folder}_{i}"))
            markup.add(types.InlineKeyboardButton(text=f"⬅️ Артқа", callback_data="back_to_folders"))
            bot.edit_message_text(f"📁 {folder} папкасының музыкалары:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception:
            pass
    else:
        bot.answer_callback_query(call.id, "Қателік орын алды!")


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_folders')
def callback_back_folders(call):
    if not music_db:
        bot.edit_message_text("Әзірге ешқандай папка жоқ.", call.message.chat.id, call.message.message_id)
        return
    markup = types.InlineKeyboardMarkup()
    for folder, tracks in music_db.items():
        count = len(tracks)
        markup.add(types.InlineKeyboardButton(text=f"📁 {folder} ({count})", callback_data=f"showfolder_{folder}"))
    bot.edit_message_text("Қолжетімді папкаларды таңлаңыз:", call.message.chat.id, call.message.message_id, reply_markup=markup)


if __name__ == '__main__':
    print("Бот жұмыс істеп тұр...")
    bot.infinity_polling()
