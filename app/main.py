# app/main.py

from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as RequestValidationError

# Import logger and configuration variables
from app.config import logger, SECRET_KEY, LOGIN_ROUTE

# Import database connection function
from app.database import connect_to_mongodb

# Import routers from the routes subdirectory
from app.routes import auth_routes, user_routes, shipment_routes, device_data_routes

logger.info("Creating FastAPI app instance.")
# Initialize FastAPI app
app = FastAPI()

# --- Static files setup ---
# Mount the static directory to serve static files (CSS, JS, images).
# The path is relative to the directory where the application is run.
app.mount("/static", StaticFiles(directory="static"), name="static")
logger.info("Static files mounted from './static'.")

# --- Jinja2 Templates setup ---
# Initialize Jinja2Templates for rendering HTML templates.
# The path is relative to the directory where the application is run.
templates = Jinja2Templates(directory="templates")
logger.info("Jinja2Templates initialized from './templates'.")

# Pass the templates instance to the routers that need it
auth_routes.set_templates(templates)
user_routes.set_templates(templates)
shipment_routes.set_templates(templates)
device_data_routes.set_templates(templates)


# --- Session middleware setup ---
# Add SessionMiddleware for managing user sessions (e.g., flash messages).
# The secret_key is used to sign the session cookie.
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
logger.info("SessionMiddleware added.")

# --- MongoDB connection setup ---
# Establish connection to MongoDB when the application starts up.
connect_to_mongodb()

# --- Include Routers ---
# Include the routers from different modules to organize API endpoints.
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(shipment_routes.router)
app.include_router(device_data_routes.router)
logger.info("All application routers included.")

# ---------------------------
# GLOBAL ERROR HANDLERS
# ---------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Global exception handler for Starlette HTTP exceptions (e.g., 404 Not Found, 401 Unauthorized).
    Logs the error and returns a JSON response.
    """
    logger.error(f"HTTP Exception caught: {exc.status_code} - {exc.detail}")
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global exception handler for Pydantic validation errors.
    Logs the validation errors and returns a JSON response with 400 Bad Request status.
    """
    logger.error(f"Validation Error caught: {exc.errors()}")
    return JSONResponse({"detail": exc.errors()}, status_code=status.HTTP_400_BAD_REQUEST)

# --- Root Route ---
# This route handles the base URL and redirects to the login page.
@app.get("/", response_class=HTMLResponse)
def root():
    """
    Root endpoint that redirects to the login page.
    """
    logger.info(f"Root endpoint accessed, redirecting to {LOGIN_ROUTE}.")
    return RedirectResponse(url=LOGIN_ROUTE)





