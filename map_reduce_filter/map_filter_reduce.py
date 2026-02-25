from functools import reduce

# Расширенный список данных для наглядности
students = [
    {"name": "Alice", "age": 20, "grades": [85, 90, 88, 92]},
    {"name": "Bob", "age": 22, "grades": [78, 89, 76, 85]},
    {"name": "Charlie", "age": 21, "grades": [92, 95, 88, 94]},
    {"name": "David", "age": 20, "grades": [90, 80, 85, 95]},
    {"name": "Eve", "age": 22, "grades": [70, 75, 80, 85]},
]

# --- Функции-помощники ---

def calculate_average(grades):
    """Вычисляет средний балл из списка оценок."""
    if not grades:
        return 0
    return sum(grades) / len(grades)

def add_average_grade(student):
    """Преобразует словарь студента, добавляя поле 'average_grade'."""
    # Используем неизменяемость: создаем новый словарь
    new_student = student.copy() 
    new_student["average_grade"] = calculate_average(student["grades"])
    return new_student

# --- Решение задач  ---

# 1. Преобразование данных: Вычислить средний балл для каждого студента
students_with_avg = list(map(add_average_grade, students))
print("--- 1. Средний балл для каждого студента ---")
# В ФП часто используется map для преобразования одного списка в другой
# (list() нужен, чтобы явно вызвать map и получить список)
for s in students_with_avg:
    print(f"{s['name']}: {s['average_grade']:.2f}")

# 2. Фильтрация данных: Отфильтровать студентов определенного возраста (например, 20 лет)
TARGET_AGE = 20
# Используем filter для отбора элементов по условию
filtered_students = list(filter(lambda s: s["age"] == TARGET_AGE, students_with_avg))
print(f"\n--- 2. Студенты возраста {TARGET_AGE} ---")
for s in filtered_students:
    print(f"{s['name']} (Возраст: {s['age']})")

# 3. Агрегация: Вычислить общий средний балл по всем студентам
# Используем генераторное выражение (внутри sum) для извлечения всех средних баллов
all_averages = [s["average_grade"] for s in students_with_avg]
overall_average = calculate_average(all_averages)

print(f"\n--- 3. Общий средний балл по всем студентам ---")
print(f"Общий средний балл: {overall_average:.2f}")

# 4. Агрегация: Найти студента (или студентов) с самым высоким средним баллом
# Находим максимальный средний балл
if students_with_avg:
    max_avg = max(s["average_grade"] for s in students_with_avg)
    
    # Используем filter для отбора всех студентов с этим баллом
    top_students = list(filter(lambda s: s["average_grade"] == max_avg, students_with_avg))
    
    print(f"\n--- 4. Студент(ы) с самым высоким средним баллом ({max_avg:.2f}) ---")
    for s in top_students:
        print(f"{s['name']}")
else:
    print("Список студентов пуст.")

# Расширенный список данных
users = [
    {"name": "Alice", "expenses": [100, 50, 75, 200]},
    {"name": "Bob", "expenses": [50, 75, 80, 100]},
    {"name": "Charlie", "expenses": [200, 300, 50, 150]},
    {"name": "David", "expenses": [100, 200, 300, 400]},
    {"name": "Andrew", "expenses": [10, 20, 30, 40]},
]

# --- Функции-критерии ---

def is_expensive_user(user):
    """Критерий фильтрации: пользователи, чье имя начинается с 'A'."""
    return user["name"].startswith('A')

# --- Решение задач в функциональном стиле ---

# 1. Отфильтровать пользователей по заданным критериям
filtered_users = list(filter(is_expensive_user, users))
print("\n--- 1. Отфильтрованные пользователи (Имя начинается с 'A') ---")
for u in filtered_users:
    print(u["name"])

# 2. Для каждого пользователя рассчитать общую сумму его расходов
# Используем map для преобразования каждого пользователя в его общую сумму расходов
# Генераторное выражение (или map) внутри sum() преобразует список расходов в их сумму
individual_totals = list(map(lambda u: sum(u["expenses"]), filtered_users))

print("\n--- 2. Суммы расходов для отфильтрованных пользователей ---")
for user, total in zip(filtered_users, individual_totals):
    print(f"{user['name']}: {total}")

# 3. Получить общую сумму расходов всех отфильтрованных пользователей
# Используем sum() для агрегации всех индивидуальных сумм
grand_total_expenses = sum(individual_totals)

print("\n--- 3. Общая сумма расходов всех отфильтрованных пользователей ---")
print(f"Общая сумма: {grand_total_expenses}")

# Расширенный список данных
orders = [
    {"order_id": 1, "customer_id": 101, "amount": 150.0},
    {"order_id": 2, "customer_id": 102, "amount": 200.0},
    {"order_id": 3, "customer_id": 101, "amount": 75.0},
    {"order_id": 4, "customer_id": 103, "amount": 100.0},
    {"order_id": 5, "customer_id": 101, "amount": 50.0},
    {"order_id": 6, "customer_id": 102, "amount": 300.0},
    {"order_id": 7, "customer_id": 103, "amount": 125.0},
]

# Заданный идентификатор клиента
TARGET_CUSTOMER_ID = 101


# 1. Фильтрация заказов: Отфильтровать заказы только для определенного клиента
# Используем filter с лямбда-функцией
customer_orders = list(filter(lambda o: o["customer_id"] == TARGET_CUSTOMER_ID, orders))

print(f"\n--- 1. Заказы клиента ID {TARGET_CUSTOMER_ID} ({len(customer_orders)} шт.) ---")
for order in customer_orders:
    print(f"Заказ ID {order['order_id']}: {order['amount']}")

# 2. Подсчет суммы заказов: Подсчитать общую сумму всех заказов для данного клиента
# Используем генераторное выражение для извлечения сумм и sum() для агрегации
total_amount = sum(order["amount"] for order in customer_orders)

print(f"\n--- 2. Общая сумма заказов ---")
print(f"Общая сумма: {total_amount:.2f}")

# 3. Подсчет средней стоимости заказов: Найти среднюю стоимость заказов для данного клиента
average_amount = 0
if customer_orders:
    # Среднее = Общая сумма / Количество заказов
    average_amount = total_amount / len(customer_orders)

print(f"\n--- 3. Средняя стоимость заказов ---")
print(f"Средняя стоимость: {average_amount:.2f}")