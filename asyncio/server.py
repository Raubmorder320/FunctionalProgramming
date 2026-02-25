import asyncio
import logging

# Настройка логирования (для солидности)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatRoom:
    """
    Комната чата.
    Содержит очередь сообщений (asyncio.Queue) и список участников.
    """
    def __init__(self, name, typ, allowed_users=None):
        self.name = name
        self.type = typ  # "Group" или "Personal"
        self.clients = set()  # Набор writer'ов (потоков вывода) подключенных клиентов
        self.allowed_users = allowed_users or set()
        self.history = []     # История сообщений
        self.msg_queue = asyncio.Queue()  # <-- ТРЕБОВАНИЕ ТЗ: Очередь событий
        self.lock = asyncio.Lock()
        
        # Запускаем "вечный" процесс обработки очереди для этой комнаты
        self._processor_task = asyncio.create_task(self.process_queue())

    async def process_queue(self):
        """
        Consumer: Бесконечно читает сообщения из очереди и рассылает их.
        """
        while True:
            msg = await self.msg_queue.get() # Ждем сообщение (await)
            await self._broadcast(msg)
            self.msg_queue.task_done()

    async def _broadcast(self, message):
        """
        Рассылка сообщения всем подключенным клиентам.
        """
        self.history.append(message)
        # Используем копию множества, чтобы избежать ошибки изменения размера во время итерации
        # и lock для потокобезопасности (в рамках asyncio это concurrency safety)
        async with self.lock:
            for client in list(self.clients):
                try:
                    client.write(f"[ROOM]{self.name} {message}\n".encode())
                    await client.drain()
                except Exception:
                    # Если клиент отвалился, удаляем его
                    self.clients.discard(client)

