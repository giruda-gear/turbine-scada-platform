### Polling Window

The poller uses time-based windows to retrieve sensor readings incrementally.

All polling windows use a half-open interval:

`[start_at, end_at)` `[10:00, 10:10)`

The end time is rounded down to the nearest 10-minute boundary to avoid requesting the current incomplete measurement interval.

#### Initial Polling

When no successful checkpoint exists, the poller retrieves the most recent one-hour period.

For example, if the current time is 10:23:

- Start time: 09:20
- End time: 10:20
- Polling window: `[09:20, 10:20)`

#### Normal Polling

After the initial ingestion, the poller starts from the last successfully processed timestamp.

For example:

- Last successful end: 10:10
- Current time: 10:23
- Polling window: `[10:10, 10:20)`

This prevents previously processed time ranges from being requested again during normal operation.

#### Handling Long Outages

To avoid excessively large API requests after a prolonged outage, each request is limited by `MAX_WINDOW`.

For example, if the last successful checkpoint is 09:00 and the current time is 12:23:

- Request 1: `[09:00, 10:00)`
- Request 2: `[10:00, 11:00)`
- Request 3: `[11:00, 12:00)`

The poller processes these windows sequentially until it catches up with the latest available data.

## Data Normalization

Different SCADA vendors may use different API structures, turbine identifiers, and field names.
The ingestion pipeline uses vendor-specific adapters to convert external payloads into a standardized internal data format.

### Example

An external SCADA API may return the following payload:

```json
{
  "turbine_code": "WT-001",
  "timestamp": "2026-11-02T10:00:00Z",
  "wind_speed": 8.2,
  "active_power": 1450.0,
  "rotor_speed": 12.5
}
{
  "turbine_id": "internal-turbine-uuid",
  "measured_at": "2026-11-02T10:00:00Z",
  "wind_speed_ms": 8.2,
  "power_output_kw": 1450.0,
  "rotor_speed_rpm": 12.5
}
```