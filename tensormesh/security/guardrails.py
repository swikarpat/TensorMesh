from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from tensormesh.security.token_vault import TokenVault
from tensormesh.telemetry.logging import logger
from tensormesh.telemetry.metrics import record_dfars_violation


class GuardrailViolation(ValueError):
    """Raised when a model input or output violates TensorMesh policy."""


def enforce_itar_cleanroom(
    payload: Mapping[str, Any],
    vault: TokenVault | None = None,
) -> dict[str, Any]:
    """Replace sensitive deposit strings with encrypted TokenVault surrogates."""
    if not isinstance(payload, Mapping):
        raise GuardrailViolation("deposit payload must be a mapping")
    token_vault = vault or TokenVault()

    def sanitize(value: Any) -> Any:
        if isinstance(value, str):
            redacted, _ = token_vault.redact_and_tokenize(value)
            return redacted
        if isinstance(value, Mapping):
            return {str(key): sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if isinstance(value, tuple):
            return [sanitize(item) for item in value]
        return value

    clean_payload = sanitize(payload)
    serialized = json.dumps(clean_payload, sort_keys=True)
    if any(identifier in serialized.upper() for identifier in ("CAGE CODE", "NSN:", "ITAR:", "DFARS:")):
        raise GuardrailViolation("unredacted defense identifier detected in cleanroom payload")
    return clean_payload


def enforce_dfars_output_invariant(verdict: Any) -> Any:
    """Require commercially viable outputs to carry a self-verifying DFARS certificate."""
    if hasattr(verdict, "model_dump"):
        record = verdict.model_dump()
    elif isinstance(verdict, Mapping):
        record = dict(verdict)
    else:
        raise GuardrailViolation("verdict must be a mapping or Pydantic model")

    conclusion = str(record.get("verdict", record.get("conclusion", ""))).casefold()
    evidence = record.get("evidence", {})
    certificate = evidence.get("dfars_252_225_7052_compliance_certificate", {})
    if conclusion in {"viable", "commercially_viable"}:
        audit_hash = certificate.get("audit_hash")
        if not audit_hash or not certificate.get("dfars_compliant"):
            record_dfars_violation(
                certificate.get("vessel_mmsi", "unknown"),
                certificate.get("nearest_restricted_port", "unknown"),
            )
            logger.warning(
                "DFARS compliance certificate missing or non-compliant",
                extra={
                    "event": "DFARS_VIOLATION_DETECTED",
                    "vessel_mmsi": certificate.get("vessel_mmsi", "unknown"),
                    "restricted_port": certificate.get("nearest_restricted_port", "unknown"),
                },
            )
            raise GuardrailViolation("commercially viable verdict lacks a compliant DFARS audit trail")
        canonical_certificate = {
            key: value for key, value in certificate.items() if key != "audit_hash"
        }
        expected_hash = hashlib.sha256(
            json.dumps(canonical_certificate, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if audit_hash != expected_hash:
            record_dfars_violation(
                certificate.get("vessel_mmsi", "unknown"),
                certificate.get("nearest_restricted_port", "unknown"),
            )
            logger.warning(
                "DFARS compliance certificate hash verification failed",
                extra={
                    "event": "DFARS_VIOLATION_DETECTED",
                    "vessel_mmsi": certificate.get("vessel_mmsi", "unknown"),
                    "restricted_port": certificate.get("nearest_restricted_port", "unknown"),
                },
            )
            raise GuardrailViolation("DFARS certificate hash failed mathematical verification")
    return verdict