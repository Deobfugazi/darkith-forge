package com.darkith.transliaison

import android.content.Context
import com.android.apksig.ApkSigner
import java.io.File
import java.security.KeyFactory
import java.security.PrivateKey
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.security.spec.PKCS8EncodedKeySpec

class ApkSignerRunner(private val context: Context) {

    /**
     * Signs forged APKs with the key material in assets/engine/{release_key,release_cert}.
     *
     * SECURITY: release_key is a PRIVATE KEY shipped inside the APK and therefore readable by
     * anyone who obtains the APK or the source archive. It must be treated as compromised and
     * rotated (see tools/rotate_signing_key.sh); never publish the archive that contains it.
     */
    fun sign(inputApk: File, outputApk: File) {
        val privateKey: PrivateKey = context.assets.open("engine/release_key").use { stream ->
            KeyFactory.getInstance("RSA").generatePrivate(PKCS8EncodedKeySpec(stream.readBytes()))
        }

        val cert: X509Certificate = context.assets.open("engine/release_cert").use { stream ->
            CertificateFactory.getInstance("X.509").generateCertificate(stream) as X509Certificate
        }

        val signer = ApkSigner.Builder(listOf(
            ApkSigner.SignerConfig.Builder("darkith", privateKey, listOf(cert)).build()
        ))
            .setInputApk(inputApk)
            .setOutputApk(outputApk)
            .setV1SigningEnabled(true)
            .setV2SigningEnabled(true)
            .setV3SigningEnabled(true)
            .build()
        signer.sign()
    }
}

