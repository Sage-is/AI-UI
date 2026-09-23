"""Unit tests for the pure engine: python -m unittest sage_is_ai.privacy.test_engine"""

import unittest

from sage_is_ai.privacy.engine import MemoryMapper, StreamReverser, pseudonymize, reverse
from sage_is_ai.privacy.rules import Rule, rules_from_config

KEY = "test-key"
TEXT = "Call Faye Silva at (613) 555-0187 or faye.silva@example.com, K1A 0B1, card 4111 1111 1111 1111."


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.rules = rules_from_config({})
        self.mapper = MemoryMapper(KEY)

    def test_detectors_pseudonymize_with_shape_and_the_card_is_redacted(self):
        out, hits = pseudonymize(TEXT, self.rules, self.mapper)
        self.assertNotIn("0187", out)
        self.assertRegex(out, r"\(613\) 555-\d{4}")
        self.assertRegex(out, r"p[0-9a-f]{8}@example\.invalid")
        self.assertRegex(out, r"K\d[A-Z] \d[A-Z]\d")
        self.assertIn("[card]", out)
        self.assertNotIn("4111", out)
        self.assertIn("Faye Silva", out)  # names need a rule or a hint
        self.assertEqual({h.rule for h in hits}, {"phone", "email", "postal_ca", "card"})

    def test_literal_rules_and_hints_catch_names_and_streets(self):
        rules = self.rules + [Rule("surname", "literal", "Silva", category="surname")]
        out, _ = pseudonymize("Faye Silva lives at 12 Alder Ave", rules, self.mapper,
                              hints=[{"kind": "street", "value": "12 Alder Ave"}])
        self.assertNotIn("Silva", out)
        self.assertNotIn("Alder", out)
        self.assertIn("Faye", out)
        self.assertRegex(out, r"\d+ \w+ Ave")

    def test_same_value_same_fake_and_reversal_is_identity(self):
        first, _ = pseudonymize(TEXT, self.rules, self.mapper)
        second, _ = pseudonymize(TEXT, self.rules, self.mapper)
        self.assertEqual(first, second)
        restored = reverse(first, self.mapper.reverse_table())
        self.assertEqual(restored, TEXT.replace("4111 1111 1111 1111", "[card]"))

    def test_redact_is_one_way_and_literal_reverses_when_unique(self):
        rules = [Rule("secret", "literal", "Acme Realty", category="org", strategy="literal", replacement="Company A")]
        out, _ = pseudonymize("Acme Realty called", rules, self.mapper)
        self.assertEqual(out, "Company A called")
        self.assertEqual(reverse(out, self.mapper.reverse_table()), "Acme Realty called")

    def test_overlaps_keep_the_longest_match(self):
        rules = self.rules + [Rule("word", "literal", "example", category="name")]
        out, _ = pseudonymize("mail faye@example.com now", rules, self.mapper)
        self.assertRegex(out, r"mail p[0-9a-f]{8}@example\.invalid now")

    def test_stream_reversal_survives_a_fake_split_across_chunks(self):
        out, _ = pseudonymize("Reply to faye.silva@example.com about (613) 555-0187 today", self.rules, self.mapper)
        table = self.mapper.reverse_table()
        pieces, emitted, reverser = [out[i:i + 5] for i in range(0, len(out), 5)], "", StreamReverser(table)
        for piece in pieces:
            emitted += reverser.feed(piece)
        emitted += reverser.flush()
        self.assertEqual(emitted, "Reply to faye.silva@example.com about (613) 555-0187 today")

    def test_pseudonymizing_twice_is_stable(self):
        once, _ = pseudonymize(TEXT, self.rules, self.mapper)
        twice, _ = pseudonymize(once, self.rules, self.mapper)
        self.assertEqual(once, twice)
        self.assertEqual(len(self.mapper.by_fake), 3)  # phone, email, postal; the card is redacted

    def test_a_fake_never_repeats_the_real_name_or_street(self):
        for key in ("k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k10", "k11", "k12"):
            mapper = MemoryMapper(key)
            for surname in ("Silva", "Moreau", "Okafor", "Andersen"):
                self.assertNotEqual(mapper.fake("surname", surname, "pseudonym").lower(), surname.lower(), key)
            for street in ("12 Alder Ave", "7 Maple St", "300 Cedar Road"):
                fake = mapper.fake("street", street, "pseudonym")
                self.assertNotIn(street.split()[1].lower(), fake.lower(), (key, fake))

    def test_collisions_get_a_new_fake(self):
        a = self.mapper.fake("email", "a@x.com", "pseudonym")
        self.mapper.by_fake[a] = ("email", "someone-else")  # force a collision on the next call
        self.mapper.by_real.pop(("email", "a@x.com"))
        b = self.mapper.fake("email", "a@x.com", "pseudonym")
        self.assertNotEqual(a, b)


class EmptyFakeTest(unittest.TestCase):
    """An empty fake in the reverse table injects the real value between every
    character of every reply. It must be unreachable by any route."""

    def test_store_refuses_an_empty_fake(self):
        with self.assertRaises(ValueError):
            MemoryMapper(KEY).store("name", "Faye", "")

    def test_a_literal_strategy_with_a_blank_replacement_pseudonymizes(self):
        mapper = MemoryMapper(KEY)
        fake = mapper.fake("name", "Faye", "literal", "")
        self.assertTrue(fake)
        self.assertNotIn("", mapper.reverse_table().keys() - {fake})

    def test_a_blank_replacement_rule_is_downgraded_at_load(self):
        rules = rules_from_config({"rules": [
            {"name": "r", "kind": "literal", "pattern": "Faye", "strategy": "literal", "replacement": "  "},
        ]})
        rule = [r for r in rules if r.name == "r"][0]
        self.assertEqual(rule.strategy, "pseudonym")

    def test_reverse_ignores_an_empty_fake_in_the_table(self):
        self.assertEqual(reverse("hello", {"": "SECRET"}), "hello")


class BadDetectorTest(unittest.TestCase):
    """kind=detector carries a key into DETECTORS. A crafted one used to
    KeyError on every chat."""

    def test_an_unknown_detector_matches_nothing_rather_than_raising(self):
        self.assertEqual(Rule("x", "detector", "not-a-detector").compiled().findall("anything"), [])

    def test_config_drops_a_detector_naming_no_builtin(self):
        rules = rules_from_config({"rules": [
            {"name": "evil", "kind": "detector", "pattern": "nope", "enabled": True},
        ]})
        self.assertNotIn("evil", [r.name for r in rules])


class ExhaustionTest(unittest.TestCase):
    """SURNAMES is forty long. The forty-first distinct name used to spin."""

    def test_a_name_past_the_shaped_space_falls_back_instead_of_spinning(self):
        mapper = MemoryMapper(KEY)
        tagged = None
        for i in range(400):
            fake = mapper.fake("surname", f"Person{i}", "pseudonym")
            self.assertTrue(fake, f"empty fake at {i}")
            if fake.startswith("[surname-"):
                tagged = fake
                break
        self.assertIsNotNone(tagged, "the shaped space never gave way to the fallback")

    def test_the_fallback_still_reverses(self):
        mapper = MemoryMapper(KEY)
        fakes = [mapper.fake("surname", f"Person{i}", "pseudonym") for i in range(400)]
        table = mapper.reverse_table()
        self.assertEqual(reverse(fakes[-1], table), "Person399")


if __name__ == "__main__":
    unittest.main()
