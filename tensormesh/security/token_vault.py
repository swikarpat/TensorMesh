import re
from cryptography.fernet import Fernet
from typing import Dict, Tuple
from tensormesh.config.settings import settings
from tensormesh.storage import CF_SECURE_STATE, RocksDBStore

class TokenVault:
    def __init__(self):
        self.store = RocksDBStore(settings.ROCKSDB_PATH)
        self.key_path = settings.KEY_PATH
        self.fernet = self._initialize_encryption()

        # Regex patterns for sensitive Critical Mineral / Defense data
        self.patterns = {
            "SUPPLIER": r"(Supplier\s*#?[A-Z0-9-]+|Account\s*#?\d+)",
            "AMOUNT": r"(\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+\s*(?:MT|Metric Tons|kg|tons))",
            "ALLOY_SPEC": r"([A-Z][a-z]?-[A-Z][a-z]?\s*alloy|NdFeB|SmCo)"
            ,"DEFENSE_IDENTIFIER": r"(?i)\b(?:CAGE\s*CODE|CAGE|NSN|ITAR|DFARS|FAR|CONTRACT\s*(?:NO\.?|NUMBER)?|DOD)\s*[-:#A-Z0-9/ ]{0,40}"
        }

    def _initialize_encryption(self) -> Fernet:
        """Loads or generates the AES-256 encryption key."""
        if not self.key_path.exists():
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as key_file:
                key_file.write(key)
        else:
            with open(self.key_path, "rb") as key_file:
                key = key_file.read()
        return Fernet(key)

    def redact_and_tokenize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Scans text, encrypts sensitive data, and replaces with surrogate tokens."""
        redacted_text = text
        token_map = {}
        token_counter = sum(1 for _ in self.store.scan(CF_SECURE_STATE, "token:"))

        for entity_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, redacted_text, re.IGNORECASE)
            for match in matches:
                original_value = match.group(0)
                token_id = f"[{entity_type}_{token_counter}]"
                encrypted_value = self.fernet.encrypt(original_value.encode())
                self.store.put_json(
                    CF_SECURE_STATE,
                    f"token:{token_id}",
                    {"encrypted_value": encrypted_value.decode("ascii"), "entity_type": entity_type},
                )
                redacted_text = redacted_text.replace(original_value, token_id)
                token_map[token_id] = original_value
                token_counter += 1

        return redacted_text, token_map

    def rehydrate(self, redacted_text: str) -> str:
        """Restores original sensitive values from tokens before showing to user."""
        rehydrated_text = redacted_text
        for key, record in self.store.scan_json(CF_SECURE_STATE, "token:"):
            token_id = key.removeprefix("token:")
            if token_id in rehydrated_text:
                encrypted_value = record["encrypted_value"].encode("ascii")
                decrypted_value = self.fernet.decrypt(encrypted_value).decode()
                rehydrated_text = rehydrated_text.replace(token_id, decrypted_value)
                    
        return rehydrated_text