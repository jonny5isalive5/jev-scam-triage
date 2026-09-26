package com.sentovara.scamcheck

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var messageBox: EditText
    private lateinit var verdictView: TextView
    private lateinit var detailsView: TextView
    private lateinit var autoSwitch: Switch
    private lateinit var keyStatus: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        messageBox = findViewById(R.id.message)
        verdictView = findViewById(R.id.verdict)
        detailsView = findViewById(R.id.details)
        autoSwitch = findViewById(R.id.auto_check)
        keyStatus = findViewById(R.id.key_status)

        findViewById<Button>(R.id.check).setOnClickListener { runCheck(null) }
        val keyBox = findViewById<EditText>(R.id.api_key)
        findViewById<Button>(R.id.save_key).setOnClickListener {
            Checker.saveApiKey(this, keyBox.text.toString())
            keyBox.setText("")
            showKeyStatus()
        }
        showKeyStatus()

        autoSwitch.isChecked = Checker.prefs(this).getBoolean(Checker.KEY_AUTO, false) && hasSmsPermission()
        autoSwitch.setOnCheckedChangeListener { _, on ->
            if (on && !hasSmsPermission()) requestPermissions(neededPermissions(), REQUEST_SMS)
            else Checker.prefs(this).edit().putBoolean(Checker.KEY_AUTO, on).apply()
        }
        handle(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

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
        verdictView.text = "Checking…"
        verdictView.setTextColor(Color.DKGRAY)
        detailsView.text = ""
        Thread {
            val v = Checker.check(applicationContext, text, senderKnown, force = true)
            runOnUiThread { show(v) }
        }.start()
    }

    private fun show(v: Verdict) {
        val (label, colour) = LABELS.getValue(v.verdict)
        verdictView.text = label
        verdictView.setTextColor(colour)
        detailsView.text = buildString {
            append("Why:\n")
            v.reasons.forEach { append("• ").append(it).append('\n') }
            append("\nWhat to do: ").append(v.advice)
        }
    }

    private fun showKeyStatus() {
        keyStatus.text = if (Checker.apiKey(this) != null) "Key saved. Jev is used for checks."
        else "No key saved: only the basic checks run."
    }

    private fun neededPermissions(): Array<String> {
        val p = mutableListOf(Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_CONTACTS)
        if (Build.VERSION.SDK_INT >= 33) p += Manifest.permission.POST_NOTIFICATIONS
        return p.toTypedArray()
    }

    private fun hasSmsPermission() = checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_SMS) {
            val granted = hasSmsPermission()
            Checker.prefs(this).edit().putBoolean(Checker.KEY_AUTO, granted).apply()
            autoSwitch.isChecked = granted
        }
    }

    companion object {
        const val EXTRA_MESSAGE = "com.sentovara.scamcheck.MESSAGE"
        const val EXTRA_SENDER_KNOWN = "com.sentovara.scamcheck.SENDER_KNOWN"
        private const val REQUEST_SMS = 1
        val LABELS = mapOf(
            LIKELY_SCAM to ("LIKELY SCAM" to Color.parseColor("#B3261E")),
            BE_CAREFUL to ("BE CAREFUL" to Color.parseColor("#8A5A00")),
            LOOKS_ORDINARY to ("LOOKS ORDINARY" to Color.parseColor("#1E6B3A")),
        )
    }
}
