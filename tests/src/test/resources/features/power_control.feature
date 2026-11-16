Feature: XR15 bridge - power control
  As the Home Assistant rest_command integration
  I want to turn the Radion XR15w light on and off through the BLE bridge
  So that the aquarium lighting can be automated

  Background:
    Given the XR15 bridge server is running

  Scenario: Turning the light on reports state "on"
    When I send a request to turn the light "on"
    Then the response status code should be 200
    And the reported state should be "on"
    And the subsequent status should be "on"

  Scenario: Turning the light off reports state "off"
    When I send a request to turn the light "off"
    Then the response status code should be 200
    And the reported state should be "off"
    And the subsequent status should be "off"

  Scenario Outline: Repeated toggling keeps status in sync
    When I send a request to turn the light "<action>"
    Then the subsequent status should be "<expected>"

    Examples:
      | action | expected |
      | on     | on       |
      | off    | off      |
      | on     | on       |
      | on     | on       |
      | off    | off      |
