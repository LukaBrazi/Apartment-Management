# Dev Plan: Сторінка "Оцінити майстра" (/rate-worker)

**Branch:** `feat/rate-worker-page`
**Created:** 2026-04-26

## Задача
Реалізувати сторінку /rate-worker для мешканця де він може оцінити майстра після закритої заявки.

- Показує done-заявки з assigned_to != null
- Не оцінено → форма зірочки + коментар
- Вже оцінено → read-only зірочки + коментар (зелена галочка)
- Empty state якщо список порожній
- Кнопка на дашборді → /rate-worker

## Кроки

- [x] 1. Backend: `ReviewableIssueSerializer` — серіалізатор з полем `my_review`
- [x] 2. Backend: `MyReviewableIssuesAPIView` — GET /issues/my/reviewable/
- [x] 3. Backend: URL `my/reviewable/` в urls.py
- [x] 4. Backend: тести для нового endpoint
- [x] 5. Frontend: тип `ReviewableIssue` в types/index.d.ts
- [x] 6. Frontend: `getMyReviewableIssues` endpoint в issueApiSlice.ts
- [x] 7. Frontend: сторінка `app/(estate)/rate-worker/page.tsx`
- [x] 8. Frontend: QuickActions href /add-rating → /rate-worker

## Definition of Done
- [ ] Всі кроки виконано
- [ ] Тести зелені (pytest)
- [ ] PR змерджено в main
- [ ] DEV_PLAN.md видалено
