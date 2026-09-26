package com.sentovara.scamcheck

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals

/**
 * Replays every golden case in spec/scam_check_spec.json (written by the Python package) through
 * the Kotlin engine. Shared by the JVM unit test and the on-device test: the regex engine differs
 * between the two (Java vs Android's ICU), so both must agree with Python.
 */
object GoldenCases {
    private fun strings(a: JSONArray) = (0 until a.length()).map { a.getString(it) }

    private fun answers(o: JSONObject?): Map<String, Answer>? = o?.let {
        it.keys().asSequence().associateWith { name -> JevClient.parseAnswer(it.getJSONObject(name)) }
    }

    /** Returns the number of golden cases checked. */
    fun verifyAll(specJson: JSONObject): Int {
        val engine = Engine(Spec(specJson))
        val golden = specJson.getJSONArray("golden")
        for (i in 0 until golden.length()) {
            val case = golden.getJSONObject(i)
            val msg = case.getString("message")
            val sender: Boolean? = if (case.isNull("sender_known")) null else case.getBoolean("sender_known")
            val exp = case.getJSONObject("expected")
            val label = "golden case $i: $msg"

            assertEquals("$label (masked)", exp.getString("masked"), engine.maskForJev(msg))
            assertEquals("$label (gate)", strings(exp.getJSONArray("gate")), engine.gateReasons(msg, sender))

            val expLinks = exp.getJSONArray("links")
            val links = engine.extractLinks(msg)
            assertEquals("$label (link count)", expLinks.length(), links.size)
            for (j in links.indices) {
                val e = expLinks.getJSONObject(j)
                assertEquals("$label (link $j)",
                    LinkFacts(e.getString("domain"), e.getString("registrable"), e.getBoolean("shortener"),
                        if (e.isNull("lookalike_of")) null else e.getString("lookalike_of")),
                    links[j])
            }

            val error = if (case.isNull("error")) null else case.getString("error")
            val v = engine.decide(msg, sender, answers(case.optJSONObject("answers")), error)
            assertEquals("$label (verdict)", exp.getString("verdict"), v.verdict)
            assertEquals("$label (reasons)", strings(exp.getJSONArray("reasons")), v.reasons)
            assertEquals("$label (advice)", exp.getString("advice"), v.advice)
        }
        return golden.length()
    }
}
