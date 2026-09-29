# -*- coding: utf-8 -*-
"""
RSA-OAEP password transport crypto.
Passwords should be encrypted with the server public key before leaving the browser,
so they are not sent as cleartext over HTTP.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_PRIVATE_KEY = None
_PUBLIC_PEM = ""
_KEY_ID = ""

_KEY_DIR = Path(__file__).resolve().parent.parent / "data"
_KEY_FILE = _KEY_DIR / "auth_rsa_private.pem"


def _allow_plaintext_password() -> bool:
    raw = (os.getenv("ALLOW_PLAINTEXT_PASSWORD") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _fingerprint(public_pem: bytes) -> str:
    digest = hashlib.sha256(public_pem).hexdigest()
    return digest[:16]


def _load_or_create_keypair() -> Tuple[object, str, str]:
    global _PRIVATE_KEY, _PUBLIC_PEM, _KEY_ID
    with _LOCK:
        if _PRIVATE_KEY is not None:
            return _PRIVATE_KEY, _PUBLIC_PEM, _KEY_ID

        private_key = None
        if _KEY_FILE.exists():
            try:
                private_key = serialization.load_pem_private_key(
                    _KEY_FILE.read_bytes(),
                    password=None,
                )
            except Exception as e:
                logger.warning("load auth RSA key failed, regenerating: %s", e)

        if private_key is None:
            _KEY_DIR.mkdir(parents=True, exist_ok=True)
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            _KEY_FILE.write_bytes(pem)
            try:
                os.chmod(_KEY_FILE, 0o600)
            except Exception:
                pass
            logger.info("generated auth RSA private key at %s", _KEY_FILE)

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        _PRIVATE_KEY = private_key
        _PUBLIC_PEM = public_pem.decode("ascii")
        _KEY_ID = _fingerprint(public_pem)
        return _PRIVATE_KEY, _PUBLIC_PEM, _KEY_ID


def get_public_key_payload() -> dict:
    _, public_pem, key_id = _load_or_create_keypair()
    return {
        "success": True,
        "keyId": key_id,
        "algorithm": "RSA-OAEP",
        "hash": "SHA-256",
        "publicKeyPem": public_pem,
    }


def decrypt_password_cipher(cipher_b64: str, key_id: str = "") -> str:
    private_key, _, current_id = _load_or_create_keypair()
    kid = (key_id or "").strip()
    if kid and kid != current_id:
        raise HTTPException(
            status_code=400,
            # ??????????????????????????
            detail="\u52a0\u5bc6\u5bc6\u94a5\u5df2\u66f4\u65b0\uff0c\u8bf7\u5237\u65b0\u9875\u9762\u540e\u91cd\u8bd5",
        )
    raw = (cipher_b64 or "").strip()
    if not raw:
        # ??????????
        raise HTTPException(status_code=400, detail="\u7f3a\u5c11\u52a0\u5bc6\u5bc6\u7801")
    try:
        blob = base64.b64decode(raw, validate=False)
        plain = private_key.decrypt(
            blob,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plain.decode("utf-8")
    except HTTPException:
        raise
    except Exception:
        logger.warning("password cipher decrypt failed")
        raise HTTPException(
            status_code=400,
            # ????????????????????????
            detail="\u5bc6\u7801\u89e3\u5bc6\u5931\u8d25\uff0c\u8bf7\u5237\u65b0\u9875\u9762\u540e\u91cd\u8bd5",
        )


def resolve_password(
    *,
    plaintext: Optional[str] = None,
    cipher: Optional[str] = None,
    key_id: str = "",
    field_label: str = "\u5bc6\u7801",
) -> str:
    """
    Prefer RSA cipher. Cleartext only when ALLOW_PLAINTEXT_PASSWORD=1.
    """
    c = (cipher or "").strip()
    if c:
        return decrypt_password_cipher(c, key_id)
    p = plaintext or ""
    if p and _allow_plaintext_password():
        logger.warning("accepted plaintext %s (ALLOW_PLAINTEXT_PASSWORD enabled)", field_label)
        return p
    if p:
        raise HTTPException(
            status_code=400,
            # {label}����ܴ��䣬��ˢ��ҳ������ԣ��������������� HTTPS
            detail=(
                f"{field_label}\u987b\u52a0\u5bc6\u4f20\u8f93\uff0c"
                "\u8bf7\u5237\u65b0\u9875\u9762\u540e\u91cd\u8bd5\uff1b"
                "\u751f\u4ea7\u73af\u5883\u8bf7\u542f\u7528 HTTPS"
            ),
        )
    return ""
