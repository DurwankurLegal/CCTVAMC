from app.core.security import hash_password, verify_password, create_access_token, decode_token


def test_password_hash_verify():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    data = {"sub": "user-123", "tenant_id": "tenant-456", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123"
    assert decoded["tenant_id"] == "tenant-456"
    assert decoded["type"] == "access"


def test_invalid_token_returns_none():
    assert decode_token("not.a.valid.token") is None
