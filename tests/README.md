# REST Assured + Cucumber Framework

An empty starter project for API test automation using REST Assured and
Cucumber (BDD). It contains no test cases — add your own `.feature` files
and step definitions as you need them.

## Stack

- Java 17
- Maven
- Cucumber 7 (JUnit 5 Platform Engine)
- REST Assured

## Project layout

```
tests/
├── pom.xml
└── src/test/
    ├── java/com/framework/
    │   ├── runner/TestRunner.java     # entry point Maven/Surefire runs
    │   ├── hooks/Hooks.java           # global setup (e.g. RestAssured.baseURI)
    │   ├── utils/ConfigReader.java    # reads config.properties / -D overrides
    │   └── stepdefinitions/           # put your step definition classes here
    └── resources/
        ├── config.properties          # base.uri and any other settings
        └── features/                  # put your .feature files here
```

## Adding a test

1. Drop a `.feature` file into `src/test/resources/features/`.
2. Add a step definition class under `src/test/java/com/framework/stepdefinitions/`.
3. Run `mvn test`.

A minimal example to get started:

```gherkin
# src/test/resources/features/example.feature
Feature: Example API check

  Scenario: Get a resource
    When I send a GET request to "/some/endpoint"
    Then the response status code should be 200
```

```java
// src/test/java/com/framework/stepdefinitions/ExampleSteps.java
package com.framework.stepdefinitions;

import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.response.Response;

import static io.restassured.RestAssured.given;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.is;

public class ExampleSteps {

    private Response response;

    @When("I send a GET request to {string}")
    public void i_send_a_get_request_to(String path) {
        response = given().when().get(path);
    }

    @Then("the response status code should be {int}")
    public void the_response_status_code_should_be(int expectedCode) {
        assertThat(response.statusCode(), is(expectedCode));
    }
}
```

## Running

```bash
cd tests
mvn test                                        # uses base.uri from config.properties
mvn test -Dbase.uri=https://api.example.com     # override the target API
```

## Reports

After a run, reports are available at:

- `target/cucumber-reports/cucumber.html`
- `target/cucumber-reports/cucumber.json`
- `target/surefire-reports/`
