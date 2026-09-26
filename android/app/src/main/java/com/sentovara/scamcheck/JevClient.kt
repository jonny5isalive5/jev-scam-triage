package com.sentovara.scamcheck

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL

class JevUnavailable(message: String) : Exception(message)

/**
 * Calls Jev's System One endpoint directly from the phone, the same request typesafe-sdk makes:
 * POST {base}/v1/systemone with a Bearer key, {"state", "model", "questions"} as JSON.
 * Only the masked message is sent. One retry on a timeout, rate limit, or server error.
 */
class JevClient(private val spec: Spec, private val apiKey: String) {

    /** `attempts` = 1 in the background, where Android allows only about 10 seconds of work. */
    fun ask(maskedMessage: String, attempts: Int = 2): Map<String, Answer> {
        var last: Exception? = null
        repeat(attempts) { attempt ->
            try {
                return askOnce(maskedMessage)
            } catch (e: RetryableError) {
                last = e
                if (attempt < attempts - 1) Thread.sleep(500)
            }
        }
        throw JevUnavailable(last?.message ?: "Jev could not be reached")
    }

    private class RetryableError(message: String) : Exception(message)

    private fun askOnce(maskedMessage: String): Map<String, Answer> {
        val api = spec.api
        val timeoutMs = (api.getDouble("request_timeout_s") * 1000).toInt()
        val body = JSONObject()
            .put("state", JSONObject().put("message", maskedMessage))
            .put("model", api.getString("model"))
            .put("questions", spec.questions)
        val conn = URL(api.getString("base_url") + api.getString("path")).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.connectTimeout = timeoutMs
            conn.readTimeout = timeoutMs
            conn.doOutput = true
            conn.setRequestProperty("Authorization", "Bearer $apiKey")
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Accept", "application/json")
            conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val status = conn.responseCode
            if (status == 429 || status >= 500) throw RetryableError("Jev returned HTTP $status")
            if (status != 200) throw JevUnavailable("Jev returned HTTP $status (check the API key in Settings)")
            val text = conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            val answersJson = JSONObject(text).getJSONObject("answers")
            val answers = answersJson.keys().asSequence().associateWith { parseAnswer(answersJson.getJSONObject(it)) }
            val missing = spec.questions.keys().asSequence().filter { it !in answers }.toList()
            if (missing.isNotEmpty()) throw JevUnavailable("Jev's response had no answer for $missing")
            return answers
        } catch (e: SocketTimeoutException) {
            throw RetryableError("Jev timed out")
        } catch (e: IOException) {
            throw RetryableError("Couldn't connect to Jev: ${e.message}")
        } finally {
            conn.disconnect()
        }
    }

    companion object {
        fun parseAnswer(o: JSONObject): Answer = when (o.getString("type")) {
            "noul" -> Answer("noul", noul = o.getDouble("noul"))
            "choice" -> {
                val p = o.getJSONObject("probabilities")
                Answer("choice", choice = o.getString("choice"),
                    probabilities = p.keys().asSequence().associateWith { p.getDouble(it) })
            }
            else -> Answer(o.getString("type"))
        }
    }
}
