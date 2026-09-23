# HackAlem AI — Career Quest Backend

## 1. Описание проекта

Это backend для хакатон-проекта HackAlem AI в треке Halyk Bank. Он реализует AI-навигатор развития сотрудника на основе детерминированного рекомендательного движка, который оценивает gaps по навыкам, роль/грейд цели, историю активности и требования следующего уровня.

Главная идея — не геймификация ради геймификации, а explainable AI рекомендации: сотрудник получает конкретный следующий квест с пояснением, почему его стоит выполнить, какие навыки он закрывает и как это связано с целевым грейдом.

## 2. Архитектура

Проект построен по модульной архитектуре FastAPI:

- app/main.py — точка входа FastAPI
- app/core/config.py — настройки и переменные окружения
- app/db/database.py — SQLite engine и сессии SQLAlchemy
- app/db/models.py — модели данных
- app/schemas — Pydantic-схемы запросов/ответов
- app/services — бизнес-логика импорта, рекомендаций, прогресса, игры, HR
- app/routers — REST-endpoints
- app/utils — утилиты для грейдов, scoring и explainability

## 3. Как положить датасет

В корне проекта находится папка:

- career_quest_dataset/case_1/career_quest_dataset

Если папка не находится рядом с проектом, можно указать путь через переменную окружения:

```bash
set DATASET_DIR=C:\path\to\dataset
```

Или в Linux/macOS:

```bash
export DATASET_DIR=/path/to/dataset
```

Поддерживаются файлы:

- employees.json
- events.json
- skills.json
- activity_history.csv

Примечание: служебные каталоги вроде __MACOSX игнорируются.

## 4. Как импортировать датасет

Есть 2 способа.

### Через API

```bash
curl -X POST "http://127.0.0.1:8000/api/import/dataset?dataset_dir=C:/path/to/career_quest_dataset/case_1/career_quest_dataset"
```

### Через seed при старте

При запуске backend автоматически создает SQLite БД и загружает датасет, если таблицы пустые.

## 5. Как запустить backend

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

После запуска Swagger доступен здесь:

- http://127.0.0.1:8000/docs

## 6. Список endpoints

- GET /health
- POST /api/import/dataset
- POST /api/import/employees
- POST /api/import/events
- POST /api/import/skills
- POST /api/import/history
- GET /api/employees
- GET /api/employees/{employee_id}
- GET /api/employees/{employee_id}/profile
- GET /api/employees/{employee_id}/trajectory
- GET /api/employees/{employee_id}/recommendations
- POST /api/employees/{employee_id}/quests/{event_id}/complete
- GET /api/game/{employee_id}/map
- GET /api/game/{employee_id}/progress
- GET /api/game/{employee_id}/quests
- GET /api/hr/dashboard
- GET /api/hr/skill-gaps
- GET /api/hr/inactive-employees
- GET /api/hr/events-effectiveness

## 7. Примеры request/response

### Профиль сотрудника

```bash
curl http://127.0.0.1:8000/api/employees/E0002/profile
```

Пример ответа:

```json
{
  "employee_id": "E0002",
  "role": "Backend Engineer",
  "grade": "Middle",
  "target_role": "Backend Engineer",
  "target_grade": "Senior",
  "progress_to_next_grade": 58.0,
  "skills": {
    "SK_PYTHON": 3,
    "SK_SYSTEM_DESIGN": 1
  }
}
```

### Recommendation

```bash
curl http://127.0.0.1:8000/api/employees/E0002/recommendations
```

Пример ответа:

```json
{
  "employee_id": "E0002",
  "role": "Backend Engineer",
  "current_grade": "Middle",
  "target_role": "Backend Engineer",
  "target_grade": "Senior",
  "progress_to_next_grade": 58,
  "recommendations": [
    {
      "event_id": "EV_006",
      "quest_title": "Designing High-Load Systems",
      "score": 0.91,
      "priority": "high",
      "affected_skills": [
        {
          "skill_id": "SK_SYSTEM_DESIGN",
          "current_level": 1,
          "required_level": 4,
          "gain": 1,
          "expected_after": 2
        }
      ],
      "reason": "System Design currently at 1 and required at 4 for Senior...",
      "game_message": "Следующий квест на карте: Designing High-Load Systems. Он приблизит тебя к уровню Senior Backend Engineer."
    }
  ]
}
```

