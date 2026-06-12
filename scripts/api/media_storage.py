from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from google.auth import default as google_auth_default
from google.auth import impersonated_credentials
from google.auth.compute_engine import Credentials as ComputeEngineCredentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.cloud import storage


UPLOAD_URL_EXPIRY = timedelta(minutes=15)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

DEFAULT_PLACE_MEDIA_BUCKET = "on-the-block-place-media"
DEFAULT_PRODUCT_MEDIA_BUCKET = "on-the-block-product-media"


@dataclass(frozen=True)
class UploadUrlResult:
    upload_url: str
    object_url: str


class MediaStorageService:
    """Generates V4 signed upload URLs for place/menu and product media buckets.

    Mirrors authorization-service's ProfileStorageService: on Cloud Run the
    attached service account self-signs via the IAM signBlob API (requires
    roles/iam.serviceAccountTokenCreator on itself). For local development,
    set SIGNING_SERVICE_ACCOUNT to impersonate a service account with that role.
    """

    def __init__(
        self,
        *,
        place_media_bucket: str | None = None,
        product_media_bucket: str | None = None,
        signing_service_account: str | None = None,
    ) -> None:
        self.place_media_bucket = place_media_bucket or os.environ.get(
            "MAP_SERVICE_PLACE_MEDIA_BUCKET", DEFAULT_PLACE_MEDIA_BUCKET
        )
        self.product_media_bucket = product_media_bucket or os.environ.get(
            "MAP_SERVICE_PRODUCT_MEDIA_BUCKET", DEFAULT_PRODUCT_MEDIA_BUCKET
        )
        self.signing_service_account = signing_service_account or os.environ.get(
            "SIGNING_SERVICE_ACCOUNT", ""
        )
        self._client: storage.Client | None = None

    def generate_place_photo_upload_url(self, marker_id: str, content_type: str) -> UploadUrlResult:
        ext = _require_extension(content_type)
        object_name = f"places/{marker_id}/{uuid.uuid4()}.{ext}"
        return self._sign(self.place_media_bucket, object_name, content_type)

    def generate_menu_photo_upload_url(self, marker_id: str, content_type: str) -> UploadUrlResult:
        ext = _require_extension(content_type)
        object_name = f"menu/{marker_id}/{uuid.uuid4()}.{ext}"
        return self._sign(self.place_media_bucket, object_name, content_type)

    def generate_product_photo_upload_url(self, product_id: str, content_type: str) -> UploadUrlResult:
        ext = _require_extension(content_type)
        object_name = f"whiskies/{product_id}/{uuid.uuid4()}.{ext}"
        return self._sign(self.product_media_bucket, object_name, content_type)

    def _sign(self, bucket_name: str, object_name: str, content_type: str) -> UploadUrlResult:
        client = self._storage_client()
        blob = client.bucket(bucket_name).blob(object_name)
        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=UPLOAD_URL_EXPIRY,
            method="PUT",
            content_type=content_type,
            **self._signing_kwargs(),
        )
        object_url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
        return UploadUrlResult(upload_url=upload_url, object_url=object_url)

    def _storage_client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client()
        return self._client

    def _signing_kwargs(self) -> dict[str, Any]:
        # Local dev: impersonate a service account that can self-sign (Signing credentials).
        if self.signing_service_account:
            source_credentials, _project = google_auth_default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials = impersonated_credentials.Credentials(
                source_credentials=source_credentials,
                target_principal=self.signing_service_account,
                target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
                lifetime=300,
            )
            return {"credentials": credentials}

        # Cloud Run: the attached compute service account can't sign locally, so sign via
        # the IAM signBlob API using its own access token (requires
        # roles/iam.serviceAccountTokenCreator granted to the SA on itself).
        credentials, _project = google_auth_default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(GoogleAuthRequest())
        service_account_email = getattr(credentials, "service_account_email", None)
        if isinstance(credentials, ComputeEngineCredentials) and service_account_email:
            return {"service_account_email": service_account_email, "access_token": credentials.token}
        return {"credentials": credentials}


def _require_extension(content_type: str) -> str:
    ext = ALLOWED_CONTENT_TYPES.get(content_type.lower())
    if ext is None:
        raise ValueError(
            "content_type must be one of: " + ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        )
    return ext
