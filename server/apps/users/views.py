# Imports
import logging
import uuid
from datetime import timedelta
from typing import Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.serializers import RememberAwareTokenObtainPairSerializer

# Get the logger
logger = logging.getLogger(__name__)

# Get the user model
UserModel = get_user_model()


def _clear_auth_cookies(res: Response) -> None:
    """Clear all three auth cookies (access, refresh, logged_in).

    Used when an auth action fails in a way that should end the session —
    e.g. refresh-for-deleted-user. Ensures the client's `logged_in=true`
    marker is wiped so `ProtectedRoute` stops treating the browser as
    authenticated and lets the user reach /login.
    """
    res.delete_cookie("access", path=settings.COOKIE_PATH)
    res.delete_cookie("refresh", path=settings.COOKIE_PATH)
    res.delete_cookie("logged_in", path=settings.COOKIE_PATH)


# Function to set the authentication cookies
def set_auth_cookies(
    res: Response,
    access_token: str,
    refresh_token: Optional[str] = None,
    *,
    remember: bool = False,
) -> None:
    """Write the auth cookies (access / refresh / logged_in) onto a response.

    Args:
        res: The response object.
        access_token: Signed access JWT (goes into the HttpOnly `access`
            cookie).
        refresh_token: Signed refresh JWT (goes into the HttpOnly
            `refresh` cookie). When None, the refresh cookie is left
            untouched — used by call sites that only rotate the access
            token.
        remember: Controls the lifetime of the `refresh` and `logged_in`
            cookies:

              - True  → Max-Age = settings.REMEMBER_ME_REFRESH_LIFETIME
                        (default 14 days). The session survives browser
                        restarts until the refresh JWT itself expires.
              - False → Max-Age omitted → session cookies. Browser drops
                        them when the last tab closes, so the user must
                        re-authenticate on next visit.

            The `access` cookie always uses ACCESS_TOKEN_LIFETIME as its
            Max-Age regardless of `remember`, because the JWT inside is
            short-lived by design and a stale cookie would just get
            refreshed via baseQueryWithReauth on the client.
    """
    access_token_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()

    # Persistent Max-Age for refresh + logged_in cookies.
    #   remember=True  → integer seconds (14 days default)
    #   remember=False → None → Django emits no Max-Age header → session cookie.
    persistent_max_age: Optional[float]
    if remember:
        persistent_max_age = getattr(
            settings,
            "REMEMBER_ME_REFRESH_LIFETIME",
            timedelta(days=14),
        ).total_seconds()
    else:
        persistent_max_age = None

    base_cookie_kwargs = {
        "path": settings.COOKIE_PATH,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTPONLY,
        "samesite": settings.COOKIE_SAMESITE,
    }

    # Access cookie — always short-lived; its JWT is ephemeral so a
    # longer cookie Max-Age would just mask expiry until the next request.
    res.set_cookie(
        "access",
        access_token,
        max_age=access_token_lifetime,
        **base_cookie_kwargs,
    )

    # Refresh cookie — Max-Age mirrors `remember`.
    if refresh_token:
        res.set_cookie(
            "refresh",
            refresh_token,
            max_age=persistent_max_age,
            **base_cookie_kwargs,
        )

    # `logged_in` is the client-visible marker ProtectedRoute consults.
    # It must NOT be HttpOnly (JS reads it), and its lifetime must match
    # the refresh cookie so the gate and the tokens die together.
    logged_in_cookie_kwargs = {**base_cookie_kwargs, "httponly": False}
    res.set_cookie(
        "logged_in",
        "true",
        max_age=persistent_max_age,
        **logged_in_cookie_kwargs,
    )


