package com.sentovara.scamcheck

import org.json.JSONObject
import java.util.regex.Matcher
import java.util.regex.Pattern

/**
 * The same checker as the Python package `scam_triage`, driven by the shared rules file
 * spec/scam_check_spec.json. The JVM unit tests replay every golden case in that file, so
 * this must produce exactly what scam_triage.engine.decide() produces.
 */

const val LIKELY_SCAM = "likely_scam"
const val BE_CAREFUL = "be_careful"
const val LOOKS_ORDINARY = "looks_ordinary"

data class LinkFacts(val domain: String, val registrable: String, val shortener: Boolean, val lookalikeOf: String?)

/** One Jev answer: `noul` for yes/no questions, `choice` + `probabilities` for the choice question. */
data class Answer(val type: String, val noul: Double = 0.0, val choice: String? = null,
                  val probabilities: Map<String, Double> = emptyMap())

data class Verdict(val verdict: String, val reasons: List<String>, val advice: String, val jevUsed: Boolean,
                   val error: String? = null)

private fun compile(spec: JSONObject): Pattern {
    var flags = Pattern.UNICODE_CHARACTER_CLASS
    if (spec.getBoolean("ignore_case")) flags = flags or Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE
    return Pattern.compile(spec.getString("pattern"), flags)
}

class Spec(val json: JSONObject) {
    val yes: Double = json.getDouble("yes_threshold")
    val questions: JSONObject = json.getJSONObject("questions")
    val api: JSONObject = json.getJSONObject("api")
    val orgWords: Map<String, String> = json.getJSONObject("organisation_words").let { o ->
        o.keys().asSequence().associateWith { o.getString(it) }
    }

    private val links = json.getJSONObject("links")
    val urlRe: Pattern = compile(links.getJSONObject("url_regex"))
    val shorteners: Set<String> = links.getJSONArray("shorteners").let { a -> (0 until a.length()).map { a.getString(it) }.toSet() }
    val twoPartSuffixes: Set<String> = links.getJSONArray("two_part_suffixes").let { a -> (0 until a.length()).map { a.getString(it) }.toSet() }
    // Insertion order matters: the first brand found in a domain wins, as in Python.
    val officialDomains: LinkedHashMap<String, Set<String>> = LinkedHashMap<String, Set<String>>().also { m ->
        val pairs = links.getJSONArray("official_domains")
        for (i in 0 until pairs.length()) {
            val pair = pairs.getJSONArray(i)
            val a = pair.getJSONArray(1)
            m[pair.getString(0)] = (0 until a.length()).map { a.getString(it) }.toSet()
        }
    }

    private val mask = json.getJSONObject("mask")
    val emailRe: Pattern = compile(mask.getJSONObject("email_regex"))
    val phoneRe: Pattern = compile(mask.getJSONObject("phone_regex"))
    val longNumberRe: Pattern = compile(mask.getJSONObject("long_number_regex"))

    val gateRules: LinkedHashMap<String, Pattern> = LinkedHashMap<String, Pattern>().also { m ->
        val pairs = json.getJSONArray("gate_rules")
        for (i in 0 until pairs.length()) {
            val pair = pairs.getJSONArray(i)
            m[pair.getString(0)] = compile(pair.getJSONObject(1))
        }
    }
}

class Engine(private val spec: Spec) {

    // --- links --------------------------------------------------------------------------------

    fun registrableDomain(domain: String): String {
        val labels = domain.lowercase().trim('.').split(".")
        if (labels.size >= 3 && labels.takeLast(2).joinToString(".") in spec.twoPartSuffixes) {
            return labels.takeLast(3).joinToString(".")
        }
        return labels.takeLast(2).joinToString(".")
    }

    private fun domainOf(url: String): String {
        val noScheme = url.replace(Regex("^https?://", RegexOption.IGNORE_CASE), "")
        return noScheme.split("/")[0].split("?")[0].split(":")[0].lowercase().trimEnd('.', ',', ';', ')')
    }

    private val govRe = Regex("(^|[.-])gov([.-]|$)")

    private fun lookalikeBrand(domain: String, registrable: String): String? {
        val squashed = domain.replace(Regex("[^a-z0-9]"), "")
        for ((brand, official) in spec.officialDomains) {
            if (brand in squashed && registrable !in official) return brand
        }
        if (govRe.containsMatchIn(domain) && !(domain.endsWith(".gov.uk") || domain.endsWith(".gov"))) {
            return "government"
        }
        return null
    }

    fun extractLinks(text: String): List<LinkFacts> {
        val facts = mutableListOf<LinkFacts>()
        val m = spec.urlRe.matcher(text)
        while (m.find()) {
            val domain = domainOf(m.group())
            if ('.' !in domain) continue
            val reg = registrableDomain(domain)
            facts += LinkFacts(domain, reg, domain in spec.shorteners || reg in spec.shorteners, lookalikeBrand(domain, reg))
        }
        return facts
    }

    // --- masking ------------------------------------------------------------------------------

    private fun replaceAll(p: Pattern, text: String, replacement: (Matcher) -> String): String {
        val m = p.matcher(text)
        val sb = StringBuffer()  // the StringBuilder overloads need Android 14+; StringBuffer works everywhere
        while (m.find()) m.appendReplacement(sb, Matcher.quoteReplacement(replacement(m)))
        m.appendTail(sb)
        return sb.toString()
    }

