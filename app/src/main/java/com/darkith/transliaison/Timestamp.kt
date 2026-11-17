package com.darkith.transliaison

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

object Timestamp {
    private val iso: SimpleDateFormat =
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }

    @Synchronized
    fun now(): String = iso.format(Date())

    fun stamp(msg: String): String = "[${now()}] $msg"
    fun err(msg: String): String = "ERROR: [${now()}] $msg"
    fun okk(msg: String): String = "OK: [${now()}] $msg"
}