class ChatServer:
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.groups = {}        # Имя группы -> ChatRoom
        self.personals = {}     # Имя привата -> ChatRoom
        
        # Маппинги для управления пользователями
        self.user_rooms = {}    # writer -> set(имен комнат)
        self.user_names = {}    # writer -> имя пользователя
        self.user_writers = {}  # имя пользователя -> writer
        
        self.global_lock = asyncio.Lock()
        # general_room = ChatRoom("General", "Group")
        # self.groups["General"] = general_room
    async def handle_client(self, reader, writer):
        """
        Обработчик подключения одного клиента.
        """
        addr = writer.get_extra_info('peername')
        logging.info(f"New connection from {addr}")

        try:
            # 1. Рукопожатие / Регистрация
            writer.write(b"Welcome! Enter your username:\n")
            await writer.drain()
            
            # Ждем ввода имени
            data = await reader.readline()
            user_name = data.decode().strip()
            
            if not user_name:
                return # Пустое имя - до свидания

            # Сохраняем данные пользователя
            self.user_names[writer] = user_name
            self.user_writers[user_name] = writer
            self.user_rooms[writer] = set()
            
            logging.info(f"User '{user_name}' logged in.")

            # Клиент сразу попадает в общий чат
            if "General" in self.groups:
                await self.join_room(writer, self.groups["General"])
                await self.groups["General"].msg_queue.put(f"System: {user_name} joined server.")

            # 2. Основной цикл обработки команд
            while True:
                data = await reader.readline()
                if not data: 
                    break # Клиент отключился
                
                msg = data.decode().strip()
                await self.process_command(writer, user_name, msg)

        except Exception as e:
            logging.error(f"Error handling client {addr}: {e}")
        finally:
            await self.disconnect_user(writer)

    async def process_command(self, writer, user_name, msg):
        """
        Разбор команд клиента.
        """
        # --- ПОЛУЧЕНИЕ СПИСКОВ ---
        if msg.startswith("/users"):
            users_list = ",".join(u for u in self.user_writers.keys() if u != user_name)
            writer.write(f"USERS:{users_list}\n".encode())
            await writer.drain()

        elif msg.startswith("/rooms"):
            # Группы + Личные чаты, где есть этот юзер
            p_rooms = [name for name, r in self.personals.items() if user_name in r.allowed_users]
            g_rooms = [f"Group:{name}" for name in self.groups.keys()]
            all_rooms = ",".join(g_rooms + p_rooms)
            writer.write(f"ROOMS:{all_rooms}\n".encode())
            await writer.drain()

        elif msg.startswith("/myrooms"):
            my_r = ",".join(self.user_rooms.get(writer, []))
            writer.write(f"MYROOMS:{my_r}\n".encode())
            await writer.drain()

        # --- СОЗДАНИЕ КОМНАТ ---
        elif msg.startswith("/create_group "):
            group_name = msg.split(" ", 1)[1]
            async with self.global_lock:
                if group_name not in self.groups:
                    room = ChatRoom(group_name, "Group")
                    self.groups[group_name] = room
                    # Автор сразу входит
                    await self.join_room(writer, room)
                    # Событие через очередь!
                    await room.msg_queue.put(f"System: {user_name} created group.")
                else:
                    writer.write(b"Error: Group exists\n"); await writer.drain()

        elif msg.startswith("/create_personal "):
            _, target_user = msg.split(" ", 1)
            if target_user not in self.user_writers:
                return # Нет такого юзера
            
            u1, u2 = sorted([user_name, target_user])
            room_name = f"Personal:{u1}:{u2}"
            
            async with self.global_lock:
                if room_name not in self.personals:
                    room = ChatRoom(room_name, "Personal", allowed_users={u1, u2})
                    self.personals[room_name] = room
                    
                    # Принудительно добавляем обоих (если они онлайн)
                    for u in [u1, u2]:
                        if u in self.user_writers:
                            w = self.user_writers[u]
                            await self.join_room(w, room)
                    
                    await room.msg_queue.put(f"System: Personal chat started.")

        # --- ВХОД И ОТПРАВКА ---
        elif msg.startswith("/join "):
            raw_name = msg.split(" ", 1)[1]
            room = self.find_room(raw_name)
            if room:
                if room.type == "Personal" and user_name not in room.allowed_users:
                    writer.write(b"Access Denied\n"); await writer.drain()
                else:
                    await self.join_room(writer, room)
                    await room.msg_queue.put(f"System: {user_name} joined.")

        elif msg.startswith("/send "):
            parts = msg.split(" ", 2) # /send RoomName Message Text
            if len(parts) == 3:
                r_name, text = parts[1], parts[2]
                room = self.find_room(r_name)
                # Проверка: клиент должен быть в комнате, чтобы писать
                if room and writer in room.clients:
                    # <-- ВАЖНО: Кладем в очередь, а не отправляем сразу
                    await room.msg_queue.put(f"{user_name}: {text}")

        elif msg.startswith("/exit"):
            await self.disconnect_user(writer)

    async def join_room(self, writer, room):
        """Вспомогательная функция входа + отправка истории."""
        async with room.lock:
            room.clients.add(writer)
        
        r_key = room.name if room.type == "Personal" else f"Group:{room.name}"
        self.user_rooms[writer].add(r_key)
        
        # Отправляем историю (сразу, без очереди, так как это только для одного)
        for old_msg in room.history:
            writer.write(f"[ROOM]{room.name} {old_msg}\n".encode())
        await writer.drain()

    def find_room(self, raw_name):
        if raw_name.startswith("Group:"):
            return self.groups.get(raw_name[6:])
        elif raw_name.startswith("Personal:"):
            return self.personals.get(raw_name)
        return None

    async def disconnect_user(self, writer):
        name = self.user_names.get(writer)
        if not name: return
        
        # Удаляем из всех комнат
        joined = self.user_rooms.get(writer, set()).copy()
        for r_name in joined:
            room = self.find_room(r_name)
            if room:
                async with room.lock:
                    room.clients.discard(writer)
        
        # Чистим списки
        self.user_names.pop(writer, None)
        self.user_writers.pop(name, None)
        self.user_rooms.pop(writer, None)
        
        try:
            writer.close()
            await writer.wait_closed()
        except: pass
        logging.info(f"User {name} disconnected.")

    async def run(self):
        # 1. Вот теперь мы внутри async-метода. Event Loop запущен!
        # Инициализируем асинхронные объекты здесь:
        self.global_lock = asyncio.Lock()
        
        general_room = ChatRoom("General", "Group")
        self.groups["General"] = general_room
        logging.info("Room 'General' created.")

        # 2. Запускаем сам сервер
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logging.info(f"Server started on {self.host}:{self.port}")
        asyncio.create_task(self.server_console())
        
        async with server:
            await server.serve_forever()
    async def server_console(self):
        """
        Фоновая задача для ввода команд администратора прямо в терминале сервера.
        Используем run_in_executor, чтобы функция input() не блокировала Event Loop.
        """
        loop = asyncio.get_running_loop()
        while True:
            # Читаем ввод с клавиатуры в отдельном потоке (без блокировки сети)
            msg = await loop.run_in_executor(None, input)
            
            if msg.strip():
                logging.info(f"Admin typing: {msg}")
                # Рассылаем во все существующие группы
                for room_name, room in self.groups.items():
                    await room.msg_queue.put(f"SERVER ADMIN: {msg}")

if __name__ == "__main__":
    try:
        asyncio.run(ChatServer().run())
    except KeyboardInterrupt:
        print("Server stopped.")