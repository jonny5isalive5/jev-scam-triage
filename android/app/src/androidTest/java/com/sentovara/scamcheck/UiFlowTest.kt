package com.sentovara.scamcheck

import android.content.Intent
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Drives the real app on an emulator. No API key is saved, so only the on-phone checks run and
 * the outcomes are deterministic; the Jev path is covered by the Python evaluation.
 */
@RunWith(AndroidJUnit4::class)
class UiFlowTest {
    private val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()

    @Before
    fun clearSettings() {
        Checker.prefs(ctx).edit().clear().commit()
    }

    private fun waitForVerdict(scenario: ActivityScenario<MainActivity>, expected: String): String {
        val deadline = System.currentTimeMillis() + 15_000
        var seen = ""
        while (System.currentTimeMillis() < deadline) {
            scenario.onActivity { seen = it.findViewById<TextView>(R.id.verdict).text.toString() }
            if (seen == expected) break
            Thread.sleep(200)
        }
        assertEquals(expected, seen)
        var details = ""
        scenario.onActivity { details = it.findViewById<TextView>(R.id.details).text.toString() }
        return details
    }

    @Test
    fun sharingAScamIntoTheAppShowsLikelyScam() {
        val intent = Intent(Intent.ACTION_SEND).setClass(ctx, MainActivity::class.java).setType("text/plain")
            .putExtra(Intent.EXTRA_TEXT, "Royal Mail: pay the £1.45 fee at https://rm-redelivery-royalmail.info/pay")
        ActivityScenario.launch<MainActivity>(intent).use { scenario ->
            val details = waitForVerdict(scenario, "LIKELY SCAM")
            assertTrue(details, "rm-redelivery-royalmail.info" in details)
            assertTrue(details, "No TypeSafe API key saved" in details)
        }
    }

    @Test
    fun pastingAndTappingCheckWorks() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity {
                it.findViewById<EditText>(R.id.message).setText("Win a prize: bit.ly/3xYz")
                it.findViewById<Button>(R.id.check).performClick()
            }
            val details = waitForVerdict(scenario, "BE CAREFUL")
            assertTrue(details, "shortened" in details)
        }
    }

    @Test
    fun savingAKeyUpdatesTheStatusLine() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            var status = ""
            scenario.onActivity {
                it.findViewById<EditText>(R.id.api_key).setText("test-key-not-real")
                it.findViewById<Button>(R.id.save_key).performClick()
                status = it.findViewById<TextView>(R.id.key_status).text.toString()
            }
            assertTrue(status, status.startsWith("Key saved"))
            assertEquals("test-key-not-real", Checker.apiKey(ctx))
        }
        Checker.prefs(ctx).edit().clear().commit()
    }

    /**
     * Setup's last step: with the permissions already granted (ci/emulator-smoke.sh grants them),
     * tapping Start protection switches background checking on, shows the confirmation, and the
     * app closes by itself.
     */
    @Test
    fun startingProtectionConfirmsAndClosesTheApp() {
        val scenario = ActivityScenario.launch(MainActivity::class.java)
        scenario.onActivity { it.findViewById<Button>(R.id.start_protection).performClick() }
        val deadline = System.currentTimeMillis() + MainActivity.AUTO_CLOSE_MS + 6_000
        while (scenario.state != Lifecycle.State.DESTROYED && System.currentTimeMillis() < deadline) {
            Thread.sleep(250)
        }
        assertEquals(Lifecycle.State.DESTROYED, scenario.state)
        assertTrue(Checker.prefs(ctx).getBoolean(Checker.KEY_AUTO, false))
        scenario.close()
        Checker.prefs(ctx).edit().clear().commit()
    }
}
