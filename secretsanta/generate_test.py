#!/usr/bin/env python3
"""Test run with fictional couples. Outputs assignment + codes table."""

import base64
import json
import os
import random
import re
import secrets
import string

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = os.path.dirname(os.path.abspath(__file__))

people = ["Jim", "Pam", "Peter", "Lois", "Mickey", "Minnie", "Donald", "Daisy"]

couples = [
    ("Jim", "Pam"),
    ("Peter", "Lois"),
    ("Mickey", "Minnie"),
    ("Donald", "Daisy"),
]

last_year: dict[str, str] = {}

_partner: dict[str, str] = {}
for _a, _b in couples:
    _partner[_a] = _b
    _partner[_b] = _a


def _valid(assignment: dict[str, str]) -> bool:
    for giver, giftee in assignment.items():
        if giver == giftee:
            return False
        if _partner.get(giver) == giftee:
            return False
        if last_year.get(giver) == giftee:
            return False
    return True


def generate_assignment() -> dict[str, str]:
    giftees = people[:]
    while True:
        random.shuffle(giftees)
        assignment = dict(zip(people, giftees))
        if _valid(assignment):
            return assignment


def _make_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _encrypt(plaintext: str, code: str) -> dict[str, str]:
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key = kdf.derive(code.encode())
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode(), None)
    return {
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


assignment = generate_assignment()
codes = {name: _make_code() for name in people}
records = [
    {"name": name, **_encrypt(assignment[name], codes[name])}
    for name in people
]

# Write test index.html
html_path = os.path.join(HERE, "index.html")
with open(html_path) as f:
    html = f.read()
html = re.sub(r'const RECORDS = .*?;', f'const RECORDS = {json.dumps(records)};', html)
test_html_path = os.path.join(HERE, "index_test.html")
with open(test_html_path, "w") as f:
    f.write(html)

print("TEST ASSIGNMENT (spoilers!)")
print("-" * 32)
for giver, giftee in assignment.items():
    print(f"  {giver:<10} → {giftee}")

print()
print("CODES TABLE (share with testers)")
print("-" * 32)
print(f"  {'Name':<10}  {'Code':<12}")
for name, code in codes.items():
    print(f"  {name:<10}  {code:<12}")

print()
print(f"Test page written to: index_test.html")
