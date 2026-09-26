package com.sentovara.scamcheck

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Not a test on its own: ci/emulator-smoke.sh runs this to switch on "Check incoming texts"
 * (with no key, so the verdict comes from the on-phone checks), then sends real SMS messages to the
 * emulator and checks which ones raise a warning notification.
 */
@RunWith(AndroidJUnit4::class)
class SmsSetup {
    @Test
    fun switchOnIncomingTextChecks() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        assertTrue(Checker.prefs(ctx).edit().clear().putBoolean(Checker.KEY_AUTO, true).commit())
    }
}
