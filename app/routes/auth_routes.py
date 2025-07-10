# app/routes/auth_routes.py

from fastapi import APIRouter, Request, Form, status, Depends, HTTPException, Response, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime, timedelta, timezone
import secrets

from app.config import (
    logger, LOGIN_ROUTE, SIGNUP_ROUTE, DASHBOARD_ROUTE, ADMIN_DASHBOARD_ROUTE,
    FORGOT_PASSWORD_ROUTE, RESET_PASSWORD_ROUTE, RECAPTCHA_SITE_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.database import get_users_collection, get_logins_collection
from app.auth import get_password_hash, verify_password, create_access_token
from app.models import Token # Import Token model for response schema

# Create an API router for authentication-related routes
router = APIRouter()

# Global variable to hold the Jinja2Templates instance
templates_instance: Optional[Jinja2Templates] = None

def set_templates(templates: Jinja2Templates):
    """
    Function to set the Jinja2Templates instance for this router.
    This is called from main.py to inject the templates object.
    """
    global templates_instance
    templates_instance = templates

@router.get("/", response_class=HTMLResponse)
def root():
    """
    Root endpoint that redirects to the login page.
    """
    logger.info(f"Root endpoint accessed, redirecting to {LOGIN_ROUTE}.")
    return RedirectResponse(url=LOGIN_ROUTE)

@router.get(LOGIN_ROUTE, response_class=HTMLResponse, name="login")
def get_login(request: Request):
    """
    Displays the login page.
    """
    logger.info("Login page requested.")
    flash = request.session.pop("flash", None) # Retrieve and clear flash messages
    return templates_instance.TemplateResponse("login.html", {"request": request, "site_key": RECAPTCHA_SITE_KEY, "flash": flash})

@router.get(SIGNUP_ROUTE, response_class=HTMLResponse, name="signup")
def get_signup(request: Request):
    """
    Displays the signup page.
    """
    logger.info("Signup page requested.")
    flash = request.session.pop("flash", None) # Retrieve and clear flash messages
    return templates_instance.TemplateResponse("signup.html", {"request": request, "flash": flash})

@router.post(SIGNUP_ROUTE)
async def post_signup(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    # Removed 'role: str = Form(...)' as it's no longer sent from the frontend.
    # The role will now be hardcoded to 'user' for new signups.
):
    """
    Handles user signup form submission.
    Creates a new user account in the database.
    """
    logger.info(f"Signup form submitted for email: {email}")
    users_collection = get_users_collection()

    if password != confirm_password:
        request.session["flash"] = "Passwords do not match."
        logger.warning("Signup failed: Passwords do not match.")
        return RedirectResponse(url=SIGNUP_ROUTE, status_code=status.HTTP_302_FOUND)

    if users_collection.find_one({"email": email}):
        request.session["flash"] = "Email already registered."
        logger.warning(f"Signup failed: Email {email} already registered.")
        return RedirectResponse(url=SIGNUP_ROUTE, status_code=status.HTTP_302_FOUND)

    # Assign a default role of "user" since the dropdown is removed.
    # If you later want to manually assign admin roles, you can do so via the admin panel.
    assigned_role = "user" 

    password_hash = get_password_hash(password) # Hash the password
    try:
        users_collection.insert_one({
            "name": fullname,
            "email": email,
            "password_hash": password_hash,
            "role": assigned_role, # Use the assigned_role
            "created_at": datetime.now(timezone.utc)
        })
        logger.info(f"Account created successfully for {email} with role {assigned_role}.")
        request.session["flash"] = "Account created successfully! Please log in."
    except Exception as e:
        logger.error(f"Database error during signup for {email}: {e}")
        request.session["flash"] = f"Error creating account: {str(e)}"

    return RedirectResponse(url=LOGIN_ROUTE, status_code=status.HTTP_302_FOUND)

@router.post(LOGIN_ROUTE)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Handles user login form submission.
    Authenticates user and sets an access token cookie.
    """
    logger.info(f"Login attempt for username: {form_data.username}")
    users_collection = get_users_collection()
    logins_collection = get_logins_collection()

    user = users_collection.find_one({"email": form_data.username})
    # Verify user existence and password
    if not user or not verify_password(form_data.password, user["password_hash"]):
        logger.warning("Invalid credentials provided.")
        # Render login page with an error message
        return templates_instance.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials",
            "site_key": RECAPTCHA_SITE_KEY
        })

    # Create an access token for the authenticated user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": user.get("role", "user")},
        expires_delta=access_token_expires
    )

    # Record the successful login attempt
    logins_collection.insert_one({
        "email": form_data.username,
        "login_time": datetime.now(timezone.utc),
        "status": "success"
    })
    logger.info(f"Login successful for {form_data.username} with role {user.get('role', 'user')}.")

    # Redirect based on user role
    redirect_url = ADMIN_DASHBOARD_ROUTE if user.get("role") == "admin" else DASHBOARD_ROUTE
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    
    # Set the access token as an HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True, # Prevents client-side JavaScript access
        secure=False,  # Set to True in production with HTTPS
        samesite="lax", # Protects against CSRF attacks
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, # Cookie expiration in seconds
        path="/" # Cookie is valid for all paths
    )
    return response

@router.post("/token", response_model=Token)
async def login_for_api_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint for API token generation (used by OAuth2PasswordBearer).
    Authenticates user and returns a JWT token.
    """
    users_collection = get_users_collection()
    user = users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": user.get("role", "user")},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(FORGOT_PASSWORD_ROUTE, response_class=HTMLResponse)
def forgot_password(request: Request):
    """
    Displays the forgot password page.
    """
    flash = request.session.pop("flash", None)
    return templates_instance.TemplateResponse("forgot_password.html", {"request": request, "flash": flash})

@router.post(FORGOT_PASSWORD_ROUTE)
async def process_forgot_password(request: Request, email: str = Form(...)):
    """
    Handles forgot password request. Generates a reset token and simulates sending it.
    """
    users_collection = get_users_collection()
    user = users_collection.find_one({"email": email})
    if user:
        reset_token = secrets.token_urlsafe(32) # Generate a secure URL-safe token
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1) # Token expires in 1 hour
        
        # Store the reset token and its expiration in the user's document
        users_collection.update_one(
            {"email": email},
            {"$set": {"reset_token": reset_token, "reset_token_expires_at": expires_at, "updated_at": datetime.now(timezone.utc)}}
        )
        
        # Construct the reset URL (for demonstration, this would be sent via email)
        reset_url = request.url_for('reset_password_get').include_query_params(token=reset_token)
        logger.info(f"Password reset requested for {email}. Token: {reset_token}. Reset URL (simulated): {reset_url}")

    # Provide a generic message to prevent email enumeration attacks
    request.session["flash"] = "If an account with that email exists, instructions to reset your password have been sent."
    return RedirectResponse(url=LOGIN_ROUTE, status_code=status.HTTP_302_FOUND)

