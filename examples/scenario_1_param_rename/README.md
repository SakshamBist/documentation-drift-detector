# Scenario 1 Documentation: Database Client

### `connect_to_database()`

Establishes a connection to the primary database cluster.

#### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `host` | str | The server hostname |
| `port` | int | Connection port (default: 5432) |
| `timeout_secs` | int | Obsolete connection timeout in seconds |
