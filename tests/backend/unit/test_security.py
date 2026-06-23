"""
Unit tests — app.core.security
================================
Covers: hash_password, verify_password, create_access_token,
        create_refresh_token, decode_token
No database or network I/O required.
"""
import time
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


# ── hash_password / verify_password ──────────────────────────────────────────

class TestHashPassword:
    def test_returns_string(self):
        h = hash_password("secret")
        assert isinstance(h, str)

    def test_not_plaintext(self):
        h = hash_password("secret")
        assert h != "secret"

    def test_different_salts(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt generates unique salts

    def test_verify_correct_password(self):
        h = hash_password("MyP@ss123")
        assert verify_password("MyP@ss123", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("MyP@ss123")
        assert verify_password("WrongPass", h) is False

    def test_verify_empty_password(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("not-empty", h) is False

    def test_unicode_password(self):
        pwd = "pàssw0rd!🔑"
        h = hash_password(pwd)
        assert verify_password(pwd, h) is True


# ── create_access_token / decode_token ───────────────────────────────────────

class TestAccessToken:
    def _payload(self, **extra) -> dict:
        return {"sub": "user-uuid-123", "tenant_id": "tenant-uuid", "role": "admin",
                "is_platform_admin": False, **extra}

    def test_returns_string(self):
        tok = create_access_token(self._payload())
        assert isinstance(tok, str) and len(tok) > 0

    def test_decode_returns_payload(self):
        tok = create_access_token(self._payload())
        data = decode_token(tok)
        assert data is not None
        assert data["sub"] == "user-uuid-123"
        assert data["role"] == "admin"

    def test_token_type_is_access(self):
        tok = create_access_token(self._payload())
        data = decode_token(tok)
        assert data["type"] == "access"

    def test_exp_field_present(self):
        tok = create_access_token(self._payload())
        data = decode_token(tok)
        assert "exp" in data

    def test_decode_invalid_token_returns_none(self):
        assert decode_token("this.is.not.a.token") is None

    def test_decode_tampered_token_returns_none(self):
        tok = create_access_token(self._payload())
        tampered = tok[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_decode_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_extra_claims_preserved(self):
        tok = create_access_token(self._payload(custom="value"))
        data = decode_token(tok)
        assert data["custom"] == "value"


# ── create_refresh_token ──────────────────────────────────────────────────────

class TestRefreshToken:
    def test_returns_three_tuple(self):
        result = create_refresh_token({"sub": "uid", "role": "admin"})
        assert len(result) == 3

    def test_token_is_string(self):
        tok, jti, exp = create_refresh_token({"sub": "uid"})
        assert isinstance(tok, str)

    def test_jti_is_string(self):
        _, jti, _ = create_refresh_token({"sub": "uid"})
        assert isinstance(jti, str) and len(jti) > 0

    def test_custom_jti_preserved(self):
        _, jti, _ = create_refresh_token({"sub": "uid"}, jti="my-custom-jti")
        assert jti == "my-custom-jti"

    def test_token_type_is_refresh(self):
        tok, _, _ = create_refresh_token({"sub": "uid"})
        data = decode_token(tok)
        assert data["type"] == "refresh"

    def test_jti_in_token_payload(self):
        tok, jti, _ = create_refresh_token({"sub": "uid"})
        data = decode_token(tok)
        assert data["jti"] == jti

    def test_expiry_in_future(self):
        from datetime import datetime, timezone
        _, _, exp = create_refresh_token({"sub": "uid"})
        assert exp > datetime.now(timezone.utc)

    def test_unique_jtis_per_call(self):
        _, jti1, _ = create_refresh_token({"sub": "uid"})
        _, jti2, _ = create_refresh_token({"sub": "uid"})
        assert jti1 != jti2
