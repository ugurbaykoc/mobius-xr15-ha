package com.mobius.xr15.tests.hooks;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.mobius.xr15.tests.config.TestConfig;
import com.mobius.xr15.tests.mock.MockXr15Server;
import io.cucumber.java.AfterAll;
import io.cucumber.java.BeforeAll;
import io.restassured.RestAssured;

public class Hooks {

    private static WireMockServer mockServer;

    @BeforeAll
    public static void beforeAll() {
        RestAssured.baseURI = TestConfig.baseUrl();

        if (TestConfig.useMockServer()) {
            mockServer = MockXr15Server.start(TestConfig.mockPort());
        }
    }

    @AfterAll
    public static void afterAll() {
        if (mockServer != null && mockServer.isRunning()) {
            mockServer.stop();
        }
    }
}
