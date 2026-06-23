"""Optional TOTP 2FA enrollment + enforced login (SRS 4.21)."""
import pyotp
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_2fa_enroll_verify_and_login(client: AsyncClient, admin_user, tenant, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    enroll = await client.post("/api/v1/auth/2fa/enroll", headers=headers)
    assert enroll.status_code == 200
    secret = enroll.json()["secret"]
    assert enroll.json()["provisioning_uri"].startswith("otpauth://")

    # verify with a valid code -> enables 2FA
    code = pyotp.TOTP(secret).now()
    v = await client.post("/api/v1/auth/2fa/verify", json={"code": code}, headers=headers)
    assert v.status_code == 200 and v.json()["enabled"] is True

    # login without OTP now fails
    no_otp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "password123"})
    assert no_otp.status_code == 401

    # login with OTP succeeds
    with_otp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "password123",
        "otp_code": pyotp.TOTP(secret).now()})
    assert with_otp.status_code == 200
    assert "access_token" in with_otp.json()
