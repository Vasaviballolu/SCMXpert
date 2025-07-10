# app/routes/device_data_routes.py

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime

from app.config import logger
from app.database import get_device_data_collection
from app.auth import get_current_active_user

# Create an API router for device data routes
router = APIRouter()

# Placeholder for Jinja2Templates instance, to be set by main.py
templates_instance: Optional[Jinja2Templates] = None

def set_templates(templates: Jinja2Templates):
    """Function to set the Jinja2Templates instance."""
    global templates_instance
    templates_instance = templates

@router.get("/device-data", response_class=HTMLResponse)
async def get_device_data(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    device_id: Optional[str] = Query(None) # Optional query parameter for filtering by device ID
):
    """
    Displays device data, optionally filtered by device ID.
    """
    logger.info(f"Device data page requested by {current_user['email']}.")
    device_data_collection = get_device_data_collection()

    try:
        # Get distinct device IDs for the filter dropdown
        device_ids_cursor = device_data_collection.distinct("Device_ID")
        device_ids = sorted([str(did) for did in device_ids_cursor]) # Convert to string and sort

        query_filter = {}
        if device_id:
            # Attempt to convert device_id to int if it's numeric, otherwise keep as string
            try:
                query_filter["Device_ID"] = int(device_id)
            except ValueError:
                query_filter["Device_ID"] = device_id

        # Fetch device data based on filter, sorted by timestamp (latest first), limited to 50 records
        devices_cursor = device_data_collection.find(query_filter, {"_id": 0}).sort("timestamp", -1).limit(50)
        
        devices = []
        for dev in devices_cursor:
            # Format timestamp for display
            if isinstance(dev.get("timestamp"), datetime):
                dev["timestamp_str"] = dev["timestamp"].strftime("%Y-%m-%d %H:%M:%S") # No UTC suffix needed here
            else:
                dev["timestamp_str"] = str(dev.get("timestamp", "N/A")) # Fallback for non-datetime types
            devices.append(dev)

        logger.info(f"Fetched records for Device ID: {device_id if device_id else 'all (latest)'}")
        
        flash = request.session.pop("flash", None) # Retrieve and clear flash messages
        return templates_instance.TemplateResponse("device_data.html", {
            "request": request,
            "devices": devices,
            "device_ids": device_ids,
            "selected_device_id": device_id if device_id else "", # Pass selected device ID to template
            "flash": flash,
            "username": current_user["email"]
        })
    except Exception as e:
        logger.error(f"Error in device data route: {e}")
        request.session["flash"] = "Error fetching device data"
        # Render the page with an error message and empty data on exception
        return templates_instance.TemplateResponse("device_data.html", {
            "request": request,
            "devices": [],
            "device_ids": [],
            "selected_device_id": "",
            "flash": "Error fetching device data",
            "username": current_user["email"]
        })

