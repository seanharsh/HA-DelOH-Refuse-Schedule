"""Constants for the Delaware Refuse Schedule integration."""

DOMAIN = "delawareoh_refuse"
CONF_ADDRESS = "address"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 90  # days
DEFAULT_SCAN_INTERVAL = 3600  # seconds (1 hour)

# ArcGIS Configuration
ARCGIS_LOOKUP_URL = "https://codgis.maps.arcgis.com/apps/instant/lookup/index.html?appid=deefc01bfe8e4b86b37dd3281e06c9e7"
ARCGIS_GEOCODE_URL = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
ARCGIS_REFUSE_LAYER_URL = "https://services.arcgis.com/eDETAHfuRDcwL2kQ/arcgis/rest/services/RefuseDay/FeatureServer/0"
ARCGIS_DAY_FIELD = "Day"

# Holiday Information
HOLIDAY_DOCUMENT_URL = "https://www.delawareohio.net/home/showpublisheddocument/4148/638689880014270000"

# Calendar Configuration
CALENDAR_NAME = "Delaware OH Refuse Schedule"
EVENT_TRASH = "Trash Collection"
EVENT_RECYCLING = "Recycling Collection"

# Days of week
WEEKDAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}
