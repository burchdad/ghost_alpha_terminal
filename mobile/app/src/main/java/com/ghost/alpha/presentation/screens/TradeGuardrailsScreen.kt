package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ghost.alpha.domain.model.RiskSeverity
import com.ghost.alpha.domain.model.TradeGuardrail
import com.ghost.alpha.presentation.components.LoadingSkeletonBox
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.viewmodel.GuardrailAssessmentState
import com.ghost.alpha.presentation.viewmodel.GuardrailApprovalState
import com.ghost.alpha.presentation.viewmodel.TradeGuardrailsViewModel

@Composable
fun TradeGuardrailsScreen(
    viewModel: TradeGuardrailsViewModel = hiltViewModel()
) {
    val assessmentState by viewModel.assessmentState.collectAsState()
    val approvalState by viewModel.approvalState.collectAsState()

    var showAssessmentForm by remember { mutableStateOf(true) }
    var symbol by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("") }
    var side by remember { mutableStateOf("BUY") }
    var price by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0x0A0E27))
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "Trade Guardrails",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0x00FF41)
        )

        if (showAssessmentForm) {
            AssessmentFormCard(
                symbol = symbol,
                onSymbolChange = { symbol = it },
                quantity = quantity,
                onQuantityChange = { quantity = it },
                side = side,
                onSideChange = { side = it },
                price = price,
                onPriceChange = { price = it },
                onSubmit = {
                    if (symbol.isNotEmpty() && quantity.isNotEmpty() && price.isNotEmpty()) {
                        viewModel.assessTradeRisk(symbol, quantity.toDouble(), side, price.toDouble())
                        showAssessmentForm = false
                    }
                }
            )
        }

        when (assessmentState) {
            GuardrailAssessmentState.Idle -> {}
            GuardrailAssessmentState.Loading -> {
                LoadingSkeletonBox(height = 300.dp)
            }

            is GuardrailAssessmentState.Success -> {
                RiskAssessmentCard((assessmentState as GuardrailAssessmentState.Success).guardrail)
                ApprovalButtonsCard(
                    approved = false,
                    onApprove = {
                        viewModel.approveTradeWithGuardrails(
                            tradeId = (assessmentState as GuardrailAssessmentState.Success).guardrail.tradeId,
                            approved = true,
                            reason = "User approved trade"
                        )
                    },
                    onReject = {
                        viewModel.approveTradeWithGuardrails(
                            tradeId = (assessmentState as GuardrailAssessmentState.Success).guardrail.tradeId,
                            approved = false,
                            reason = "User rejected trade"
                        )
                    }
                )
            }

            is GuardrailAssessmentState.Error -> {
                ErrorBanner(
                    message = (assessmentState as GuardrailAssessmentState.Error).message,
                    onRetry = { showAssessmentForm = true }
                )
            }
        }

        when (approvalState) {
            GuardrailApprovalState.Idle -> {}
            GuardrailApprovalState.Loading -> {
                Text("Processing approval...", color = Color(0x00FF41))
            }

            is GuardrailApprovalState.Success -> {
                val audit = (approvalState as GuardrailApprovalState.Success).audit
                ApprovalResultCard(audit)
                Button(
                    onClick = {
                        viewModel.clearApprovalState()
                        viewModel.clearCurrentTrade()
                        showAssessmentForm = true
                        symbol = ""
                        quantity = ""
                        price = ""
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0x00FF41))
                ) {
                    Text("New Trade", color = Color.Black)
                }
            }

            is GuardrailApprovalState.Error -> {
                ErrorBanner(
                    message = (approvalState as GuardrailApprovalState.Error).message,
                    onRetry = { viewModel.clearApprovalState() }
                )
            }
        }
    }
}

@Composable
private fun AssessmentFormCard(
    symbol: String,
    onSymbolChange: (String) -> Unit,
    quantity: String,
    onQuantityChange: (String) -> Unit,
    side: String,
    onSideChange: (String) -> Unit,
    price: String,
    onPriceChange: (String) -> Unit,
    onSubmit: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0x1A1F3A)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Assess Trade Risk", fontWeight = FontWeight.Bold, color = Color(0x00FF41))

            FormInputField("Symbol", symbol, onSymbolChange)
            FormInputField("Quantity", quantity, onQuantityChange)
            FormInputField("Price", price, onPriceChange)

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    onClick = { onSideChange("BUY") },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (side == "BUY") Color(0x00FF41) else Color(0x1A1F3A)
                    )
                ) {
                    Text(if (side == "BUY") "BUY ✓" else "BUY", color = if (side == "BUY") Color.Black else Color.White)
                }
                Button(
                    onClick = { onSideChange("SELL") },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (side == "SELL") Color(0xFF6464) else Color(0x1A1F3A)
                    )
                ) {
                    Text(if (side == "SELL") "SELL ✓" else "SELL", color = if (side == "SELL") Color.Black else Color.White)
                }
            }

            Button(
                onClick = onSubmit,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0x00FF41))
            ) {
                Text("Assess Risk", color = Color.Black, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun FormInputField(label: String, value: String, onValueChange: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label, fontSize = 12.sp, color = Color(0xAAAAAA))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0x0A0E27), RoundedCornerShape(6.dp))
                .padding(12.dp)
        ) {
            if (value.isEmpty()) {
                Text(label, color = Color(0x666666), fontSize = 12.sp)
            } else {
                Text(value, color = Color.White, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun RiskAssessmentCard(guardrail: TradeGuardrail) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0x1A1F3A)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("${guardrail.symbol} - ${guardrail.side}", fontWeight = FontWeight.Bold, color = Color(0x00FF41))
                Text("${guardrail.quantity} @ ${guardrail.price}", fontSize = 12.sp, color = Color(0xAAAAAA))
            }

            // Risk Score
            RiskScoreDisplay(guardrail.riskScore.overallScore, guardrail.riskScore.recommendation)

            // Guardrail Status
            GuardrailStatusDisplay(guardrail.guardrailStatus)

            // Portfolio Impact
            PortfolioImpactDisplay(guardrail.estimatedImpact)

            // Warnings
            if (guardrail.warnings.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Warnings", fontWeight = FontWeight.Bold, color = Color(0xFFAA00), fontSize = 12.sp)
                    guardrail.warnings.forEach { warning ->
                        WarningItem(warning.title, warning.message, warning.severity)
                    }
                }
            }
        }
    }
}

