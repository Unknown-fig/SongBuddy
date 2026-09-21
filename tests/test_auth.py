import pytest
from auth import auth_manager, extract_bearer_token

def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = auth_manager.hash_password(password)
    
    assert hashed != password
    assert auth_manager.verify_password(password, hashed) is True
    assert auth_manager.verify_password("WrongPassword!", hashed) is False

def test_jwt_token_lifecycle():
    user_id = "test_user"
    token = auth_manager.create_access_token(user_id=user_id, scopes=["read", "stream"])
    
    assert isinstance(token, str)
    assert len(token) > 20

    payload = auth_manager.verify_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert "stream" in payload["scopes"]

def test_jwt_token_revocation():
    user_id = "revocation_user"
    token = auth_manager.create_access_token(user_id=user_id)
    
    assert auth_manager.verify_token(token) is not None
    
    # Revoke the token
    auth_manager.revoke_token(token)
    
    # Verification should now fail
    assert auth_manager.verify_token(token) is None

def test_extract_bearer_token():
    assert extract_bearer_token("Bearer abc123xyz") == "abc123xyz"
    assert extract_bearer_token("bearer  my_token ") == "my_token"
    assert extract_bearer_token("Basic dXNlcjpwYXNz") is None
    assert extract_bearer_token(None) is None
    assert extract_bearer_token("") is None
