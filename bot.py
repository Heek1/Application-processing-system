import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class RegisterState(StatesGroup):
    waiting_for_name = State()

class RequestState(StatesGroup):
    waiting_for_text = State()

class CommentState(StatesGroup):
    waiting_for_request_id = State()
    waiting_for_text = State()

class ChangeStatusState(StatesGroup):
    waiting_for_request_id = State()
    waiting_for_status = State()

class ChangeRoleState(StatesGroup):
    waiting_for_tg_id = State()
    waiting_for_role = State()


async def api_get(path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}{path}") as resp:
            return resp.status, await resp.json()

async def api_post(path: str, payload: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}{path}", json=payload) as resp:
            return resp.status, await resp.json()

async def api_put(path: str, payload: dict):
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{API_URL}{path}", json=payload) as resp:
            return resp.status, await resp.json()


async def get_user_role(tg_id: int) -> str:
    status, data = await api_get(f"/user/{tg_id}")
    if status == 200:
        return data.get("role", "client").lower()
    return "client"

def format_request(req: dict) -> str:
    return (
        f"Заявка #{req['request_id']}\n"
        f"Статус: {req['status']}\n"
        f"Текст: {req['text']}\n"
        f"Створено: {str(req.get('created_at', ''))[:16]}\n"
    )

def get_menu(role: str):
    role = role.lower()
    if role == "admin":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Всі заявки"), KeyboardButton(text="Заявки за статусом")],
                [KeyboardButton(text="Додати коментар"), KeyboardButton(text="Змінити статус")],
                [KeyboardButton(text="Всі користувачі"), KeyboardButton(text="Змінити роль")],
                [KeyboardButton(text="Статистика"), KeyboardButton(text="Повідомлення")],
            ],
            resize_keyboard=True
        )
    elif role == "manager":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Всі заявки"), KeyboardButton(text="Заявки за статусом")],
                [KeyboardButton(text="Додати коментар"), KeyboardButton(text="Змінити статус")],
                [KeyboardButton(text="Повідомлення")],
            ],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Створити заявку")],
            [KeyboardButton(text="Мої заявки")],
            [KeyboardButton(text="Повідомлення")],
        ],
        resize_keyboard=True
    )

