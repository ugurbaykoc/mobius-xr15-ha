package com.mobius.xr15.tests.steps;

import com.mobius.xr15.tests.config.TestConfig;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;

import static io.restassured.RestAssured.given;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.notNullValue;

public class XR15Steps {

    private Response response;

    @Given("the XR15 bridge server is running")
    public void the_bridge_server_is_running() {
        response = get("/status");
        assertThat("XR15 bridge server is not reachable at " + TestConfig.baseUrl(),
                response.statusCode(), is(200));
    }

    @When("I request the device status")
    public void i_request_the_device_status() {
        response = get("/status");
    }

    @When("I send a request to turn the light {string}")
    public void i_send_a_request_to_turn_the_light(String action) {
        response = get("/" + action);
    }

    @When("I request the unknown endpoint {string}")
    public void i_request_the_unknown_endpoint(String path) {
        response = get(path);
    }

    @Then("the response status code should be {int}")
    public void the_response_status_code_should_be(int expectedCode) {
        assertThat(response.statusCode(), is(expectedCode));
    }

    @Then("the response should contain a valid {string} field")
    public void the_response_should_contain_a_valid_field(String field) {
        assertThat(response.jsonPath().getString(field), notNullValue());
    }

    @Then("the response content type should be {string}")
    public void the_response_content_type_should_be(String contentType) {
        assertThat(response.contentType(), containsString(contentType));
    }

    @Then("the reported state should be {string}")
    public void the_reported_state_should_be(String expectedState) {
        assertThat(response.jsonPath().getString("state"), equalTo(expectedState));
    }

    @Then("the subsequent status should be {string}")
    public void the_subsequent_status_should_be(String expectedState) {
        Response status = get("/status");
        assertThat(status.jsonPath().getString("state"), equalTo(expectedState));
    }

    private static Response get(String path) {
        return given().baseUri(TestConfig.baseUrl()).when().get(path);
    }
}
