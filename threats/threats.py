import multiprocessing
import re
import time
import json
import random
from collections import Counter
from functools import reduce
from typing import List, Dict, Tuple, Iterator

# --- 1. CONFIG & DATA SIMULATION (Имитация данных) ---

STOP_WORDS = frozenset({'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот'})

# Имитация "сырых" данных для генерации
MOCK_TOPICS = ["политика", "котики", "криптовалюта", "погода", "AI", "Python"]
MOCK_HASHTAGS = ["#news", "#fun", "#btc", "#winter", "#gpt", "#code", "#fail"]
MOCK_VERBS = ["любит", "ненавидит", "обсуждает", "игнорирует", "покупает", "продает"]

def simulate_fetch_source(source_id: int, count: int = 10000) -> Iterator[str]:
    """
    Генератор, имитирующий получение данных из источника (ленивая загрузка).
    В реальности здесь был бы API call с пагинацией.
    """
    print(f"[Source-{source_id}] Начало сбора данных...")
    # Симулируем задержку сети
    time.sleep(random.uniform(0.1, 0.5))
    
    # Симуляция ошибки (Отказоустойчивость: 1 источник из 10 может упасть)
    if source_id == 100: # Тест на ошибку
        raise ConnectionError("Connection reset by peer")

    for _ in range(count):
        topic = random.choice(MOCK_TOPICS)
        hashtag = random.choice(MOCK_HASHTAGS)
        verb = random.choice(MOCK_VERBS)
        # Генерируем "мусорное" сообщение
        yield f"Пользователь {random.randint(1, 1000)} {verb} тему {topic}! Очень интересно... {hashtag} http://spam.link"
        
    
    print(f"[Source-{source_id}] Сбор завершен.")

# --- 2. PURE FUNCTIONS (Чистые функции для обработки) ---

def clean_text(text: str) -> str:
    """Удаляет ссылки, спецсимволы и приводит к нижнему регистру."""
    text = text.lower()
    text = re.sub(r'http\S+', '', text) # Удалить ссылки
    text = re.sub(r'[^\w\s#]', '', text) # Удалить пунктуацию, кроме #
    return text

def tokenize(text: str) -> List[str]:
    """Разбивает текст на токены."""
    return text.split()

def filter_stopwords(tokens: List[str]) -> List[str]:
    """Удаляет стоп-слова. Использует frozenset для O(1) поиска."""
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 2]

def analyze_tokens(tokens: List[str]) -> Dict[str, Counter]:
    """
    Анализирует список токенов. Возвращает структуру с частотами.
    Разделяет обычные слова и хэштеги.
    """
    words = []
    hashtags = []
    
    for t in tokens:
        if t.startswith('#'):
            hashtags.append(t)
        else:
            words.append(t)
            
    return {
        "words": Counter(words),
        "hashtags": Counter(hashtags)
    }

# --- 3. MAPPER (Обработчик одного чанка данных) ---

def process_source_data(source_id: int) -> Dict[str, Counter]:
    """
    Функция-воркер. Выполняет полный цикл ETL для одного источника.
    Обеспечивает изоляцию ошибок (Try-Except).
    """
    local_result = {
        "words": Counter(),
        "hashtags": Counter()
    }
    
    try:
        # 1. Fetch (лениво получаем данные)
        # В реальной задаче здесь fetch_limit был бы миллион
        data_stream = simulate_fetch_source(source_id, count=1000000) 
        
        # 2. Processing Pipeline (Functional style composition)
        for raw_msg in data_stream:
            # Композиция функций: raw -> clean -> tokenize -> filter -> analyze
            cleaned = clean_text(raw_msg)
            tokens = tokenize(cleaned)
            filtered = filter_stopwords(tokens)
            analysis = analyze_tokens(filtered)
            
            # Локальная агрегация (чтобы не передавать гигабайты текста обратно в main процесс)
            local_result["words"].update(analysis["words"])
            local_result["hashtags"].update(analysis["hashtags"])
            
    except Exception as e:
        # Обеспечение надежности: логируем, но не роняем весь процесс
        print(f"!!! ОШИБКА в источнике {source_id}: {e}")
        return None # Возвращаем сигнал об ошибке, но программа работает дальше

    return local_result

# --- 4. REDUCER (Свертка результатов) ---

def merge_results(acc: Dict, new_data: Dict) -> Dict:
    """
    Функция свертки (Reduce). Объединяет результаты от разных процессов.
    """
    if new_data is None: # Пропускаем результаты упавших источников
        return acc
        
    acc["words"].update(new_data["words"])
    acc["hashtags"].update(new_data["hashtags"])
    return acc

# --- 5. MAIN CONTROLLER ---

def main():
    start_time = time.time()
    
    # 16 источников данных
    sources = list(range(1, 17))
    
    # Для демонстрации отказоустойчивости сделаем 5-й источник "битым" (см. simulate_fetch_source)
    
    print(f"Запуск распределенной обработки {len(sources)} источников...")
    
    # Инициализация пула процессов
    # Используем количество ядер CPU для максимальной эффективности
    cpu_count = multiprocessing.cpu_count()
    print(f"Используется ядер процессора: {cpu_count}")
    
    with multiprocessing.Pool(processes=cpu_count) as pool:
        # Параллельный запуск process_source_data для каждого источника
        # imap_unordered эффективнее для памяти и позволяет начать обработку результатов по мере поступления
        mapped_results = pool.map(process_source_data, sources)
    
    print("Сбор данных и первичная обработка завершены. Начинаем Reducer...")
    
    # Свертка всех локальных Counter'ов в один глобальный
    initial_state = {"words": Counter(), "hashtags": Counter()}
    final_result = reduce(merge_results, mapped_results, initial_state)
    
    # SORTING & REPORTING
    top_words = final_result["words"].most_common(10)
    top_hashtags = final_result["hashtags"].most_common(10)
    
    end_time = time.time()
    
    # SAVE RESULT
    output = {
        "meta": {
            "execution_time": round(end_time - start_time, 2),
            "sources_processed": len(sources)
        },
        "top_trends": top_hashtags,
        "top_keywords": top_words
    }
    
    with open("analysis_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
        
    print(f"\nГотово! Время выполнения: {output['meta']['execution_time']} сек.")
    print("Топ Тренды:", top_hashtags)
    print(top_words)

if __name__ == "__main__":
    main()