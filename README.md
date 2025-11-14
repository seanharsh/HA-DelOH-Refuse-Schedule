# Delaware OH Refuse Schedule - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/seanharsh/HA-DelOH-Refuse-Schedule.svg)](https://github.com/seanharsh/HA-DelOH-Refuse-Schedule/releases)
[![License](https://img.shields.io/github/license/seanharsh/HA-DelOH-Refuse-Schedule.svg)](LICENSE)

A Home Assistant custom integration that creates a calendar entity for Delaware, Ohio refuse and recycling collection schedules. Automatically determines your collection day based on your address and adjusts for holidays.

## Features

- **Automatic Address Lookup**: Uses Delaware County's lookup map to determine your collection day
- **Holiday Adjustments**: Automatically adjusts collection dates for city holidays
- **Calendar Integration**: Creates a Home Assistant calendar entity with all upcoming collections
- **Unified Events**: All events labeled "Trash & Recycling Collection"
- **All-Day Events**: Collection events appear as all-day events in your calendar
- **Automatic Updates**: Refreshes schedule and holiday information every 90 days (configurable)

## Installation

### HACS (Recommended)

## Installing

1. Install via HACS either by searching for HA-DelOH-Refuse-Schedule or clicking the icon below:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=seanharsh&repository=ha-deloH-refuse-schedule)

2. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/delawareoh_refuse` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for "Delaware OH Refuse Schedule"
4. Enter your Delaware, Ohio street address (e.g., "1 Sandusky St")
5. Set the update interval (default: 90 days)
6. Click **Submit**

The integration will:
- Look up your collection day using Delaware County's map
- Download and parse the current holiday schedule
- Create a calendar entity with your collection schedule

### Configuration Options

- **Address**: Your street address in Delaware, Ohio
- **Update Interval**: How often to check for schedule updates (1-365 days, default: 90)

## Usage

Once configured, you'll have a calendar entity named "Refuse Schedule - [Your Address]" that shows:

- **Trash & Recycling Collection**: Weekly events on your collection day
- **Holiday Adjustments**: Automatically moved dates when holidays affect collection

### Entity ID Format

The calendar entity ID is based on your address:
- Format: `calendar.delawareoh_refuse_[sanitized_address]`
- Example: `calendar.delawareoh_refuse_1_sandusky_st`

### Calendar Entity Usage

The calendar entity can be used in:

- **Calendar Cards**: Display upcoming collections in your dashboard
- **Automations**: Trigger reminders or actions before collection day
- **Google Calendar Sync**: Sync to external calendars
- **Mobile App**: View collection schedule on your phone

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

## Holiday Adjustments

The integration automatically handles Delaware's holiday schedule:

- **Memorial Day** (Monday): All collections shift forward one day
- **Independence Day** (Friday): Friday collection moves to Saturday
- **Labor Day** (Monday): All collections shift forward one day
- **Thanksgiving** (Thursday): Thursday→Friday, Friday→Saturday
- **Christmas** (Thursday): Thursday→Friday, Friday→Saturday
- **New Year's Day** (Thursday): Thursday→Friday, Friday→Saturday

When holidays affect your collection day, the calendar automatically shows the adjusted date.

## Data Sources

This integration uses official Delaware, Ohio resources:

- **Address Lookup**: [Delaware County Refuse Collection Map](https://codgis.maps.arcgis.com/apps/instant/lookup/index.html?appid=deefc01bfe8e4b86b37dd3281e06c9e7)
- **Holiday Schedule**: [Delaware Public Works 2025 Holiday Document](https://www.delawareohio.net/home/showpublisheddocument/4148/638689880014270000)

## Troubleshooting

### Integration Not Appearing

- Ensure you've restarted Home Assistant after installation
- Check that files are in `config/custom_components/delawareoh_refuse/`
- Check Home Assistant logs for errors

### Address Not Found

- Verify your address is within Delaware, Ohio city limits
- Try different address formats (e.g., "1 Sandusky St" vs "1 Sandusky Street")
- Check the [official map](https://codgis.maps.arcgis.com/apps/instant/lookup/index.html?appid=deefc01bfe8e4b86b37dd3281e06c9e7) to ensure your address is in the system

### No Events Showing

- Check that the integration loaded successfully in Devices & Services
- Verify the coordinator is updating (check entity attributes)
- Enable debug logging to see detailed information

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.delawareoh_refuse: debug
```

Then restart Home Assistant and check the logs.

## Support

For issues, questions, or feature requests:

- **GitHub Issues**: [Report an issue](https://github.com/seanharsh/HA-DelOH-Refuse-Schedule/issues)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with the City of Delaware, Ohio or Delaware County. Use at your own risk.