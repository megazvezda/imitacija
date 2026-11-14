# Backend integration

Run the receiver separately. All crew and environment measurements use one configured `data_route`:

```toml
base_url = "http://localhost:9000"
data_route = "/data"
```

Both scopes send `POST http://localhost:9000/data`. `data_route` is a shared path, without owner/channel placeholders or per-channel overrides. It replaces the previous `crew_route`, `environment_route` and `channel_routes` settings; remove those keys from older configuration files.

Run normal delivery with `uv run imitacija --config config/healthy.toml` (without `--preview`). Set `IMITACIJA_TOKEN` if a Bearer token is required. The receiver distinguishes records using `X-Simulation-Scope` (`crew` / `environment`), `X-Owner-ID`, and the body’s `channel`. Multiple crew members produce independent records; each compartment sample is posted once. Add `[[crew]]` records with unique IDs to configure more crew.

The JSON body contains exactly four fields. Evaluation and result classification belong to a separate backend:

```json
{
  "channel": "bp_systolic",
  "value": 15198.75216531,
  "unit": "Pa",
  "measured_at": "2026-11-14T08:00:00Z"
}
```

The `unit` field names the wire unit of `value`, as defined by the channel registry. This illustrative 114 mmHg BP is transmitted in Pa. Boolean flags use `unit: "boolean"`; dimensionless numerical ratios use `"1"`. Temperature is K, pulse/respiration s⁻¹, saturation a fraction, volume m³, and dose Sv; consult the dictionary for every unit. The legacy `bone_ntx_pct_baseline` identifier is retained, but its SI-wire value is fractional **change** (0 = baseline, 0.03 = +3%), explicitly documented in the dictionary. The `ambient_light_lux` identifier uses lx. Boolean virus/SPE values remain JSON booleans.

`measured_at` is UTC point acquisition time or the end of the declared observation window. Laboratory results can arrive later and out of order. A receiver should not treat HTTP arrival order as collection order or overwrite a fresh sample with an older delayed specimen. It should not treat a missing/dry/unsampled channel as normal.

Headers supply the context without changing nigelNote's body:

| Header | Meaning |
| --- | --- |
| `Idempotency-Key` | Run + owner + channel + sequence; unchanged on retry. Receiver should deduplicate. |
| `X-Simulation-Run` | New unique delivery run on each process start. |
| `X-Simulation-Scope` | `crew` or `environment`. |
| `X-Owner-ID` | Crew ID or compartment ID according to scope. |
| `X-Sensor-ID` | Owner + acquisition group; paired results share the physical acquisition group. |
| `X-Window-Seconds` | 0 for point sampling; duration ending at `measured_at` otherwise. |
| `X-Simulation-Start`, `X-Simulation-Speed` | Mapping of run time to timestamps; acceleration must be explicit to the backend. |
| `X-Result-Available-Seconds` | Result eligibility time in elapsed simulation seconds, including configured lab/communication delay. |
| `X-Dictionary-Version` | Static registry schema/version, currently `1`. |
| `Authorization` | Optional Bearer token from the `IMITACIJA_TOKEN` environment variable. |

Return 2xx after accepting a reading. Permanent authentication/schema failures count as failed delivery; selected transient failures retry with the same body/key. Finite runs may discard delayed results at their bounded shutdown deadline. The ending counters report delivery, overflow, expiry, failure, retry and shutdown-drop totals. Reconcile accepted results with idempotency keys rather than expecting exactly-once network delivery.

Export static configuration-specific metadata before integration:

```sh
uv run imitacija --config config/healthy.toml --dictionary
```

Dictionary JSON retains nigelNote's `environment` and `channels` fields, and adds units, source units, specimen/method, collection/window/availability definitions, citations, enabled flags and exclusions. It is exported explicitly; the worker does not register it automatically or persist it. The receiver decides how to import/serve it and whether its ingestion contract accepts the proposed headers/routes.


## Local JSON preview

`--preview` exposes raw JSON at `/`, `/readings` and `/json`, and metadata at `/dictionary`. It replaces backend delivery with bounded latest-result state held only in RAM. The four-field `reading` object is the exact POST body; surrounding preview context includes conventional values, baselines and run/clock/owner metadata. Refresh to obtain another snapshot. Normal backend delivery does not start this local server.
