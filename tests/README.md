# XR15 Bridge API Tests

REST Assured + Cucumber (BDD) test automation suite for the `xr15_server.py` BLE HTTP
bridge — covering the `/status`, `/on`, and `/off` endpoints used by the Home
Assistant `rest_command` integration.

## Stack

- Java 17
- Maven
- Cucumber 7 (JUnit 5 Platform Engine)
- REST Assured
- WireMock (embedded mock of the bridge, so the suite runs without real BLE hardware)

## Project layout

```
tests/
├── pom.xml
└── src/test/
    ├── java/com/mobius/xr15/tests/
    │   ├── runner/RunCucumberTest.java   # entry point Maven/Surefire runs
    │   ├── config/TestConfig.java        # base URL + mock/real toggle
    │   ├── hooks/Hooks.java              # starts/stops the mock server
    │   ├── mock/MockXr15Server.java      # WireMock stand-in for xr15_server.py
    │   └── steps/XR15Steps.java          # step definitions
    └── resources/features/
        ├── status.feature
        ├── power_control.feature
        └── error_handling.feature
```

## Running the tests

### Against the embedded mock (default, no hardware needed)

```bash
cd tests
mvn test
```

By default the suite starts an in-process WireMock server on port 8765 that mimics
`xr15_server.py`'s behavior (stateful `/on` → `/off` → `/status` transitions), so
it's safe to run in CI or on a laptop with no Raspberry Pi or BLE light attached.

### Against a real bridge server

Point the suite at an actual `xr15_server.py` instance (e.g. running on your
Raspberry Pi) and disable the mock:

```bash
cd tests
mvn test -Dxr15.baseUrl=http://192.168.50.182:8765 -Dxr15.useMock=false
```

Supplying `xr15.baseUrl` automatically disables the mock; `-Dxr15.useMock=false`
is shown for clarity but is optional. The base URL can also be supplied via the
`XR15_BASE_URL` environment variable.

> Note: `/on` and `/off` on the real server kick off the BLE write asynchronously
> and respond immediately, so these tests validate the HTTP contract (status
> codes, JSON shape, state bookkeeping) rather than confirming the physical
> light actually changed — verify that visually or via `xr15_server.py status`.

## Reports

After a run, reports are available at:

- `target/cucumber-reports/cucumber.html`
- `target/cucumber-reports/cucumber.json`
- `target/surefire-reports/`
