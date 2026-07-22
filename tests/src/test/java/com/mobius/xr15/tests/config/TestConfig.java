package com.mobius.xr15.tests.config;

/**
 * Central place for reading how the suite should reach the XR15 bridge:
 * a real server (Raspberry Pi running xr15_server.py) or the embedded mock.
 */
public final class TestConfig {

    private static final String DEFAULT_BASE_URL = "http://localhost:8765";
    private static final int MOCK_PORT = 8765;

    private TestConfig() {
    }

    public static String baseUrl() {
        String fromProp = System.getProperty("xr15.baseUrl");
        if (fromProp != null && !fromProp.isBlank()) {
            return fromProp;
        }
        String fromEnv = System.getenv("XR15_BASE_URL");
        if (fromEnv != null && !fromEnv.isBlank()) {
            return fromEnv;
        }
        return DEFAULT_BASE_URL;
    }

    /**
     * Mock is used by default so the suite is runnable without real BLE hardware.
     * It is disabled automatically once a real base URL is supplied, unless
     * xr15.useMock is set explicitly.
     */
    public static boolean useMockServer() {
        String override = System.getProperty("xr15.useMock");
        if (override != null && !override.isBlank()) {
            return Boolean.parseBoolean(override);
        }
        boolean realUrlProvided = isSet(System.getProperty("xr15.baseUrl"))
                || isSet(System.getenv("XR15_BASE_URL"));
        return !realUrlProvided;
    }

    public static int mockPort() {
        return MOCK_PORT;
    }

    private static boolean isSet(String value) {
        return value != null && !value.isBlank();
    }
}
