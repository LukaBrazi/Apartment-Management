# Imports
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class LocalMinioS3Storage(S3Boto3Storage):
    """⚠️ DEV-ONLY: Custom S3 storage для local MinIO без TLS.

    Метод ``url()`` робить ``https → http`` downgrade — це навмисно для
    local MinIO, який слухає ``http://localhost:8080`` без TLS. Без цього
    downgrade ``S3Boto3Storage`` згенерує ``https://`` URL, який браузер не
    зможе завантажити.

    **НЕ використовувати у staging/production.** У production
    ``config/settings/production.py`` імпортує
    ``storages.backends.s3boto3.S3Boto3Storage`` напряму через
    ``STORAGES["default"]["BACKEND"]`` — TLS обов'язковий, custom_domain
    приходить з R2 (Cloudflare R2 завжди https).
    """

    # Constructor
    def __init__(self, *args, **kwargs):
        # Call the parent constructor
        super().__init__(*args, **kwargs)

        # Set the endpoint URL and custom domain
        self.endpoint_url = settings.AWS_S3_ENDPOINT_URL
        self.custom_domain = settings.AWS_S3_CUSTOM_DOMAIN

    # Method to return the URL of the file
    def url(self, name, parameters=None, expire=None):
        """Return the URL of the file with an https→http downgrade.

        Local MinIO has no TLS, so we strip ``https://`` → ``http://`` to
        let the browser fetch the file. This downgrade is the entire reason
        this subclass exists; in production we use the upstream
        ``S3Boto3Storage`` directly.
        """
        url = super().url(name, parameters, expire)
        if url.startswith("https"):
            url = "http" + url[5:]
        return url


class StaticStorage(LocalMinioS3Storage):
    """⚠️ DEV-ONLY static-files storage backend (MinIO).

    Public ACL because static files (JS/CSS/images) are served to anonymous
    visitors. ``file_overwrite=False`` keeps deterministic URLs across
    redeploys for the same content hash.
    """

    # Attributes
    location = "static"
    default_acl = "public-read"
    querystring_auth = False
    file_overwrite = False


class MediaStorage(LocalMinioS3Storage):
    """⚠️ DEV-ONLY media-files storage backend (MinIO).

    Private ACL — user uploads (avatars, issue attachments) require signed
    URLs to read. ``file_overwrite=False`` prevents accidental clobbering
    of an existing user's avatar by another upload with the same filename.
    """

    # Attributes
    location = "media"
    default_acl = "private"
    file_overwrite = False
