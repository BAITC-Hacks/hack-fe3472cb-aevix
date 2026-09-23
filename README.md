# HackAlem AI — Career Quest Backend

## 1. Описание проекта

Это backend для хакатон-проекта HackAlem AI в треке Halyk Bank. Он реализует AI-навигатор развития сотрудника на основе детерминированного рекомендательного движка, который оценивает gaps по навыкам, роль/грейд цели, историю активности и требования следующего уровня.

Главное ядро — Explainable AI Recommendation Engine: сотрудник получает 1–3 следующих шага с skill gaps, critical skills, требованиями role profile, историей активности, prerequisites и понятным объяснением.

Career City — только visualization/gamification layer поверх уже рассчитанных рекомендаций. Growth Coins — необязательная мотивационная фича, а ESG/Impact tags — визуальный слой. Ни один из этих слоёв не влияет на recommendation score.

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
- app/services/llm_service.py — optional OpenAI explanation layer с template fallback
- app/services/team_service.py — optional collaboration layer
- app/services/esg_service.py — Growth Coins wallet и ESG Impact Catalog

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

Для optional LLM-объяснений используйте только переменные окружения или `.env`:

```env
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-6-astra
```

Без `OPENAI_API_KEY` backend работает через локальный template explanation. Deterministic engine всегда выбирает события и считает score; OpenAI только формулирует объяснение.

Поддерживаются файлы:

- employees.json
- events.json
- skills.json
- activity_history.csv

Примечание: служебные каталоги вроде __MACOSX игнорируются.

## 4. Как импортировать датасет

Есть 2 способа.

### Через API

Импорт доступен только после входа HR. Сначала получите cookie сессии и `csrf_token`:

