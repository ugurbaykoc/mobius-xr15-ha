package com.mobius.xr15.tests.mock;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.client.WireMock;
import com.github.tomakehurst.wiremock.core.WireMockConfiguration;
import com.github.tomakehurst.wiremock.client.ResponseDefinitionBuilder;
import com.github.tomakehurst.wiremock.stubbing.Scenario;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.stubFor;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;

/**
 * Stand-in for xr15_server.py's HTTP surface (/on, /off, /status), so the
 * feature suite can run in CI without a Raspberry Pi + real BLE light attached.
 * Mirrors the real server's behavior: /on and /off respond immediately and
 * flip the state that a later /status call reports.
 */
public final class MockXr15Server {

    private static final String SCENARIO = "xr15-power-state";
    private static final String STATE_ON = "ON";
    private static final String STATE_OFF = "OFF";

    private MockXr15Server() {
    }

    public static WireMockServer start(int port) {
        WireMockServer server = new WireMockServer(WireMockConfiguration.options().port(port));
        server.start();
        WireMock.configureFor("localhost", port);
        registerStubs();
        return server;
    }

    private static void registerStubs() {
        stubFor(get(urlEqualTo("/status"))
                .inScenario(SCENARIO)
                .whenScenarioStateIs(Scenario.STARTED)
                .willReturn(jsonState("unknown")));

        stubFor(get(urlEqualTo("/status"))
                .inScenario(SCENARIO)
                .whenScenarioStateIs(STATE_ON)
                .willReturn(jsonState("on")));

        stubFor(get(urlEqualTo("/status"))
                .inScenario(SCENARIO)
                .whenScenarioStateIs(STATE_OFF)
                .willReturn(jsonState("off")));

        stubFor(get(urlEqualTo("/on"))
                .inScenario(SCENARIO)
                .willReturn(jsonState("on"))
                .willSetStateTo(STATE_ON));

        stubFor(get(urlEqualTo("/off"))
                .inScenario(SCENARIO)
                .willReturn(jsonState("off"))
                .willSetStateTo(STATE_OFF));
    }

    private static ResponseDefinitionBuilder jsonState(String state) {
        return aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json; charset=utf-8")
                .withBody("{\"state\": \"" + state + "\"}");
    }
}
