import requests
import logging
import json

logging.basicConfig(level=logging.INFO)


def split_text(text, max_length=2500):
    """
    Разделяет текст на две части, если он превышает max_length.
    """
    if len(text) <= max_length:
        return [text]
    
    midpoint = len(text) // 2
    part1 = text[:midpoint]
    part2 = text[midpoint:]
    
    return [part1.strip(), part2.strip()]

def generate_prompt(rules, code):
    """
    Генерация промпта для проверки кода.
    """
    return f"""
    Проанализируй следующий код на соответствие приведённым стандартам и правилам.

    Сначала укажи:
    1. Какие стандарты или рекомендации были нарушены (с указанием конкретных пунктов из правил, если применимо).

    Затем предложи:
    1. Как исправить каждую из ошибок - в виде уже исправленного кода В ФОРМАТЕ ``` неправильный код до ```  ```исправленный код после```
    2. Общие рекомендации по улучшению кода, ТОЛЬКО если ошибок нет.

    Приведи ответы в структурированном формате с пояснениями.

    Правила:
    {rules}

    Код:
    {code}
    """

def call_llm_model(prompt, file_path=None, file_content=None):
    """
    Отправка запроса к языковой модели с обработкой ошибок и логированием.
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
        error_message = e.response.json().get('error', {}).get('message', '')
        if "превышает допустимый лимит" in error_message:
            logging.warning(f"Превышен лимит токенов для файла: {file_path}. Разделение содержимого...")

            midpoint = len(file_content) // 2
            first_half = file_content[:midpoint]
            second_half = file_content[midpoint:]
            
            first_half_content = call_llm_model(prompt, file_path, first_half)
            second_half_content = call_llm_model(prompt, file_path, second_half)

            return first_half_content + "\n\n" + second_half_content
        else:
        
            logging.error(f"Ошибка запроса: {e}")
            raise e

def process_code_review(code_to_check):
    """
    Процесс проверки кода с правилами из PDF.
    """
    pdf_text = open('python_rules_of.txt', 'r', encoding='utf-8').read()
    
    rules_image_text = """
    1. Использование стандартных инструментов и библиотек: популярные версии пакетов (Falcon, Gunicorn, Gevent, Alembic).
    2. Логирование: корректное использование logging.
    3. Аутентификация: проверка обработки JWT-токенов.
    4. Оптимизация производительности при работе с большими данными.
    """
  
    combined_rules = pdf_text + "\n" + rules_image_text
    rules_parts = split_text(combined_rules)

    responses = []
    for i, rules in enumerate(rules_parts):
        logging.info(f"Обработка части {i + 1}...")

        prompt = generate_prompt(rules, code_to_check)
        
        try:
            response = call_llm_model(prompt, file_content=code_to_check)
            responses.append(response)
            logging.info(f"Часть {i + 1} успешно обработана.")
        except Exception as e:
            logging.error(f"Ошибка при обработке части {i + 1}: {e}")
            responses.append(None)
    
    return responses

def display_results(responses):
    """
    Вывод результатов проверки в удобном формате.
    """
    combined_result = ""
    for i, response in enumerate(responses):
        if response:
            combined_result += f"\nРезультаты проверки для части {i + 1}:\n"
            combined_result += response + "\n"
        else:
            combined_result += f"\nРезультаты проверки для части {i + 1}: Ошибка обработки.\n"
    
   
    print(combined_result)

if __name__ == "__main__":
    pdf_path = "/home/maksim-litvninov/Documents/evraz/for-one-file.pdf"
    file_path = "/home/maksim-litvninov/Downloads/evraz_zip/python/backend-master/backend-master/freenit/decorators.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        code_to_check = f.read()

    responses = process_code_review(pdf_path, code_to_check)

    display_results(responses)