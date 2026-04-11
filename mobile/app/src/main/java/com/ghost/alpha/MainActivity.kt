package com.ghost.alpha

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import dagger.hilt.android.AndroidEntryPoint
import com.ghost.alpha.navigation.GhostAlphaRoot
import com.ghost.alpha.ui.theme.GhostAlphaTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private var pendingOAuthCallback by mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        pendingOAuthCallback = intent?.dataString
        setContent {
            GhostAlphaTheme {
                GhostAlphaRoot(initialDeepLink = pendingOAuthCallback)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        pendingOAuthCallback = intent.dataString
    }
}