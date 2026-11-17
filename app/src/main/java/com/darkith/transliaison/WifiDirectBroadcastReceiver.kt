package com.darkith.transliaison
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.wifi.p2p.WifiP2pManager
import android.util.Log

class WifiDirectBroadcastReceiver : BroadcastReceiver() {
    companion object { private const val TAG = "WifiDirectReceiver" }
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            WifiP2pManager.WIFI_P2P_STATE_CHANGED_ACTION -> Log.d(TAG, "state changed")
            WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION -> Log.d(TAG, "peers changed")
            WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION -> Log.d(TAG, "connection changed")
            WifiP2pManager.WIFI_P2P_THIS_DEVICE_CHANGED_ACTION -> Log.d(TAG, "device changed")
        }
    }
}

