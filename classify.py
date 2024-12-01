system_prompt = """
Проанализируй код и определи его категорию по следующим критериям:
- Тесты: наличие тестовых фреймворков (unittest, pytest), функции test_*, assert.
- Адаптеры: код взаимодействия с API, CLI, Kafka, логирование через logging или специальные клиенты.
- Архитектура базы данных: модели или миграции, различай декларативный (SQLAlchemy ORM) и императивный (SQL-запросы напрямую) подходы.
- Роутеры: маршруты, декораторы типа @app.route, @router.
- Data Science/ML: использование библиотек pandas, scikit-learn, TensorFlow, PyTorch.
- Композиты: сборка компонентов, инициализация зависимостей, внедрение паттернов DI.
- Бизнес логика: классы, методы, основная логика приложения.
- Конфиги: настройки, файлы с параметрами, .env, yaml.

Даже если в коде отсутствуют конкретные фразы или библиотеки, определяй категорию на основе общего смысла и логики реализации. Оцени структуру, назначение функций, названия переменных и комментарии, чтобы понять, к какой категории относится данный файл.

Особое внимание уделяй **названиям файлов и их путям** — они часто указывают на назначение файла (например, test_*.py, config.yaml, router.py). Название файла может иметь ключевое значение для определения категории.

ОТВЕТЬ всего **одним словом** — выбранной категорией.

Ввод пользователя будет представлен в следующем формате: 
"file_path" : <путь к файлу>, "file_content" : <содержание файла>
"""

import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def call_llm_model(system_prompt, file_path, file_content):
    """
    Функция делает запрос к API модели для классификации файла на основе его содержимого.
    Если длина контента превышает лимит токенов, контент делится на части и отправляется поэтапно,
    затем категории объединяются.
    """
    url = "http://84.201.152.196:8020/v1/completions"
    headers = {
        "Authorization": "2oMV0YId1hBESqT9Yb7LairbVADrgvJc",
        "Content-Type": "application/json"
    }
    data_template = {
        "model": "mistral-nemo-instruct-2407",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"file_path : {file_path}, file_content : {file_content}"
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=data_template).json()
        return response['choices'][0]['message']['content']
    
    except Exception as e:
        if isinstance(e, requests.exceptions.RequestException):
            error_message = e.response.json().get('error', {}).get('message', '')
            if "превышает допустимый лимит" in error_message:
                logging.warning(f"Превышен лимит токенов для файла: {file_path}. Разделение содержимого...")
                
                midpoint = len(file_content) // 2
                first_half = file_content[:midpoint]
                second_half = file_content[midpoint:]
                
                first_half_category = call_llm_model(system_prompt, file_path, first_half)
                second_half_category = call_llm_model(system_prompt, file_path, second_half)
                
                if first_half_category == second_half_category:
                    return first_half_category
        
                return f"{first_half_category}, {second_half_category}"
        
        logging.error(f"Ошибка при обработке файла {file_path}: {e}")
        return "Ошибка"

def classify_files_in_repo(repo_path):
    """
    Функция проходит по всем файлам в репозитории и классифицирует их
    на основе содержимого.
    """
    classification_result = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".py", ".json", ".cfg", ".yaml")): 
                file_path = os.path.join(root, file)
                logging.info(f"Обработка файла: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        category = call_llm_model(system_prompt, '/'.join(file_path.split('/')[-4:]), content)
                        classification_result[file_path] = category
                        logging.info(f"Файл обработан успешно: {file_path}")
                except Exception as e:
                    logging.error(f"Ошибка при обработке файла {file_path}: {e}")
                    
    return classification_result

if __name__ == "__main__":
    repo_path = "/home/maksim-litvninov/Downloads/evraz_zip/python/backend-master"
    results = classify_files_in_repo(repo_path)
    for file, category in results.items():
        print(f"{file}: {category}")
