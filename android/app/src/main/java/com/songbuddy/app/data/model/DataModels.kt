package com.songbuddy.app.data.model

import com.google.gson.annotations.SerializedName

data class Track(
    @SerializedName("id") val id: String,
    @SerializedName("title") val title: String,
    @SerializedName("artist") val artist: String,
    @SerializedName("album") val album: String? = null,
    @SerializedName("thumbnail") val thumbnail: String? = null,
    @SerializedName("duration") val duration: Any? = null, // Can be Int or String e.g. "3:45"
    @SerializedName("is_featured") val isFeatured: Boolean = false,
    @SerializedName("stream_url") val streamUrl: String? = null
) {
    fun getFormattedDuration(): String {
        return when (duration) {
            is Number -> {
                val seconds = duration.toLong()
                val mins = seconds / 60
                val secs = seconds % 60
                String.format("%d:%02d", mins, secs)
            }
            is String -> duration.ifEmpty { "--:--" }
            else -> "--:--"
        }
    }

    fun getDurationInSeconds(): Long {
        return when (duration) {
            is Number -> duration.toLong()
            is String -> {
                val parts = duration.split(":")
                if (parts.size == 2) {
                    val m = parts[0].toLongOrNull() ?: 0L
                    val s = parts[1].toLongOrNull() ?: 0L
                    m * 60 + s
                } else {
                    0L
                }
            }
            else -> 0L
        }
    }
}

data class LoginRequest(
    @SerializedName("username") val username: String,
    @SerializedName("password") val password: String
)

data class RegisterRequest(
    @SerializedName("username") val username: String,
    @SerializedName("password") val password: String,
    @SerializedName("name") val name: String? = null,
    @SerializedName("email") val email: String? = null
)

data class User(
    @SerializedName("username") val username: String,
    @SerializedName("name") val name: String? = null,
    @SerializedName("email") val email: String? = null
)

data class AuthResponse(
    @SerializedName("access_token") val accessToken: String? = null,
    @SerializedName("token_type") val tokenType: String? = null,
    @SerializedName("user") val user: User? = null,
    @SerializedName("message") val message: String? = null
)

data class LyricLine(
    @SerializedName("time") val timeSeconds: Double,
    @SerializedName("text") val text: String
)

data class LyricsResponse(
    @SerializedName("synced") val synced: Boolean = false,
    @SerializedName("plain_lyrics") val plainLyrics: String? = null,
    @SerializedName("lines") val lines: List<LyricLine> = emptyList()
)

data class HealthResponse(
    @SerializedName("status") val status: String,
    @SerializedName("service") val service: String? = null,
    @SerializedName("uptime_seconds") val uptimeSeconds: Double? = null,
    @SerializedName("memory_mb") val memoryMb: Double? = null
)
