package com.songbuddy.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.songbuddy.app.data.repository.SongBuddyRepository
import com.songbuddy.app.player.PlayerController
import com.songbuddy.app.ui.components.MiniPlayer
import com.songbuddy.app.ui.screens.*
import com.songbuddy.app.ui.theme.SongBuddyTheme
import com.songbuddy.app.ui.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {

    private lateinit var repository: SongBuddyRepository
    private lateinit var playerController: PlayerController
    private lateinit var viewModel: MainViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate()
        enableEdgeToEdge()

        repository = SongBuddyRepository(applicationContext)
        playerController = PlayerController(applicationContext, repository)
        viewModel = MainViewModel(repository)

        setContent {
            SongBuddyTheme {
                val token by viewModel.tokenState.collectAsState()
                val username by viewModel.usernameState.collectAsState()
                val serverUrl by viewModel.serverUrlState.collectAsState()
                val trendingTracks by viewModel.trendingTracks.collectAsState()
                val searchResults by viewModel.searchResults.collectAsState()
                val isLoading by viewModel.isLoading.collectAsState()
                val errorMessage by viewModel.errorMessage.collectAsState()
                val serverHealthy by viewModel.serverHealthy.collectAsState()

                val currentTrack by playerController.currentTrack.collectAsState()
                val isPlaying by playerController.isPlaying.collectAsState()
                val playbackPos by playerController.playbackPosition.collectAsState()
                val duration by playerController.duration.collectAsState()
                val isBuffering by playerController.isBuffering.collectAsState()
                val queue by playerController.queue.collectAsState()
                val lyrics by playerController.lyrics.collectAsState()
                val activeLyricIndex by playerController.activeLyricIndex.collectAsState()
                val automixEnabled by playerController.automixEnabled.collectAsState()

                var isFullPlayerVisible by remember { mutableStateOf(false) }

                val navController = rememberNavController()

                Box(modifier = Modifier.fillMaxSize()) {
                    if (token.isNullOrEmpty()) {
                        AuthScreen(
                            onLogin = { u, p -> viewModel.login(u, p) },
                            onRegister = { u, p, n, e -> viewModel.register(u, p, n, e) },
                            onSaveServerUrl = { url -> viewModel.saveServerUrl(url) },
                            currentServerUrl = serverUrl,
                            isLoading = isLoading,
                            errorMessage = errorMessage
                        )
                    } else {
                        Scaffold(
                            modifier = Modifier.fillMaxSize()
                        ) { innerPadding ->
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(innerPadding)
                            ) {
                                NavHost(
                                    navController = navController,
                                    startDestination = "home"
                                ) {
                                    composable("home") {
                                        HomeScreen(
                                            username = username,
                                            trendingTracks = trendingTracks,
                                            isLoading = isLoading,
                                            onTrackSelect = { track, list ->
                                                playerController.playTrack(track, list)
                                            },
                                            onNavigateSearch = { navController.navigate("search") },
                                            onLogout = { viewModel.logout() },
                                            serverHealthy = serverHealthy
                                        )
                                    }

                                    composable("search") {
                                        SearchScreen(
                                            onBack = { navController.popBackStack() },
                                            onSearch = { q -> viewModel.search(q) },
                                            searchResults = searchResults,
                                            isLoading = isLoading,
                                            onTrackSelect = { track, list ->
                                                playerController.playTrack(track, list)
                                            }
                                        )
                                    }
                                }

                                // Persistent MiniPlayer
                                if (currentTrack != null && !isFullPlayerVisible) {
                                    val progress = if (duration > 0) playbackPos.toFloat() / duration else 0f
                                    MiniPlayer(
                                        track = currentTrack!!,
                                        isPlaying = isPlaying,
                                        progress = progress,
                                        onTogglePlayPause = { playerController.togglePlayPause() },
                                        onSkipNext = { playerController.skipToNext() },
                                        onClick = { isFullPlayerVisible = true },
                                        modifier = Modifier.align(Alignment.BottomCenter)
                                    )
                                }
                            }
                        }

                        // Full Screen Glassmorphism Player Overlay
                        if (isFullPlayerVisible && currentTrack != null) {
                            PlayerScreen(
                                track = currentTrack!!,
                                isPlaying = isPlaying,
                                playbackPositionMs = playbackPos,
                                durationMs = duration,
                                isBuffering = isBuffering,
                                lyrics = lyrics,
                                activeLyricIndex = activeLyricIndex,
                                automixEnabled = automixEnabled,
                                queue = queue,
                                onTogglePlayPause = { playerController.togglePlayPause() },
                                onSeekTo = { pos -> playerController.seekTo(pos) },
                                onSkipNext = { playerController.skipToNext() },
                                onSkipPrevious = { playerController.skipToPrevious() },
                                onToggleAutomix = { playerController.toggleAutomix() },
                                onSelectQueueTrack = { t -> playerController.playTrack(t) },
                                onClose = { isFullPlayerVisible = false }
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        playerController.release()
        super.onDestroy()
    }
}
