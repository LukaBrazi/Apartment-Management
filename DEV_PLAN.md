# Dev Plan: Feedback Form

**Branch:** `feat/feedback-form`
**Created:** 2026-04-26

## Задача

На сторінці `/contacts` додати форму зворотного зв'язку для авторизованих користувачів щодо роботи застосунку ApartmentOS. Форма містить тільки поле "Повідомлення" — ім'я та email підставляються автоматично з `request.user`. Записи зберігаються в БД, доступні в Django Admin з фільтрами. При новому записі — email-сповіщення адміну через Celery. Rate limit: 3 запити на акаунт за 10 хвилин. Анонімний користувач форму не бачить. Над формою — пояснення що це відгук про застосунок, а не про керуючу компанію.

## Кроки

- [x] 1. Створити Django app `feedback`: модель `Feedback` (user FK, message, created_at, is_reviewed), міграція
- [x] 2. DRF серіалайзер + `POST /api/v1/feedback/create/` view з `IsAuthenticated` + FeedbackRateThrottle (3/600s)
- [x] 3. Підключити URL в `config/urls.py`, зареєструвати модель в Django Admin
- [x] 4. Email-сповіщення адміну через Celery при новому Feedback записі
- [x] 5. Написати pytest тести: успішна відправка, rate limit, анонімний 401, валідація message (11 тестів)
- [x] 6. RTK Query endpoint `submitFeedback` в `feedbackApiSlice.ts`
- [x] 7. Компонент `FeedbackForm.tsx` — textarea + лічильник + стан подяки після відправки
- [x] 8. Інтегрувати `FeedbackForm` в `/contacts/page.tsx` (тільки для авторизованих, з поясненням)

## Definition of Done

- [x] Всі кроки виконано
- [ ] Тести зелені (pytest) — потрібно запустити на Mac
- [ ] Форма видима тільки авторизованим
- [ ] Запис з'являється в Django Admin після відправки
- [ ] Email надходить адміну
- [ ] PR змерджено в main
- [ ] DEV_PLAN.md видалено