def status_keyboard():
    statuses = ["Нова", "В обробці", "Виконано", "Відхилено"]
    buttons = [[InlineKeyboardButton(text=s, callback_data=f"status:{s}")] for s in statuses]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def role_keyboard():
    roles = ["client", "manager", "admin"]
    buttons = [[InlineKeyboardButton(text=r.capitalize(), callback_data=f"role:{r}")] for r in roles]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    status, data = await api_get(f"/user/{tg_id}")

    if status == 200:
        role = data.get("role", "client")
        await message.answer(
            f"З поверненням, {data['name']}.\nРоль: {role}",
            reply_markup=get_menu(role)
        )
    else:
        await message.answer(
            "Вітаю. Введіть ваше повне ім'я для реєстрації:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegisterState.waiting_for_name)


@dp.message(RegisterState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    tg_id = message.from_user.id

    status, data = await api_post("/user/add", {
        "tg_id": tg_id,
        "full_name": full_name,
        "role": "client"
    })
    await state.clear()

    if status in (200, 201):
        await message.answer(
            f"Реєстрація успішна.\nІм'я: {full_name}\nРоль: client",
            reply_markup=get_menu("client")
        )
    else:
        await message.answer(f"Помилка реєстрації: {data.get('message', 'Невідома помилка')}")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Система обробки заявок\n\n"
        "Клієнт:\n"
        "- Створити заявку\n"
        "- Мої заявки\n"
        "- Повідомлення\n\n"
        "Менеджер:\n"
        "- Всі заявки\n"
        "- Заявки за статусом\n"
        "- Додати коментар\n"
        "- Змінити статус\n\n"
        "Адмін:\n"
        "- Всі користувачі\n"
        "- Змінити роль\n"
        "- Статистика\n\n"
        "Статуси: Нова -> В обробці -> Виконано / Відхилено"
    )
    await message.answer(text)


@dp.message(F.text == "Створити заявку")
async def create_request_start(message: Message, state: FSMContext):
    await message.answer("Опишіть вашу заявку:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RequestState.waiting_for_text)

@dp.message(RequestState.waiting_for_text)
async def create_request_finish(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    status, data = await api_post("/request/add", {
        "client_id": tg_id,
        "text": message.text.strip()
    })
    await state.clear()
    role = await get_user_role(tg_id)

    if status in (200, 201):
        await message.answer(
            f"Заявку #{data['request_id']} створено. Статус: {data['status']}",
            reply_markup=get_menu(role)
        )
    else:
        await message.answer(
            f"Помилка: {data.get('message', 'Невідома помилка')}",
            reply_markup=get_menu(role)
        )


@dp.message(F.text == "Мої заявки")
async def my_requests(message: Message):
    tg_id = message.from_user.id
    status, data = await api_get(f"/user/{tg_id}/requests")

    if status != 200 or not data:
        await message.answer("У вас ще немає заявок.")
        return

    chunks, current = [], ""
    for req in data[:10]:
        block = format_request(req) + "\n"
        if len(current) + len(block) > 3800:
            chunks.append(current)
            current = block
        else:
            current += block
    if current:
        chunks.append(current)

    for chunk in chunks:
        await message.answer(chunk)


@dp.message(F.text == "Всі заявки")
async def all_requests(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ("manager", "admin"):
        await message.answer("Немає доступу.")
        return

    status, data = await api_get("/requests")
    if status != 200 or not data:
        await message.answer("Заявок немає.")
        return

    chunks, current = [], ""
    for req in data[:15]:
        block = format_request(req) + f"Клієнт ID: {req['client_id']}\n\n"
        if len(current) + len(block) > 3800:
            chunks.append(current)
            current = block
        else:
            current += block
    if current:
        chunks.append(current)

    for chunk in chunks:
        await message.answer(chunk)


@dp.message(F.text == "Заявки за статусом")
async def filter_by_status(message: Message):
    role = await get_user_role(message.from_user.id)
    if role not in ("manager", "admin"):
        await message.answer("Немає доступу.")
        return
    await message.answer("Оберіть статус:", reply_markup=status_keyboard())

@dp.callback_query(F.data.startswith("status:"))
async def filter_status_cb(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == ChangeStatusState.waiting_for_status:
        return

    selected = callback.data.split(":")[1]
    status, data = await api_get(f"/requests?status={selected}")
    await callback.answer()

    if status != 200 or not data:
        await callback.message.answer(f"Заявок зі статусом '{selected}' немає.")
        return

    chunks, current = [], ""
    for req in data[:15]:
        block = format_request(req) + f"Клієнт ID: {req['client_id']}\n\n"
        if len(current) + len(block) > 3800:
            chunks.append(current)
            current = block
        else:
            current += block
    if current:
        chunks.append(current)

    for chunk in chunks:
        await callback.message.answer(chunk)


@dp.message(F.text == "Змінити статус")
async def change_status_start(message: Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ("manager", "admin"):
        await message.answer("Немає доступу.")
        return
    await message.answer("Введіть номер заявки:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ChangeStatusState.waiting_for_request_id)

@dp.message(ChangeStatusState.waiting_for_request_id)
async def change_status_get_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть коректний числовий ID.")
        return
    await state.update_data(request_id=int(message.text))
    await message.answer("Оберіть новий статус:", reply_markup=status_keyboard())
    await state.set_state(ChangeStatusState.waiting_for_status)

@dp.callback_query(F.data.startswith("status:"), ChangeStatusState.waiting_for_status)
async def change_status_finish(callback: CallbackQuery, state: FSMContext):
    new_status = callback.data.split(":")[1]
    data = await state.get_data()
    request_id = data["request_id"]
    tg_id = callback.from_user.id
    role = await get_user_role(tg_id)

    status, resp = await api_put(f"/request/{request_id}/status", {
        "status": new_status,
        "manager_id": tg_id
    })
    await state.clear()
    await callback.answer()

    if status == 200:
        await callback.message.answer(
            f"Статус заявки #{request_id} змінено на: {new_status}",
            reply_markup=get_menu(role)
        )
    else:
        await callback.message.answer(
            f"Помилка: {resp.get('message', 'Невідома помилка')}",
            reply_markup=get_menu(role)
        )


@dp.message(F.text == "Додати коментар")
async def add_comment_start(message: Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role not in ("manager", "admin"):
        await message.answer("Немає доступу.")
        return
    await message.answer("Введіть номер заявки:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(CommentState.waiting_for_request_id)

@dp.message(CommentState.waiting_for_request_id)
async def comment_get_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть коректний числовий ID.")
        return
    await state.update_data(request_id=int(message.text))
    await message.answer("Введіть текст коментаря:")
    await state.set_state(CommentState.waiting_for_text)

@dp.message(CommentState.waiting_for_text)
async def comment_finish(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    data = await state.get_data()
    role = await get_user_role(tg_id)

    status, resp = await api_post("/comment/add", {
        "request_id": data["request_id"],
        "user_id_tg": tg_id,
        "text": message.text.strip()
    })
    await state.clear()

    if status in (200, 201):
        await message.answer(
            f"Коментар до заявки #{data['request_id']} додано.",
            reply_markup=get_menu(role)
        )
    else:
        await message.answer(
            f"Помилка: {resp.get('message', 'Невідома помилка')}",
            reply_markup=get_menu(role)
        )


@dp.message(F.text == "Повідомлення")
async def my_messages(message: Message):
    tg_id = message.from_user.id
    status, data = await api_get(f"/user/{tg_id}/messages?unread_only=false")

    if status != 200 or not data:
        await message.answer("У вас немає повідомлень.")
        return

    text = "Ваші повідомлення:\n\n"
    for msg in data[:10]:
        read_mark = "[прочитано]" if msg.get("is_read") else "[нове]"
        text += f"{read_mark} {msg['content']}\n"
        text += f"{str(msg.get('created_at', ''))[:16]}\n\n"

        if not msg.get("is_read"):
            await api_put(f"/message/{msg['msg_id']}/read", {})

    await message.answer(text)


@dp.message(F.text == "Всі користувачі")
async def all_users(message: Message):
    role = await get_user_role(message.from_user.id)
    if role != "admin":
        await message.answer("Немає доступу.")
        return

    status, data = await api_get("/users")
    if status != 200 or not data:
        await message.answer("Користувачів немає.")
        return

    text = "Список користувачів:\n\n"
    for u in data:
        text += f"{u.get('name', '?')} | ID: {u['tg_id']} | {u.get('role', '?')}\n"

    await message.answer(text)


@dp.message(F.text == "Змінити роль")
async def change_role_start(message: Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role != "admin":
        await message.answer("Немає доступу.")
        return
    await message.answer("Введіть Telegram ID користувача:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ChangeRoleState.waiting_for_tg_id)

@dp.message(ChangeRoleState.waiting_for_tg_id)
async def change_role_get_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть коректний числовий ID.")
        return
    await state.update_data(target_tg_id=int(message.text))
    await message.answer("Оберіть нову роль:", reply_markup=role_keyboard())
    await state.set_state(ChangeRoleState.waiting_for_role)

@dp.callback_query(F.data.startswith("role:"), ChangeRoleState.waiting_for_role)
async def change_role_finish(callback: CallbackQuery, state: FSMContext):
    new_role = callback.data.split(":")[1]
    data = await state.get_data()
    target_id = data["target_tg_id"]
    admin_role = await get_user_role(callback.from_user.id)

    status, resp = await api_put(f"/user/{target_id}/role", {"role": new_role})
    await state.clear()
    await callback.answer()

    if status == 200:
        await callback.message.answer(
            f"Роль користувача {target_id} змінено на: {new_role}",
            reply_markup=get_menu(admin_role)
        )
    else:
        await callback.message.answer(
            f"Помилка: {resp.get('message', 'Невідома помилка')}",
            reply_markup=get_menu(admin_role)
        )


@dp.message(F.text == "Статистика")
async def get_stats(message: Message):
    role = await get_user_role(message.from_user.id)
    if role != "admin":
        await message.answer("Немає доступу.")
        return

    status, data = await api_get("/stats")
    if status != 200:
        await message.answer("Не вдалося отримати статистику.")
        return

    by_status = "\n".join(
        f"  {s['status']}: {s['count']}" for s in data.get("requests_by_status", [])
    )
    by_role = "\n".join(
        f"  {r['role'].capitalize()}: {r['count']}" for r in data.get("users_by_role", [])
    )

    text = (
        f"Статистика\n\n"
        f"Всього користувачів: {data['total_users']}\n"
        f"Всього заявок: {data['total_requests']}\n"
        f"Всього коментарів: {data['total_comments']}\n\n"
        f"Заявки за статусом:\n{by_status}\n\n"
        f"Користувачі за роллю:\n{by_role}"
    )
    await message.answer(text)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())