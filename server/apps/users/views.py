# Imports
import logging
import uuid
from typing import Dict, Optional

from django.conf import settings
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Get the logger
logger = logging.getLogger(__name__)


# Function to set the authentication cookies
def set_auth_cookies(
    res: Response, access_token: str, refresh_token: Optional[str] = None
) -> None:
    """Set the authentication cookies.

    Args:
        res (Response): The response object.
        access_token (str): The access token.
        refresh_token (Optional[str]): The refresh token.
    """

    # Get the access token lifetime from settings
    access_token_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()

    # Get the cookie settings
    cookie_settings = {
        "path": settings.COOKIE_PATH,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTPONLY,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": access_token_lifetime,
    }

    # Set the access token cookie
    res.set_cookie("access", access_token, **cookie_settings)

    # If the refresh token is provided
    if refresh_token:
        # Get the refresh token lifetime from settings
        refresh_token_lifetime = settings.SIMPLE_JWT[
            "REFRESH_TOKEN_LIFETIME"
        ].total_seconds()

        # Make a copy of the cookie settings
        refresh_cookie_settings = cookie_settings.copy()

        # Update the max age for the refresh token
        refresh_cookie_settings["max_age"] = refresh_token_lifetime

        # Set the refresh token cookie
        res.set_cookie("refresh", refresh_token, **refresh_cookie_settings)

    # Make a copy of the cookie settings
    logged_in_cookie_settings = cookie_settings.copy()

    # Set the httponly to False
    logged_in_cookie_settings["httponly"] = False

    # Set the logged in cookie
    res.set_cookie("logged_in", "true", **logged_in_cookie_settings)


# Custom Token Obtain Pair API View
class CustomTokenObtainPairAPIView(TokenObtainPairView):
    """Custom Token Obtain Pair API View

    This class extends the TokenObtainPairView class to set the authentication cookies.

    Extends:
        TokenObtainPairView

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
            Response: The response object
        """

        # Get the response
        res = super().post(request, *args, **kwargs)

        # If the status code is 200
        if res.status_code == status.HTTP_200_OK:
            # Get the access and refresh tokens
            access_token = res.data.get("access")
            refresh_token = res.data.get("refresh")

            # If the access and refresh tokens are provided
            if access_token and refresh_token:
                # Set the authentication cookies
                set_auth_cookies(res, access_token, refresh_token)

                # Remove the access and refresh tokens from the response data
                res.data.pop("access")
                res.data.pop("refresh")

                # Add the message to the response data
                res.data["message"] = "Login successful."

            # Else
            else:
                # Add the message to the response data
                res.data["message"] = "Login failed."

                # Log the error
                logger.error("Access or refresh token not provided in response data.")

        # Return the response
        return res


# Custom Token Refresh API View
class CustomTokenRefreshAPIView(TokenRefreshView):
    """Custom Token Refresh API View

    This class extends the TokenRefreshView class to set the authentication cookies.

    Args:
        TokenRefreshView

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

        # Get the refresh token from the cookies
        refresh_token = request.COOKIES.get("refresh")

        # If the refresh token is provided
        if refresh_token:
            # Add the refresh token to the request data
            request.data["refresh"] = refresh_token

        # Get the response
        res = super().post(request, *args, **kwargs)

        # If the status code is 200
        if res.status_code == status.HTTP_200_OK:
            # Get the access and refresh tokens
            access_token = res.data.get("access")
            refresh_token = res.data.get("refresh")

            # If the access and refresh tokens are provided
            if access_token and refresh_token:
                # Set the authentication cookies
                set_auth_cookies(res, access_token, refresh_token)

                # Remove the access and refresh tokens from the response data
                res.data.pop("access")
                res.data.pop("refresh")

                # Add the message to the response data
                res.data["message"] = "Access token refreshed successfully."

            # Else
            else:
                # Add the message to the response data
                res.data["message"] = (
                    "Access or refresh token not provided in response data."
                )

                # Log the error
                logger.error("Access or refresh token not provided in response data.")

        # Return the response
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
        res.delete_cookie("access")
        res.delete_cookie("refresh")
        res.delete_cookie("logged_in")
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
