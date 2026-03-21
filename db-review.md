# Database Review — Skandi Apartments

> Дата: 2026-03-21
> Стек: PostgreSQL · Django ORM · Django REST Framework
> Перевірено: `issues`, `passes`, `posts`, `profiles`, `ratings`, `reports`, `news`, `apartments`, `common`

---

## 🔴 Критичні проблеми продуктивності

### 1. N+1 у `IssueSerializer.get_view_count()` — 2N запитів на список

**Файл:** `apps/issues/serializers.py:88-93`

При серіалізації списку з N issue виконуються 2N додаткових запити:

```python
# Поточний код — ПРОБЛЕМА
def get_view_count(self, obj):
    content_type = ContentType.objects.get_for_model(obj)  # запит #1 (per item)
    return ContentView.objects.filter(
        content_type=content_type, object_id=obj.pkid
    ).count()  # запит #2 (per item)
```

`ContentType.objects.get_for_model()` кешується на рівні Django, але `ContentView.objects.filter(...).count()` — окремий SELECT на кожен об'єкт у списку.

**Виправлення:** Анотувати queryset у view:

```python
# views.py — IssueListAPIView.get_queryset()
from django.db.models import Count, Subquery, OuterRef
from apps.common.models import ContentView
from django.contrib.contenttypes.models import ContentType

base_qs = Issue.objects.select_related(
    "apartment", "unit__entrance__building", "category",
    "reported_by", "assigned_to",
).annotate(
    view_count=Count("content_views", distinct=True)
)
```

```python
# serializers.py
view_count = serializers.IntegerField(read_only=True, default=0)  # замість SerializerMethodField
```

---

### 2. N+1 у `BasePostSerializer.get_view_count()` — 2N запитів на список постів

**Файл:** `apps/posts/serializers.py:465-470`

Аналогічна проблема — виконується `ContentView.objects.filter(...).count()` окремо для кожного поста:

```python
def get_view_count(self, obj):
    content_type = ContentType.objects.get_for_model(obj)  # кешується, але...
    return ContentView.objects.filter(
        content_type=content_type, object_id=obj.pkid
    ).count()  # окремий запит для кожного поста
```

**Виправлення:** Анотувати у queryset через `GenericRelation`:

```python
# Post model вже має:
content_views = GenericRelation(ContentView, related_query_name="posts")

# PostListAPIView / PostDetailAPIView
Post.objects.annotate(
    replies_count=Count("replies", distinct=True),
    view_count=Count("content_views", distinct=True),  # додати
)
```

---

### 3. N+1 у `BasePostSerializer.get_avatar()` — доступ до `author.profile` без join

**Файл:** `apps/posts/serializers.py:506-511`, `apps/posts/serializers.py:183-188`, `TopPostSerialzier:112-114`

```python
def get_avatar(self, obj):
    if obj.author.profile.avatar:   # ← 2 окремих запити без select_related!
        return obj.author.profile.avatar.url
    return None
```

Для списку з N постів: N запитів на `author` + N запитів на `profile`.

**Виправлення:** Додати у всі queryset постів:

```python
Post.objects.select_related("author__profile").annotate(...)
```

---

### 4. N+1 у `AssignedIssuesListAPIView` — queryset без `select_related`

**Файл:** `apps/issues/views.py:127-141`

```python
class AssignedIssuesListAPIView(generics.ListAPIView):
    queryset = Issue.objects.all()   # ← жодного select_related!

    def get_queryset(self):
        return self.queryset.filter(assigned_to=self.request.user)
```

`IssueSerializer` звертається до `unit.entrance.building.name`, `reported_by.full_name`, `assigned_to.full_name`, `category.name` — це 4-5 окремих JOIN-ів на кожен рядок.

**Виправлення:**

```python
def get_queryset(self):
    return Issue.objects.filter(assigned_to=self.request.user).select_related(
        "apartment", "unit__entrance__building",
        "category", "reported_by", "assigned_to",
    )
```

---

### 5. N+1 у `Issue.save()` — `Issue.objects.get(pk=self.pk)` при кожному оновленні

**Файл:** `apps/issues/models.py:209-213`

```python
def save(self, *args, **kwargs):
    if is_existing:
        old_issue = Issue.objects.get(pk=self.pk)  # ← зайвий SELECT на кожен save!
        old_assigned_to = old_issue.assigned_to
```

Кожен `issue.save()` викликає SELECT для порівняння `assigned_to`.

**Виправлення:** Використати `update_fields` + передавати старе значення, або:

