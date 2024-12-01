import logging
import requests
def split_text(text, max_length=2000):
    """Разделяет текст на части, если он превышает max_length."""
    if len(text) <= max_length:
        return [text]
    
    midpoint = len(text) // 2
    part1 = text[:midpoint]
    part2 = text[midpoint:]
    
    return [part1.strip(), part2.strip()]

def generate_prompt(rules, folder_context):
    """Генерация промпта для анализа папки."""
    return f"""
    Проанализируй код в папке на соответствие архитектурным стандартам и рекомендациям.

    Проверь:
    1. Взаимодействие между файлами и модулями на предмет логической связности и зависимостей.
    2. Соответствие общей архитектурной логике, например, правильная структура импорта и использования библиотек.
    3. Целостность архитектуры: нет ли избыточных или ненужных зависимостей.
    4. Соответствие структуре проекта (разделение на слои, конфиги, бизнес-логику и т.д.).
    Отвечай НА РУССКОМ ЯЗЫКЕ и не очень много слов чтобы было, и отражены основные моменты.
    
    Правила:
    {rules}

    Контекст папки:
    {folder_context}
    """

def call_llm_model(prompt):
    """Отправка запроса к языковой модели с обработкой ошибок и логированием."""
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
                "content": prompt
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=data_template)
        response.raise_for_status()

        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            logging.error("Ответ от API не содержит нужных данных.")
            return "Ответ от модели пустой или неправильно сформирован."
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
        return "Ошибка обработки запроса."

def call_llm_model_with_split(prompt):
    """Рекурсивная отправка запроса к модели с разбиением данных на части при ошибке."""
    try:
        return call_llm_model(prompt)
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
        if len(prompt) > 1000: 
            parts = split_text(prompt, max_length=len(prompt)//4)
            responses = []
            for part in parts:
                response = call_llm_model(part)
                responses.append(response)
            return "\n".join(responses)
        else:
            return "Ошибка обработки запроса: слишком большой или неподходящий запрос."

def process_folder(folder_context, rules_parts):
    """Обработка контекста папки с разбиением при необходимости."""
    folder_responses = []
    for rules in rules_parts:
        prompt = generate_prompt(rules, folder_context)
        response = call_llm_model_with_split(prompt)
        folder_responses.append(response)
    return "\n".join(folder_responses)

def get_all_folders(repo_root):
    """Получаем список всех папок, отсортированных по глубине (сначала вложенные)."""
    folder_list = []
    for root, _, _ in os.walk(repo_root):
        if "github" not in root and "bin" not in root:
            folder_list.append(root)
    folder_list.sort(key=lambda x: x.count(os.sep), reverse=True)
    return folder_list

def process_repository_analysis(repo_root):
    """Анализ репозитория с правилами из PDF, обрабатывая папки снизу вверх."""
    rules_text = open('python_rules_of.txt', 'r', encoding='utf-8').read()
    rules_parts = split_text(rules_text)
    
    folder_list = get_all_folders(repo_root)
    
    responses = []
    for folder_path in folder_list:
        folder_context = ""
        files = [f for f in os.listdir(folder_path) if f.endswith(".py") and os.path.isfile(os.path.join(folder_path, f))]
        
        for file in files:
            with open(os.path.join(folder_path, file), 'r', encoding='utf-8') as f:
                folder_context += f"\n# {file}\n" + f.read()
        
        if folder_context: 
            logging.info(f"Обработка папки: {folder_path}")
            folder_responses = []
            for rules in rules_parts:
                prompt = generate_prompt(rules, folder_context)
                response = call_llm_model_with_split(prompt)
                folder_responses.append(response)
            
            combined_response = "\n".join(folder_responses)
            responses.append((folder_path, combined_response))
    
    return responses


def get_results(responses):
    """Вывод результатов анализа в удобном формате."""
    all_results = ""  
    for folder, response in responses:
        all_results += f"\nРезультаты анализа папки '{folder}':\n"
        all_results += response
        all_results += "\n" 
    
    return all_results  

def summarize(text):
    """Отправка запроса к языковой модели с обработкой ошибок и логированием."""
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
                "content": "Сделай суммаризацию всего входящего текста и верни ответ на русском языке. Каждую папку выделяй каким нибудь спец. символом чтобы было удобнее читать"
            },
            {
                "role":"user",
                "content" : text
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=data_template)
        response.raise_for_status()

        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            logging.error("Ответ от API не содержит нужных данных.")
            return "Ответ от модели пустой или неправильно сформирован."
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса: {e}")
        return "Ошибка обработки запроса."
    
def process(repo_root, rules_path):
#pdf_path = "/home/maksim-litvninov/Documents/evraz/Руководство Python.pdf"
    repo_root = "/home/maksim-litvninov/Downloads/evraz_zip/python/backend-master/backend-master"

    responses = process_repository_analysis( repo_root)
    result = get_results(responses)

    summarization = summarize(result)
    return summarization
#    print (summarization)