# Custom Token Obtain Pair API View
class CustomTokenObtainPairAPIView(TokenObtainPairView):
    """Custom Token Obtain Pair API View

    Extends SimpleJWT's TokenObtainPairView to:

      1. Use RememberAwareTokenObtainPairSerializer, which accepts a
         `remember_me` boolean and bakes a `remember: true` claim into
         the refresh token when set.
      2. Move access + refresh tokens from the response body into
         HttpOnly cookies (the SPA never touches raw tokens).
      3. Adjust cookie Max-Age based on `remember_me` so a ticked
         checkbox produces a 14-day persistent session while an unticked
         one yields a session cookie that dies on browser close.

    Extends:
        TokenObtainPairView
    """

    serializer_class = RememberAwareTokenObtainPairSerializer
    throttle_scope = "login"

    def post(self, request: Request, *args: Dict, **kwargs: Dict) -> Response:
        """Handle the POST request.

        Args:
            request (Request): The request object.
            *args (dict): The arguments.
            **kwargs (dict): The keyword arguments.

        Returns:
            Response: The response object.
        """
        # Read `remember_me` from input BEFORE super() runs — the serializer
        # will pop it during validation, so we capture it here once to
        # drive cookie Max-Age post-response. Missing / non-boolean values
        # default to False (safest: a typo must not silently extend the
        # session).
        remember = bool(request.data.get("remember_me", False))

        res = super().post(request, *args, **kwargs)

        if res.status_code == status.HTTP_200_OK:
            access_token = res.data.get("access")
            refresh_token = res.data.get("refresh")

            if access_token and refresh_token:
                set_auth_cookies(
                    res, access_token, refresh_token, remember=remember
                )
                res.data.pop("access")
                res.data.pop("refresh")
                res.data["message"] = "Login successful."
            else:
                res.data["message"] = "Login failed."
                logger.error("Access or refresh token not provided in response data.")

        return res


