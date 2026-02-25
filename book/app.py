import json
from functools import reduce
from flask import Flask, render_template, request

app = Flask(__name__)

# ==========================================
# 1. ФУНКЦИОНАЛЬНЫЕ ПРИМИТИВЫ (FP Core)
# ==========================================

def pipe(*functions):
    """Композиция функций: pipe(f, g)(x) -> g(f(x))"""
    return reduce(lambda f, g: lambda x: g(f(x)), functions, lambda x: x)

def f_filter(predicate):
    return lambda iterable: filter(predicate, iterable)

def f_map(transform):
    return lambda iterable: map(transform, iterable)

def f_sort(key_func, reverse=False):
    return lambda iterable: sorted(iterable, key=key_func, reverse=reverse)

# ==========================================
# 2. ГЕНЕРАТОРЫ И РАБОТА С ДАННЫМИ
# ==========================================

def stream_books(filepath="books.json"):
    """Ленивый генератор данных (поток)"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            yield from data
    except FileNotFoundError:
        yield from []

def extract_metadata():
    """Извлечение уникальных жанров и авторов (Pure FP)"""
    def reducer(acc, book):
        acc["genres"].add(book.get("genre", "").strip())
        for author in book.get("author", []):
            acc["authors"].add(author.strip())
        return acc

    raw_data = reduce(reducer, stream_books(), {"genres": set(), "authors": set()})
    return sorted(list(raw_data["genres"])), sorted(list(raw_data["authors"]))

# ==========================================
# 3. ЧИСТЫЕ ФУНКЦИИ (АЛГОРИТМЫ)
# ==========================================

def evaluate_book(book: dict, pref_genres: list, pref_authors: list, pref_keywords: list) -> dict:
    """Расчет рейтинга. Возвращает новый словарь (Иммутабельность)."""
    genre_score = 3 if book.get("genre", "").lower() in pref_genres else 0
    book_authors = [a.lower() for a in book.get("author", [])]
    author_score = sum(2 for a in pref_authors if a.lower() in book_authors)
    desc = book.get("description", "").lower()
    keyword_score = sum(1 for kw in pref_keywords if kw in desc)
    
    total_score = genre_score + author_score + keyword_score
    return {**book, "score": total_score}

# ==========================================
# 4. ВЕБ-ИНТЕРФЕЙС И РОУТИНГ (FLASK)
# ==========================================

@app.route("/", methods=["GET", "POST"])
def index():
    genres, authors = extract_metadata()
    results = None
    
    # Состояние формы по умолчанию (чтобы не сбрасывалось)
    state = {
        "genres": [], "authors": [], "keywords": "", 
        "year": "", "strict_genre": False, "sort_by": "score"
    }

    if request.method == "POST":
        # 1. Читаем данные и сохраняем в state для отображения
        state["genres"] = request.form.getlist("genres")
        state["authors"] = request.form.getlist("authors")
        state["keywords"] = request.form.get("keywords", "")
        state["year"] = request.form.get("year", "")
        state["strict_genre"] = request.form.get("strict_genre") == "on"
        state["sort_by"] = request.form.get("sort_by", "score")

        # 2. Подготовка предикатов
        pref_genres = [g.lower().strip() for g in state["genres"]]
        pref_authors = [a.lower().strip() for a in state["authors"]]
        pref_keywords = [k.lower().strip() for k in state["keywords"].split(",") if k.strip()]
        
        try:
            min_year = int(state["year"]) if state["year"] else 0
        except ValueError:
            min_year = 0

        has_prefs = bool(pref_genres or pref_authors or pref_keywords)

        # Функция для сортировки (вторичная сортировка по алфавиту при равном счете)
        sort_key = {
            "score": lambda b: (b["score"], b.get("title", "")),
            "alphabet": lambda b: b.get("title", ""),
            "year": lambda b: (b.get("first_publish_year", 0), b.get("title", ""))
        }.get(state["sort_by"], lambda b: b["score"])
        
        is_reverse = state["sort_by"] in ["score", "year"]

        # 3. ПОСТРОЕНИЕ ПАЙПЛАЙНА
        recommendation_pipeline = pipe(
            # Фильтр по году
            f_filter(lambda b: b.get("first_publish_year", 0) >= min_year if min_year else True),
            # Оценка
            f_map(lambda b: evaluate_book(b, pref_genres, pref_authors, pref_keywords)),
            # ИСПРАВЛЕНИЕ: Отсекаем нулевой рейтинг ТОЛЬКО если пользователь ввел предпочтения
            f_filter(lambda b: b["score"] > 0 if has_prefs else True),
            # Фильтр ТЗ: Строгое совпадение жанра
            f_filter(lambda b: b["genre"].lower() in pref_genres if state["strict_genre"] and pref_genres else True),
            # Сортировка
            f_sort(sort_key, reverse=is_reverse)
        )

        results = list(recommendation_pipeline(stream_books()))

    return render_template("index.html", genres=genres, authors=authors, results=results, state=state)

if __name__ == "__main__":
    app.run(debug=True)