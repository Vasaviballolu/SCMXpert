# app/auth.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, logger
from app.database import get_users_collection
from app.models import TokenData

# Password hashing context using bcrypt scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for handling token authentication
# tokenUrl specifies the endpoint where clients can obtain a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.

    Args:
        data (dict): The payload data to encode into the token.
                     Should contain at least 'sub' (subject/username) and 'role'.
        expires_delta (Optional[timedelta]): The duration for which the token will be valid.
                                             If None, uses ACCESS_TOKEN_EXPIRE_MINUTES from config.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Calculate expiration time in UTC.
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    
    # Encode the JWT using the secret key and algorithm from config.
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency function to get the current user from the JWT token.
    It first checks the cookie, then the Authorization header.

    Args:
        request (Request): The FastAPI request object.
        token (str): The token from the Authorization header (if present).

    Returns:
        dict: The user document from MongoDB.

    Raises:
        HTTPException: If authentication fails (e.g., missing token, invalid token, user not found).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get the token from the 'access_token' cookie.
    jwt_token = request.cookies.get("access_token")
    logger.debug(f"JWT token from cookie: {jwt_token}")

    # If cookie token is not found, but a token is provided via OAuth2 scheme (header), use that.
    if not jwt_token and token:
        jwt_token = token
    
    # If no token is found at all, raise an authentication exception.
    if not jwt_token:
        logger.error("JWT token not found in cookie or header.")
        raise credentials_exception

    try:
        # Decode the JWT token using the secret key and algorithm.
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        # Extract username (subject) from the payload.
        username: str = payload.get("sub")
        if username is None:
            logger.error("Username not found in JWT payload.")
            raise credentials_exception
        
        # Create a TokenData object from the payload.
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError as e:
        # Log JWT decoding errors and raise an authentication exception.
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception

    # Fetch the user from the database using the username from the token.
    users_collection = get_users_collection()
    user = users_collection.find_one({"email": token_data.username})
    if user is None:
        logger.error("User not found for given token data.")
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency function to ensure the current user is active.
    Currently, it just checks if the user object is not None.
    """
    if not current_user:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def verify_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    """
    Dependency function to verify if the current user has 'admin' role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

