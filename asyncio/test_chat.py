import pytest
import pytest_asyncio
import asyncio
from server import ChatServer

# Порт для тестов, чтобы не конфликтовать с запущенным вручную сервером
TEST_PORT = 9999
HOST = '127.0.0.1'

# ИСПРАВЛЕНИЕ: Используем pytest_asyncio.fixture вместо pytest.fixture
@pytest_asyncio.fixture
async def server():
    """Фикстура: запускает сервер перед тестом и останавливает после."""
    chat_server = ChatServer(host=HOST, port=TEST_PORT)
    # Запускаем сервер в фоновой задаче
    server_task = asyncio.create_task(chat_server.run())
    
    # Даем серверу немного времени на старт
    await asyncio.sleep(0.1)
    
    yield chat_server
    
    # Остановка сервера (через отмену задачи, для тестов ок)
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

async def connect_client(username):
    """Помощник для создания клиента."""
    reader, writer = await asyncio.open_connection(HOST, TEST_PORT)
    
    # Читаем приветствие
    await reader.readline() # Welcome...
    
    # Шлем имя
    writer.write(f"{username}\n".encode())
    await writer.drain()
    
    return reader, writer

@pytest.mark.asyncio
async def test_connect_and_general_room(server):
    """
    Тест 1: Проверяем, что при подключении пользователь 
    автоматически попадает в комнату General.
    """
    reader, writer = await connect_client("Tester1")
    
    found_general = False
    for _ in range(5): 
        line = await reader.readline()
        decoded = line.decode().strip()
        if "[ROOM]General" in decoded:
            found_general = True
            break
            
    writer.close()
    await writer.wait_closed()
    
    assert found_general, "Клиент не был автоматически добавлен в General"

@pytest.mark.asyncio
async def test_message_broadcast(server):
    """
    Тест 2: Алиса пишет в General, Боб должен это увидеть.
    """
    r_alice, w_alice = await connect_client("Alice")
    r_bob, w_bob = await connect_client("Bob")
    
    await asyncio.sleep(0.1)
    
    # Алиса отправляет сообщение в General
    msg_text = "Hello Bob"
    w_alice.write(f"/send Group:General {msg_text}\n".encode())
    await w_alice.drain()
    
    # Боб читает поток
    received_msg = False
    try:
        for _ in range(10):
            line = await asyncio.wait_for(r_bob.readline(), timeout=1.0)
            decoded = line.decode().strip()
            # Ожидаемый формат: [ROOM]General Alice: Hello Bob
            if "Alice: Hello Bob" in decoded:
                received_msg = True
                break
    except asyncio.TimeoutError:
        pass
        
    w_alice.close()
    w_bob.close()
    
    assert received_msg, "Боб не получил сообщение от Алисы в General"

@pytest.mark.asyncio
async def test_create_group(server):
    """
    Тест 3: Создание новой группы.
    """
    r, w = await connect_client("Creator")
    
    group_name = "SecretBase"
    w.write(f"/create_group {group_name}\n".encode())
    await w.drain()
    
    success = False
    for _ in range(10):
        line = await r.readline()
        decoded = line.decode()
        if f"[ROOM]{group_name}" in decoded and "created group" in decoded:
            success = True
            break
            
    w.close()
    assert success, "Не удалось создать группу или не пришло подтверждение"