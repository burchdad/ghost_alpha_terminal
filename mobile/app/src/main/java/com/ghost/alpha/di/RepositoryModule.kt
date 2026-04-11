package com.ghost.alpha.di

import com.ghost.alpha.data.repository.AuthRepositoryImpl
import com.ghost.alpha.data.repository.AuditTrailRepositoryImpl
import com.ghost.alpha.data.repository.AutonomyRepositoryImpl
import com.ghost.alpha.data.repository.BrokerRepositoryImpl
import com.ghost.alpha.data.repository.CopilotRepositoryImpl
import com.ghost.alpha.data.repository.GuardrailRepositoryImpl
import com.ghost.alpha.data.repository.MarketRepositoryImpl
import com.ghost.alpha.data.repository.PerformanceRepositoryImpl
import com.ghost.alpha.data.repository.RealtimeRepositoryImpl
import com.ghost.alpha.domain.repository.AuthRepository
import com.ghost.alpha.domain.repository.AuditTrailRepository
import com.ghost.alpha.domain.repository.AutonomyRepository
import com.ghost.alpha.domain.repository.BrokerRepository
import com.ghost.alpha.domain.repository.CopilotRepository
import com.ghost.alpha.domain.repository.GuardrailRepository
import com.ghost.alpha.domain.repository.MarketRepository
import com.ghost.alpha.domain.repository.PerformanceRepository
import com.ghost.alpha.domain.repository.RealtimeRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    @Singleton
    abstract fun bindAuthRepository(impl: AuthRepositoryImpl): AuthRepository

    @Binds
    @Singleton
    abstract fun bindAuditTrailRepository(impl: AuditTrailRepositoryImpl): AuditTrailRepository

    @Binds
    @Singleton
    abstract fun bindAutonomyRepository(impl: AutonomyRepositoryImpl): AutonomyRepository

    @Binds
    @Singleton
    abstract fun bindMarketRepository(impl: MarketRepositoryImpl): MarketRepository

    @Binds
    @Singleton
    abstract fun bindBrokerRepository(impl: BrokerRepositoryImpl): BrokerRepository

    @Binds
    @Singleton
    abstract fun bindRealtimeRepository(impl: RealtimeRepositoryImpl): RealtimeRepository

    @Binds
    @Singleton
    abstract fun bindCopilotRepository(impl: CopilotRepositoryImpl): CopilotRepository

    @Binds
    @Singleton
    abstract fun bindPerformanceRepository(impl: PerformanceRepositoryImpl): PerformanceRepository

    @Binds
    @Singleton
    abstract fun bindGuardrailRepository(impl: GuardrailRepositoryImpl): GuardrailRepository
}