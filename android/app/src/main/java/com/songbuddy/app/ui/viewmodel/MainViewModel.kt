package com.songbuddy.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.songbuddy.app.data.model.Track
import com.songbuddy.app.data.repository.SongBuddyRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class MainViewModel(private val repository: SongBuddyRepository) : ViewModel() {

    val tokenState: StateFlow<String?> = repository.tokenFlow.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubsubscribed(5000),
        initialValue = null
    )

    val usernameState: StateFlow<String?> = repository.usernameFlow.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubsubscribed(5000),
        initialValue = null
    )

    val serverUrlState: StateFlow<String> = repository.serverUrlFlow.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubsubscribed(5000),
        initialValue = "http://10.0.2.2:8000"
    )

    private val _trendingTracks = MutableStateFlow<List<Track>>(emptyList())
    val trendingTracks: StateFlow<List<Track>> = _trendingTracks.asStateFlow()

    private val _searchResults = MutableStateFlow<List<Track>>(emptyList())
    val searchResults: StateFlow<List<Track>> = _searchResults.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _serverHealthy = MutableStateFlow(true)
    val serverHealthy: StateFlow<Boolean> = _serverHealthy.asStateFlow()

    init {
        checkHealth()
        fetchTrending()
    }

    fun checkHealth() {
        viewModelScope.launch {
            val result = repository.checkHealth()
            _serverHealthy.value = result.isSuccess
        }
    }

    fun fetchTrending() {
        viewModelScope.launch {
            _isLoading.value = true
            val result = repository.getTrending()
            result.onSuccess {
                _trendingTracks.value = it
            }.onFailure {
                _errorMessage.value = it.message
            }
            _isLoading.value = false
        }
    }

    fun search(query: String) {
        if (query.isBlank()) {
            _searchResults.value = emptyList()
            return
        }
        viewModelScope.launch {
            _isLoading.value = true
            val result = repository.searchTracks(query)
            result.onSuccess {
                _searchResults.value = it
            }.onFailure {
                _errorMessage.value = it.message
            }
            _isLoading.value = false
        }
    }

    fun login(u: String, p: String) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            val result = repository.login(u, p)
            result.onFailure {
                _errorMessage.value = it.message
            }
            _isLoading.value = false
        }
    }

    fun register(u: String, p: String, n: String?, e: String?) {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            val result = repository.register(u, p, n, e)
            result.onSuccess {
                login(u, p)
            }.onFailure {
                _errorMessage.value = it.message
            }
            _isLoading.value = false
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
        }
    }

    fun saveServerUrl(url: String) {
        viewModelScope.launch {
            repository.tokenManager.saveServerUrl(url)
            checkHealth()
            fetchTrending()
        }
    }
}