@router.get(RESET_PASSWORD_ROUTE, response_class=HTMLResponse, name="reset_password_get")
def reset_password_get(request: Request, token: Optional[str] = Query(None)):
    """
    Displays the password reset page.
    Validates the presence of a reset token in the query parameters.
    """
    flash = request.session.pop("flash", None)
    if not token:
        request.session["flash"] = "Invalid or missing password reset token."
        return RedirectResponse(url=FORGOT_PASSWORD_ROUTE, status_code=status.HTTP_302_FOUND)
    return templates_instance.TemplateResponse("password_reset.html", {"request": request, "token": token, "flash": flash})

@router.post(RESET_PASSWORD_ROUTE)
async def reset_password_post(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """
    Handles password reset form submission.
    Validates the token and updates the user's password.
    """
    users_collection = get_users_collection()

    if new_password != confirm_password:
        request.session["flash"] = "Passwords do not match."
        # Redirect back to the reset password page with the token
        return RedirectResponse(url=f"{RESET_PASSWORD_ROUTE}?token={token}", status_code=status.HTTP_302_FOUND)

    # Find the user by the reset token and ensure it's not expired
    user = users_collection.find_one({
        "reset_token": token,
        "reset_token_expires_at": {"$gt": datetime.now(timezone.utc)}
    })

    if not user:
        request.session["flash"] = "Invalid or expired password reset token."
        logger.warning(f"Invalid or expired reset token used: {token}")
        return RedirectResponse(url=FORGOT_PASSWORD_ROUTE, status_code=status.HTTP_302_FOUND)

    # Hash the new password and update the user's record
    new_password_hash = get_password_hash(new_password)
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": new_password_hash,
            "reset_token": None, # Clear the token after use
            "reset_token_expires_at": None, # Clear expiration
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    logger.info(f"Password successfully reset for {user['email']}.")
    request.session["flash"] = "Your password has been reset successfully. Please log in."
    return RedirectResponse(url=LOGIN_ROUTE, status_code=status.HTTP_302_FOUND)

