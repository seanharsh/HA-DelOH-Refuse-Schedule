"""Holiday parser for Delaware refuse collection schedule adjustments."""
from __future__ import annotations

import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple
from io import BytesIO

import requests
from PyPDF2 import PdfReader

from .const import HOLIDAY_DOCUMENT_URL

_LOGGER = logging.getLogger(__name__)


class HolidayParser:
    """Parser for Delaware refuse collection holiday schedules."""

    def __init__(self):
        """Initialize the holiday parser."""
        self.holidays: Dict[date, Dict[str, Any]] = {}

    def fetch_holiday_schedule(self) -> bytes:
        """
        Fetch the holiday schedule document.

        Returns:
            PDF content as bytes

        Raises:
            requests.RequestException: If download fails
        """
        _LOGGER.debug("Fetching holiday schedule from %s", HOLIDAY_DOCUMENT_URL)

        # Add headers to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.delawareohio.net"
        }

        response = requests.get(HOLIDAY_DOCUMENT_URL, headers=headers, timeout=30)
        response.raise_for_status()

        return response.content

    def parse_pdf(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Parse the PDF document and extract holiday information.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            List of holiday dictionaries with date and adjustment info
        """
        _LOGGER.debug("Parsing PDF content")

        holidays = []

        try:
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PdfReader(pdf_file)

            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text()

            _LOGGER.debug("Extracted text length: %d characters", len(full_text))

            # Split into sections by holiday entry
            # Pattern: "Day, Month Date   Holiday Name"
            # Example: "Monday, January 20   Martin Luther King, Jr. Day"
            lines = full_text.split('\n')

            current_holiday = None
            current_text = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if this line starts a new holiday entry
                # Format: "Day, Month Date   Holiday Name"
                date_match = re.match(
                    r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
                    r'(\w+)\s+(\d{1,2})(?:,\s+(\d{4}))?\s+(.+)',
                    line
                )

                if date_match:
                    # Save previous holiday if exists
                    if current_holiday and current_text:
                        holiday_info = self._parse_holiday_entry(
                            current_holiday, '\n'.join(current_text)
                        )
                        if holiday_info:
                            holidays.append(holiday_info)

                    # Start new holiday
                    day_of_week = date_match.group(1)
                    month_name = date_match.group(2)
                    day = int(date_match.group(3))
                    year = int(date_match.group(4)) if date_match.group(4) else datetime.now().year
                    holiday_name = date_match.group(5).strip()

                    # Parse the date
                    try:
                        holiday_date = datetime.strptime(
                            f"{month_name} {day}, {year}", "%B %d, %Y"
                        ).date()

                        current_holiday = {
                            "name": holiday_name,
                            "date": holiday_date,
                            "day_of_week": day_of_week
                        }
                        current_text = []
                    except ValueError:
                        _LOGGER.warning("Could not parse date: %s %d, %d", month_name, day, year)
                        current_holiday = None
                else:
                    # Add to current holiday's text
                    if current_holiday:
                        current_text.append(line)

            # Don't forget the last holiday
            if current_holiday and current_text:
                holiday_info = self._parse_holiday_entry(
                    current_holiday, '\n'.join(current_text)
                )
                if holiday_info:
                    holidays.append(holiday_info)

            _LOGGER.info("Parsed %d holidays from PDF", len(holidays))

        except Exception as err:
            _LOGGER.error("Error parsing PDF: %s", err)
            raise

        return holidays

    def _parse_holiday_entry(
        self, holiday: Dict[str, Any], text: str
    ) -> Dict[str, Any] | None:
        """
        Parse a single holiday entry's text to extract adjustment information.

        Args:
            holiday: Dictionary with name, date, day_of_week
            text: Text describing the collection adjustments

        Returns:
            Complete holiday dictionary with adjustment info
        """
        adjustment = {}

        # Normalize whitespace for better matching (PDF extraction can have extra spaces)
        normalized_text = re.sub(r'\s+', ' ', text)

        # Pattern 1: "No Collection Delays this week"
        if "No Collection Delays" in text or "No Delay" in text:
            adjustment["type"] = "none"

        # Pattern 2: "Collections will be delayed one day this week"
        elif re.search(r'delayed\s+one\s+day', normalized_text, re.IGNORECASE):
            adjustment["type"] = "shift_one_day"
            # Find which day has no collection
            no_collection_match = re.search(
                r'Collections will NOT\s+occur on (Monday|Tuesday|Wednesday|Thursday|Friday)',
                normalized_text
            )
            if no_collection_match:
                adjustment["no_collection_day"] = no_collection_match.group(1)

        # Pattern 3: Specific day rescheduling
        # "Monday collections will take place on Tuesday"
        # Note: "take place" might be split as "take pl ace" in PDF extraction
        elif re.search(r'collections will (?:take pl?\s*ace|occur) on', normalized_text, re.IGNORECASE):
            adjustment["type"] = "specific_reschedule"
            adjustment["reschedules"] = []

            # Find all reschedule patterns
            reschedule_matches = re.finditer(
                r'(Monday|Tuesday|Wednesday|Thursday|Friday) collections will (?:take pl?\s*ace|occur) on (Monday|Tuesday|Wednesday|Thursday|Friday)',
                normalized_text
            )

            for match in reschedule_matches:
                from_day = match.group(1)
                to_day = match.group(2)
                adjustment["reschedules"].append({
                    "from": from_day,
                    "to": to_day
                })

        # Pattern 4: Accelerated schedule (earlier pickup but same day)
        elif "accelerated schedule" in text:
            adjustment["type"] = "accelerated"

        # Default: if we see "Collections will NOT occur" but no delay, assume it's rescheduled
        elif "will NOT occur" in normalized_text:
            adjustment["type"] = "specific_reschedule"
            adjustment["reschedules"] = []

            # Try to find the reschedule info
            reschedule_matches = re.finditer(
                r'(Monday|Tuesday|Wednesday|Thursday|Friday) collections will (?:take pl?\s*ace|occur) on (Monday|Tuesday|Wednesday|Thursday|Friday)',
                normalized_text
            )

            for match in reschedule_matches:
                from_day = match.group(1)
                to_day = match.group(2)
                adjustment["reschedules"].append({
                    "from": from_day,
                    "to": to_day
                })

        holiday["adjustment"] = adjustment
        holiday["description"] = text

        return holiday

    def _parse_adjustment(self, text: str) -> Dict[str, str]:
        """
        Parse the schedule adjustment from text.

        Args:
            text: Text containing adjustment information

        Returns:
            Dictionary mapping original day to adjusted day
        """
        # TODO: Implement based on actual document format
        # Example: "Monday collection moves to Tuesday" ->
        # {"Monday": "Tuesday"}

        adjustment = {}

        # Common patterns:
        # "Monday to Tuesday"
        # "Monday collection delayed to Tuesday"
        # "No collection on Monday, pickup on Tuesday"

        pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday).*?(to|delayed to|pickup on)\s+(Monday|Tuesday|Wednesday|Thursday|Friday)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            original_day = match.group(1).capitalize()
            adjusted_day = match.group(3).capitalize()
            adjustment[original_day] = adjusted_day

        return adjustment

    def get_adjusted_date(self, original_date: date, collection_day: str) -> date | None:
        """
        Get the adjusted collection date if it falls on a holiday.

        Args:
            original_date: The original scheduled collection date
            collection_day: Day of week (e.g., "Monday")

        Returns:
            The adjusted date if there's a holiday adjustment, None if no collection,
            otherwise original_date
        """
        # Check if this date is a holiday
        if original_date not in self.holidays:
            return original_date

        holiday_info = self.holidays[original_date]
        adjustment = holiday_info.get("adjustment", {})
        adj_type = adjustment.get("type")

        _LOGGER.debug(
            "Checking adjustment for %s on %s (holiday: %s, type: %s)",
            collection_day, original_date, holiday_info.get("name"), adj_type
        )

        # No adjustment needed
        if adj_type == "none":
            return original_date

        # Accelerated schedule - same day, just earlier
        if adj_type == "accelerated":
            return original_date

        # Shift entire week by one day
        if adj_type == "shift_one_day":
            no_collection_day = adjustment.get("no_collection_day")
            # If the holiday falls on the collection day, shift forward by 1
            if collection_day == no_collection_day:
                return original_date + timedelta(days=1)
            # If collection day is after the holiday in the week, also shift
            week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            if (no_collection_day in week_days and collection_day in week_days and
                week_days.index(collection_day) > week_days.index(no_collection_day)):
                return original_date + timedelta(days=1)
            return original_date

        # Specific day rescheduling
        if adj_type == "specific_reschedule":
            reschedules = adjustment.get("reschedules", [])

            for reschedule in reschedules:
                if collection_day == reschedule["from"]:
                    to_day = reschedule["to"]
                    days_offset = self._get_day_offset(collection_day, to_day)
                    return original_date + timedelta(days=days_offset)

            return original_date

        # Unknown adjustment type - return original date
        return original_date

    def _get_day_offset(self, from_day: str, to_day: str) -> int:
        """
        Calculate the offset in days between two weekday names.

        Args:
            from_day: Starting day name (e.g., "Monday")
            to_day: Target day name (e.g., "Tuesday")

        Returns:
            Number of days to add
        """
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        try:
            from_idx = days.index(from_day)
            to_idx = days.index(to_day)

            offset = to_idx - from_idx
            if offset <= 0:
                offset += 7

            return offset
        except ValueError:
            _LOGGER.error("Invalid day name: %s or %s", from_day, to_day)
            return 0

    def update(self) -> None:
        """Fetch and update the holiday schedule."""
        try:
            pdf_content = self.fetch_holiday_schedule()
            holidays_list = self.parse_pdf(pdf_content)

            # Convert list to dictionary indexed by date
            self.holidays = {h["date"]: h for h in holidays_list}

            _LOGGER.info("Updated holiday schedule with %d holidays", len(self.holidays))

        except Exception as err:
            _LOGGER.error("Failed to update holiday schedule: %s", err)
            # Don't raise - use cached holidays if update fails