```bash
curl -c /tmp/career-quest-hr.cookies -X POST http://127.0.0.1:8000/api/auth/hr/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"hr","password":"YOUR_HR_PASSWORD"}'
curl -b /tmp/career-quest-hr.cookies -X POST http://127.0.0.1:8000/api/import/dataset \
  -H 'X-CSRF-Token: CSRF_TOKEN_FROM_LOGIN'
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

### Отдельные кабинеты сотрудника и HR

Перед первым входом HR создайте локальные учётные данные из корня backend:

```bash
venv/bin/python -m app.setup_hr
```

Команда сохраняет хеш пароля в `.env`, а логин и сгенерированный пароль — в `.local/hr-access.txt` с доступом только владельцу. Оба файла исключены из Git. После настройки перезапустите backend. `venv/bin/python -m app.setup_hr --rotate` заменяет пароль и отзывает существующие сессии; после команды также нужен перезапуск.

Запуск frontend:

```bash
cd frontend
npm install
npm run dev
```

- Сотрудник: http://localhost:5173/employee
- HR: http://localhost:5173/hr

Сотрудник не видит HR-навигацию. Backend проверяет HR-сессию на **всех** `/api/hr/*`, `/api/import/*` и `POST /api/employees/register`. Сам URL, employee_id или роль, указанная клиентом, доступ не предоставляют. Импорт, регистрация и выход требуют также заголовок `X-CSRF-Token` из ответа входа. Сессия хранится в HttpOnly cookie, действует 8 часов и отзывается при выходе; её токен в БД хранится в виде хеша. Без настроенного `HR_PASSWORD_HASH` вход закрыт.

Новые маршруты входа: `POST /api/auth/hr/login`, `GET /api/auth/session`, `POST /api/auth/logout`.

Сотруднический кабинет сохраняет демонстрационный выбор профиля; индивидуальный вход сотрудников/корпоративный SSO не подключён. Для развёртывания используйте HTTPS, `HR_COOKIE_SECURE=true`, перечислите точные адреса frontend в `ALLOWED_ORIGINS` через запятую. Рекомендуется единый домен с прокси `/api` на backend. Веб-сервер должен отдавать `frontend/dist/index.html` для `/employee` и `/hr`, как это делает Vite. Не публикуйте локальный файл учётных данных.

### Пошаговое обучение

«Моё обучение» показывает описание занятия и план из 3–5 шагов. План создаётся при первом раскрытии и сохраняется для сотрудника и занятия. Отметки сохраняются через `POST /api/employees/{employee_id}/quests/{event_id}/steps/{step_number}/complete`; чтение — через `GET /api/employees/{employee_id}/quests/{event_id}/steps?language=ru` (также `kk`, `en`). Повторное чтение возвращает тот же план.

Если план создан, для финального завершения нужны все его шаги. Подтверждение завершения отдельно начисляет награду и обновляет навыки; для командного квеста оно выполняется в «Совместном обучении». Ранее выбранные задания без сохранённого плана поддерживают прежний API завершения.

## 6. Список endpoints

- GET /health
- POST /api/import/dataset
- POST /api/import/employees
- POST /api/import/events
- POST /api/import/skills
- POST /api/import/history
- POST /api/import/check-profiles
- POST /api/import/check-history
- POST /api/import/jury-dataset
- GET /api/employees
- POST /api/employees/register
- GET /api/employees/{employee_id}
- GET /api/employees/{employee_id}/profile
- GET /api/employees/{employee_id}/trajectory
- GET /api/employees/{employee_id}/recommendations
- POST /api/employees/{employee_id}/quests/{event_id}/complete
- GET /api/employees/{employee_id}/quests/{event_id}/steps
- POST /api/employees/{employee_id}/quests/{event_id}/steps/{step_number}/complete
- POST /api/employees/{employee_id}/quests/{event_id}/select
- POST /api/pairs/invitations
- GET /api/pairs/invitations?employee_id=E0002
- GET /api/pairs/invitations/{invitation_id}/preview?employee_id=E0003
- POST /api/pairs/invitations/{invitation_id}/respond
- GET /api/pairs/{pair_id}
- GET /api/game/{employee_id}/map
- GET /api/game/{employee_id}/progress
- GET /api/game/{employee_id}/quests
- GET /api/hr/dashboard
- GET /api/hr/skill-gaps
- GET /api/hr/inactive-employees
- GET /api/hr/events-effectiveness
- POST /api/teams
- GET /api/teams/{team_id}
- POST /api/teams/{team_id}/join
- POST /api/teams/{team_id}/quests/{event_id}/start
- POST /api/teams/{team_id}/quests/{event_id}/complete
- POST /api/teams/{team_id}/pause
- POST /api/teams/{team_id}/resume
- GET /api/wallet/{employee_id}
- GET /api/esg-goals
- POST /api/esg-goals/{goal_id}/contribute
- GET /api/hr/esg-engagement

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
      "title": "Designing High-Load Systems",
      "quest_title": "Designing High-Load Systems",
      "type": "workshop",
      "score": 0.91,
      "priority": "high",
      "scoring_factors": {
        "skill_gap_score": 0.9,
        "critical_skill_score": 1.0,
        "event_impact_score": 0.8,
        "role_grade_relevance_score": 0.9,
        "history_score": 0.7,
        "prerequisite_score": 1.0
      },
      "why_recommended": [
        "System Design is 1, required level for Senior is 4",
        "This is a critical skill for the target grade",
        "The event improves System Design by +1"
      ],
      "affected_skills": [
        {
          "skill_id": "SK_SYSTEM_DESIGN",
          "current_level": 1,
          "required_level": 4,
          "gain": 1,
          "expected_after": 2,
          "gap_before": 3,
          "gap_after": 2,
          "is_critical": true
        }
      ],
      "history_signal": {
        "completed_similar": 2,
        "missed_or_declined_similar": 0,
        "already_completed_this_event": false
      },
      "explanation": "System Design is currently 1 while Senior Backend Engineer requires 4. The event improves System Design by +1 and reduces the gap from 3 to 2."
    }
  ]
}
```

После импорта jury-профиля рекомендации доступны сразу:

```bash
curl -X POST http://127.0.0.1:8000/api/import/check-profiles -F "file=@employees.json"
curl http://127.0.0.1:8000/api/employees/E_TEST_001/recommendations
```

Для полного набора файлов можно использовать `multipart/form-data` endpoint `/api/import/jury-dataset` с полями `employees`, `history`, `events`, `skills`. Импорт идемпотентный и обновляет записи по `employee_id`/`record_id`.

Регистрация одного сотрудника выполняется через `POST /api/employees/register` с тем же форматом профиля, что и в `employees.json`.

Завершение добровольного квеста возвращает обновление навыков, progress и Growth Coins:

```json
{
  "progress_to_next_grade_before": 57.35,
  "progress_to_next_grade_after": 60.12,
  "coins_earned": 120,
  "wallet_balance": 840,
  "coin_reason": "Voluntary quest completed, critical skill improved, skill gap reduced"
}
```

Для `mandatory=true` событие может быть записано в `activity_history`, но `coins_earned` всегда равен `0`.

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
  - `skill_gap_score * 0.30`
  - `critical_skill_score * 0.20`
  - `event_impact_score * 0.20`
  - `role_grade_relevance_score * 0.15`
  - `history_score * 0.10`
  - `prerequisite_score * 0.05`
7. Учитываются completed, missed, declined, dropped и уже завершённые события.
8. Возвращается top 1–3 события вместе с explainability.

Важно: движок не выбирает единственный самый низкий навык и не строит рекомендацию по одному полю профиля — используется несколько факторов одновременно.

## 9. Как работает game map

Игровая карта — это визуальный слой поверх рекомендаций:

- Current Profile — текущий профиль сотрудника
- Core Skills — текущий набор ключевых навыков
- Senior Ready / target zone — целевой грейд
- `center` — progress и wallet balance
- `districts` — визуальные группы навыков, locked/unlocked status и impact tags
- `quest_board` — события непосредственно из recommendation engine с `source: recommendation_engine`
- `completed_quest_ids` — завершённые активности

Game service не рассчитывает score и не выбирает события по потребностям районов.

Frontend использует Halyk Together как основной пользовательский flow. Career City убран из интерфейса; старые `/api/game/*` endpoints сохранены только для обратной совместимости backend-клиентов.

Quest steps строятся через OpenAI Responses API, если задан `OPENAI_API_KEY`. Backend передаёт модели только выбранное событие и профиль сотрудника, а результатом становится structured JSON из 3–5 шагов. Без ключа используется локальный template fallback, поэтому прохождение квеста не ломается.

Это позволяет сотруднику видеть прогресс как карьерную карту, но объяснение остаётся в рекомендациях, а не только в анимации.

## 10. Команды, coins и ESG

Команды являются optional collaboration layer: создатель добавляет участников, команда запускает и завершает квесты, может быть поставлена на паузу или перейти в `waiting_for_member` после трёх командных квестов. Командная механика не меняет AI score.

Growth Coins не являются деньгами и не формируют рейтинг сотрудников. Их можно потратить на ESG-инициативы после проверки HR: mentoring, Green Office, образовательную программу или workshop. API возвращает `pending_hr_review`, а HR видит только агрегированную вовлечённость через `/api/hr/esg-engagement`.

### Совместный квест

Кнопка «Пройти с коллегой» публикует только выбранную активность и договорённости: диапазон дат, формат (`online_together`, `in_person` или `self_paced_discussion`) и отображаемое имя/псевдоним. Scoring, skill gaps и полная рекомендация в приглашение не попадают.

Перед откликом второй сотрудник вызывает `preview` endpoint. Backend заново проверяет событие через его собственный recommendation context и возвращает `eligible` с персональным объяснением. Если активность не подходит по роли, грейду или развитию, ответ будет `eligible: false`, а pair space не создаётся. После подходящего согласия создаётся pair space с участниками и следующим шагом.

## 11. Как проверить на профиле E0002

```bash
curl http://127.0.0.1:8000/api/employees/E0002/recommendations
```

Также доступны:

```bash
curl http://127.0.0.1:8000/api/game/E0002/map
curl http://127.0.0.1:8000/api/hr/dashboard
```

## 12. Тест

```bash
python -m pytest app/tests/test_recommendation.py -q
```

## 13. Ограничения и принципы

- Employee видит только себя.
- HR видит только агрегированную аналитику.
- Mandatory events не входят в AI-рекомендации.
- Данные синтетические.
- Детерминированный fallback engine обязателен.
- Нет публичного рейтинга сотрудников.
