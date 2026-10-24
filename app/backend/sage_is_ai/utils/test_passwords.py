"""passlib -> bcrypt parity: python -m unittest sage_is_ai.utils.test_passwords

Every fixture hash below was produced by passlib 1.7.4 on bcrypt 4.3.0 inside the
last build with passlib (2026-10-14), with the CryptContext the app used. If a change to
utils/passwords.py stops verifying one of them, real users stop signing in.
Needs bcrypt, so it runs inside the image: `make image_unit_tests`.
"""

import unittest

from sage_is_ai.utils.passwords import (
    BCRYPT_MAX_BYTES,
    get_password_hash,
    verify_password,
)

LONG = "L" * 100

PASSLIB_FIXTURES = [
    (
        "2b ascii",
        "password",
        "$2b$12$sBRtvMHcqddvx12jla/6LOWj3A1o74oQSVlNNNWWurcXwntBbIa8m",
    ),
    (
        "2b unicode",
        "pässwörd-日本語-🌱",
        "$2b$12$vDpg5Uzo545Ne9keHe8c.OG1dJDcVfordyr0m9WxWz4VXs.2QUu8.",
    ),
    ("2a", "password", "$2a$12$IWfwICevfCCfswUAWcRrneR.nm47Yc5chmp83OGNs4jvkEJIk/LZu"),
    ("2y", "password", "$2y$12$ZPdO/LNHOxOGGnrE0ZYQDOT6eAvaS3keXxwcLLsPFkHi0Rwvbcuw2"),
    (
        "2b 100 bytes",
        LONG,
        "$2b$12$TTdrSIND/f710KYjtyB4Pe7A2fZl4heWOtaX3kWDfemnHRUxyjFZ6",
    ),
]


class PasslibParity(unittest.TestCase):
    def test_every_passlib_hash_still_verifies(self):
        for label, password, stored in PASSLIB_FIXTURES:
            with self.subTest(label):
                self.assertIs(verify_password(password, stored), True)

    def test_wrong_password_fails(self):
        for label, password, stored in PASSLIB_FIXTURES[:4]:
            with self.subTest(label):
                self.assertIs(verify_password(password + "x", stored), False)

    def test_72_byte_cut_matches_passlib(self):
        # passlib verified these two as True; anything else locks those users out.
        stored = PASSLIB_FIXTURES[-1][2]
        self.assertIs(verify_password(LONG[:BCRYPT_MAX_BYTES], stored), True)
        self.assertIs(verify_password(LONG + "x", stored), True)

    def test_new_hashes_match_passlib_shape(self):
        h = get_password_hash("password")
        self.assertTrue(h.startswith("$2b$12$"), h)
        self.assertEqual(len(h), 60)
        self.assertIs(verify_password("password", h), True)
        self.assertIs(verify_password("Password", h), False)

    def test_long_password_hashes_instead_of_raising(self):
        # bcrypt 5 raises on > 72 bytes; the cut must happen before bcrypt sees it.
        h = get_password_hash("é" * 200)
        self.assertIs(verify_password("é" * 200, h), True)

    def test_survives_bcrypt_5_length_check(self):
        # bcrypt 4.x cuts silently, so on it the test above passes with or
        # without our cut. Simulate bcrypt 5, which raises past 72 bytes.
        import bcrypt
        from unittest import mock

        real_hashpw, real_checkpw = bcrypt.hashpw, bcrypt.checkpw

        def strict(fn):
            def wrapped(password, *rest):
                if len(password) > 72:
                    raise ValueError("password cannot be longer than 72 bytes")
                return fn(password, *rest)

            return wrapped

        with (
            mock.patch.object(bcrypt, "hashpw", strict(real_hashpw)),
            mock.patch.object(bcrypt, "checkpw", strict(real_checkpw)),
        ):
            h = get_password_hash(LONG)
            self.assertIs(verify_password(LONG, h), True)
            self.assertIs(verify_password(LONG, PASSLIB_FIXTURES[-1][2]), True)

    def test_missing_hash_is_none(self):
        self.assertIsNone(verify_password("password", None))
        self.assertIsNone(verify_password("password", ""))

    def test_malformed_hash_is_false_not_an_exception(self):
        for bad in ["not-a-hash", "$2b$12$short", "$1$md5$crypt"]:
            with self.subTest(bad):
                self.assertIs(verify_password("password", bad), False)


if __name__ == "__main__":
    unittest.main()
