package com.ghost.alpha.data.local

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters
import com.ghost.alpha.domain.model.Position
import com.ghost.alpha.domain.model.Signal
import com.ghost.alpha.domain.model.TradeExecutionResult
import kotlinx.coroutines.flow.Flow
import java.time.Instant

@Entity(tableName = "signals")
data class SignalEntity(
    @PrimaryKey val symbol: String,
    val signal: String,
    val confidence: Double,
    val reasoning: String,
    val generatedAt: String
) {
    fun toDomain(): Signal = Signal(
        symbol = symbol,
        signal = signal,
        confidence = confidence,
        reasoning = reasoning,
        generatedAt = Instant.parse(generatedAt)
    )
}

@Entity(tableName = "positions")
data class PositionEntity(
    @PrimaryKey val symbol: String,
    val strategy: String,
    val side: String,
    val entryPrice: Double,
    val currentPrice: Double,
    val unrealizedPnl: Double,
    val unrealizedPnlPct: Double,
    val units: Double,
    val notional: Double,
    val sector: String,
    val openedAt: String
) {
    fun toDomain(): Position = Position(
        symbol = symbol,
        strategy = strategy,
        side = side,
        entryPrice = entryPrice,
        currentPrice = currentPrice,
        unrealizedPnl = unrealizedPnl,
        unrealizedPnlPct = unrealizedPnlPct,
        units = units,
        notional = notional,
        sector = sector,
        openedAt = Instant.parse(openedAt)
    )
}

@Entity(tableName = "trade_history")
data class TradeHistoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val symbol: String,
    val strategy: String,
    val side: String,
    val accepted: Boolean,
    val reason: String?,
    val positionSize: Double,
    val riskLevel: String,
    val createdAt: String
)

fun Signal.toEntity(): SignalEntity = SignalEntity(
    symbol = symbol,
    signal = signal,
    confidence = confidence,
    reasoning = reasoning,
    generatedAt = generatedAt.toString()
)

fun Position.toEntity(): PositionEntity = PositionEntity(
    symbol = symbol,
    strategy = strategy,
    side = side,
    entryPrice = entryPrice,
    currentPrice = currentPrice,
    unrealizedPnl = unrealizedPnl,
    unrealizedPnlPct = unrealizedPnlPct,
    units = units,
    notional = notional,
    sector = sector,
    openedAt = openedAt.toString()
)

fun TradeExecutionResult.toEntity(symbol: String, strategy: String, side: String): TradeHistoryEntity = TradeHistoryEntity(
    symbol = symbol,
    strategy = strategy,
    side = side,
    accepted = accepted,
    reason = reason,
    positionSize = positionSize,
    riskLevel = riskLevel,
    createdAt = Instant.now().toString()
)

@Dao
interface SignalDao {
    @Query("SELECT * FROM signals ORDER BY generatedAt DESC")
    fun observeAll(): Flow<List<SignalEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: SignalEntity)
}

@Dao
interface PositionDao {
    @Query("SELECT * FROM positions ORDER BY openedAt DESC")
    fun observeAll(): Flow<List<PositionEntity>>

    @Query("DELETE FROM positions")
    suspend fun clear()

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun replaceAll(entities: List<PositionEntity>)
}

@Dao
interface TradeHistoryDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: TradeHistoryEntity)
}

class InstantConverters {
    @TypeConverter
    fun fromInstant(value: Instant?): String? = value?.toString()

    @TypeConverter
    fun toInstant(value: String?): Instant? = value?.let(Instant::parse)
}

@Database(
    entities = [SignalEntity::class, PositionEntity::class, TradeHistoryEntity::class],
    version = 1,
    exportSchema = false
)
@TypeConverters(InstantConverters::class)
abstract class GhostAlphaDatabase : RoomDatabase() {
    abstract fun signalDao(): SignalDao
    abstract fun positionDao(): PositionDao
    abstract fun tradeHistoryDao(): TradeHistoryDao
}