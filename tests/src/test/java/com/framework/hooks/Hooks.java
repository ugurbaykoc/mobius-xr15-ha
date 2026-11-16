package com.framework.hooks;

import com.framework.utils.ConfigReader;
import io.cucumber.java.BeforeAll;
import io.restassured.RestAssured;

public class Hooks {

    @BeforeAll
    public static void beforeAll() {
        RestAssured.baseURI = ConfigReader.get("base.uri");
    }
}
