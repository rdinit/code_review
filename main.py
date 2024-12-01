import time
import flask
import telebot
import os
import process

API_TOKEN = os.environ['API_TOKEN']
WEBHOOK_URL_BASE = os.environ['WEBHOOK_URL_BASE']

WEBHOOK_URL_PATH = '/webhook'
bot = telebot.TeleBot(API_TOKEN)
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)

app = flask.Flask(__name__)

@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)

@app.route('/')
def index():
    return 'Hello, World!'


def create_report(report_path, contents):
    # Для создания файла репорта, можно править для ваших потребностей
    with open(report_path, "w") as file:
        file.write(contents)
    return report_path


# Функция для обработки файлов и создания репортов
def process_file(file) -> str:
    # Здесь должна быть логика обработки файла
    #print("Processing file:", file)
    text = file.decode('utf-8')
    file_errors = process.process_file(text)

    r = []
    for f in file_errors:
        if file_errors[f] is None:
            continue
        r.append('\n\n'+ f)
        t = ''
        for i in file_errors[f]:
            if i is None:
                continue
            t += i
        r.append(t)

    report = create_report("report.md", '\n'.join(r))
    return report


# Функция для обработки архивов
def process_archive(zip_file):
    with ZipFile(io.BytesIO(zip_file), 'r') as archive:
        archive.extractall('temp')
    arch_folder = list(sorted(os.listdir('.')))[-1]
    responses, file_errors = process.process_repo(arch_folder)

    r = []
    for f in file_errors:
        if file_errors[f] is None:
            continue
        r.append('\n\n'+ f)
        t = ''
        for i in file_errors[f]:
            if i is None:
                continue
            t += i
        r.append(t)
    r.append('\n')
    shutil.rmtree('temp')

    for i in responses:
        r.append(''.join(i))

    report = create_report("report.md", '\n'.join(r))
    return report


@bot.message_handler(content_types=['document'])
def handle_document(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    if message.document.file_name.endswith('.zip'):
        result_report = process_archive(downloaded_file)
        r_type = "архив"
    else:
        result_report = process_file(downloaded_file)
        r_type = "файл"

    bot.reply_to(message, f"Ваш {r_type} был обработан, результаты прикреплены к сообщению.")
    with open(result_report, "rb") as report_file:
        bot.send_document(chat_id=message.chat.id, document=report_file)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! Я бот для проверки проектов. Отправьте мне файл или архив для обработки.")


@bot.message_handler(func=lambda message: True)
def unknown_command(message):
    bot.reply_to(message, "Я не знаю, что делать с этим. Пожалуйста, отправьте мне файл или архив для обработки.")



app.run(host='0.0.0.0', port=5000)