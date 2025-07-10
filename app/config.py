# app/config.py

import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# --- Configure Logger ---
# Using __name__ ensures the logger name reflects the module it's in.
# This fixes the ImportError by correctly initializing the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# File handler for logging to a file
file_handler = logging.FileHandler('app.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Stream handler for logging to console
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(stream_handler)

logger.info("Logger initialized.")

# --- Load environment variables ---
# Load .env file, overriding existing environment variables if they conflict.
loaded = load_dotenv(override=True)
logger.info(f".env file loaded: {loaded}")

# --- Configuration Variables ---
# Retrieve JWT secret key from environment variables.
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
# Retrieve JWT algorithm from environment variables.
ALGORITHM = os.getenv("JWT_ALGORITHM")
# Retrieve access token expiration minutes, default to "10" if not set.
raw_expire_minutes = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10")
logger.debug(f"DEBUG: Raw value from os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'): '{raw_expire_minutes}'")
# Convert expiration minutes to an integer.
ACCESS_TOKEN_EXPIRE_MINUTES = int(raw_expire_minutes)

# Retrieve reCAPTCHA site key from environment variables.
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY")
# Retrieve reCAPTCHA secret key from environment variables.
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")
# Retrieve MongoDB URI from environment variables.
MONGO_URI = os.getenv("MONGO_URI")

# Validate critical environment variables.
# If any essential variable is missing, log a critical error and raise a ValueError.
if not all([SECRET_KEY, ALGORITHM, RECAPTCHA_SITE_KEY, RECAPTCHA_SECRET_KEY, MONGO_URI]):
    logger.critical("Missing critical environment variables. Please check your .env file.")
    raise ValueError("Missing critical environment variables. Check your .env file.")

# --- URL Path Constants ---
# Define constants for various application routes for easy management and consistency.
LOGIN_ROUTE = "/login"
SIGNUP_ROUTE = "/signup"
DASHBOARD_ROUTE = "/dashboard"
ADMIN_DASHBOARD_ROUTE = "/admin-dashboard"
USER_MANAGEMENT_ROUTE = "/user_management"
CREATE_SHIPMENT_ROUTE = "/create-shipment"
EDIT_SHIPMENT_ROUTE = "/edit-shipment"
FORGOT_PASSWORD_ROUTE = "/forgot-password"
RESET_PASSWORD_ROUTE = "/reset-password"

# --- Datetime Format Constant ---
# Define a standard datetime display format.
DATETIME_DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S UTC"

