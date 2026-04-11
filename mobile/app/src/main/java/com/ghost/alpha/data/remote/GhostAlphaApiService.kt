package com.ghost.alpha.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface GhostAlphaApiService {
    @POST("auth/login")
    suspend fun login(@Body payload: LoginRequestDto): AuthResponseDto

    @POST("auth/refresh")
    suspend fun refreshSession(): AuthResponseDto

    @POST("auth/2fa/verify")
    suspend fun verifyTwoFactor(@Body payload: TwoFactorVerifyRequestDto): TwoFactorVerifyResponseDto

    @GET("auth/session/high-trust-status")
    suspend fun getHighTrustStatus(): HighTrustStatusDto

    @POST("auth/logout")
    suspend fun logout(): Map<String, Any>

    @GET("signal/{symbol}")
    suspend fun getSignal(@Path("symbol") symbol: String): SignalDto

    @GET("portfolio")
    suspend fun getPortfolio(): PortfolioDto

    @GET("swarm/{symbol}")
    suspend fun getSwarm(@Path("symbol") symbol: String): SwarmResponseDto

    @POST("execute")
    suspend fun executeTrade(@Body payload: ExecuteTradeRequestDto): ExecuteTradeResponseDto

    @GET("brokers/status")
    suspend fun getBrokers(): Map<String, BrokerStatusItemDto>

    @POST("alpaca/oauth/disconnect")
    suspend fun disconnectAlpaca(): Map<String, Any>

    @POST("backtest")
    suspend fun runBacktest(@Body payload: BacktestRequestDto): BacktestResponseDto

    // Trade Guardrails
    @POST("trade/guardrails/assess")
    suspend fun assessTradeRisks(@Body payload: TradeGuardrailRequestDto): TradeGuardrailResponseDto

    @POST("trade/guardrails/approve")
    suspend fun approveTradeWithGuardrails(@Body payload: GuardrailApprovalDto): TradeExecutionAuditDto

    @GET("trade/audits/{tradeId}")
    suspend fun getTradeAudit(@Path("tradeId") tradeId: String): TradeExecutionAuditDto

    @GET("trade/audits/recent/{limit}")
    suspend fun getRecentTradeAudits(@Path("limit") limit: Int = 10): List<TradeExecutionAuditDto>

    // Copilot AI Command Layer
    @GET("copilot/context")
    suspend fun getCopilotContext(): CopilotContextResponseDto

    @POST("copilot/chat")
    suspend fun sendCopilotMessage(@Body payload: CopilotChatRequestDto): CopilotChatResponseDto

    @GET("copilot/telemetry/summary")
    suspend fun getCopilotTelemetrySummary(): CopilotTelemetrySummaryResponseDto

    // Performance Intelligence
    @GET("metrics/truth-dashboard")
    suspend fun getTruthDashboard(@Query("days") days: Int = 7): TruthDashboardResponseDto

    @GET("agents/weights")
    suspend fun getAgentWeights(): AgentWeightsResponseDto

    @GET("agents/execution-history")
    suspend fun getExecutionHistory(@Query("limit") limit: Int = 50): ExecutionHistoryResponseDto

    @GET("performance/{symbol}")
    suspend fun getSymbolPerformance(@Path("symbol") symbol: String): PerformanceResponseDto

    // Decision Audit Trail
    @GET("agents/audit/decisions")
    suspend fun getDecisionAudits(
        @Query("limit") limit: Int = 50,
        @Query("symbol") symbol: String? = null,
        @Query("status") status: String? = null
    ): DecisionAuditSummaryListResponseDto

    @GET("agents/audit/replay/{auditId}")
    suspend fun getDecisionReplay(@Path("auditId") auditId: String): DecisionReplayResponseDto

    @GET("agents/audit/decisions/{auditId}")
    suspend fun getDecisionAuditDetail(@Path("auditId") auditId: String): DecisionAuditDetailResponseDto
}