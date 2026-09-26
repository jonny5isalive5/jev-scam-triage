package com.sentovara.scamcheck

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject

/** App-wide entry point: loads the shared rules once and runs a full check. Call off the main thread. */
object Checker {
    private const val PREFS = "scamcheck"
    private const val KEY_API = "typesafe_api_key"
    const val KEY_AUTO = "auto_check_enabled"
    const val NO_KEY = "No TypeSafe key saved yet, so only the basic checks ran."

    @Volatile private var cached: Pair<Spec, Engine>? = null

    fun engine(ctx: Context): Pair<Spec, Engine> = cached ?: synchronized(this) {
        cached ?: run {
            val text = ctx.assets.open("scam_check_spec.json").bufferedReader(Charsets.UTF_8).use { it.readText() }
            val spec = Spec(JSONObject(text))
            (spec to Engine(spec)).also { cached = it }
        }
    }

    fun prefs(ctx: Context): SharedPreferences = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun apiKey(ctx: Context): String? = prefs(ctx).getString(KEY_API, null)?.trim()?.takeIf { it.isNotEmpty() }

    fun saveApiKey(ctx: Context, key: String) = prefs(ctx).edit().putString(KEY_API, key.trim()).apply()

    /**
     * Whether a background check should raise a notification. A "be careful" that only means Jev
     * couldn't be reached (no key, offline) would fire for every text from a non-contact, so in the
     * background only a likely scam, or a "be careful" that Jev actually judged, raises a warning.
     */
    fun shouldWarn(v: Verdict): Boolean = v.verdict == LIKELY_SCAM || (v.verdict == BE_CAREFUL && v.jevUsed)

    /**
     * `force = true` for a pasted or shared message (always checked in full).
     * `force = false` for background texts: the gate lets ordinary messages through untouched,
     * so they are never sent anywhere.
     */
    fun check(ctx: Context, message: String, senderKnown: Boolean?, force: Boolean, background: Boolean = false): Verdict {
        val (spec, engine) = engine(ctx)
        val gate = engine.gateReasons(message, senderKnown)
        if (!force && gate.isEmpty()) {
            return Verdict(LOOKS_ORDINARY, listOf(Engine.GATE_SKIPPED_REASON), engine.advice(LOOKS_ORDINARY, null), false)
        }
        val key = apiKey(ctx)
        if (key == null) {
            val v = engine.decide(message, senderKnown, null, NO_KEY)
            return v.copy(reasons = v.reasons.dropLast(1) + NO_KEY)
        }
        return try {
            val answers = JevClient(spec, key).ask(engine.maskForJev(message), attempts = if (background) 1 else 2)
            engine.decide(message, senderKnown, answers)
        } catch (e: JevUnavailable) {
            engine.decide(message, senderKnown, null, e.message)
        }
    }
}
