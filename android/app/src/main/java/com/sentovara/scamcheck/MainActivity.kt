package com.sentovara.scamcheck

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var messageBox: EditText
    private lateinit var keyBox: EditText
    private lateinit var verdictCard: LinearLayout
    private lateinit var verdictView: TextView
    private lateinit var detailsView: TextView
    private lateinit var autoSwitch: Switch
    private lateinit var keyStatus: TextView
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        messageBox = findViewById(R.id.message)
        keyBox = findViewById(R.id.api_key)
        verdictCard = findViewById(R.id.verdict_card)
        verdictView = findViewById(R.id.verdict)
        detailsView = findViewById(R.id.details)
        autoSwitch = findViewById(R.id.auto_check)
        keyStatus = findViewById(R.id.key_status)

        findViewById<Button>(R.id.check).setOnClickListener { runCheck(null) }
        findViewById<Button>(R.id.save_key).setOnClickListener { saveKeyTapped() }
        findViewById<Button>(R.id.start_protection).setOnClickListener { startProtection() }
        autoSwitch.setOnCheckedChangeListener { _, on ->
            if (on == isProtected()) return@setOnCheckedChangeListener
            if (on) startProtection()
            else {
                Checker.prefs(this).edit().putBoolean(Checker.KEY_AUTO, false).apply()
                render()
            }
        }
        render()
        handle(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    // --- setup and protection -----------------------------------------------------------------

    private fun isProtected() = Checker.prefs(this).getBoolean(Checker.KEY_AUTO, false) && hasSmsPermission()

    private fun render() {
        val on = isProtected()
        findViewById<TextView>(R.id.status).apply {
            setText(if (on) R.string.status_on else R.string.status_off)
            setTextColor(getColor(if (on) R.color.teal_light else R.color.header_text_soft))
        }
        findViewById<TextView>(R.id.setup_title).setText(if (on) R.string.setup_title_on else R.string.setup_title_off)
        findViewById<TextView>(R.id.setup_body).setText(if (on) R.string.setup_body_on else R.string.setup_body_off)
        findViewById<TextView>(R.id.step1).setText(if (on) R.string.step1_on else R.string.step1)
        val setupOnly = if (on) View.GONE else View.VISIBLE
        findViewById<View>(R.id.step2).visibility = setupOnly
        findViewById<View>(R.id.step2_body).visibility = setupOnly
        findViewById<View>(R.id.start_protection).visibility = setupOnly
        autoSwitch.visibility = if (on) View.VISIBLE else View.GONE
        autoSwitch.isChecked = on
        showKeyStatus()
    }

    /** Stores whatever is in the key box. Returns false if it was empty. */
    private fun storeTypedKey(): Boolean {
        val typed = keyBox.text.toString()
        if (typed.isBlank()) return false
        Checker.saveApiKey(this, typed)
        keyBox.setText("")
        showKeyStatus()
        return true
    }

    /**
     * Saving a key finishes setup: straight on to the permissions if protection isn't on yet, or
     * straight to the "Jev is watching" confirmation (which closes the app) if it already is.
     * Before, it only changed the status line, which on a phone upgraded from an earlier version
     * (protection already on) looked like nothing happened.
     */
    private fun saveKeyTapped() {
        if (!storeTypedKey()) {
            keyStatus.setText(R.string.paste_key_first)
            return
        }
        if (isProtected()) protectionGranted() else startProtection()
    }

    private fun showKeyStatus() {
        val saved = Checker.apiKey(this) != null
        keyStatus.text = if (saved) "Key saved. Jev is used for checks." else "No key saved: only the basic checks run."
        keyBox.setHint(if (saved) R.string.api_key_hint_saved else R.string.api_key_hint)
    }

    private fun startProtection() {
        storeTypedKey()
        val missing = neededPermissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) protectionGranted() else requestPermissions(missing.toTypedArray(), REQUEST_SMS)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQUEST_SMS) return
        if (hasSmsPermission()) protectionGranted()
        else {
            render()
            keyStatus.setText(R.string.permission_needed)
        }
    }

    /**
     * Switches background checking on and says so. When warnings can be shown, the confirmation
     * closes itself and the app with it, since there's nothing left to do: protection runs in
     * the background. If notifications are off, it stays open and explains instead.
     */
    private fun protectionGranted() {
        Checker.prefs(this).edit().putBoolean(Checker.KEY_AUTO, true).apply()
        render()
        if (!canNotify()) {
            AlertDialog.Builder(this)
                .setTitle(R.string.notifications_off_title)
                .setMessage(R.string.notifications_off_body)
                .setPositiveButton(R.string.done_ok, null)
                .show()
            return
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.done_title)
            .setMessage(R.string.done_body)
            .setPositiveButton(R.string.done_ok) { _, _ -> finish() }
            .setOnCancelListener { finish() }
            .show()
        handler.postDelayed({
            if (!isFinishing) {
                dialog.dismiss()
                finish()
            }
        }, AUTO_CLOSE_MS)
    }

    private fun neededPermissions(): List<String> {
        val p = mutableListOf(Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_CONTACTS)
        if (Build.VERSION.SDK_INT >= 33) p += Manifest.permission.POST_NOTIFICATIONS
        return p
    }

    private fun hasSmsPermission() = checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED

    private fun canNotify() = Build.VERSION.SDK_INT < 33 ||
        checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    // --- checking a message ---------------------------------------------------------------------

    private fun handle(intent: Intent?) {
        if (intent == null) return
        val text = when {
            intent.action == Intent.ACTION_SEND -> intent.getStringExtra(Intent.EXTRA_TEXT)
            intent.hasExtra(EXTRA_MESSAGE) -> intent.getStringExtra(EXTRA_MESSAGE)
            else -> null
        } ?: return
        messageBox.setText(text)
        val sender: Boolean? = if (intent.hasExtra(EXTRA_SENDER_KNOWN)) intent.getBooleanExtra(EXTRA_SENDER_KNOWN, true) else null
        runCheck(sender)
    }

    private fun runCheck(senderKnown: Boolean?) {
        val text = messageBox.text.toString()
        if (text.isBlank()) return
        verdictCard.visibility = View.VISIBLE
        verdictCard.background = null
        verdictView.text = "Checking…"
        verdictView.setTextColor(getColor(R.color.text_soft))
        detailsView.text = ""
        Thread {
            val v = Checker.check(applicationContext, text, senderKnown, force = true)
            runOnUiThread { show(v) }
        }.start()
    }

    private fun show(v: Verdict) {
        val (label, colour, soft) = LABELS.getValue(v.verdict)
        verdictCard.background = GradientDrawable().apply {
            cornerRadius = resources.displayMetrics.density * 14
            setColor(getColor(soft))
        }
        verdictView.text = label
        verdictView.setTextColor(getColor(colour))
        detailsView.text = buildString {
            append("Why:\n")
            v.reasons.forEach { append("• ").append(it).append('\n') }
            append("\nWhat to do: ").append(v.advice)
        }
    }

    companion object {
        const val EXTRA_MESSAGE = "com.sentovara.scamcheck.MESSAGE"
        const val EXTRA_SENDER_KNOWN = "com.sentovara.scamcheck.SENDER_KNOWN"
        private const val REQUEST_SMS = 1
        const val AUTO_CLOSE_MS = 4_000L
        val LABELS = mapOf(
            LIKELY_SCAM to Triple("LIKELY SCAM", R.color.scam, R.color.scam_soft),
            BE_CAREFUL to Triple("BE CAREFUL", R.color.careful, R.color.careful_soft),
            LOOKS_ORDINARY to Triple("LOOKS ORDINARY", R.color.ordinary, R.color.ordinary_soft),
        )
    }
}
