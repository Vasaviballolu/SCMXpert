# app/database.py

from pymongo import MongoClient
from app.config import MONGO_URI, logger

# Global variables for MongoDB client and database instance
client = None
db = None
users_collection = None
logins_collection = None
shipment_collection = None
device_data_collection = None

def connect_to_mongodb():
    """
    Establishes a connection to MongoDB and initializes collection objects.
    This function should be called once during application startup.
    """
    global client, db, users_collection, logins_collection, shipment_collection, device_data_collection
    try:
        # Create a MongoClient instance using the URI from config.
        client = MongoClient(MONGO_URI)
        # Access the 'scmexpert' database.
        db = client["scmexpert"]
        # Initialize collection objects for various data types.
        users_collection = db["user"]
        logins_collection = db["logins"]
        shipment_collection = db["shipments"]
        device_data_collection = db["device_data"]
        logger.info("MongoDB connection established and collections initialized.")
    except Exception as e:
        # Log a critical error if connection fails and re-raise the exception.
        logger.critical(f"Failed to connect to MongoDB: {e}")
        raise

def get_database():
    """
    Returns the MongoDB database instance.
    Ensures that the connection is established before returning the database.
    """
    if db is None:
        # If db is not initialized, attempt to connect.
        connect_to_mongodb()
    return db

def get_users_collection():
    """Returns the 'user' collection."""
    if users_collection is None:
        connect_to_mongodb()
    return users_collection

def get_logins_collection():
    """Returns the 'logins' collection."""
    if logins_collection is None:
        connect_to_mongodb()
    return logins_collection

def get_shipment_collection():
    """Returns the 'shipments' collection."""
    if shipment_collection is None:
        connect_to_mongodb()
    return shipment_collection

def get_device_data_collection():
    """Returns the 'device_data' collection."""
    if device_data_collection is None:
        connect_to_mongodb()
    return device_data_collection

