from __future__ import annotations

from typing import Optional

import pytest

from ismypwdsafe.scan_parser import classify_key, parse_env_text


def test_parser_handles_quotes_comments_export_and_continuations() -> None:
    text = "\n".join(
        [
            "# comment",
            "export DB_PASSWORD=\"hunter2 # still value\" # trailing comment",
            "SINGLE_QUOTED='a # b'",
            "UNQUOTED=a#b",
            "UNQUOTED_COMMENT=a # b",
            "MULTI=hello\\",
            "world",
            "EMPTY=",
            "REFERENCE=${DB_PASSWORD}",
            "PLACEHOLDER=changeme",
            "MALFORMED LINE",
            "PASSWORD=password",
        ]
    )

    result = parse_env_text(text)
    entries = {entry.key: entry for entry in result.entries}

    assert entries["DB_PASSWORD"].value == "hunter2 # still value"
    assert entries["DB_PASSWORD"].line == 2
    assert entries["SINGLE_QUOTED"].value == "a # b"
    assert entries["UNQUOTED"].value == "a#b"
    assert entries["UNQUOTED_COMMENT"].value == "a"
    assert entries["MULTI"].value == "helloworld"
    assert entries["PASSWORD"].value == "password"
    assert "EMPTY" not in entries
    assert "REFERENCE" not in entries
    assert "PLACEHOLDER" not in entries
    assert result.empty_values == 1
    assert result.references == 1
    assert result.placeholders == 1
    assert result.unparseable_lines == 1
    assert any("missing '='" in warning for warning in result.warnings)


def test_parser_handles_crlf_and_bom() -> None:
    result = parse_env_text("\ufeffPASSWORD=secret\r\nAPI_KEY=token\r\n")
    assert [(entry.key, entry.value, entry.line) for entry in result.entries] == [
        ("PASSWORD", "secret", 1),
        ("API_KEY", "token", 2),
    ]


def test_parser_rejects_unterminated_and_trailing_characters() -> None:
    result = parse_env_text(
        "\n".join(
            [
                "A=\"unterminated",
                "B='unterminated",
                "C=\"value\" trailing",
                "D=good",
            ]
        )
    )
    assert [entry.key for entry in result.entries] == ["D"]
    assert result.unparseable_lines == 3


def test_parser_decodes_double_quote_escapes() -> None:
    result = parse_env_text('PASSWORD="a\\"b\\\\c\\n"\n')
    assert result.entries[0].value == 'a"b\\c\n'


@pytest.mark.parametrize(
    "key, expected",
    [
        ("DB_PASSWORD", "password"),
        ("USER_PASSWORD", "password"),
        ("PASSWD", "password"),
        ("APP_PASSPHRASE", "password"),
        ("PWD", "password"),
        ("API_KEY", "token"),
        ("SECRET_KEY", "token"),
        ("CLIENT_SECRET", "token"),
        ("AUTH_TOKEN", "token"),
        ("PRIVATE_KEY", "token"),
        ("AWS_SECRET_ACCESS_KEY", "token"),
        ("PASSWORD_HASH", None),
        ("PASSWORD_SALT", None),
        ("PASSWORD_FILE", None),
        ("PASSWORD_RESET_TOKEN", None),
        ("PASSWORD_MIN_LENGTH", None),
        ("PASSWORD_STRENGTH", None),
        ("API_KEY_ID", None),
        ("DATABASE_URL", None),
        ("not-a-key", None),
    ],
)
def test_key_classification(key: str, expected: Optional[str]) -> None:
    assert classify_key(key) == expected


@pytest.mark.parametrize(
    "header",
    [
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
        "-----BEGIN DSA PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        "-----BEGIN PGP PRIVATE KEY BLOCK-----",
        "---- BEGIN SSH2 ENCRYPTED PRIVATE KEY ----",
    ],
)
def test_private_key_headers_are_critical(header: str) -> None:
    text = f"SSH_KEY={header}\nnot-a-real-key\n"
    result = parse_env_text(text)
    assert len(result.critical) == 1
    assert result.critical[0].key == "SSH_KEY"
    assert result.critical[0].line == 1
    assert "PRIVATE KEY" in result.critical[0].key_format
