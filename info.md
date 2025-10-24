# Delaware Refuse Schedule

A Home Assistant custom integration that creates a calendar entity for Delaware, Ohio refuse and recycling collection schedules.

## Features

- **Automatic Address Lookup**: Determines your collection day from your Delaware, OH address
- **Holiday Adjustments**: Automatically adjusts collection dates for city holidays
- **Calendar Integration**: Creates a Home Assistant calendar entity with all upcoming collections
- **Unified Events**: All events labeled "Trash & Recycling Collection" for simplicity
- **All-Day Events**: Collection events appear as all-day events in your calendar

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the 3-dot menu → "Custom repositories"
4. Add this repository URL
5. Select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/delawareoh_refuse` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for "Delaware Refuse Schedule"
4. Enter your Delaware, Ohio address (e.g., "1 Sandusky St, Delaware, OH")
5. Set update interval in days (default is 90, recommended to leave as-is)
6. Click **Submit**

The integration will:
- Look up the collection day using Delaware County's site
- Download the current holiday schedule
- Create a calendar entity with your collection schedule, appears as an all-day event

## Usage

Once configured, you'll have a calendar entity named "Refuse Schedule - [Your Address]" that shows:
- **Trash & Recycling Collection**: Weekly events on your collection day
- **Holiday Adjustments**: Automatically moves collection dates when holidays effect collection (e.g., Thanksgiving Thursday collection moves to Friday)

### Entity ID

The calendar entity ID will be based on your address:
- Format: `calendar.delawareoh_refuse_[sanitized_address]`
- Example: `calendar.delawareoh_refuse_1_sandusky_st`

### Example Automation

Get a reminder the night before trash collection:

```yaml
automation:
  - alias: "Trash Collection Reminder"
    trigger:
      - platform: calendar
        entity_id: calendar.delawareoh_refuse_1_sandusky_st
        event: start
        offset: "-18:00:00"  # 18 hours before (6pm day before)
    action:
      - service: notify.mobile_app
        data:
          title: "Trash Collection Tomorrow"
          message: "Don't forget to put out the trash tonight!"
```

## Data Sources

This integration uses official Delaware, Ohio resources:
- **Address Lookup**: Delaware County Refuse Collection Map
- **Holiday Schedule**: Delaware Public Works 2025 Holiday Document