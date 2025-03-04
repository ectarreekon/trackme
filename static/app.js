const API_URL = window.location.origin;
let map, watchId, currentMarker;

function initMap() {
    // Initialize map centered on Philippines
    map = L.map('map').setView([12.8797, 121.7740], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

function saveLocation(position) {
    const { latitude, longitude } = position.coords;

    fetch(`${API_URL}/save_location`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ latitude, longitude })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            console.log('Location saved', data);
            updateLocationList();
            updateMapMarker(latitude, longitude, data.address);
        } else {
            console.error('Location save failed:', data.message);
            displayErrorMessage(data.message);
        }
    })
    .catch(error => {
        console.error('Error saving location:', error);
        displayErrorMessage('Failed to save location');
    });
}

function updateMapMarker(lat, lon, address) {
    // Remove previous marker if exists
    if (currentMarker) {
        map.removeLayer(currentMarker);
    }

    // Create popup content with address details
    const popupContent = `
        <b>Current Location</b><br>
        Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}<br>
        Address: ${address.full_address || 'Unknown'}
    `;

    // Add new marker
    currentMarker = L.marker([lat, lon])
        .addTo(map)
        .bindPopup(popupContent)
        .openPopup();

    // Center and zoom map to current location
    map.setView([lat, lon], 10);
}

function updateLocationList() {
    fetch(`${API_URL}/locations`)
    .then(response => response.json())
    .then(locations => {
        const list = document.getElementById('locationList');
        list.innerHTML = '<h2>Recent Locations</h2>';
        locations.forEach(loc => {
            const addressDetails = loc.address || {};
            list.innerHTML += `
                <div class="location-item">
                    <p>
                        Lat: ${loc.latitude.toFixed(4)}, 
                        Lon: ${loc.longitude.toFixed(4)}<br>
                        Full Address: ${addressDetails.full_address || 'Unknown'}<br>
                        City: ${addressDetails.city || 'N/A'}<br>
                        Province: ${addressDetails.province || 'N/A'}<br>
                        Time: ${new Date(loc.timestamp).toLocaleString()}
                    </p>
                </div>
            `;
        });
    })
    .catch(error => {
        console.error('Error fetching locations:', error);
        displayErrorMessage('Failed to fetch location history');
    });
}

function displayErrorMessage(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    // Hide error after 5 seconds
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function startTracking() {
    if ('geolocation' in navigator) {
        // Options for more accurate tracking
        const options = {
            enableHighAccuracy: true, 
            timeout: 10000,  // 10 seconds timeout
            maximumAge: 0    // Do not use cached location
        };

        watchId = navigator.geolocation.watchPosition(
            saveLocation, 
            error => {
                console.error('Geolocation error:', error);
                displayErrorMessage(error.message || 'Unable to retrieve location');
            }, 
            options
        );
    } else {
        displayErrorMessage('Geolocation is not supported by your browser');
    }
}

function stopTracking() {
    if (watchId) {
        navigator.geolocation.clearWatch(watchId);
        console.log('Location tracking stopped');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    startTracking();
});

// Optional: Add tracking controls
document.getElementById('startTracking').addEventListener('click', startTracking);
document.getElementById('stopTracking').addEventListener('click', stopTracking);
