package com.sentovara.scamcheck

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * The golden cases on a real Android runtime, using the rules file bundled in the app. Android's
 * regex engine (ICU) is not java.util.regex, so passing on the JVM alone isn't enough.
 */
@RunWith(AndroidJUnit4::class)
class GoldenCasesDeviceTest {
    @Test
    fun everyGoldenCaseMatchesPythonOnDevice() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val text = ctx.assets.open("scam_check_spec.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
        assertTrue(GoldenCases.verifyAll(JSONObject(text)) > 0)
    }
}