    fun maskForJev(text: String): String {
        var t = replaceAll(spec.emailRe, text) { "<EMAIL_ADDRESS>" }
        t = replaceAll(spec.urlRe, t) { m ->
            val url = m.group()
            val trailing = url.substring(url.trimEnd('.', ',', ';', ':', '!', '?', ')').length)
            "<URL>$trailing"
        }
        t = replaceAll(spec.phoneRe, t) { "<PHONE_NUMBER>" }
        t = replaceAll(spec.longNumberRe, t) { "<NUMBER>" }
        return t
    }

    // --- gate ---------------------------------------------------------------------------------

    fun mixedScriptWords(text: String): List<String> {
        val found = mutableListOf<String>()
        val m = Pattern.compile("\\w+", Pattern.UNICODE_CHARACTER_CLASS).matcher(text)
        while (m.find()) {
            val word = m.group()
            val scripts = mutableSetOf<Character.UnicodeScript>()
            var i = 0
            while (i < word.length) {
                val cp = word.codePointAt(i)
                if (Character.isLetter(cp)) scripts += Character.UnicodeScript.of(cp)
                i += Character.charCount(cp)
            }
            if (Character.UnicodeScript.LATIN in scripts &&
                (Character.UnicodeScript.GREEK in scripts || Character.UnicodeScript.CYRILLIC in scripts)) {
                found += word
            }
        }
        return found
    }

    fun gateReasons(text: String, senderKnown: Boolean?): List<String> {
        val reasons = spec.gateRules.filter { (_, p) -> p.matcher(text).find() }.keys.toMutableList()
        if (mixedScriptWords(text).isNotEmpty()) reasons += "look_alike_letters"
        if (senderKnown == false) reasons += "unknown_sender"
        return reasons
    }

    // --- decision -----------------------------------------------------------------------------

    fun advice(verdict: String, org: String?, personal: Boolean = false): String {
        if (verdict == LOOKS_ORDINARY) {
            return "Nothing here looks like a scam, but that isn't a guarantee. If it asks for money or details later, " +
                "check again."
        }
        if (personal && org == null) {
            return "Don't reply to this number or send money. If it claims to be someone you know, call them on the " +
                "number you already have for them."
        }
        val where = if (org != null && org in spec.orgWords) "${spec.orgWords.getValue(org)}'s own app or website"
        else "a number or website you already trust"
        return "Don't tap links or reply. If you think it might be real, check it through $where, not this message."
    }

    /** Port of scam_triage.engine.decide(). `answers` is null when Jev couldn't be reached. */
    fun decide(message: String, senderKnown: Boolean?, answers: Map<String, Answer>?, error: String? = null): Verdict {
        val links = extractLinks(message)
        val lookalikes = links.mapNotNull { it.lookalikeOf }.toSortedSet()
        val shortener = links.any { it.shortener }
        val oddLetters = mixedScriptWords(message)

        val codeReasons = mutableListOf<String>()
        for (l in links) {
            if (l.lookalikeOf != null) {
                codeReasons += "The link goes to ${l.domain}, which uses the name '${l.lookalikeOf}' but isn't its real website."
            }
        }
        if (shortener) codeReasons += "The link is shortened, so you can't see where it really goes."
        if (oddLetters.isNotEmpty()) codeReasons += "Some words use look-alike letters from other alphabets, a trick to slip past filters."
        if (senderKnown == false) codeReasons += "The sender isn't in your contacts."

        if (answers == null) {
            val verdict = if (lookalikes.isNotEmpty() || oddLetters.isNotEmpty()) LIKELY_SCAM else BE_CAREFUL
            return Verdict(verdict, codeReasons + "Couldn't reach the checker, so only the basic checks ran.",
                advice(verdict, null), jevUsed = false, error = error)
        }

        val said = answers.filterValues { it.type == "noul" }.mapValues { it.value.noul >= spec.yes }
        val claim = answers.getValue("claims_to_be")
        val org = claim.choice?.takeIf { it != "none" && (claim.probabilities[it] ?: 0.0) >= spec.yes }

        val jevReasons = mutableListOf<String>()
        if (org != null) jevReasons += "It presents itself as coming from ${spec.orgWords.getValue(org)}."
        if (said["asks_for_sensitive_info"] == true) jevReasons += "It asks for passwords, codes, card or bank details, or personal details."
        if (said["asks_for_action"] == true) jevReasons += "It asks you to tap a link, call, reply, or pay."
        if (said["creates_pressure"] == true) jevReasons += "It rushes you with a deadline or a threat of losing something."
        if (said["offers_money"] == true) jevReasons += "It offers money, a prize, a refund, or easy pay."
        if (said["personal_pretext"] == true) jevReasons += "It starts a personal conversation from someone you may not know."

        val action = said["asks_for_action"] == true
        val pressure = said["creates_pressure"] == true
        val money = said["offers_money"] == true
        val pretext = said["personal_pretext"] == true
        val likely = lookalikes.isNotEmpty() ||
            said["asks_for_sensitive_info"] == true ||
            (action && (pressure || money)) ||
            (oddLetters.isNotEmpty() && action)
        val careful = (action && (org != null || shortener || senderKnown == false)) ||
            pretext || money || pressure || shortener
        val verdict = when {
            likely -> LIKELY_SCAM
            careful -> BE_CAREFUL
            else -> LOOKS_ORDINARY
        }
        val reasons = (codeReasons + jevReasons).ifEmpty { listOf("Nothing in it matches the patterns scams use.") }
        return Verdict(verdict, reasons, advice(verdict, org, personal = pretext), jevUsed = true)
    }

    companion object {
        const val GATE_SKIPPED_REASON = "No links, contact details, requests, or money mentioned."
    }
}
