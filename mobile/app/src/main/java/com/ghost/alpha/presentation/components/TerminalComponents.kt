package com.ghost.alpha.presentation.components

import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Badge
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import com.ghost.alpha.domain.model.AgentVote
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin

@Composable
fun TerminalCard(
    title: String,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            HorizontalDivider(color = MaterialTheme.colorScheme.primary.copy(alpha = 0.25f))
            content()
        }
    }
}

@Composable
fun MetricRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun SignalBadge(signal: String) {
    val background = when (signal.uppercase()) {
        "BUY", "BULLISH" -> Color(0xFF103A2B)
        "SELL", "BEARISH" -> Color(0xFF401B22)
        else -> Color(0xFF21303B)
    }
    val content = when (signal.uppercase()) {
        "BUY", "BULLISH" -> Color(0xFF2BFDB3)
        "SELL", "BEARISH" -> Color(0xFFFF7B88)
        else -> Color(0xFF8BCBFF)
    }
    Text(
        text = signal,
        color = content,
        style = MaterialTheme.typography.labelMedium,
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(background)
            .padding(horizontal = 12.dp, vertical = 6.dp)
    )
}

@Composable
fun ConfidenceMeter(confidence: Double) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        MetricRow("Confidence", "${(confidence * 100).toInt()}%")
        LinearProgressIndicator(
            progress = { confidence.toFloat().coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.primary,
            trackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)
        )
    }
}

@Composable
fun ErrorBanner(
    message: String,
    modifier: Modifier = Modifier,
    onRetry: (() -> Unit)? = null
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
        shape = RoundedCornerShape(14.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Network / Execution Error", color = MaterialTheme.colorScheme.onErrorContainer, fontWeight = FontWeight.SemiBold)
            Text(message, color = MaterialTheme.colorScheme.onErrorContainer)
            if (onRetry != null) {
                Button(onClick = onRetry) {
                    Text("Retry")
                }
            }
        }
    }
}

@Composable
fun SkeletonTerminalCard(
    title: String,
    rows: Int,
    modifier: Modifier = Modifier
) {
    TerminalCard(title = title, modifier = modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            repeat(rows) { idx ->
                val width = if (idx % 2 == 0) 0.95f else 0.72f
                Box(
                    modifier = Modifier
                        .fillMaxWidth(width)
                        .height(14.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f))
                )
            }
        }
    }
}

@Composable
fun LoadingRow(message: String = "Syncing live state...") {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Start,
        verticalAlignment = Alignment.CenterVertically
    ) {
        LinearProgressIndicator(modifier = Modifier.weight(1f))
        Spacer(modifier = Modifier.width(10.dp))
        Text(message, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun SwarmNodeGraph(
    agents: List<AgentVote>,
    consensusSignal: String,
    modifier: Modifier = Modifier
) {
    if (agents.isEmpty()) {
        Text("Awaiting agent topology")
        return
    }

    var canvasWidthPx = 0
    var canvasHeightPx = 0

    BoxWithConstraints(
        modifier = modifier
            .fillMaxWidth()
            .height(260.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.65f))
            .onSizeChanged {
                canvasWidthPx = it.width
                canvasHeightPx = it.height
            }
    ) {
        val nodePositions = calculateNodePositions(agents.size, canvasWidthPx, canvasHeightPx)
        val centerX = canvasWidthPx / 2f
        val centerY = canvasHeightPx / 2f
        val heatColor = signalColor(consensusSignal).copy(alpha = 0.14f)

        Canvas(modifier = Modifier.fillMaxSize()) {
            // Confidence heat layer around the consensus center.
            drawCircle(
                color = heatColor,
                radius = size.minDimension * 0.42f,
                center = androidx.compose.ui.geometry.Offset(centerX, centerY)
            )

            nodePositions.forEachIndexed { i, p1 ->
                for (j in i + 1 until nodePositions.size) {
                    val p2 = nodePositions[j]
                    val agree = agents[i].bias.equals(agents[j].bias, ignoreCase = true)
                    drawLine(
                        color = if (agree) Color(0xFF2BFDB3) else Color(0xFFFF7B88),
                        start = androidx.compose.ui.geometry.Offset(p1.first, p1.second),
                        end = androidx.compose.ui.geometry.Offset(p2.first, p2.second),
                        strokeWidth = if (agree) 3f else 1.7f,
                        alpha = if (agree) 0.36f else 0.28f
                    )
                }
            }

            drawCircle(
                color = signalColor(consensusSignal),
                radius = 22f,
                center = androidx.compose.ui.geometry.Offset(centerX, centerY),
                style = Stroke(width = 4f),
                alpha = 0.85f
            )
        }

        Text(
            text = consensusSignal,
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.Bold,
            color = signalColor(consensusSignal),
            modifier = Modifier.align(Alignment.Center)
        )

        val density = LocalDensity.current
        nodePositions.forEachIndexed { idx, point ->
            val vote = agents[idx]
            val xDp = with(density) { point.first.toDp() } - 26.dp
            val yDp = with(density) { point.second.toDp() } - 26.dp

            Box(
                modifier = Modifier
                    .offset(xDp, yDp)
                    .size(52.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(signalColor(vote.bias).copy(alpha = 0.22f)),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = vote.name.take(2).uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    color = signalColor(vote.bias),
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
fun ConfidenceHeatmap(
    agents: List<AgentVote>,
    modifier: Modifier = Modifier
) {
    if (agents.isEmpty()) {
        Text("No agent confidence map available")
        return
    }

    val sorted = agents.sortedByDescending { it.confidence }
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        sorted.forEach { vote ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = vote.name,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.width(90.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(10.dp)
                        .clip(RoundedCornerShape(999.dp))
                        .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .fillMaxWidth(vote.confidence.toFloat().coerceIn(0f, 1f))
                            .clip(RoundedCornerShape(999.dp))
                            .background(signalColor(vote.bias).copy(alpha = 0.75f))
                    )
                }
                Text(
                    text = "${(vote.confidence * 100).toInt()}%",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}

private fun calculateNodePositions(count: Int, widthPx: Int, heightPx: Int): List<Pair<Float, Float>> {
    if (count == 0 || widthPx == 0 || heightPx == 0) return emptyList()
    val centerX = widthPx / 2f
    val centerY = heightPx / 2f
    val radius = (minOf(widthPx, heightPx) * 0.34f)
    return (0 until count).map { idx ->
        val angle = (2 * PI / count) * idx - (PI / 2)
        val x = centerX + (radius * cos(angle)).toFloat()
        val y = centerY + (radius * sin(angle)).toFloat()
        x to y
    }
}

private fun signalColor(signal: String): Color {
    return when (signal.uppercase()) {
        "BUY", "BULLISH" -> Color(0xFF2BFDB3)
        "SELL", "BEARISH" -> Color(0xFFFF7B88)
        else -> Color(0xFF8BCBFF)
    }
}

@Composable
fun LoadingSkeletonBox(height: androidx.compose.ui.unit.Dp = 100.dp, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(height)
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f))
    )
}