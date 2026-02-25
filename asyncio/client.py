import tkinter as tk
from tkinter import simpledialog
import asyncio
import threading
from datetime import datetime

# --- КОНФИГУРАЦИЯ ЦВЕТОВ (DARK THEME) ---
COLORS = {
    "bg_main": "#212121",       # Основной фон
    "bg_sec":  "#303030",       # Фон сайдбара и инпутов
    "bg_dialog": "#424242",     # Фон диалоговых окон
    "fg_text": "#ECEFF1",       # Белый текст
    "accent":  "#00B0FF",       # Голубой акцент
    "error":   "#FF5252",       # Красный (ошибки)
    "msg_self": "#00E676",      # Зеленый (свои сообщения)
    "msg_other": "#40C4FF",     # Голубой (чужие)
    "msg_sys": "#FFAB40",       # Оранжевый (система)
    "input_bg": "#424242",      # Фон ввода
    "btn_hover": "#616161"      # Цвет кнопки при наведении
}

class ModernChatClient:
    def __init__(self):
        # Настройка Asyncio
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()
        
        self.reader = None
        self.writer = None
        self.username = ""
        self.current_room = None
        
        self.chat_widgets = {} 
        self.active_rooms = []

        # Инициализация GUI
        self.root = tk.Tk()
        self.root.title("Chat")
        self.root.geometry("950x650")
        self.root.configure(bg=COLORS["bg_main"])
        
        self.font_main = ("Consolas", 11)
        self.font_ui = ("Segoe UI", 10, "bold")

        self._build_login_screen()

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    # --- ИНТЕРФЕЙС: LOGIN SCREEN ---
    def _build_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self.login_frame, text="SERVER IP:", bg=COLORS["bg_main"], fg=COLORS["accent"], font=self.font_ui).pack(pady=5)
        self.entry_ip = tk.Entry(self.login_frame, bg=COLORS["input_bg"], fg="white", insertbackground="white", relief="flat")
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.pack(pady=5, ipadx=5, ipady=5)

        tk.Label(self.login_frame, text="USERNAME:", bg=COLORS["bg_main"], fg=COLORS["accent"], font=self.font_ui).pack(pady=5)
        self.entry_user = tk.Entry(self.login_frame, bg=COLORS["input_bg"], fg="white", insertbackground="white", relief="flat")
        self.entry_user.pack(pady=5, ipadx=5, ipady=5)

        self.btn_connect = tk.Button(self.login_frame, text="CONNECT", bg=COLORS["accent"], fg="black", font=self.font_ui,
                        command=self._on_connect_click, relief="flat", activebackground=COLORS["msg_other"])
        self.btn_connect.pack(pady=20, fill="x")

    def _on_connect_click(self):
        ip = self.entry_ip.get()
        user = self.entry_user.get()
        if not user: return
        
        self.username = user
        self.btn_connect.config(state="disabled", text="CONNECTING...")
        asyncio.run_coroutine_threadsafe(self.connect_to_server(ip, 8888, user), self.loop)

    # --- ИНТЕРФЕЙС: MAIN CHAT ---
    def _build_main_ui(self):
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR
        self.sidebar = tk.Frame(self.root, bg=COLORS["bg_sec"], width=220)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        tk.Label(self.sidebar, text="ROOMS", bg=COLORS["bg_sec"], fg=COLORS["accent"], font=("Segoe UI", 14, "bold")).pack(pady=15)
        
        self.rooms_list_frame = tk.Frame(self.sidebar, bg=COLORS["bg_sec"])
        self.rooms_list_frame.pack(fill="both", expand=True)

        ctrl_frame = tk.Frame(self.sidebar, bg=COLORS["bg_sec"])
        ctrl_frame.pack(side="bottom", fill="x", pady=10)
        
        tk.Button(ctrl_frame, text="+ NEW GROUP", bg=COLORS["input_bg"], fg="white", relief="flat",
                  command=self.ask_create_group, activebackground=COLORS["btn_hover"]).pack(fill="x", padx=10, pady=5)
        tk.Button(ctrl_frame, text="> JOIN ROOM", bg=COLORS["input_bg"], fg="white", relief="flat",
                  command=self.ask_join_room, activebackground=COLORS["btn_hover"]).pack(fill="x", padx=10, pady=5)

        # 2. CHAT AREA
        self.chat_container = tk.Frame(self.root, bg=COLORS["bg_main"])
        self.chat_container.grid(row=0, column=1, sticky="nsew")
        
        self.header_label = tk.Label(self.chat_container, text="Select a room to start chatting", bg=COLORS["bg_main"], fg="gray", font=("Segoe UI", 16))
        self.header_label.pack(side="top", fill="x", pady=10)

        self.placeholder_frame = tk.Frame(self.chat_container, bg=COLORS["bg_main"])
        self.placeholder_frame.pack(expand=True, fill="both")

        input_frame = tk.Frame(self.chat_container, bg=COLORS["bg_sec"], height=60)
        input_frame.pack(side="bottom", fill="x")
        
        # Поле ввода изначально отключено
        self.msg_entry = tk.Entry(input_frame, bg=COLORS["input_bg"], fg="gray", 
                                  insertbackground="white", font=self.font_main, 
                                  relief="flat", state="disabled")
        self.msg_entry.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        self.msg_entry.bind("<Return>", lambda e: self.send_msg())
        
        self.send_btn = tk.Button(input_frame, text="SEND", bg=COLORS["accent"], fg="black", font=("Segoe UI", 10, "bold"),
                             command=self.send_msg, state="disabled", relief="flat")
        self.send_btn.pack(side="right", padx=15, pady=15)

    # --- КАСТОМНЫЕ ОКНА ---
    def show_custom_error(self, message):
        """Красивое окно ошибки вместо системного."""
        top = tk.Toplevel(self.root)
        top.title("Error")
        top.geometry("400x150")
        top.configure(bg=COLORS["bg_dialog"])
        
        # Центрируем
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        top.geometry(f"+{x}+{y}")

        tk.Label(top, text="⚠ CONNECTION ERROR", fg=COLORS["error"], bg=COLORS["bg_dialog"], font=("Segoe UI", 12, "bold")).pack(pady=10)
        tk.Label(top, text=message, fg="white", bg=COLORS["bg_dialog"], wraplength=380).pack(pady=5)
        
        # Сброс интерфейса при ошибке входа
        if hasattr(self, 'btn_connect'):
             self.btn_connect.config(state="normal", text="CONNECT")

        tk.Button(top, text="CLOSE", bg=COLORS["error"], fg="white", command=top.destroy, relief="flat").pack(pady=10)

    # --- ЛОГИКА UI ---
    def update_sidebar_rooms(self):
        for widget in self.rooms_list_frame.winfo_children():
            widget.destroy()
            
        for room in self.active_rooms:
            display_name = room.replace("Group:", "# ").replace("Personal:", "@ ")
            if room.startswith("Personal:"):
                parts = room.split(":")
                if len(parts) == 3:
                    other = parts[2] if parts[1] == self.username else parts[1]
                    display_name = f"@ {other}"

            # Подсветка активной комнаты
            bg_color = COLORS["input_bg"] if room == self.current_room else COLORS["bg_sec"]
            fg_color = COLORS["accent"] if room == self.current_room else COLORS["fg_text"]

            btn = tk.Button(self.rooms_list_frame, text=display_name, anchor="w", padx=15,
                            bg=bg_color, fg=fg_color, relief="flat",
                            activebackground=COLORS["bg_main"], activeforeground=COLORS["accent"],
                            font=("Segoe UI", 10),
                            command=lambda r=room: self.switch_room(r))
            btn.pack(fill="x", pady=2)

    def switch_room(self, room_id):
        self.current_room = room_id
        self.update_sidebar_rooms() # Обновить подсветку
        
        display = room_id.replace("Group:", "# ").replace("Personal:", "@ ")
        self.header_label.config(text=display, fg=COLORS["fg_text"])
        
        # Разблокируем ввод
        self.msg_entry.config(state="normal", fg="white", bg=COLORS["input_bg"])
        self.send_btn.config(state="normal")
        self.msg_entry.focus_set() # Фокус на ввод

        for w in self.chat_widgets.values():
            w.pack_forget()
        self.placeholder_frame.pack_forget()
        
        if room_id not in self.chat_widgets:
            self._create_chat_widget(room_id)
            
        self.chat_widgets[room_id].pack(expand=True, fill="both", padx=15, pady=5)

    def _create_chat_widget(self, room_id):
        txt = tk.Text(self.chat_container, bg=COLORS["bg_main"], fg=COLORS["fg_text"],
                      font=self.font_main, state="disabled", wrap="word", borderwidth=0,
                      padx=10, pady=10)
        
        txt.tag_config("self", foreground=COLORS["msg_self"])
        txt.tag_config("other", foreground=COLORS["msg_other"])
        txt.tag_config("system", foreground=COLORS["msg_sys"], font=("Consolas", 10, "italic"))
        txt.tag_config("time", foreground="gray", font=("Consolas", 9))
        
        self.chat_widgets[room_id] = txt

    def append_message(self, room_key, user, text):
        """
        Добавляет сообщение. 
        room_key - это УЖЕ полный ключ (Group:Name), найденный в process_packet.
        """
        if room_key not in self.active_rooms:
            self.active_rooms.append(room_key)
            self.update_sidebar_rooms()
            
        if room_key not in self.chat_widgets:
            self._create_chat_widget(room_key)

        txt_widget = self.chat_widgets[room_key]
        now = datetime.now().strftime("%H:%M")
        
        txt_widget.config(state="normal")
        
        tag = "other"
        if user == self.username: tag = "self"
        if user == "System": tag = "system"
        
        if user == "System":
            txt_widget.insert("end", f"\n[{now}] {text}\n", ("system"))
        else:
            txt_widget.insert("end", f"\n[{now}] ", "time")
            txt_widget.insert("end", f"{user}: ", tag)
            txt_widget.insert("end", f"{text}")
            
        txt_widget.see("end")
        txt_widget.config(state="disabled")

    # --- СЕТЬ ---
    async def connect_to_server(self, ip, port, username):
        try:
            self.reader, self.writer = await asyncio.open_connection(ip, port)
            
            await self.reader.readline() 
            self.writer.write(f"{username}\n".encode())
            await self.writer.drain()
            
            # Успех - строим UI
            self.root.after(0, self._build_main_ui)
            
            self.writer.write(b"/myrooms\n")
            await self.writer.drain()
            
            await self.listen_server()
            
        except Exception as e:
            # FIX: сохраняем текст ошибки в строку и передаем в lambda через аргумент по умолчанию
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self.show_custom_error(msg))

    async def listen_server(self):
        while True:
            try:
                line = await self.reader.readline()
                if not line: break
                text = line.decode().strip()
                self.root.after(0, lambda t=text: self.process_packet(t))
            except Exception:
                break
        
        # Если цикл прервался (разрыв соединения)
        self.root.after(0, lambda: self.show_custom_error("Disconnected from server"))

    def process_packet(self, text):
        # print(f"DEBUG: {text}") 
        
        if text.startswith("MYROOMS:"):
            raw = text.split(":", 1)[1]
            if raw:
                rooms = raw.split(",")
                first_load = len(self.active_rooms) == 0 # Проверка: это первый запуск?
                
                for r in rooms:
                    r = r.strip()
                    if r and r not in self.active_rooms:
                        self.active_rooms.append(r)
                
                self.update_sidebar_rooms()

                # --- ДОБАВЛЕНО: Авто-выбор комнаты ---
                # Если комната не выбрана и список пришел, выбираем первую (General)
                if not self.current_room and self.active_rooms:
                    # Предпочитаем General, если она есть
                    target = "Group:General"
                    if target in self.active_rooms:
                        self.switch_room(target)
                    else:
                        self.switch_room(self.active_rooms[0])
                
        elif text.startswith("[ROOM]"):
            # FIX: Умный парсинг имени комнаты
            try:
                content = text[6:] # "RoomName User: Msg"
                
                # Попытка найти разделитель "User:" (или System:)
                # Проблема сервера: он шлет "[ROOM]Name Msg".
                # Нам нужно понять, где кончается имя комнаты и начинается сообщение.
                
                # Эвристика: пробуем найти имя комнаты среди наших активных
                found_room_key = None
                rest_msg = ""

                # 1. Сначала проверяем точное совпадение начала строки с нашими комнатами
                # (с учетом префикса Group: или без)
                
                # Если сервер шлет "Group:Name", то все просто.
                # Если сервер шлет "Name", то нам надо найти "Group:Name".
                
                possible_room_name = content.split(" ", 1)[0] # Берем первое слово
                
                # Проверяем, есть ли такое среди ключей active_rooms
                if possible_room_name in self.active_rooms:
                    found_room_key = possible_room_name
                elif f"Group:{possible_room_name}" in self.active_rooms:
                    found_room_key = f"Group:{possible_room_name}"
                elif f"Personal:{possible_room_name}" in self.active_rooms:
                    # Для Personal имен чуть сложнее, но обычно там нет пробелов в ID
                    found_room_key = f"Personal:{possible_room_name}"
                
                # Если нашли ключ
                if found_room_key:
                    # Отрезаем имя комнаты из сообщения. 
                    # Сервер шлет: "[ROOM]Name User: Text" -> content="Name User: Text"
                    # Если мы определили, что Name - это имя комнаты, то остаток это "User: Text"
                    # Длина имени комнаты в сообщении:
                    len_name = len(possible_room_name)
                    rest = content[len_name:].strip() # "User: Text"
                    
                    if ": " in rest:
                        user, msg = rest.split(": ", 1)
                    else:
                        user = "System"
                        msg = rest
                        
                    self.append_message(found_room_key, user, msg)
                else:
                    # Если комната новая (еще нет в списке), или логика выше не сработала.
                    # Фолбэк на старую логику: первое слово - комната
                    room_name, rest = content.split(" ", 1)
                    # Предполагаем, что это группа
                    full_key = f"Group:{room_name}"
                    
                    if ": " in rest:
                        user, msg = rest.split(": ", 1)
                    else:
                        user = "System"
                        msg = rest
                    
                    self.append_message(full_key, user, msg)

            except Exception as e:
                print(f"Parse error: {e}")

    # --- ДЕЙСТВИЯ ---
    def send_msg(self):
        text = self.msg_entry.get()
        if not text or not self.current_room: return
        
        self.msg_entry.delete(0, "end")
        cmd = f"/send {self.current_room} {text}\n"
        asyncio.run_coroutine_threadsafe(self._send_async(cmd), self.loop)

    def ask_create_group(self):
        name = simpledialog.askstring("New Group", "Enter group name:")
        if name:
            # FIX: Удаляем пробелы, чтобы не ломать протокол сервера
            name = name.replace(" ", "_")
            cmd = f"/create_group {name}\n"
            asyncio.run_coroutine_threadsafe(self._send_async(cmd), self.loop)

    def ask_join_room(self):
        name = simpledialog.askstring("Join", "Enter room name:")
        if name:
            name = name.replace(" ", "_")
            if not name.startswith("Group:") and not name.startswith("Personal:"):
                 name = f"Group:{name}"
            cmd = f"/join {name}\n"
            asyncio.run_coroutine_threadsafe(self._send_async(cmd), self.loop)

    async def _send_async(self, cmd):
        if self.writer:
            try:
                self.writer.write(cmd.encode())
                await self.writer.drain()
            except Exception:
                self.root.after(0, lambda: self.show_custom_error("Failed to send message"))

if __name__ == "__main__":
    client = ModernChatClient()
    client.root.mainloop()