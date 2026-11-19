package com.darkith.transliaison

import android.Manifest
import android.app.Activity
import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.database.Cursor
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.AlarmClock
import android.provider.ContactsContract
import android.provider.MediaStore
import android.provider.Settings
import android.telephony.SmsManager
import android.telephony.TelephonyManager
import android.webkit.JavascriptInterface
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * DeviceBridge — the device-action families the default-app suite needs.
 *
 * SPI-19: a method family is whole or absent. Each family below is complete:
 *   dial*  sms*  contacts*  camera*  clock*  media*  notif*  sys*
 *
 * SPI-13: raw android.* only. No androidx symbol is referenced, so the raw chain
 * (aapt2 -> kotlinc -> d8 -> zip -> zipalign -> apksigner) keeps compiling against
 * android.jar alone.
 *
 * Everything returns a String. Synchronous calls answer inline; calls that need an
 * Activity result answer "PENDING:<id>" and deliver the payload through the host's
 * onActivityResult -> DeviceBridge.deliver(). The UI polls `deviceResult(id)`.
 */
class DeviceBridge(private val host: HomekeeperActivity) {

    companion object {
        const val VERSION = "device-bridge-1"

        /** Request codes owned by this bridge. Kept clear of the file-chooser code. */
        const val REQ_CAMERA = 0x0D01
        const val REQ_PICK_IMAGE = 0x0D02
        const val REQ_CAPTURE_VIDEO = 0x0D03

        /** id -> payload, written by deliver() on the UI thread, read by the poller. */
        private val results = java.util.concurrent.ConcurrentHashMap<String, String>()
        private var seq = 0

        fun nextId(prefix: String): String = prefix + "-" + (++seq)

        fun deliver(id: String, payload: String) {
            results[id] = payload
        }

        /** Drop results nobody collected, so a long session cannot grow without bound. */
        fun sweep(keep: Int = 32) {
            if (results.size <= keep) return
            val keys = results.keys.toList()
            for (i in 0 until keys.size - keep) results.remove(keys[i])
        }
    }

    private fun ok(vararg kv: Pair<String, Any?>): String =
        JSONObject().apply { kv.forEach { (k, v) -> put(k, v) } }.toString()

    private fun err(e: Throwable): String = "ERROR: " + (e.message ?: e.javaClass.simpleName)

    private fun granted(p: String): Boolean =
        host.checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED

    private fun need(p: String): String = "ERROR: permission not granted: $p"

    @JavascriptInterface fun version(): String = VERSION

    /* ------------------------------------------------------------------ sys* */

