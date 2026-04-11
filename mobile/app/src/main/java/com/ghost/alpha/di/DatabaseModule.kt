package com.ghost.alpha.di

import android.content.Context
import androidx.room.Room
import com.ghost.alpha.data.local.GhostAlphaDatabase
import com.ghost.alpha.data.local.PositionDao
import com.ghost.alpha.data.local.SignalDao
import com.ghost.alpha.data.local.TradeHistoryDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): GhostAlphaDatabase =
        Room.databaseBuilder(context, GhostAlphaDatabase::class.java, "ghost_alpha_terminal.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    fun provideSignalDao(database: GhostAlphaDatabase): SignalDao = database.signalDao()

    @Provides
    fun providePositionDao(database: GhostAlphaDatabase): PositionDao = database.positionDao()

    @Provides
    fun provideTradeHistoryDao(database: GhostAlphaDatabase): TradeHistoryDao = database.tradeHistoryDao()
}