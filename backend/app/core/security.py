from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext
import pyotp
import qrcode
from io import BytesIO
import base64

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
        "type": "refresh",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    return payload.get("type") == expected_type


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret, digits=settings.TOTP_DIGITS, interval=settings.TOTP_PERIOD)
    return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER)


def generate_qr_code(data: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def verify_totp(secret: str, token: str, valid_window: int = 1) -> bool:
    totp = pyotp.TOTP(secret, digits=settings.TOTP_DIGITS, interval=settings.TOTP_PERIOD)
    return totp.verify(token, valid_window=valid_window)


def generate_backup_codes(count: int = 10, length: int = 8) -> list[str]:
    import secrets
    import string
    alphabet = string.ascii_uppercase + string.digits
    return [
        "".join(secrets.choice(alphabet) for _ in range(length))
        for _ in range(count)
    ]


def hash_backup_code(code: str) -> str:
    return hash_password(code)


def verify_backup_code(plain_code: str, hashed_code: str) -> bool:
    return verify_password(plain_code, hashed_code)