```python
# Перевіряти зміну assigned_to через Django signals (post_save) або
# зберігати початковий стан у __init__:
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._original_assigned_to_id = self.assigned_to_id  # без запиту

def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    if self.pk and self._original_assigned_to_id != self.assigned_to_id and self.assigned_to:
        self.notify_assigned_user()
```

---

### 6. N+1 у `ProfileListAPIView` — `select_related("user")` відсутній

**Файл:** `apps/profiles/views.py:96-100`

```python
def get_queryset(self):
    return (
        Profile.objects.exclude(user__is_staff=True)
        .exclude(user__is_superuser=True)
        .filter(occupation=Profile.Occupation.TENANT)
        # ← немає select_related("user")!
    )
```

`ProfileSerializer` звертається до `user.first_name`, `user.last_name`, `user.username`, `user.full_name`, `user.is_staff`, `user.date_joined` — окремий запит на кожен профіль.

**Виправлення:**

```python
Profile.objects.select_related("user", "unit__entrance__building").exclude(...).filter(...)
```

---

### 7. N+1 у `ProfileSerializer.get_apartment()` та `get_average_rating()` — lazy queryset per row

**Файл:** `apps/profiles/serializers.py:121-128, 135-146`

```python
def get_apartment(self, obj):
    apartments = obj.user.apartment.all()   # ← окремий SELECT на кожен профіль

def get_average_rating(self, obj):
    return obj.get_average_rating()   # ← obj.user.received_ratings.aggregate(...) per row
```

Для списку з N профілів — 2N додаткових агрегатних запитів.

**Виправлення для apartment:** додати `prefetch_related("user__apartment")` до queryset.
**Виправлення для average_rating:** анотувати queryset:

```python
from django.db.models import Avg

Profile.objects.select_related("user").annotate(
    average_rating=Avg("user__received_ratings__rating")
)
# У serializers:
average_rating = serializers.FloatField(read_only=True, default=0.0)
```

---

## 🟠 Важливі оптимізації

### 8. `NewsListAPIView` і `NewsAdminListCreateAPIView` — відсутній `select_related`

**Файл:** `apps/news/views.py:21-23, 45-46`

```python
qs = News.objects.filter(is_published=True).order_by(...)
# NewsListSerializer звертається до category.name та author.full_name
# → N запитів на category + N запитів на author
```

**Виправлення:**

```python
qs = News.objects.filter(is_published=True).select_related(
    "category", "author"
).order_by("-pinned", "-published_at", "-created_at")
```

---

### 9. `ReportListAPIView` — `select_related` для `reported_user` відсутній

**Файл:** `apps/reports/views.py:96`

```python
return Report.objects.filter(reported_by=user)
```

`ReportListSerializer` звертається до `reported_user.username` та `reported_user.full_name` — N+1.

**Виправлення:**

```python
return Report.objects.filter(reported_by=user).select_related(
    "reported_user", "reported_by"
)
```

---

### 10. `BookmarkPostAPIView` — `post.bookmarked_by.all()` завантажує всіх юзерів

**Файл:** `apps/posts/views.py:391, 434`

```python
if user in post.bookmarked_by.all():   # ← SELECT * FROM bookmarked_by WHERE post_id=...
```

Завантажує всі рядки M2M таблиці тільки щоб перевірити одне значення.

**Виправлення:**

```python
if post.bookmarked_by.filter(pk=user.pk).exists():
```

---

### 11. `Post.save()` — зайвий запит до `author.profile` без prefetch

**Файл:** `apps/posts/models.py:145-148`

```python
def save(self, *args, **kwargs):
    if not (
        self.author.is_superuser
        or self.author.is_staff
        or self.author.profile.occupation == Profile.Occupation.TENANT  # ← SELECT profile
    ):
```

При кожному збереженні поста — окремий запит на `profile`.

**Виправлення:** Кешувати або завантажувати заздалегідь:

```python
# У create-endpoint'і: serializer.save() передає author з вже завантаженим профілем
# Або перенести перевірку у permissions class де user вже завантажений з профілем
```

---

### 12. `ContentView.record_view()` — `view.save()` тригерить повний UPDATE без потреби

**Файл:** `apps/common/models.py:162-167`

```python
if not created:
    view.last_viewed = view.last_viewed   # ← присвоює саме собі!
    view.save()   # ← full UPDATE всіх полів
```

`last_viewed = auto_now=True` оновлюється автоматично, але код все одно викликає `save()` без `update_fields`.

**Виправлення:**

```python
if not created:
    cls.objects.filter(pk=view.pk).update(last_viewed=timezone.now())
    # або просто прибрати блок 'if not created' — auto_now робить своє при наступному save
```

