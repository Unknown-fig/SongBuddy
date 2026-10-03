package com.songbuddy.app.player

import android.content.Context
import android.net.Uri
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import com.songbuddy.app.data.model.LyricLine
import com.songbuddy.app.data.model.LyricsResponse
import com.songbuddy.app.data.model.Track
import com.songbuddy.app.data.repository.SongBuddyRepository
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

@OptIn(UnstableApi::class)
class PlayerController(
    private val context: Context,
    private val repository: SongBuddyRepository
) {

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private var exoPlayer: ExoPlayer? = null

    private val _currentTrack = MutableStateFlow<Track?>(null)
    val currentTrack: StateFlow<Track?> = _currentTrack.asStateFlow()

    private val _isPlaying = MutableStateFlow(false)
    val isPlaying: StateFlow<Boolean> = _isPlaying.asStateFlow()

    private val _playbackPosition = MutableStateFlow(0L)
    val playbackPosition: StateFlow<Long> = _playbackPosition.asStateFlow()

    private val _duration = MutableStateFlow(0L)
    val duration: StateFlow<Long> = _duration.asStateFlow()

    private val _isBuffering = MutableStateFlow(false)
    val isBuffering: StateFlow<Boolean> = _isBuffering.asStateFlow()

    private val _queue = MutableStateFlow<List<Track>>(emptyList())
    val queue: StateFlow<List<Track>> = _queue.asStateFlow()

    private val _lyrics = MutableStateFlow<LyricsResponse?>(null)
    val lyrics: StateFlow<LyricsResponse?> = _lyrics.asStateFlow()

    private val _activeLyricIndex = MutableStateFlow(-1)
    val activeLyricIndex: StateFlow<Int> = _activeLyricIndex.asStateFlow()

    private val _automixEnabled = MutableStateFlow(true)
    val automixEnabled: StateFlow<Boolean> = _automixEnabled.asStateFlow()

    private var updatePositionJob: Job? = null

    init {
        setupPlayer()
    }

    private fun setupPlayer() {
        if (exoPlayer == null) {
            exoPlayer = ExoPlayer.Builder(context).build().apply {
                addListener(object : Player.Listener {
                    override fun onIsPlayingChanged(playing: Boolean) {
                        _isPlaying.value = playing
                        if (playing) {
                            startPositionUpdates()
                        } else {
                            stopPositionUpdates()
                        }
                    }

                    override fun onPlaybackStateChanged(state: Int) {
                        _isBuffering.value = (state == Player.STATE_BUFFERING)
                        if (state == Player.STATE_READY) {
                            _duration.value = exoPlayer?.duration?.coerceAtLeast(0L) ?: 0L
                        } else if (state == Player.STATE_ENDED) {
                            onTrackEnded()
                        }
                    }
                })
            }
        }
    }

    private fun startPositionUpdates() {
        stopPositionUpdates()
        updatePositionJob = scope.launch {
            while (isActive) {
                exoPlayer?.let { player ->
                    val pos = player.currentPosition.coerceAtLeast(0L)
                    _playbackPosition.value = pos
                    val dur = player.duration.coerceAtLeast(0L)
                    _duration.value = dur

                    // Sync active lyric line
                    updateActiveLyric(pos / 1000.0)
                }
                delay(250)
            }
        }
    }

    private fun stopPositionUpdates() {
        updatePositionJob?.cancel()
        updatePositionJob = null
    }

    private fun updateActiveLyric(currentTimeSec: Double) {
        val lines = _lyrics.value?.lines ?: return
        if (lines.isEmpty()) return

        var index = -1
        for (i in lines.indices) {
            if (lines[i].timeSeconds <= currentTimeSec) {
                index = i
            } else {
                break
            }
        }
        _activeLyricIndex.value = index
    }

    fun playTrack(track: Track, newQueue: List<Track> = emptyList()) {
        scope.launch {
            if (newQueue.isNotEmpty()) {
                _queue.value = newQueue
            } else if (!_queue.value.contains(track)) {
                _queue.value = _queue.value + track
            }

            _currentTrack.value = track
            _lyrics.value = null
            _activeLyricIndex.value = -1

            val baseUrl = repository.serverUrlFlow.value
            val token = repository.tokenManager.getToken() ?: ""
            val streamUrl = repository.buildStreamUrl(track.id, baseUrl)

            val metadata = MediaMetadata.Builder()
                .setTitle(track.title)
                .setArtist(track.artist)
                .setAlbumTitle(track.album ?: "SongBuddy")
                .setArtworkUri(track.thumbnail?.let { Uri.parse(it) })
                .build()

            val mediaItem = MediaItem.Builder()
                .setUri(streamUrl)
                .setMediaId(track.id)
                .setMediaMetadata(metadata)
                .build()

            exoPlayer?.run {
                stop()
                clearMediaItems()
                setMediaItem(mediaItem)
                prepare()
                play()
            }

            fetchLyricsForTrack(track)

            if (_automixEnabled.value && _queue.value.size <= 3) {
                fetchAutomixRadio(track.id)
            }
        }
    }

    private fun fetchLyricsForTrack(track: Track) {
        scope.launch {
            val result = repository.getLyrics(track.title, track.artist, track.getDurationInSeconds())
            result.onSuccess { lyricsResp ->
                _lyrics.value = lyricsResp
            }
        }
    }

    private fun fetchAutomixRadio(videoId: String) {
        scope.launch {
            val result = repository.getRadioQueue(videoId)
            result.onSuccess { newTracks ->
                val existingIds = _queue.value.map { it.id }.toSet()
                val filtered = newTracks.filterNot { existingIds.contains(it.id) }
                _queue.value = _queue.value + filtered
            }
        }
    }

    private fun onTrackEnded() {
        skipToNext()
    }

    fun togglePlayPause() {
        exoPlayer?.let { player ->
            if (player.isPlaying) {
                player.pause()
            } else {
                if (player.playbackState == Player.STATE_ENDED) {
                    player.seekTo(0)
                }
                player.play()
            }
        }
    }

    fun seekTo(positionMs: Long) {
        exoPlayer?.seekTo(positionMs)
        _playbackPosition.value = positionMs
    }

    fun skipToNext() {
        val q = _queue.value
        val current = _currentTrack.value ?: return
        val index = q.indexOfFirst { it.id == current.id }
        if (index >= 0 && index + 1 < q.size) {
            playTrack(q[index + 1])
        }
    }

    fun skipToPrevious() {
        val q = _queue.value
        val current = _currentTrack.value ?: return
        val index = q.indexOfFirst { it.id == current.id }
        if (index > 0) {
            playTrack(q[index - 1])
        } else {
            seekTo(0)
        }
    }

    fun toggleAutomix() {
        _automixEnabled.value = !_automixEnabled.value
    }

    fun release() {
        stopPositionUpdates()
        exoPlayer?.release()
        exoPlayer = null
        scope.cancel()
    }
}
