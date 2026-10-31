# Scenario 3 Documentation: Auth Module

### `authenticate_user()`

Authenticates user against the central identity provider.

#### Parameters
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `username` | str | User account handle |
| `token` | str | Bearer auth token |
| `use_ssl` | bool | Legacy boolean flag indicating if SSL should be used |
