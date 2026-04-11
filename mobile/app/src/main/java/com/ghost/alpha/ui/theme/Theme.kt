package com.ghost.alpha.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val GhostColorScheme = darkColorScheme(
    primary = Color(0xFF2BFDB3),
    onPrimary = Color(0xFF03120D),
    secondary = Color(0xFF66E3FF),
    onSecondary = Color(0xFF041117),
    tertiary = Color(0xFFFFC857),
    background = Color(0xFF060B10),
    surface = Color(0xFF0A1219),
    surfaceVariant = Color(0xFF0F1C26),
    onBackground = Color(0xFFE6F1F7),
    onSurface = Color(0xFFE6F1F7),
    error = Color(0xFFFF6474)
)

@Composable
fun GhostAlphaTheme(content: @Composable () -> Unit) {
    val colorScheme = if (isSystemInDarkTheme()) GhostColorScheme else GhostColorScheme
    MaterialTheme(
        colorScheme = colorScheme,
        typography = GhostTypography,
        content = content
    )
}