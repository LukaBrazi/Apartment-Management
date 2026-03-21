# UX/UI Review — Skandi Apartments
> Перевірено: `client/src/app/(estate)/` та `client/src/components/`
> Дата: 21 березня 2026
> Стек: Next.js 14, TailwindCSS, shadcn/ui, Nordic Design System

---

## 🔴 Критично впливає на UX

### 1. `PostCard.tsx` — Grid не адаптується під мобільний
**Проблема:** `grid grid-cols-2 gap-6` — жодного responsive-префіксу. На 375px кожна картка займає ~168px в ширину. Текст заголовка (`text-2xl`) і превью тіла переповнює картку, кнопки "View Post" / іконки зминаються.

**Пропозиція:**
```tsx
// Поточний код:
<div className="mt-7 grid grid-cols-2 gap-6">
// Замінити на:
<div className="mt-7 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
```

---

### 2. `PostCard.tsx` — Кнопки на англійській мові в українському інтерфейсі
**Проблема:** Кнопки `"Create a Post"` та `"View Post"` залишились англійською. Весь інший UI — українською. Виглядає як незавершена локалізація.

**Пропозиція:** Замінити на `"Нова публікація"` та `"Переглянути"`. Заголовок `"Усі публікації — ({count})"` з `text-5xl` також надто великий на мобільному — замінити на `text-2xl sm:text-4xl lg:text-5xl`.

---

### 3. `IssueCard.tsx` — Повна невідповідність стилю дизайн-системі
**Проблема:** `IssueCard` використовує застарілий стиль (shadcn `Card` + `border-dashed`), тоді як всі інші компоненти (Dashboard, ResidentDashboard) вже оновлені до Nordic Design System. В темному режимі: заголовок — `dark:text-lime-500` (яскраво-зелений), бейдж пріоритету — `dark:bg-lime-500 dark:text-veryBlack` — виглядає як помилка верстки.

**Пропозиція:** Привести до єдиного стилю:
```tsx
// Замінити Card-обгортку та хардкодовані кольори на:
<Link href={`/issue/${issue.id}`} className="block rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-sm hover:shadow-md transition-shadow dark:border-[#2D3D4F] dark:bg-[#162032]">
  <h3 className="font-semibold text-[#111827] dark:text-[#F0EDE6] truncate">{issue.title}</h3>
  // StatusChip + Badge з існуючою системою кольорів
</Link>
```

---

### 4. `ComingSoon.tsx` — Технічний debug-текст показується користувачам
**Проблема:** Компонент виводить `NEXT_PUBLIC_PAYMENTS_URL`, `NEXT_PUBLIC_CONTACTS_URL` у `<p>` елементі кожному відвідувачу. Це технічна деталь впровадження, яка ніяк не допомагає користувачу і виглядає як помилка. Крім того, компонент не має dark mode (`bg-white` без `dark:bg-[#162032]`).

**Пропозиція:** Видалити рядок з env-змінною з JSX повністю. Додати dark mode:
```tsx
// Видалити:
<p className="mt-3 text-xs text-[#9CA3AF] font-mono">{`NEXT_PUBLIC_${microserviceKey}_URL`}</p>

// Додати до div-обгортки:
className="... dark:border-[#2D3D4F] dark:bg-[#162032]"
// Та до тексту:
className="text-sm text-[#6B7280] dark:text-[#8FA8B8]"
```

---

### 5. `FormFieldComponent.tsx` — `id` відсутній для Textarea і PasswordInput
**Проблема:** `label` має `htmlFor={name}`, але `id={name}` є лише в `Input`. `PasswordInput` і `Textarea` не отримують `id`, тому клік по лейблу не фокусує поле. Ламає accessibility та стандартну UX-поведінку браузера.

**Пропозиція:**
```tsx
// Textarea:
<Textarea id={name} {...register(name)} ... />

// PasswordInput:
<PasswordInput id={name} {...register(name)} ... />
```

---

## 🟠 Помітні проблеми

### 6. `ResidentDashboard.tsx` — KPI "Контакти" показує "В розробці" як числове значення
**Проблема:** `value="В розробці"` рендериться в `<p className="text-2xl font-bold">` — елементі для числа. Текст "В розробці" виглядає зламаним у слоті для числа, масштабується погано і не відповідає тому, що очікує користувач.

