# --- Authentication Logic & Callbacks ---
from typing import Optional
from jose import jwt, JWTError
from ix.misc.settings import Settings
from ix.db import User


def get_user_from_token(token_data: dict) -> Optional[User]:
    """Decode the access token and retrieve the corresponding user."""
    if not token_data or "access_token" not in token_data:
        return None

    try:
        access_token = token_data["access_token"]
        payload = jwt.decode(
            access_token, Settings.secret_key, algorithms=[Settings.algorithm]
        )
        username = payload.get("sub")
        if not username:
            return None
        user = User.find_one(User.username == username).run()
        return user
    except JWTError:
        return None
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None
