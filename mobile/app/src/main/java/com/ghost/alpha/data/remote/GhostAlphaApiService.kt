package com.ghost.alpha.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

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
}