---

## 🟡 Покращення схеми

### 13. `Rating` — відсутній `unique_together`, можливе дублювання оцінок

**Файл:** `apps/ratings/models.py`

Немає обмеження на унікальність пари `(rating_user, rated_user)` — один юзер може виставити кілька оцінок.

**Виправлення:**

```python
class Meta:
    verbose_name = _("Rating")
    verbose_name_plural = _("Ratings")
    unique_together = [("rating_user", "rated_user")]
    ordering = ["-created_at"]
```

SQL-еквівалент:
```sql
ALTER TABLE ratings_rating ADD CONSTRAINT unique_rating_per_pair
    UNIQUE (rating_user_id, rated_user_id);
```

---

### 14. `Report` — `on_delete=CASCADE` з `null=True` — логічне протиріччя

**Файл:** `apps/reports/models.py:40-55`

```python
reported_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, ...)
reported_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, ...)
```

Якщо поле може бути `null` (тобто зв'язок необов'язковий) — `CASCADE` видаляє звіт при видаленні юзера. Але адміністративні звіти (зв'язок «слабкий») мають зберігатися як архів.

**Виправлення:**

```python
reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, ...)
reported_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, ...)
```

---

### 15. `Post` і `Reply` — відсутній `Meta.ordering`

**Файл:** `apps/posts/models.py`

```python
class Post(TimeStampedModel):
    class Meta:
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        # ← немає ordering!
```

Порядок визначається лише в окремих views і може бути непередбачуваним в інших місцях (наприклад, `replies = ReplySerializer(many=True, read_only=True)` у `PostSerializer` не має гарантованого порядку).

**Виправлення:**

```python
class Post(TimeStampedModel):
    class Meta:
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        ordering = ["-created_at"]

class Reply(TimeStampedModel):
    class Meta:
        verbose_name = _("Reply")
        verbose_name_plural = _("Replies")
        ordering = ["created_at"]
```

---

### 16. `News.excerpt` — `TextField` замість `CharField`

**Файл:** `apps/news/models.py:42`

```python
excerpt = models.TextField(_("Excerpt"))
```

`excerpt` за суттю є коротким текстом (summary). `TextField` не має обмеження на довжину і зберігається в окремому toast-сегменті PostgreSQL. Для коротких рядків краще:

```python
excerpt = models.CharField(_("Excerpt"), max_length=500)
```

---

### 17. `Rating.comment` — `TextField` для коротких коментарів

**Файл:** `apps/ratings/models.py:73-76`

```python
comment = models.TextField(_("Comment"), blank=True)
```

Коментар до оцінки здебільшого короткий. Краще обмежити:

```python
comment = models.CharField(_("Comment"), max_length=500, blank=True, default="")
```

Це також виключить `null` та спростить порівняння.

---

### 18. `Profile.bio` — `null=True` на текстовому полі (антипатерн Django)

**Файл:** `apps/profiles/models.py:115`

```python
bio = models.TextField(_("Bio"), blank=True, null=True)
```

Django-конвенція: для текстових полів `null=True` створює два можливих «порожніх» стани (`NULL` і `""`), що ускладнює перевірки. Краще:

```python
bio = models.TextField(_("Bio"), blank=True, default="")
```

---

### 19. `ContentView.object_id` — `PositiveIntegerField` несумісний з `BigAutoField`

**Файл:** `apps/common/models.py:87`

```python
object_id = models.PositiveIntegerField(verbose_name=_("Object ID"))
```

`TimeStampedModel.pkid` є `BigAutoField` (64-bit). `PositiveIntegerField` — 32-bit (max ~2.1 млрд). При великій кількості записів можливе переповнення.

**Виправлення:**

```python
object_id = models.PositiveBigIntegerField(verbose_name=_("Object ID"))
```

---

### 20. `Post.upvotes` / `Post.downvotes` — денормалізовані лічильники можуть десинхронізуватися

**Файл:** `apps/posts/models.py:91-103`

Поряд з M2M-таблицями `upvoted_by`/`downvoted_by` зберігаються окремі лічильники `upvotes`/`downvotes`. При race condition або помилці у serializer лічильники можуть не відповідати кількості рядків у M2M.

**Рекомендація:** Або видалити лічильники й анотувати через `Count`, або додати `CheckConstraint` та `DatabaseError`-handling:

```python
# Альтернатива: скасувати Int-поля, анотувати при вибірці
Post.objects.annotate(
    upvotes_count=Count("upvoted_by", distinct=True),
    downvotes_count=Count("downvoted_by", distinct=True),
)
```

---

## 📊 Рекомендовані індекси

| Таблиця | Поле | Причина | SQL |
|---|---|---|---|
| `issues_issue` | `status` | фільтрація у `IssueFilter`, частий WHERE | `CREATE INDEX ON issues_issue (status);` |
| `issues_issue` | `priority` | фільтрація у `IssueFilter` | `CREATE INDEX ON issues_issue (priority);` |
| `issues_issue` | `due_at` | сортування + `is_overdue` (порівняння з NOW) | `CREATE INDEX ON issues_issue (due_at);` |
| `issues_issue` | `(status, assigned_to_id)` | `AssignedIssuesListAPIView` фільтр + статус | `CREATE INDEX ON issues_issue (status, assigned_to_id);` |
| `news_news` | `is_published` | WHERE у `NewsListAPIView` | `CREATE INDEX ON news_news (is_published);` |
| `news_news` | `pinned` | ORDER BY у всіх news queries | `CREATE INDEX ON news_news (pinned DESC);` |
| `news_news` | `published_at` | ORDER BY | `CREATE INDEX ON news_news (published_at DESC);` |
| `passes_vehiclepass` | `status` | фільтрація у `VehiclePassFilter` | `CREATE INDEX ON passes_vehiclepass (status);` |
| `passes_vehiclepass` | `visit_date` | ORDER BY + фільтрація | `CREATE INDEX ON passes_vehiclepass (visit_date);` |
| `profiles_profile` | `occupation` | фільтрація у `ProfileListAPIView` (filterset) | `CREATE INDEX ON profiles_profile (occupation);` |
| `posts_post` | `upvotes` | ORDER BY у `PostListAPIView` і `TopPostsListAPIView` | `CREATE INDEX ON posts_post (upvotes DESC);` |
| `common_contentview` | `(content_type_id, object_id)` | фільтрація `get_view_count` | `CREATE INDEX ON common_contentview (content_type_id, object_id);` |

> **Примітка:** `ForeignKey`-поля (`reported_by_id`, `assigned_to_id`, `tenant_id` тощо) вже мають індекси автоматично від Django. Перераховані вище — тільки *не-FK* поля.

---

## 📋 Міграції — зауваження

**`profiles` app** має 6 міграцій із squash-кандидатами:
```
0001_initial.py
0002_initial.py          ← дубль імені (конфлікт merge)
0002_alter_profile_avatar.py
0004_merge_0002_initial_0003_alter_profile_avatar.py
0005_alter_profile_occupation.py
0007_building_fk_to_m2m.py   ← пропущений 0006!
```

Рекомендовано виконати `manage.py squashmigrations profiles 0001 0007` після деплою на staging. Пропуск 0006 вказує на ручне видалення міграції — потрібна перевірка цілісності.

**`apartments` app** має міграцію `0004_data_migrate_apartments_to_units.py` — data migration із RunPython. При squash вона має залишитися або бути перетворена на RunSQL з ідемпотентним скриптом.

---

## 🔧 Зведений пріоритет виправлень

| # | Проблема | Вплив | Складність виправлення |
|---|---|---|---|
| 1 | `IssueSerializer.get_view_count()` N+1 | 🔴 Критичний | Низька |
| 2 | `BasePostSerializer.get_view_count()` N+1 | 🔴 Критичний | Низька |
| 3 | `BasePostSerializer.get_avatar()` N+1 | 🔴 Критичний | Низька |
| 4 | `AssignedIssuesListAPIView` — без select_related | 🔴 Критичний | Низька |
| 5 | `Issue.save()` — зайвий SELECT | 🟠 Важливий | Середня |
| 6 | `ProfileListAPIView` — без select_related | 🔴 Критичний | Низька |
| 7 | `ProfileSerializer` — N+1 aggregate | 🟠 Важливий | Середня |
| 8 | `NewsListAPIView` — без select_related | 🟠 Важливий | Низька |
| 9 | `ReportListAPIView` — без select_related | 🟠 Важливий | Низька |
| 10 | `BookmarkPostAPIView` — `.all()` замість `.exists()` | 🟠 Важливий | Низька |
| 11 | `Rating` — відсутній unique_together | 🟡 Схема | Низька |
| 12 | `Report` — CASCADE на nullable FK | 🟡 Схема | Низька |
| 13 | `ContentView.object_id` — 32-bit overflow | 🟡 Схема | Середня |
| 14 | Індекси на `status`, `priority`, `pinned` | 🟠 Важливий | Низька |
