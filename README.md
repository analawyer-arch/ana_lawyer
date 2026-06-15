# HR FAQ Bot

Telegram-бот для сотрудников отдела кадров. Отвечает на типовые вопросы по 7 темам
и обрабатывает свободные вопросы через Anthropic Claude.

Репозиторий: [github.com/analawyer-arch/ana_lawyer](https://github.com/analawyer-arch/ana_lawyer)

---

## Структура проекта

```
hr-faq-bot/
├── bot.py                     # Точка входа — запускать этот файл
├── handlers/
│   ├── menu.py                # Главное меню и навигация по темам
│   └── free_question.py       # Обработка свободных вопросов через AI
├── content/
│   ├── employment.md          # Трудоустройство по ТК
│   ├── vacation.md            # Отпуск
│   ├── sick_leave.md          # Больничный
│   ├── ip.md                  # ИП и самозанятые
│   ├── accreditation.md       # IT-аккредитация
│   ├── military_deferment.md  # Отсрочка от армии/мобилизации
│   ├── dismissal.md           # Увольнение
│   └── files/                 # PDF-документы (отправляются ботом)
├── logs/
│   └── .gitkeep               # Папка для логов (создаётся автоматически)
├── .env.example               # Шаблон переменных окружения
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Быстрый старт

### 1. Скачайте проект

**С GitHub:**
```bash
git clone https://github.com/analawyer-arch/ana_lawyer.git
cd ana_lawyer
```

**Или** распакуйте архив `hr-faq-bot-upload.zip` на сервере.

### 2. Создайте виртуальное окружение и установите зависимости

```bash
python3 -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Создайте файл `.env` из шаблона

```bash
# Linux / macOS
cp .env.example .env

# Windows
copy .env.example .env
```

Откройте `.env` и заполните значения:

| Переменная          | Обязательно | Описание |
|---------------------|-------------|----------|
| `BOT_TOKEN`         | Да          | Токен бота от [@BotFather](https://t.me/BotFather) |
| `HR_CONTACT`        | Да          | Контакты кадров (например, `@hr_manager`) |
| `ANTHROPIC_API_KEY` | Нет         | Ключ с [console.anthropic.com](https://console.anthropic.com/) — для AI-ответов |
| `PROXY`             | Нет         | Прокси, если Telegram недоступен (`http://host:port`) |

> **Важно:** файл `.env` не загружается на GitHub. Создайте его вручную на каждом сервере.

### 4. Заполните контентные файлы

Откройте файлы в папке `content/` и замените строку `[Текст ответа будет добавлен]`
на реальные ответы по каждой теме.

### 5. Запустите бота

```bash
python3 bot.py
```

На Windows, если `python` не работает:
```bash
py bot.py
```

Для остановки нажмите `Ctrl+C`. Должен работать **только один** экземпляр бота.

---

## Загрузка на сервер (Linux)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/analawyer-arch/ana_lawyer.git
cd ana_lawyer

# 2. Установить зависимости
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Создать и заполнить .env
cp .env.example .env
nano .env

# 4. Запустить (для проверки)
python3 bot.py
```

Для постоянной работы используйте systemd, screen или tmux.

---

## Логирование неотвеченных вопросов

Если Claude не смог уверенно ответить на вопрос, бот:

1. Отправляет пользователю стандартный ответ с контактом специалиста.
2. Записывает вопрос в `logs/unanswered.log`:

```json
{"date": "2026-06-15T12:00:00", "username": "ivan_petrov", "user_id": 123456789, "question": "..."}
```

---

## Как работает ИИ-ответ

При нажатии «💬 Задать свой вопрос» бот:

1. Переходит в режим ожидания текста.
2. Отправляет вопрос в Anthropic API (модель `claude-sonnet-4-6`) вместе
   с содержимым папки `content/` в качестве базы знаний.
3. Если Claude отвечает `UNKNOWN` — вопрос логируется, пользователь получает
   направление к специалисту.
4. Иначе — ответ отправляется пользователю.

Без `ANTHROPIC_API_KEY` бот работает, но AI-ответы отключены.

---

## Требования

- Python 3.11+
- Доступ к Telegram Bot API
- Anthropic API (опционально, для свободных вопросов)
