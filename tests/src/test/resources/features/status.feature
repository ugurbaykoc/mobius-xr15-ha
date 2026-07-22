Feature: XR15 bridge - device status
  As the Home Assistant rest_command integration
  I want to query the current reported state of the Radion XR15w bridge
  So that the switch entity reflects reality

  Background:
    Given the XR15 bridge server is running

  Scenario: Status endpoint responds with a valid payload
    When I request the device status
    Then the response status code should be 200
    And the response content type should be "application/json"
    And the response should contain a valid "state" field