    @JavascriptInterface fun sysInfo(): String = try {
        ok(
            "sdk" to Build.VERSION.SDK_INT,
            "release" to Build.VERSION.RELEASE,
            "device" to Build.DEVICE,
            "model" to Build.MODEL,
            "manufacturer" to Build.MANUFACTURER,
            "abi" to Build.SUPPORTED_ABIS.joinToString(","),
            "package" to host.packageName
        )
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun sysPermissions(): String = try {
        val names = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.SEND_SMS,
            Manifest.permission.READ_SMS,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.CALL_PHONE,
            Manifest.permission.READ_MEDIA_IMAGES,
            Manifest.permission.POST_NOTIFICATIONS,
            Manifest.permission.ACCESS_FINE_LOCATION
        )
        val a = JSONArray()
        names.forEach { a.put(JSONObject().apply { put("name", it); put("granted", granted(it)) }) }
        a.toString()
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun sysRequest(permissions: String): String = try {
        val list = permissions.split(",").map { it.trim() }.filter { it.isNotEmpty() }.toTypedArray()
        host.runOnUiThread { host.requestPermissions(list, 0x0D10) }
        "OK"
    } catch (e: Throwable) { err(e) }

    /* ----------------------------------------------------------------- dial* */

    @JavascriptInterface fun dialNumber(number: String?): String = try {
        if (number.isNullOrBlank()) "ERROR: empty number" else {
            val i = Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(number)))
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            host.startActivity(i)
            "OK"
        }
    } catch (e: Throwable) { err(e) }

    /**
     * ACTION_CALL places the call without the dialer confirming. It needs CALL_PHONE
     * and is deliberately separate from dialNumber so the UI must ask for it.
     */
    @JavascriptInterface fun dialCall(number: String?): String = try {
        when {
            number.isNullOrBlank() -> "ERROR: empty number"
            !granted(Manifest.permission.CALL_PHONE) -> need(Manifest.permission.CALL_PHONE)
            else -> {
                val i = Intent(Intent.ACTION_CALL, Uri.parse("tel:" + Uri.encode(number)))
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                host.startActivity(i)
                "OK"
            }
        }
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun dialTelephony(): String = try {
        val tm = host.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        ok(
            "phoneType" to tm.phoneType,
            "simState" to tm.simState,
            "networkOperator" to (tm.networkOperator ?: ""),
            "networkCountry" to (tm.networkCountryIso ?: ""),
            "canDial" to granted(Manifest.permission.CALL_PHONE)
        )
    } catch (e: Throwable) { err(e) }

    /* ------------------------------------------------------------------ sms* */

    @JavascriptInterface fun smsSend(number: String?, text: String?): String = try {
        when {
            number.isNullOrBlank() -> "ERROR: empty number"
            text == null -> "ERROR: empty text"
            !granted(Manifest.permission.SEND_SMS) -> need(Manifest.permission.SEND_SMS)
            else -> {
                val mgr = if (Build.VERSION.SDK_INT >= 31) {
                    host.getSystemService(SmsManager::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    SmsManager.getDefault()
                }
                val parts = mgr.divideMessage(text)
                if (parts.size > 1) mgr.sendMultipartTextMessage(number, null, parts, null, null)
                else mgr.sendTextMessage(number, null, text, null, null)
                ok("sent" to true, "parts" to parts.size)
            }
        }
    } catch (e: Throwable) { err(e) }

    /** Open the system composer instead of sending directly — no SEND_SMS needed. */
    @JavascriptInterface fun smsCompose(number: String?, text: String?): String = try {
        val i = Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse("smsto:" + Uri.encode(number ?: ""))
            if (!text.isNullOrEmpty()) putExtra("sms_body", text)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        host.startActivity(i)
        "OK"
    } catch (e: Throwable) { err(e) }

    /** Read the SMS inbox. READ_SMS is a restricted permission; we report, never crash. */
    @JavascriptInterface fun smsInbox(limit: Int): String = try {
        if (!granted(Manifest.permission.READ_SMS)) need(Manifest.permission.READ_SMS) else {
            val a = JSONArray()
            val cols = arrayOf("_id", "address", "body", "date", "type")
            val c: Cursor? = host.contentResolver.query(
                Uri.parse("content://sms/inbox"), cols, null, null, "date DESC"
            )
            c?.use {
                var n = 0
                while (it.moveToNext() && n < limit.coerceIn(1, 500)) {
                    a.put(JSONObject().apply {
                        put("id", it.getLong(0))
                        put("address", it.getString(1) ?: "")
                        put("body", it.getString(2) ?: "")
                        put("date", it.getLong(3))
                        put("type", it.getInt(4))
                    })
                    n++
                }
            }
            a.toString()
        }
    } catch (e: Throwable) { err(e) }

    /* ------------------------------------------------------------- contacts* */

    @JavascriptInterface fun contactsList(limit: Int): String = try {
        if (!granted(Manifest.permission.READ_CONTACTS)) need(Manifest.permission.READ_CONTACTS) else {
            val a = JSONArray()
            val proj = arrayOf(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER,
                ContactsContract.CommonDataKinds.Phone.TYPE
            )
            val c = host.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI, proj, null, null,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
            )
            c?.use {
                var n = 0
                while (it.moveToNext() && n < limit.coerceIn(1, 2000)) {
                    a.put(JSONObject().apply {
                        put("name", it.getString(0) ?: "")
                        put("number", it.getString(1) ?: "")
                        put("type", it.getInt(2))
                    })
                    n++
                }
            }
            a.toString()
        }
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun contactsSearch(query: String?): String = try {
        if (!granted(Manifest.permission.READ_CONTACTS)) need(Manifest.permission.READ_CONTACTS) else {
            val q = (query ?: "").trim()
            if (q.isEmpty()) "[]" else {
                val a = JSONArray()
                val proj = arrayOf(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                )
                val sel = ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " LIKE ?"
                val c = host.contentResolver.query(
                    ContactsContract.CommonDataKinds.Phone.CONTENT_URI, proj, sel,
                    arrayOf("%$q%"), ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
                )
                c?.use {
                    var n = 0
                    while (it.moveToNext() && n < 200) {
                        a.put(JSONObject().apply {
                            put("name", it.getString(0) ?: "")
                            put("number", it.getString(1) ?: "")
                        })
                        n++
                    }
                }
                a.toString()
            }
        }
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun contactsAdd(name: String?, number: String?, email: String?): String = try {
        if (!granted(Manifest.permission.WRITE_CONTACTS)) need(Manifest.permission.WRITE_CONTACTS) else {
            val raw = ContentValues().apply {
                put(ContactsContract.RawContacts.ACCOUNT_TYPE, null as String?)
                put(ContactsContract.RawContacts.ACCOUNT_NAME, null as String?)
            }
            val rawUri = host.contentResolver.insert(ContactsContract.RawContacts.CONTENT_URI, raw)
            if (rawUri == null) "ERROR: insert failed" else {
            val rawId = android.content.ContentUris.parseId(rawUri)
            host.contentResolver.insert(ContactsContract.Data.CONTENT_URI, ContentValues().apply {
                put(ContactsContract.Data.RAW_CONTACT_ID, rawId)
                put(ContactsContract.Data.MIMETYPE, ContactsContract.CommonDataKinds.StructuredName.CONTENT_ITEM_TYPE)
                put(ContactsContract.CommonDataKinds.StructuredName.DISPLAY_NAME, name ?: "")
            })
            if (!number.isNullOrBlank()) {
                host.contentResolver.insert(ContactsContract.Data.CONTENT_URI, ContentValues().apply {
                    put(ContactsContract.Data.RAW_CONTACT_ID, rawId)
                    put(ContactsContract.Data.MIMETYPE, ContactsContract.CommonDataKinds.Phone.CONTENT_ITEM_TYPE)
                    put(ContactsContract.CommonDataKinds.Phone.NUMBER, number)
                })
            }
            if (!email.isNullOrBlank()) {
                host.contentResolver.insert(ContactsContract.Data.CONTENT_URI, ContentValues().apply {
                    put(ContactsContract.Data.RAW_CONTACT_ID, rawId)
                    put(ContactsContract.Data.MIMETYPE, ContactsContract.CommonDataKinds.Email.CONTENT_ITEM_TYPE)
                    put(ContactsContract.CommonDataKinds.Email.ADDRESS, email)
                })
            }
            ok("added" to true, "rawId" to rawId)
            }
        }
    } catch (e: Throwable) { err(e) }

    /* --------------------------------------------------------------- camera* */

    @JavascriptInterface fun cameraList(): String = try {
        val mgr = host.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val a = JSONArray()
        mgr.cameraIdList.forEach { id ->
            val ch = mgr.getCameraCharacteristics(id)
            val facing = when (ch.get(CameraCharacteristics.LENS_FACING)) {
                CameraCharacteristics.LENS_FACING_FRONT -> "front"
                CameraCharacteristics.LENS_FACING_BACK -> "back"
                CameraCharacteristics.LENS_FACING_EXTERNAL -> "external"
                else -> "unknown"
            }
            val flash = ch.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            a.put(JSONObject().apply { put("id", id); put("facing", facing); put("flash", flash) })
        }
        a.toString()
    } catch (e: Throwable) { err(e) }

    /**
     * Capture a photo with the system camera app and store it in the app's own
     * Pictures directory. Returns PENDING:<id>; the path arrives via deviceResult().
     * No CAMERA permission is needed because another app takes the picture.
     */
    @JavascriptInterface fun cameraCapture(): String = try {
        val dir = File(host.getExternalFilesDir(Environment.DIRECTORY_PICTURES), "")
        dir.mkdirs()
        val out = File(dir, "darkith-" + System.currentTimeMillis() + ".jpg")
        val uri = android.provider.MediaStore.Files.getContentUri("external")
        val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
            putExtra(MediaStore.EXTRA_OUTPUT, Uri.fromFile(out))
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        val id = nextId("camera")
        host.pendingDeviceIntent = Pair(id, out.absolutePath)
        host.startActivityForResult(intent, REQ_CAMERA)
        "PENDING:$id"
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun cameraPickImage(): String = try {
        val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
            type = "image/*"
            addCategory(Intent.CATEGORY_OPENABLE)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        val id = nextId("image")
        host.pendingDeviceIntent = Pair(id, "")
        host.startActivityForResult(Intent.createChooser(intent, "Pick an image"), REQ_PICK_IMAGE)
        "PENDING:$id"
    } catch (e: Throwable) { err(e) }

    /* ---------------------------------------------------------------- clock* */

    @JavascriptInterface fun clockSetAlarm(hour: Int, minute: Int, label: String?, skipUi: Boolean): String = try {
        val intent = Intent(if (skipUi) AlarmClock.ACTION_SET_ALARM else AlarmClock.ACTION_SHOW_ALARMS).apply {
            if (skipUi) {
                putExtra(AlarmClock.EXTRA_HOUR, hour.coerceIn(0, 23))
                putExtra(AlarmClock.EXTRA_MINUTES, minute.coerceIn(0, 59))
                putExtra(AlarmClock.EXTRA_SKIP_UI, true)
                if (!label.isNullOrBlank()) putExtra(AlarmClock.EXTRA_MESSAGE, label)
            }
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        host.startActivity(intent)
        "OK"
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun clockTimer(seconds: Int, label: String?): String = try {
        val intent = Intent(AlarmClock.ACTION_SET_TIMER).apply {
            putExtra(AlarmClock.EXTRA_LENGTH, seconds.coerceIn(1, 86400))
            putExtra(AlarmClock.EXTRA_SKIP_UI, true)
            if (!label.isNullOrBlank()) putExtra(AlarmClock.EXTRA_MESSAGE, label)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        host.startActivity(intent)
        "OK"
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun clockShowAlarms(): String = try {
        host.startActivity(Intent(AlarmClock.ACTION_SHOW_ALARMS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        "OK"
    } catch (e: Throwable) { err(e) }

    /* ---------------------------------------------------------------- media* */

    /** Ask MediaStore for images/video/audio. This is how a gallery gets real thumbnails. */
    @JavascriptInterface fun mediaList(kind: String?, limit: Int): String = try {
        val k = (kind ?: "image").lowercase()
        val (collection, mimePrefix) = when (k) {
            "video" -> MediaStore.Video.Media.EXTERNAL_CONTENT_URI to "video/"
            "audio" -> MediaStore.Audio.Media.EXTERNAL_CONTENT_URI to "audio/"
            else -> MediaStore.Images.Media.EXTERNAL_CONTENT_URI to "image/"
        }
        val a = JSONArray()
        val proj = arrayOf(
            MediaStore.MediaColumns._ID,
            MediaStore.MediaColumns.DISPLAY_NAME,
            MediaStore.MediaColumns.SIZE,
            MediaStore.MediaColumns.DATE_MODIFIED,
            MediaStore.MediaColumns.MIME_TYPE
        )
        val c = host.contentResolver.query(collection, proj, null, null,
            MediaStore.MediaColumns.DATE_MODIFIED + " DESC")
        c?.use {
            var n = 0
            while (it.moveToNext() && n < limit.coerceIn(1, 5000)) {
                val id = it.getLong(0)
                val uri = Uri.withAppendedPath(collection, id.toString())
                a.put(JSONObject().apply {
                    put("id", id)
                    put("name", it.getString(1) ?: "")
                    put("bytes", it.getLong(2))
                    put("mtime", it.getLong(3) * 1000L)
                    put("mime", it.getString(4) ?: (mimePrefix + "unknown"))
                    put("uri", uri.toString())
                    put("path", mediaPath(uri))
                })
                n++
            }
        }
        a.toString()
    } catch (e: Throwable) { err(e) }

    /** Resolve a content:// MediaStore uri to a real filesystem path when possible. */
    private fun mediaPath(uri: Uri): String = try {
        val proj = arrayOf(MediaStore.MediaColumns.DATA)
        host.contentResolver.query(uri, proj, null, null, null)?.use {
            if (it.moveToFirst()) it.getString(0) ?: "" else ""
        } ?: ""
    } catch (e: Throwable) { "" }

    /* ---------------------------------------------------------------- notif* */

    private fun channel(): String {
        val id = "darkith-default"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = host.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (nm.getNotificationChannel(id) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(id, "Darkith", NotificationManager.IMPORTANCE_DEFAULT)
                )
            }
        }
        return id
    }

    @JavascriptInterface fun notifPost(title: String?, body: String?): String = try {
        if (Build.VERSION.SDK_INT >= 33 && !granted(Manifest.permission.POST_NOTIFICATIONS)) {
            need(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            val nm = host.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val n: Notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Notification.Builder(host, channel())
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle(title ?: "Darkith")
                    .setContentText(body ?: "")
                    .setAutoCancel(true)
                    .build()
            } else {
                @Suppress("DEPRECATION")
                Notification.Builder(host)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle(title ?: "Darkith")
                    .setContentText(body ?: "")
                    .setAutoCancel(true)
                    .build()
            }
            nm.notify(System.currentTimeMillis().toInt(), n)
            "OK"
        }
    } catch (e: Throwable) { err(e) }

    @JavascriptInterface fun notifCancelAll(): String = try {
        val nm = host.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.cancelAll()
        "OK"
    } catch (e: Throwable) { err(e) }

    /* --------------------------------------------------------------- results */

    /** The UI polls this after a PENDING:<id> call. Returns "" until the result lands. */
    @JavascriptInterface fun deviceResult(id: String?): String = try {
        if (id.isNullOrBlank()) "" else results.remove(id) ?: ""
    } catch (e: Throwable) { "" }
}
