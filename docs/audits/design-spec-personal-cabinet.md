# ApartmentOS — Design Specification: Personal Cabinet (Tenant Dashboard)
> Version 2.0 | March 2026 | Stack: Django 4.2 · Next.js 14 · TailwindCSS 3

---

## Table of Contents

1. [Design System Reference](#1-design-system-reference)
2. [Page Layout & Navigation Shell](#2-page-layout--navigation-shell)
3. [Dashboard (Home)](#3-dashboard-home)
4. [My Requests (Issues)](#4-my-requests-issues)
5. [Visitor Passes](#5-visitor-passes)
6. [Announcements & News](#6-announcements--news)
7. [My Profile](#7-my-profile)
8. [Shared / Reusable Components](#8-shared--reusable-components)
9. [Mobile Behaviour (375 px)](#9-mobile-behaviour-375-px)
10. [API Mapping](#10-api-mapping)

---

## 1. Design System Reference

### 1.1 Colour Tokens

| Token        | Hex       | Tailwind utility               | Usage                                    |
|--------------|-----------|--------------------------------|------------------------------------------|
| Primary      | `#1E2761` | `bg-[#1E2761]`                 | Sidebar bg, primary buttons, headings    |
| Secondary    | `#CADCFC` | `bg-[#CADCFC]`                 | Sidebar hover highlight, light chips     |
| Accent       | `#4A90D9` | `bg-[#4A90D9]`                 | Links, active states, progress bars      |
| Success      | `#2D8A4E` | `bg-[#2D8A4E]`                 | "Done" status, success toasts            |
| Warning      | `#D97706` | `bg-[#D97706]` (amber-600)     | SLA warning, "In Progress" status        |
| Danger       | `#C0392B` | `bg-[#C0392B]`                 | Overdue SLA, error states, ban badge     |
| Background   | `#F8FAFC` | `bg-slate-50`                  | Page background                          |
| Surface      | `#FFFFFF` | `bg-white`                     | Cards, modals                            |
| Border       | `#E2E8F0` | `border-slate-200`             | Card borders                             |
| Text Primary | `#0F172A` | `text-slate-900`               | Body text                                |
| Text Muted   | `#64748B` | `text-slate-500`               | Labels, captions                         |

### 1.2 Typography Scale

| Role        | Size / Weight | Tailwind classes                              |
|-------------|---------------|-----------------------------------------------|
| H1 (page)   | 32 px / 700   | `text-3xl font-bold`                          |
| H2 (section)| 24 px / 700   | `text-2xl font-bold`                          |
| H3 (card)   | 18 px / 600   | `text-lg font-semibold`                       |
| Body        | 16 px / 400   | `text-base font-normal`                       |
| Caption     | 14 px / 400   | `text-sm`                                     |
| Label       | 12 px / 500   | `text-xs font-medium uppercase tracking-wide` |

Font family: `Inter` — add to `tailwind.config.js`:
```js
fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] }
```

### 1.3 Base Card Pattern

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
  <!-- content -->
</div>
```

### 1.4 Status Badge Map

| Status       | Tailwind classes                                                              |
|--------------|-------------------------------------------------------------------------------|
| reported     | `bg-slate-200 text-slate-700 rounded-full px-3 py-1 text-xs font-semibold`   |
| accepted     | `bg-[#CADCFC] text-[#1E2761] rounded-full px-3 py-1 text-xs font-semibold`   |
| in_progress  | `bg-amber-100 text-amber-700 rounded-full px-3 py-1 text-xs font-semibold`   |
| done         | `bg-green-100 text-[#2D8A4E] rounded-full px-3 py-1 text-xs font-semibold`   |
| rejected     | `bg-red-100 text-[#C0392B] rounded-full px-3 py-1 text-xs font-semibold`     |
| pending(pass)| `bg-yellow-100 text-yellow-700 rounded-full px-3 py-1 text-xs font-semibold` |
| closed(pass) | `bg-slate-100 text-slate-500 rounded-full px-3 py-1 text-xs font-semibold`   |

---

## 2. Page Layout & Navigation Shell

### 2.1 ASCII Wireframe — Full Layout (Desktop 1280px)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SIDEBAR (w-64, fixed)          │  MAIN CONTENT AREA (flex-1, ml-64)        │
│  bg-[#1E2761]                   │  bg-slate-50 min-h-screen                 │
│                                 │                                            │
│  ┌───────────────────────────┐  │  ┌──────────────────────────────────────┐ │
│  │ 🏢  ApartmentOS             │  │  │  TOP BAR (sticky, h-16)              │ │
│  │     [logo 40px]           │  │  │  bg-white border-b border-slate-200  │ │
│  └───────────────────────────┘  │  │  [Page Title]         [🔔] [Avatar▼] │ │
│                                 │  └──────────────────────────────────────┘ │
│  ┌───────────────────────────┐  │                                            │
│  │  Кв. 47 · Під'їзд 2      │  │  ┌──────────────────────────────────────┐ │
│  │  Корпус A                 │  │  │                                      │ │
│  └───────────────────────────┘  │  │   PAGE CONTENT  (px-6 py-8)          │ │
│                                 │  │                                      │ │
│  nav links:                     │  └──────────────────────────────────────┘ │
│  ● Dashboard          [HOME]    │                                            │
│  ○ Мої заявки        [WRENCH]   │                                            │
│  ○ Перепустки        [CAR]      │                                            │
│  ○ Оголошення        [NEWSPR]   │                                            │
│  ○ Профіль           [USER]     │                                            │
│                                 │                                            │
│  ─────────────────────────────  │                                            │
│  [Avatar 32px]  Dmytro A.       │                                            │
│  tenant · кв. 47                │                                            │
│  [Вийти]                        │                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Sidebar — Full Code

```html
<aside class="fixed inset-y-0 left-0 z-50 w-64 bg-[#1E2761] flex flex-col">

  <!-- Logo -->
  <div class="flex items-center gap-3 px-6 py-5 border-b border-white/10">
    <img src="/logo.svg" alt="ApartmentOS" class="h-10 w-10" />
    <span class="text-white font-bold text-lg leading-tight">
      ApartmentOS
    </span>
  </div>

  <!-- Apartment chip -->
  <div class="mx-4 mt-4 rounded-xl bg-white/10 px-4 py-3">
    <p class="text-[#CADCFC] text-xs font-medium uppercase tracking-wide">Ваша квартира</p>
    <p class="text-white font-semibold text-sm mt-0.5">Кв. 47, Під'їзд 2</p>
    <p class="text-white/60 text-xs">Корпус A</p>
  </div>

  <!-- Nav -->
  <nav class="flex-1 px-3 mt-6 space-y-1">

    <!-- Default link -->
    <a href="/cabinet/issues"
       class="flex items-center gap-3 px-4 py-3 rounded-xl text-white/70
              hover:bg-white/10 hover:text-white transition-colors duration-150">
      <Wrench class="h-5 w-5 shrink-0" />
      <span class="text-sm font-medium">Мої заявки</span>
    </a>

    <!-- Active link (replace default classes) -->
    <a href="/cabinet"
       class="flex items-center gap-3 px-4 py-3 rounded-xl
              bg-[#CADCFC] text-[#1E2761]">
      <LayoutDashboard class="h-5 w-5 shrink-0" />
      <span class="text-sm font-semibold">Dashboard</span>
    </a>

  </nav>

  <!-- Footer -->
  <div class="border-t border-white/10 px-4 py-4">
    <div class="flex items-center gap-3 mb-3">
      <img src="{avatar}" class="h-8 w-8 rounded-full object-cover ring-2 ring-white/20" />
      <div>
        <p class="text-white text-sm font-medium leading-none">{first_name} {last_name}</p>
        <p class="text-white/50 text-xs mt-0.5">Tenant · Кв. {unit}</p>
      </div>
    </div>
    <button class="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                   text-white/60 hover:bg-red-500/20 hover:text-red-300 transition-colors text-sm">
      <LogOut class="h-4 w-4" /> Вийти
    </button>
  </div>

</aside>
```

**Nav items table (lucide-react icons):**

| Label      | Icon              | Route                    |
|------------|-------------------|--------------------------|
| Dashboard  | `LayoutDashboard` | `/cabinet`               |
| Мої заявки | `Wrench`          | `/cabinet/issues`        |
| Перепустки | `Car`             | `/cabinet/passes`        |
| Оголошення | `Newspaper`       | `/cabinet/announcements` |
| Профіль    | `UserCircle`      | `/cabinet/profile`       |

### 2.3 Top Bar

```html
<header class="sticky top-0 z-40 h-16 bg-white border-b border-slate-200
               flex items-center justify-between px-6">

  <h1 class="text-xl font-bold text-slate-900">{pageTitle}</h1>

  <div class="flex items-center gap-3">

    <!-- Notification bell -->
    <button class="relative p-2 rounded-xl hover:bg-slate-100 transition-colors">
      <Bell class="h-5 w-5 text-slate-600" />
      <!-- Red dot — only when there are unread items -->
      <span class="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#C0392B]"></span>
    </button>

    <!-- Avatar + name dropdown -->
    <button class="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl hover:bg-slate-100 transition-colors">
      <img src="{avatar}" class="h-8 w-8 rounded-full object-cover" />
      <span class="text-sm font-medium text-slate-700 hidden sm:block">{first_name}</span>
      <ChevronDown class="h-4 w-4 text-slate-400" />
    </button>

  </div>
</header>
```

### 2.4 Layout Shell States

| State          | Behaviour                                                              |
|----------------|------------------------------------------------------------------------|
| Authenticated  | Full sidebar visible, avatar populated from profile                    |
| Loading auth   | Skeleton pulses on nav: `animate-pulse bg-white/10 rounded-xl h-10`   |
| Session expired| Toast "Сесія закінчилась" (danger) + `router.push('/login')`          |
| Banned tenant  | All pages render, but warning banner shown below top bar               |

---

## 3. Dashboard (Home)

**Route:** `/cabinet`
**API:** `GET /api/v1/issues/my-issues/`, `/api/v1/passes/my/`, `/api/v1/posts/announcements/`

### 3.1 ASCII Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│  "Вітаємо, Dmytro! 👋"   (text-3xl font-bold text-slate-900)       │
│  "Ваш особистий кабінет · Кв. 47"  (text-sm text-slate-500)        │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 🔧 Відкриті  │   │ 🚗 Активні   │   │ 📢 Нові      │
│    заявки    │   │  перепустки  │   │ оголошення   │
│              │   │              │   │              │
│      3       │   │      1       │   │      5       │
│              │   │              │   │              │
│ Переглянути→ │   │ Переглянути→ │   │ Переглянути→ │
└──────────────┘   └──────────────┘   └──────────────┘

┌─────────────────────────────────────┐  ┌──────────────────────┐
│  Останні заявки                     │  │  Останнє оголошення  │
│  ─────────────────────────────────  │  │                      │
│  🔧 Не працює ліфт  [in_progress]   │  │  📌 Планове відкл.  │
│     SLA: ▓▓▓▓▓▓▓▒░  2г 15хв        │  │  електроенергії      │
│  ─────────────────────────────────  │  │                      │
│  💧 Протікає труба  [accepted]       │  │  "З 10:00 до 14:00.."│
│     SLA: ▓▓▓▓▓▓▓▓▒  5г 00хв        │  │                      │
│  ─────────────────────────────────  │  │  📅 21 бер 2026      │
│  🔌 Зламана розетка [reported]      │  │                      │
│     SLA: ▓▓▓░░░░░░  23г 00хв       │  │  [Читати далі →]     │
│                                     │  └──────────────────────┘
│  [Всі заявки →]                     │
└─────────────────────────────────────┘
```

### 3.2 Stat Tile Component

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6
            flex flex-col gap-4 hover:shadow-md transition-shadow cursor-pointer"
     onClick="router.push(link)">

  <div class="flex items-center justify-between">
    <p class="text-sm font-medium text-slate-500">{label}</p>
    <div class="h-10 w-10 rounded-xl {iconBg} flex items-center justify-center">
      <IconComponent class="h-5 w-5 {iconColor}" />
    </div>
  </div>

  <p class="text-4xl font-bold text-slate-900">{count}</p>

  <a href="{link}" class="text-sm font-medium text-[#4A90D9] hover:underline flex items-center gap-1">
    Переглянути <ArrowRight class="h-3.5 w-3.5" />
  </a>

</div>
```

**Three tiles:**

| Label              | Icon        | `iconBg`         | `iconColor`          | Link                     |
|--------------------|-------------|------------------|----------------------|--------------------------|
| Відкриті заявки    | `Wrench`    | `bg-[#CADCFC]`   | `text-[#1E2761]`     | `/cabinet/issues`        |
| Активні перепустки | `Car`       | `bg-amber-100`   | `text-amber-700`     | `/cabinet/passes`        |
| Нові оголошення    | `Megaphone` | `bg-green-100`   | `text-[#2D8A4E]`     | `/cabinet/announcements` |

**Loading skeleton:**
```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 animate-pulse">
  <div class="flex justify-between mb-4">
    <div class="h-4 w-28 bg-slate-200 rounded"></div>
    <div class="h-10 w-10 bg-slate-200 rounded-xl"></div>
  </div>
  <div class="h-10 w-16 bg-slate-200 rounded mb-4"></div>
  <div class="h-4 w-24 bg-slate-200 rounded"></div>
</div>
```

**Error tile:**
```html
<div class="bg-white rounded-2xl border border-red-100 p-6 flex items-center gap-3">
  <AlertCircle class="h-5 w-5 text-[#C0392B] shrink-0" />
  <p class="text-sm text-slate-600">Не вдалося завантажити дані</p>
</div>
```

### 3.3 Recent Issues Mini-List

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">

  <div class="flex items-center justify-between mb-5">
    <h2 class="text-lg font-semibold text-slate-900">Останні заявки</h2>
    <a href="/cabinet/issues"
       class="text-sm font-medium text-[#4A90D9] hover:underline">Всі заявки →</a>
  </div>

  <!-- Issue row (max 3, repeated) -->
  <div class="space-y-0 divide-y divide-slate-100">
    <div class="flex items-center justify-between py-3">
      <div class="flex items-center gap-3 min-w-0">
        <div class="h-8 w-8 rounded-lg bg-[#CADCFC] flex items-center justify-center shrink-0">
          <Wrench class="h-4 w-4 text-[#1E2761]" />
        </div>
        <div class="min-w-0">
          <p class="text-sm font-medium text-slate-900 truncate">{issue.title}</p>
          <p class="text-xs text-slate-500">{issue.category.name}</p>
        </div>
      </div>
      <div class="flex items-center gap-3 shrink-0 ml-3">
        <span class="{statusBadgeClass}">{statusLabel}</span>
        <SlaTimerBadge dueAt="{issue.due_at}" createdAt="{issue.created_at}" />
      </div>
    </div>
  </div>

  <!-- Empty state -->
  <div class="py-10 text-center hidden">
    <CheckCircle class="h-10 w-10 text-[#2D8A4E] mx-auto mb-3" />
    <p class="text-sm font-medium text-slate-700">Немає відкритих заявок</p>
    <p class="text-xs text-slate-500 mt-1">Усе під контролем!</p>
  </div>

</div>
```

### 3.4 Latest Announcement Card

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 flex flex-col gap-4 h-fit">

  <div class="flex items-center gap-2">
    <Megaphone class="h-5 w-5 text-[#4A90D9]" />
    <h2 class="text-lg font-semibold text-slate-900">Останнє оголошення</h2>
  </div>

  <!-- Pinned badge — conditional -->
  <span class="inline-flex items-center gap-1 text-xs font-medium
               text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full w-fit">
    <Pin class="h-3 w-3" /> Закріплено
  </span>

  <h3 class="text-base font-semibold text-slate-800">{announcement.title}</h3>
  <p class="text-sm text-slate-600 line-clamp-4">{announcement.body}</p>

  <div class="flex items-center justify-between mt-auto pt-2 border-t border-slate-100">
    <span class="text-xs text-slate-400 flex items-center gap-1">
      <Calendar class="h-3.5 w-3.5" /> {formatDate(announcement.created_at)}
    </span>
    <a href="/cabinet/announcements"
       class="text-sm font-medium text-[#4A90D9] hover:underline flex items-center gap-1">
      Читати далі <ArrowRight class="h-3.5 w-3.5" />
    </a>
  </div>

  <!-- Empty state -->
  <div class="py-8 text-center">
    <Inbox class="h-8 w-8 text-slate-300 mx-auto mb-2" />
    <p class="text-sm text-slate-500">Поки немає оголошень</p>
  </div>

</div>
```

### 3.5 Dashboard Page Grid

```html
<!-- Page wrapper -->
<div class="px-6 py-8 max-w-7xl mx-auto">

  <!-- Greeting -->
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-slate-900">Вітаємо, {first_name}! 👋</h1>
    <p class="text-sm text-slate-500 mt-1">Ваш особистий кабінет · Кв. {unit}</p>
  </div>

  <!-- Stat tiles: 3-col on lg, 1-col on mobile -->
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
    <!-- 3 × StatTile -->
  </div>

  <!-- Content: 2-col on lg, 1-col on mobile -->
  <div class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
    <!-- RecentIssues (left) -->
    <!-- LatestAnnouncement (right) -->
  </div>

</div>
```

---

## 4. My Requests (Issues)

**Route:** `/cabinet/issues`
**API:** `GET /api/v1/issues/my-issues/`
**Create:** `POST /api/v1/issues/create/{unit_id}/`

### 4.1 ASCII Wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│  FILTER BAR                                      [+ Нова заявка]     │
│  [Статус ▾]  [Категорія ▾]   [🔍 Пошук заявок...]                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  ISSUE CARD                                                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  🔧 Не працює ліфт                          [in_progress]      │  │
│  │  Ліфт · Середній · 18 бер 2026                                │  │
│  │                                                                │  │
│  │  SLA  ▓▓▓▓▓▓▓▓░░░  до 20 бер 14:00  (⏱ 2г 15хв)             │  │
│  │                                                                │  │
│  │  Ліфт зупиняється між 3 та 4 поверхами...                     │  │
│  │                                                                │  │
│  │  [Avatar] Іван М. (Електрик)  [★ Оцінити]       [Деталі →]   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  ✅ Замінено лампочку                          [done]          │  │
│  │  Електрика · Низький · 14 бер 2026                            │  │
│  │  Виконано: 15 бер 2026                                        │  │
│  │  [★★★★☆]                                        [Деталі →]   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Issue Card Component

```html
<article class="bg-white rounded-2xl shadow-sm border border-slate-100 p-5
                hover:shadow-md transition-shadow">

  <!-- Header -->
  <div class="flex items-start justify-between gap-4 mb-3">
    <div class="flex items-center gap-3 min-w-0">
      <div class="h-9 w-9 rounded-xl bg-[#CADCFC] flex items-center justify-center shrink-0">
        <Wrench class="h-4 w-4 text-[#1E2761]" />
      </div>
      <div class="min-w-0">
        <h3 class="text-base font-semibold text-slate-900 truncate">{issue.title}</h3>
        <p class="text-xs text-slate-500 mt-0.5">
          {issue.category.name} · {priorityLabel} · {formatDate(issue.created_at)}
        </p>
      </div>
    </div>
    <span class="{statusBadgeClass} shrink-0">{statusLabel}</span>
  </div>

  <!-- SLA bar — hidden for done / rejected -->
  <div class="mb-4">
    <div class="flex items-center justify-between mb-1.5">
      <span class="text-xs font-medium text-slate-500 uppercase tracking-wide">SLA</span>
      <SlaTimerText dueAt="{issue.due_at}" createdAt="{issue.created_at}" />
    </div>
    <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
      <div class="{slaBarColor} h-full rounded-full transition-all duration-500"
           style="width: {slaFillPercent}%"></div>
    </div>
  </div>

  <!-- Description -->
  <p class="text-sm text-slate-600 line-clamp-2 mb-4">{issue.description}</p>

  <!-- Footer -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      <!-- Worker chip (if assigned) -->
      <div class="flex items-center gap-1.5 text-xs text-slate-500">
        <img src="{worker.avatar}" class="h-5 w-5 rounded-full object-cover" />
        <span>{worker.first_name} {worker.last_name}</span>
      </div>
      <!-- Rate button (done + not yet rated) -->
      <button class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700
                     rounded-lg text-xs font-medium hover:bg-amber-100 transition-colors">
        <Star class="h-3.5 w-3.5" /> Оцінити
      </button>
      <!-- Stars (already rated) -->
      <StarRating rating="{issue.my_rating}" readonly size="sm" />
    </div>
    <a href="/cabinet/issues/{issue.id}"
       class="flex items-center gap-1 text-sm font-medium text-[#4A90D9] hover:underline">
      Деталі <ArrowRight class="h-4 w-4" />
    </a>
  </div>

</article>
```

### 4.3 SLA Timer Utility & Component

```typescript
// src/utils/sla.ts
export type SlaStatus = {
  isOverdue: boolean;
  fillPercent: number;   // 0-100 — how much of SLA has elapsed
  remainingMs: number;
  color: 'green' | 'amber' | 'red';
};

export function getSlaStatus(dueAt: string, createdAt: string): SlaStatus {
  const now     = Date.now();
  const due     = new Date(dueAt).getTime();
  const created = new Date(createdAt).getTime();
  const total   = due - created;
  const elapsed = now - created;
  const fillPercent = Math.max(0, Math.min(100, (elapsed / total) * 100));
  const remaining   = due - now;
  const color =
    fillPercent < 50 ? 'green' :
    fillPercent < 80 ? 'amber' : 'red';
  return { isOverdue: remaining < 0, fillPercent, remainingMs: remaining, color };
}
```

**SLA bar color map:**

| `fillPercent` | `slaBarColor`          | `slaTextColor`     |
|---------------|------------------------|--------------------|
| < 50%         | `bg-[#2D8A4E]`         | `text-[#2D8A4E]`   |
| 50–80%        | `bg-amber-400`         | `text-amber-600`   |
| > 80%         | `bg-[#C0392B]`         | `text-[#C0392B]`   |
| overdue       | `bg-[#C0392B] animate-pulse` | `text-[#C0392B] font-semibold` |

**SlaTimerText component:**
```html
<span class="{textColor} text-xs flex items-center gap-1">
  <Clock class="h-3.5 w-3.5" />
  {isOverdue
    ? 'Прострочено ' + formatDuration(Math.abs(remainingMs))
    : 'Залишилось ' + formatDuration(remainingMs)}
</span>
```

### 4.4 Filter Bar

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-4
            flex flex-wrap items-center gap-3 mb-6">

  <select class="text-sm border border-slate-200 rounded-xl px-3 py-2
                 text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-[#4A90D9]">
    <option value="">Всі статуси</option>
    <option value="reported">Reported</option>
    <option value="accepted">Accepted</option>
    <option value="in_progress">In Progress</option>
    <option value="done">Done</option>
    <option value="rejected">Rejected</option>
  </select>

  <select class="text-sm border border-slate-200 rounded-xl px-3 py-2
                 text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-[#4A90D9]">
    <option value="">Всі категорії</option>
    <!-- populated dynamically -->
  </select>

  <div class="flex-1 relative min-w-48">
    <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
    <input type="search"
           placeholder="Пошук заявок..."
           class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-xl
                  focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
  </div>

  <button class="ml-auto flex items-center gap-2 px-4 py-2 bg-[#1E2761] text-white
                 rounded-xl text-sm font-medium hover:bg-[#2a3480] transition-colors">
    <Plus class="h-4 w-4" /> Нова заявка
  </button>

</div>
```

### 4.5 New Issue Modal

```html
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
  <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">

    <div class="flex items-center justify-between mb-6">
      <h2 class="text-xl font-bold text-slate-900">Нова заявка</h2>
      <button class="p-2 hover:bg-slate-100 rounded-xl"><X class="h-5 w-5" /></button>
    </div>

    <form class="space-y-4">

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">Назва *</label>
        <input type="text" placeholder="Коротко опишіть проблему"
               class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm
                      focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">Категорія *</label>
        <select class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm
                       bg-white focus:outline-none focus:ring-2 focus:ring-[#4A90D9]">
          <option value="">Оберіть категорію...</option>
        </select>
        <!-- SLA hint after selection -->
        <p class="text-xs text-slate-500 mt-1 flex items-center gap-1">
          <Info class="h-3.5 w-3.5" /> SLA для цієї категорії: 24 год
        </p>
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">Опис *</label>
        <textarea rows="4" placeholder="Детальний опис проблеми..."
                  class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm
                         focus:outline-none focus:ring-2 focus:ring-[#4A90D9] resize-none"></textarea>
      </div>

      <div class="flex gap-3 pt-2">
        <button type="button"
                class="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl
                       text-sm font-medium text-slate-700 hover:bg-slate-50">
          Скасувати
        </button>
        <button type="submit"
                class="flex-1 px-4 py-2.5 bg-[#1E2761] text-white rounded-xl
                       text-sm font-medium hover:bg-[#2a3480] transition-colors">
          Відправити заявку
        </button>
      </div>

    </form>
  </div>
</div>
```

### 4.6 Rate Worker Modal

```html
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
  <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">

    <h2 class="text-xl font-bold text-slate-900 mb-1">Оцінити виконання</h2>
    <p class="text-sm text-slate-500 mb-5">Залишіть відгук про роботу майстра</p>

    <!-- Worker info card -->
    <div class="flex items-center gap-3 p-4 bg-slate-50 rounded-xl mb-6">
      <img src="{worker.avatar}" class="h-10 w-10 rounded-full object-cover" />
      <div>
        <p class="font-medium text-slate-900">{worker.full_name}</p>
        <p class="text-xs text-slate-500">{worker.occupation}</p>
      </div>
    </div>

    <!-- Interactive star picker -->
    <div class="flex justify-center gap-2 mb-2">
      <!-- for i in [1..5] -->
      <button class="h-10 w-10 rounded-lg hover:bg-amber-50 flex items-center
                     justify-center transition-colors group">
        <Star class="h-7 w-7 {i <= selectedRating
          ? 'text-amber-400 fill-amber-400'
          : 'text-slate-200 group-hover:text-amber-200'}" />
      </button>
    </div>
    <!-- Label under stars: 1=Дуже погано, 2=Погано, 3=Нормально, 4=Добре, 5=Відмінно -->
    <p class="text-center text-sm text-slate-500 mb-4">{ratingLabel}</p>

    <textarea rows="3" placeholder="Коментар (необов'язково)"
              class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm
                     focus:outline-none focus:ring-2 focus:ring-[#4A90D9] resize-none mb-4"></textarea>

    <div class="flex gap-3">
      <button class="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl
                     text-sm font-medium text-slate-700">Пізніше</button>
      <button class="flex-1 px-4 py-2.5 bg-amber-500 text-white rounded-xl
                     text-sm font-medium hover:bg-amber-600">Оцінити</button>
    </div>

  </div>
</div>
```

### 4.7 Issues Empty & Error States

```html
<!-- Empty (no issues at all) -->
<div class="flex flex-col items-center justify-center py-20 text-center">
  <div class="h-20 w-20 rounded-2xl bg-[#CADCFC] flex items-center justify-center mb-5">
    <CheckCircle class="h-10 w-10 text-[#1E2761]" />
  </div>
  <h3 class="text-lg font-semibold text-slate-800 mb-2">Заявок немає</h3>
  <p class="text-sm text-slate-500 max-w-xs mb-6">
    Якщо щось потребує ремонту — створіть заявку.
  </p>
  <button class="px-5 py-2.5 bg-[#1E2761] text-white rounded-xl text-sm font-medium">
    <Plus class="h-4 w-4 inline mr-1.5" /> Нова заявка
  </button>
</div>

<!-- Loading skeleton (×3) -->
<div class="space-y-4">
  <div class="bg-white rounded-2xl border border-slate-100 p-5 animate-pulse">
    <div class="flex gap-3 mb-4">
      <div class="h-9 w-9 bg-slate-200 rounded-xl shrink-0"></div>
      <div class="flex-1 space-y-2">
        <div class="h-4 w-3/5 bg-slate-200 rounded"></div>
        <div class="h-3 w-2/5 bg-slate-200 rounded"></div>
      </div>
      <div class="h-6 w-20 bg-slate-200 rounded-full"></div>
    </div>
    <div class="h-1.5 bg-slate-200 rounded-full mb-4"></div>
    <div class="h-3 w-full bg-slate-200 rounded mb-2"></div>
    <div class="h-3 w-4/5 bg-slate-200 rounded"></div>
  </div>
  <!-- repeat ×2 -->
</div>

<!-- Error -->
<div class="bg-red-50 border border-red-100 rounded-2xl p-6 flex items-start gap-4">
  <AlertCircle class="h-6 w-6 text-[#C0392B] shrink-0 mt-0.5" />
  <div>
    <h3 class="font-semibold text-red-800 mb-1">Помилка завантаження</h3>
    <p class="text-sm text-red-600 mb-3">Перевірте з'єднання та спробуйте знову.</p>
    <button class="text-sm font-medium text-[#C0392B] hover:underline">Повторити</button>
  </div>
</div>
```

---

## 5. Visitor Passes

**Route:** `/cabinet/passes`
**API:** `GET /api/v1/passes/my/`, `POST /api/v1/passes/`, `POST /api/v1/passes/{id}/close/`

### 5.1 ASCII Wireframe

```
┌──────────────────────────────────────────────────────┐
│  TABS: [Активні (1)]  [Завершені]     [+ Нова]       │
└──────────────────────────────────────────────────────┘

── ACTIVE ─────────────────────────────────────────────

┌──────────────────────────────────────────────────────┐
│  🚗  АА 1234 ВС                         [Активна]    │
│                                                      │
│  📅 Дата: 21 березня 2026                            │
│  💬 Прийде до 12:00, місце №3                        │
│  🕐 Створено: 20 бер 2026 о 15:30                    │
│                                                      │
│  [ Закрити перепустку ]                              │
└──────────────────────────────────────────────────────┘

── CLOSED ─────────────────────────────────────────────

┌──────────────────────────────────────────────────────┐
│  🚗  ВС 5678 МН  · 15 бер 2026 · Закрив: Іван  [Закрита] │
└──────────────────────────────────────────────────────┘
```

### 5.2 Tabs

```html
<div class="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit mb-6">
  <button class="px-4 py-2 rounded-lg bg-white shadow-sm text-sm font-semibold text-slate-900">
    Активні
    <span class="ml-2 inline-flex items-center justify-center h-5 min-w-5 px-1
                 bg-[#1E2761] text-white text-xs rounded-full">{pendingCount}</span>
  </button>
  <button class="px-4 py-2 rounded-lg text-sm font-medium text-slate-500 hover:text-slate-700">
    Завершені
  </button>
</div>
```

### 5.3 Active Pass Card

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">

  <div class="flex items-start justify-between gap-4 mb-4">
    <div class="flex items-center gap-3">
      <div class="h-10 w-10 rounded-xl bg-amber-100 flex items-center justify-center">
        <Car class="h-5 w-5 text-amber-700" />
      </div>
      <div>
        <p class="text-base font-bold text-slate-900 tracking-widest font-mono">
          {pass.car_number}
        </p>
        <p class="text-xs text-slate-500">Гостьове авто</p>
      </div>
    </div>
    <span class="bg-yellow-100 text-yellow-700 rounded-full px-3 py-1 text-xs font-semibold">
      Активна
    </span>
  </div>

  <div class="space-y-2 mb-5">
    <div class="flex items-center gap-2 text-sm text-slate-600">
      <Calendar class="h-4 w-4 text-slate-400 shrink-0" />
      Дата візиту: <strong class="text-slate-800">{formatDate(pass.visit_date)}</strong>
    </div>
    <div class="flex items-start gap-2 text-sm text-slate-600">
      <MessageSquare class="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
      {pass.comment || 'Без коментаря'}
    </div>
    <div class="flex items-center gap-2 text-xs text-slate-400">
      <Clock class="h-3.5 w-3.5" />
      Створено {formatDateTime(pass.created_at)}
    </div>
  </div>

  <button class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm font-medium
                 text-slate-600 hover:border-[#C0392B] hover:text-[#C0392B] hover:bg-red-50
                 transition-all flex items-center justify-center gap-2">
    <X class="h-4 w-4" /> Закрити перепустку
  </button>

</div>
```

### 5.4 Closed Pass Row (compact)

```html
<div class="bg-white rounded-2xl border border-slate-100 p-4 flex items-center justify-between">
  <div class="flex items-center gap-3">
    <div class="h-9 w-9 rounded-xl bg-slate-100 flex items-center justify-center">
      <Car class="h-4 w-4 text-slate-400" />
    </div>
    <div>
      <p class="text-sm font-semibold text-slate-700 font-mono">{pass.car_number}</p>
      <p class="text-xs text-slate-400">
        {formatDate(pass.visit_date)} · Закрив: {pass.closed_by?.first_name ?? 'Охоронець'}
      </p>
    </div>
  </div>
  <span class="bg-slate-100 text-slate-500 rounded-full px-3 py-1 text-xs font-semibold">
    Закрита
  </span>
</div>
```

### 5.5 New Pass Modal

```html
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
  <div class="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">

    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold text-slate-900">Нова перепустка</h2>
        <p class="text-sm text-slate-500 mt-0.5">Пропуск для гостьового авто</p>
      </div>
      <button class="p-2 hover:bg-slate-100 rounded-xl"><X class="h-5 w-5" /></button>
    </div>

    <form class="space-y-4">

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">Номер авто *</label>
        <div class="relative">
          <Car class="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input type="text" placeholder="AA 0000 BC"
                 class="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm
                        uppercase tracking-widest font-mono
                        focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
        </div>
        <p class="text-xs text-slate-400 mt-1">Латиницею, без пробілів</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">Дата візиту *</label>
        <input type="date" min="{today}"
               class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm
                      bg-white focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1.5">Коментар</label>
        <textarea rows="3" placeholder="Час прибуття, номер паркомісця..."
                  class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm
                         focus:outline-none focus:ring-2 focus:ring-[#4A90D9] resize-none"></textarea>
      </div>

      <div class="bg-[#CADCFC]/30 border border-[#CADCFC] rounded-xl px-4 py-3
                  flex items-start gap-2.5">
        <Info class="h-4 w-4 text-[#1E2761] shrink-0 mt-0.5" />
        <p class="text-xs text-[#1E2761]">
          Перепустка активна з 00:00 до 23:59 обраної дати.
          Охоронець перевірить авто на в'їзді.
        </p>
      </div>

      <div class="flex gap-3 pt-2">
        <button type="button"
                class="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl
                       text-sm font-medium text-slate-700 hover:bg-slate-50">Скасувати</button>
        <button type="submit"
                class="flex-1 px-4 py-2.5 bg-[#1E2761] text-white rounded-xl
                       text-sm font-medium hover:bg-[#2a3480]">Оформити</button>
      </div>

    </form>
  </div>
</div>
```

### 5.6 Close Confirmation Dialog

```html
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
  <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 text-center">
    <div class="h-14 w-14 rounded-2xl bg-red-100 flex items-center justify-center mx-auto mb-4">
      <X class="h-7 w-7 text-[#C0392B]" />
    </div>
    <h3 class="text-lg font-bold text-slate-900 mb-2">Закрити перепустку?</h3>
    <p class="text-sm text-slate-500 mb-6">
      Авто <strong class="text-slate-800">{pass.car_number}</strong> більше
      не матиме доступу. Цю дію не можна скасувати.
    </p>
    <div class="flex gap-3">
      <button class="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl
                     text-sm font-medium text-slate-700">Залишити</button>
      <button class="flex-1 px-4 py-2.5 bg-[#C0392B] text-white rounded-xl
                     text-sm font-medium hover:bg-red-700">Закрити</button>
    </div>
  </div>
</div>
```

### 5.7 Passes Empty State

```html
<div class="flex flex-col items-center py-16 text-center">
  <div class="h-16 w-16 rounded-2xl bg-amber-100 flex items-center justify-center mb-4">
    <Car class="h-8 w-8 text-amber-600" />
  </div>
  <h3 class="text-base font-semibold text-slate-700 mb-1">Активних перепусток немає</h3>
  <p class="text-sm text-slate-500 mb-5">Оформіть пропуск для гостьового авто</p>
  <button class="px-5 py-2.5 bg-[#1E2761] text-white rounded-xl text-sm font-medium">
    <Plus class="h-4 w-4 inline mr-1.5" /> Нова перепустка
  </button>
</div>
```

---

## 6. Announcements & News

**Route:** `/cabinet/announcements`
**API:** `GET /api/v1/posts/announcements/`, `GET /api/v1/news/`

### 6.1 ASCII Wireframe

```
┌────────────────────────────────────────────────────────────┐
│  TABS: [Оголошення]  [Новини]     [🔍 Пошук...]            │
└────────────────────────────────────────────────────────────┘

── PINNED ───────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────┐
│  bg-[#1E2761]  📌 ЗАКРІПЛЕНО                               │
│  Планове відключення електроенергії                        │
│  "З 10:00 до 14:00 буде відключено..."    21 бер 2026      │
│  [Детальніше →]                                            │
└────────────────────────────────────────────────────────────┘

── ANNOUNCEMENTS LIST ───────────────────────────────────────
  [Megaphone icon] Заголовок оголошення 1       20 бер 2026
  [Megaphone icon] Заголовок оголошення 2       18 бер 2026

── NEWS GRID (3-col) ────────────────────────────────────────
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ [cover img]  │  │ [cover img]  │  │ [cover img]  │
│ Категорія    │  │ Категорія    │  │ Категорія    │
│ Заголовок    │  │ Заголовок    │  │ Заголовок    │
│ 15 бер·👁142 │  │ 14 бер·👁89  │  │ 12 бер·👁210 │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 6.2 Pinned Announcement Banner

```html
<div class="bg-[#1E2761] rounded-2xl p-6 text-white mb-6">
  <div class="flex items-center gap-2 mb-3">
    <Pin class="h-4 w-4 text-[#CADCFC]" />
    <span class="text-xs font-semibold text-[#CADCFC] uppercase tracking-wide">Закріплено</span>
  </div>
  <h3 class="text-xl font-bold mb-2">{announcement.title}</h3>
  <p class="text-white/80 text-sm line-clamp-3 mb-4">{announcement.body}</p>
  <div class="flex items-center justify-between">
    <span class="text-xs text-white/50 flex items-center gap-1">
      <Calendar class="h-3.5 w-3.5" /> {formatDate(announcement.created_at)}
    </span>
    <button class="text-sm font-medium text-[#CADCFC] hover:text-white flex items-center gap-1">
      Детальніше <ArrowRight class="h-4 w-4" />
    </button>
  </div>
</div>
```

### 6.3 Announcement Row

```html
<div class="bg-white rounded-2xl border border-slate-100 p-5
            flex items-start gap-4 hover:shadow-sm transition-shadow cursor-pointer">
  <div class="h-10 w-10 rounded-xl bg-[#CADCFC] flex items-center justify-center shrink-0">
    <Megaphone class="h-5 w-5 text-[#1E2761]" />
  </div>
  <div class="flex-1 min-w-0">
    <p class="font-semibold text-slate-900 mb-1">{announcement.title}</p>
    <p class="text-sm text-slate-600 line-clamp-2">{announcement.body}</p>
    <p class="text-xs text-slate-400 mt-2 flex items-center gap-1">
      <Calendar class="h-3.5 w-3.5" /> {formatDate(announcement.created_at)}
    </p>
  </div>
  <ChevronRight class="h-5 w-5 text-slate-400 shrink-0 mt-1" />
</div>
```

### 6.4 News Card (Grid Item)

```html
<article class="bg-white rounded-2xl border border-slate-100 overflow-hidden
                hover:shadow-md transition-shadow cursor-pointer group">
  <div class="aspect-video bg-slate-100 overflow-hidden">
    <img src="{news.cover_image}" alt="{news.title}"
         class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
  </div>
  <div class="p-4">
    <span class="inline-block text-xs font-semibold text-[#4A90D9]
                 bg-[#CADCFC]/40 px-2 py-0.5 rounded-full mb-2">
      {news.category.name}
    </span>
    <h3 class="font-semibold text-slate-900 line-clamp-2 mb-2
               group-hover:text-[#4A90D9] transition-colors">{news.title}</h3>
    <p class="text-sm text-slate-500 line-clamp-2 mb-3">{news.excerpt}</p>
    <div class="flex items-center justify-between text-xs text-slate-400">
      <span class="flex items-center gap-1">
        <Calendar class="h-3.5 w-3.5" /> {formatDate(news.published_at)}
      </span>
      <span class="flex items-center gap-1">
        <Eye class="h-3.5 w-3.5" /> {news.views_count}
      </span>
    </div>
  </div>
</article>
```

**Grid wrapper:**
```html
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
  <!-- NewsCard × N -->
</div>
```

### 6.5 Empty State

```html
<div class="flex flex-col items-center py-20 text-center">
  <Inbox class="h-14 w-14 text-slate-200 mb-4" />
  <h3 class="text-base font-semibold text-slate-600 mb-1">Оголошень немає</h3>
  <p class="text-sm text-slate-400">Нові оголошення від управителя з'являться тут</p>
</div>
```

---

## 7. My Profile

**Route:** `/cabinet/profile`
**API:** `GET /api/v1/profiles/{slug}/`, `PATCH /api/v1/profiles/{slug}/`

### 7.1 ASCII Wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│  PROFILE HERO                                                         │
│  [Avatar 80px + camera btn]  Dmytro Andriienko                       │
│                              ★★★★☆  Репутація 82/100                │
│                              [Кв.47] [Під'їзд 2] [Корпус A]          │
│                              ⚠ 2 скарги з 5                          │
│                                                          [✏ Змінити] │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐   ┌─────────────────────────────┐
│  ОСОБИСТІ ДАНІ              │   │  МОЯ КВАРТИРА               │
│  ✉ dimas@gmail.com          │   │  47     2     Корпус A       │
│  📞 +380 50 000 0000        │   │  квартира під'їзд корпус     │
│  👤 Чоловіча                │   │                             │
│  📍 Kyiv, Ukraine           │   │  ℹ Змінити у адміністратора │
│                  [Редагувати]│   └─────────────────────────────┘
└─────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  РЕПУТАЦІЯ ТА ЗВІТИ                                                   │
│  Репутація  ▓▓▓▓▓▓▓▓▓░  82/100                                       │
│  Скарги     ▓▓░░░░░░░░  2/5                                           │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 Profile Hero Card

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mb-6">
  <div class="flex items-start gap-5">

    <!-- Avatar -->
    <div class="relative shrink-0">
      <img src="{profile.avatar || '/default-avatar.png'}"
           class="h-20 w-20 rounded-2xl object-cover ring-2 ring-slate-100" />
      <button class="absolute -bottom-1.5 -right-1.5 h-7 w-7 rounded-lg bg-[#1E2761]
                     flex items-center justify-center shadow-md hover:bg-[#2a3480]">
        <Camera class="h-3.5 w-3.5 text-white" />
      </button>
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <h2 class="text-2xl font-bold text-slate-900">
        {user.first_name} {user.last_name}
      </h2>

      <div class="flex items-center gap-2 mt-1">
        <StarRating rating="{Math.round(profile.reputation / 20)}" readonly size="sm" />
        <span class="text-sm text-slate-500">Репутація {profile.reputation}/100</span>
      </div>

      <div class="flex items-center gap-2 mt-2.5 flex-wrap">
        <span class="inline-flex items-center gap-1 text-xs bg-[#CADCFC]
                     text-[#1E2761] px-2.5 py-1 rounded-full font-medium">
          <Home class="h-3 w-3" /> Кв. {unit.number}
        </span>
        <span class="inline-flex items-center gap-1 text-xs bg-slate-100
                     text-slate-600 px-2.5 py-1 rounded-full">
          Під'їзд {entrance.number}
        </span>
        <span class="inline-flex items-center gap-1 text-xs bg-slate-100
                     text-slate-600 px-2.5 py-1 rounded-full">
          Корпус {building.name}
        </span>
      </div>

      <!-- Warning: reports ≥ 3 -->
      <div class="mt-3 flex items-center gap-2 text-sm text-amber-700
                  bg-amber-50 px-3 py-2 rounded-xl w-fit">
        <AlertTriangle class="h-4 w-4 shrink-0" />
        У вас {report_count} скарг. При 5 — доступ буде заблоковано.
      </div>
    </div>

    <button class="flex items-center gap-1.5 px-4 py-2 border border-slate-200 rounded-xl
                   text-sm font-medium text-slate-700 hover:bg-slate-50 shrink-0">
      <Pencil class="h-4 w-4" /> Змінити
    </button>

  </div>
</div>
```

### 7.3 Personal Data Card (View + Edit mode)

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">

  <div class="flex items-center justify-between mb-5">
    <h3 class="text-lg font-semibold text-slate-900">Особисті дані</h3>
    <button class="flex items-center gap-1.5 text-sm font-medium text-[#4A90D9] hover:underline">
      <Pencil class="h-4 w-4" /> Редагувати
    </button>
  </div>

  <!-- VIEW mode -->
  <dl class="space-y-0 divide-y divide-slate-50">
    <div class="flex items-center gap-3 py-3">
      <Mail class="h-4 w-4 text-slate-400 shrink-0" />
      <dt class="text-sm text-slate-500 w-24 shrink-0">Email</dt>
      <dd class="text-sm font-medium text-slate-800">{user.email}</dd>
    </div>
    <div class="flex items-center gap-3 py-3">
      <Phone class="h-4 w-4 text-slate-400 shrink-0" />
      <dt class="text-sm text-slate-500 w-24 shrink-0">Телефон</dt>
      <dd class="text-sm font-medium text-slate-800">{profile.phone_number || '—'}</dd>
    </div>
    <div class="flex items-center gap-3 py-3">
      <User class="h-4 w-4 text-slate-400 shrink-0" />
      <dt class="text-sm text-slate-500 w-24 shrink-0">Стать</dt>
      <dd class="text-sm font-medium text-slate-800">{genderLabel}</dd>
    </div>
    <div class="flex items-center gap-3 py-3">
      <MapPin class="h-4 w-4 text-slate-400 shrink-0" />
      <dt class="text-sm text-slate-500 w-24 shrink-0">Місто</dt>
      <dd class="text-sm font-medium text-slate-800">
        {profile.city_of_origin}, {profile.country_of_origin}
      </dd>
    </div>
  </dl>

  <!-- EDIT mode (toggled) -->
  <form class="space-y-4 mt-4 hidden">
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-xs font-medium text-slate-600 mb-1.5">Ім'я</label>
        <input type="text" value="{user.first_name}"
               class="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm
                      focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-600 mb-1.5">Прізвище</label>
        <input type="text" value="{user.last_name}"
               class="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm
                      focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
      </div>
    </div>
    <div>
      <label class="block text-xs font-medium text-slate-600 mb-1.5">Телефон</label>
      <input type="tel"
             class="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm
                    focus:outline-none focus:ring-2 focus:ring-[#4A90D9]" />
    </div>
    <div>
      <label class="block text-xs font-medium text-slate-600 mb-1.5">Стать</label>
      <select class="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm
                     bg-white focus:outline-none focus:ring-2 focus:ring-[#4A90D9]">
        <option value="M">Чоловіча</option>
        <option value="F">Жіноча</option>
        <option value="O">Інша</option>
      </select>
    </div>
    <div class="flex gap-3">
      <button type="button"
              class="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl
                     text-sm font-medium text-slate-700 hover:bg-slate-50">Скасувати</button>
      <button type="submit"
              class="flex-1 px-4 py-2.5 bg-[#1E2761] text-white rounded-xl
                     text-sm font-medium hover:bg-[#2a3480]">Зберегти</button>
    </div>
  </form>

</div>
```

### 7.4 Apartment Card (Read-only)

```html
<div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
  <div class="flex items-center gap-2 mb-5">
    <Building class="h-5 w-5 text-[#4A90D9]" />
    <h3 class="text-lg font-semibold text-slate-900">Моя квартира</h3>
  </div>
  <div class="grid grid-cols-2 gap-3">
    <div class="bg-slate-50 rounded-xl p-4 text-center">
      <p class="text-2xl font-bold text-[#1E2761]">{unit.number}</p>
      <p class="text-xs text-slate-500 mt-1">Квартира</p>
    </div>
    <div class="bg-slate-50 rounded-xl p-4 text-center">
      <p class="text-2xl font-bold text-[#1E2761]">{entrance.number}</p>
      <p class="text-xs text-slate-500 mt-1">Під'їзд</p>
    </div>
    <div class="bg-slate-50 rounded-xl p-4 text-center col-span-2">
      <p class="text-xl font-bold text-[#1E2761]">Корпус {building.name}</p>
      <p class="text-xs text-slate-500 mt-1">{building.address}</p>
    </div>
  </div>
  <p class="text-xs text-slate-400 mt-4 text-center flex items-center justify-center gap-1">
    <Info class="h-3.5 w-3.5" />
    Змінити дані квартири можна тільки у адміністратора
  </p>
</div>
```

### 7.5 Reputation Widget

```html
<div class="bg-white rounded-2xl border border-slate-100 p-5">
  <h3 class="text-base font-semibold text-slate-900 mb-5 flex items-center gap-2">
    <Shield class="h-5 w-5 text-[#4A90D9]" /> Репутація та звіти
  </h3>

  <!-- Reputation -->
  <div class="mb-5">
    <div class="flex justify-between text-sm mb-2">
      <span class="text-slate-600">Репутація</span>
      <span class="font-semibold text-slate-900">{profile.reputation}/100</span>
    </div>
    <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
      <div class="h-full bg-[#2D8A4E] rounded-full transition-all"
           style="width: {profile.reputation}%"></div>
    </div>
  </div>

  <!-- Reports against user -->
  <div>
    <div class="flex justify-between text-sm mb-2">
      <span class="text-slate-600">Скарги проти вас</span>
      <span class="{report_count >= 3 ? 'text-[#C0392B] font-bold' : 'font-semibold text-slate-900'}">
        {report_count}/5
      </span>
    </div>
    <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
      <div class="h-full rounded-full transition-all
                  {report_count >= 4 ? 'bg-[#C0392B]'
                   : report_count >= 2 ? 'bg-amber-400'
                   : 'bg-[#2D8A4E]'}"
           style="width: {(report_count / 5) * 100}%"></div>
    </div>
    <!-- Ban message -->
    <p class="mt-2 text-xs text-[#C0392B] font-medium flex items-center gap-1">
      <Ban class="h-3.5 w-3.5" /> Ваш акаунт заблоковано. Зверніться до адміністратора.
    </p>
  </div>

</div>
```

---

## 8. Shared / Reusable Components

### 8.1 StarRating

```tsx
// Props: rating: 1-5, readonly?: boolean, size?: 'sm' | 'md' | 'lg'
const sizeMap = { sm: 'h-4 w-4', md: 'h-5 w-5', lg: 'h-6 w-6' };

<div class="flex items-center gap-0.5">
  {[1,2,3,4,5].map(i => (
    <Star class={`${sizeMap[size]} transition-transform
      ${i <= rating ? 'text-amber-400 fill-amber-400' : 'text-slate-200 fill-slate-200'}
      ${!readonly ? 'cursor-pointer hover:scale-110' : ''}`}
      onClick={!readonly ? () => onChange(i) : undefined}
    />
  ))}
</div>
```

### 8.2 Toast

```html
<!-- Stack: fixed bottom-4 right-4 z-[100] space-y-2 -->
<div class="flex items-start gap-3 bg-white rounded-2xl shadow-lg border border-slate-100
            px-4 py-3.5 min-w-72 max-w-sm
            animate-in slide-in-from-right duration-200">
  <!-- success: CheckCircle text-[#2D8A4E] -->
  <!-- error:   AlertCircle text-[#C0392B] -->
  <!-- info:    Info        text-[#4A90D9] -->
  <IconComponent class="h-5 w-5 shrink-0 mt-0.5" />
  <div class="flex-1">
    <p class="text-sm font-semibold text-slate-900">{title}</p>
    <p class="text-xs text-slate-500 mt-0.5">{message}</p>
  </div>
  <button class="p-1 hover:bg-slate-100 rounded-lg">
    <X class="h-3.5 w-3.5 text-slate-400" />
  </button>
</div>
```

### 8.3 PageHeader

```html
<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-2xl font-bold text-slate-900">{title}</h1>
    <p class="text-sm text-slate-500 mt-0.5">{subtitle}</p>
  </div>
  <!-- slot for action buttons -->
</div>
```

### 8.4 Pagination

```html
<div class="flex items-center justify-between pt-6 border-t border-slate-100">
  <p class="text-sm text-slate-500">Показано {from}–{to} з {total}</p>
  <div class="flex gap-1">
    <button class="h-8 w-8 flex items-center justify-center rounded-lg
                   hover:bg-slate-100 disabled:opacity-40">
      <ChevronLeft class="h-4 w-4" />
    </button>
    <!-- current page -->
    <button class="h-8 w-8 flex items-center justify-center rounded-lg
                   bg-[#1E2761] text-white text-sm font-medium">
      {page}
    </button>
    <!-- other pages -->
    <button class="h-8 w-8 flex items-center justify-center rounded-lg
                   hover:bg-slate-100 text-sm text-slate-700">{page+1}</button>
    <button class="h-8 w-8 flex items-center justify-center rounded-lg
                   hover:bg-slate-100 disabled:opacity-40">
      <ChevronRight class="h-4 w-4" />
    </button>
  </div>
</div>
```

### 8.5 Inline Validation Error

```html
<p class="flex items-center gap-1 text-xs text-[#C0392B] mt-1">
  <AlertCircle class="h-3.5 w-3.5 shrink-0" /> {errorMessage}
</p>
```

---

## 9. Mobile Behaviour (375 px)

### 9.1 Responsive Change Table

| Element                 | Desktop (≥ 1024px)              | Mobile (375 px)                            |
|-------------------------|---------------------------------|--------------------------------------------|
| Sidebar                 | Fixed left, `w-64`, always on   | `hidden`; replaced by bottom nav bar       |
| Top bar title           | Full page title                 | Shorter or icon only                       |
| Dashboard stat tiles    | `grid-cols-3`                   | `grid-cols-1`                              |
| Dashboard 2-col layout  | `grid-cols-[1fr_320px]`         | Single column stacked                      |
| Issue cards             | Full card with SLA bar          | Compact row (title + badge, expand on tap) |
| Pass cards              | Full card                       | Full card, single column                   |
| News grid               | `grid-cols-3`                   | `grid-cols-1`                              |
| Profile layout          | Side-by-side cards              | Single column                              |
| Profile hero            | Horizontal (avatar left)        | Vertical centred                           |
| Modals                  | Centred dialog                  | Bottom sheet (`rounded-t-3xl`)             |

### 9.2 Bottom Navigation Bar (Mobile only)

```html
<nav class="fixed bottom-0 inset-x-0 z-50 bg-white border-t border-slate-200
            flex sm:hidden safe-area-pb">
  <a href="/cabinet"
     class="flex-1 flex flex-col items-center gap-1 py-3
            {isActive('/cabinet') ? 'text-[#1E2761]' : 'text-slate-400'}">
    <LayoutDashboard class="h-5 w-5" />
    <span class="text-[10px] font-medium">Головна</span>
  </a>
  <a href="/cabinet/issues"
     class="flex-1 flex flex-col items-center gap-1 py-3 relative text-slate-400">
    <Wrench class="h-5 w-5" />
    <span class="absolute top-2 right-[calc(50%-18px)] h-4 min-w-4 px-1
                 bg-[#C0392B] text-white text-[9px] font-bold rounded-full
                 flex items-center justify-center">{openIssuesCount}</span>
    <span class="text-[10px] font-medium">Заявки</span>
  </a>
  <a href="/cabinet/passes"
     class="flex-1 flex flex-col items-center gap-1 py-3 text-slate-400">
    <Car class="h-5 w-5" />
    <span class="text-[10px] font-medium">Перепустки</span>
  </a>
  <a href="/cabinet/announcements"
     class="flex-1 flex flex-col items-center gap-1 py-3 text-slate-400">
    <Newspaper class="h-5 w-5" />
    <span class="text-[10px] font-medium">Новини</span>
  </a>
  <a href="/cabinet/profile"
     class="flex-1 flex flex-col items-center gap-1 py-3 text-slate-400">
    <UserCircle class="h-5 w-5" />
    <span class="text-[10px] font-medium">Профіль</span>
  </a>
</nav>
```

### 9.3 Bottom Sheet Modal (Mobile)

```html
<!-- Wraps any modal content on mobile -->
<div class="fixed inset-0 z-50 bg-black/40
            sm:flex sm:items-center sm:justify-center sm:p-4">
  <div class="
    fixed bottom-0 inset-x-0 sm:static
    bg-white rounded-t-3xl sm:rounded-2xl
    shadow-xl w-full sm:max-w-lg
    max-h-[92dvh] overflow-y-auto
    p-6 pb-[calc(1.5rem+env(safe-area-inset-bottom))]
    animate-in slide-in-from-bottom duration-300 sm:animate-none
  ">
    <!-- Drag pill (mobile only) -->
    <div class="w-10 h-1 bg-slate-200 rounded-full mx-auto mb-5 sm:hidden"></div>
    <!-- modal content -->
  </div>
</div>
```

### 9.4 Dashboard — Responsive Layout

```html
<!-- Stat tiles -->
<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
  <!-- StatTile × 3 -->
</div>

<!-- Content block -->
<div class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
  <!-- RecentIssues spans full on mobile, left on desktop -->
  <!-- LatestAnnouncement below on mobile, right on desktop -->
</div>
```

### 9.5 Compact Issue Row (Mobile only)

```html
<!-- Used on very small viewports as alternative to full IssueCard -->
<div class="bg-white rounded-xl border border-slate-100 p-4 flex items-center gap-3">
  <div class="h-8 w-8 rounded-lg bg-[#CADCFC] flex items-center justify-center shrink-0">
    <Wrench class="h-4 w-4 text-[#1E2761]" />
  </div>
  <div class="flex-1 min-w-0">
    <p class="text-sm font-semibold text-slate-900 truncate">{issue.title}</p>
    <SlaTimerText dueAt="{issue.due_at}" createdAt="{issue.created_at}" />
  </div>
  <span class="{statusBadgeClass} shrink-0">{statusLabel}</span>
</div>
```

---

## 10. API Mapping

| Page / Action               | Method | Endpoint                              | JWT |
|-----------------------------|--------|---------------------------------------|-----|
| Dashboard — issues          | GET    | `/api/v1/issues/my-issues/`           | ✓   |
| Dashboard — passes          | GET    | `/api/v1/passes/my/`                  | ✓   |
| Dashboard — announcements   | GET    | `/api/v1/posts/announcements/`        | ✓   |
| Issues — list               | GET    | `/api/v1/issues/my-issues/`           | ✓   |
| Issues — create             | POST   | `/api/v1/issues/create/{unit_id}/`    | ✓   |
| Issues — detail             | GET    | `/api/v1/issues/{id}/`                | ✓   |
| Issues — update             | PATCH  | `/api/v1/issues/{id}/update/`         | ✓   |
| Rate worker                 | POST   | `/api/v1/ratings/create/`             | ✓   |
| Passes — list (mine)        | GET    | `/api/v1/passes/my/`                  | ✓   |
| Passes — create             | POST   | `/api/v1/passes/`                     | ✓   |
| Passes — close              | POST   | `/api/v1/passes/{id}/close/`          | ✓   |
| Announcements — list        | GET    | `/api/v1/posts/announcements/`        | ✓   |
| News — list                 | GET    | `/api/v1/news/`                       | ✓   |
| News — detail               | GET    | `/api/v1/news/{slug}/`                | ✓   |
| Profile — get               | GET    | `/api/v1/profiles/{slug}/`            | ✓   |
| Profile — update            | PATCH  | `/api/v1/profiles/{slug}/`            | ✓   |
| Logout                      | POST   | `/api/v1/auth/jwt/destroy/`           | ✓   |

### 10.1 Request Body Examples

**Create Issue:**
```json
{ "title": "Не працює ліфт", "description": "...", "category": 3 }
```

**Create Pass:**
```json
{ "car_number": "AA1234BC", "visit_date": "2026-03-21", "comment": "Прийде о 12:00" }
```

**Create Rating:**
```json
{ "rated_user": "<worker-uuid>", "rating": 4, "comment": "Зробив швидко" }
```

**Update Profile:**
```json
{ "phone_number": "+380501234567", "gender": "M", "bio": "...", "city_of_origin": "Kyiv" }
```

---

## Appendix: Recommended Next.js File Structure

```
client/src/app/cabinet/
├── layout.tsx                  ← Shell: Sidebar + TopBar (auth guard, role=TENANT)
├── page.tsx                    ← Dashboard
├── issues/
│   ├── page.tsx                ← List + filter
│   └── [id]/page.tsx           ← Issue detail
├── passes/
│   └── page.tsx                ← Tabs: active / closed
├── announcements/
│   └── page.tsx                ← Tabs: announcements / news
└── profile/
    └── page.tsx                ← View + inline edit

client/src/components/cabinet/
├── Sidebar.tsx
├── TopBar.tsx
├── BottomNav.tsx               ← Mobile only
├── dashboard/
│   ├── StatTile.tsx
│   ├── RecentIssues.tsx
│   └── LatestAnnouncement.tsx
├── issues/
│   ├── IssueCard.tsx
│   ├── IssueFilterBar.tsx
│   ├── SlaTimer.tsx            ← SlaTimerText + SlaTimerBadge
│   ├── NewIssueModal.tsx
│   └── RateWorkerModal.tsx
├── passes/
│   ├── PassCard.tsx
│   ├── NewPassModal.tsx
│   └── ClosePassDialog.tsx
├── announcements/
│   ├── AnnouncementCard.tsx
│   └── NewsCard.tsx
└── profile/
    ├── ProfileHero.tsx
    ├── PersonalDataCard.tsx
    ├── ApartmentCard.tsx
    └── ReputationWidget.tsx

client/src/components/shared/
├── StarRating.tsx
├── Toast.tsx                   ← + useToast hook
├── PageHeader.tsx
├── StatusBadge.tsx             ← maps Issue/Pass status → badge classes
└── Pagination.tsx

client/src/utils/
├── sla.ts                      ← getSlaStatus()
└── formatDate.ts               ← formatDate(), formatDateTime(), formatDuration()
```

---

*End of specification — v2.0*
*March 2026 · ApartmentOS Project · Web Designer Agent*