@Composable
private fun RiskScoreDisplay(score: Double, recommendation: String) {
    val riskColor = when {
        score < 30 -> Color(0x00FF41)
        score < 60 -> Color(0xFFAA00)
        else -> Color(0xFF6464)
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Risk Score", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xAAAAAA))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("$score / 100", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = riskColor)
            Text(recommendation, fontSize = 12.sp, color = riskColor)
        }
        LinearProgressIndicator(
            progress = { score / 100f },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp),
            color = riskColor,
            trackColor = Color(0x2A2F4A)
        )
    }
}

@Composable
private fun GuardrailStatusDisplay(status: com.ghost.alpha.domain.model.GuardrailStatus) {
    val statusIcon = if (status.passed) Icons.Default.Check else Icons.Default.Close
    val statusColor = if (status.passed) Color(0x00FF41) else Color(0xFF6464)

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = statusIcon,
                contentDescription = null,
                modifier = Modifier.size(20.dp),
                tint = statusColor
            )
            Text(
                if (status.passed) "PASSED" else "BLOCKED",
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
                color = statusColor
            )
        }
        if (status.blockers.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Blockers:", fontSize = 11.sp, color = Color(0xFF6464), fontWeight = FontWeight.Bold)
                status.blockers.forEach { blocker ->
                    Text("• $blocker", fontSize = 10.sp, color = Color(0xFF6464))
                }
            }
        }
    }
}

@Composable
private fun PortfolioImpactDisplay(impact: com.ghost.alpha.domain.model.PortfolioImpact) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Portfolio Impact", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xAAAAAA))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("Current Exposure: ${String.format("%.1f", impact.currentExposure)}%", fontSize = 11.sp, color = Color(0xCCCCCC))
            Text("Proposed: ${String.format("%.1f", impact.proposedExposure)}%", fontSize = 11.sp, color = Color(0x00FF41))
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("Drawdown Risk: ${String.format("%.1f", impact.drawdownRisk)}%", fontSize = 11.sp, color = Color(0xCCCCCC))
            Text("Liquidity: ${impact.liquidityRisk}", fontSize = 11.sp, color = Color(0xAAAAAA))
        }
    }
}

@Composable
private fun WarningItem(title: String, message: String, severity: RiskSeverity) {
    val warnColor = when (severity) {
        RiskSeverity.LOW -> Color(0x00FF41)
        RiskSeverity.MEDIUM -> Color(0xFFAA00)
        RiskSeverity.HIGH -> Color(0xFF9966)
        RiskSeverity.CRITICAL -> Color(0xFF6464)
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0x2A2F4A), RoundedCornerShape(6.dp))
            .padding(8.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = warnColor)
            Text(message, fontSize = 10.sp, color = Color(0xAAAAAA))
        }
    }
}

@Composable
private fun ApprovalButtonsCard(approved: Boolean, onApprove: () -> Unit, onReject: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Button(
            onClick = onReject,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6464))
        ) {
            Text("Reject Trade", color = Color.White)
        }
        Button(
            onClick = onApprove,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0x00FF41))
        ) {
            Text("Execute Trade", color = Color.Black, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun ApprovalResultCard(audit: com.ghost.alpha.domain.model.TradeExecutionAudit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0x1A1F3A)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Execution Result", fontWeight = FontWeight.Bold, color = Color(0x00FF41))
                val resultColor = when (audit.executionStatus) {
                    com.ghost.alpha.domain.model.ExecutionStatus.EXECUTED -> Color(0x00FF41)
                    com.ghost.alpha.domain.model.ExecutionStatus.REJECTED -> Color(0xFF6464)
                    else -> Color(0xFFAA00)
                }
                Text(audit.executionStatus.name, color = resultColor, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }

            Text("Trade ID: ${audit.tradeId}", fontSize = 11.sp, color = Color(0xAAAAAA))
            if (audit.pnl != null) {
                val pnlColor = if (audit.pnl > 0) Color(0x00FF41) else Color(0xFF6464)
                Text("PnL: ${String.format("%.2f", audit.pnl)}", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = pnlColor)
            }
        }
    }
}
