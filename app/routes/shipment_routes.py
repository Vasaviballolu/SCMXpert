# app/routes/shipment_routes.py

from fastapi import APIRouter, Request, Form, status, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError as RequestValidationError
from typing import Optional
from datetime import datetime, timezone

from app.config import (
    logger, CREATE_SHIPMENT_ROUTE, EDIT_SHIPMENT_ROUTE, DATETIME_DISPLAY_FORMAT
)
from app.database import get_shipment_collection
from app.auth import get_current_active_user, verify_admin
from app.models import ShipmentCreateData

# Create an API router for shipment-related routes
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

@router.get(CREATE_SHIPMENT_ROUTE, response_class=HTMLResponse)
async def get_create_shipment(request: Request, current_user: dict = Depends(get_current_active_user)):
    """
    Displays the page for creating a new shipment.
    """
    logger.info(f"Create shipment page requested by {current_user['email']}.")
    flash = request.session.pop("flash", None) # Retrieve and clear flash messages
    return templates_instance.TemplateResponse("create_shipment.html", {
        "request": request,
        "user_name": current_user["email"],
        "role": current_user["role"],
        "flash": flash
    })

@router.post(CREATE_SHIPMENT_ROUTE)
async def create_shipment(
    request: Request,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Handles the submission for creating a new shipment.
    Validates form data using Pydantic and saves to the database.
    """
    shipment_collection = get_shipment_collection()
    
    # Manually parse form data and validate with Pydantic model
    form_data = await request.form()
    try:
        # Create a ShipmentCreateData instance from form data
        shipment_data = ShipmentCreateData(
            shipment_id=form_data.get("shipment_id"),
            po_number=form_data.get("po_number"),
            route_details=form_data.get("route_details"),
            device=form_data.get("device"),
            ndc_number=form_data.get("ndc_number"),
            serial_number=form_data.get("serial_number"),
            container_number=form_data.get("container_number"),
            goods_type=form_data.get("goods_type"),
            expected_delivery_date=form_data.get("expected_delivery_date"),
            delivery_number=form_data.get("delivery_number"),
            batch_id=form_data.get("batch_id"),
            origin=form_data.get("origin"),
            destination=form_data.get("destination"),
            shipment_description=form_data.get("shipment_description")
        )
    except RequestValidationError as e:
        logger.error(f"Validation error during shipment creation: {e.errors()}")
        request.session["flash"] = f"Validation error: {e.errors()}"
        return RedirectResponse(url=CREATE_SHIPMENT_ROUTE, status_code=status.HTTP_302_FOUND)

    logger.info(f"Shipment creation submitted by {current_user['email']} for shipment ID: {shipment_data.shipment_id}.")
    
    # Check for duplicate shipment ID
    if shipment_collection.find_one({"shipment_id": shipment_data.shipment_id}):
        request.session["flash"] = f"Shipment ID '{shipment_data.shipment_id}' already exists."
        logger.warning(f"Duplicate shipment ID: {shipment_data.shipment_id}.")
        return RedirectResponse(url=CREATE_SHIPMENT_ROUTE, status_code=status.HTTP_302_FOUND)

    shipment_dict = shipment_data.model_dump() # Convert Pydantic model to dictionary (Pydantic v2)
    shipment_dict["created_at"] = datetime.now(timezone.utc)
    shipment_dict["created_by"] = current_user["email"]
    
    try:
        shipment_collection.insert_one(shipment_dict) # Insert the new shipment into MongoDB
        request.session["flash"] = f"Shipment {shipment_data.shipment_id} created successfully!"
        logger.info(f"Shipment {shipment_data.shipment_id} created successfully.")
    except Exception as e:
        logger.error(f"Error creating shipment {shipment_data.shipment_id}: {e}")
        request.session["flash"] = f"Error creating shipment: {str(e)}"
    return RedirectResponse(url=CREATE_SHIPMENT_ROUTE, status_code=status.HTTP_302_FOUND)

@router.get(EDIT_SHIPMENT_ROUTE, response_class=HTMLResponse)
async def get_edit_shipment(request: Request, current_user: dict = Depends(verify_admin)):
    """
    Displays the page for editing existing shipments. Requires admin role.
    Fetches all shipments for display.
    """
    logger.info(f"Edit shipment page requested by {current_user['email']}.")
    shipment_collection = get_shipment_collection()
    flash = request.session.pop("flash", None) # Retrieve and clear flash messages
    
    shipments_cursor = shipment_collection.find({}, {"_id": 0}) # Find all shipments, exclude '_id'
    shipments = []
    for shipment in shipments_cursor:
        # Format datetime fields for display
        if isinstance(shipment.get("created_at"), datetime):
            shipment["created_at"] = shipment["created_at"].strftime(DATETIME_DISPLAY_FORMAT)
        if isinstance(shipment.get("last_updated"), datetime):
            shipment["last_updated"] = shipment["last_updated"].strftime(DATETIME_DISPLAY_FORMAT)
        shipments.append(shipment)
    return templates_instance.TemplateResponse("edit_shipment.html", {"request": request, "shipments": shipments, "flash": flash})

@router.post(EDIT_SHIPMENT_ROUTE)
async def post_edit_shipment(
    request: Request,
    current_user: dict = Depends(verify_admin),
    shipment_id: str = Form(...),
    status_value: str = Form(...),
    destination: str = Form(...),
    expected_delivery_date: str = Form(...)
):
    """
    Handles the submission for updating an existing shipment. Requires admin role.
    """
    logger.info(f"Admin {current_user['email']} updating shipment {shipment_id}.")
    shipment_collection = get_shipment_collection()

    update_data = {
        "status": status_value,
        "destination": destination,
        "expected_delivery_date": expected_delivery_date,
        "last_updated": datetime.now(timezone.utc),
        "updated_by": current_user["email"]
    }
    # Update the shipment document in MongoDB
    result = shipment_collection.update_one(
        {"shipment_id": shipment_id},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        request.session["flash"] = "Shipment updated successfully."
        logger.info(f"Shipment {shipment_id} updated successfully.")
    else:
        request.session["flash"] = "No changes made or shipment not found."
        logger.warning(f"No update performed for shipment {shipment_id}.")
    return RedirectResponse(url=EDIT_SHIPMENT_ROUTE, status_code=status.HTTP_302_FOUND)

@router.get("/delete-shipment/{shipment_id}")
async def delete_shipment(shipment_id: str, request: Request, current_user: dict = Depends(verify_admin)):
    """
    Deletes a specified shipment. Requires admin role.
    """
    logger.info(f"Admin {current_user['email']} deleting shipment {shipment_id}.")
    shipment_collection = get_shipment_collection()
    try:
        # Delete the shipment document
        result = shipment_collection.delete_one({"shipment_id": shipment_id})
        if result.deleted_count > 0:
            request.session["flash"] = "Shipment deleted successfully."
            logger.info(f"Shipment {shipment_id} deleted.")
        else:
            request.session["flash"] = "Shipment not found or already deleted."
            logger.warning(f"Delete attempted on non-existent shipment {shipment_id}.")
    except Exception as e:
        request.session["flash"] = f"Error deleting shipment: {str(e)}"
        logger.error(f"Error deleting shipment {shipment_id}: {e}")
    return RedirectResponse(url=EDIT_SHIPMENT_ROUTE, status_code=status.HTTP_302_FOUND)

@router.get("/all-shipments", response_class=HTMLResponse)
async def get_all_shipments(request: Request, current_user: dict = Depends(get_current_active_user)):
    """
    Displays a list of all shipments.
    """
    logger.info(f"All shipments page requested by {current_user['email']}.")
    shipment_collection = get_shipment_collection()
    
    shipments_cursor = shipment_collection.find({}, {"_id": 0}) # Find all shipments, exclude '_id'
    shipments = []
    for shipment in shipments_cursor:
        # Format datetime fields for display
        if isinstance(shipment.get("created_at"), datetime):
            shipment["created_at"] = shipment["created_at"].strftime(DATETIME_DISPLAY_FORMAT)
        # Add other datetime fields if necessary (e.g., 'last_updated')
        if isinstance(shipment.get("last_updated"), datetime):
            shipment["last_updated"] = shipment["last_updated"].strftime(DATETIME_DISPLAY_FORMAT)
        shipments.append(shipment)
    flash = request.session.pop("flash", None) # Retrieve and clear flash messages
    return templates_instance.TemplateResponse("all_shipments.html", {
        "request": request,
        "shipments": shipments,
        "role": current_user["role"],
        "flash": flash
    })

