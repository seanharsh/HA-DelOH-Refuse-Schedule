"""ArcGIS client for Delaware County address lookup."""
from __future__ import annotations

import logging
from typing import Any

import requests

from .const import ARCGIS_GEOCODE_URL, ARCGIS_REFUSE_LAYER_URL, ARCGIS_DAY_FIELD

_LOGGER = logging.getLogger(__name__)


class ArcGISClient:
    """Client for interacting with Delaware County ArcGIS service."""

    def __init__(self):
        """Initialize the ArcGIS client."""
        self.geocode_url = ARCGIS_GEOCODE_URL
        self.refuse_layer_url = ARCGIS_REFUSE_LAYER_URL
        self.day_field = ARCGIS_DAY_FIELD

    def lookup_address(self, address: str) -> dict[str, Any]:
        """
        Look up an address and return collection information.

        Args:
            address: Street address in Delaware, Ohio

        Returns:
            Dictionary containing collection_day and zone information

        Raises:
            ValueError: If address cannot be found or is invalid
            requests.RequestException: If API request fails
        """
        _LOGGER.debug("Looking up address: %s", address)

        # Step 1: Geocode the address to get coordinates
        geocode_params = {
            "f": "json",
            "address": address,
            "city": "Delaware",
            "state": "OH",
            "outFields": "*"
        }

        _LOGGER.debug("Geocoding address with params: %s", geocode_params)
        geocode_response = requests.get(
            self.geocode_url, params=geocode_params, timeout=30
        )
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()

        if not geocode_data.get("candidates"):
            raise ValueError(f"Address not found: {address}")

        location = geocode_data["candidates"][0]["location"]
        _LOGGER.debug("Geocoded to coordinates: (%s, %s)", location['x'], location['y'])

        # Step 2: Query RefuseDay layer with coordinates
        query_url = f"{self.refuse_layer_url}/query"
        query_params = {
            "f": "json",
            "geometry": f"{location['x']},{location['y']}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",  # WGS84
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false"
        }

        _LOGGER.debug("Querying refuse layer: %s", query_url)
        feature_response = requests.get(query_url, params=query_params, timeout=30)
        feature_response.raise_for_status()
        feature_data = feature_response.json()

        if not feature_data.get("features"):
            raise ValueError(f"No collection zone found for address: {address}")

        # Step 3: Extract collection day from response
        attributes = feature_data["features"][0]["attributes"]
        collection_day = attributes.get(self.day_field, "").strip()

        if not collection_day:
            raise ValueError(f"Collection day not set for address: {address}")

        # Normalize to title case (MONDAY -> Monday)
        collection_day = collection_day.capitalize()

        _LOGGER.info("Address %s has collection day: %s", address, collection_day)

        return {
            "collection_day": collection_day,
            "zone": attributes.get("OBJECTID"),
            "address": address,
            "coordinates": location
        }

    def get_collection_day(self, address: str) -> str:
        """
        Get the collection day for an address.

        Args:
            address: Street address in Delaware, Ohio

        Returns:
            Day of week (e.g., "Monday", "Tuesday")
        """
        result = self.lookup_address(address)
        return result.get("collection_day", "Unknown")
