Feature: XR15 bridge - error handling
  As the Home Assistant rest_command integration
  I want unsupported routes to fail predictably
  So that misconfiguration is easy to diagnose

  Background:
    Given the XR15 bridge server is running

  Scenario: Requesting an unknown route returns 404
    When I request the unknown endpoint "/bogus"
    Then the response status code should be 404
