import os
import sys
import requests
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Flask App Configuration
app = Flask(__name__)
CORS(app)

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_address_from_coordinates(latitude, longitude):
    """
    Reverse geocode coordinates using OpenStreetMap Nominatim API
    """
    try:
        # OpenStreetMap Nominatim API endpoint
        url = f"https://nominatim.openstreetmap.org/reverse"
        
        # Parameters for reverse geocoding
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1
        }
        
        # Headers to respect Nominatim usage policy
        headers = {
            'User-Agent': 'LocationTrackerApp/1.0'
        }
        
        # Make request to Nominatim
        response = requests.get(url, params=params, headers=headers)
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Extract address components
            if 'display_name' in data:
                # Full address string
                full_address = data.get('display_name', 'Unknown Location')
                
                # More structured address extraction
                address_components = data.get('address', {})
                
                # Create a more structured address dictionary
                structured_address = {
                    'full_address': full_address,
                    'city': address_components.get('city', ''),
                    'province': address_components.get('province', ''),
                    'country': address_components.get('country', ''),
                    'postcode': address_components.get('postcode', '')
                }
                
                return structured_address
        
        return {'full_address': 'Location not found'}
    
    except Exception as e:
        logger.error(f"Address lookup error: {str(e)}")
        return {'full_address': 'Location lookup failed'}

def get_mongodb_connection():
    """
    Establish and test MongoDB connection
    Returns the database connection or None if failed
    """
    try:
        # Get MongoDB URI from environment variable
        MONGO_URI = os.getenv('MONGODB_CONNECTION_STRING')
        
        if not MONGO_URI:
            logger.error("MongoDB URI is not set in environment variables")
            return None

        # Create MongoDB Client with connection timeout
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Test the connection
        client.admin.command('ismaster')
        
        # Get the database
        db = client.get_database('location_tracker')
        
        logger.info("Successfully connected to MongoDB Atlas")
        return db

    except Exception as e:
        logger.error(f"MongoDB Connection Error: {str(e)}")
        return None

# Global database connection
try:
    database = get_mongodb_connection()
    if database is None:
        logger.error("Failed to establish MongoDB connection")
        sys.exit(1)
    
    # Specific collection
    locations_collection = database.locations

except Exception as e:
    logger.error(f"Initialization Error: {str(e)}")
    sys.exit(1)

@app.route('/')
def index():
    """Render the main PWA page"""
    return render_template('index.html')

@app.route('/save_location', methods=['POST'])
def save_location():
    """
    Save location data to MongoDB Atlas
    Validates location is within Philippines
    """
    try:
        # Validate database connection
        if database is None:
            return jsonify({
                'status': 'error', 
                'message': 'Database connection lost'
            }), 500

        location_data = request.get_json()
        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')

        # Validate Philippines Bounding Box
        if not is_within_philippines(latitude, longitude):
            return jsonify({
                'status': 'error', 
                'message': 'Location outside Philippines'
            }), 400

        # Get address from coordinates
        address_info = get_address_from_coordinates(latitude, longitude)

        # Prepare MongoDB Document
        location_doc = {
            'latitude': float(latitude),
            'longitude': float(longitude),
            'address': address_info,
            'timestamp': datetime.utcnow()
        }

        # Insert Location
        result = locations_collection.insert_one(location_doc)

        logger.info(f"Location saved: {result.inserted_id}")
        return jsonify({
            'status': 'success', 
            'message': 'Location saved',
            'id': str(result.inserted_id),
            'address': address_info
        }), 200

    except Exception as e:
        logger.error(f"Location save error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

def is_within_philippines(lat, lon):
    """
    Validate if coordinates are within Philippines
    Rough bounding box for Philippines
    """
    try:
        lat = float(lat)
        lon = float(lon)
        return (
            4.5 <= lat <= 21.5 and 
            116.0 <= lon <= 127.0
        )
    except (ValueError, TypeError):
        return False

@app.route('/locations')
def get_locations():
    """Retrieve recent location history"""
    locations = list(locations_collection.find().sort('timestamp', -1).limit(50))
    
    # Convert ObjectId to string for JSON serialization
    for location in locations:
        location['_id'] = str(location['_id'])
    
    return jsonify(locations)

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)