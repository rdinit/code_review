import logging
import os
import autopep8
from yapf.yapflib.yapf_api import FormatCode
import classify
import onefile_fix

def pep8_beautify(file_path):
    return autopep8.fix_file(file_path)

def yapf_beautify(file_path, conf_path=None):
    code = open(file_path, "r" , encoding="utf-8").read()
    return FormatCode(code, style_config=conf_path)


def unpack_zip(zip_path):
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall()

import requests
import logging
import json
import os
import process_zip

logging.basicConfig(level=logging.INFO)


def get_all_folders(repo_root):
    """Получаем список всех папок, отсортированных по глубине (сначала вложенные)."""
    folder_list = []
    for root, _, _ in os.walk(repo_root):
        if "github" not in root and "bin" not in root:
            folder_list.append(root)
    folder_list.sort(key=lambda x: x.count(os.sep), reverse=True)
    return folder_list


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

def one_file_process(file_path, lang='python'):
    if lang == 'python':
        return process_file(file_path, lang=lang)


def process_file(file_path, lang='python', yapf_path=None):
    if lang == 'python':
        res = yapf_beautify(file_path, yapf_path)
        print(res)
        res = res[0]
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(res)
    return classify.call_llm_model(classify.system_prompt, '/'.join(file_path.split('/')[-4:]), res)


def process_repo(repo_root, lang='python'):
    rules_text = open('python_rules_of.txt', 'r', encoding='utf-8').read()
    rules_parts =  split_text(rules_text, max_length=2000)

        
    folder_list = get_all_folders(repo_root)
    if lang == 'python':
        extension = '.py'
    responses = []
    file_errors = dict()
    for folder_path in folder_list:
        folder_context = ""
        files = [f for f in os.listdir(folder_path) if f.endswith(extension) and os.path.isfile(os.path.join(folder_path, f))]
        
        for file in files:
            fp = os.path.join(folder_path, file)
            category = process_file(fp, lang=lang)
            # TODO check category emplacement in structure
            with open(fp, 'r', encoding='utf-8') as f:
                fcontent = f.read()
            file_errors[file] = onefile_fix.process_code_review(fcontent)
            folder_context += f"\n# {file}\n" + fcontent
        
        if folder_context: 
            logging.info(f"Обработка папки: {folder_path}")
            folder_responses = []
            for rules in rules_parts:
                prompt = process_zip.generate_prompt(rules, folder_context)
                response = process_zip.call_llm_model_with_split(prompt)
                folder_responses.append(response)
            
            combined_response = "\n".join(folder_responses)
            responses.append((folder_path, combined_response))
    
    return responses, file_errors


responses, file_errors = process_repo('../sample_projects/hackernews-api-main')

import pickle
with open('responses.pkl', 'wb') as f:
    pickle.dump(responses, f)
with open('file_errors.pkl', 'wb') as f:
    pickle.dump(file_errors, f)