# Custom Token Refresh API View
class CustomTokenRefreshAPIView(TokenRefreshView):
    """Custom Token Refresh API View

    Rotates the refresh token *manually* instead of delegating to
    TokenRefreshSerializer, because we need three things the stock
    serializer doesn't give us:

      1. **Ghost-session guard.** If the user was deleted / anonymized
         while the refresh cookie was still live, newer SimpleJWT raises
         User.DoesNotExist deep inside validation and the SPA sees a 500
         that it interprets as "retry later" — producing an infinite
         refresh loop that traps the browser on /welcome. We detect the
         missing user explicitly, blacklist the token, clear cookies,
         and return 401 code=user_not_found.

      2. **Remember-me claim preservation.** The refresh token carries a
         `remember: true` claim when the user ticked the box at login.
         On rotation, the NEW refresh token must also carry that claim
         and its `exp` must be extended to the remember-me lifetime;
         otherwise the persistence would silently degrade to 5 minutes
         after the first auto-refresh.

      3. **Consistent cookie Max-Age across rotations.** The refresh +
         logged_in cookies' Max-Age is derived from the claim above, so
         Remember sessions stay persistent and non-Remember sessions
         stay session-only even after dozens of rotations.

    Failure modes we fall back to SimpleJWT's default handling:
      - Missing refresh cookie → super() returns 400 (contract pin).
      - Invalid / expired / blacklisted token → super() returns 401
        token_not_valid (contract pin).

    Args:
        TokenRefreshView
    """

    def post(self, request: Request, *args: Dict, **kwargs: Dict) -> Response:
        """Handle the POST request.

        Args:
            request (Request): The request object.
            *args (dict): The arguments.
            **kwargs (dict): The keyword arguments.

        Returns:
            Response: The response object.
        """
        refresh_token = request.COOKIES.get("refresh")

        # No cookie → defer to SimpleJWT's stock serializer, which emits
        # a 400 validation error. Keeps test_refresh_without_cookie_*
        # contract stable.
        if not refresh_token:
            return super().post(request, *args, **kwargs)

        # Make the cookie token available for SimpleJWT's error path.
        request.data["refresh"] = refresh_token

        # Validate the token (signature, exp, blacklist) upfront. Any
        # failure here falls back to super() so tampered / expired
        # tokens get SimpleJWT's canonical 401 token_not_valid response.
        try:
            rt = RefreshToken(refresh_token)
        except TokenError:
            return super().post(request, *args, **kwargs)

        user_id = rt.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])

        # ── Ghost-session guard ──
        # Token signature is valid but the subject was removed /
        # deactivated. End the session cleanly.
        try:
            user = UserModel.objects.get(
                **{settings.SIMPLE_JWT["USER_ID_FIELD"]: user_id},
                is_active=True,
            )
        except UserModel.DoesNotExist:
            logger.warning(
                "Refresh attempted for non-existent/inactive user (id=%s). "
                "Blacklisting token and clearing cookies.",
                user_id,
            )
            try:
                rt.blacklist()
            except (TokenError, AttributeError):
                # blacklist() can raise if token_blacklist isn't installed
                # or if the token is already blacklisted.
                pass

            res = Response(
                {"detail": "User not found.", "code": "user_not_found"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_auth_cookies(res)
            return res

        # ── Remember-me aware rotation ──
        # Read the claim from the OLD token — it's the source of truth
        # for whether the session was marked persistent at login.
        remember = bool(rt.get("remember", False))

        # Emulate BLACKLIST_AFTER_ROTATION — blacklist the old token
        # before we hand out a replacement so a stolen copy can't be
        # reused in parallel with the new one.
        if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION", False):
            try:
                rt.blacklist()
            except (TokenError, AttributeError):
                pass

        # Mint the replacement pair. for_user() creates a fresh
        # OutstandingToken row with the correct expires_at derived from
        # the token's final exp, so blacklist bookkeeping stays clean.
        new_rt = RefreshToken.for_user(user)
        new_rt["remember"] = remember
        if remember:
            new_rt.set_exp(
                lifetime=getattr(
                    settings,
                    "REMEMBER_ME_REFRESH_LIFETIME",
                    timedelta(days=14),
                )
            )
        new_access = new_rt.access_token

        res = Response(
            {"message": "Access token refreshed successfully."},
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(
            res, str(new_access), str(new_rt), remember=remember
        )
        return res


# ── GDPR: Right to Access (Data Export) ──────────────────────────────────────

class GDPRDataExportAPIView(APIView):
    """GDPRDataExportAPIView

    GDPR Art. 15 + Art. 20 — Right of Access and Right to Data Portability.

    Returns a structured JSON snapshot of all personal data held for the
    authenticated user: account info, profile, issues, ratings, reports,
    vehicle passes, and posts.

    GET /api/v1/auth/my-data/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, *args: Dict, **kwargs: Dict) -> Response:
        from apps.common.models import GDPRAuditLog
        from apps.issues.models import Issue
        from apps.passes.models import VehiclePass
        from apps.posts.models import Post
        from apps.ratings.models import Rating
        from apps.reports.models import Report

        user = request.user

        # Audit log
        GDPRAuditLog.log(
            event=GDPRAuditLog.EventType.DATA_EXPORT,
            subject=user,
            actor=user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        profile = getattr(user, "profile", None)

        # ── Account data ──────────────────────────────────────────────────────
        account = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat(),
            "is_active": user.is_active,
        }

        # ── Profile data ──────────────────────────────────────────────────────
        profile_data = {}
        if profile:
            profile_data = {
                "gender": profile.gender,
                "bio": profile.bio or "",
                "occupation": profile.occupation,
                "phone_number": str(profile.phone_number) if profile.phone_number else "",
                "country_of_origin": str(profile.country_of_origin),
                "city_of_origin": profile.city_of_origin,
                "reputation": profile.reputation,
                "report_count": profile.report_count,
            }

        # ── Issues reported by user ───────────────────────────────────────────
        issues = list(
            Issue.objects.filter(reported_by=user).values(
                "pkid", "title", "status", "priority", "created_at"
            )
        )
        for i in issues:
            i["pkid"] = str(i["pkid"])
            i["created_at"] = i["created_at"].isoformat()

        # ── Ratings given by user ─────────────────────────────────────────────
        ratings_given = list(
            Rating.objects.filter(rating_user=user).values(
                "pkid", "rating", "comment", "created_at"
            )
        )
        for r in ratings_given:
            r["pkid"] = str(r["pkid"])
            r["created_at"] = r["created_at"].isoformat()

        # ── Reports filed by user ─────────────────────────────────────────────
        reports_made = list(
            Report.objects.filter(reported_by=user).values(
                "pkid", "title", "description", "created_at"
            )
        )
        for r in reports_made:
            r["pkid"] = str(r["pkid"])
            r["created_at"] = r["created_at"].isoformat()

        # ── Vehicle passes ────────────────────────────────────────────────────
        passes = list(
            VehiclePass.objects.filter(tenant=user).values(
                "pkid", "car_number", "visit_date", "status", "created_at"
            )
        )
        for p in passes:
            p["pkid"] = str(p["pkid"])
            p["visit_date"] = p["visit_date"].isoformat()
            p["created_at"] = p["created_at"].isoformat()

        # ── Posts authored by user ────────────────────────────────────────────
        posts = list(
            Post.objects.filter(author=user).values("pkid", "title", "created_at")
        )
        for p in posts:
            p["pkid"] = str(p["pkid"])
            p["created_at"] = p["created_at"].isoformat()

        payload = {
            "account": account,
            "profile": profile_data,
            "issues": issues,
            "ratings_given": ratings_given,
            "reports_made": reports_made,
            "vehicle_passes": passes,
            "posts": posts,
            "exported_at": __import__("django.utils.timezone", fromlist=["now"]).now().isoformat(),
        }

        return Response(payload, status=status.HTTP_200_OK)


# ── GDPR: Right to Erasure ────────────────────────────────────────────────────

class GDPREraseAccountAPIView(APIView):
    """GDPREraseAccountAPIView

    GDPR Art. 17 — Right to Erasure.

    Pseudonymizes the authenticated user's personal data in-place so that
    business records (issues, ratings, passes, etc.) are preserved with a
    NULL or anonymized FK, while the personal-data link is severed.

    Steps:
      1. Pseudonymize User fields (email, username, first/last name)
      2. Deactivate the account
      3. Clear Profile personal fields (bio, phone, avatar)
      4. Blacklist the current refresh token so no further logins are possible
      5. Clear auth cookies and return 200

    POST /api/v1/auth/user/anonymize/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request, *args: Dict, **kwargs: Dict) -> Response:
        user = request.user
        anon_id = str(uuid.uuid4()).replace("-", "")[:20]

        with transaction.atomic():
            from apps.common.models import GDPRAuditLog

            # Audit: log the erasure request before anonymizing
            GDPRAuditLog.log(
                event=GDPRAuditLog.EventType.ACCOUNT_ANONYMIZED,
                subject=user,
                actor=user,
                detail=f"Self-requested via POST /api/v1/auth/anonymize/ original_email={user.email}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            # 1. Pseudonymize User fields
            user.email = f"deleted_{anon_id}@gdpr.invalid"
            user.username = f"deleted_{anon_id}"
            user.first_name = ""
            user.last_name = ""
            user.is_active = False
            user.save(
                update_fields=["email", "username", "first_name", "last_name", "is_active"]
            )

            # 2. Clear Profile personal data
            profile = getattr(user, "profile", None)
            if profile:
                profile.bio = ""
                profile.phone_number = "+10000000000"  # placeholder, not real
                profile.city_of_origin = ""
                profile.avatar = None
                profile.save(
                    update_fields=["bio", "phone_number", "city_of_origin", "avatar"]
                )

        # 3. Blacklist JWT refresh token
        refresh_token = request.COOKIES.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        # 4. Clear auth cookies and return
        res = Response(
            {"message": "Your account has been anonymized. Goodbye."},
            status=status.HTTP_200_OK,
        )
        res.delete_cookie("access", path=settings.COOKIE_PATH)
        res.delete_cookie("refresh", path=settings.COOKIE_PATH)
        res.delete_cookie("logged_in", path=settings.COOKIE_PATH)
        return res


# Logout API View
class LogoutAPIView(APIView):
    """Logout API View

    This class is used to logout the user by deleting the authentication cookies.

    Extends:
        APIView

    Methods:
        post(request: Request, *args: Dict, **kwargs: Dict) -> Response: Handle the POST request.

    Returns:
        Response: The response object.
    """

    # Method to handle the POST request
    def post(self, request: Request, *args: Dict, **kwargs: Dict) -> Response:
        """Handle the POST request.

        Args:
            request (Request): The request object.
            *args (dict): The arguments.
            **kwargs (dict): The keyword arguments.

        Returns:
            Response: The response object.
        """

        # Blacklist the refresh token so it can't be reused after logout
        refresh_token = request.COOKIES.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                # Token already invalid or expired — safe to ignore
                pass

        # Create a response object
        res = Response(status=status.HTTP_204_NO_CONTENT)

        # Delete the authentication cookies
        res.delete_cookie("access")
        res.delete_cookie("refresh")
        res.delete_cookie("logged_in")

        # Return the response
        return res
