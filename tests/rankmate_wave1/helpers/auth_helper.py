"""Authentication helpers for Wave 1 API tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from .api_client import RankmateApiClient
from .assertion_helper import envelope_data


@dataclass(frozen=True)
class AuthSession:
    token: str
    refresh_token: str
    user_type: Optional[int] = None


class AuthHelper:
    def __init__(
        self,
        client: RankmateApiClient,
        *,
        phone_number: str = "string",
        campaign: str = "string",
        device_id: str = "string",
    ):
        self.client = client
        self.phone_number = self._fallback_string(phone_number)
        self.campaign = self._fallback_string(campaign)
        self.device_id = self._fallback_string(device_id)

    @staticmethod
    def _fallback_string(value: Optional[str]) -> str:
        if value is None:
            return "string"
        candidate = str(value).strip()
        return candidate if candidate else "string"

    def login(
        self,
        *,
        email: str,
        password: str,
        phone_number: Optional[str] = None,
        campaign: Optional[str] = None,
        device_id: Optional[str] = None,
    ):
        resolved_phone_number = self._fallback_string(phone_number) if phone_number is not None else self.phone_number
        resolved_campaign = self._fallback_string(campaign) if campaign is not None else self.campaign
        resolved_device_id = self._fallback_string(device_id) if device_id is not None else self.device_id

        payload = {
            "email": email,
            "password": password,
            "phoneNumber": resolved_phone_number,
            "campaign": resolved_campaign,
            "deviceID": resolved_device_id,
        }

        # Temporary runtime contract debug to verify login payload shape exactly matches Swagger.
        print(f"[Wave1API][AuthHelper.login] payload={payload}")

        # RankmateApiClient.request sends json=json_body (not form data).
        return self.client.post("/auth/login", json_body=payload)

    def refresh_token(self, *, token: str, refresh_token: str):
        return self.client.post(
            "/auth/refresh-token",
            json_body={"token": token, "refreshToken": refresh_token},
        )

    def logout(self, *, token: str, refresh_token: Optional[str] = None):
        payload = {
            "token": token,
            "refreshToken": refresh_token or "",
        }
        return self.client.post("/auth/logout", token=token, json_body=payload)

    def extract_session(self, payload: Mapping[str, object]) -> AuthSession:
        data = envelope_data(payload)
        if not isinstance(data, Mapping):
            raise AssertionError(f"Auth payload missing data envelope: {payload}")

        token = data.get("token")
        refresh_token = data.get("refreshToken")
        user_type = data.get("userType")

        if not isinstance(token, str) or not token.strip():
            raise AssertionError(f"Auth payload missing token: {payload}")
        if not isinstance(refresh_token, str) or not refresh_token.strip():
            raise AssertionError(f"Auth payload missing refreshToken: {payload}")

        return AuthSession(
            token=token,
            refresh_token=refresh_token,
            user_type=user_type if isinstance(user_type, int) else None,
        )