## 8. Как работает recommendation engine

Алгоритм детерминированный и укладывается в требования по скорости:

1. Определяется целевой грейд сотрудника из career_goal или следующего уровня по иерархии.
2. Загружается RoleProfile для target_role + target_grade.
3. Считаются skill gaps: required_level - current_level.
4. Берутся только positive gaps > 0.
5. События-фильтры:
   - mandatory = false
   - target_roles содержит роль сотрудника/целевую роль
   - target_grades сопоставимы с целевым грейдом
   - событие развивает хотя бы один gap-навык
   - prerequisites выполнены
   - event_id уже не завершен
6. Считается score на основе нескольких факторов:
   - gap_importance
   - critical_skill_bonus
   - event_impact
   - role_grade_relevance
   - history_fit
7. Возвращается top 1–3 события вместе с explainability.

Важно: движок не выбирает единственный самый низкий навык и не строит рекомендацию по одному полю профиля — используется несколько факторов одновременно.

## 9. Как работает game map

Игровая карта — это визуальный слой поверх рекомендаций:

- Current Profile — текущий профиль сотрудника
- Core Skills — текущий набор ключевых навыков
- Senior Ready / target zone — целевой грейд
- recommended_quest_ids — top-квесты для следующего шага

Это позволяет сотруднику видеть прогресс как карьерную карту, но объяснение остаётся в рекомендациях, а не только в анимации.

## 10. Как проверить на профиле E0002

```bash
curl http://127.0.0.1:8000/api/employees/E0002/recommendations
```

Также доступны:

```bash
curl http://127.0.0.1:8000/api/game/E0002/map
curl http://127.0.0.1:8000/api/hr/dashboard
```

## Тест

```bash
python -m pytest app/tests/test_recommendation.py -q
```

## Ограничения и принципы

- Employee видит только себя.
- HR видит только агрегированную аналитику.
- Mandatory events не входят в AI-рекомендации.
- Данные синтетические.
- Детерминированный fallback engine обязателен.
- Нет публичного рейтинга сотрудников.

## Frontend

Веб-интерфейс лежит в папке `frontend/` (React 18 + TypeScript + Vite, без UI-библиотек, адаптивный под телефон).

**Требования:** Node.js 18+ и запущенный backend на `http://127.0.0.1:8000`.

### Запуск

В первом терминале запустите backend (см. выше), в macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Во втором терминале:

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173. Для проверки с телефона в той же Wi-Fi сети используйте адрес `Network`, который выводит Vite.

### Переменные окружения

- `BACKEND_URL` — адрес backend для dev-прокси Vite (по умолчанию `http://127.0.0.1:8000`), см. `frontend/.env.example`.

### Экраны

- **Мой путь** — профиль сотрудника, готовность к целевому грейду, карьерная карта Junior → Lead, до 3 рекомендованных квестов с объяснением «почему», прирост навыков до/после, кнопка «Отметить выполненным» (`POST /api/employees/{id}/quests/{event_id}/complete`), разрывы навыков относительно `role_profiles` и история обучения.
- **HR-аналитика** — только агрегированные показатели: KPI, главные разрывы в навыках, популярные мероприятия, сегменты риска.
- Интерфейс на трёх языках (kk / ru / en), светлая и тёмная темы.

### Проверка основного сценария

1. Откройте http://localhost:5173 — загрузится сотрудник `E0002`.
2. Через поиск выберите любого сотрудника (по имени, роли или ID).
3. В блоке «Следующие квесты» нажмите «Отметить выполненным» — готовность и уровни навыков обновятся.
4. Переключитесь на вкладку «HR-аналитика».

### Сторонние компоненты

React, React DOM, Vite, @vitejs/plugin-react, TypeScript (MIT); шрифт Inter (Google Fonts, SIL OFL). Названия навыков и мероприятий берутся из датасета кейса `case_1/career_quest_dataset`.
