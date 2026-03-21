# Skandi Apartments — Design Images & Icons Specification

> **Version 1.0** | March 2026 | Stack: Django 4.2 · Next.js 14 · TailwindCSS 3

---

## Table of Contents

1. [Brand Identity](#1-brand-identity)
2. [Icons Library](#2-icons-library)
3. [Illustrations & Images](#3-illustrations--images)
4. [AI Generation Prompts](#4-ai-generation-prompts)
5. [Technical Requirements](#5-technical-requirements)
6. [File Organization](#6-file-organization)

---

## 1. Brand Identity

### 1.1 Logo

#### Full Logo (Primary)
- **Name:** `skandi-logo-full.svg`
- **Usage:** Sidebar header (w-10, h-10), marketing materials
- **Variants:**
  - Default (dark on light)
  - Inverted (light on dark) — for sidebar bg-[#1E2761]
  - Monochrome (black & white)
- **Formats:** SVG (primary), PNG 256x256, PNG 512x512
- **Safe Area:** 16px padding
- **Min Width:** 40px (sidebar context)
- **Reference:** Currently using `next.svg` & `vercel.svg` — **TODO:** Replace with Skandi-branded logo

#### Favicon
- **Name:** `favicon.ico`
- **Sizes:** 16x16, 32x32, 64x64
- **Format:** ICO
- **Note:** Current favicon at `/app/favicon.ico` should be updated with Skandi brand mark
- **Variants Needed:**
  - Apple touch icon (180x180, PNG)
  - Android chrome (192x192, 512x512, PNG)

#### Minimal Mark (Icon)
- **Name:** `skandi-mark.svg`
- **Usage:** Browser tabs, micro interfaces
- **Size:** 40x40px (scalable SVG)
- **Colors:** Primary navy (#1C2B3A) or white depending on context

---

### 1.2 Color Palette

#### Primary Brand Colors

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| **Nordic Navy** | `#1C2B3A` | `bg-nordic-navy` | Primary UI, headers, active states |
| **Nordic Teal** | `#3D7A8A` | `bg-nordic-teal` | Accent, CTA buttons, links |
| **Nordic Frost** | `#5BA3B5` | `bg-nordic-frost` | Accent dark mode, hover states |
| **Nordic Cream** | `#F7F6F2` | `bg-nordic-cream` | Page background, warm surfaces |
| **Nordic Stone** | `#EFEDE6` | `bg-nordic-stone` | Secondary surface (light) |
| **Nordic Ice** | `#EBF3F5` | `bg-nordic-ice` | Teal-tinted surfaces |
| **Nordic Silver** | `#E2E5E8` | `bg-nordic-silver` | Borders (light mode) |
| **Nordic Slate** | `#6B7F8C` | `text-nordic-slate` | Muted text, placeholders |

#### Semantic Status Colors

| Status | Hex | Tailwind | SVG Stroke | Usage |
|--------|-----|----------|-----------|-------|
| **Success** | `#2D8A4E` | `bg-[#2D8A4E]` | `#2D8A4E` | Done, approved, success states |
| **Warning** | `#D97706` | `bg-amber-600` | `#D97706` | In progress, SLA warning |
| **Danger** | `#C0392B` | `bg-[#C0392B]` | `#C0392B` | Overdue, error, rejected |
| **Info** | `#4A90D9` | `bg-[#4A90D9]` | `#4A90D9` | Links, announcements, info |
| **Pending** | `#F59E0B` | `bg-amber-400` | `#F59E0B` | Pending pass, awaiting action |

#### Neutral Grays (from Tailwind)

| Role | Hex | Tailwind | SVG Stroke |
|------|-----|----------|-----------|
| Text Primary | `#0F172A` | `text-slate-900` | `#0F172A` |
| Text Secondary | `#64748B` | `text-slate-500` | `#64748B` |
| Border Light | `#E2E8F0` | `border-slate-200` | `#E2E8F0` |
| Surface | `#FFFFFF` | `bg-white` | — |
| Background | `#F8FAFC` | `bg-slate-50` | — |

---

### 1.3 Typography

#### Font Family
- **Primary:** `Inter` (system fallback: sans-serif)
- **Weights Used:** 400, 500, 600, 700
- **Load:** Via Tailwind `fontFamily.inter` config

#### Type Scale

| Role | Size | Weight | Tailwind Classes | SVG Usage |
|------|------|--------|------------------|-----------|
| **H1** | 32px | 700 | `text-3xl font-bold` | Page titles, hero |
| **H2** | 24px | 700 | `text-2xl font-bold` | Section headers |
| **H3** | 18px | 600 | `text-lg font-semibold` | Card titles |
| **Body** | 16px | 400 | `text-base font-normal` | Paragraph text |
| **Small** | 14px | 400 | `text-sm` | Labels, captions |
| **Tiny** | 12px | 500 | `text-xs font-medium` | Badges, tags |

---

## 2. Icons Library

### 2.1 Navigation Icons

Used in sidebar navigation (`/cabinet/*` routes). All icons from **Lucide React** (primary source).

| Icon | Lucide Name | Size | Color | States |
|------|-------------|------|-------|--------|
| 🏠 Dashboard | `LayoutDashboard` | 20px | white (nav) / `text-nordic-navy` (active) | outlined |
| 🔧 My Requests | `Wrench` | 20px | white (nav) / `text-nordic-navy` (active) | outlined |
| 🚗 Visitor Passes | `Car` | 20px | white (nav) / `text-nordic-navy` (active) | outlined |
| 📢 Announcements | `Newspaper` | 20px | white (nav) / `text-nordic-navy` (active) | outlined |
| 👤 Profile | `UserCircle` | 20px | white (nav) / `text-nordic-navy` (active) | outlined |
| 🚪 Logout | `LogOut` | 16px | `text-red-400` / hover `text-red-300` | outlined |

**Implementation:**
```tsx
// Use lucide-react directly
import { LayoutDashboard, Wrench, Car, Newspaper, UserCircle, LogOut } from 'lucide-react';

// In sidebar nav
<Wrench className="h-5 w-5" /> // 20px
```

---

### 2.2 Top Bar & Utility Icons

| Icon | Lucide Name | Size | Color (Light) | Color (Dark) | Purpose |
|------|-------------|------|---------------|--------------|---------|
| 🔔 Notifications | `Bell` | 20px | `#64748B` | `#E2E5E8` | Notification toggle |
| ▼ Dropdown | `ChevronDown` | 16px | `#94A3B8` | `#CBD5E1` | Dropdown trigger |
| → Arrow Right | `ArrowRight` | 14px | `#4A90D9` | `#5BA3B5` | Link indicators |
| ✓ Check | `Check` | 16px | `#2D8A4E` | — | Confirmation |
| ✕ Close | `X` | 16px | `#64748B` | `#E2E5E8` | Close/dismiss |
| ⚙ Settings | `Settings` | 20px | `#64748B` | `#E2E5E8` | Settings access |
| 🔍 Search | `Search` | 20px | `#64748B` | — | Search input |
| ⏰ Timer | `Clock` | 16px | `#D97706` | — | SLA timer |
| ⭐ Star | `Star` | 16px | `#F59E0B` | — | Rating, favorite |
| 📅 Calendar | `Calendar` | 14px | `#64748B` | — | Date indicator |
| 📌 Pin | `Pin` | 12px | `#F59E0B` | — | Pinned badge |
| 📬 Inbox | `Inbox` | 32px | `#CBD5E1` | — | Empty state icon |

---

### 2.3 Issue (Request) Category Icons

Displayed in issue cards with colored background chips.

| Category | Icon | Lucide Name | BG Color | Icon Color | 24px SVG |
|----------|------|-------------|----------|-----------|----------|
| 🔧 Maintenance | `Wrench` | `Wrench` | `#CADCFC` | `#1E2761` | `⚙` |
| 💧 Plumbing | `Droplet` | `Droplet` | `#A7D8DE` | `#0F5B6B` | `💧` |
| 🔌 Electrical | `Zap` | `Zap` | `#FFE8CC` | `#C27803` | `⚡` |
| 🚪 Carpentry | `Hammer` | `Hammer2` | `#DCC9E8` | `#5B2E71` | `🔨` |
| 🪟 Glazing | `Glass` | — custom | `#B3E5FC` | `#01579B` | `🪟` |
| 🌡️ HVAC | `Wind` | `Wind` | `#FFE0B2` | `#E65100` | `🌬️` |
| 🏗️ Infrastructure | `Building` | `Building2` | `#C8E6C9` | `#1B5E20` | `🏢` |
| 🛡️ Security | `Shield` | `Shield` | `#F8BBD0` | `#880E4F` | `🛡️` |

**Implementation:**
```tsx
const categoryIconMap = {
  'maintenance': { Icon: Wrench, bg: 'bg-[#CADCFC]', color: 'text-[#1E2761]' },
  'plumbing': { Icon: Droplet, bg: 'bg-[#A7D8DE]', color: 'text-[#0F5B6B]' },
  // ...
};

<div className={`${categoryIconMap[cat].bg} rounded-lg p-2`}>
  <categoryIconMap[cat].Icon className={`h-4 w-4 ${categoryIconMap[cat].color}`} />
</div>
```

---

### 2.4 Status Badge Icons

Inline mini-icons for status labels (optional, 12-14px).

| Status | Icon | Color | Usage |
|--------|------|-------|-------|
| 📋 Reported | `FileText` | `#64748B` | Initial state |
| ✋ Accepted | `CheckCircle2` | `#4A90D9` | Acknowledged by team |
| ⏳ In Progress | `Loader` | `#D97706` | Work started, rotating animation |
| ✅ Done | `CheckCircle` | `#2D8A4E` | Completed |
| ❌ Rejected | `XCircle` | `#C0392B` | Not fixable or declined |
| ⏱️ Pending | `Clock` | `#F59E0B` | Awaiting approval |
| 🔒 Closed | `Lock` | `#64748B` | Archived/locked |

---

### 2.5 Pass (Visitor Permit) Icons

| Element | Icon | Lucide Name | Color | Size |
|---------|------|-------------|-------|------|
| 🚗 Vehicle | `Car` | `Car` | `#3D7A8A` | 20px |
| 📝 Document | `FileCheck` | `FileCheck` | `#4A90D9` | 20px |
| 👤 Guest | `User` | `User` | `#3D7A8A` | 20px |
| 📅 Date | `Calendar` | `Calendar` | `#64748B` | 16px |
| 🚪 Gate | `DoorOpen` | `DoorOpen` | `#2D8A4E` | 20px |

---

### 2.6 Admin Panel Icons

For `/admin/*` routes (management interface).

| Section | Icon | Lucide Name | Color | 24px | Purpose |
|---------|------|-------------|-------|------|---------|
| 🏢 Buildings | `Building2` | `Building2` | `#3D7A8A` | YES | Building management |
| 👥 Residents | `Users` | `Users` | `#3D7A8A` | YES | Tenant directory |
| 🔑 Passes | `Key` | `Key` | `#D97706` | YES | Visitor pass management |
| 📰 Posts | `FileText` | `FileText` | `#4A90D9` | YES | News/announcements |
| 🛠️ Workers | `Hammer` | `Hammer2` | `#F59E0B` | YES | Technician roster |
| 🎫 Issues | `Wrench` | `Wrench` | `#3D7A8A` | YES | Maintenance requests |
| ⚙️ Settings | `Settings` | `Settings` | `#64748B` | YES | System configuration |
| 📊 Analytics | `BarChart3` | `BarChart3` | `#4A90D9` | YES | Statistics & reports |
| 🚪 Guard Portal | `Shield` | `Shield` | `#C0392B` | YES | Security gate control |

---

### 2.7 Empty States & Illustrations

Larger, more decorative icons for empty states (32-48px).

| Use Case | Icon | Lucide Name | Color | Size | SVG needed? |
|----------|------|-------------|-------|------|-------------|
| No requests | `CheckCircle` | `CheckCircle` | `#2D8A4E` | 40px | NO (Lucide) |
| No passes | `Inbox` | `Inbox` | `#CBD5E1` | 40px | NO (Lucide) |
| No announcements | `Inbox` | `Inbox` | `#CBD5E1` | 40px | NO (Lucide) |
| Error / 404 | `AlertCircle` | `AlertCircle` | `#C0392B` | 48px | NO (Lucide) |
| Loading | Custom spinner | — | `#4A90D9` | 32px | YES (see below) |
| No search results | `Search` | `Search` | `#94A3B8` | 40px | NO (Lucide) |
| Unauthorized | `Lock` | `Lock` | `#C0392B` | 48px | NO (Lucide) |

---

## 3. Illustrations & Images

### 3.1 Hero / Welcome Section

**File:** `/public/assets/images/hero-welcome.webp` or SVG illustration

**Purpose:** Dashboard welcome section, first-time user experience

**Dimensions:**
- Desktop: 1200px × 400px
- Mobile: 375px × 300px
- Format: WebP (primary), JPG fallback

**Style:** Flat design, minimalist, Nordic aesthetic

**Content Elements:**
- Stylized apartment building in soft blues/teals
- Happy resident silhouette
- Floating UI elements (phone, checkmark, calendar)
- Soft warm light indicating management

**Color Palette:**
- Background: Linear gradient (white → `#EBF3F5`)
- Building: `#3D7A8A` (Nordic Teal)
- Accent: `#F59E0B` (warm gold)
- Shadows: `#1C2B3A` @ 10% opacity

**Dark Mode Variant:**
- Background: `#0F1923` → `#162032`
- Building: `#5BA3B5` (lighter teal)
- Accents: `#F59E0B` (unchanged)

---

### 3.2 Building Card Thumbnail

**File:** `/public/assets/images/buildings.webp` (existing, currently used)

**Current:** 567KB WebP at full resolution

**Optimize to:**
- 400px × 300px, 60-80KB WebP
- 400px × 300px, 100KB JPG (fallback)
- Crop focus: building facade with clear detail

**Usage:**
- Building management cards
- Admin dashboard building list
- Homepage property showcase

**Multiple Variants Needed:**
- `building-01-residential.webp` (modern Nordic apartment)
- `building-02-historic.webp` (classic European)
- `building-03-villa.webp` (suburban residential)

---

### 3.3 User Avatar Placeholders

**Naming:** `/public/assets/images/avatars/placeholder-{gender}.svg`

**Variants:**
- `placeholder-male.svg` (40x40, 64x64, 128x128)
- `placeholder-female.svg`
- `placeholder-neutral.svg`

**Style:** Flat geometric, Nordic color palette

**Colors:**
- Avatar circle: `#EBF3F5` (light teal)
- Icon/figure: `#3D7A8A` (Nordic teal)
- Stroke: `#CBD5E1` (light border)

**Usage:**
- Sidebar user profile (32x32)
- Issue card technician (20x20)
- Top bar (32x32)
- Admin user list (48x48)

---

### 3.4 Status Illustration Cards

**Purpose:** Large visual indicators for issue/pass statuses

**Dimensions:** 320px × 200px (card interior)

**Variants:** 6 designs (one per primary status)

| Status | File | Colors | Icon |
|--------|------|--------|------|
| Reported | `status-reported.svg` | `#94A3B8` `#E2E5E8` | 📋 |
| Accepted | `status-accepted.svg` | `#4A90D9` `#EEF3FD` | ✋ |
| In Progress | `status-in-progress.svg` | `#D97706` `#FEF3C7` | ⏳ (rotating) |
| Done | `status-done.svg` | `#2D8A4E` `#DCFCE7` | ✅ |
| Rejected | `status-rejected.svg` | `#C0392B` `#FEE2E2` | ❌ |
| Pending | `status-pending.svg` | `#F59E0B` `#FEF3C7` | ⏱️ |

**Design:**
- Large centered icon (80px)
- Rounded square background with status color @ 10% opacity
- Status label below icon
- Subtle gradient or pattern background

---

### 3.5 Empty States

**File Pattern:** `/public/assets/images/empty-{state}.svg`

**Dimensions:** 240px × 240px (centered in empty container)

**Variants with Custom SVG Needed:**

#### 3.5.1 Empty Issues List
- **File:** `empty-issues.svg`
- **Content:** Checkmark + apartment elements
- **Colors:** `#2D8A4E` (success green), `#E2E5E8` (outline)
- **Emotion:** Calm, satisfied
- **Text below:** "Немає відкритих заявок — Усе під контролем!"

#### 3.5.2 Empty Passes List
- **File:** `empty-passes.svg`
- **Content:** Car with prohibition/empty state indicator
- **Colors:** `#CBD5E1` (muted), `#64748B` (dark neutral)
- **Text below:** "Немає активних перепусток"

#### 3.5.3 Empty Announcements
- **File:** `empty-announcements.svg`
- **Content:** Empty mailbox / inbox illustration
- **Colors:** `#CBD5E1`, `#94A3B8`
- **Text below:** "Поки немає оголошень"

#### 3.5.4 Empty Search Results
- **File:** `empty-search.svg`
- **Content:** Magnifying glass with X or empty results indicator
- **Colors:** `#94A3B8`, `#E2E5E8`
- **Text below:** "Результатів не знайдено"

---

### 3.6 Error Pages

**Dimensions:** Full page (1200px × 800px desktop, responsive mobile)

**Variants:**

#### 3.6.1 404 Not Found
- **File:** `error-404.svg`
- **Content:** Confused character, question mark, building elements
- **Colors:** Playful use of Nordic palette, warm tones
- **Style:** Flat illustration, slightly humorous
- **Text:** "Сторінку не знайдено"

#### 3.6.2 500 Server Error
- **File:** `error-500.svg`
- **Content:** Broken gear, warning symbols, building in distress
- **Colors:** Warm reds/oranges, `#C0392B` accent
- **Style:** Flat, apologetic tone
- **Text:** "Помилка сервера — спробуйте пізніше"

#### 3.6.3 403 Forbidden / Unauthorized
- **File:** `error-403.svg`
- **Content:** Locked door, prohibition symbol
- **Colors:** `#C0392B` (danger), `#1C2B3A` (navy)
- **Style:** Secure, official look
- **Text:** "Доступ заборонено"

---

### 3.7 Loading States

**Spinner SVG:** `/public/assets/images/loading-spinner.svg`

**Existing:**
- `loading-light.svg` (649 bytes) — light background
- `loading-dark.svg` (1025 bytes) — dark background

**Specifications for custom spinner (if needed):**
- Size: 32px × 32px (scalable SVG)
- Stroke: 3px
- Color (light): `#4A90D9` (Nordic/primary blue)
- Color (dark): `#5BA3B5` (Nordic Frost)
- Animation: 1.2s linear rotate, `@keyframes spin`
- SVG should define `:animation` or be animated via CSS

**Usage:**
```tsx
<img
  src="/assets/images/loading-spinner.svg"
  alt="Loading..."
  className="h-8 w-8 animate-spin"
/>
```

---

### 3.8 Modal / Overlay Illustrations

**Purpose:** Large, engaging illustrations in modals and full-screen overlays

#### 3.8.1 Confirmation Modal
- **File:** `modal-confirm.svg`
- **Size:** 200px × 160px
- **Content:** Checkmark, person giving thumbs up
- **Colors:** `#2D8A4E`, `#DCFCE7`, white

#### 3.8.2 Error Modal
- **File:** `modal-error.svg`
- **Size:** 200px × 160px
- **Content:** Warning sign, troubled character
- **Colors:** `#C0392B`, `#FEE2E2`, white

#### 3.8.3 Success Overlay
- **File:** `modal-success.svg`
- **Size:** 240px × 200px
- **Content:** Confetti, checkmark, celebrating elements
- **Colors:** `#2D8A4E`, `#F59E0B`, `#4A90D9`, white

---

## 4. AI Generation Prompts

### 4.1 Hero Welcome Illustration

**Platform:** Midjourney / DALL-E 3

**Prompt:**
```
A minimalist flat design illustration of a modern Nordic apartment building
at golden hour, warm lighting from the left, with a happy resident in
silhouette looking out a window. Soft color palette: creams, teals, and warm golds.
Include floating UI elements (phone, calendar, checkmark icons) in soft shadows
around the building. Clean lines, Scandinavian design aesthetic, no shadows,
high quality 2D illustration.
Dimensions: 1200x400px, 150 DPI.
Color scheme: #F7F6F2, #3D7A8A, #F59E0B, #1C2B3A.
```

**Alternative (simpler):**
```
Flat design apartment building exterior, Nordic style, warm light,
happy resident silhouette, floating icons (phone, calendar),
color palette: creams and teals, minimalist, professional illustration.
```

---

### 4.2 Building Card Image

**Platform:** Midjourney / DALL-E 3

**Prompt:**
```
A photograph of a modern 5-story residential apartment complex in Scandinavia.
Nordic architecture with clean lines, white and light grey facade,
symmetrical windows arranged in rows, clear blue sky, natural daylight.
Slightly angled view showing building corner. Professional real estate
photography, sharp focus on building facade.
No people visible. Daytime, overcast sky, professional lighting.
Dimensions: 400x300px.
```

**Note:** Consider using actual property photos instead (more credible for real estate)

---

### 4.3 Empty Issues State

**Platform:** Midjourney / Custom SVG

**Prompt (SVG alternative):**
```
SVG flat design illustration:
- Central large green checkmark (✓) in circle (#2D8A4E)
- Two apartment windows with happy faces peeking out (minimalist style)
- Small maintenance tools (wrench, screwdriver) arranged decoratively
- Soft background circle (#DCFCE7)
- Overall happy, accomplished mood
- Color palette: #2D8A4E, #DCFCE7, #F7F6F2
- 240x240px canvas
- SVG only, no raster fallback needed
```

**Prompt (AI image):**
```
Flat design illustration of a satisfied apartment resident,
checkmark and wrench icons, everything is fixed and organized,
happy mood, Scandinavian minimalist style,
color palette: greens, creams, teals, 240x240px.
```

---

### 4.4 Error 404 Illustration

**Platform:** Midjourney / DALL-E 3

**Prompt:**
```
A whimsical flat design illustration of a confused character (cartoon style)
standing in front of a large question mark, with apartment building elements
and a "404" number visible. Warm, friendly colors: creams, teals, and warm oranges.
Minimalist Scandinavian design. Playful but professional mood.
Dimensions: 1200x800px (can be cropped).
Color scheme: #F7F6F2, #3D7A8A, #F59E0B, #E65100.
```

---

### 4.5 Loading Spinner Animation

**No prompt needed** — Use existing `loading-light.svg` and `loading-dark.svg`

**Or create custom:**
```
SVG of concentric circles or segmented ring.
Rotate 360° over 1.2 seconds.
Stroke color: #4A90D9 (light) / #5BA3B5 (dark)
Dimensions: 32x32px, stroke-width: 3px
```

---

### 4.6 Status Illustrations (In Progress)

**Platform:** Midjourney / Custom SVG

**Prompt Example (In Progress Status):**
```
Flat design illustration of "work in progress":
- Central rotating/spinning gear or wrench icon
- Worker figure with positive gesture
- Progress bar or hourglass element
- Colors: #D97706 (amber), #FEF3C7 (light amber), #1C2B3A (text)
- Dimensions: 320x200px (for card)
- Minimalist, clean Scandinavian style
```

---

### 4.7 Success Confirmation Modal

**Platform:** Midjourney / DALL-E 3

**Prompt:**
```
Flat design celebration illustration:
A happy person with raised hands, large green checkmark,
confetti particles (subtle), apartment or building icon,
warm light surrounding. Minimalist Scandinavian style.
Colors: #2D8A4E (green), #F59E0B (gold), #DCFCE7 (light green), white.
Dimensions: 240x200px.
Celebratory but professional mood.
```

---

## 5. Technical Requirements

### 5.1 File Formats by Use Case

| Use Case | Recommended | Fallback | Requirements |
|----------|-------------|----------|--------------|
| **Logo** | SVG | PNG | Scalable, crisp @2x |
| **Icons (UI)** | SVG | — | Max 2KB each, monochrome or 1-2 colors |
| **Icons (Lucide)** | JSX (lucide-react) | — | Don't create new icons if Lucide has them |
| **Hero illustration** | WebP | JPG | Optimized <150KB |
| **Building photos** | WebP | JPG | 400px min width, <100KB |
| **Empty states** | SVG | PNG | Scalable, self-contained |
| **Error pages** | SVG or WebP | JPG | Full-page responsive |
| **Avatar placeholder** | SVG | PNG | Crisp @2x, multiple sizes |
| **Modal overlays** | SVG or WebP | PNG | Smooth curves, sharp edges |
| **Spinner** | SVG | — | Animated in CSS |

### 5.2 Image Optimization

#### WebP Conversion
```bash
# Install cwebp or use online tools
cwebp -q 80 image.jpg -o image.webp

# Batch convert
for f in *.jpg; do cwebp -q 80 "$f" -o "${f%.jpg}.webp"; done
```

#### Responsive Images (Next.js)
```tsx
import Image from 'next/image';

export default function HeroImage() {
  return (
    <Image
      src="/assets/images/hero-welcome.webp"
      alt="Welcome"
      width={1200}
      height={400}
      priority
      placeholder="blur"
      blurDataURL="data:image/svg+xml,..."
    />
  );
}
```

#### SVG Optimization
```bash
# Use SVGO (npm install -g svgo)
svgo input.svg -o output.svg

# Or use online: https://svgomg.web.app
```

**Target sizes:**
- Logo SVG: <5KB
- Icon SVG: <2KB
- Illustration SVG: <20KB
- Hero WebP: <150KB (desktop), <80KB (mobile)

### 5.3 Dark Mode Variants

**Icons:** Most Lucide icons work unchanged. Override `color` class:

```tsx
<Bell className="h-5 w-5 text-slate-600 dark:text-slate-300" />
```

**Illustrations:**

Some illustrations need dark variants:

| Illustration | Light Version | Dark Version | Toggle |
|--------------|---------------|--------------|--------|
| Hero welcome | `hero-welcome.webp` | `hero-welcome-dark.webp` | `prefers-color-scheme` |
| Empty states | Default (light) | Inverted colors @ 85% | Dynamically recolor SVG |
| Error pages | Light bg, dark text | Dark bg, light text | Full variant or CSS filter |

**CSS Approach (for SVG):**
```css
@media (prefers-color-scheme: dark) {
  img[data-theme="adaptive"] {
    filter: invert(1) hue-rotate(180deg);
    /* Or: use separate src via picture element */
  }
}
```

**HTML Approach (more reliable):**
```html
<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="/assets/images/empty-issues-dark.svg">
  <img src="/assets/images/empty-issues.svg" alt="Empty state">
</picture>
```

### 5.4 Responsive Icon Sizes

| Context | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| **Nav icon** | 20px | 20px | 18px |
| **Icon badge (8x8)** | 8x8px | 8x8px | 6x6px |
| **Status icon** | 16px | 14px | 12px |
| **Avatar (user)** | 32x32px | 28x28px | 24x24px |
| **Empty state icon** | 48x48px | 40x40px | 32x32px |
| **Hero illustration** | 1200x400px | 768x300px | 375x300px |

### 5.5 Accessibility

#### SVG Icons
```tsx
// WITH accessible label
<button aria-label="Search">
  <Search className="h-5 w-5" />
</button>

// Or use title element
<svg>
  <title>Search</title>
  <!-- icon path -->
</svg>
```

#### Images
```tsx
// Decorative (no alt needed)
<img src="pattern.svg" alt="" aria-hidden="true" />

// Informative
<img src="status-done.svg" alt="Request completed successfully" />
```

#### High Contrast Mode
- Ensure icons have sufficient stroke width (min 2px for 16px icons)
- Use solid colors, not gradients where possible
- Test in Windows High Contrast mode

---

## 6. File Organization

### 6.1 Directory Structure

```
/client/public/
├── assets/
│   ├── icons/
│   │   ├── navigation/
│   │   │   ├── dashboard.svg
│   │   │   ├── wrench.svg (if custom)
│   │   │   └── ... (though Lucide is primary)
│   │   ├── status/
│   │   │   ├── status-reported.svg
│   │   │   ├── status-done.svg
│   │   │   └── ... (6 variants)
│   │   └── utilities/
│   │       ├── loading-spinner.svg
│   │       ├── spinner-dark.svg
│   │       └── empty-check.svg
│   ├── images/
│   │   ├── hero/
│   │   │   ├── hero-welcome.webp
│   │   │   ├── hero-welcome-dark.webp
│   │   │   └── hero-welcome.jpg (fallback)
│   │   ├── buildings/
│   │   │   ├── building-01-residential.webp
│   │   │   ├── building-02-historic.webp
│   │   │   └── buildings.webp (legacy, optimize)
│   │   ├── avatars/
│   │   │   ├── placeholder-male.svg
│   │   │   ├── placeholder-female.svg
│   │   │   └── placeholder-neutral.svg
│   │   ├── empty-states/
│   │   │   ├── empty-issues.svg
│   │   │   ├── empty-passes.svg
│   │   │   ├── empty-announcements.svg
│   │   │   └── empty-search.svg
│   │   ├── errors/
│   │   │   ├── error-404.svg
│   │   │   ├── error-500.svg
│   │   │   └── error-403.svg
│   │   ├── modals/
│   │   │   ├── modal-confirm.svg
│   │   │   ├── modal-error.svg
│   │   │   └── modal-success.svg
│   │   └── status/
│   │       ├── status-reported.svg
│   │       ├── status-accepted.svg
│   │       ├── status-in-progress.svg
│   │       ├── status-done.svg
│   │       ├── status-rejected.svg
│   │       └── status-pending.svg
│   ├── logos/
│   │   ├── skandi-logo-full.svg
│   │   ├── skandi-logo-full-dark.svg
│   │   ├── skandi-mark.svg
│   │   ├── favicon.ico
│   │   ├── apple-touch-icon.png
│   │   └── android-chrome.png
│   └── brand/
│       └── color-palette.json (hex reference)
```

---

### 6.2 Import Examples

#### Using Lucide Icons
```tsx
import { LayoutDashboard, Wrench, Bell, CheckCircle } from 'lucide-react';

export function Navigation() {
  return (
    <nav>
      <LayoutDashboard className="h-5 w-5 text-white" />
      <Wrench className="h-5 w-5 text-white" />
    </nav>
  );
}
```

#### Using Custom SVG Icons
```tsx
import Image from 'next/image';

export function EmptyState() {
  return (
    <div className="text-center">
      <Image
        src="/assets/images/empty-states/empty-issues.svg"
        alt=""
        width={240}
        height={240}
      />
      <p>Немає відкритих заявок</p>
    </div>
  );
}
```

#### Using WebP Images with Fallback
```tsx
export function HeroSection() {
  return (
    <picture>
      <source srcSet="/assets/images/hero/hero-welcome.webp" type="image/webp" />
      <source srcSet="/assets/images/hero/hero-welcome.jpg" type="image/jpeg" />
      <img
        src="/assets/images/hero/hero-welcome.jpg"
        alt="Welcome to Skandi Apartments"
        className="w-full h-auto"
      />
    </picture>
  );
}
```

#### Dark Mode Image Switching
```tsx
'use client';

import { useTheme } from 'next-themes';
import Image from 'next/image';

export function AdaptiveHero() {
  const { theme } = useTheme();

  return (
    <Image
      src={theme === 'dark'
        ? '/assets/images/hero/hero-welcome-dark.webp'
        : '/assets/images/hero/hero-welcome.webp'
      }
      alt="Welcome"
      width={1200}
      height={400}
      priority
    />
  );
}
```

---

### 6.3 Implementation Checklist

**Phase 1: Brand Foundation (Week 1)**
- [ ] Create/finalize Skandi logo (full + mark + favicon)
- [ ] Generate brand color palette JSON reference
- [ ] Set up folder structure in `/public/assets/`
- [ ] Document color hex codes in Figma/design system

**Phase 2: Icon System (Week 2)**
- [ ] Verify Lucide React covers all navigation/utility icons (likely yes)
- [ ] Create custom status illustrations (6 SVGs)
- [ ] Create loading spinner SVG (if needed beyond existing)
- [ ] Optimize all SVG files with SVGO

**Phase 3: Images & Illustrations (Week 3-4)**
- [ ] Generate/source hero welcome illustration (Midjourney or designer)
- [ ] Optimize building photo(s) to WebP format
- [ ] Create avatar placeholders (3 SVGs: male, female, neutral)
- [ ] Create empty state illustrations (4 SVGs)
- [ ] Create error page illustrations (3 SVGs)

**Phase 4: Dark Mode & Responsive (Week 4-5)**
- [ ] Create dark variants for illustrations needing them
- [ ] Test icon colors at light/dark contrast
- [ ] Verify responsive image sizes on mobile/tablet
- [ ] Test WebP fallback rendering

**Phase 5: Integration & QA (Week 5)**
- [ ] Update Next.js Image components to use optimized assets
- [ ] Add Lucide icons to sidebar/navigation
- [ ] Implement empty state illustrations on all list pages
- [ ] Test on iOS Safari, Android Chrome, desktop browsers

---

## 7. Brand Color Reference

### 7.1 Exported for Designers & Developers

**Save as:** `/public/assets/brand/skandi-colors.json`

```json
{
  "brand": {
    "nordics": {
      "navy": "#1C2B3A",
      "teal": "#3D7A8A",
      "frost": "#5BA3B5",
      "cream": "#F7F6F2",
      "stone": "#EFEDE6",
      "ice": "#EBF3F5",
      "silver": "#E2E5E8",
      "slate": "#6B7F8C",
      "midnight": "#0F1923",
      "charcoal": "#162032",
      "dusk": "#1E2D3D",
      "warm": "#C9C4BC"
    }
  },
  "semantic": {
    "success": "#2D8A4E",
    "warning": "#D97706",
    "danger": "#C0392B",
    "info": "#4A90D9",
    "pending": "#F59E0B"
  },
  "ui": {
    "textPrimary": "#0F172A",
    "textSecondary": "#64748B",
    "border": "#E2E8F0",
    "surface": "#FFFFFF",
    "background": "#F8FAFC"
  }
}
```

---

## 8. Next Steps & Design Handoff

### For Designers:
1. Use color palette above for all mockups
2. Create SVGs in Figma/Adobe XD, export as outlined
3. Use Lucide React icon set (available in Figma plugin)
4. Follow responsive dimensions per section

### For Developers:
1. Install dependencies: `npm install lucide-react next-image-export-optimizer`
2. Update imports in components to use color tokens
3. Replace placeholder images with generated/sourced assets
4. Test dark mode with `prefers-color-scheme` media query
5. Use Next.js `<Image>` component for all images (auto-optimization)

### For Copywriters:
1. Use primary color (#1C2B3A / Nordic Navy) in visual hierarchy
2. Ensure alt text on images describes action, not "image of..."
3. Match tone to illustrations (friendly, modern, organized)

---

**Document Created:** March 2026
**Last Updated:** [Your Date]
**Status:** Ready for Implementation ✓

