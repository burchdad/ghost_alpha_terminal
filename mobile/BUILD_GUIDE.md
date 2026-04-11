# Android Mobile App - Build & Development Guide

## Project Structure

The Ghost Alpha Terminal Android app is located in `/mobile/` with full Clean Architecture + MVVM setup:

```
mobile/
├── gradle/
│   └── wrapper/
│       └── gradle-wrapper.properties    # Gradle 8.5 config
├── app/
│   └── src/main/
│       ├── java/com/ghost/alpha/
│       │   ├── data/                    # API, WebSocket, Room DB, secure storage
│       │   ├── domain/                  # Models, repositories, use cases
│       │   ├── presentation/            # Screens, ViewModels, Components
│       │   ├── di/                      # Hilt dependency injection
│       │   ├── navigation/              # Compose navigation graph
│       │   ├── ui/theme/                # Dark terminal theme
│       │   ├── utils/                   # Firebase FCM service
│       │   ├── GhostAlphaApp.kt         # Hilt application class
│       │   └── MainActivity.kt          # Compose activity
│       ├── res/                         # Strings, colors, security config
│       └── AndroidManifest.xml
├── app/build.gradle.kts                # App build config with Hilt, Room, Retrofit, etc.
├── build.gradle.kts                    # Root build config
├── settings.gradle.kts                 # Gradle settings
├── gradle.properties                   # Version catalogs, Android config
├── gradlew                             # Unix wrapper (executable)
└── gradlew.bat                         # Windows wrapper

```

## What's Implemented

### ✅ Complete

- **Clean Architecture**: data/domain/presentation layers properly separated
- **Dependency Injection**: Hilt with NetworkModule, DatabaseModule, RepositoryModule
- **Authentication**: JWT + refresh token rotation, EncryptedSharedPreferences, token interceptor
- **Real-Time**: WebSocket manager with auto-reconnect and exponential backoff
- **Local Storage**: Room DB with DAOs for caching signals, positions, trades
- **API Client**: Retrofit + OkHttp with secure token handling
- **Navigation**: Compose NavGraph with 7 screens (Login, 2FA, Dashboard, Swarm Terminal, Trading, Brokers, Backtesting)
- **ViewModels**: Per-screen state management with StateFlow
- **UI**: Dark terminal-style theme, Compose-only (no XML layouts)
- **FCM Integration**: Firebase Cloud Messaging scaffold for notifications
- **Deep Links**: OAuth callback handler (ghost://oauth/callback)

### 📦 Key Dependencies

- Jetpack Compose 1.7.4
- Hilt 2.52 (dependency injection)
- Retrofit 2.11.0 (HTTP client)
- OkHttp 4.12.0 (with interceptors + authenticator)
- Room 2.6.1 (local DB)
- EncryptedSharedPreferences (secure token storage)
- Kotlinx Coroutines 1.8.0
- Kotlinx Serialization (JSON parsing)
- Firebase Cloud Messaging 24.1.0
- Compose Navigation

## First-Time Setup

### Prerequisites

- Android Studio Koala or later
- Android SDK 35 (target)
- Android SDK 28+ (minSdk)
- JDK 17+

### Steps

1. **Clone and navigate:**
   ```bash
   cd /workspaces/ghost_alpha_terminal/mobile
   ```

2. **Build the project:**
   ```bash
   # On Unix/Mac/Linux:
   ./gradlew build

   # On Windows:
   gradlew.bat build
   ```

3. **Run on emulator or device:**
   ```bash
   ./gradlew installDebug
   ```

4. **Open in Android Studio:**
   - File → Open → Select `/mobile` folder
   - Let Gradle sync (first time will take 2-5 min)
   - Run → Select emulator/device

## Configuration

### Backend API URLs

Edit `app/build.gradle.kts`:

```kotlin
buildConfigField("String", "API_BASE_URL", '"https://api.ghostalpha.ai/"')
buildConfigField("String", "WS_BASE_URL", '"wss://api.ghostalpha.ai/ws"')
```

### Firebase FCM

1. Download `google-services.json` from Firebase Console
2. Place in `app/` folder
3. Gradle will auto-detect on next build

### Broker OAuth

Deep link is pre-configured:
- Scheme: `ghost://`
- Host: `oauth`
- Path: `/callback`

Handled in `BrokerConnectionScreen` via Chrome Custom Tabs.

## Key Code Entry Points

### Authentication Flow

- **Login**: `LoginScreen` + `AuthViewModel` + `LoginUseCase`
- **2FA**: `TwoFactorScreen` + `AuthViewModel`
- **Token Refresh**: `TokenRefreshAuthenticator` (auto-intercepts 401s)
- **Secure Storage**: `AuthTokenStorage` (EncryptedSharedPreferences)

### Real-Time Data

- **WebSocket Manager**: `GhostAlphaWebSocketManager` (auto-reconnect, heartbeat)
- **Streams**: Exposed as `StateFlow<T>` in view models
- **Repository**: `RealtimeRepositoryImpl` bridges WebSocket → StateFlow

### Trading Features

- **Signals**: `FetchSignalsUseCase` → `MarketRepository` → `GhostAlphaApiService`
- **Execute Trade**: `ExecuteTradeUseCase`
- **Brokers**: `ConnectBrokerUseCase`, `DisconnectBrokerUseCase`
- **Backtest**: Upload simulation, poll results

## Testing (Not Yet Implemented)

Create `app/src/test/java/com/ghost/alpha/` with:
- `AuthRepositoryTest.kt`
- `MarketRepositoryTest.kt`
- `WebSocketManagerTest.kt`
- View model unit tests

## Deployment

```bash
# Generate signed APK
./gradlew assembleRelease

# Generate App Bundle (for Play Store)
./gradlew bundleRelease
```

Signed APK: `app/build/outputs/apk/release/app-release.apk`
App Bundle: `app/build/outputs/bundle/release/app-release.aab`

## Common Issues

| Issue | Solution |
|-------|----------|
| Gradle sync fails | Run `./gradlew clean`, then resync in Android Studio |
| EncryptedSharedPreferences crash | Ensure AndroidKeyStore is available (all modern devices have it) |
| WebSocket connection timeout | Check backend is deployed; URL is configurable in `buildConfigField` |
| Token refresh loop | Verify refresh endpoint returns valid new access token |
| Room DB migration error | Delete app data (Settings → Apps → Ghost Alpha → Storage → Clear) |

## Next Steps

1. **Add unit tests** for repositories and use cases
2. **Implement error UI** for network failures and edge cases
3. **Add loading skeleton** screens for better UX
4. **Wire Firebase FCM** for real trade/alert notifications
5. **Implement biometric auth** as optional step-up
6. **Add device fingerprint** for risk scoring

---

**Built with production-grade architecture. Ready for enterprise scaling.**
