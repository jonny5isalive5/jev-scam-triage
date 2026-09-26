package com.sentovara.scamcheck

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ShouldWarnTest {
    private fun v(verdict: String, jevUsed: Boolean) = Verdict(verdict, emptyList(), "", jevUsed)

    @Test
    fun likelyScamAlwaysWarns() {
        assertTrue(Checker.shouldWarn(v(LIKELY_SCAM, jevUsed = true)))
        assertTrue(Checker.shouldWarn(v(LIKELY_SCAM, jevUsed = false)))  // e.g. a fake brand link, found on the phone
    }

    @Test
    fun beCarefulWarnsOnlyWhenJevJudgedIt() {
        assertTrue(Checker.shouldWarn(v(BE_CAREFUL, jevUsed = true)))
        assertFalse(Checker.shouldWarn(v(BE_CAREFUL, jevUsed = false)))  // "couldn't check" is not a warning
    }

    @Test
    fun looksOrdinaryNeverWarns() {
        assertFalse(Checker.shouldWarn(v(LOOKS_ORDINARY, jevUsed = true)))
    }
}
