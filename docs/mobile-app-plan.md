# ApartmentOS — Mobile App Implementation Plan

**Owner:** Dmytro (CEO)
**Tech lead:** Claude (mobile architecture + implementation pair)
**Created:** 2026-04-19
**Target:** v1.0 в TestFlight / Google Play Internal Testing за 3 тижні від старту
**Status:** План затверджено. Phase 0 стартує на тижні 2026-04-20.

---

## Зміст

1. [Мета](#мета)
2. [Архітектурні рішення](#архітектурні-рішення-зафіксовано)
3. [Тижневий timeline](#тижневий-timeline)
4. [Зовнішні залежності](#зовнішні-залежності-блокери)
5. [Phase 0 — Audit](#phase-0--audit--prep-1д)
6. [Phase 1 — PWA foundation](#phase-1--pwa-foundation-1д)
7. [Phase 2 — Static export + Bearer auth](#phase-2--static-export--bearer-auth-2д)
8. [Phase 3 — Capacitor integration](#phase-3--capacitor-integration-1д)
9. [Phase 4 — Push notifications](#phase-4--push-notifications-3д)
10. [Phase 5 — App Store prep](#phase-5--app-store-prep-2д)
11. [Phase 6 — CI/CD + beta](#phase-6--cicd--beta-4д)
12. [Phase 7 — Submit + launch](#phase-7--submit--launch-1-2-тижні)
13. [Reгістр ризиків](#ризики)
14. [Acceptance criteria](#acceptance-criteria-per-phase)
15. [Appendix: команди](#appendix-a--команди-cheat-sheet)
16. [Appendix: glossary](#appendix-b--glossary)

---

## Мета

Випустити нативний мобільний клієнт ApartmentOS для iOS + Android, використовуючи Capacitor як native shell над існуючим Next.js фронтом. Апка має:

- Пройти App Store Review (Apple 4.2) та Google Play review
- Отримувати push-повідомлення (нові заявки, зміна статусу, нові оголошення, нові перепустки)
- Працювати офлайн у read-only режимі (останні кешовані дані)
- Завантажуватись з локального bundle за ≤ 2 сек (холодний старт)
- Підтримувати 3 ролі (tenant, guard, staff) з тією ж навігацією що і web

---

## Архітектурні рішення (зафіксовано)

### D1: Static export + локальний bundle

Capacitor пакує статичний `out/` Next.js-у в нативний білд. Оновлення контенту через API, оновлення коду — через App Store.

**Плюси:** швидкий cold start, офлайн-капабельність, незалежність від availability серверу.
**Мінуси:** обмежена серверна функціональність Next.js (прибираємо server components з `cookies()`/`headers()`, middleware, API routes).

### D2: Bearer tokens у SecureStorage

Замість httpOnly cookies (які погано переносяться через `capacitor://localhost` origin) — явний `Authorization: Bearer <jwt>` header з токенами у `@capacitor/preferences` (iOS Keychain / Android EncryptedSharedPreferences через плагін).

**Scope цієї зміни:** базовий RTK Query baseQuery, `logged_in` cookie check, ProtectedRoute, login/logout flows.

### D3: Push via firebase-admin + django-push-notifications

Django: `django-push-notifications` (керує моделями `GCMDevice`, `APNSDevice`) + `firebase-admin` SDK для доставки. Frontend: `@capacitor/push-notifications`. Celery task `send_push` диспатчиться з існуючих signals (Issue/Pass/Post/News).

### D4: Dynamic routes → query strings

`output: 'export'` у Next.js 14 App Router вимагає щоб **усі** dynamic params були відомі на build time. Наші `[id]` / `[slug]` роути не можуть бути pre-generated, тому:

- `/issue/[id]` → `/issue?id=<uuid>`
- `/issue/update-issue/[id]` → `/issue/update?id=<uuid>`
- `/news/[slug]` → `/news/detail?slug=<slug>`

Web-URL-и для tenant-ів всередині web-порталу змінюються, але публічного SEO немає (це closed portal), тож регресія прийнятна. Legacy-URLs можна підтримати через Django-side redirect-и на перехідний період.

---

## Тижневий timeline

```
Тиждень 1 (Apr 20 — Apr 26):  Phase 0, Phase 1, Phase 2
Тиждень 2 (Apr 27 — May 03):  Phase 3, Phase 4 (backend + client)
Тиждень 3 (May 04 — May 10):  Phase 5, Phase 6, internal beta
Тиждень 4 (May 11 — May 17):  Phase 7 — submit + Apple/Google review
```

Загальний effort: **~13 людино-днів**.
Застосунок в App Store Review зазвичай займає 1-3 дні, перший реджект закладено у план.

---

## Зовнішні залежності (блокери)

Ці речі потрібно запустити ASAP паралельно з розробкою — вони мають довгий lead-time:

- [ ] **Apple Developer Account** ($99/рік) — реєстрація на [developer.apple.com](https://developer.apple.com). Верифікація юр.особи 1-2 дні. Потрібен Tax ID / ІПН, банківський рахунок.
- [ ] **Google Play Console** ($25 одноразово) — [play.google.com/console](https://play.google.com/console). Верифікація 1-3 дні.
- [ ] **Firebase project** — [console.firebase.google.com](https://console.firebase.google.com). Створити проект `apartmentos-prod`, додати iOS + Android app, отримати:
  - `google-services.json` (Android)
  - `GoogleService-Info.plist` (iOS)
  - FCM Server Key / service account JSON для Django
- [ ] **APNs Authentication Key** — згенерувати в Apple Developer Console (Certificates, IDs & Profiles → Keys), додати в Firebase Console
- [ ] **Apple bundle ID** — зареєструвати `org.apartmentos.app` в Apple Developer → Identifiers
- [ ] **Android package name** — `org.apartmentos.app` в Google Play Console → App creation
- [ ] **Privacy Policy URL** — `https://apartmentos.org/privacy` (статична сторінка, треба створити)
- [ ] **Terms of Service URL** — `https://apartmentos.org/terms` (теж нова)
- [ ] **Support URL** — `https://apartmentos.org/support` або email `support@apartmentos.org`
- [ ] **Скріншоти** — 6.7" iPhone (1290×2796), 6.5" iPhone (1242×2688), optional 5.5" iPhone, Android phone (1080×1920+), Android tablet — по 3-5 штук кожного
- [ ] **App іконка 1024×1024** без прозорості та без alpha для iOS, 512×512 для Android

---

## Phase 0 — Audit + prep (1д)

**Мета:** точно знати що ламається при переході на `output: 'export'` і скласти список передумов для Phase 2.

### 0.1 Dynamic route inventory

- [ ] Знайти всі динамічні сегменти:
  ```bash
  find client/src/app -type d -name '[*]' -o -type d -name '\[*\]'
  ```
- [ ] Документувати кожен: endpoint API, чи використовується query/params
- [ ] Для кожного прийняти рішення: query-string refactor VS pre-fetch-at-build (для малих finite dataset як-от новини можна pre-fetch)
- [ ] Результат: `docs/dynamic-routes-plan.md` з таблицею

### 0.2 Server-only APIs inventory

- [ ] `grep -r "from 'next/headers'" client/src` → список файлів що юзають `cookies()` / `headers()` server-side
- [ ] `grep -r "'use server'" client/src` → список server actions
- [ ] `ls client/src/app/api/` → API routes (якщо є)
- [ ] `ls client/middleware.ts` → middleware (має бути винесене або видалене)
- [ ] Для кожного вирішити: перенести логіку на Django / зробити client-side

### 0.3 Baseline метрики

- [ ] `cd client && npm run build` → зафіксувати поточний розмір bundle
- [ ] Lighthouse audit на `https://apartmentos.org/welcome` (mobile profile): PWA score, Performance, Accessibility — записати baseline для порівняння
- [ ] `ls -lh client/.next/static/chunks/*.js | sort -k5 -h | tail -10` → top 10 найважчих чанків

### 0.4 Environment audit

- [ ] Список `process.env.*` в client: які build-time, які runtime
- [ ] У Capacitor апці runtime env-ів не існує — усе має бути build-time (через `NEXT_PUBLIC_*`)
- [ ] Перевірити що `NEXT_PUBLIC_API_URL` або аналог правильно налаштований

### 0.5 Auth flow mapping

- [ ] Прочитати `client/src/components/shared/ProtectedRoutes.tsx`
- [ ] Прочитати `client/src/lib/redux/features/auth/*`
- [ ] Документувати:
  - Як виставляється `logged_in` cookie
  - Як проходить login/logout
  - Де зчитується JWT
  - Як працює refresh
- [ ] Вирішити: які файли потрібно змінити у Phase 2 для Bearer auth

### Deliverables Phase 0

- [ ] `docs/dynamic-routes-plan.md` — таблиця з рішеннями по кожному dynamic route
- [ ] `docs/server-apis-inventory.md` — список server-only usage з планом міграції
- [ ] `docs/auth-migration-plan.md` — точний список файлів для Bearer-auth refactor
- [ ] GitHub issue "Phase 0 audit complete" з цими вкладеннями

---

## Phase 1 — PWA foundation (1д)

Базис для Capacitor і паралельно бонус для web-користувачів (Add to Home Screen в мобільному браузері).

### 1.1 Icon + splash generation

- [ ] Створити master-іконку `brand/icon-master.svg` 1024×1024, без прозорості, з ApartmentOS logo на brand-primary `#2F6FED`
- [ ] Встановити генератор:
  ```bash
  cd client && npm i -D @capacitor/assets sharp
  ```
- [ ] Створити `client/public/resources/icon.png` (1024×1024) + `splash.png` (2732×2732) і splash-dark
- [ ] Згенерувати всі розміри:
  ```bash
  npx @capacitor/assets generate --iconBackgroundColor '#2F6FED' --splashBackgroundColor '#FFFFFF' --splashBackgroundColorDark '#0F1923'
  ```
- [ ] Перевірити що створились:
  - `android/app/src/main/res/mipmap-*/`
  - `ios/App/App/Assets.xcassets/AppIcon.appiconset/`
  - `ios/App/App/Assets.xcassets/Splash.imageset/`

### 1.2 Web manifest

- [ ] Створити `client/public/manifest.json`:
  ```json
  {
    "name": "ApartmentOS",
    "short_name": "ApartmentOS",
    "description": "Портал управління багатоквартирним будинком",
    "start_url": "/welcome",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#FFFFFF",
    "theme_color": "#2F6FED",
    "lang": "uk",
    "icons": [
      { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
      { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" },
      { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
    ]
  }
  ```
- [ ] У `client/src/app/layout.tsx` додати до `<head>`:
  ```tsx
  import type { Viewport, Metadata } from "next";
  export const metadata: Metadata = {
    manifest: "/manifest.json",
    appleWebApp: {
      capable: true,
      statusBarStyle: "default",
      title: "ApartmentOS",
    },
    // ...existing
  };
  ```

### 1.3 Service worker + offline

- [ ] Встановити `next-pwa` (сумісний з App Router в обмеженому режимі):
  ```bash
  npm i next-pwa
  ```
- [ ] Або альтернатива: власний `public/sw.js` + реєстрація в `layout.tsx` (простіше для static export)
- [ ] Стратегії:
  - `CacheFirst` для static assets (`/_next/static/*`, `/icons/*`, `/assets/*`)
  - `NetworkFirst` з fallback на cache для `/api/v1/*`
  - Offline page: `public/offline.html` з кнопкою "Спробувати ще раз"
- [ ] Додати `client/public/offline.html` — мінімальний HTML з логотипом + "Немає зʼєднання"

### 1.4 Apple PWA meta

- [ ] `client/src/app/layout.tsx`:
  ```tsx
  // Додати в <head> через Next 14 metadata API:
  appleWebApp: { capable: true, title: "ApartmentOS" }
  ```
- [ ] Створити apple-touch-icon у всіх розмірах (180×180 основний):
  ```bash
  # через @capacitor/assets вже має бути
  ls client/public/icons/apple-touch-icon*.png
  ```

### 1.5 Lighthouse PWA verification

- [ ] `npm run build && npm run start`
- [ ] Chrome DevTools → Lighthouse → Mobile → PWA audit
- [ ] Мета: PWA score ≥ 90, Installable = yes
- [ ] Зафіксувати результати в `docs/lighthouse-baseline.md`

### Deliverables Phase 1

- [ ] Working PWA: можна додати на home screen з мобільного Safari / Chrome
- [ ] Offline fallback показує `offline.html`
- [ ] Іконки + splash готові для всіх розмірів
- [ ] Lighthouse PWA ≥ 90

---

## Phase 2 — Static export + Bearer auth (2д)

### 2.1 next.config.js для static export

- [ ] Відкрити `client/next.config.js`:
  ```js
  /** @type {import('next').NextConfig} */
  module.exports = {
    output: "export",
    images: { unoptimized: true },           // next/image не має optimizer у export
    trailingSlash: true,                     // критично для Capacitor WebView routing
    distDir: ".next",                        // залишаємо, `out/` генерується окремо
    // reactStrictMode, etc.
  };
  ```
- [ ] Перевірити що `webDir` у майбутньому `capacitor.config.ts` буде `out/`
- [ ] Задокументувати: `next dev` залишається для локальної розробки, `next build` тепер === `next build && next export` (export вбудовано в output: 'export')

### 2.2 Dynamic routes refactor (query strings)

#### 2.2.1 /issue/[id] → /issue

- [ ] Створити `client/src/app/(estate)/issue/page.tsx` (новий):
  ```tsx
  "use client";
  import { useSearchParams } from "next/navigation";
  import IssueDetails from "@/components/issue/IssueDetails";
  import { Suspense } from "react";
  function IssuePageInner() {
    const id = useSearchParams().get("id") ?? "";
    return <IssueDetails params={{ id }} />;
  }
  export default function IssuePage() {
    return <Suspense><IssuePageInner /></Suspense>;
  }
  ```
- [ ] Видалити `client/src/app/(estate)/issue/[id]/page.tsx`
- [ ] У всіх `<Link href={\`/issue/\${id}\`}>` замінити на `<Link href={\`/issue?id=\${id}\`}>`:
  ```bash
  grep -rn '/issue/${' client/src/
  grep -rn '"/issue/' client/src/
  ```

#### 2.2.2 /issue/update-issue/[id] → /issue/update

- [ ] Ідентична структура. Створити `client/src/app/(estate)/issue/update/page.tsx`
- [ ] Видалити `client/src/app/(estate)/issue/update-issue/[id]/page.tsx`
- [ ] Оновити посилання: `IssueDetails.tsx:105` поточне `/issue/update-issue/${id}` → `/issue/update?id=${id}`

#### 2.2.3 /news/[slug] → /news/detail

- [ ] Створити `client/src/app/(estate)/news/detail/page.tsx` (reuse existing component)
- [ ] Видалити `client/src/app/(estate)/news/[slug]/page.tsx`
- [ ] Оновити посилання у `client/src/app/(estate)/news/page.tsx` з `/news/${item.slug}` → `/news/detail?slug=${item.slug}`

#### 2.2.4 Інші dynamic routes

- [ ] Знайти решту через `find client/src/app -type d \\( -name '[[]*[]]' \\)` і повторити pattern

### 2.3 Server-only API removal

- [ ] Якщо є `middleware.ts` — перенести логіку в `ProtectedRoute` client component
- [ ] Якщо є `app/api/*` — перенести на Django endpoints
- [ ] Видалити `'use server'` action файли (якщо знайдено в Phase 0)

### 2.4 Bearer auth refactor

#### 2.4.1 Token storage helper

- [ ] Створити `client/src/lib/auth/tokenStorage.ts`:
  ```ts
  import { Preferences } from "@capacitor/preferences"; // встановимо у Phase 3
  // На web fallback у localStorage
  const isCapacitor = typeof (window as any)?.Capacitor?.isNativePlatform === "function"
    && (window as any).Capacitor.isNativePlatform();

  export const tokenStorage = {
    async get(key: "access" | "refresh"): Promise<string | null> {
      if (isCapacitor) return (await Preferences.get({ key })).value;
      return localStorage.getItem(key);
    },
    async set(key: "access" | "refresh", value: string) {
      if (isCapacitor) await Preferences.set({ key, value });
      else localStorage.setItem(key, value);
    },
    async clear() {
      if (isCapacitor) { await Preferences.remove({ key: "access" }); await Preferences.remove({ key: "refresh" }); }
      else { localStorage.removeItem("access"); localStorage.removeItem("refresh"); }
    },
  };
  ```

#### 2.4.2 RTK Query baseQuery

- [ ] Оновити `client/src/lib/redux/services/apiSlice.ts` (або аналог):
  ```ts
  const rawBaseQuery = fetchBaseQuery({
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "https://api.apartmentos.org",
    prepareHeaders: async (headers) => {
      const token = await tokenStorage.get("access");
      if (token) headers.set("Authorization", `Bearer ${token}`);
      return headers;
    },
    credentials: "omit", // не покладаємося на cookies у native
  });

  // Інтерцептор для 401 → refresh
  const baseQueryWithRefresh: BaseQueryFn = async (args, api, extraOptions) => {
    let result = await rawBaseQuery(args, api, extraOptions);
    if (result.error?.status === 401) {
      const refresh = await tokenStorage.get("refresh");
      if (refresh) {
        const refreshed = await rawBaseQuery(
          { url: "/api/v1/auth/jwt/refresh/", method: "POST", body: { refresh } },
          api, extraOptions
        );
        if (refreshed.data) {
          await tokenStorage.set("access", (refreshed.data as any).access);
          result = await rawBaseQuery(args, api, extraOptions);
        } else {
          await tokenStorage.clear();
          api.dispatch(setLoggedOut());
        }
      }
    }
    return result;
  };
  ```

#### 2.4.3 Login flow

- [ ] Знайти login form submit (скоріше `components/forms/auth/LoginForm.tsx`)
- [ ] При успішній авторизації:
  ```ts
  await tokenStorage.set("access", response.access);
  await tokenStorage.set("refresh", response.refresh);
  // прибрати все що писало в cookies
  router.push("/welcome");
  ```

#### 2.4.4 Logout flow

- [ ] Замість `setCookie("logged_in", "")` — `await tokenStorage.clear()`
- [ ] Видалити `cookies-next` залежність якщо ніде більше не юзається

#### 2.4.5 ProtectedRoute refactor

- [ ] `client/src/components/shared/ProtectedRoutes.tsx`:
  ```tsx
  useEffect(() => {
    tokenStorage.get("access").then((t) => {
      if (!t) router.replace("/login");
      else setChecked(true);
    });
  }, []);
  ```
- [ ] Прибрати `getCookie("logged_in")` логіку

#### 2.4.6 Django CORS

- [ ] Перевірити `server/config/settings/*.py` — `CORS_ALLOWED_ORIGINS` має містити:
  - `capacitor://localhost`
  - `http://localhost` (Android WebView дефолт)
  - `ionic://localhost` (legacy fallback)
- [ ] `CORS_ALLOW_CREDENTIALS = False` вже для Bearer-моделі (хоча CORS credentials не заважає, просто не потрібно)
- [ ] Додати `Authorization` у `CORS_ALLOW_HEADERS` якщо його там немає

### 2.5 Build verification

- [ ] `cd client && npm run build`
- [ ] Очікуваний результат: папка `client/out/` з `index.html` + статичними ресурсами
- [ ] Перевірити що з'явилась `out/issue/index.html` (не `out/issue/[id]/index.html`)
- [ ] Локальний serve: `npx serve out/ -p 3001` — відкрити в браузері, протестувати:
  - [ ] Login flow
  - [ ] Dashboard рендерить
  - [ ] Deep link `http://localhost:3001/issue?id=<real-uuid>` рендерить детальку
  - [ ] Logout

### Deliverables Phase 2

- [ ] `npm run build` стабільно генерує `client/out/`
- [ ] Smoke test у Safari/Chrome на `http://localhost:3001` проходить end-to-end
- [ ] Bearer auth працює (перевірено в Network tab: `Authorization: Bearer ...` замість Cookie)
- [ ] Commit: `feat(frontend): static export + bearer auth refactor`

---

## Phase 3 — Capacitor integration (1д)

### 3.1 Install

- [ ] `cd client && npm i @capacitor/core @capacitor/cli`
- [ ] `npx cap init "ApartmentOS" org.apartmentos.app --web-dir=out`
- [ ] Перевірити згенерований `client/capacitor.config.ts`:
  ```ts
  import type { CapacitorConfig } from "@capacitor/cli";
  const config: CapacitorConfig = {
    appId: "org.apartmentos.app",
    appName: "ApartmentOS",
    webDir: "out",
    server: {
      androidScheme: "https",
      cleartext: false,
      // allowNavigation: ["apartmentos.org", "api.apartmentos.org"],
    },
    plugins: {
      SplashScreen: {
        launchShowDuration: 1500,
        backgroundColor: "#FFFFFF",
        androidSplashResourceName: "splash",
        splashFullScreen: false,
        splashImmersive: false,
      },
      StatusBar: {
        style: "DARK",
        backgroundColor: "#FFFFFF",
      },
      Keyboard: {
        resize: "body",
        style: "DARK",
        resizeOnFullScreen: true,
      },
    },
  };
  export default config;
  ```

### 3.2 Add platforms

- [ ] macOS + Xcode required for iOS: `npx cap add ios`
- [ ] Android Studio required: `npx cap add android`
- [ ] `npm run build && npx cap sync`
- [ ] Результат: дві нові папки `client/ios/` + `client/android/`
- [ ] Додати в `.gitignore`:
  ```
  client/ios/App/App/public/
  client/android/app/src/main/assets/public/
  client/android/.gradle/
  client/android/app/build/
  client/ios/App/Pods/
  ```

### 3.3 Essential plugins

- [ ] ```bash
  cd client && npm i \
    @capacitor/preferences \
    @capacitor/splash-screen \
    @capacitor/status-bar \
    @capacitor/keyboard \
    @capacitor/app \
    @capacitor/network \
    @capacitor/browser
  npx cap sync
  ```

### 3.4 App-level hooks

- [ ] Створити `client/src/lib/capacitor/init.ts`:
  ```ts
  import { App } from "@capacitor/app";
  import { StatusBar, Style } from "@capacitor/status-bar";
  import { Capacitor } from "@capacitor/core";

  export async function initCapacitor() {
    if (!Capacitor.isNativePlatform()) return;

    await StatusBar.setStyle({ style: Style.Light });
    await StatusBar.setBackgroundColor({ color: "#FFFFFF" });

    // Android hardware back → web history
    App.addListener("backButton", ({ canGoBack }) => {
      if (canGoBack) window.history.back();
      else App.exitApp();
    });

    // Deep links з push notifications
    App.addListener("appUrlOpen", (event) => {
      const url = new URL(event.url);
      const path = url.pathname + url.search;
      window.location.href = path;
    });
  }
  ```
- [ ] Викликати в `client/src/app/layout.tsx` (client component wrapper) або в useEffect root провайдера

### 3.5 Safe area handling

- [ ] Додати в `client/src/app/globals.css`:
  ```css
  @supports (padding: env(safe-area-inset-top)) {
    .cap-safe-top { padding-top: env(safe-area-inset-top); }
    .cap-safe-bottom { padding-bottom: env(safe-area-inset-bottom); }
  }
  ```
- [ ] Застосувати `.cap-safe-top` до MobileHeader + `.cap-safe-bottom` до BottomNav

### 3.6 iOS scheme handler

- [ ] Відкрити `client/ios/App/App/Info.plist`, переконатися що є:
  ```xml
  <key>CFBundleDisplayName</key>
  <string>ApartmentOS</string>
  <key>UILaunchStoryboardName</key>
  <string>CAPLaunchScreen</string>
  ```

### 3.7 Android permissions baseline

- [ ] `client/android/app/src/main/AndroidManifest.xml`:
  ```xml
  <uses-permission android:name="android.permission.INTERNET" />
  <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
  ```

### 3.8 Smoke test в симуляторах

- [ ] iOS: `npx cap open ios` → у Xcode обрати iPhone 15 simulator → Run
  - [ ] Splash screen показується
  - [ ] Dashboard вантажиться
  - [ ] Login flow працює
  - [ ] Back button (swipe) працює
- [ ] Android: `npx cap open android` → у Android Studio обрати Pixel 7 emulator → Run
  - [ ] Splash screen показується
  - [ ] Hardware back button працює
  - [ ] Login flow працює

### Deliverables Phase 3

- [ ] iOS app запускається в симуляторі, виконує весь основний flow
- [ ] Android app запускається в емуляторі, виконує весь основний flow
- [ ] Commit: `feat(mobile): capacitor integration with ios + android platforms`

---

## Phase 4 — Push notifications (3д)

### 4.1 Backend: модель DeviceToken

- [ ] Нова міграція в `server/core_apps/notifications/`:
  ```bash
  cd server && python manage.py startapp push_devices  # або додати до notifications
  ```
- [ ] Модель у `core_apps/notifications/models.py`:
  ```python
  class DeviceToken(TimeStampedModel):
      user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="device_tokens")
      platform = models.CharField(max_length=8, choices=[("ios", "iOS"), ("android", "Android")])
      token = models.TextField(unique=True)
      active = models.BooleanField(default=True)
      last_used_at = models.DateTimeField(auto_now=True)
      app_version = models.CharField(max_length=32, blank=True)

      class Meta:
          indexes = [models.Index(fields=["user", "active"])]
  ```
- [ ] Міграція:
  ```bash
  python manage.py makemigrations notifications
  python manage.py migrate
  ```

### 4.2 Backend: register endpoint

- [ ] Serializer + view:
  ```python
  # core_apps/notifications/api/device_views.py
  class DeviceTokenSerializer(serializers.ModelSerializer):
      class Meta:
          model = DeviceToken
          fields = ["platform", "token", "app_version"]

  class DeviceRegisterAPIView(CreateAPIView):
      serializer_class = DeviceTokenSerializer
      permission_classes = [IsAuthenticated]

      def perform_create(self, serializer):
          # Upsert: один і той же token може бути перереєстрований
          DeviceToken.objects.update_or_create(
              token=serializer.validated_data["token"],
              defaults={
                  "user": self.request.user,
                  "platform": serializer.validated_data["platform"],
                  "active": True,
                  "app_version": serializer.validated_data.get("app_version", ""),
              },
          )

  class DeviceUnregisterAPIView(GenericAPIView):
      permission_classes = [IsAuthenticated]
      def post(self, request):
          DeviceToken.objects.filter(
              user=request.user, token=request.data.get("token")
          ).update(active=False)
          return Response(status=204)
  ```
- [ ] URLs:
  ```python
  # core_apps/notifications/urls.py
  path("devices/register/", DeviceRegisterAPIView.as_view(), name="device-register"),
  path("devices/unregister/", DeviceUnregisterAPIView.as_view(), name="device-unregister"),
  ```

### 4.3 Backend: firebase-admin

- [ ] Додати у `server/requirements.txt`:
  ```
  firebase-admin>=6.5.0
  ```
- [ ] `pip install -r requirements.txt`
- [ ] Зберегти Firebase service-account JSON через Railway secrets як env var `FIREBASE_CREDENTIALS_JSON` (raw JSON string)
- [ ] У `config/settings/base.py`:
  ```python
  FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS_JSON")
  ```
- [ ] `core_apps/notifications/push.py`:
  ```python
  import json, firebase_admin
  from firebase_admin import credentials, messaging
  from django.conf import settings

  _app = None
  def _get_app():
      global _app
      if _app: return _app
      if not settings.FIREBASE_CREDENTIALS:
          raise ImproperlyConfigured("FIREBASE_CREDENTIALS_JSON not set")
      cred = credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS))
      _app = firebase_admin.initialize_app(cred)
      return _app

  def send_push(user, title, body, data=None):
      _get_app()
      tokens = list(DeviceToken.objects.filter(user=user, active=True).values_list("token", flat=True))
      if not tokens: return
      msg = messaging.MulticastMessage(
          tokens=tokens,
          notification=messaging.Notification(title=title, body=body),
          data={k: str(v) for k, v in (data or {}).items()},
      )
      response = messaging.send_multicast(msg)
      # Деактивувати "invalid token" tokens
      for idx, result in enumerate(response.responses):
          if not result.success and result.exception.code in ("UNREGISTERED", "INVALID_ARGUMENT"):
              DeviceToken.objects.filter(token=tokens[idx]).update(active=False)
  ```

### 4.4 Backend: Celery task + signals

- [ ] `core_apps/notifications/tasks.py`:
  ```python
  from celery import shared_task
  from .push import send_push as _send
  from django.contrib.auth import get_user_model

  @shared_task(rate_limit="50/s", retry_backoff=True, max_retries=3)
  def send_push_task(user_id, title, body, data=None):
      user = get_user_model().objects.filter(pk=user_id).first()
      if not user: return
      _send(user, title, body, data)
  ```
- [ ] Вивести signal-based dispatch у `core_apps/issues/signals.py`:
  ```python
  @receiver(post_save, sender=Issue)
  def notify_on_issue_created(sender, instance, created, **kwargs):
      if not created: return
      # Сповіщаємо assignee (dispatcher/worker)
      if instance.assigned_to_id:
          send_push_task.delay(
              instance.assigned_to_id,
              "Нова заявка",
              instance.title[:80],
              {"screen": "issue", "id": str(instance.id)},
          )

  @receiver(pre_save, sender=Issue)
  def capture_status_change(sender, instance, **kwargs):
      if instance.pk:
          old = Issue.objects.filter(pk=instance.pk).first()
          if old and old.status != instance.status:
              send_push_task.delay(
                  instance.reported_by_id,
                  "Статус вашої заявки змінено",
                  f"{instance.title[:50]}: {instance.get_status_display()}",
                  {"screen": "issue", "id": str(instance.id)},
              )
  ```
- [ ] Аналогічні signals для:
  - `VehiclePass` (new → guard, closed → tenant)
  - `Post` (pinned → all tenants в org)
  - `News` (new published → all members of org)

### 4.5 Frontend: plugin install

- [ ] ```bash
  cd client && npm i @capacitor/push-notifications
  npx cap sync
  ```

### 4.6 Frontend: iOS-специфіка

- [ ] `client/ios/App/App/Info.plist`:
  ```xml
  <key>UIBackgroundModes</key>
  <array>
    <string>remote-notification</string>
  </array>
  ```
- [ ] Додати APS capability: Xcode → App target → Signing & Capabilities → + Capability → Push Notifications
- [ ] Під APS key з Apple Developer має бути в Firebase (завантажено як частину зовнішніх залежностей)

### 4.7 Frontend: Android-специфіка

- [ ] Завантажити `google-services.json` → `client/android/app/google-services.json`
- [ ] `client/android/build.gradle` (project-level) → додати `classpath 'com.google.gms:google-services:4.4.0'`
- [ ] `client/android/app/build.gradle` → `apply plugin: 'com.google.gms.google-services'`
- [ ] `AndroidManifest.xml` → `<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />`

### 4.8 Frontend: registration + handlers

- [ ] `client/src/lib/capacitor/push.ts`:
  ```ts
  import { PushNotifications } from "@capacitor/push-notifications";
  import { Capacitor } from "@capacitor/core";
  import { apiSlice } from "@/lib/redux/services/apiSlice";

  export async function registerPush(dispatch: AppDispatch) {
    if (!Capacitor.isNativePlatform()) return;

    const perm = await PushNotifications.requestPermissions();
    if (perm.receive !== "granted") return;

    await PushNotifications.register();

    PushNotifications.addListener("registration", async ({ value: token }) => {
      await dispatch(apiSlice.endpoints.registerDevice.initiate({
        platform: Capacitor.getPlatform() === "ios" ? "ios" : "android",
        token,
        app_version: process.env.NEXT_PUBLIC_APP_VERSION ?? "dev",
      }));
    });

    PushNotifications.addListener("pushNotificationReceived", (notification) => {
      // Foreground: показати власний toast
      toast.info(notification.title ?? "Нове повідомлення");
    });

    PushNotifications.addListener("pushNotificationActionPerformed", ({ notification }) => {
      // User tapped push → deep link
      const data = notification.data;
      if (data.screen === "issue" && data.id) {
        window.location.href = `/issue?id=${data.id}`;
      } else if (data.screen === "pass" && data.id) {
        window.location.href = `/guard-portal`;
      } else if (data.screen === "news" && data.slug) {
        window.location.href = `/news/detail?slug=${data.slug}`;
      }
    });
  }
  ```
- [ ] Додати RTK endpoint:
  ```ts
  registerDevice: builder.mutation<void, { platform: "ios" | "android"; token: string; app_version: string }>({
    query: (body) => ({ url: "/api/v1/notifications/devices/register/", method: "POST", body }),
  }),
  ```
- [ ] Викликати `registerPush(dispatch)` у `layout.tsx` після login (не раніше — permission має запитуватись коли користувач вже увійшов)

### 4.9 E2E тест push (ручний)

- [ ] iOS: прошити тестовий білд на фізичний пристрій (в симуляторі push notifications не приходять)
- [ ] Android: емулятор з Google Play services підтримує FCM push — можна тестувати
- [ ] У Firebase Console → Cloud Messaging → Send test message → обрати token зі списку
- [ ] Перевірити:
  - [ ] Push приходить при killed app
  - [ ] Push приходить при background
  - [ ] Toast показується при foreground
  - [ ] Tap на push відкриває правильну сторінку

### Deliverables Phase 4

- [ ] Push реєстрація працює на обох платформах
- [ ] Backend signals відправляють push при створенні/зміні Issue/Pass
- [ ] Deep link з push відкриває правильну сторінку
- [ ] Commit: `feat(push): firebase push notifications end-to-end`

---

## Phase 5 — App Store prep (2д)

### 5.1 Legal pages

- [ ] Створити `server/templates/legal/privacy.html` (або Django view + template)
  - [ ] Перелік даних що збираємо: email, ім'я, номер квартири, avatar, push device token
  - [ ] Цілі обробки
  - [ ] Права суб'єктів даних (GDPR + Ukraine DPA)
  - [ ] Контакт DPO: `privacy@apartmentos.org`
- [ ] `server/templates/legal/terms.html` — ToS для мешканців
- [ ] `server/templates/legal/support.html` — інструкції + контакт
- [ ] Додати URL-и `/privacy`, `/terms`, `/support` в Django
- [ ] Verify URL-и публічно доступні без логіну (Apple reviewer їх вимагатиме)

### 5.2 App Store Connect listing

- [ ] [appstoreconnect.apple.com](https://appstoreconnect.apple.com) → Create new app
- [ ] Bundle ID: `org.apartmentos.app`
- [ ] SKU: `apartmentos-ios-v1`
- [ ] Primary language: Ukrainian
- [ ] Category: Productivity / Lifestyle (залежить від позиціонування)
- [ ] Заповнити:
  - [ ] App Name (30 chars): "ApartmentOS"
  - [ ] Subtitle (30 chars): "Портал вашого ЖК"
  - [ ] Description (4000 chars) — напишемо в окремому doc
  - [ ] Keywords (100 chars): "ЖК, керування, квартира, заявки, перепустка, мешканець"
  - [ ] Promotional text (170 chars)
  - [ ] Support URL
  - [ ] Privacy Policy URL
  - [ ] Marketing URL (optional)
- [ ] Age rating: 4+ (немає контенту 17+)
- [ ] Content Rights: power of attorney для третіх сторін = No

### 5.3 App Privacy (App Store)

- [ ] Apple вимагає декларацію даних:
  - [ ] Email: Linked to User, Used for App Functionality
  - [ ] Name: Linked to User, Used for App Functionality
  - [ ] Phone Number: Linked to User, if collected
  - [ ] Photos: Linked to User (avatar)
  - [ ] Device ID / Push Token: Linked to User, Used for App Functionality
- [ ] Не збираємо: tracking cookies, location, financial info, health

### 5.4 iOS Info.plist purpose strings

- [ ] `client/ios/App/App/Info.plist`:
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>Щоб додати фото до аватара або заявки</string>
  <key>NSPhotoLibraryUsageDescription</key>
  <string>Щоб обрати зображення з галереї для аватара</string>
  <key>NSUserTrackingUsageDescription</key>
  <string>ApartmentOS не відстежує користувачів між застосунками</string>
  ```

### 5.5 Google Play Console listing

- [ ] Apps → Create app
- [ ] App name: ApartmentOS
- [ ] Default language: Ukrainian
- [ ] App/game: App
- [ ] Free/paid: Free
- [ ] Declarations: accept Play Developer Program Policies
- [ ] Заповнити Main store listing:
  - [ ] Short description (80 chars)
  - [ ] Full description (4000 chars)
  - [ ] App icon (512×512)
  - [ ] Feature graphic (1024×500)
  - [ ] Phone screenshots ×4
  - [ ] Tablet screenshots ×4 (optional але краще так)
- [ ] Data safety section (аналог Apple App Privacy) — заповнити
- [ ] Target audience: Adults

### 5.6 Скріншоти генерація

- [ ] Створити script `client/scripts/gen-screenshots.sh`:
  - Запускає dev-build на конкретних розмірах viewport
  - Playwright screenshot на:
    - `/welcome` — dashboard
    - `/report-issue` — форма
    - `/issue?id=<demo>` — деталька
    - `/news` — новини
    - `/profile` — профіль
  - Розміри: 1290×2796 (6.7"), 1242×2688 (6.5"), 1080×2340 (Android phone), 2048×2732 (Android tablet)
- [ ] Згенерувати 4-5 скрінів на розмір
- [ ] (Опціонально) накласти рамки iPhone/Android через [screenshots.pro](https://screenshots.pro) або Figma шаблон

### 5.7 Demo-акаунт для review

- [ ] Для Apple reviewer потрібні demo credentials
- [ ] Створити seed-акаунт `apple-review@apartmentos.org` / `TestReview2026!`
- [ ] Переконатися що цей акаунт бачить демо-контент (есть заявки, пасс, новини)
- [ ] Додати в App Store Connect → App Information → App Review Information:
  - Username, Password
  - Notes: "Demo tenant account. Sign in with provided creds to see all features."

### 5.8 App icon + splash fine-tuning

- [ ] iOS icon 1024×1024 без rounded corners (iOS додає сам), без alpha
- [ ] Android icon 512×512 adaptive (foreground + background)
- [ ] Пересвідчитися що `@capacitor/assets` згенерувало всі розміри
- [ ] Візуальна перевірка в симуляторах (іконка виглядає добре на домашньому екрані)

### Deliverables Phase 5

- [ ] Privacy / Terms / Support сторінки опубліковані на apartmentos.org
- [ ] App Store Connect listing заповнений (без білда ще)
- [ ] Google Play Console listing заповнений
- [ ] Скріншоти готові в потрібних розмірах
- [ ] Demo reviewer account створений
- [ ] Commit: `chore(legal): privacy + terms + support pages`

---

## Phase 6 — CI/CD + beta (4д)

### 6.1 Fastlane setup (iOS)

- [ ] `cd client/ios && bundle init`
- [ ] `Gemfile`:
  ```ruby
  gem "fastlane"
  ```
- [ ] `bundle install`
- [ ] `bundle exec fastlane init` → Deliver + Match
- [ ] Створити `ios/fastlane/Fastfile`:
  ```ruby
  default_platform(:ios)
  platform :ios do
    desc "Build and upload to TestFlight"
    lane :beta do
      match(type: "appstore", readonly: is_ci)
      build_app(scheme: "App", workspace: "App.xcworkspace")
      upload_to_testflight(skip_waiting_for_build_processing: true)
    end
  end
  ```
- [ ] Налаштувати Match: приватний репо для certs+profiles (або local-git режим на початку)

### 6.2 Fastlane setup (Android)

- [ ] `client/android/fastlane/Fastfile`:
  ```ruby
  default_platform(:android)
  platform :android do
    desc "Build and upload to Play Internal track"
    lane :internal do
      gradle(task: "clean bundleRelease")
      upload_to_play_store(track: "internal", aab: "app/build/outputs/bundle/release/app-release.aab")
    end
  end
  ```
- [ ] Keystore:
  ```bash
  keytool -genkey -v -keystore apartmentos-release.keystore -alias apartmentos -keyalg RSA -keysize 2048 -validity 10000
  ```
- [ ] Зберегти keystore в password manager + GitHub Actions secrets
- [ ] Google Play service account JSON → GH secret `GOOGLE_PLAY_JSON`

### 6.3 GitHub Actions — iOS build

- [ ] `.github/workflows/mobile-ios.yml`:
  ```yaml
  name: iOS build
  on:
    push:
      branches: [main]
      paths: [client/**]
    workflow_dispatch:
  jobs:
    build:
      runs-on: macos-14
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-node@v4
          with: { node-version: 20 }
        - run: cd client && npm ci
        - run: cd client && npm run build
        - run: cd client && npx cap sync ios
        - uses: ruby/setup-ruby@v1
          with: { ruby-version: 3.2, bundler-cache: true, working-directory: client/ios }
        - env:
            MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
            MATCH_GIT_URL: ${{ secrets.MATCH_GIT_URL }}
            FASTLANE_USER: ${{ secrets.APPLE_ID }}
            FASTLANE_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}
          run: cd client/ios && bundle exec fastlane beta
  ```

### 6.4 GitHub Actions — Android build

- [ ] `.github/workflows/mobile-android.yml`:
  ```yaml
  name: Android build
  on:
    push:
      branches: [main]
      paths: [client/**]
    workflow_dispatch:
  jobs:
    build:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-java@v4
          with: { distribution: temurin, java-version: 17 }
        - uses: actions/setup-node@v4
          with: { node-version: 20 }
        - run: cd client && npm ci
        - run: cd client && npm run build
        - run: cd client && npx cap sync android
        - env:
            ANDROID_KEYSTORE_B64: ${{ secrets.ANDROID_KEYSTORE_B64 }}
            ANDROID_KEYSTORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
            GOOGLE_PLAY_JSON: ${{ secrets.GOOGLE_PLAY_JSON }}
          run: |
            echo $ANDROID_KEYSTORE_B64 | base64 -d > client/android/apartmentos-release.keystore
            echo $GOOGLE_PLAY_JSON > client/android/fastlane/google-play.json
        - uses: ruby/setup-ruby@v1
          with: { ruby-version: 3.2, bundler-cache: true, working-directory: client/android }
        - run: cd client/android && bundle exec fastlane internal
  ```

### 6.5 Secrets audit

- [ ] GitHub → Settings → Secrets → Actions:
  - [ ] `APPLE_ID` — Apple Developer email
  - [ ] `APPLE_APP_PASSWORD` — App-specific password
  - [ ] `MATCH_PASSWORD` — шифрування сертифікатів
  - [ ] `MATCH_GIT_URL` — приватний git для Match certs
  - [ ] `ANDROID_KEYSTORE_B64` — base64 keystore
  - [ ] `ANDROID_KEYSTORE_PASSWORD`
  - [ ] `GOOGLE_PLAY_JSON` — сервісний JSON

### 6.6 Internal beta testing

- [ ] TestFlight:
  - [ ] Додати Dmytro (CEO) + 2-3 тестери як Internal Testers
  - [ ] Internal testing стартує одразу, без review
  - [ ] Роздати посилання TestFlight
- [ ] Google Play Internal:
  - [ ] Додати email тестерів в Google Group
  - [ ] Роздати opt-in URL
- [ ] Smoke tests на реальних пристроях:
  - [ ] Login
  - [ ] Dashboard
  - [ ] Submit issue
  - [ ] Request pass (tenant) / close pass (guard)
  - [ ] Receive push при новій заявці
  - [ ] Tap push → deep link
  - [ ] Offline behavior

### 6.7 Crash reporting (необов'язково для v1, бажано)

- [ ] Sentry iOS + Android SDK через `@sentry/capacitor`
- [ ] Source maps upload у CI

### Deliverables Phase 6

- [ ] Кожен push в main автоматично створює новий TestFlight білд + Play Internal білд
- [ ] Internal тестери отримують нові білди без ручної участі
- [ ] Minimum 3 зовнішні тестери пройшли смоук-тести
- [ ] Commit: `ci(mobile): add ios + android build pipelines with fastlane`

---

## Phase 7 — Submit + launch (1-2 тижні)

### 7.1 Pre-submission checklist

- [ ] TestFlight білд без crashes протягом 48 годин з боку beta-тестерів
- [ ] Play Internal білд без crashes 48 годин
- [ ] Review all Apple guidelines: 2.1 (integrity), 2.3.1 (accurate metadata), 4.2 (minimum functionality), 5.1 (privacy)
- [ ] Review all Google policies: restricted content, monetization, ads (n/a)

### 7.2 Apple submission

- [ ] App Store Connect → Add build from TestFlight
- [ ] Fill "What's new in this version"
- [ ] Submit for review
- [ ] Trick questions → "No" (encryption: якщо тільки HTTPS — вказати exempt)
- [ ] Expected review time: 1-3 дні
- [ ] Responding to reviewer: 24-годинний SLA

### 7.3 Google submission

- [ ] Play Console → Production → Create release → from Internal
- [ ] Country selection: Ukraine first, потім expand (після v1)
- [ ] Submit for review
- [ ] Expected review time: ~2-3 дні (інколи швидше)

### 7.4 Launch plan

- [ ] **Soft launch:** повідомити Skandi residents (існуюча демо-org) про availability
- [ ] **Monitoring:** слідкувати за crash reports перші 48 годин
- [ ] **Feedback loop:** створити `#mobile-feedback` канал (або email) для bug reports
- [ ] **Post-launch v1.1:** планувати на основі зібраного фідбеку

### 7.5 Post-launch roadmap (не у v1)

- [ ] Biometric auth (Face ID / Touch ID / Fingerprint) via `@aparajita/capacitor-biometric-auth`
- [ ] Camera integration для фото у заявках (`@capacitor/camera`)
- [ ] Share sheet (`@capacitor/share`) — поділитися заявкою/новиною
- [ ] Deep linking через Universal Links (iOS) + App Links (Android) — щоб `https://apartmentos.org/issue?id=…` відкривав апку
- [ ] Background sync для офлайн-створення заявок (`@capacitor/background-task`)
- [ ] Badge count на іконці (unread notifications)

---

## Ризики

| # | Ризик | Ймовірність | Вплив | Мітігація |
|---|---|---|---|---|
| R1 | Apple реджект за guideline 4.2 ("repackaged web") | Середня | Високий | Додати native fічі: push, status bar, deep links, offline. У app description підкреслити нативну функціональність. |
| R2 | Cookies не передаються через WebView | Висока | Високий | D2 — Bearer tokens. Виконано в Phase 2. |
| R3 | Static export ламається на dynamic routes | Висока | Середній | D4 — query-string refactor. Виконано в Phase 2. |
| R4 | Push на iOS потребує APNs key + Apple Dev | Висока | Високий | Запустити реєстрацію Apple Dev у Week 1. |
| R5 | Bundle size > 10MB → повільний cold start | Середня | Середній | Lazy-load recharts, tree-shake lucide. Bundle analyzer в Phase 0. |
| R6 | RTK Query cache не persists між session | Низька | Низький | `redux-persist` якщо потрібно. Для v1 прийнятно перезавантажувати. |
| R7 | CORS ламається на Android `http://localhost` origin | Середня | Середній | Додати всі Capacitor origins у Django `CORS_ALLOWED_ORIGINS`. |
| R8 | Firebase trial → paid при великих обсягах push | Низька | Низький | FCM free до 1M messages/day. Достатньо для v1. |
| R9 | App Store reviewer не може увійти в demo-акаунт | Середня | Високий | Тестувати demo-creds у final TestFlight білді перед submit. |
| R10 | Deep links не працюють з push | Середня | Середній | Ручний E2E тест у Phase 4.9. |

---

## Acceptance criteria per phase

### Phase 0
- Існують 3 документи: `dynamic-routes-plan.md`, `server-apis-inventory.md`, `auth-migration-plan.md`
- Немає сюрпризів при переході на static export

### Phase 1
- PWA Lighthouse ≥ 90
- "Add to Home Screen" працює на iOS Safari
- Offline page показується коли немає мережі

### Phase 2
- `npm run build` генерує `out/` без помилок
- Smoke test у web-браузері на `localhost:3001` проходить: login → dashboard → issue details → logout
- Network tab показує `Authorization: Bearer` замість cookies

### Phase 3
- Додаток запускається в iOS simulator без crash
- Додаток запускається в Android emulator без crash
- Splash screen показується 1.5 сек
- Login → Dashboard flow працює end-to-end в обох simulators

### Phase 4
- Push реєстрація: після login → token з'являється в Django admin → DeviceToken таблиці
- Firebase test message → приходить на пристрій
- Створення issue → assignee отримує push
- Tap на push → відкриває `/issue?id=<correct-id>`

### Phase 5
- Privacy / Terms / Support — публічно доступні на apartmentos.org
- App Store Connect listing: ≥ 95% complete (тільки білд missing)
- Google Play Console listing: ≥ 95% complete

### Phase 6
- GH Actions workflow `mobile-ios.yml` зелений на main branch
- GH Actions workflow `mobile-android.yml` зелений на main branch
- TestFlight отримує новий білд автоматично при push
- Play Internal отримує новий білд автоматично при push

### Phase 7
- Apple submission → submitted for review
- Google submission → submitted for review
- Після approval: v1.0 доступна публічно

---

## Appendix A — Команди cheat sheet

```bash
# Dev — звичайний Next
cd client && npm run dev

# Build static bundle
cd client && npm run build

# Capacitor sync (після кожного build)
cd client && npx cap sync

# Open iOS project
cd client && npx cap open ios

# Open Android project
cd client && npx cap open android

# Run on iOS simulator
cd client && npx cap run ios

# Run on Android emulator
cd client && npx cap run android

# Update all Capacitor plugins
cd client && npm update && npx cap sync

# Regenerate icons + splashes
cd client && npx @capacitor/assets generate

# Fastlane iOS beta
cd client/ios && bundle exec fastlane beta

# Fastlane Android internal
cd client/android && bundle exec fastlane internal

# Backend push test (через Django shell)
cd server && python manage.py shell
>>> from core_apps.notifications.tasks import send_push_task
>>> send_push_task.delay(1, "Test", "Hello from Django", {"screen": "welcome"})
```

---

## Appendix B — Glossary

- **Capacitor** — open-source фреймворк від Ionic для обгортання web apps у native shells. Використовує WKWebView (iOS) / WebView (Android).
- **FCM** — Firebase Cloud Messaging. Google-сервіс для push notifications. Підтримує і Android (напряму), і iOS (через APNs proxy).
- **APNs** — Apple Push Notification service. Нативний push для iOS. Firebase дозволяє використовувати APNs без окремої інфраструктури.
- **Bundle ID / Package name** — унікальний ідентифікатор застосунку на платформі. `org.apartmentos.app` для обох платформ.
- **TestFlight** — Apple beta-distribution сервіс. Роздача preview-білдів до 10000 тестерів без App Store review.
- **Google Play Internal Testing** — аналог TestFlight від Google. До 100 тестерів.
- **Match (fastlane)** — інструмент для шерингу iOS certificates + provisioning profiles між кількома машинами через приватний git-repo.
- **Universal Links / App Links** — нативний deep linking: `https://apartmentos.org/issue?id=…` відкриває саме в апці якщо вона встановлена. Додаємо post-v1.
- **Guideline 4.2** — Apple вимога мінімальної нативної функціональності. Тонкі web-wrapper-и реджектять.

---

**Коли план затверджено — оновити цей документ:**
- Відмічати checkbox-и `- [x]` по мірі виконання
- Додавати дату виконання біля кожного phase deliverable
- Вести changelog коли план змінюється