**Пропозиція:** Замість текстового value, показати `—` або `0` як value, а "В розробці" — як окремий `badge` під лейблом. Або відобразити KPI-карту Контактів в disabled-стані з іконкою замка:
```tsx
value="—"
// + додати `opacity-60 pointer-events-none` до картки Contacts
```

---

### 7. `PostCard.tsx` — Empty state не відповідає загальному стилю
**Проблема:**
```tsx
<p className="h2-semibold dark:text-lime-500">Публікацій не знайдено!</p>
```
Порожній стан — просто текстовий рядок з `dark:text-lime-500` (невідповідний колір). На відміну від Dashboard (є іконка + текст + CTA-кнопка) — повна невідповідність.

**Пропозиція:** Привести до єдиного стилю пустих станів:
```tsx
<div className="flex flex-col items-center gap-3 py-16 text-[#6B7280]">
  <FileText className="h-12 w-12 opacity-30" />
  <p className="text-sm">Публікацій поки немає</p>
  <Link href="/add-post" className="mt-1 rounded-lg bg-[#2F6FED] px-4 py-2 text-sm font-medium text-white hover:bg-[#2460d4]">
    Написати першу
  </Link>
</div>
```

---

### 8. `QuickActions.tsx` — Немає візуального натяку на скрол на мобільному
**Проблема:** Скролбар повністю прихований (`[&::-webkit-scrollbar]:hidden`). На 375px права кнопка "Оцінити майстра" не видна, і жоден візуальний сигнал не вказує, що є ще контент праворуч.

**Пропозиція:** Додати fade-out gradient маску на правий край контейнера:
```tsx
// Обгортка:
<div className="relative">
  <div className="flex items-center gap-3 overflow-x-auto pb-1 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
    {/* кнопки */}
  </div>
  {/* Gradient-маска */}
  <div className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-[#F7F8FA] dark:from-[#0F1923]" />
</div>
```

---

### 9. `CreateIssueForm.tsx` — Відсутнє validation feedback для react-select полів
**Проблема:** При спробі відправити форму без вибраного будинку — жодного червоного повідомлення під Select. `FormFieldComponent` виводить помилки автоматично, але кастомний `<Select>` від react-select не підключений до системи відображення помилок react-hook-form.

**Пропозиція:** Додати відображення помилки під Selects:
```tsx
// Після <Select> для будинку:
{errors.location_note && (
  <span className="text-xs text-red-500 font-medium">
    {errors.location_note.message as string}
  </span>
)}
```

---

### 10. `IssueCard.tsx` — Текст обрізається по символах, а не по словах
**Проблема:**
```tsx
issue.title.substring(0, 20) + "...."  // обрізає "Протікає кран у ва" → "Протікає кран у ва...."
issue.description.substring(0, 35)
```
`substring(0, N)` може обрізати посередині слова. Також `"…."` (чотири крапки) — нестандартний символ.

**Пропозиція:** Використати CSS `truncate` або `line-clamp-2`:
```tsx
<h3 className="truncate font-semibold">{issue.title}</h3>
<p className="line-clamp-2 text-sm text-[#6B7280]">{issue.description}</p>
```

---

### 11. `ResidentDashboard.tsx` — Оголошення не є клікабельними посиланнями
**Проблема:** Кожне оголошення — це `<div>` з hover-ефектом (`hover:bg-[#F7F8FA]`), але не має `href`. Користувач бачить поведінку посилання (hover-підсвічування, cursor:default), але нікуди потрапити не може. Для сторінки `/announcements` ще немає деталей, але hover-ефект вводить в оману.

**Пропозиція:** Або замінити на `<Link href="/announcements">` поки немає detail-сторінки, або повністю прибрати hover-стан (`hover:bg-[#F7F8FA]`) з `<div>`.

---

## 🟡 Покращення

### 12. `StatusChip.tsx` — Відсутні dark mode варіанти для кольорів статусів
**Проблема:** Chip-кольори (`bg-blue-50 text-blue-600`, `bg-amber-50 text-amber-600`) — це дуже світлі відтінки, які виглядають добре на білому фоні, але в dark mode стають майже невидимими на темному `bg-[#162032]`.

**Пропозиція:** Додати явні dark-варіанти до CONFIG:
```tsx
reported:    { label: "Подано",    classes: "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300" },
accepted:    { label: "Прийнято", classes: "bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300" },
in_progress: { label: "В роботі", classes: "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300" },
done:        { label: "Виконано", classes: "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400", icon: true },
rejected:    { label: "Відхилено",classes: "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400" },
```

