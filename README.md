## Polling Window

The poller retrieves sensor data using 10-minute aligned, half-open time windows.

flowchart TD
    A["**Polling Orchestrator**<br/>run_polling()"]
    B["**Checkpoint Management**<br/>Load checkpoint<br/>Calculate polling window"]
    C["**Data Ingestion**<br/>HTTP Client<br/>External SCADA API"]
    D["**Data Processing**<br/>Vendor Adapter<br/>Canonical Mapping<br/>Turbine ID Resolution<br/>Data Validation"]
    E["**Data Persistence**<br/>PostgreSQL UPSERT<br/>Update Checkpoint"]
    F["**Success / Failure**<br/>Success: Update last_success_at<br/>Failure: Record last_attempt_at and last_error<br/>Retry on next execution"]

    A --> B --> C --> D --> E --> F

### Initial Polling

If no successful checkpoint exists, retrieve the latest one-hour window.

**Example:** Current time = `10:23`

```text
start_at = 09:20
end_at   = 10:20

Window: [09:20, 10:20)
```

### Normal Polling

Start from the last successful checkpoint.

**Example:** Last successful end = `10:10`

```text
start_at = 10:10
end_at   = 10:20

Window: [10:10, 10:20)
```

### Long Outages

Split the missing time range into sequential requests, each limited by `MAX_WINDOW`.

**Example:** Last checkpoint = `09:00`, Current time = `12:23`, `MAX_WINDOW = 1 hour`

```text
Request 1: [09:00, 10:00)
Request 2: [10:00, 11:00)
Request 3: [11:00, 12:00)
```

Continue until the latest available interval is reached.

## Data Normalization

Vendor-specific adapters convert SCADA API responses into a common internal format.

| External field | Internal Canonical field |
|---|---|
| `turbine_code` | `turbine_id` |
| `timestamp` | `measured_at` |
| `wind_speed` | `wind_speed_ms` |
| `active_power` | `power_output_kw` |
| `rotor_speed` | `rotor_speed_rpm` |