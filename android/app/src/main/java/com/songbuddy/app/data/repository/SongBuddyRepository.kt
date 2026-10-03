package com.songbuddy.app.data.repository

import android.content.Context
import com.songbuddy.app.data.api.AuthInterceptor
import com.songbuddy.app.data.api.SongBuddyApi
import com.songbuddy.app.data.local.TokenManager
import com.songbuddy.app.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class SongBuddyRepository(private val context: Context) {

    val tokenManager = TokenManager(context)
    private var currentApi: SongBuddyApi? = null
    private var currentBaseUrl: String? = null

    val tokenFlow: Flow<String?> = tokenManager.tokenFlow
    val usernameFlow: Flow<String?> = tokenManager.usernameFlow
    val serverUrlFlow: Flow<String> = tokenManager.serverUrlFlow

    private suspend fun getApi(): SongBuddyApi {
        val baseUrl = tokenManager.getServerUrl()
        if (currentApi == null || currentBaseUrl != baseUrl) {
            currentBaseUrl = baseUrl
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            val client = OkHttpClient.Builder()
                .addInterceptor(AuthInterceptor(tokenManager))
                .addInterceptor(logging)
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(20, TimeUnit.SECONDS)
                .build()

            val retrofit = Retrofit.Builder()
                .baseUrl("$baseUrl/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            currentApi = retrofit.create(SongBuddyApi::class.java)
        }
        return currentApi!!
    }

    fun buildStreamUrl(videoId: String, baseUrl: String): String {
        return "$baseUrl/api/stream?id=$videoId"
    }

    suspend fun login(username: String, password: String): Result<AuthResponse> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().login(LoginRequest(username, password))
            if (response.isSuccessful && response.body() != null) {
                val body = response.body()!!
                if (!body.accessToken.isNullOrEmpty()) {
                    tokenManager.saveToken(body.accessToken, username)
                }
                Result.success(body)
            } else {
                Result.failure(Exception(response.errorBody()?.string() ?: "Login failed with code ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun register(username: String, password: String, name: String?, email: String?): Result<AuthResponse> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().register(RegisterRequest(username, password, name, email))
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception(response.errorBody()?.string() ?: "Registration failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            getApi().logout()
        } catch (_: Exception) {}
        tokenManager.clearToken()
        Result.success(Unit)
    }

    suspend fun getTrending(): Result<List<Track>> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().getTrending()
            if (response.isSuccessful) {
                Result.success(response.body() ?: emptyList())
            } else {
                Result.failure(Exception("Failed to load trending tracks (${response.code()})"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun searchTracks(query: String): Result<List<Track>> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().search(query)
            if (response.isSuccessful) {
                Result.success(response.body() ?: emptyList())
            } else {
                Result.failure(Exception("Search failed (${response.code()})"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getRadioQueue(videoId: String): Result<List<Track>> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().getRadio(videoId)
            if (response.isSuccessful) {
                Result.success(response.body() ?: emptyList())
            } else {
                Result.failure(Exception("Failed to fetch radio queue (${response.code()})"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getLyrics(track: String, artist: String, duration: Long?): Result<LyricsResponse> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().getLyrics(track, artist, duration)
            if (response.isSuccessful) {
                Result.success(response.body() ?: LyricsResponse())
            } else {
                Result.failure(Exception("Lyrics not available"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun checkHealth(): Result<HealthResponse> = withContext(Dispatchers.IO) {
        try {
            val response = getApi().getHealth()
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Server unhealthy"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
