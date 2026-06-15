import json
import logging
import os
from datetime import datetime
from pathlib import Path

import anthropic
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

router = Router()

CONTENT_DIR = Path(__file__).parent.parent / "content"
LOG_FILE = Path(__file__).parent.parent / "logs" / "unanswered.log"

UNKNOWN_MARKER = "UNKNOWN"

SYSTEM_PROMPT_TEMPLATE = """\
Ты — помощник отдела кадров. Отвечай на вопросы сотрудников строго на основе \
предоставленной базы знаний. Отвечай кратко, по-деловому, на русском языке. \
Не выдумывай фактов, которых нет в базе знаний.

Темы базы знаний:
1. Трудоустройство по ТК
2. Отпуск
3. Больничный
4. ИП и самозанятые
5. IT-аккредитация компании
6. Отсрочка от армии

Если вопрос не относится ни к одной из этих тем, или ты не можешь уверенно \
ответить на основе базы знаний — ответь ровно одним словом: {marker}

База знаний:
---
{knowledge_base}
---
""".format(
    marker=UNKNOWN_MARKER,
    knowledge_base="{knowledge_base}",
)


class QuestionStates(StatesGroup):
    waiting_for_question = State()


def _load_knowledge_base() -> str:
    """Read all .md files from content/ and join them."""
    parts: list[str] = []
    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            parts.append(f"### {md_file.stem}\n{text}")
        except OSError as exc:
            logger.warning("Не удалось прочитать %s: %s", md_file, exc)
    return "\n\n---\n\n".join(parts) if parts else "(база знаний пуста)"


def _log_unanswered(username: str | None, user_id: int, question: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "username": username or "",
        "user_id": user_id,
        "question": question,
    }
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.error("Не удалось записать в лог: %s", exc)


def _is_unknown(answer: str) -> bool:
    return answer.strip().upper() == UNKNOWN_MARKER


async def _ask_claude(question: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY не задан в .env")

    knowledge_base = _load_knowledge_base()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(knowledge_base=knowledge_base)

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text.strip()


@router.callback_query(F.data == "free_question")
async def free_question_start(callback: CallbackQuery, state: FSMContext) -> None:
    # If AI is not configured, immediately redirect to HR contacts
    if not os.getenv("ANTHROPIC_API_KEY"):
        hr_contact = os.getenv("HR_CONTACT", "специалиста отдела кадров")
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        from handlers.menu import main_menu_keyboard
        await callback.message.answer(
            f"Функция AI-ответов пока не подключена.\n\n"
            f"Задайте вопрос напрямую специалистам отдела кадров: {hr_contact}",
            reply_markup=main_menu_keyboard(),
        )
        await callback.answer()
        return

    await state.set_state(QuestionStates.waiting_for_question)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "✍️ Напишите ваш вопрос — я постараюсь на него ответить:"
    )
    await callback.answer()


@router.message(QuestionStates.waiting_for_question, F.text)
async def process_question(message: Message, state: FSMContext) -> None:
    await state.clear()
    question = message.text or ""

    hr_contact = os.getenv("HR_CONTACT", "специалиста отдела кадров")

    thinking_msg = await message.answer("⏳ Обрабатываю вопрос…")

    try:
        answer = await _ask_claude(question)
    except Exception as exc:
        logger.exception("Ошибка при обращении к Anthropic API: %s", exc)
        await thinking_msg.delete()
        await message.answer(
            "⚠️ Произошла техническая ошибка. Попробуйте позже или обратитесь к "
            f"{hr_contact}."
        )
        _return_to_menu_hint(message)
        return

    await thinking_msg.delete()

    if _is_unknown(answer):
        _log_unanswered(
            username=message.from_user.username,
            user_id=message.from_user.id,
            question=question,
        )
        await message.answer(
            f"Пока не могу точно ответить, обратитесь к специалисту отдела кадров: "
            f"{hr_contact}"
        )
    else:
        await message.answer(answer)

    from handlers.menu import main_menu_keyboard  # local import to avoid circular

    await message.answer(
        "Если остались вопросы — выберите тему или задайте ещё один:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(QuestionStates.waiting_for_question)
async def question_not_text(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте вопрос текстом.")


def _return_to_menu_hint(message: Message) -> None:
    pass  # placeholder, menu hint is shown after answer block
