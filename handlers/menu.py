from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router()

CONTENT_DIR = Path(__file__).parent.parent / "content"
FILES_DIR = CONTENT_DIR / "files"
MILITARY_DEFERMENT_PDF = FILES_DIR / "Отсрочка_от_армии_и_мобилизации_документы.pdf"

TOPICS: dict[str, tuple[str, str]] = {
    "employment":          ("📋 Трудоустройство по ТК",        "employment.md"),
    "vacation":            ("🏖️ Отпуск",                       "vacation.md"),
    "sick_leave":          ("🏥 Больничный",                    "sick_leave.md"),
    "ip":                  ("💼 ИП и самозанятые",              "ip.md"),
    "accreditation":       ("🏆 IT-аккредитация",               "accreditation.md"),
    "military_deferment":  ("🪖 Отсрочка от армии/мобилизации", "military_deferment.md"),
    "dismissal":           ("🚪 Увольнение",                    "dismissal.md"),
}

MAX_MSG_LEN = 4096


def main_menu_keyboard() -> InlineKeyboardMarkup:
    topic_items = [
        InlineKeyboardButton(text=label, callback_data=f"topic:{key}")
        for key, (label, _) in TOPICS.items()
    ]
    # Pair topics into rows of 2 columns
    buttons = [
        topic_items[i : i + 2] for i in range(0, len(topic_items), 2)
    ]
    buttons.append(
        [InlineKeyboardButton(text="💬 Задать свой вопрос", callback_data="free_question")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
        ]
    )


def military_submenu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🪖 Отсрочка от армии", callback_data="military:army")],
            [
                InlineKeyboardButton(
                    text="📋 Отсрочка от мобилизации",
                    callback_data="military:mobilization",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")],
        ]
    )


def military_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="topic:military_deferment",
                )
            ]
        ]
    )


def read_topic_content(filename: str) -> str:
    path = CONTENT_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "⚠️ Информация по этой теме пока не добавлена."


def split_text(text: str, chunk_size: int = MAX_MSG_LEN) -> list[str]:
    """Split text into chunks no longer than chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]
    parts: list[str] = []
    while text:
        parts.append(text[:chunk_size])
        text = text[chunk_size:]
    return parts


def extract_military_content(section: str) -> str:
    content = read_topic_content("military_deferment.md")
    army_marker = "Отсрочка от срочной службы (призыв)"
    mob_marker = "Отсрочка от мобилизации"
    doc_marker = "Документы"

    intro, rest = content.split(army_marker, 1)
    army_part, rest = rest.split(mob_marker, 1)
    mob_part = rest.split(doc_marker, 1)[0] if doc_marker in rest else rest

    intro = intro.strip()
    army_text = f"{army_marker}\n{army_part.strip()}"
    mob_text = f"{mob_marker}\n{mob_part.strip()}"

    if section == "army":
        return f"{intro}\n\n{army_text}"
    return f"{intro}\n\n{mob_text}"


async def send_text_parts(message: Message, parts: list[str], reply_markup=None) -> None:
    for i, part in enumerate(parts):
        markup = reply_markup if i == len(parts) - 1 else None
        await message.answer(part, reply_markup=markup)


async def send_military_subsection(callback: CallbackQuery, section: str) -> None:
    content = extract_military_content(section)
    await send_text_parts(callback.message, split_text(content))

    if not MILITARY_DEFERMENT_PDF.is_file():
        await callback.message.answer(
            "⚠️ Файл с документами временно недоступен.",
            reply_markup=military_back_keyboard(),
        )
        return

    document = FSInputFile(MILITARY_DEFERMENT_PDF)
    await callback.message.answer_document(
        document,
        reply_markup=military_back_keyboard(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Добро пожаловать! Команда кадров AYA (Ana_Lawyer, Almira, Liberty) на связи.\n\n"
        "Здесь можно быстро узнать всё по трудоустройству, отпускам, больничным, day off, "
        "увольнению, сотрудничеству по ИП, аккредитации компании и отсрочке от армии/мобилизации.\n\n"
        "Жми на нужную тему 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("topic:"))
async def topic_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    key = callback.data.removeprefix("topic:")
    if key not in TOPICS:
        await callback.answer("Неизвестная тема", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if key == "military_deferment":
        await callback.message.answer(
            "Выберите подраздел:",
            reply_markup=military_submenu_keyboard(),
        )
        await callback.answer()
        return

    _, filename = TOPICS[key]
    content = read_topic_content(filename)
    await send_text_parts(callback.message, split_text(content), back_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("military:"))
async def military_subsection_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    section = callback.data.removeprefix("military:")
    if section not in {"army", "mobilization"}:
        await callback.answer("Неизвестный подраздел", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await send_military_subsection(callback, section)
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "Выберите тему или задайте свой вопрос:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
