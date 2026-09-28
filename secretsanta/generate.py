#!/usr/bin/env python3
"""
Secret Santa generator — run once per year.

Writes to the same directory as this script:
  records.json                         — safe to publish (encrypted)
  codes.json                           — build personalized links (keep private)
  PRIVATE_assignment_do_not_view.json  — plaintext assignment (keep very private)

Then embeds records.json into index.html.

Usage:
  pip install cryptography
  python3 generate.py
"""

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

# ── Edit these each year ──────────────────────────────────────────────────────

people = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]

couples = [
    ("Alice", "Bob"),
    ("Carol", "Dave"),
    ("Eve", "Frank"),
    ("Grace", "Hank"),
]

# 2025 assignments — used to prevent repeats this year.
last_year: dict[str, str] = {
    "Alice": "Hank",
    "Bob":   "Frank",
    "Carol": "Bob",
    "Dave":  "Grace",
    "Eve":   "Alice",
    "Frank": "Carol",
    "Grace": "Dave",
    "Hank":  "Eve",
}

# ── Assignment logic ──────────────────────────────────────────────────────────

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


# ── Crypto ────────────────────────────────────────────────────────────────────

def _make_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _encrypt(plaintext: str, code: str) -> dict[str, str]:
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    key = kdf.derive(code.encode())
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode(), None)  # 16-byte auth tag appended
    return {
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    assignment = generate_assignment()
    codes = {name: _make_code() for name in people}
    records = [
        {"name": name, **_encrypt(assignment[name], codes[name])}
        for name in people
    ]

    def write(filename: str, data: object) -> None:
        path = os.path.join(HERE, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  wrote {filename}")

    print("Generating...")
    write("records.json", records)
    write("codes.json", codes)
    write("PRIVATE_assignment_do_not_view.json", assignment)

    html_path = os.path.join(HERE, "index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            html = f.read()
        html = re.sub(r'const RECORDS = .*?;', f'const RECORDS = {json.dumps(records)};', html)
        with open(html_path, "w") as f:
            f.write(html)
        print("  embedded records → index.html")

    print("\nPersonalized links:")
    deployed = "https://YOUR-DEPLOYED-URL"
    for name, code in codes.items():
        print(f"  {name}: {deployed}/?n={name}&c={code}")

    print("\nAssignment (PRIVATE — do not open until after the party):")
    for giver, giftee in assignment.items():
        print(f"  {giver} → {giftee}")


if __name__ == "__main__":
    main()
