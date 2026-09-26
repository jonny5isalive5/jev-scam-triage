package com.sentovara.scamcheck

import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** The golden cases on the JVM (java.util.regex). See GoldenCasesDeviceTest for Android's engine. */
class GoldenCasesTest {
    @Test
    fun everyGoldenCaseMatchesPython() {
        val spec = JSONObject(File("../../spec/scam_check_spec.json").readText(Charsets.UTF_8))
        assertTrue(GoldenCases.verifyAll(spec) > 0)
    }
}
