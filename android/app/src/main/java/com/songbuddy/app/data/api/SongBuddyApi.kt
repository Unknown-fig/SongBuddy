package com.songbuddy.app.data.api

import com.songbuddy.app.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface SongBuddyApi {

    @POST("/api/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("/api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @POST("/api/auth/logout")
    suspend fun logout(): Response<Map<String, String>>

    @GET("/api/trending")
    suspend fun getTrending(): Response<List<Track>>

    @GET("/api/search")
    suspend fun search(
        @Query("q") query: String,
        @Query("limit") limit: Int = 16
    ): Response<List<Track>>

    @GET("/api/radio")
    suspend fun getRadio(@Query("id") videoId: String): Response<List<Track>>

    @GET("/api/lyrics")
    suspend fun getLyrics(
        @Query("track") track: String,
        @Query("artist") artist: String = "",
        @Query("duration") duration: Long? = null
    ): Response<LyricsResponse>

    @GET("/api/health")
    suspend fun getHealth(): Response<HealthResponse>
}
