"""Calendar platform for Delaware Refuse Schedule."""
from __future__ import annotations

from datetime import datetime, date, timedelta
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CALENDAR_NAME
from .coordinator import DelawareRefuseCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Delaware Refuse Schedule calendar platform."""
    coordinator: DelawareRefuseCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([DelawareRefuseCalendar(coordinator, entry)], True)


class DelawareRefuseCalendar(CoordinatorEntity, CalendarEntity):
    """Representation of a Delaware Refuse Schedule calendar."""

    def __init__(
        self, coordinator: DelawareRefuseCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._entry = entry

        # Use address for the entity name
        address = coordinator.address
        self._attr_name = f"Refuse Schedule - {address}"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"

        # Set suggested entity_id based on address (sanitized)
        # Remove special characters and convert to lowercase with underscores
        safe_address = address.lower().replace(',', '').replace('.', '')
        safe_address = ''.join(c if c.isalnum() or c.isspace() else '_' for c in safe_address)
        safe_address = '_'.join(safe_address.split())
        self._attr_has_entity_name = False
        self.entity_id = f"calendar.delawareoh_refuse_{safe_address}"

        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    async def async_update(self) -> None:
        """Update the calendar."""
        await super().async_update()

        # Find the next upcoming event
        now = dt_util.now()
        upcoming_events = self.coordinator.get_events(
            now, now + timedelta(days=30)
        )

        if upcoming_events:
            # Sort by start date and get the first one
            upcoming_events.sort(key=lambda x: x["start"])
            next_event = upcoming_events[0]

            # For all-day events, keep as date objects
            # For timed events, convert to datetime
            start = next_event["start"]
            end = next_event["end"]
            is_all_day = next_event.get("all_day", False)

            # All-day events should be date objects, not datetime
            if is_all_day:
                # Ensure we have date objects
                if isinstance(start, datetime):
                    start = start.date()
                if isinstance(end, datetime):
                    end = end.date()
            else:
                # Timed events need timezone-aware datetime objects
                if isinstance(start, date) and not isinstance(start, datetime):
                    start = datetime.combine(start, datetime.min.time())
                    start = dt_util.as_local(start)
                elif isinstance(start, datetime) and start.tzinfo is None:
                    start = dt_util.as_local(start)

                if isinstance(end, date) and not isinstance(end, datetime):
                    end = datetime.combine(end, datetime.min.time())
                    end = dt_util.as_local(end)
                elif isinstance(end, datetime) and end.tzinfo is None:
                    end = dt_util.as_local(end)

            self._event = CalendarEvent(
                summary=next_event["summary"],
                start=start,
                end=end,
                description=next_event.get("description", ""),
            )
        else:
            self._event = None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = self.coordinator.get_events(start_date, end_date)

        calendar_events = []
        for event in events:
            start = event["start"]
            end = event["end"]
            is_all_day = event.get("all_day", False)

            # All-day events should be date objects, not datetime
            if is_all_day:
                # Ensure we have date objects
                if isinstance(start, datetime):
                    start = start.date()
                if isinstance(end, datetime):
                    end = end.date()
            else:
                # Timed events need timezone-aware datetime objects
                if isinstance(start, date) and not isinstance(start, datetime):
                    start = datetime.combine(start, datetime.min.time())
                    start = dt_util.as_local(start)
                elif isinstance(start, datetime) and start.tzinfo is None:
                    start = dt_util.as_local(start)

                if isinstance(end, date) and not isinstance(end, datetime):
                    end = datetime.combine(end, datetime.min.time())
                    end = dt_util.as_local(end)
                elif isinstance(end, datetime) and end.tzinfo is None:
                    end = dt_util.as_local(end)

            calendar_events.append(
                CalendarEvent(
                    summary=event["summary"],
                    start=start,
                    end=end,
                    description=event.get("description", ""),
                )
            )

        return calendar_events

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.coordinator.data:
            return {}

        return {
            "collection_day": self.coordinator.data.get("collection_day"),
            "address": self.coordinator.data.get("address"),
            "last_updated": self.coordinator.data.get("last_updated"),
        }
