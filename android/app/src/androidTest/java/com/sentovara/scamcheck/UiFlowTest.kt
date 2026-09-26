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
            assertTrue(details, Checker.NO_KEY in details)
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

    private fun waitUntilClosed(scenario: ActivityScenario<MainActivity>) {
        val deadline = System.currentTimeMillis() + MainActivity.AUTO_CLOSE_MS + 6_000
        while (scenario.state != Lifecycle.State.DESTROYED && System.currentTimeMillis() < deadline) {
            Thread.sleep(250)
        }
        assertEquals(Lifecycle.State.DESTROYED, scenario.state)
    }

    /** Saving a key during setup goes straight on to protection (permissions are pre-granted in CI). */
    @Test
    fun savingAKeyFinishesSetupAndCloses() {
        val scenario = ActivityScenario.launch(MainActivity::class.java)
        var status = ""
        scenario.onActivity {
            it.findViewById<EditText>(R.id.api_key).setText("test-key-not-real")
            it.findViewById<Button>(R.id.save_key).performClick()
            status = it.findViewById<TextView>(R.id.key_status).text.toString()
        }
        assertTrue(status, status.startsWith("Key saved"))
        assertEquals("test-key-not-real", Checker.apiKey(ctx))
        waitUntilClosed(scenario)
        assertTrue(Checker.prefs(ctx).getBoolean(Checker.KEY_AUTO, false))
        scenario.close()
        Checker.prefs(ctx).edit().clear().commit()
    }

    /**
     * The bug from a real phone: protection was already on (from an earlier version), so saving
     * the key only changed the status line and nothing seemed to happen. It must confirm and close.
     */
    @Test
    fun savingAKeyWhenAlreadyProtectedConfirmsAndCloses() {
        Checker.prefs(ctx).edit().putBoolean(Checker.KEY_AUTO, true).commit()
        val scenario = ActivityScenario.launch(MainActivity::class.java)
        scenario.onActivity {
            it.findViewById<EditText>(R.id.api_key).setText("test-key-not-real")
            it.findViewById<Button>(R.id.save_key).performClick()
        }
        waitUntilClosed(scenario)
        assertEquals("test-key-not-real", Checker.apiKey(ctx))
        scenario.close()
        Checker.prefs(ctx).edit().clear().commit()
    }

    /** Tapping Save key with an empty box says so and stays open. */
    @Test
    fun savingAnEmptyKeySaysSo() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            var status = ""
            scenario.onActivity {
                it.findViewById<Button>(R.id.save_key).performClick()
                status = it.findViewById<TextView>(R.id.key_status).text.toString()
            }
            assertEquals(ctx.getString(R.string.paste_key_first), status)
            assertEquals(Lifecycle.State.RESUMED, scenario.state)
        }
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
        waitUntilClosed(scenario)
        assertTrue(Checker.prefs(ctx).getBoolean(Checker.KEY_AUTO, false))
        scenario.close()
        Checker.prefs(ctx).edit().clear().commit()
    }
}
