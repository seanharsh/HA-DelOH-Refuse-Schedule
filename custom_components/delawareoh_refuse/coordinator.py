"""Data update coordinator for Delaware Refuse Schedule."""
from __future__ import annotations

from datetime import datetime, date, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_ADDRESS
from .arcgis_client import ArcGISClient
from .holiday_parser import HolidayParser

_LOGGER = logging.getLogger(__name__)


class DelawareRefuseCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Delaware refuse schedule data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.entry = entry
        self.address = entry.data[CONF_ADDRESS]
        self.arcgis_client = ArcGISClient()
        self.holiday_parser = HolidayParser()
        self.collection_day: str | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the ArcGIS service and holiday schedule."""
        try:
            # Get collection day for the address if we don't have it
            if not self.collection_day:
                _LOGGER.debug("Looking up collection day for address: %s", self.address)
                result = await self.hass.async_add_executor_job(
                    self.arcgis_client.lookup_address, self.address
                )
                self.collection_day = result.get("collection_day")
                _LOGGER.info("Collection day for %s: %s", self.address, self.collection_day)

            # Update holiday schedule (don't fail if this doesn't work)
            try:
                _LOGGER.debug("Updating holiday schedule")
                await self.hass.async_add_executor_job(self.holiday_parser.update)
                _LOGGER.debug("Holiday schedule updated successfully")
            except Exception as holiday_err:
                _LOGGER.warning(
                    "Could not update holiday schedule: %s. "
                    "Collection calendar will work without holiday adjustments.",
                    holiday_err
                )

            # Generate upcoming collection events
            events = self._generate_events()
            _LOGGER.debug("Generated %d collection events", len(events))

            return {
                "collection_day": self.collection_day,
                "address": self.address,
                "events": events,
                "last_updated": datetime.now(),
            }

        except Exception as err:
            _LOGGER.error("Error updating Delaware refuse schedule: %s", err, exc_info=True)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _generate_events(self, days_ahead: int = 90) -> list[dict[str, Any]]:
        """
        Generate collection events for the next N days.

        Args:
            days_ahead: Number of days to generate events for

        Returns:
            List of event dictionaries
        """
        if not self.collection_day:
            return []

        events = []
        today = date.today()

        # Map day names to weekday numbers
        day_mapping = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }

        target_weekday = day_mapping.get(self.collection_day)
        if target_weekday is None:
            _LOGGER.error("Invalid collection day: %s", self.collection_day)
            return []

        # Find all occurrences of the collection day in the next N days
        current_date = today
        end_date = today + timedelta(days=days_ahead)

        while current_date <= end_date:
            if current_date.weekday() == target_weekday:
                # Check if this date needs to be adjusted for a holiday
                # Need to check the entire week for holidays that might affect this day
                adjusted_date = self._get_adjusted_collection_date(current_date)

                if adjusted_date is None:
                    # No collection this day (cancelled)
                    current_date += timedelta(days=1)
                    continue

                # All events are "Trash & Recycling Collection"
                summary = "Trash & Recycling Collection"
                description = f"Trash and recycling collection for {self.address}"

                events.append({
                    "summary": summary,
                    "start": adjusted_date,
                    "end": adjusted_date,
                    "description": description,
                    "all_day": True,
                })

            current_date += timedelta(days=1)

        _LOGGER.debug("Generated %d collection events", len(events))
        return events

    def _get_adjusted_collection_date(self, scheduled_date: date) -> date | None:
        """
        Get the actual collection date accounting for holidays.

        This checks if there's a holiday during the week that affects this collection day.

        Args:
            scheduled_date: The normally scheduled collection date

        Returns:
            Adjusted date or None if collection is cancelled
        """
        # Check if the scheduled date itself is a holiday
        if scheduled_date in self.holiday_parser.holidays:
            holiday_info = self.holiday_parser.holidays[scheduled_date]
            adjustment = holiday_info.get("adjustment", {})
            adj_type = adjustment.get("type")

            _LOGGER.debug(
                "Collection day %s falls on holiday: %s (type: %s)",
                scheduled_date, holiday_info.get("name"), adj_type
            )

            # Check if this specific day is rescheduled
            if adj_type == "specific_reschedule":
                reschedules = adjustment.get("reschedules", [])
                for reschedule in reschedules:
                    if self.collection_day == reschedule["from"]:
                        # Move to the specified day
                        days_offset = self._get_day_offset(
                            reschedule["from"], reschedule["to"]
                        )
                        adjusted = scheduled_date + timedelta(days=days_offset)
                        _LOGGER.debug(
                            "Adjusting %s collection from %s to %s",
                            self.collection_day, scheduled_date, adjusted
                        )
                        return adjusted

            # Accelerated schedule - same day, just earlier pickup
            if adj_type == "accelerated":
                return scheduled_date

            # No adjustment needed
            if adj_type == "none":
                return scheduled_date

        # Check if there's a holiday earlier in the week that pushes this day forward
        # For "shift_one_day" holidays, all days after the holiday shift forward
        week_start = scheduled_date - timedelta(days=scheduled_date.weekday())

        for day_offset in range(scheduled_date.weekday()):
            check_date = week_start + timedelta(days=day_offset)
            if check_date in self.holiday_parser.holidays:
                holiday_info = self.holiday_parser.holidays[check_date]
                adjustment = holiday_info.get("adjustment", {})
                adj_type = adjustment.get("type")

                if adj_type == "shift_one_day":
                    # This holiday shifts the entire week
                    _LOGGER.debug(
                        "Holiday %s on %s shifts collection from %s to %s",
                        holiday_info.get("name"), check_date,
                        scheduled_date, scheduled_date + timedelta(days=1)
                    )
                    return scheduled_date + timedelta(days=1)

                elif adj_type == "specific_reschedule":
                    # Check if this holiday affects our collection day
                    reschedules = adjustment.get("reschedules", [])
                    for reschedule in reschedules:
                        # If a day before us is rescheduled to our day, we need to move
                        if reschedule["to"] == self.collection_day:
                            _LOGGER.debug(
                                "Holiday %s reschedules %s to %s, pushing %s forward",
                                holiday_info.get("name"), reschedule["from"],
                                reschedule["to"], scheduled_date
                            )
                            return scheduled_date + timedelta(days=1)

        return scheduled_date

    def _get_day_offset(self, from_day: str, to_day: str) -> int:
        """Calculate days between two weekday names."""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        try:
            from_idx = days.index(from_day)
            to_idx = days.index(to_day)
            offset = to_idx - from_idx
            if offset <= 0:
                offset += 7
            return offset
        except ValueError:
            return 0

    def get_events(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """
        Get events within a date range.

        Args:
            start_date: Start of date range (timezone-aware)
            end_date: End of date range (timezone-aware)

        Returns:
            List of events within the range
        """
        if not self.data or "events" not in self.data:
            return []

        events = []
        for event in self.data["events"]:
            event_date = event["start"]

            # Convert date to timezone-aware datetime for comparison
            if isinstance(event_date, date) and not isinstance(event_date, datetime):
                event_date = datetime.combine(event_date, datetime.min.time())
                event_date = dt_util.as_local(event_date)
            elif isinstance(event_date, datetime) and event_date.tzinfo is None:
                event_date = dt_util.as_local(event_date)

            # Ensure comparison dates are timezone-aware
            start_compare = start_date
            end_compare = end_date

            if start_compare.tzinfo is None:
                start_compare = dt_util.as_local(start_compare)
            if end_compare.tzinfo is None:
                end_compare = dt_util.as_local(end_compare)

            if start_compare <= event_date <= end_compare:
                events.append(event)

        return events
