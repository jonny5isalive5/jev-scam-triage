package com.sentovara.scamcheck

import android.content.Intent
import android.graphics.Bitmap
import android.util.Base64
import android.util.Log
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayOutputStream

/**
 * Not a check: writes small screenshots of the main screens to logcat (tag SCREENSHOT, base64 JPEG
 * in chunks) so the UI can be looked at from the CI log. ci/emulator-smoke.sh prints them.
 */
@RunWith(AndroidJUnit4::class)
class ScreenshotDump {
    private val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()

    private fun dump(name: String) {
        Thread.sleep(1500)
        val shot = InstrumentationRegistry.getInstrumentation().uiAutomation.takeScreenshot() ?: return
        val w = 360
        val small = Bitmap.createScaledBitmap(shot, w, shot.height * w / shot.width, true)
        val out = ByteArrayOutputStream()
        small.compress(Bitmap.CompressFormat.JPEG, 60, out)
        val b64 = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
        b64.chunked(800).forEachIndexed { i, part -> Log.i("SCREENSHOT", "$name $i $part") }
        Log.i("SCREENSHOT", "$name END")
    }

    @Test
    fun dumpScreens() {
        Checker.prefs(ctx).edit().clear().commit()
        ActivityScenario.launch(MainActivity::class.java).use { dump("setup") }

        val intent = Intent(Intent.ACTION_SEND).setClass(ctx, MainActivity::class.java).setType("text/plain")
            .putExtra(Intent.EXTRA_TEXT, "Royal Mail: your parcel is on hold. Pay the 1.45 fee: https://rm-redelivery-royalmail.info/pay")
        ActivityScenario.launch<MainActivity>(intent).use { scenario ->
            Thread.sleep(2000)
            scenario.onActivity { activity ->
                val root = activity.findViewById<android.view.ViewGroup>(android.R.id.content).getChildAt(0)
                (root as android.widget.ScrollView).fullScroll(android.view.View.FOCUS_DOWN)
            }
            dump("result")
        }

        Checker.prefs(ctx).edit().putBoolean(Checker.KEY_AUTO, true).commit()
        ActivityScenario.launch(MainActivity::class.java).use { dump("protected") }
        Checker.prefs(ctx).edit().clear().commit()
    }
}
