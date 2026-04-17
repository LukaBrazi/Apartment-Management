# ApartmentOS — Project Instructions

## Git & Deployment Rules

### Push to main — ЗАБОРОНЕНО без дозволу

**Тільки CEO (Dmytro) має право пушити в `main`.**

- Без прямої команди або спеціальної вказівки — **НЕ пушити в main**.
- Усі зміни оформлюються через feature-гілку → PR → code review → merge CEO.
- Агенти можуть комітити у feature-гілки, але push в `main` — виключно з дозволу CEO.
- Якщо потрібно терміново пушнути — запитай дозвіл у CEO перед push.
- Ніколи не робити репо публічним.

### CI/CD

- Railway "Wait for CI" увімкнено — деплой тільки після зелених тестів.
- GitHub Actions: Django pytest → Playwright E2E → auto-deploy.

## Project Structure

- **Backend:** Django + DRF (`server/`)
- **Frontend:** Next.js 14 App Router (`client/`)
- **E2E Tests:** Playwright (окремий репо `sckandi-e2e`)
- **Domain:** apartmentos.org

## Naming

- Бренд: **ApartmentOS** (не "Skandi Apartments", не "EstateOS")
- Реєстрація користувачів — тільки через адміна (self-registration вимкнена)
- Google OAuth — вимкнений
