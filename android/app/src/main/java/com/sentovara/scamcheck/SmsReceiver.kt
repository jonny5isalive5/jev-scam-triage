package com.sentovara.scamcheck

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.ContactsContract
import android.provider.Telephony

/**
 * Checks each incoming text in the background when "Check incoming texts" is on. Ordinary
 * messages stop at the on-phone gate and are never sent anywhere. Risky ones raise a warning
 * notification. Nothing is deleted or blocked: the text still arrives in your messages app.
 */
class SmsReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        if (!Checker.prefs(context).getBoolean(Checker.KEY_AUTO, false)) return

        val bySender = linkedMapOf<String, StringBuilder>()
        for (sms in Telephony.Sms.Intents.getMessagesFromIntent(intent) ?: return) {
            val from = sms.originatingAddress ?: "unknown"
            bySender.getOrPut(from) { StringBuilder() }.append(sms.messageBody ?: "")
        }

        val pending = goAsync()
        val app = context.applicationContext
        Thread {
            try {
                for ((sender, body) in bySender) {
                    val known = senderInContacts(app, sender)
                    val v = Checker.check(app, body.toString(), known, force = false, background = true)
                    if (Checker.shouldWarn(v)) warn(app, sender, body.toString(), known, v)
                }
            } finally {
                pending.finish()
            }
        }.start()
    }

    /** null when contacts permission wasn't given (then "unknown sender" is simply not used). */
    private fun senderInContacts(ctx: Context, number: String): Boolean? {
        if (ctx.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) return null
        val uri = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode(number))
        return ctx.contentResolver.query(uri, arrayOf(ContactsContract.PhoneLookup._ID), null, null, null)
            ?.use { it.moveToFirst() } ?: false
    }

    private fun warn(ctx: Context, sender: String, body: String, known: Boolean?, v: Verdict) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL, ctx.getString(R.string.channel_name), NotificationManager.IMPORTANCE_HIGH))

        val open = Intent(ctx, MainActivity::class.java)
            .putExtra(MainActivity.EXTRA_MESSAGE, body)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        if (known != null) open.putExtra(MainActivity.EXTRA_SENDER_KNOWN, known)
        val id = (sender + body).hashCode()
        val tap = PendingIntent.getActivity(ctx, id, open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

        val title = (if (v.verdict == LIKELY_SCAM) "Likely scam" else "Be careful") + " – text from $sender"
        val n = Notification.Builder(ctx, CHANNEL)
            .setSmallIcon(R.drawable.ic_shield)
            .setContentTitle(title)
            .setContentText(v.reasons.firstOrNull() ?: v.advice)
            .setStyle(Notification.BigTextStyle().bigText(v.reasons.joinToString("\n") { "• $it" } + "\n\n" + v.advice))
            .setContentIntent(tap)
            .setAutoCancel(true)
            .build()
        nm.notify(id, n)
    }

    companion object {
        private const val CHANNEL = "scam_warnings"
    }
}