---

### 13. `WelcomeHero.tsx` — Немає CTA для користувачів без квартири
**Проблема:** Коли `buildingName === "—"` і `unitNumber === "—"` — бейдж-секція просто порожня. Новий мешканець не бачить жодної підказки, що потрібно додати квартиру у профілі.

**Пропозиція:** Додати інформаційний CTA-бейдж коли квартира не додана:
```tsx
{(!buildingName || buildingName === "—") && (
  <Link href="/apartment" className="flex items-center gap-1.5 rounded-lg border border-dashed border-[#2F6FED] px-3 py-1.5 text-sm font-medium text-[#2F6FED] hover:bg-[#EEF3FD] transition-colors">
    <Plus className="h-4 w-4" />
    Додати квартиру
  </Link>
)}
```

---

### 14. `LeftNavbar.tsx` — Зламана логіка активного стану навігації
**Проблема:**
```tsx
pathname.includes(linkItem.path) && linkItem.path.length > 1
```
Перевірка `includes()` означає: якщо є пункт `/profile`, то `/profile/edit` також буде "активним". Якщо додати пункт `/issue`, він буде активним і на `/report-issue`. Захист `length > 1` рятує тільки від `/`.

**Пропозиція:** Замінити на `startsWith()` для коректної ієрархії:
```tsx
const isActive =
  pathname === linkItem.path ||
  (linkItem.path.length > 1 && pathname.startsWith(linkItem.path + "/"));
```

---

### 15. `Navbar.tsx` — Назва бренду прихована на мобільних
**Проблема:** `hidden sm:block` на `"Skandi Apartments"` — на телефоні видно лише іконку будинку. Без підпису користувачу важче ідентифікувати застосунок, особливо якщо встановлений PWA на кількох пристроях.

**Пропозиція:** Показати хоча б скорочений варіант на мобільному:
```tsx
// Замість hidden sm:block показати "Skandi" на мобільному:
<p className="font-robotoSlab font-bold text-[#111827] dark:text-[#F0EDE6] tracking-tight">
  <span className="sm:hidden">Skandi</span>
  <span className="hidden sm:inline">Skandi <span className="text-[#2F6FED]">Apartments</span></span>
</p>
```

---

### 16. `PostCard.tsx` / `IssueCard.tsx` — Відсутні hover-transition на картках
**Проблема:** PostCard (`Card` від shadcn) не має явного `transition-shadow` чи `hover:shadow-md`. IssueCard має `hover:border-pumpkin dark:border-gray hover:dark:border-platinum` — зміна кольору рамки, але без плавного переходу.

**Пропозиція:** Додати плавні мікроанімації на всі картки:
```tsx
// PostCard:
className="... transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"

// IssueCard:
className="... transition-all duration-200 hover:border-[#3D7A8A] dark:hover:border-[#5BA3B5]"
```

---

## ✨ Дизайн-рекомендації

### A. Скелетони повинні відповідати розмірам реального контенту
Dashboard-скелетони в ResidentDashboard мають `h-10` (40px), тоді як реальні рядки issues займають ~56px (py-3.5 + контент). При завантаженні відбувається "стрибок" layout. Рекомендація: встановити `h-14` для skeleton issues, `h-12` для announcements.

### B. Сторінка `/announcements` потребує повноцінної реалізації
Зараз `announcements/page.tsx` рендерить `<ComingSoon>`. Але announcements вже показуються на Dashboard, дані є в API. Без detail-сторінки оголошення є "неклікабельними тизерами" — незадовільна UX. Мінімальний варіант: список оголошень з `title` + `created_at` + повним текстом при відкритті.

### C. Додати `aria-label` на всі icon-only кнопки
PostActions (upvote/downvote/bookmark), ThemeSwitcher, AuthAvatar dropdown-тригер — всі мають icon-only кнопки без `aria-label`. Screen reader оголошуватиме "button" без контексту. Рекомендація: `aria-label="Підтримати публікацію"`, `aria-label="Зберегти в закладки"` тощо.

### D. Feedback після успішних дій — тривалість тостів
React-toastify використовується без явного `autoClose`. Дефолт — 5 секунд. Для коротких повідомлень ("Збережено") це надто довго, для важливих ("Заявку подано. Підтвердження надіслано...") — замало. Рекомендація: `autoClose: 3000` для success, `autoClose: 6000` для інформаційних повідомлень з дією.
