from base64 import b64encode

from iot_home.dashboard import basic_auth_valid


def basic(value: str) -> str:
    return "Basic " + b64encode(value.encode("utf-8")).decode("ascii")


def test_basic_auth_allows_when_not_configured():
    assert basic_auth_valid(None, None, None)


def test_basic_auth_accepts_matching_credentials():
    assert basic_auth_valid(basic("operator:secret"), "operator", "secret")


def test_basic_auth_rejects_missing_or_wrong_credentials():
    assert not basic_auth_valid(None, "operator", "secret")
    assert not basic_auth_valid(basic("operator:wrong"), "operator", "secret")
    assert not basic_auth_valid(basic("wrong:secret"), "operator", "secret")
    assert not basic_auth_valid("Bearer token", "operator", "secret")
