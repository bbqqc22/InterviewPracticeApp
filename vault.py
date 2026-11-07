"""Encrypted storage. Your password is turned into an encryption key (scrypt) and
all data is encrypted (Fernet = AES + integrity check). Without the password the
file 'interview_vault.enc' is unreadable. There is NO password recovery.
"""
import base64, json, os, secrets, shutil, time
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

HERE = Path(__file__).parent
VAULT_FILE = HERE / "interview_vault.enc"
GUARD_FILE = HERE / "vault_guard.json"   # failed-attempt counter only; holds no secrets
MIN_PASSWORD = 10
MAX_TRIES = 5
LOCKOUT_SECONDS = 300
_N, _R, _P = 2 ** 15, 8, 1


class WrongPassword(Exception):
    pass


def _derive(password, salt):
    kdf = Scrypt(salt=salt, length=32, n=_N, r=_R, p=_P)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def empty_data():
    return {"candidates": {}, "prepared_answers": {}, "custom_candidate_qs": [],
            "settings": {"api_key": ""}, "lab_runs": []}


def exists():
    return VAULT_FILE.exists()


class Vault:
    def __init__(self, salt, key):
        self.salt, self.key = salt, key

    # -- create / open
    @classmethod
    def create(cls, password, data=None):
        if len(password) < MIN_PASSWORD:
            raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
        salt = secrets.token_bytes(16)
        v = cls(salt, _derive(password, salt))
        v.save(data or empty_data())
        return v

    @classmethod
    def open(cls, password):
        blob = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
        salt = base64.b64decode(blob["salt"])
        v = cls(salt, _derive(password, salt))
        try:
            data = json.loads(Fernet(v.key).decrypt(blob["token"].encode()).decode("utf-8"))
        except InvalidToken:
            raise WrongPassword()
        return v, data

    # -- save (atomic, keeps one backup of the previous version)
    def save(self, data):
        token = Fernet(self.key).encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode()
        blob = {"v": 1, "kdf": "scrypt", "salt": base64.b64encode(self.salt).decode(), "token": token}
        tmp = VAULT_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(blob), encoding="utf-8")
        if VAULT_FILE.exists():
            shutil.copy2(VAULT_FILE, VAULT_FILE.with_suffix(".bak"))
        os.replace(tmp, VAULT_FILE)

    def change_password(self, new_password, data):
        if len(new_password) < MIN_PASSWORD:
            raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
        self.salt = secrets.token_bytes(16)
        self.key = _derive(new_password, self.salt)
        self.save(data)


# -- failed-attempt guard (slows guessing through the app; the encryption itself is the real protection)
def _guard():
    try:
        return json.loads(GUARD_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"fails": 0, "locked_until": 0}


def lock_seconds_left():
    return max(0, int(_guard().get("locked_until", 0) - time.time()))


def register_failure():
    g = _guard()
    g["fails"] = g.get("fails", 0) + 1
    if g["fails"] >= MAX_TRIES:
        g["fails"], g["locked_until"] = 0, time.time() + LOCKOUT_SECONDS
    GUARD_FILE.write_text(json.dumps(g), encoding="utf-8")
    return MAX_TRIES - g["fails"] if g["fails"] else 0


def register_success():
    GUARD_FILE.write_text(json.dumps({"fails": 0, "locked_until": 0}), encoding="utf-8")
