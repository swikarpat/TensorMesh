import hashlib
import json
import unittest

from tensormesh.security.guardrails import (
    GuardrailViolation,
    enforce_dfars_output_invariant,
    enforce_itar_cleanroom,
)


class FakeVault:
    def __init__(self):
        self.values = []

    def redact_and_tokenize(self, text):
        if "CAGE" in text.upper():
            self.values.append(text)
            return "[DEFENSE_TOKEN]", {"[DEFENSE_TOKEN]": text}
        return text, {}


class GuardrailTests(unittest.TestCase):
    def test_itar_cleanroom_tokenizes_defense_identifiers(self):
        vault = FakeVault()
        clean = enforce_itar_cleanroom({"deposit_id": "DEP-1", "contract": "CAGE CODE ABC123"}, vault)
        self.assertEqual(clean["contract"], "[DEFENSE_TOKEN]")
        self.assertEqual(vault.values, ["CAGE CODE ABC123"])

    def test_dfars_invariant_rejects_tampered_certificate(self):
        certificate = {
            "dfars_compliant": True,
            "section_848_compliant": True,
            "origin_port": "Singapore",
            "destination_port": "Yokohama",
            "violations": [],
        }
        certificate["audit_hash"] = hashlib.sha256(
            json.dumps(certificate, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        certificate["violations"] = ["tampered"]
        with self.assertRaises(GuardrailViolation):
            enforce_dfars_output_invariant({
                "verdict": "commercially_viable",
                "evidence": {"dfars_252_225_7052_compliance_certificate": certificate},
            })


if __name__ == "__main__":
    unittest.main()