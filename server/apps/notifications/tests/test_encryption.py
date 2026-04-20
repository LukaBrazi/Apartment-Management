"""Unit tests for the Fernet token-encryption module.

The module is tiny but carries a lot of weight — every Telegram bot
token in the platform ends up encrypted through it. These tests nail
down the contract so a refactor can't silently break at-rest secrecy.
"""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.notifications.encryption import (
    decrypt_token,
    encrypt_token,
    mask_token,
)


class TestRoundTrip:
    def test_encrypt_then_decrypt_returns_original(self):
        plaintext = "123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        ciphertext = encrypt_token(plaintext)
        assert ciphertext != plaintext
        assert decrypt_token(ciphertext) == plaintext

    def test_encrypt_empty_string_returns_empty(self):
        assert encrypt_token("") == ""

    def test_decrypt_empty_string_returns_empty(self):
        assert decrypt_token("") == ""

    def test_ciphertext_is_ascii(self):
        """Ciphertext must fit in a TextField without encoding drama."""
        ciphertext = encrypt_token("123:abc")
        ciphertext.encode("ascii")  # raises UnicodeEncodeError if not ASCII

    def test_two_encryptions_of_same_plaintext_differ(self):
        """Fernet includes a random IV — ciphertexts must diverge."""
        a = encrypt_token("same-token")
        b = encrypt_token("same-token")
        assert a != b
        assert decrypt_token(a) == decrypt_token(b) == "same-token"


class TestErrorPaths:
    def test_missing_key_raises_improperly_configured(self):
        with override_settings(
            TELEGRAM_BOT_ENCRYPTION_KEY="",
            TELEGRAM_BOT_ENCRYPTION_KEYS=[],
        ):
            with pytest.raises(ImproperlyConfigured):
                encrypt_token("anything")

    def test_invalid_key_format_raises_improperly_configured(self):
        with override_settings(TELEGRAM_BOT_ENCRYPTION_KEY="not-a-valid-fernet-key"):
            with pytest.raises(ImproperlyConfigured):
                encrypt_token("anything")

    def test_decrypt_with_wrong_key_raises_invalid_token(self):
        ciphertext = encrypt_token("secret")
        foreign_key = Fernet.generate_key().decode("ascii")
        with override_settings(TELEGRAM_BOT_ENCRYPTION_KEY=foreign_key):
            with pytest.raises(InvalidToken):
                decrypt_token(ciphertext)


class TestKeyRotation:
    def test_multi_fernet_decrypts_old_ciphertext_during_rotation(self):
        """Rotation: old key still decrypts, new key encrypts going forward."""
        old_key = Fernet.generate_key().decode("ascii")
        new_key = Fernet.generate_key().decode("ascii")

        # Write with old key.
        with override_settings(TELEGRAM_BOT_ENCRYPTION_KEY=old_key):
            old_ciphertext = encrypt_token("legacy-token")

        # After rotation: new key first, old key second. Reads still work.
        with override_settings(
            TELEGRAM_BOT_ENCRYPTION_KEYS=[new_key, old_key],
        ):
            assert decrypt_token(old_ciphertext) == "legacy-token"
            # New writes use the new key.
            new_ciphertext = encrypt_token("fresh-token")
            assert decrypt_token(new_ciphertext) == "fresh-token"

        # Once old key is dropped, old ciphertext becomes undecryptable.
        with override_settings(TELEGRAM_BOT_ENCRYPTION_KEY=new_key):
            with pytest.raises(InvalidToken):
                decrypt_token(old_ciphertext)


class TestMask:
    def test_masks_bot_token_preserving_bot_id_and_tail(self):
        """Bot IDs are public (visible in every getMe reply) — safe to show.

        The secret body, however, must be redacted to keep logs and UI
        screenshots from leaking the credential.
        """
        masked = mask_token("123456789:ABCxxxxxxxxxxxxxxxxxxxxxxx-wXYZ")
        assert masked.startswith("123456789:")
        assert "ABC" not in masked
        assert masked.endswith("wXYZ")
        assert "•" in masked

    def test_empty_returns_empty(self):
        assert mask_token("") == ""

    def test_short_non_standard_shape_masks_everything_but_tail(self):
        masked = mask_token("abcdef")
        assert masked == "••••cdef"

    def test_very_short_masks_completely(self):
        assert mask_token("ab") == "••••"
