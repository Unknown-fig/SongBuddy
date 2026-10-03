package com.songbuddy.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.songbuddy.app.data.model.LyricsResponse
import com.songbuddy.app.data.model.Track
import com.songbuddy.app.ui.theme.DarkBackground
import com.songbuddy.app.ui.theme.DarkSurfaceVariant
import com.songbuddy.app.ui.theme.EmeraldPrimary
import kotlinx.coroutines.launch

@Composable
fun PlayerScreen(
    track: Track,
    isPlaying: Boolean,
    playbackPositionMs: Long,
    durationMs: Long,
    isBuffering: Boolean,
    lyrics: LyricsResponse?,
    activeLyricIndex: Int,
    automixEnabled: Boolean,
    queue: List<Track>,
    onTogglePlayPause: () -> Unit,
    onSeekTo: (Long) -> Unit,
    onSkipNext: () -> Unit,
    onSkipPrevious: () -> Unit,
    onToggleAutomix: () -> Unit,
    onSelectQueueTrack: (Track) -> Unit,
    onClose: () -> Unit
) {
    var showQueue by remember { mutableStateOf(false) }
    var showLyrics by remember { mutableStateOf(false) }

    val coroutineScope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    // Auto-scroll lyrics view when active line changes
    LaunchedEffect(activeLyricIndex) {
        if (showLyrics && activeLyricIndex >= 0 && lyrics?.lines?.isNotEmpty() == true) {
            coroutineScope.launch {
                listState.animateScrollToItem((activeLyricIndex - 2).coerceAtLeast(0))
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
    ) {
        // Blurred Album Art Background
        AsyncImage(
            model = track.thumbnail,
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .fillMaxSize()
                .blur(80.dp)
                .background(Color.Black.copy(alpha = 0.6f))
        )

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            Color.Black.copy(alpha = 0.3f),
                            DarkBackground.copy(alpha = 0.85f),
                            DarkBackground
                        )
                    )
                )
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Top Bar
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onClose) {
                    Icon(Icons.Default.KeyboardArrowDown, contentDescription = "Close", tint = Color.White, modifier = Modifier.size(32.dp))
                }

                Text(
                    text = if (showLyrics) "SYNCHRONIZED LYRICS" else if (showQueue) "AUTOMIX QUEUE" else "NOW PLAYING",
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp
                    ),
                    color = Color.LightGray
                )

                IconButton(onClick = { showQueue = !showQueue; if (showQueue) showLyrics = false }) {
                    Icon(
                        Icons.Default.QueueMusic,
                        contentDescription = "Queue",
                        tint = if (showQueue) EmeraldPrimary else Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (showQueue) {
                // Automix Queue View
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Automix Infinite Queue (${queue.size})",
                            style = MaterialTheme.typography.titleMedium,
                            color = Color.White,
                            fontWeight = FontWeight.Bold
                        )

                        TextButton(onClick = onToggleAutomix) {
                            Text(
                                text = if (automixEnabled) "Automix ON" else "Automix OFF",
                                color = if (automixEnabled) EmeraldPrimary else Color.Gray
                            )
                        }
                    }

                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        itemsIndexed(queue) { _, qTrack ->
                            val isCurrent = qTrack.id == track.id
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable { onSelectQueueTrack(qTrack) },
                                color = if (isCurrent) EmeraldPrimary.copy(alpha = 0.2f) else DarkSurfaceVariant.copy(alpha = 0.6f)
                            ) {
                                Row(
                                    modifier = Modifier.padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    AsyncImage(
                                        model = qTrack.thumbnail,
                                        contentDescription = qTrack.title,
                                        contentScale = ContentScale.Crop,
                                        modifier = Modifier
                                            .size(44.dp)
                                            .clip(RoundedCornerShape(8.dp))
                                    )
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = qTrack.title,
                                            fontWeight = FontWeight.Bold,
                                            color = if (isCurrent) EmeraldPrimary else Color.White,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                        Text(
                                            text = qTrack.artist,
                                            fontSize = 12.sp,
                                            color = Color.Gray,
                                            maxLines = 1
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            } else if (showLyrics) {
                // Synchronized Lyrics View
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                ) {
                    val lines = lyrics?.lines ?: emptyList()
                    if (lines.isEmpty()) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text(
                                text = lyrics?.plainLyrics ?: "No lyrics available for this track",
                                color = Color.Gray,
                                textAlign = TextAlign.Center,
                                modifier = Modifier.padding(16.dp)
                            )
                        }
                    } else {
                        LazyColumn(
                            state = listState,
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(vertical = 40.dp)
                        ) {
                            itemsIndexed(lines) { index, line ->
                                val isActive = index == activeLyricIndex
                                Text(
                                    text = line.text,
                                    style = MaterialTheme.typography.titleLarge.copy(
                                        fontWeight = if (isActive) FontWeight.ExtraBold else FontWeight.Medium,
                                        fontSize = if (isActive) 22.sp else 18.sp
                                    ),
                                    color = if (isActive) EmeraldPrimary else Color.White.copy(alpha = 0.5f),
                                    textAlign = TextAlign.Center,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 10.dp)
                                        .clickable {
                                            onSeekTo((line.timeSeconds * 1000).toLong())
                                        }
                                )
                            }
                        }
                    }
                }
            } else {
                // Main Artwork Player View
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    AsyncImage(
                        model = track.thumbnail ?: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300",
                        contentDescription = track.title,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier
                            .fillMaxWidth(0.85f)
                            .aspectRatio(1f)
                            .clip(RoundedCornerShape(24.dp))
                            .background(Color.DarkGray)
                    )

                    Spacer(modifier = Modifier.height(32.dp))

                    Text(
                        text = track.title,
                        style = MaterialTheme.typography.headlineSmall.copy(
                            fontWeight = FontWeight.Bold
                        ),
                        color = Color.White,
                        textAlign = TextAlign.Center,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = track.artist + if (!track.album.isNullOrEmpty()) " • ${track.album}" else "",
                        style = MaterialTheme.typography.bodyLarge,
                        color = Color.Gray,
                        textAlign = TextAlign.Center,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }

            // Lyrics Toggle Button
            IconButton(
                onClick = { showLyrics = !showLyrics; if (showLyrics) showQueue = false },
                modifier = Modifier.padding(bottom = 8.dp)
            ) {
                Icon(
                    Icons.Default.Subtitles,
                    contentDescription = "Lyrics",
                    tint = if (showLyrics) EmeraldPrimary else Color.Gray
                )
            }

            // Scrubber Bar
            Column(modifier = Modifier.fillMaxWidth()) {
                Slider(
                    value = if (durationMs > 0) playbackPositionMs.toFloat() / durationMs else 0f,
                    onValueChange = { frac ->
                        onSeekTo((frac * durationMs).toLong())
                    },
                    colors = SliderDefaults.colors(
                        thumbColor = EmeraldPrimary,
                        activeTrackColor = EmeraldPrimary,
                        inactiveTrackColor = Color.White.copy(alpha = 0.2f)
                    )
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = formatTime(playbackPositionMs),
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                    Text(
                        text = formatTime(durationMs),
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Transport Controls
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onToggleAutomix,
                    modifier = Modifier.size(48.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.AutoAwesome,
                        contentDescription = "Automix",
                        tint = if (automixEnabled) EmeraldPrimary else Color.Gray
                    )
                }

                IconButton(
                    onClick = onSkipPrevious,
                    modifier = Modifier.size(56.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.SkipPrevious,
                        contentDescription = "Previous",
                        tint = Color.White,
                        modifier = Modifier.size(36.dp)
                    )
                }

                Surface(
                    shape = CircleShape,
                    color = EmeraldPrimary,
                    modifier = Modifier
                        .size(64.dp)
                        .clip(CircleShape)
                        .clickable { onTogglePlayPause() }
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        if (isBuffering) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(28.dp),
                                color = Color.Black,
                                strokeWidth = 3.dp
                            )
                        } else {
                            Icon(
                                imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                                contentDescription = if (isPlaying) "Pause" else "Play",
                                tint = Color.Black,
                                modifier = Modifier.size(36.dp)
                            )
                        }
                    }
                }

                IconButton(
                    onClick = onSkipNext,
                    modifier = Modifier.size(56.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.SkipNext,
                        contentDescription = "Next",
                        tint = Color.White,
                        modifier = Modifier.size(36.dp)
                    )
                }

                IconButton(
                    onClick = { showQueue = !showQueue },
                    modifier = Modifier.size(48.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.QueueMusic,
                        contentDescription = "Queue",
                        tint = if (showQueue) EmeraldPrimary else Color.Gray
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

private fun formatTime(ms: Long): String {
    val totalSecs = ms / 1000
    val mins = totalSecs / 60
    val secs = totalSecs % 60
    return String.format("%d:%02d", mins, secs)
}
