/**
 * SongBuddy Studio — Premium 3-Column Workstation ("Groovvy" UI Engine)
 * Client-side State Manager, Audio Driver & Interactive Player
 */

// ============================================================================
// State Definition
// ============================================================================
const state = {
  theme: localStorage.getItem('songbuddy_theme') || 'dark',
  currentTrack: null,
  isPlaying: false,
  queue: JSON.parse(localStorage.getItem('songbuddy_queue') || '[]'),
  radioQueue: [],
  radioLoading: false,
  radioRequestId: 0,
  sessionPlayedIds: [],
  autoplay: localStorage.getItem('songbuddy_autoplay') !== 'false',
  history: [],
  featuredTracks: [],
  likedTracks: JSON.parse(localStorage.getItem('songbuddy_liked_tracks') || '[]'),
  volume: parseFloat(localStorage.getItem('songbuddy_volume') || '0.8'),
  isMuted: false,
  isShuffle: false,
  isRepeat: false,
  activeView: 'home',
  lyrics: {
    synced: [],
    plain: '',
    activeIndex: -1,
    isOpen: false
  },
  karaokeMode: false,
  lyricsEventSource: null,
  searchDebounceTimer: null,
  lastSearchResults: [],
  activeSearchFilter: 'all',
  currentHeroIndex: 0,
  screenOffPlayback: localStorage.getItem('songbuddy_screenoff') !== 'false',
  keepScreenAwake: localStorage.getItem('songbuddy_keepawake') === 'true',
  user: JSON.parse(localStorage.getItem('songbuddy_user') || 'null'),
  equalizer: {
    enabled: localStorage.getItem('songbuddy_eq_enabled') !== 'false',
    preset: localStorage.getItem('songbuddy_eq_preset') || 'flat',
    bands: JSON.parse(localStorage.getItem('songbuddy_eq_bands') || '[0, 0, 0, 0, 0]')
  },
  playbackSpeed: parseFloat(localStorage.getItem('songbuddy_playback_speed') || '1.0'),
  sleepTimer: {
    active: false,
    mode: null,
    remainingSeconds: 0
  },
  audioEngine: {
    normalization: localStorage.getItem('songbuddy_normalization') === 'true',
    preampGain: parseFloat(localStorage.getItem('songbuddy_preamp') || '0'),
    spatialAudio: parseFloat(localStorage.getItem('songbuddy_spatial') || '0'),
    crossfadeSeconds: parseInt(localStorage.getItem('songbuddy_crossfade') || '0', 10),
    audiophilePassthrough: localStorage.getItem('songbuddy_audiophile') === 'true',
    showRemainingTime: localStorage.getItem('songbuddy_show_remaining') === 'true',
    repeatMode: localStorage.getItem('songbuddy_repeat_mode') || 'off', // 'off' | 'all' | 'one'
    quality: localStorage.getItem('songbuddy_quality') || 'high' // 'high' | 'low' | 'auto'
  },
  localLibrary: [],
  userPlaylists: [],
  smartPlaylists: { on_repeat: [], recently_played: [], jump_back_in: [] },
  offlineTracks: [],
  activeLibraryTab: 'favourites',
  listeningStats: JSON.parse(localStorage.getItem('songbuddy_listening_stats') || '{"tracksPlayed":0,"totalMinutes":0,"playCounts":{}}'),
  sponsorblock: {
    enabled: false,
    segments: [],
    skippedSegments: new Set(),
    bypassedStarts: new Set(),
    lastSkipped: null,
    undoTimeout: null
  },
  eightD: {
    enabled: localStorage.getItem('songbuddy_8d_enabled') === 'true',
    speed: parseFloat(localStorage.getItem('songbuddy_8d_speed') || '11')
  },
  networkResilience: {
    adaptiveBitrate: true,
    effectiveType: '4g',
    downlink: 10,
    isRecovering: false,
    recoveryTimeout: null
  },
  jukebox: {
    currentRoomCode: 'PARTY1',
    hostToken: localStorage.getItem('songbuddy_jukebox_host_PARTY1') || null,
    guestId: localStorage.getItem('songbuddy_jukebox_guest_id') || ('guest_' + Math.random().toString(36).substring(2, 10)),
    guestVotes: {},
    pollTimer: null,
    activeTab: 'host',
    autoAdvance: true
  },
  shareModal: {
    selectedHours: 24,
    allowDownload: true
  }
};

// ============================================================================
// Curated Data: Hero Slides, Top Artists & Initial Charts
// ============================================================================
const HERO_SLIDES = [
  {
    id: "kTJczUoc26U",
    title: "In My Feelings",
    artist: "Camila Cabello",
    plays: "63 Million Plays",
    tag: "Trending New Hits",
    image: "/assets/artists/camila_cabello.jpg",
    thumbnail: "/assets/artists/camila_cabello.jpg",
    duration_formatted: "3:40"
  },
  {
    id: "4NRXx6U8ABQ",
    title: "Blinding Lights",
    artist: "The Weeknd",
    plays: "95 Million Plays",
    tag: "Global Viral Top 1",
    image: "/assets/artists/the_weeknd.jpg",
    thumbnail: "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg",
    duration_formatted: "3:20"
  },
  {
    id: "TUVcZfQe-Kw",
    title: "Levitating",
    artist: "Dua Lipa",
    plays: "78 Million Plays",
    tag: "Retro Pop Anthem",
    image: "/assets/artists/dua_lipa.jpg",
    thumbnail: "https://i.ytimg.com/vi/TUVcZfQe-Kw/hqdefault.jpg",
    duration_formatted: "3:23"
  },
  {
    id: "0-7IHOXkiV8",
    title: "Butterfly Effect",
    artist: "Travis Scott",
    plays: "84 Million Plays",
    tag: "Astroworld Hit",
    image: "/assets/artists/travis_scott.jpg",
    thumbnail: "/assets/artists/travis_scott.jpg",
    duration_formatted: "3:10"
  }
];

const TOP_ARTISTS = [
  {
    name: "Travis Scott",
    plays: "44M Plays",
    avatar: "/assets/artists/travis_scott.jpg",
    search: "Travis Scott popular hits"
  },
  {
    name: "Billie Eilish",
    plays: "203M Plays",
    avatar: "/assets/artists/billie_eilish.jpg",
    search: "Billie Eilish hits"
  },
  {
    name: "The Weeknd",
    plays: "60M Plays",
    avatar: "/assets/artists/the_weeknd.jpg",
    search: "The Weeknd hits"
  },
  {
    name: "Kanye West",
    plays: "15M Plays",
    avatar: "/assets/artists/kanye_west.jpg",
    search: "Kanye West songs"
  },
  {
    name: "Nicki Minaj",
    plays: "100M Plays",
    avatar: "/assets/artists/nicki_minaj.jpg",
    search: "Nicki Minaj hits"
  },
  {
    name: "Dua Lipa",
    plays: "100M Plays",
    avatar: "/assets/artists/dua_lipa.jpg",
    search: "Dua Lipa popular songs"
  }
];

// Helper to safely get element
const $ = (id) => document.getElementById(id);

// Audio Engine Instance
let audio = null;
let ytPlayer = null;
let ytReady = false;
let isYTActive = false;
let pendingYTTrack = null;
let ytProgressInterval = null;

// YouTube Official Player Audio Driver (100% Genuine Songs, No IP Blocks, No Test Sounds)
window.onYouTubeIframeAPIReady = function() {
  try {
    ytPlayer = new YT.Player('yt-audio-player', {
      height: '120',
      width: '200',
      playerVars: {
        autoplay: 0,
        controls: 0,
        disablekb: 1,
        fs: 0,
        playsinline: 1,
        rel: 0,
        modestbranding: 1
      },
      events: {
        onReady: onYTPlayerReady,
        onStateChange: onYTPlayerStateChange,
        onError: onYTPlayerError
      }
    });
  } catch (err) {
    console.warn('[YT.Player init warning]:', err);
  }
};

function onYTPlayerReady() {
  ytReady = true;
  if (ytPlayer && typeof ytPlayer.setVolume === 'function') {
    ytPlayer.setVolume(state.volume * 100);
  }
  if (pendingYTTrack) {
    const t = pendingYTTrack;
    pendingYTTrack = null;
    playTrack(t);
  }
}

function onYTPlayerStateChange(event) {
  // 1 = PLAYING, 2 = PAUSED, 0 = ENDED, 3 = BUFFERING
  if (event.data === 1) {
    state.isPlaying = true;
    updatePlayPauseIcons(true);
    startYTProgressTracker();
    enableBackgroundAudioSession();
    if (state.currentTrack) updateMediaSession(state.currentTrack);
  } else if (event.data === 2) {
    // If paused because screen was locked / turned off, and screen-off playback is enabled:
    if (document.hidden && state.isPlaying && state.screenOffPlayback) {
      console.log('[SongBuddy] Screen turned off. Keeping audio active in background...');
      enableBackgroundAudioSession();
      if (ytPlayer && typeof ytPlayer.playVideo === 'function') {
        setTimeout(() => {
          if (state.isPlaying) {
            try { ytPlayer.playVideo(); } catch (e) {}
          }
        }, 80);
      }
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'playing';
      }
      return;
    }
    state.isPlaying = false;
    updatePlayPauseIcons(false);
    stopYTProgressTracker();
    stopBackgroundAudioSession();
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = 'paused';
    }
  } else if (event.data === 0) {
    stopYTProgressTracker();
    if (state.sleepTimer && state.sleepTimer.active && state.sleepTimer.mode === 'track') {
      triggerSleepTimerExecution();
      return;
    }
    if (state.isRepeat) {
      if (ytPlayer && typeof ytPlayer.seekTo === 'function') {
        ytPlayer.seekTo(0, true);
        ytPlayer.playVideo();
      }
    } else {
      playNextTrack(false);
    }
  }
}

function onYTPlayerError(e) {
  console.warn('[YouTube Player Error, falling back to native stream]:', e);
  isYTActive = false;
  stopYTProgressTracker();
  if (state.currentTrack) {
    const streamUrl = state.currentTrack.streamUrl || `/api/stream?id=${encodeURIComponent(state.currentTrack.id)}`;
    audio.src = streamUrl;
    audio.load();
    audio.play().then(() => updatePlayPauseIcons(true)).catch(console.warn);
  }
}

function updateProgressUI(cur, dur) {
  if ($('scrub-current-time')) $('scrub-current-time').textContent = formatTime(cur);
  if ($('cinema-current-time')) $('cinema-current-time').textContent = formatTime(cur);
  if (!isNaN(dur) && dur > 0) {
    if ($('scrub-total-time')) {
      if (state.audioEngine && state.audioEngine.showRemainingTime) {
        const rem = Math.max(0, dur - cur);
        $('scrub-total-time').textContent = `-${formatTime(rem)}`;
      } else {
        $('scrub-total-time').textContent = formatTime(dur);
      }
    }
    if ($('cinema-total-time')) $('cinema-total-time').textContent = formatTime(dur);
    const pct = (cur / dur) * 100;
    if ($('scrubber-played-bar')) $('scrubber-played-bar').style.width = `${pct}%`;
    const mobProg = $('mobile-mini-progress');
    if (mobProg) mobProg.style.width = `${pct}%`;
    const cinFill = $('cinema-scrubber-fill');
    if (cinFill) cinFill.style.width = `${pct}%`;
  }
  if (typeof checkCrossfadeTrigger === 'function') {
    checkCrossfadeTrigger(cur, dur);
  }
  if (typeof recordTrackListeningTelemetry === 'function' && state.currentTrack) {
    recordTrackListeningTelemetry(state.currentTrack, cur, dur);
  }
  updateLyricsSync(cur);
  syncMediaSessionPosition(cur, dur);
}

function startYTProgressTracker() {
  stopYTProgressTracker();
  ytProgressInterval = setInterval(() => {
    if (!isYTActive || !ytPlayer || typeof ytPlayer.getCurrentTime !== 'function') return;
    const cur = ytPlayer.getCurrentTime() || 0;
    const dur = ytPlayer.getDuration() || 0;
    updateProgressUI(cur, dur);
  }, 250);
}

function stopYTProgressTracker() {
  if (ytProgressInterval) {
    clearInterval(ytProgressInterval);
    ytProgressInterval = null;
  }
}

function seekPlayerTo(seconds) {
  if (isYTActive && ytPlayer && typeof ytPlayer.seekTo === 'function') {
    ytPlayer.seekTo(seconds, true);
  }
  if (audio && !isNaN(audio.duration) && audio.duration > 0) {
    audio.currentTime = seconds;
  }
}

// ============================================================================
// Network Resilience & Continuous Audio Playback
// Auto-skipping is disabled permanently to prevent buffer underruns and playback stutter
async function fetchTrackSponsorBlock(videoId) {
  state.sponsorblock.segments = [];
  state.sponsorblock.skippedSegments = new Set();
  state.sponsorblock.bypassedStarts = new Set();
  state.sponsorblock.lastSkipped = null;
}

function checkSponsorBlockSkip(curTime, dur) {
  // Disabled permanently: mid-song seeking breaks audio stream buffers and playback continuity
  return;
}

function showSponsorBlockToast(seg) {
  // Suppressed permanently: no skipping toasts shown
  return;
}

function revertSponsorBlockSkip() {
  return;
}

function toggleSponsorBlock() {
  state.sponsorblock.enabled = false;
  showToastNotification('Auto-skip is disabled to guarantee uninterrupted, crystal-clear audio');
}

async function triggerStreamRecovery(offset = 0) {
  if (state.networkResilience.isRecovering || !state.currentTrack || !state.currentTrack.id) return;
  state.networkResilience.isRecovering = true;

  const recoveryToast = $('stream-recovery-toast');
  const recoveryMsg = $('stream-recovery-msg');
  if (recoveryToast && recoveryMsg) {
    recoveryMsg.textContent = 'Refreshing stream token via CDN recovery...';
    recoveryToast.classList.remove('hidden');
  }

  const cleanOffset = Math.max(0, Math.floor(offset));
  try {
    const res = await fetch(`/api/stream/refresh?id=${encodeURIComponent(state.currentTrack.id)}&offset=${cleanOffset}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data && data.stream_url && audio) {
      console.log('[CDN Recovery] Successfully received fresh playback URL.');
      audio.src = data.stream_url;
      audio.load();

      const onCanPlay = () => {
        audio.removeEventListener('canplay', onCanPlay);
        try {
          if (cleanOffset > 0) audio.currentTime = cleanOffset;
          audio.play().then(() => updatePlayPauseIcons(true)).catch(console.warn);
        } catch (e) {
          console.warn('[CDN Recovery Playback Error]:', e);
        }
      };
      audio.addEventListener('canplay', onCanPlay);

      if (recoveryMsg) recoveryMsg.textContent = 'Resumed stream via CDN token recovery';
      setTimeout(() => {
        if (recoveryToast) recoveryToast.classList.add('hidden');
      }, 3000);
      return;
    }
  } catch (err) {
    console.warn('[CDN Recovery] Token refresh failed:', err);
    if (recoveryToast) recoveryToast.classList.add('hidden');
    if (ytPlayer && typeof ytPlayer.loadVideoById === 'function') {
      isYTActive = true;
      ytPlayer.loadVideoById(state.currentTrack.id, cleanOffset);
      ytPlayer.playVideo();
      updatePlayPauseIcons(true);
      startYTProgressTracker();
    }
  } finally {
    state.networkResilience.isRecovering = false;
  }
}

function setupNetworkResilience() {
  if ('connection' in navigator && navigator.connection) {
    const conn = navigator.connection;
    const updateConn = () => {
      state.networkResilience.effectiveType = conn.effectiveType || '4g';
      state.networkResilience.downlink = conn.downlink || 10;
      const statusEl = $('sidebar-network-status');
      if (conn.effectiveType === '2g' || conn.effectiveType === 'slow-2g') {
        state.audioEngine.quality = 'low';
        if (statusEl) {
          statusEl.innerHTML = '<span class="online-dot" style="background:#eab308;"></span> Adaptive Opus • 48–64kbps';
        }
      } else {
        if (statusEl) {
          statusEl.innerHTML = '<span class="online-dot"></span> Direct Opus • 160kbps';
        }
      }
    };
    conn.addEventListener('change', updateConn);
    updateConn();
  }

  fetch('/api/health/cookies')
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (data && $('label-cookie-health')) {
        const score = data.health_score ?? (data.status === 'healthy' ? 100 : 75);
        $('label-cookie-health').textContent = `Session Shield: ${score}% (${data.status})`;
      }
    })
    .catch(() => {});
}


// ============================================================================
// Authentication & User Presets
// ============================================================================
const DEFAULT_USER = {
  id: 'usr_dave_cooper',
  name: 'Dave Cooper',
  email: 'dave@songbuddy.studio',
  avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
  plan: 'Hi-Fi Studio VIP'
};const SPOTIFY_USER = {
  id: 'usr_alex_rivera',
  name: 'Alex Rivera',
  email: 'alex.rivera@songbuddy.studio',
  avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
  plan: 'Hi-Fi Studio VIP'
};

const GOOGLE_USER = {
  id: 'usr_google_dave',
  name: 'Dave Cooper',
  email: 'dave.cooper@songbuddy.studio',
  avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80',
  plan: 'Hi-Fi Studio VIP'
};

let toastTimer = null;
function showToastNotification(message) {
  let toast = $('songbuddy-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'songbuddy-toast';
    toast.className = 'songbuddy-toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>${message}</span>`;
  toast.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove('visible');
  }, 3200);
}

function checkAuthState() {
  const overlay = $('auth-overlay');
  const user = state.user;

  // Always keep overlay hidden by default on state check so guest users are never blocked
  overlay?.classList.add('hidden');

  if (user) {
    const cleanName = user.name ? user.name.replace(/\s*\([^)]*\)/g, '').trim() : 'Listener';
    if ($('user-name')) $('user-name').textContent = cleanName;
    if ($('user-avatar')) $('user-avatar').src = user.avatar;
    if ($('dropdown-user-name')) $('dropdown-user-name').textContent = cleanName;
    if ($('dropdown-user-email')) $('dropdown-user-email').textContent = user.email;
    if ($('dropdown-avatar')) $('dropdown-avatar').src = user.avatar;
    if ($('made-for-user-heading')) $('made-for-user-heading').textContent = `Curated Flow for ${cleanName.split(' ')[0] || cleanName}`;
  } else {
    if ($('user-name')) $('user-name').textContent = 'Guest';
    if ($('user-avatar')) $('user-avatar').src = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80';
    if ($('dropdown-user-name')) $('dropdown-user-name').textContent = 'Guest Listener';
    if ($('dropdown-user-email')) $('dropdown-user-email').textContent = 'Click to sign in';
    if ($('made-for-user-heading')) $('made-for-user-heading').textContent = 'Curated Stations For You';
  }
}

function openAuthModal() {
  const overlay = $('auth-overlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
  }
}

function closeAuthModal() {
  const overlay = $('auth-overlay');
  if (overlay) {
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
  }
}

function loginUser(userData, remember = true) {
  state.user = userData;
  if (remember) {
    localStorage.setItem('songbuddy_user', JSON.stringify(userData));
  } else {
    sessionStorage.setItem('songbuddy_user', JSON.stringify(userData));
  }
  closeAuthModal();
  checkAuthState();
  closeUserDropdown();
  showToastNotification(`Welcome back, ${userData.name}!`);
}

function logoutUser() {
  state.user = null;
  localStorage.removeItem('songbuddy_user');
  sessionStorage.removeItem('songbuddy_user');
  closeUserDropdown();
  closeAuthModal();
  checkAuthState();
  showToastNotification('Logged out of SongBuddy Studio');
}

function closeUserDropdown() {
  $('user-profile-container')?.classList.remove('open');
  $('user-dropdown-menu')?.classList.add('hidden');
}

function toggleUserDropdown() {
  const container = $('user-profile-container');
  const menu = $('user-dropdown-menu');
  if (!menu || !container) return;
  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    container.classList.add('open');
  } else {
    menu.classList.add('hidden');
    container.classList.remove('open');
  }
}

function showAuthAlert(msg, type = 'error') {
  const alertBox = $('auth-alert');
  if (!alertBox) return;
  alertBox.className = `auth-alert ${type}`;
  alertBox.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
      ${type === 'error' 
        ? '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>' 
        : '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'}
    </svg>
    <span>${msg}</span>
  `;
  alertBox.classList.remove('hidden');
}

function hideAuthAlert() {
  const alertBox = $('auth-alert');
  if (alertBox) alertBox.classList.add('hidden');
}

function setAuthMode(mode) {
  const tabSignIn = $('tab-sign-in');
  const tabRegister = $('tab-register');
  const nameGroup = $('field-name-group');
  const submitText = $('btn-auth-submit-text');
  const emailLabel = $('auth-label-email');

  hideAuthAlert();

  if (mode === 'register') {
    tabSignIn?.classList.remove('active');
    tabSignIn?.setAttribute('aria-selected', 'false');
    tabRegister?.classList.add('active');
    tabRegister?.setAttribute('aria-selected', 'true');
    nameGroup?.classList.remove('hidden');
    if ($('auth-input-name')) $('auth-input-name').required = true;
    if (submitText) submitText.textContent = 'Create SongBuddy Account';
    if (emailLabel) emailLabel.textContent = 'Email Address';
  } else {
    tabRegister?.classList.remove('active');
    tabRegister?.setAttribute('aria-selected', 'false');
    tabSignIn?.classList.add('active');
    tabSignIn?.setAttribute('aria-selected', 'true');
    nameGroup?.classList.add('hidden');
    if ($('auth-input-name')) $('auth-input-name').required = false;
    if (submitText) submitText.textContent = 'Sign In to SongBuddy';
    if (emailLabel) emailLabel.textContent = 'Email or Username';
  }
}

function handleAuthFormSubmit() {
  const isRegister = $('tab-register')?.classList.contains('active');
  const emailInput = $('auth-input-email');
  const pwInput = $('auth-input-password');
  const nameInput = $('auth-input-name');
  const remember = $('auth-remember-me')?.checked ?? true;

  const emailVal = emailInput?.value.trim();
  const pwVal = pwInput?.value;

  if (!emailVal || !pwVal) {
    showAuthAlert('Please enter both email and password.');
    return;
  }

  if (pwVal.length < 4) {
    showAuthAlert('Password must be at least 4 characters.');
    return;
  }

  if (isRegister) {
    const nameVal = nameInput?.value.trim() || emailVal.split('@')[0];
    const newUser = {
      id: 'usr_' + Date.now(),
      name: nameVal,
      email: emailVal.includes('@') ? emailVal : `${emailVal}@songbuddy.studio`,
      avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80',
      plan: 'Hi-Fi Studio Member'
    };
    loginUser(newUser, remember);
  } else {
    const displayName = emailVal.includes('@') ? emailVal.split('@')[0] : emailVal;
    const formattedName = displayName.charAt(0).toUpperCase() + displayName.slice(1);
    const user = {
      id: 'usr_' + Math.random().toString(36).substring(2, 9),
      name: formattedName,
      email: emailVal.includes('@') ? emailVal : `${emailVal}@songbuddy.studio`,
      avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
      plan: 'Hi-Fi Studio VIP'
    };
    loginUser(user, remember);
  }
}

// ============================================================================
// Theme Management & Dynamic Toasts
// ============================================================================
function initTheme() {
  if (!localStorage.getItem('songbuddy_theme_v2')) {
    localStorage.setItem('songbuddy_theme', 'dark');
    localStorage.setItem('songbuddy_theme_v2', 'true');
  }
  const savedTheme = localStorage.getItem('songbuddy_theme') || 'dark';
  setTheme(savedTheme, false);
}

function setTheme(themeName, showToast = true) {
  state.theme = themeName;
  document.documentElement.setAttribute('data-theme', themeName);
  localStorage.setItem('songbuddy_theme', themeName);

  const iconSage = $('theme-icon-sage');
  const iconDark = $('theme-icon-dark');
  const themeText = $('theme-text');

  if (themeName === 'neumorphic') {
    iconSage?.classList.add('hidden');
    iconDark?.classList.remove('hidden');
    if (themeText) themeText.textContent = 'Obsidian';
  } else {
    iconSage?.classList.remove('hidden');
    iconDark?.classList.add('hidden');
    if (themeText) themeText.textContent = 'Sage Clay';
  }

  if (showToast) {
    showToastNotification(themeName === 'neumorphic' ? 'Neumorphic Sage Theme Activated' : 'Obsidian Dark Theme Activated');
  }
}

function toggleTheme() {
  const nextTheme = state.theme === 'neumorphic' ? 'dark' : 'neumorphic';
  setTheme(nextTheme, true);
}

function showToastNotification(message, duration = 2800) {
  let toast = $('app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.className = 'app-toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `
    <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16" style="flex-shrink:0;">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
    </svg>
    <span>${escapeHTML(message)}</span>
  `;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

// ============================================================================
// Initialization
// ============================================================================
async function initApp() {
  // Initialize theme mode
  initTheme();

  audio = $('audio-engine');
  if (!audio) {
    audio = document.createElement('audio');
    audio.id = 'audio-engine';
    audio.preload = 'auto';
    document.body.appendChild(audio);
  }

  // Check auth state & show login if unauthenticated
  checkAuthState();

  // Set initial volume
  audio.volume = state.volume;
  if ($('volume-slider')) $('volume-slider').value = state.volume;

  // Render static components FIRST
  renderTopArtists();
  updateHeroSlide(0);

  // Set default player preview
  setTrackPreview(HERO_SLIDES[3]); // Butterfly Effect by default

  // Attach event listeners safely
  setupEventListeners();
  setupAudioListeners();
  setupMediaSession();
  updateScreenOffUI();
  initPWA();
  initAudioSuiteUI();
  initSubsonicUI();
  initJukeboxUI();
  initShareLinkUI();
  handleUrlRouting();
  window.addEventListener('hashchange', handleUrlRouting);
  setupNetworkResilience();

  // Initialize IndexedDB Offline Storage & Synchronize User Library
  OfflineDB.init().catch(console.warn);
  syncUserLibrary().catch(console.warn);
  setAudioQuality(state.audioEngine.quality || 'high');

  // Load live trending tracks from server
  await loadTrendingTracks();
  renderLikedTracks();

  // Initialize Queue UI badge & state
  updateQueueBadge();

  // Rotate Hero slide every 10 seconds if not currently playing
  setInterval(() => {
    if (!state.isPlaying) {
      const nextIdx = (state.currentHeroIndex + 1) % HERO_SLIDES.length;
      updateHeroSlide(nextIdx);
    }
  }, 10000);
}

// ============================================================================
// Hero Spotlight Slider Logic
// ============================================================================
function updateHeroSlide(index) {
  state.currentHeroIndex = index;
  const slide = HERO_SLIDES[index];
  if (!slide) return;

  if ($('hero-title')) $('hero-title').textContent = slide.title;
  if ($('hero-artist')) $('hero-artist').textContent = slide.artist;
  if ($('hero-plays')) $('hero-plays').textContent = slide.plays;
  if ($('hero-artist-img')) $('hero-artist-img').src = slide.image;

  document.querySelectorAll('.h-dot').forEach((dot, idx) => {
    dot.classList.toggle('active', idx === index);
  });

  // Check liked status
  const isLiked = state.likedTracks.some(t => t.id === slide.id);
  $('hero-heart-btn')?.classList.toggle('liked', isLiked);
}

// ============================================================================
// Top Artists Rendering
// ============================================================================
function renderTopArtists() {
  const container = $('artists-row');
  if (!container) return;
  container.innerHTML = '';

  TOP_ARTISTS.forEach(artist => {
    const card = document.createElement('div');
    card.className = 'artist-card';
    card.innerHTML = `
      <div class="artist-avatar-wrapper">
        <img src="${artist.avatar}" alt="${artist.name}" class="artist-avatar" loading="lazy">
      </div>
      <span class="artist-name">${artist.name}</span>
      <span class="artist-plays">${artist.plays}</span>
    `;
    card.addEventListener('click', () => {
      const input = $('search-input');
      if (input) input.value = artist.search;
      handleSearch(artist.search);
      switchView('search');
    });
    container.appendChild(card);
  });
}

// ============================================================================
// Trending Tracks & Top Charts
// ============================================================================
async function loadTrendingTracks() {
  try {
    const res = await fetch('/api/trending');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const tracks = await res.json();
    state.featuredTracks = tracks;
    renderTopCharts(tracks);
  } catch (err) {
    console.warn('[Error loading trending tracks]:', err);
    // Use fallback sample charts
    const fallbacks = [
      { id: "4NRXx6U8ABQ", title: "Blinding Lights", artist: "The Weeknd", duration_formatted: "3:20", thumbnail: "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg" },
      { id: "kTJczUoc26U", title: "STAY", artist: "The Kid LAROI, Justin Bieber", duration_formatted: "2:21", thumbnail: "https://i.ytimg.com/vi/kTJczUoc26U/hqdefault.jpg" },
      { id: "0-7IHOXkiV8", title: "Way Down We Go", artist: "KALEO", duration_formatted: "3:39", thumbnail: "https://i.ytimg.com/vi/0-7IHOXkiV8/hqdefault.jpg" },
      { id: "TUVcZfQe-Kw", title: "Levitating", artist: "Dua Lipa", duration_formatted: "3:23", thumbnail: "https://i.ytimg.com/vi/TUVcZfQe-Kw/hqdefault.jpg" },
      { id: "34Na4j8AVgA", title: "Starboy", artist: "The Weeknd ft. Daft Punk", duration_formatted: "3:50", thumbnail: "https://i.ytimg.com/vi/34Na4j8AVgA/hqdefault.jpg" }
    ];
    renderTopCharts(fallbacks);
  }
}

function renderTopCharts(tracks) {
  const container = $('top-charts-list');
  if (!container) return;
  container.innerHTML = '';

  tracks.slice(0, 6).forEach((track, index) => {
    const row = createTrackRow(track, index + 1);
    container.appendChild(row);
  });
}

function createTrackRow(track, rankNumber) {
  const row = document.createElement('div');
  row.className = 'chart-row';
  if (state.currentTrack && state.currentTrack.id === track.id) {
    row.classList.add('active');
  }

  let thumb = track.thumbnail || generateFallbackCover(track.title, track.artist);
  if (thumb.includes('hq720.jpg')) {
    thumb = thumb.replace('hq720.jpg', 'hqdefault.jpg');
  }
  const duration = track.duration_formatted || '3:30';
  const rank = String(rankNumber).padStart(2, '0');

  row.innerHTML = `
    <span class="chart-rank">${rank}</span>
    <img src="${thumb}" alt="${escapeHTML(track.title)}" class="chart-thumb" loading="lazy" onerror="if(this.src.includes('hq720.jpg')){this.src=this.src.replace('hq720.jpg','hqdefault.jpg');}else{this.onerror=null;this.src=generateFallbackCover('${escapeHTML(track.title)}','${escapeHTML(track.artist)}');}">
    <div class="chart-info">
      <span class="chart-title">${escapeHTML(track.title)}</span>
      <span class="chart-artist">${escapeHTML(track.artist)}</span>
    </div>
    <span class="chart-time">${duration}</span>
    <button class="chart-offline-btn" title="Download for Offline Play" aria-label="Save Offline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
    </button>
    <button class="chart-queue-btn" title="Add to Queue" aria-label="Add to Queue">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
    </button>
    <button class="chart-play-icon" title="Play" aria-label="Play Track">
      <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
    </button>
  `;

  // Attach offline download listener
  const offlineBtn = row.querySelector('.chart-offline-btn');
  offlineBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    OfflineDB.saveTrack(track);
  });

  // Attach queue button listener with stopPropagation to prevent auto-play
  const queueBtn = row.querySelector('.chart-queue-btn');
  queueBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    addToQueue(track);
  });

  row.addEventListener('click', () => {
    playTrack(track);
  });

  return row;
}

// ============================================================================
// Queue Management (Workstation "Up Next" Queue Engine)
// ============================================================================
function saveQueueToStorage() {
  try {
    localStorage.setItem('songbuddy_queue', JSON.stringify(state.queue));
  } catch (err) {
    console.warn('[Storage error]:', err);
  }
}

function addToQueue(track, silent = false) {
  if (!track || !track.id) return;

  const trackObj = {
    id: track.id,
    title: track.title || 'Unknown Title',
    artist: track.artist || 'Unknown Artist',
    thumbnail: track.thumbnail || '',
    duration_formatted: track.duration_formatted || '3:30',
    streamUrl: track.streamUrl || ''
  };

  state.queue.push(trackObj);
  saveQueueToStorage();
  updateQueueBadge();
  renderQueueDrawer();

  if (!silent) {
    showToastNotification(`Added "${trackObj.title}" to queue`);
  }
}

function removeFromQueue(index) {
  if (index >= 0 && index < state.queue.length) {
    const removed = state.queue.splice(index, 1)[0];
    saveQueueToStorage();
    updateQueueBadge();
    renderQueueDrawer();
    showToastNotification(`Removed "${removed?.title || 'track'}" from queue`);
  }
}

function clearQueue() {
  if (!state.queue || state.queue.length === 0) return;
  state.queue = [];
  saveQueueToStorage();
  updateQueueBadge();
  renderQueueDrawer();
  showToastNotification('Queue cleared');
}

function removeFromRadioQueue(index) {
  if (state.radioQueue && index >= 0 && index < state.radioQueue.length) {
    const removed = state.radioQueue.splice(index, 1)[0];
    updateQueueBadge();
    renderQueueDrawer();
    showToastNotification(`Removed "${removed?.title || 'track'}" from recommendations`);
  }
}

function clearRadioQueue() {
  if (!state.radioQueue || state.radioQueue.length === 0) return;
  state.radioQueue = [];
  updateQueueBadge();
  renderQueueDrawer();
  showToastNotification('Auto recommendations cleared');
}

function playQueuedTrack(index) {
  if (index >= 0 && index < state.queue.length) {
    const track = state.queue.splice(index, 1)[0];
    saveQueueToStorage();
    updateQueueBadge();
    renderQueueDrawer();
    playTrack(track, { startRadio: false });
  }
}

function updateQueueBadge() {
  const badge = $('queue-count-badge');
  const count = state.queue ? state.queue.length : 0;
  if (badge) {
    badge.textContent = count;
    badge.classList.toggle('hidden', count === 0);
  }

  const pill = $('queue-pill-count');
  if (pill) {
    const autoCount = state.radioQueue ? state.radioQueue.length : 0;
    if (count > 0 && autoCount > 0) {
      pill.textContent = `${count} queued • ${autoCount} auto`;
    } else if (count > 0) {
      pill.textContent = `${count} ${count === 1 ? 'track' : 'tracks'}`;
    } else if (autoCount > 0) {
      pill.textContent = `${autoCount} recommended`;
    } else {
      pill.textContent = '0 tracks';
    }
  }
}

function openQueueDrawer() {
  const overlay = $('queue-drawer-overlay');
  if (!overlay) return;
  $('pwa-install-toast')?.classList.add('hidden');
  overlay.classList.remove('hidden');
  updateDockActive('dock-btn-queue');
  renderQueueDrawer();
}

function closeQueueDrawer() {
  const overlay = $('queue-drawer-overlay');
  if (overlay) {
    overlay.classList.add('hidden');
  }
  if (state.activeView === 'home' && window.innerWidth > 768) {
    updateDockActive('dock-btn-home');
  } else {
    updateDockActive('dock-btn-music');
  }
}

// ============================================================================
// Search Bar Expansion, Suggestions & Mobile Discovery Drawer
// ============================================================================
const RECENT_SEARCHES_KEY = 'songbuddy_recent_searches';
let mobileSearchDebounce = null;
let desktopSearchDebounce = null;
let desktopSearchAbort = null;

function getRecentSearches() {
  try {
    const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function saveRecentSearch(query) {
  if (!query || !query.trim()) return;
  const clean = query.trim();
  try {
    let list = getRecentSearches().filter(q => q.toLowerCase() !== clean.toLowerCase());
    list.unshift(clean);
    if (list.length > 8) list = list.slice(0, 8);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(list));
    renderDesktopRecentSearches();
  } catch (e) {}
}

function removeRecentSearch(query) {
  try {
    let list = getRecentSearches().filter(q => q.toLowerCase() !== query.toLowerCase());
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(list));
    renderDesktopRecentSearches();
  } catch (e) {}
}

function clearAllRecentSearches() {
  try {
    localStorage.removeItem(RECENT_SEARCHES_KEY);
    renderDesktopRecentSearches();
  } catch (e) {}
}

function renderDesktopRecentSearches() {
  const listEl = $('desktop-recent-list');
  const sectionEl = $('desktop-recent-section');
  if (!listEl || !sectionEl) return;
  const recent = getRecentSearches();
  if (recent.length === 0) {
    sectionEl.classList.add('hidden');
    listEl.innerHTML = '';
    return;
  }
  sectionEl.classList.remove('hidden');
  listEl.innerHTML = '';
  recent.forEach(item => {
    const li = document.createElement('li');
    li.className = 'recent-search-item';
    li.innerHTML = `
      <div class="recent-search-query">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" style="color:#64748b;flex-shrink:0;">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        <span>${escapeHTML(item)}</span>
      </div>
      <button type="button" class="recent-search-remove" title="Remove" aria-label="Remove">&times;</button>
    `;
    li.querySelector('.recent-search-query')?.addEventListener('click', () => {
      const input = $('search-input');
      if (input) input.value = item;
      handleSearch(item, true);
      closeDesktopSearchDropdown();
    });
    li.querySelector('.recent-search-remove')?.addEventListener('click', (e) => {
      e.stopPropagation();
      removeRecentSearch(item);
    });
    listEl.appendChild(li);
  });
}

function openDesktopSearchDropdown() {
  const popover = $('search-dropdown-popover');
  const wrapper = $('search-box-wrapper');
  if (!popover || !wrapper) return;
  wrapper.classList.add('is-expanded');
  popover.classList.remove('hidden');
  renderDesktopRecentSearches();

  const inputVal = ($('search-input')?.value || '').trim();
  if (inputVal) {
    searchDesktopInstantMatches(inputVal);
  } else {
    $('desktop-live-results-section')?.classList.add('hidden');
  }
}

function closeDesktopSearchDropdown() {
  const popover = $('search-dropdown-popover');
  const wrapper = $('search-box-wrapper');
  if (wrapper) wrapper.classList.remove('is-expanded');
  if (popover) popover.classList.add('hidden');
}

async function searchDesktopInstantMatches(query) {
  const section = $('desktop-live-results-section');
  const container = $('desktop-live-results');
  if (!section || !container) return;

  if (!query || !query.trim()) {
    section.classList.add('hidden');
    container.innerHTML = '';
    return;
  }

  if (desktopSearchAbort) desktopSearchAbort.abort();
  desktopSearchAbort = new AbortController();

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query.trim())}&limit=5`, {
      signal: desktopSearchAbort.signal
    });
    if (!res.ok) return;
    const tracks = await res.json();
    if (Array.isArray(tracks) && tracks.length > 0) {
      section.classList.remove('hidden');
      container.innerHTML = '';
      tracks.slice(0, 5).forEach(t => {
        const item = document.createElement('div');
        item.className = 'desktop-live-result-item';
        const thumb = t.thumbnail || generateFallbackCover(t.title, t.artist);
        const duration = t.duration_formatted || '3:30';
        item.innerHTML = `
          <img src="${thumb}" alt="${escapeHTML(t.title)}" class="desktop-live-thumb" onerror="if(this.src.includes('hq720.jpg')){this.src=this.src.replace('hq720.jpg','hqdefault.jpg');}else{this.onerror=null;this.src=generateFallbackCover('${escapeHTML(t.title)}','${escapeHTML(t.artist)}');}">
          <div class="desktop-live-meta">
            <span class="desktop-live-title">${escapeHTML(t.title)}</span>
            <span class="desktop-live-artist">${escapeHTML(t.artist || 'Artist')}</span>
          </div>
          <span class="desktop-live-duration">${duration}</span>
        `;
        item.addEventListener('click', () => {
          saveRecentSearch(query);
          playTrack(t);
          closeDesktopSearchDropdown();
          showToastNotification(`Playing: ${t.title}`);
        });
        container.appendChild(item);
      });
    } else {
      section.classList.add('hidden');
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      section.classList.add('hidden');
    }
  }
}

function openMobileSearch(initialQuery = '') {
  const overlay = $('mobile-search-drawer');
  const card = $('mobile-search-card');
  if (!overlay) return;
  $('pwa-install-toast')?.classList.add('hidden');
  overlay.classList.remove('hidden');
  updateDockActive('dock-btn-search');

  if (card) {
    card.style.transform = '';
  }

  const input = $('mobile-search-input');
  if (input) {
    if (initialQuery) {
      input.value = initialQuery;
      searchMobileMusic(initialQuery);
    } else if (!input.value.trim()) {
      renderMobileSearchResults(HERO_SLIDES, 'Trending Hits (Tap to play)');
    }
    setTimeout(() => {
      input.focus();
      if (input.value) {
        input.select();
      }
      card?.classList.add('is-full-height');
    }, 120);
  }
}

function closeMobileSearch() {
  const overlay = $('mobile-search-drawer');
  const card = $('mobile-search-card');
  if (card) {
    card.classList.remove('is-full-height');
    card.style.transform = '';
  }
  if (overlay) {
    overlay.classList.add('hidden');
  }
  if (state.activeView === 'home') {
    updateDockActive('dock-btn-home');
  } else if (state.activeView === 'search') {
    updateDockActive('dock-btn-search');
  } else {
    updateDockActive('dock-btn-music');
  }
}

function initMobileSearchGestures() {
  const card = $('mobile-search-card');
  const handle = $('mobile-search-drag-handle');
  if (!card) return;

  let startY = 0;
  let currentY = 0;
  let isDragging = false;

  const target = handle || card;

  target.addEventListener('touchstart', (e) => {
    if (e.touches.length !== 1) return;
    startY = e.touches[0].clientY;
    currentY = startY;
    isDragging = true;
    card.style.transition = 'none';
  }, { passive: true });

  target.addEventListener('touchmove', (e) => {
    if (!isDragging) return;
    currentY = e.touches[0].clientY;
    const deltaY = currentY - startY;
    if (deltaY > 0) {
      card.style.transform = `translateY(${deltaY}px)`;
    }
  }, { passive: true });

  target.addEventListener('touchend', () => {
    if (!isDragging) return;
    isDragging = false;
    card.style.transition = 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)';
    const deltaY = currentY - startY;
    if (deltaY > 70) {
      card.style.transform = 'translateY(100%)';
      setTimeout(() => closeMobileSearch(), 200);
    } else {
      card.style.transform = 'translateY(0)';
    }
  });
}

let mobileSearchAbort = null;

async function searchMobileMusic(query) {
  const statusEl = $('mobile-search-status');
  const resultsEl = $('mobile-search-results');
  const clearBtn = $('mobile-search-clear');

  if (clearBtn) {
    clearBtn.classList.toggle('hidden', !query || !query.trim());
  }

  if (!query || !query.trim()) {
    if (mobileSearchAbort) {
      mobileSearchAbort.abort();
      mobileSearchAbort = null;
    }
    fetch('/api/trending')
      .then(r => r.json())
      .then(trending => {
        if (Array.isArray(trending) && trending.length) {
          renderMobileSearchResults(trending, 'Popular Recommendations & Hits');
        } else {
          renderMobileSearchResults(HERO_SLIDES, 'Popular Recommendations & Hits');
        }
      })
      .catch(() => renderMobileSearchResults(HERO_SLIDES, 'Popular Recommendations & Hits'));
    return;
  }

  const cleanQuery = query.trim();
  if (statusEl) statusEl.textContent = `Searching for "${cleanQuery}"...`;
  if (resultsEl) {
    resultsEl.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;gap:10px;padding:32px 16px;color:#94a3b8;font-weight:600;">
        <div class="spinner" style="width:20px;height:20px;border-width:2px;"></div>
        <span>Searching all tracks & artists...</span>
      </div>`;
  }

  if (mobileSearchAbort) {
    mobileSearchAbort.abort();
  }
  mobileSearchAbort = new AbortController();

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(cleanQuery)}&limit=20`, {
      signal: mobileSearchAbort.signal
    });
    if (!res.ok) throw new Error('Search failed with status ' + res.status);
    const tracks = await res.json();
    if (Array.isArray(tracks) && tracks.length > 0) {
      renderMobileSearchResults(tracks, `Results for "${cleanQuery}" (${tracks.length}):`);
    } else {
      if (statusEl) statusEl.textContent = `No exact matches for "${cleanQuery}"`;
      if (resultsEl) {
        resultsEl.innerHTML = `
          <div style="text-align:center;padding:24px 16px;color:#94a3b8;">
            <p style="font-size:0.95rem;font-weight:600;margin-bottom:6px;">No tracks found for "${escapeHTML(cleanQuery)}"</p>
            <p style="font-size:0.8rem;color:#64748b;">Try checking spelling or search by artist name.</p>
          </div>`;
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') return;
    console.warn('Mobile search error:', e);
    if (statusEl) statusEl.textContent = `Search error — displaying popular tracks:`;
    fetch('/api/trending')
      .then(r => r.json())
      .then(trending => {
        if (Array.isArray(trending) && trending.length) {
          renderMobileSearchResults(trending, 'Trending Hits:');
        } else {
          renderMobileSearchResults(HERO_SLIDES, 'Trending Hits:');
        }
      })
      .catch(() => renderMobileSearchResults(HERO_SLIDES, 'Trending Hits:'));
  }
}

function renderMobileSearchResults(tracks, label) {
  const statusEl = $('mobile-search-status');
  const resultsEl = $('mobile-search-results');
  if (statusEl && label) statusEl.textContent = label;
  if (!resultsEl) return;
  resultsEl.innerHTML = '';

  const list = (tracks && tracks.length) ? tracks : HERO_SLIDES;
  list.forEach(track => {
    const row = document.createElement('div');
    row.className = 'mobile-track-row';
    const thumb = track.thumbnail || generateFallbackCover(track.title, track.artist);
    const duration = track.duration_formatted || '3:30';
    row.innerHTML = `
      <img src="${thumb}" alt="${escapeHTML(track.title)}" class="mobile-track-thumb" onerror="if(this.src.includes('hq720.jpg')){this.src=this.src.replace('hq720.jpg','hqdefault.jpg');}else{this.onerror=null;this.src=generateFallbackCover('${escapeHTML(track.title)}','${escapeHTML(track.artist)}');}">
      <div class="mobile-track-info">
        <div class="mobile-track-title">${escapeHTML(track.title)}</div>
        <div class="mobile-track-artist">${escapeHTML(track.artist || 'Artist')}</div>
      </div>
      <span style="font-size:0.75rem;color:#64748b;margin-right:6px;font-variant-numeric:tabular-nums;">${duration}</span>
      <button class="mobile-track-play-btn" title="Play">
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <polygon points="8 5 19 12 8 19 8 5"></polygon>
        </svg>
      </button>
    `;
    row.addEventListener('click', () => {
      playTrack(track);
      closeMobileSearch();
      showToastNotification(`Playing: ${track.title}`);
    });
    resultsEl.appendChild(row);
  });
}

function playRadioTrack(index) {
  if (index >= 0 && index < state.radioQueue.length) {
    const track = state.radioQueue.splice(index, 1)[0];
    renderQueueDrawer();
    playTrack(track, { startRadio: true });
    showToastNotification(`Playing: ${track.title}`);
  }
}

const renderQueueUI = function(...args) {
  return renderQueueDrawer(...args);
};
window.renderQueueUI = renderQueueUI;

function renderQueueDrawer() {
  // 1. Synchronize Autoplay Switch
  const autoplaySwitch = $('queue-autoplay-switch');
  if (autoplaySwitch) {
    autoplaySwitch.checked = (state.autoplay !== false);
  }

  // 2. Update Now Playing card inside queue drawer
  const npTitle = $('queue-np-title');
  const npArtist = $('queue-np-artist');
  const npThumb = $('queue-np-thumb');
  const npEq = $('queue-np-eq');
  const skipNpBtn = $('btn-queue-skip-np');

  if (state.currentTrack) {
    if (npTitle) npTitle.textContent = state.currentTrack.title || 'Unknown Title';
    if (npArtist) npArtist.textContent = state.currentTrack.artist || 'Unknown Artist';
    if (npThumb) setSafeCoverArt(npThumb, state.currentTrack);
    if (npEq) npEq.style.opacity = state.isPlaying ? '1' : '0.4';
    if (skipNpBtn) skipNpBtn.style.display = 'inline-flex';
  } else {
    if (npTitle) npTitle.textContent = 'No track playing';
    if (npArtist) npArtist.textContent = 'Choose a song to start listening';
    if (npEq) npEq.style.opacity = '0.2';
    if (skipNpBtn) skipNpBtn.style.display = 'none';
  }

  // 3. Update Manual Next Up Queue
  const listContainer = $('queue-items-list');
  const manualCountBadge = $('queue-manual-count');
  const clearBtn = $('btn-clear-queue');
  const manualCount = state.queue ? state.queue.length : 0;

  if (clearBtn) {
    clearBtn.style.display = manualCount > 0 ? 'inline-flex' : 'none';
  }

  if (manualCountBadge) {
    if (manualCount > 0) {
      manualCountBadge.textContent = `${manualCount}`;
      manualCountBadge.style.display = 'inline-block';
    } else {
      manualCountBadge.style.display = 'none';
    }
  }

  if (listContainer) {
    listContainer.innerHTML = '';
    if (manualCount > 0) {
      state.queue.forEach((track, index) => {
        const item = document.createElement('div');
        item.className = 'queue-item-row';

        let thumb = track.thumbnail || generateFallbackCover(track.title, track.artist);
        if (thumb.includes('hq720.jpg')) {
          thumb = thumb.replace('hq720.jpg', 'hqdefault.jpg');
        }

        item.setAttribute('draggable', 'true');
        item.dataset.index = index;

        item.innerHTML = `
          <div class="queue-drag-handle" title="Drag to reorder track">
            <svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13">
              <circle cx="9" cy="6" r="1.8"></circle>
              <circle cx="15" cy="6" r="1.8"></circle>
              <circle cx="9" cy="12" r="1.8"></circle>
              <circle cx="15" cy="12" r="1.8"></circle>
              <circle cx="9" cy="18" r="1.8"></circle>
              <circle cx="15" cy="18" r="1.8"></circle>
            </svg>
          </div>
          <span class="queue-item-order">${index + 1}</span>
          <img src="${thumb}" alt="${escapeHTML(track.title)}" class="queue-item-thumb" loading="lazy" onerror="this.onerror=null;this.src=generateFallbackCover('${escapeHTML(track.title)}','${escapeHTML(track.artist)}');">
          <div class="queue-item-info">
            <span class="queue-item-title">${escapeHTML(track.title)}</span>
            <span class="queue-item-artist">${escapeHTML(track.artist)}</span>
          </div>
          <span class="queue-item-time">${track.duration_formatted || '3:30'}</span>
          <button class="queue-item-play-btn" title="Play Now" aria-label="Play Now">
            <svg viewBox="0 0 24 24" fill="currentColor" width="15" height="15">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          </button>
          <button class="queue-item-remove-btn" title="Remove from queue" aria-label="Remove from queue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" width="15" height="15">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        `;

        item.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('text/plain', String(index));
          e.dataTransfer.effectAllowed = 'move';
          item.classList.add('dragging');
        });
        item.addEventListener('dragend', () => {
          item.classList.remove('dragging');
          document.querySelectorAll('.queue-item-row').forEach(r => r.classList.remove('drag-over'));
        });
        item.addEventListener('dragover', (e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = 'move';
          item.classList.add('drag-over');
        });
        item.addEventListener('dragleave', () => {
          item.classList.remove('drag-over');
        });
        item.addEventListener('drop', (e) => {
          e.preventDefault();
          item.classList.remove('drag-over');
          const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
          const toIdx = index;
          if (!isNaN(fromIdx) && fromIdx !== toIdx && state.queue[fromIdx]) {
            const moved = state.queue.splice(fromIdx, 1)[0];
            state.queue.splice(toIdx, 0, moved);
            saveQueueToStorage();
            renderQueueUI();
            showToastNotification(`Moved "${moved.title}" in queue`);
          }
        });

        item.querySelector('.queue-item-play-btn')?.addEventListener('click', (e) => {
          e.stopPropagation();
          playQueuedTrack(index);
        });

        item.querySelector('.queue-item-remove-btn')?.addEventListener('click', (e) => {
          e.stopPropagation();
          removeFromQueue(index);
        });

        item.addEventListener('click', () => {
          playQueuedTrack(index);
        });

        listContainer.appendChild(item);
      });
    } else {
      // Manual queue is empty
      if (state.radioQueue && state.radioQueue.length > 0) {
        listContainer.innerHTML = `
          <div class="queue-manual-empty-hint">
            Priority queue is empty. Recommended tracks in <strong>Auto Playlist</strong> below will play next.
          </div>
        `;
      } else if (!state.radioLoading) {
        listContainer.innerHTML = `
          <div class="queue-empty-state">
            <div class="queue-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="26" height="26">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <circle cx="4" cy="6" r="1.5" fill="currentColor"></circle>
                <circle cx="4" cy="12" r="1.5" fill="currentColor"></circle>
                <circle cx="4" cy="18" r="1.5" fill="currentColor"></circle>
              </svg>
            </div>
            <span class="queue-empty-title">Your Queue is Empty</span>
            <p class="queue-empty-subtitle">Tap the <strong>+</strong> icon on any song in Top Charts or Search to queue it up next.</p>
          </div>
        `;
      }
    }
  }

  // 4. Render Auto Playlist Continuous Recommendations
  const autoListContainer = $('queue-auto-list');
  const autoHeader = $('queue-auto-header');
  const autoDesc = $('queue-auto-desc');
  const clearAutoBtn = $('btn-clear-auto-queue');

  if (clearAutoBtn) {
    clearAutoBtn.style.display = (state.radioQueue && state.radioQueue.length > 0) ? 'inline-flex' : 'none';
  }

  if (autoListContainer) {
    autoListContainer.innerHTML = '';

    if (state.radioLoading) {
      if (autoHeader) autoHeader.style.display = 'flex';
      autoListContainer.innerHTML = `
        <div class="queue-auto-loading">
          <div class="queue-auto-spinner"></div>
          <span>Curating continuous recommendations...</span>
        </div>
      `;
    } else if (state.radioQueue && state.radioQueue.length > 0) {
      if (autoHeader) autoHeader.style.display = 'flex';
      if (autoDesc) {
        autoDesc.textContent = state.currentTrack
          ? `Continuous radio matching "${state.currentTrack.title}" vibe`
          : 'Continuous radio recommendations';
      }

      state.radioQueue.forEach((track, index) => {
        const row = document.createElement('div');
        row.className = 'queue-auto-row';

        let thumb = track.thumbnail || generateFallbackCover(track.title, track.artist);
        if (thumb.includes('hq720.jpg')) {
          thumb = thumb.replace('hq720.jpg', 'hqdefault.jpg');
        }

        row.innerHTML = `
          <span class="queue-auto-icon" title="Recommended Song">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
          </span>
          <img src="${thumb}" alt="${escapeHTML(track.title)}" class="queue-item-thumb" loading="lazy" onerror="this.onerror=null;this.src=generateFallbackCover('${escapeHTML(track.title)}','${escapeHTML(track.artist)}');">
          <div class="queue-item-info">
            <span class="queue-item-title">${escapeHTML(track.title)}</span>
            <span class="queue-item-artist">${escapeHTML(track.artist)}</span>
          </div>
          <span class="queue-item-time">${track.duration_formatted || '3:30'}</span>
          <button class="queue-item-play-btn" title="Play Now" aria-label="Play Now">
            <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          </button>
          <button class="queue-item-add-btn" title="Add to Priority Queue" aria-label="Add to Queue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" width="15" height="15">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
          <button class="queue-item-remove-btn queue-item-remove-auto-btn" title="Remove from recommendations" aria-label="Remove from queue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" width="15" height="15">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        `;

        row.querySelector('.queue-item-play-btn')?.addEventListener('click', (e) => {
          e.stopPropagation();
          playRadioTrack(index);
        });

        row.querySelector('.queue-item-add-btn')?.addEventListener('click', (e) => {
          e.stopPropagation();
          const added = state.radioQueue.splice(index, 1)[0];
          if (added) {
            addToQueue(added);
          }
        });

        row.querySelector('.queue-item-remove-auto-btn')?.addEventListener('click', (e) => {
          e.stopPropagation();
          removeFromRadioQueue(index);
        });

        row.addEventListener('click', () => {
          playRadioTrack(index);
        });

        autoListContainer.appendChild(row);
      });
    } else {
      if (autoHeader) autoHeader.style.display = 'none';
      if (state.currentTrack && !state.radioLoading) {
        loadRadioQueue(state.currentTrack.id, state.currentTrack.artist, state.currentTrack.title);
      }
    }
  }

  // 5. Update header pill count: manual + auto
  const pill = $('queue-pill-count');
  if (pill) {
    const autoCount = state.radioQueue ? state.radioQueue.length : 0;
    if (manualCount > 0 && autoCount > 0) {
      pill.textContent = `${manualCount} queued • ${autoCount} auto`;
    } else if (manualCount > 0) {
      pill.textContent = `${manualCount} ${manualCount === 1 ? 'track' : 'tracks'}`;
    } else if (autoCount > 0) {
      pill.textContent = `${autoCount} recommended`;
    } else {
      pill.textContent = '0 tracks';
    }
  }
}

// ============================================================================
// Audio Engine & Playback
// ============================================================================
function cleanPrimaryArtist(artistName) {
  if (!artistName) return '';
  const cleaned = String(artistName).replace(/ - Topic|VEVO|Official/gi, '').trim();
  const primary = cleaned.split(/[,&/]|(?:\s+[-–—]\s+)|\b(?:feat\.?|ft\.?|with|x|vs\.?)\b/i)[0];
  return primary.replace(/[\(\[\{].*?[\)\]\}]/g, '').replace(/^[^\w]+|[^\w]+$/g, '').trim().toLowerCase();
}

// Regional & Linguistic Context Detection (Hindi / Indian vs Western Pop)
const HINDI_SCRIPT_RE = /[\u0900-\u097F\u0A00-\u0A7F\u0980-\u09FF\u0B80-\u0BFF\u0C00-\u0C7F\u0600-\u06FF]/;
const HINDI_KEYWORDS = new Set([
  'hindi', 'bollywood', 'punjabi', 'bhangra', 'sufi', 'ghazal', 'qawwali', 'lofi hindi',
  'dil', 'pyar', 'pyaar', 'ishq', 'mohabbat', 'tere', 'teri', 'mera', 'meri', 'tum', 'hum',
  'sanam', 'zindagi', 'saath', 'deewana', 'aankhon', 'raat', 'chaand', 'saiyaara', 'bairan',
  'aarzu', 'sahiba', 'taare', 'pal', 'zulfein', 'dhol', 'nach', 'channa', 'kesariya', 'shayad',
  'khairiyat', 'humsafar', 'dhadak', 'raataan', 'lambiyan', 'chaleya', 'baarishein', 'tu hai',
  'kahan', 'pehli', 'nazar', 'kabhi', 'dosti', 'yaari', 'ranjha', 'heer', 'mann', 'duniya',
  'naina', 'ankhiyaan', 'sajna', 'dholna', 'mahiya', 'jatt', 'pind', 'kudi', 'gaana', 'geet',
  'aashiqui', 'bewafa', 'sadqa', 'dua', 'humnava', 'rabba', 'ishqbaazi', 'tujhe', 'mujhe',
  'apna', 'bana', 'le', 'kahani', 'baarish', 'tera', 'chahunga', 'muskurane', 'sukoon',
  'musafir', 'leja', 're', 'lut', 'gaye', 'qismat', 'kalank', 'ghungroo', 'bekhayali', 'pehla',
  'gerua', 'bulleya', 'zaalima', 'hawayein', 'matargashti', 'kasoor', 'choo', 'lo', 'aaftab',
  'heeriye', 'satranga', 'soulmate', 'pasoori', 'husn', 'faasle', 'kho', 'gaye', 'safarnama',
  'alvida', 'jeena', 'jeene', 'laga', 'tera fitoor', 'nainowale', 'subhanallah', 'kabira'
]);
const INDIAN_ARTISTS = new Set([
  'arijit singh', 'atif aslam', 'shreya ghoshal', 'neha kakkar', 'jubin nautiyal',
  'sonu nigam', 'sunidhi chauhan', 'mohit chauhan', 'kishore kumar', 'lata mangeshkar',
  'mukesh', 'mohammed rafi', 'pritam', 'ar rahman', 'a.r. rahman', 'badshah',
  'diljit dosanjh', 'ap dhillon', 'karan aujla', 'honey singh', 'yo yo honey singh',
  'darshan raval', 'anuv jain', 'prateek kuhad', 'sachin-jigar', 'vishal mishra',
  'armaan malik', 'b praak', 'jaani', 'sidhu moosewala', 'guru randhawa', 'hardy sandhu',
  'shubh', 'talwiinder', 'king', 'mc stan', 'divine', 'raftaar', 'kumar sanu',
  'udit narayan', 'alka yagnik', 'kavita krishnamurthy', 'jagjit singh', 'nusrat fateh ali khan',
  'rahat fateh ali khan', 'lucky ali', 'kk', 'shaan', 'himesh reshammiya', 'mika singh',
  'sachet tandon', 'stebin ben', 'jasleen royal', 'aditya rikhari', 'madhurxo', 'kushagra',
  'aur', 'sickved', 'banjaare', 't-series', 'zee music', 'sony music india', 'yrf', 'tips',
  'saregama', 'speed records', 'white hill music', 'anirudh ravichander', 'devi sri prasad',
  'vishal-shekhar', 'amit trivedi', 'mithoon', 'meet bros', 'tony kakkar', 'pawandeep rajan',
  'arunita kanjilal', 'shankar mahadevan', 'hariharan', 'pankaj udhas', 'bhupen hazarika'
]);
const BLATANT_WESTERN_ARTISTS = new Set([
  'the weeknd', 'taylor swift', 'drake', 'justin bieber', 'dua lipa', 'ed sheeran',
  'billie eilish', 'ariana grande', 'bruno mars', 'rihanna', 'beyonce', 'post malone',
  'kendrick lamar', 'eminem', 'kanye west', 'travis scott', 'coldplay', 'imagine dragons',
  'maroon 5', 'shawn mendes', 'harry styles', 'olivia rodrigo', 'adele', 'sam smith',
  'katy perry', 'lady gaga', 'selena gomez', 'charlie puth', 'zayn', 'camila cabello',
  'sabrina carpenter', 'chappell roan', 'charli xcx', 'queen', 'the beatles', 'michael jackson',
  'sza', 'doja cat', 'miley cyrus', 'jack harlow', 'future', 'metro boomin', 'gunna', 'lil baby',
  'lil nas x', '21 savage', 'cardi b', 'nicki minaj', 'marshmello', 'alan walker', 'david guetta',
  'calvin harris', 'avicii', 'dj snake', 'tiesto', 'kygo', 'martin garrix', 'halsey', 'benson boone'
]);

const HINDI_FALLBACK_TRACKS = [
  { id: "BddP6PY427U", title: "Kesariya", artist: "Arijit Singh, Pritam", thumbnail: "https://i.ytimg.com/vi/BddP6PY427U/hqdefault.jpg", duration_formatted: "4:28" },
  { id: "284Ov7ysmfA", title: "Tum Hi Ho", artist: "Arijit Singh", thumbnail: "https://i.ytimg.com/vi/284Ov7ysmfA/hqdefault.jpg", duration_formatted: "4:22" },
  { id: "ElZfdU54Cp8", title: "Apna Bana Le", artist: "Arijit Singh, Sachin-Jigar", thumbnail: "https://i.ytimg.com/vi/ElZfdU54Cp8/hqdefault.jpg", duration_formatted: "4:21" },
  { id: "CL68r_9gB0k", title: "Raataan Lambiyan", artist: "Jubin Nautiyal, Tanishk Bagchi", thumbnail: "https://i.ytimg.com/vi/CL68r_9gB0k/hqdefault.jpg", duration_formatted: "3:50" },
  { id: "V7LwfY5U5WI", title: "Chaleya", artist: "Arijit Singh, Shilpa Rao, Anirudh", thumbnail: "https://i.ytimg.com/vi/V7LwfY5U5WI/hqdefault.jpg", duration_formatted: "3:20" },
  { id: "O2unP9q58z4", title: "Pehle Bhi Main", artist: "Vishal Mishra, Raj Shekhar", thumbnail: "https://i.ytimg.com/vi/O2unP9q58z4/hqdefault.jpg", duration_formatted: "4:10" },
  { id: "6MgsHSAcI9k", title: "O Maahi", artist: "Arijit Singh, Pritam", thumbnail: "https://i.ytimg.com/vi/6MgsHSAcI9k/hqdefault.jpg", duration_formatted: "3:53" },
  { id: "cUMm_P_b_lY", title: "Guli Mata", artist: "Saad Lamjarred, Shreya Ghoshal", thumbnail: "https://i.ytimg.com/vi/cUMm_P_b_lY/hqdefault.jpg", duration_formatted: "3:40" }
];

function isIndianHindiTrack(title, artist) {
  const text = `${title || ''} ${artist || ''}`.toLowerCase();
  if (HINDI_SCRIPT_RE.test(text)) return true;
  const cleanArt = (artist || '').toLowerCase().trim();
  for (const ia of INDIAN_ARTISTS) {
    if (cleanArt.includes(ia) || text.includes(ia)) return true;
  }
  const words = text.match(/[a-zA-Z]+/g) || [];
  for (const w of words) {
    if (HINDI_KEYWORDS.has(w)) return true;
  }
  return false;
}

function isBlatantWesternTrack(title, artist) {
  const cleanArt = (artist || '').toLowerCase().trim();
  const cleanTitle = (title || '').toLowerCase().trim();
  const text = `${cleanTitle} ${cleanArt}`;
  for (const wa of BLATANT_WESTERN_ARTISTS) {
    if (cleanArt.includes(wa) || text.includes(wa)) return true;
  }
  return false;
}

async function playTrack(track, options = { startRadio: true }) {
  if (!track || !track.id) return;

  state.currentTrack = track;
  state.isPlaying = true;

  // Track recent session playback history (up to last 150 played songs) to prevent ping-pong loops
  if (!Array.isArray(state.sessionPlayedIds)) state.sessionPlayedIds = [];
  state.sessionPlayedIds = state.sessionPlayedIds.filter(id => id !== track.id);
  state.sessionPlayedIds.push(track.id);
  if (state.sessionPlayedIds.length > 150) {
    state.sessionPlayedIds.shift();
  }

  // Add to history
  if (!state.history.some(t => t.id === track.id)) {
    state.history.unshift(track);
  }

  // Handle local user audio files directly with native engine
  if (track.isLocal || (track.id && String(track.id).startsWith('local-'))) {
    isYTActive = false;
    stopYTProgressTracker();
    if (ytPlayer && typeof ytPlayer.pauseVideo === 'function') ytPlayer.pauseVideo();
    updatePlayerUI(track);
    updateMediaSession(track);
    audio.src = track.streamUrl;
    audio.load();
    try {
      await audio.play();
      updatePlayPauseIcons(true);
    } catch (err) {
      console.warn('[Local audio playback error]:', err);
      updatePlayPauseIcons(false);
    }
    return;
  }

  updatePlayerUI(track);
  updateMediaSession(track);

  // Initialize Web Audio DSP and apply active playback speed
  initWebAudio();
  resumeAudioContext();
  if (audio) {
    audio.playbackRate = state.playbackSpeed || 1.0;
  }
  if (ytPlayer && typeof ytPlayer.setPlaybackRate === 'function') {
    try { ytPlayer.setPlaybackRate(state.playbackSpeed || 1.0); } catch (e) {}
  }

  // Primary: Use YouTube Official Player for 100% genuine song playback (zero bot blocks / zero test sounds)
  // When Karaoke mode or 8D Audio mode is active, route through Direct Audio stream so Web Audio DSP can process
  if (!state.karaokeMode && (!state.eightD || !state.eightD.enabled) && track.id && (!track.streamUrl || track.id.length === 11)) {
    isYTActive = true;
    if (audio) {
      audio.pause();
      audio.src = '';
    }
    if (ytPlayer && typeof ytPlayer.loadVideoById === 'function') {
      ytPlayer.loadVideoById(track.id);
      ytPlayer.playVideo();
      updatePlayPauseIcons(true);
      startYTProgressTracker();
    } else {
      pendingYTTrack = track;
      const q = (state.audioEngine && state.audioEngine.quality) || 'high';
      const streamUrl = track.offlineBlobUrl || track.streamUrl || `/api/stream?id=${encodeURIComponent(track.id)}&quality=${q}`;
      audio.src = streamUrl;
      audio.load();
      audio.play().then(() => updatePlayPauseIcons(true)).catch(console.warn);
    }
  } else {
    isYTActive = false;
    stopYTProgressTracker();
    if (ytPlayer && typeof ytPlayer.pauseVideo === 'function') ytPlayer.pauseVideo();
    const q = (state.audioEngine && state.audioEngine.quality) || 'high';
    const streamUrl = track.offlineBlobUrl || track.streamUrl || `/api/stream?id=${encodeURIComponent(track.id)}&quality=${q}`;
    audio.src = streamUrl;
    audio.load();
    try {
      await audio.play();
      updatePlayPauseIcons(true);
    } catch (err) {
      console.warn('[Audio play exception]:', err);
      updatePlayPauseIcons(false);
    }
  }

  // Load lyrics asynchronously
  fetchLyrics(track);

  // Auto-fetch SponsorBlock skip segments for music skits & intros
  if (track.id && String(track.id).length === 11) {
    fetchTrackSponsorBlock(track.id);
  } else {
    state.sponsorblock.segments = [];
    state.sponsorblock.skippedSegments = new Set();
    state.sponsorblock.bypassedStarts = new Set();
  }

  // Fetch automix recommendations in the background seeded by track and artist
  if (options && options.startRadio !== false) {
    loadRadioQueue(track.id, track.artist, track.title);
  }

  // Update ambient glow with soft color shift
  shiftAmbientAura(track.id);
}

function setTrackPreview(track) {
  state.currentTrack = track;
  updatePlayerUI(track);
}

function setSafeCoverArt(imgEl, track) {
  if (!imgEl) return;
  const fallback = generateFallbackCover(track.title, track.artist);
  let src = track.thumbnail;
  if (!src) {
    imgEl.src = fallback;
    return;
  }
  if (src.includes('hq720.jpg')) {
    src = src.replace('hq720.jpg', 'hqdefault.jpg');
  }
  imgEl.onerror = () => {
    if (imgEl.src.includes('hq720.jpg')) {
      imgEl.src = imgEl.src.replace('hq720.jpg', 'hqdefault.jpg');
    } else if (imgEl.src.includes('maxresdefault.jpg')) {
      imgEl.src = imgEl.src.replace('maxresdefault.jpg', 'hqdefault.jpg');
    } else {
      imgEl.onerror = null;
      imgEl.src = fallback;
    }
  };
  imgEl.src = src;
}

function updatePlayerUI(track) {
  if ($('player-track-name')) $('player-track-name').textContent = track.title || 'Unknown Title';
  if ($('player-track-artist')) $('player-track-artist').textContent = track.artist || 'Unknown Artist';
  if ($('player-track-album')) $('player-track-album').textContent = `${track.album || 'SongBuddy Stream'} • Direct Opus`;

  setSafeCoverArt($('player-cover-art'), track);

  // Sync Now Playing card in queue drawer
  if ($('queue-np-title')) $('queue-np-title').textContent = track.title || 'Unknown Title';
  if ($('queue-np-artist')) $('queue-np-artist').textContent = track.artist || 'Unknown Artist';
  const qnpThumb = $('queue-np-thumb');
  if (qnpThumb) setSafeCoverArt(qnpThumb, track);

  if ($('scrub-current-time')) $('scrub-current-time').textContent = '0:00';
  if ($('scrub-total-time')) $('scrub-total-time').textContent = track.duration_formatted || '3:45';
  if ($('scrubber-played-bar')) $('scrubber-played-bar').style.width = '0%';

  // Update active state in chart lists
  document.querySelectorAll('.chart-row').forEach(row => {
    const titleEl = row.querySelector('.chart-title');
    if (titleEl && titleEl.textContent === track.title) {
      row.classList.add('active');
    } else {
      row.classList.remove('active');
    }
  });

  // Sync heart liked status on right player panel
  const isLiked = state.likedTracks.some(t => t.id === track.id);
  $('hero-heart-btn')?.classList.toggle('liked', isLiked);
  $('btn-neu-heart')?.classList.toggle('liked', isLiked);

  // Sync Mobile Mini-Player Bar
  const mobileMini = $('mobile-mini-player');
  if (mobileMini) {
    mobileMini.classList.remove('hidden');
    if ($('mobile-mini-title')) $('mobile-mini-title').textContent = track.title || 'Unknown Title';
    if ($('mobile-mini-artist')) $('mobile-mini-artist').textContent = track.artist || 'Unknown Artist';
    const miniThumb = $('mobile-mini-thumb');
    if (miniThumb) setSafeCoverArt(miniThumb, track);
  }

  // Sync Cinema Ambilight Mode & Dynamic Thumbnail Roaming Beam
  syncCinemaTrack(track);
  updateAmbientThumbnailColors(track);
}

function updatePlayPauseIcons(isPlaying) {
  const playSvg = $('play-svg');
  const pauseSvg = $('pause-svg');
  if (playSvg && pauseSvg) {
    if (isPlaying) {
      playSvg.classList.add('hidden');
      pauseSvg.classList.remove('hidden');
    } else {
      playSvg.classList.remove('hidden');
      pauseSvg.classList.add('hidden');
    }
  }

  // Sync Mobile Mini-Player Play/Pause icons
  const mobPlay = $('mobile-play-icon');
  const mobPause = $('mobile-pause-icon');
  if (mobPlay && mobPause) {
    if (isPlaying) {
      mobPlay.classList.add('hidden');
      mobPause.classList.remove('hidden');
    } else {
      mobPlay.classList.remove('hidden');
      mobPause.classList.add('hidden');
    }
  }

  // Sync Cinema Ambilight Play/Pause icons
  const cinPlay = $('cinema-play-svg');
  const cinPause = $('cinema-pause-svg');
  if (cinPlay && cinPause) {
    if (isPlaying) {
      cinPlay.classList.add('hidden');
      cinPause.classList.remove('hidden');
    } else {
      cinPlay.classList.remove('hidden');
      cinPause.classList.add('hidden');
    }
  }

  // Active roaming light pulse
  const ambilight = $('screen-ambilight');
  if (ambilight) {
    ambilight.classList.toggle('paused', !isPlaying);
  }

  // Animate mini equalizer bars when playing
  const eqChip = $('chip-equalizer');
  if (eqChip) {
    eqChip.classList.toggle('playing', !!isPlaying);
  }

  const queueEq = $('queue-np-eq');
  if (queueEq) {
    queueEq.style.opacity = isPlaying ? '1' : '0.4';
  }
}

function togglePlayPause() {
  if (!state.currentTrack) {
    if (state.featuredTracks.length > 0) {
      playTrack(state.featuredTracks[0]);
    } else {
      playTrack(HERO_SLIDES[0]);
    }
    return;
  }

  if (isYTActive && ytPlayer && typeof ytPlayer.getPlayerState === 'function') {
    const pState = ytPlayer.getPlayerState();
    if (pState === 1) { // 1 = PLAYING
      ytPlayer.pauseVideo();
      state.isPlaying = false;
      updatePlayPauseIcons(false);
      stopYTProgressTracker();
    } else {
      ytPlayer.playVideo();
      state.isPlaying = true;
      updatePlayPauseIcons(true);
      startYTProgressTracker();
    }
    return;
  }

  if (!audio.src || audio.src === '' || audio.src === window.location.href || !audio.src.includes(encodeURIComponent(state.currentTrack.id))) {
    playTrack(state.currentTrack);
    return;
  }

  if (audio.paused) {
    audio.play().then(() => {
      state.isPlaying = true;
      updatePlayPauseIcons(true);
    }).catch(err => {
      console.warn('[Audio play retry via playTrack]:', err);
      playTrack(state.currentTrack);
    });
  } else {
    audio.pause();
    state.isPlaying = false;
    updatePlayPauseIcons(false);
  }
}

function playNextTrack(isManual = false) {
  const currentId = state.currentTrack?.id;
  const playedSet = new Set([
    currentId,
    ...(state.sessionPlayedIds || []),
    ...(state.history || []).map(t => t.id)
  ]);

  if (state.queue && state.queue.length > 0) {
    let nextIndex = 0;
    if (state.isShuffle) {
      nextIndex = Math.floor(Math.random() * state.queue.length);
    }
    const next = state.queue.splice(nextIndex, 1)[0];
    saveQueueToStorage();
    updateQueueBadge();
    renderQueueDrawer();
    if (next) {
      playTrack(next, { startRadio: false });
      showToastNotification(`Playing from queue: ${next.title}`);
    }
    return;
  }

  const isCurrentIndian = state.currentTrack && isIndianHindiTrack(state.currentTrack.title, state.currentTrack.artist);

  if ((state.autoplay !== false || isManual) && state.radioQueue && state.radioQueue.length > 0) {
    // Auto Playlist: Find the first recommendation that is not currentTrack and has not been played recently
    let nextTrack = null;
    while (state.radioQueue.length > 0) {
      const candidate = state.isShuffle
        ? state.radioQueue.splice(Math.floor(Math.random() * state.radioQueue.length), 1)[0]
        : state.radioQueue.shift();

      if (candidate && candidate.id && candidate.id !== currentId && !playedSet.has(candidate.id)) {
        // If current track was Hindi, skip any blatant Western pop candidate in the queue!
        if (isCurrentIndian && isBlatantWesternTrack(candidate.title, candidate.artist)) {
          continue;
        }
        nextTrack = candidate;
        break;
      }
    }

    updateQueueBadge();
    renderQueueDrawer();

    if (nextTrack) {
      playTrack(nextTrack, { startRadio: true });
      showToastNotification(`Autoplaying recommendation: ${nextTrack.title}`);
      return;
    }
  }

  // Fallback when radioQueue is empty or exhausted:
  if (state.autoplay !== false || isManual) {
    if (isCurrentIndian) {
      const unplayedHindi = HINDI_FALLBACK_TRACKS.filter(t => t && t.id && t.id !== currentId && !playedSet.has(t.id));
      if (unplayedHindi.length > 0) {
        playTrack(unplayedHindi[0], { startRadio: true });
        showToastNotification(`Autoplaying: ${unplayedHindi[0].title}`);
        return;
      }
      const currentIdx = HINDI_FALLBACK_TRACKS.findIndex(t => t.id === currentId);
      const nextIdx = (currentIdx + 1) % HINDI_FALLBACK_TRACKS.length;
      playTrack(HINDI_FALLBACK_TRACKS[nextIdx], { startRadio: true });
      showToastNotification(`Autoplaying: ${HINDI_FALLBACK_TRACKS[nextIdx].title}`);
      return;
    }

    if (state.featuredTracks && state.featuredTracks.length > 0) {
      const unplayedFeatured = state.featuredTracks.filter(t => t && t.id && t.id !== currentId && !playedSet.has(t.id));
      if (unplayedFeatured.length > 0) {
        playTrack(unplayedFeatured[0], { startRadio: true });
        return;
      }
      const currentIdx = state.featuredTracks.findIndex(t => t.id === currentId);
      const nextIdx = (currentIdx + 1) % state.featuredTracks.length;
      playTrack(state.featuredTracks[nextIdx], { startRadio: true });
      return;
    }
  }

  if (state.autoplay === false && !isManual) {
    state.isPlaying = false;
    updatePlayPauseIcons(false);
  }
}

function playPrevTrack() {
  const curTime = (isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function')
    ? ytPlayer.getCurrentTime()
    : (audio ? audio.currentTime : 0);

  if (curTime > 3) {
    seekPlayerTo(0);
    return;
  }
  if (state.history.length > 1) {
    state.history.shift(); // Remove current
    const prev = state.history.shift();
    if (prev) playTrack(prev);
  } else {
    seekPlayerTo(0);
  }
}

// ============================================================================
// Radio & Automix (Auto Playlist Recommendation Driver)
// ============================================================================
async function loadRadioQueue(seedId, seedArtist = '', seedTitle = '') {
  if (!seedId) return;
  state.radioRequestId = (state.radioRequestId || 0) + 1;
  const currentReqId = state.radioRequestId;
  state.radioLoading = true;
  renderQueueDrawer();

  try {
    const artistQuery = seedArtist || (state.currentTrack && state.currentTrack.artist) || '';
    const titleQuery = seedTitle || (state.currentTrack && state.currentTrack.title) || '';
    const isCurrentIndian = isIndianHindiTrack(titleQuery, artistQuery);

    const artistParam = artistQuery ? `&artist=${encodeURIComponent(artistQuery)}` : '';
    const titleParam = titleQuery ? `&title=${encodeURIComponent(titleQuery)}` : '';
    const res = await fetch(`/api/radio?id=${encodeURIComponent(seedId)}${artistParam}${titleParam}`);
    if (currentReqId !== state.radioRequestId) return; // Stale request, discard
    if (!res.ok) {
      state.radioLoading = false;
      renderQueueDrawer();
      return;
    }
    const tracks = await res.json();
    if (currentReqId !== state.radioRequestId) return;

    // 1. Exclude the seed track itself, current playing track, and all session-played tracks
    const playedSet = new Set([
      seedId,
      state.currentTrack?.id,
      ...(state.sessionPlayedIds || []),
      ...(state.history || []).map(t => t.id)
    ]);
    let filtered = Array.isArray(tracks) ? tracks.filter(t => t && t.id && !playedSet.has(t.id)) : [];

    // Filter blatant Western tracks if current track is Hindi
    if (isCurrentIndian) {
      filtered = filtered.filter(t => !isBlatantWesternTrack(t.title, t.artist));
    }

    // 2. Intelligent related discovery fallback if automix returns fewer than 8 songs
    const targetSeedArtist = artistQuery;
    const normSeedArtist = cleanPrimaryArtist(targetSeedArtist);
    if (filtered.length < 8 && state.currentTrack) {
      try {
        let queryTerm;
        if (isCurrentIndian) {
          queryTerm = normSeedArtist
            ? `${targetSeedArtist} similar hindi bollywood songs radio mix`
            : (titleQuery ? `${titleQuery} hindi songs similar mix` : 'Top Trending Hindi Bollywood Hits 2026');
        } else {
          queryTerm = normSeedArtist
            ? `${targetSeedArtist} radio mix similar songs`
            : 'Trending Music Hits';
        }
        const searchRes = await fetch(`/api/search?q=${encodeURIComponent(queryTerm)}`);
        if (searchRes.ok) {
          const searchData = await searchRes.json();
          if (Array.isArray(searchData) && currentReqId === state.radioRequestId) {
            const existingIds = new Set([...playedSet, ...filtered.map(t => t.id)]);
            searchData.forEach(st => {
              if (st && st.id && !existingIds.has(st.id)) {
                if (isCurrentIndian && isBlatantWesternTrack(st.title, st.artist)) {
                  return;
                }
                existingIds.add(st.id);
                filtered.push(st);
              }
            });
          }
        }
      } catch (fbErr) {
        console.warn('[Discovery fallback error]:', fbErr);
      }
    }

    if (currentReqId !== state.radioRequestId) return;

    // 3. Client-side diversity: ensure the immediate next recommendation is a related/different singer
    if (normSeedArtist && filtered.length > 1) {
      const firstArtist = cleanPrimaryArtist(filtered[0].artist);
      if (firstArtist === normSeedArtist) {
        const swapIdx = filtered.findIndex(t => cleanPrimaryArtist(t.artist) !== normSeedArtist);
        if (swapIdx > 0) {
          const [diffTrack] = filtered.splice(swapIdx, 1);
          filtered.unshift(diffTrack);
        }
      }
    }

    // 4. Queue prioritization: FRESH recommendations for the current track MUST be placed AT THE FRONT!
    // Never let old Western tracks from a previous session remain ahead of newly generated recommendations!
    const existingValid = (state.radioQueue || []).filter(t => t && t.id && !playedSet.has(t.id));
    let cleanedExisting = existingValid;
    if (isCurrentIndian) {
      // Purge any Western pop remnants left over from startup or previous sessions
      cleanedExisting = existingValid.filter(t => !isBlatantWesternTrack(t.title, t.artist));
    }
    const newIds = new Set(filtered.map(t => t.id));
    const toAppend = cleanedExisting.filter(t => !newIds.has(t.id));
    state.radioQueue = [...filtered, ...toAppend].slice(0, 50);

    state.radioLoading = false;

    // Update Radio Automix view if user navigated there
    const list = $('radio-tracks-list');
    if (list) {
      list.innerHTML = '';
      state.radioQueue.forEach((track, idx) => {
        const row = createTrackRow(track, idx + 1);
        list.appendChild(row);
      });
    }

    const radioHeading = $('radio-seed-heading');
    if (radioHeading && state.currentTrack) {
      radioHeading.textContent = `Automix: ${state.currentTrack.title}`;
    }

    // Refresh Queue Drawer badge and recommended song list
    updateQueueBadge();
    renderQueueDrawer();
  } catch (err) {
    console.warn('[Automix error]:', err);
    if (currentReqId === state.radioRequestId) {
      state.radioLoading = false;
      renderQueueDrawer();
    }
  }
}

// ============================================================================
// Synchronized Lyrics Engine
// ============================================================================
const clientLyricsCache = new Map();

function cleanTitleForLyrics(raw) {
  return (raw || '')
    .replace(/\s*[\(\[](?:official\s*(?:video|audio|music\s*video|lyric\s*video|visualizer)?|lyrics?|4k|hd|remastered|audio|hq)[\)\]]|\s*\|\s*.*$/gi, '')
    .replace(/\s*\b(ft\.?|feat\.?)\b.*$/gi, '')
    .trim();
}

async function fetchLyrics(track) {
  state.lyrics.synced = [];
  state.lyrics.plain = '';
  state.lyrics.activeIndex = -1;

  if (state.lyricsEventSource) {
    try { state.lyricsEventSource.close(); } catch (e) {}
    state.lyricsEventSource = null;
  }

  if ($('lyrics-track-title')) $('lyrics-track-title').textContent = track.title;
  if ($('lyrics-track-artist')) $('lyrics-track-artist').textContent = track.artist;
  const wrapper = $('lyrics-lines-wrapper');

  let cleanTitle = cleanTitleForLyrics(track.title);
  let cleanArtist = cleanTitleForLyrics(track.artist);

  // Eliminate generic placeholder artist like "Release" or "Release - Topic"
  const isGenericArtist = !cleanArtist || /^(?:release(?:\s*-\s*topic)?|various artists|topic|unknown(?: artist)?)$/i.test(cleanArtist);
  if (isGenericArtist) {
    if (track.title && /sicklot/i.test(track.title)) {
      cleanArtist = 'SickLot';
      track.artist = 'SickLot';
    } else if (/la la la/i.test(cleanTitle)) {
      cleanArtist = 'SickLot';
      track.artist = 'SickLot';
    } else {
      cleanArtist = '';
    }
    if (track.artist && $('lyrics-track-artist')) {
      $('lyrics-track-artist').textContent = track.artist;
    }
  }

  const cacheKey = `${cleanTitle.toLowerCase()}|||${cleanArtist.toLowerCase()}`;

  // 1. Instant Cache Hit (0ms)
  if (clientLyricsCache.has(cacheKey)) {
    const cachedData = clientLyricsCache.get(cacheKey);
    if (cachedData.cues && cachedData.cues.length) {
      state.lyrics.synced = cachedData.cues;
      renderSyncedLyrics();
      return;
    } else if (cachedData.syncedLyrics) {
      state.lyrics.synced = parseLrc(cachedData.syncedLyrics);
      renderSyncedLyrics();
      return;
    } else if (cachedData.plainLyrics) {
      state.lyrics.plain = cachedData.plainLyrics;
      renderPlainLyrics();
      return;
    }
  }

  // 2. Shimmer Skeleton Loading State
  if (wrapper) {
    wrapper.innerHTML = `
      <div class="lyrics-skeleton-loader">
        <div class="skeleton-line w-80"></div>
        <div class="skeleton-line w-60"></div>
        <div class="skeleton-line w-90"></div>
        <div class="skeleton-line w-70"></div>
        <div class="skeleton-line w-50"></div>
      </div>
    `;
  }

  if ($('mini-lyrics-current')) $('mini-lyrics-current').textContent = 'Connecting real-time lyrics stream...';
  if ($('mini-lyrics-next')) $('mini-lyrics-next').textContent = 'Direct Audio Opus Stream';

  // 3. Server-Sent Events (SSE) Real-Time Timeline Connection
  let sseHandled = false;
  if (window.EventSource) {
    try {
      const sseUrl = `/api/lyrics/sse?title=${encodeURIComponent(cleanTitle)}&artist=${encodeURIComponent(cleanArtist)}&id=${encodeURIComponent(track.id || '')}`;
      const es = new EventSource(sseUrl);
      state.lyricsEventSource = es;

      es.addEventListener('manifest', (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && payload.cues && payload.cues.length) {
            sseHandled = true;
            clientLyricsCache.set(cacheKey, { cues: payload.cues, instrumental: payload.instrumental });
            if (state.currentTrack && state.currentTrack.id === track.id) {
              state.lyrics.synced = payload.cues;
              renderSyncedLyrics();
              const miniCurrent = $('mini-lyrics-current');
              const miniNext = $('mini-lyrics-next');
              if (miniCurrent && state.lyrics.synced[0]) miniCurrent.textContent = `"${state.lyrics.synced[0].text}"`;
              if (miniNext && state.lyrics.synced[1]) miniNext.textContent = `"${state.lyrics.synced[1].text}"`;
            }
          }
        } catch (err) {
          console.warn('[Lyrics SSE parse error]:', err);
        }
        es.close();
        state.lyricsEventSource = null;
      });

      es.onerror = () => {
        es.close();
        state.lyricsEventSource = null;
        if (!sseHandled) {
          executeStandardLyricsFetch(cleanTitle, cleanArtist, cacheKey, wrapper, track);
        }
      };

      // Fallback timer
      setTimeout(() => {
        if (!sseHandled && (!state.lyrics.synced || !state.lyrics.synced.length)) {
          if (state.lyricsEventSource) {
            try { state.lyricsEventSource.close(); } catch (e) {}
            state.lyricsEventSource = null;
          }
          executeStandardLyricsFetch(cleanTitle, cleanArtist, cacheKey, wrapper, track);
        }
      }, 3000);
      return;
    } catch (e) {
      console.warn('[SSE connect exception]:', e);
    }
  }

  executeStandardLyricsFetch(cleanTitle, cleanArtist, cacheKey, wrapper, track);
}

async function executeStandardLyricsFetch(cleanTitle, cleanArtist, cacheKey, wrapper, track) {
  try {
    const res = await fetch(`/api/lyrics?title=${encodeURIComponent(cleanTitle)}&artist=${encodeURIComponent(cleanArtist)}&id=${encodeURIComponent(track.id || '')}`);
    if (!res.ok) throw new Error('Lyrics not found');
    const data = await res.json();
    clientLyricsCache.set(cacheKey, data);

    if (state.currentTrack && state.currentTrack.id === track.id) {
      if (data.syncedLyrics) {
        state.lyrics.synced = parseLrc(data.syncedLyrics);
        renderSyncedLyrics();
        const miniCurrent = $('mini-lyrics-current');
        const miniNext = $('mini-lyrics-next');
        if (miniCurrent && state.lyrics.synced[0]) miniCurrent.textContent = `"${state.lyrics.synced[0].text}"`;
        if (miniNext && state.lyrics.synced[1]) miniNext.textContent = `"${state.lyrics.synced[1].text}"`;
      } else if (data.plainLyrics) {
        state.lyrics.plain = data.plainLyrics;
        renderPlainLyrics();
        if ($('mini-lyrics-current')) $('mini-lyrics-current').textContent = 'Tap to view song lyrics';
        if ($('mini-lyrics-next')) $('mini-lyrics-next').textContent = 'Direct Audio Opus Stream';
      } else {
        if (wrapper) wrapper.innerHTML = `<p class="lyric-line">No synchronized lyrics found for this track.</p>`;
        if ($('mini-lyrics-current')) $('mini-lyrics-current').textContent = 'Instrumental or plain playback';
      }
    }
  } catch (err) {
    if (wrapper && state.currentTrack && state.currentTrack.id === track.id) {
      wrapper.innerHTML = `<p class="lyric-line">No lyrics available for this track.</p>`;
    }
    if ($('mini-lyrics-current')) $('mini-lyrics-current').textContent = 'Tap for lyrics studio';
  }
}

function parseLrc(lrcText) {
  const lines = lrcText.split('\n');
  const result = [];
  const regex = /\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/;

  for (const line of lines) {
    const match = regex.exec(line);
    if (match) {
      const mins = parseInt(match[1], 10);
      const secs = parseInt(match[2], 10);
      const ms = parseFloat(`0.${match[3]}`);
      const time = mins * 60 + secs + ms;
      const text = match[4].trim();
      if (text) {
        result.push({ time, text });
      }
    }
  }
  return result;
}

function renderSyncedLyrics() {
  const wrapper = $('lyrics-lines-wrapper');
  if (!wrapper) return;
  wrapper.innerHTML = '';

  state.lyrics.synced.forEach((item, index) => {
    const p = document.createElement('p');
    p.className = 'lyric-line';
    p.dataset.index = index;
    p.dataset.time = item.time;
    p.textContent = item.text;
    p.addEventListener('click', () => {
      seekPlayerTo(item.time);
    });
    wrapper.appendChild(p);
  });
}

function renderPlainLyrics() {
  const wrapper = $('lyrics-lines-wrapper');
  if (!wrapper) return;
  wrapper.innerHTML = '';
  const lines = state.lyrics.plain.split('\n');
  lines.forEach(line => {
    if (line.trim()) {
      const p = document.createElement('p');
      p.className = 'lyric-line';
      p.textContent = line;
      wrapper.appendChild(p);
    }
  });
}

function updateLyricsSync(currentTime) {
  // 1. Karaoke Intro Countdown Handling
  const countdownEl = $('karaoke-countdown-badge');
  if (state.karaokeMode && state.lyrics.synced && state.lyrics.synced.length > 0) {
    const firstVocalTime = state.lyrics.synced[0].time;
    if (currentTime < firstVocalTime - 0.2) {
      const remainingSec = Math.ceil(firstVocalTime - currentTime);
      if (countdownEl) {
        countdownEl.classList.remove('hidden');
        countdownEl.textContent = `Singing starts in ${remainingSec}s`;
      }
    } else {
      if (countdownEl) countdownEl.classList.add('hidden');
    }
  } else {
    if (countdownEl) countdownEl.classList.add('hidden');
  }

  if (!state.lyrics.synced.length) return;

  let activeIdx = -1;
  for (let i = 0; i < state.lyrics.synced.length; i++) {
    if (currentTime >= state.lyrics.synced[i].time) {
      activeIdx = i;
    } else {
      break;
    }
  }

  if (activeIdx !== state.lyrics.activeIndex && activeIdx !== -1) {
    state.lyrics.activeIndex = activeIdx;

    // Update real-time mini lyrics in the right player column
    const miniCurrent = $('mini-lyrics-current');
    const miniNext = $('mini-lyrics-next');
    if (miniCurrent && state.lyrics.synced[activeIdx]) {
      miniCurrent.textContent = `"${state.lyrics.synced[activeIdx].text}"`;
    }
    if (miniNext) {
      const nextLine = state.lyrics.synced[activeIdx + 1];
      miniNext.textContent = nextLine ? `"${nextLine.text}"` : 'Direct Audio Opus Stream';
    }

    const overlay = $('lyrics-overlay');
    if (overlay && !overlay.classList.contains('hidden')) {
      const lines = document.querySelectorAll('.lyric-line');
      lines.forEach((line, idx) => {
        if (idx === activeIdx) {
          line.classList.add('active');
          line.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          line.classList.remove('active');
          line.style.removeProperty('--karaoke-progress');
        }
      });
    }
  }

  // 2. Real-Time Karaoke Text Gradient Sweep on the Active Line
  if (state.karaokeMode && state.lyrics.activeIndex >= 0 && state.lyrics.synced[state.lyrics.activeIndex]) {
    const curCue = state.lyrics.synced[state.lyrics.activeIndex];
    const nextCue = state.lyrics.synced[state.lyrics.activeIndex + 1];
    const lineDur = curCue.duration || (nextCue ? Math.max(0.5, nextCue.time - curCue.time) : 4.0);
    const elapsed = Math.max(0, currentTime - curCue.time);
    const progressPct = Math.min(100, Math.max(0, (elapsed / lineDur) * 100));

    const activeLineEl = document.querySelector('.lyric-line.active');
    if (activeLineEl) {
      activeLineEl.style.setProperty('--karaoke-progress', `${progressPct}%`);
    }
  }
}

function openLyrics() {
  const overlay = $('lyrics-overlay');
  overlay?.classList.remove('hidden');
  state.lyrics.isOpen = true;
  updateDockActive('dock-btn-music');

  if (state.currentTrack) {
    if (!state.lyrics.synced || !state.lyrics.synced.length) {
      fetchLyrics(state.currentTrack);
    } else {
      const curTime = (isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function')
        ? (ytPlayer.getCurrentTime() || 0)
        : (audio ? audio.currentTime : 0);
      updateLyricsSync(curTime);
    }
  }
}
window.openLyrics = openLyrics;

function closeLyrics() {
  const overlay = $('lyrics-overlay');
  overlay?.classList.add('hidden');
  state.lyrics.isOpen = false;
  if (state.activeView === 'home') {
    updateDockActive('dock-btn-home');
  } else {
    updateDockActive('dock-btn-music');
  }
}
window.closeLyrics = closeLyrics;

// ============================================================================

function handleSearch(query, immediate = false) {
  if (!query || !query.trim()) {
    // Keep user on search view and show discovery state
    if (state.activeView === 'search') {
      renderSearchDiscoveryState();
    }
    return;
  }

  const cleanQuery = query.trim();
  switchView('search');

  // Sync inputs and clear buttons
  const mainInput = $('search-input');
  const inViewInput = $('in-view-search-input');
  if (mainInput && mainInput.value !== cleanQuery) mainInput.value = cleanQuery;
  if (inViewInput && inViewInput.value !== cleanQuery) inViewInput.value = cleanQuery;
  $('search-clear-btn')?.classList.remove('hidden');
  $('in-view-search-clear')?.classList.remove('hidden');

  // Always reset search filter to 'all' so results are never collapsed to 1 track
  state.activeSearchFilter = 'all';
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.filter === 'all');
  });

  const loading = $('search-loading');
  const resultsList = $('search-results-list');
  const titleEl = $('search-view-title');
  if (titleEl) titleEl.textContent = `Search Results: "${cleanQuery}"`;

  if (loading) loading.classList.remove('hidden');

  clearTimeout(state.searchDebounceTimer);

  const performSearch = async () => {
    if (desktopSearchAbort) {
      desktopSearchAbort.abort();
    }
    desktopSearchAbort = new AbortController();

    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(cleanQuery)}&limit=20`, {
        signal: desktopSearchAbort.signal
      });
      if (loading) loading.classList.add('hidden');
      if (!res.ok) throw new Error('Search failed with status ' + res.status);
      const tracks = await res.json();
      state.lastSearchResults = Array.isArray(tracks) ? tracks : [];
      renderSearchResults(state.lastSearchResults);
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (loading) loading.classList.add('hidden');
      if (resultsList) resultsList.innerHTML = `<p style="color:var(--text-muted); padding:20px;">No tracks found for "${escapeHTML(cleanQuery)}".</p>`;
    }
  };

  if (immediate) {
    performSearch();
  } else {
    state.searchDebounceTimer = setTimeout(performSearch, 300);
  }
}

function renderSearchDiscoveryState() {
  const container = $('search-results-list');
  const titleEl = $('search-view-title');
  if (titleEl) titleEl.textContent = 'Explore & Search Music';

  const recent = typeof getRecentSearches === 'function' ? getRecentSearches() : [];
  const trendingTags = [
    { label: '🔥 Trending Hits', q: 'Trending Global and Indian Hits' },
    { label: 'Arijit Singh', q: 'Arijit Singh' },
    { label: 'The Weeknd', q: 'The Weeknd' },
    { label: 'Taylor Swift', q: 'Taylor Swift' },
    { label: 'Coldplay', q: 'Coldplay' },
    { label: 'Travis Scott', q: 'Travis Scott' },
    { label: 'Lo-Fi Study Chill', q: 'Lo-Fi Chill Relax Beats' },
    { label: 'Bollywood Retro', q: 'Bollywood Classics Retro Hits' },
    { label: 'Desi Hip-Hop', q: 'Desi Hip Hop Hits' },
    { label: 'Punjabi Wave', q: 'Karan Aujla Diljit Dosanjh Punjabi Hits' },
    { label: 'Deep Focus', q: 'Deep Focus Ambient Electronic Beats' }
  ];

  let html = `
    <div class="search-discovery-wrapper">
      <div class="search-prompt-hero">
        <div class="search-prompt-icon-ring">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>
        <h3 class="search-prompt-title">What would you like to hear?</h3>
        <p class="search-prompt-subtitle">Type any artist, song, album, or paste a YouTube URL to stream immediately.</p>
      </div>
  `;

  if (recent.length > 0) {
    html += `
      <div class="search-discovery-section">
        <div class="search-discovery-section-header">
          <span class="search-discovery-section-title">Recent Searches</span>
          <button type="button" class="search-discovery-clear-btn" id="btn-discovery-clear-recents">Clear All</button>
        </div>
        <div class="search-discovery-chips" id="discovery-recent-chips">
          ${recent.map(r => `
            <div class="discovery-chip" data-query="${escapeHTML(r)}" role="button" tabindex="0">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              <span>${escapeHTML(r)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  html += `
      <div class="search-discovery-section">
        <div class="search-discovery-section-header">
          <span class="search-discovery-section-title">Trending & Recommended</span>
        </div>
        <div class="search-discovery-chips">
          ${trendingTags.map(t => `
            <button type="button" class="discovery-trending-pill" data-query="${escapeHTML(t.q)}">
              ${escapeHTML(t.label)}
            </button>
          `).join('')}
        </div>
      </div>

      <div class="search-discovery-section">
        <div class="search-discovery-section-header">
          <span class="search-discovery-section-title">Browse Music Categories</span>
        </div>
        <div class="search-discovery-genres-grid">
          <div class="discovery-genre-card" data-query="Pop Hits" style="--card-hue: 330deg;" role="button" tabindex="0">
            <span class="discovery-genre-name">Pop</span>
          </div>
          <div class="discovery-genre-card" data-query="Hip Hop and Rap Hits" style="--card-hue: 25deg;" role="button" tabindex="0">
            <span class="discovery-genre-name">Hip-Hop</span>
          </div>
          <div class="discovery-genre-card" data-query="Electronic Dance EDM" style="--card-hue: 260deg;" role="button" tabindex="0">
            <span class="discovery-genre-name">Electronic</span>
          </div>
          <div class="discovery-genre-card" data-query="Indie Acoustic Alternative" style="--card-hue: 145deg;" role="button" tabindex="0">
            <span class="discovery-genre-name">Indie & Acoustic</span>
          </div>
          <div class="discovery-genre-card" data-query="Bollywood Melodies and Hits" style="--card-hue: 45deg;" role="button" tabindex="0">
            <span class="discovery-genre-name">Bollywood</span>
          </div>
          <div class="discovery-genre-card" data-query="Lo-Fi Chill Beats Study" style="--card-hue: 200deg;" role="button" tabindex="0">
            <span class="discovery-genre-name">Lo-Fi</span>
          </div>
        </div>
      </div>
    </div>
  `;

  if (container) {
    container.innerHTML = html;

    // Attach click listeners for chips
    container.querySelectorAll('.discovery-chip, .discovery-trending-pill, .discovery-genre-card').forEach(el => {
      el.addEventListener('click', () => {
        const q = el.dataset.query;
        if (q) {
          const mainInput = $('search-input');
          const inViewInput = $('in-view-search-input');
          if (mainInput) mainInput.value = q;
          if (inViewInput) inViewInput.value = q;
          $('search-clear-btn')?.classList.remove('hidden');
          $('in-view-search-clear')?.classList.remove('hidden');
          if (typeof saveRecentSearch === 'function') saveRecentSearch(q);
          handleSearch(q, true);
        }
      });
    });

    container.querySelector('#btn-discovery-clear-recents')?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (typeof clearAllRecentSearches === 'function') clearAllRecentSearches();
      renderSearchDiscoveryState();
    });
  }
}

function renderSearchResults(tracks) {
  const container = $('search-results-list');
  if (!container) return;
  container.innerHTML = '';

  let list = tracks || [];
  const filter = state.activeSearchFilter || 'all';
  const currentQuery = $('search-input')?.value?.toLowerCase()?.trim() || '';

  if (filter === 'artists' && currentQuery) {
    const artistMatches = list.filter(t => (t.artist || '').toLowerCase().includes(currentQuery));
    if (artistMatches.length > 0) {
      list = artistMatches;
    }
  } else if (filter === 'albums' && currentQuery) {
    const albumMatches = list.filter(t => (t.album || '').toLowerCase().includes(currentQuery) || (t.title || '').toLowerCase().includes(currentQuery));
    if (albumMatches.length > 0) {
      list = albumMatches;
    }
  }

  if (!list.length) {
    container.innerHTML = `<p style="color:var(--text-muted); padding:20px;">No matching tracks found.</p>`;
    return;
  }

  list.forEach((track, index) => {
    const row = createTrackRow(track, index + 1);
    container.appendChild(row);
  });
}

// ============================================================================
// Neumorphic Dock & Navigation Helpers
// ============================================================================
function updateDockActive(activeId) {
  document.querySelectorAll('.neu-dock-item').forEach(item => {
    if (item.id === activeId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
}

function updateDockPopoverUser() {
  const user = state.user || DEFAULT_USER;
  const nameEl = $('dock-popover-name');
  const avatarEl = $('dock-popover-avatar');
  if (nameEl) nameEl.textContent = user.name;
  if (avatarEl) avatarEl.src = user.avatar;
}

function toggleDockUserPopover(forceClose = false) {
  const popover = $('dock-user-popover');
  if (!popover) return;
  if (forceClose || !popover.classList.contains('hidden')) {
    popover.classList.add('hidden');
    if (state.activeView === 'home') {
      updateDockActive('dock-btn-home');
    } else {
      updateDockActive('dock-btn-music');
    }
  } else {
    updateDockPopoverUser();
    popover.classList.remove('hidden');
    updateDockActive('dock-btn-user');
  }
}

// ============================================================================
// View Navigation
// ============================================================================
function switchView(viewName, subMode = 'favourites') {
  const views = {
    home: $('view-home'),
    search: $('view-search'),
    library: $('view-library'),
    radio: $('view-radio')
  };

  if (!views[viewName]) return;
  state.activeView = viewName;

  Object.values(views).forEach(v => v?.classList.remove('active'));
  views[viewName].classList.add('active');

  if (viewName === 'library') {
    if (subMode === 'recent') {
      renderLibraryHistory();
    } else {
      renderLikedTracks();
    }
  }

  // Update active navigation item
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.dataset.view === viewName || (viewName === 'library' && item.dataset.view === subMode)) {
      item.classList.add('active');
    } else if (item.dataset.view) {
      item.classList.remove('active');
    }
  });

  // Sync floating dock active status
  if (viewName === 'home') {
    updateDockActive('dock-btn-home');
  } else if (viewName === 'search') {
    updateDockActive('dock-btn-search');
  } else {
    updateDockActive('dock-btn-music');
  }
}

function handleNavigationClick(view) {
  // Update active state across all nav items
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === view);
  });

  switch (view) {
    case 'home':
      switchView('home');
      $('main-feed')?.scrollTo({ top: 0, behavior: 'smooth' });
      showToastNotification('Explore Home Feed');
      break;

    case 'search':
      switchView('search');
      const searchBoxInput = $('in-view-search-input') || $('search-input');
      if (searchBoxInput && searchBoxInput.value.trim()) {
        handleSearch(searchBoxInput.value.trim(), true);
      } else {
        renderSearchDiscoveryState();
      }
      setTimeout(() => {
        searchBoxInput?.focus();
        searchBoxInput?.select();
      }, 50);
      showToastNotification('Search & Discover Music');
      break;

    case 'genres':
      switchView('home');
      setTimeout(() => {
        const grid = $('genres-grid') || document.querySelector('.split-col-genres');
        if (grid) {
          grid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 80);
      showToastNotification('Explore Genres & Moods');
      break;

    case 'albums':
    case 'lib-albums':
      switchView('search');
      document.querySelectorAll('.filter-pill').forEach(p => {
        p.classList.toggle('active', p.dataset.filter === 'albums');
      });
      state.activeSearchFilter = 'albums';
      const albumQuery = 'Top Trending Albums';
      if ($('search-input')) $('search-input').value = albumQuery;
      handleSearch(albumQuery);
      showToastNotification('Browsing Trending Albums');
      break;

    case 'artists':
      switchView('home');
      setTimeout(() => {
        const row = $('artists-row') || document.querySelector('.top-artists-section');
        if (row) {
          row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 80);
      showToastNotification('Discover Top Artists');
      break;

    case 'radio':
      switchView('radio');
      if (!state.radioQueue || state.radioQueue.length === 0) {
        if (state.currentTrack) {
          loadRadioQueue(state.currentTrack.id, state.currentTrack.artist, state.currentTrack.title);
        } else if (state.featuredTracks.length > 0) {
          loadRadioQueue(state.featuredTracks[0].id, state.featuredTracks[0].artist, state.featuredTracks[0].title);
        } else {
          loadRadioQueue(HERO_SLIDES[1].id, HERO_SLIDES[1].artist, HERO_SLIDES[1].title);
        }
      }
      showToastNotification('Continuous Radio Station');
      break;

    case 'recent':
      switchView('library', 'recent');
      showToastNotification('Recently Played Songs');
      break;

    case 'favourites':
      switchView('library', 'favourites');
      showToastNotification('Your Liked Songs');
      break;

    case 'queue':
      openQueueDrawer();
      break;

    case 'local':
      $('local-audio-file-input')?.click();
      break;

    case 'jukebox':
      openJukeboxModal();
      showToastNotification('Party Jukebox Station');
      break;

    default:
      switchView('home');
  }
}

// ============================================================================
// Liked Songs & History Management
// ============================================================================
function toggleLike(track) {
  if (!track || !track.id) return;
  const existsIdx = state.likedTracks.findIndex(t => t.id === track.id);
  const willLike = existsIdx === -1;
  if (!willLike) {
    state.likedTracks.splice(existsIdx, 1);
  } else {
    state.likedTracks.unshift(track);
  }

  localStorage.setItem('songbuddy_liked_tracks', JSON.stringify(state.likedTracks));
  renderLikedTracks();

  const isLiked = state.likedTracks.some(t => t.id === track.id);
  if (state.currentTrack && state.currentTrack.id === track.id) {
    $('hero-heart-btn')?.classList.toggle('liked', isLiked);
    $('btn-neu-heart')?.classList.toggle('liked', isLiked);
  }
  showToastNotification(willLike ? `Saved "${track.title}" to Favorites` : `Removed "${track.title}" from Favorites`);
}

function renderLikedTracks() {
  const display = $('liked-count-display');
  const heading = document.querySelector('.library-heading');
  const tag = document.querySelector('.library-hero-text .hero-tag');
  const heartBox = document.querySelector('.library-heart-box');

  if (heading) heading.textContent = 'Liked Songs';
  if (tag) tag.textContent = 'COLLECTION';
  if (display) display.textContent = `${state.likedTracks.length} songs saved`;
  if (heartBox) {
    heartBox.innerHTML = `
      <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
      </svg>
    `;
  }

  const list = $('liked-tracks-list');
  if (!list) return;
  list.innerHTML = '';

  if (state.likedTracks.length === 0) {
    list.innerHTML = `
      <div style="text-align:center; padding: 48px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;">No favourite songs saved yet</p>
        <p style="font-size: 0.88rem; opacity: 0.8;">Tap the heart icon on any playing track to save it here.</p>
      </div>
    `;
    return;
  }

  state.likedTracks.forEach((track, index) => {
    const row = createTrackRow(track, index + 1);
    list.appendChild(row);
  });
}

function renderLibraryHistory() {
  const display = $('liked-count-display');
  const heading = document.querySelector('.library-heading');
  const tag = document.querySelector('.library-hero-text .hero-tag');
  const heartBox = document.querySelector('.library-heart-box');

  if (heading) heading.textContent = 'Recently Played';
  if (tag) tag.textContent = 'LISTENING HISTORY';
  if (display) display.textContent = `${state.history.length} songs in history`;
  if (heartBox) {
    heartBox.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12 6 12 12 16 14"></polyline>
      </svg>
    `;
  }

  const list = $('liked-tracks-list');
  if (!list) return;
  list.innerHTML = '';

  if (state.history.length === 0) {
    list.innerHTML = `
      <div style="text-align:center; padding: 48px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;">No listening history yet</p>
        <p style="font-size: 0.88rem; opacity: 0.8;">Play any track from Explore or Search to see your listening history here.</p>
      </div>
    `;
    return;
  }

  state.history.forEach((track, index) => {
    const row = createTrackRow(track, index + 1);
    list.appendChild(row);
  });
}

// ============================================================================
// Multi-Tab Library Management Hub (Favourites, Playlists, On Repeat, Recent, Most Played, Offline, Local)
// ============================================================================
function switchLibraryTab(tabName) {
  state.activeLibraryTab = tabName;
  document.querySelectorAll('.lib-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  const dropzoneWrap = $('local-dropzone-container');
  if (dropzoneWrap) {
    dropzoneWrap.classList.toggle('hidden', tabName !== 'local');
  }

  const customShelf = $('custom-playlists-shelf');
  if (customShelf) {
    customShelf.classList.toggle('hidden', tabName !== 'custom');
  }

  const headingTitle = $('library-heading-title');
  const heroTag = $('library-hero-tag');

  if (tabName === 'favourites') {
    if (headingTitle) headingTitle.textContent = 'Liked Songs';
    if (heroTag) heroTag.textContent = 'PERSONAL COLLECTION';
    renderLikedTracks();
  } else if (tabName === 'custom') {
    if (headingTitle) headingTitle.textContent = 'Custom Playlists';
    if (heroTag) heroTag.textContent = 'SAVED PLAYLISTS';
    renderCustomPlaylistsShelf();
  } else if (tabName === 'on-repeat') {
    if (headingTitle) headingTitle.textContent = 'On Repeat';
    if (heroTag) heroTag.textContent = 'SMART AUTO-GENERATED';
    renderOnRepeatTracks();
  } else if (tabName === 'recent') {
    if (headingTitle) headingTitle.textContent = 'Recently Played';
    if (heroTag) heroTag.textContent = 'PLAYBACK HISTORY';
    renderLibraryHistory();
  } else if (tabName === 'most-played') {
    if (headingTitle) headingTitle.textContent = 'Most Played';
    if (heroTag) heroTag.textContent = 'TOP SCROBBLES';
    renderMostPlayedTracks();
  } else if (tabName === 'offline') {
    if (headingTitle) headingTitle.textContent = 'Saved Offline';
    if (heroTag) heroTag.textContent = 'OFFLINE CACHE (INDEXEDDB)';
    renderOfflineTracks();
  } else if (tabName === 'local') {
    if (headingTitle) headingTitle.textContent = 'Local Audio Files';
    if (heroTag) heroTag.textContent = 'ID3 TAG & OFFLINE STUDIO';
    renderLocalLibraryTracks();
  }
}

// ============================================================================
// IndexedDB Offline Cache Engine ("SongBuddyOfflineDB")
// ============================================================================
const OfflineDB = {
  db: null,
  async init() {
    if (this.db) return this.db;
    return new Promise((resolve) => {
      if (!window.indexedDB) {
        console.warn('[OfflineDB] IndexedDB not supported by client.');
        resolve(null);
        return;
      }
      const request = indexedDB.open('songbuddy_offline_db', 1);
      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('offline_tracks')) {
          const store = db.createObjectStore('offline_tracks', { keyPath: 'id' });
          store.createIndex('savedAt', 'savedAt', { unique: false });
        }
      };
      request.onsuccess = (e) => {
        this.db = e.target.result;
        resolve(this.db);
      };
      request.onerror = (e) => {
        console.warn('[OfflineDB init error]:', e);
        resolve(null);
      };
    });
  },

  async saveTrack(track) {
    const db = await this.init();
    if (!db) return false;
    try {
      showToastNotification(`Downloading "${track.title}" for offline playback...`);
      const q = (state.audioEngine && state.audioEngine.quality) || 'high';
      const streamUrl = track.streamUrl || `/api/stream?id=${encodeURIComponent(track.id)}&quality=${q}`;
      const res = await fetch(streamUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();

      const item = {
        id: track.id,
        title: track.title,
        artist: track.artist,
        album: track.album || 'Single',
        duration: track.duration || 0,
        duration_formatted: track.duration_formatted || formatTime(track.duration || 0),
        thumbnail: track.thumbnail || '',
        audioBlob: blob,
        mimeType: blob.type || 'audio/webm',
        savedAt: Date.now()
      };

      return new Promise((resolve) => {
        const tx = db.transaction('offline_tracks', 'readwrite');
        const store = tx.objectStore('offline_tracks');
        store.put(item);
        tx.oncomplete = () => {
          showToastNotification(`"${track.title}" saved offline!`);
          if (state.activeLibraryTab === 'offline') renderOfflineTracks();
          resolve(true);
        };
        tx.onerror = () => resolve(false);
      });
    } catch (err) {
      console.warn('[Offline save failed]:', err);
      showToastNotification(`Offline caching failed: ${err.message}`, 4000);
      return false;
    }
  },

  async getTracks() {
    const db = await this.init();
    if (!db) return [];
    return new Promise((resolve) => {
      const tx = db.transaction('offline_tracks', 'readonly');
      const store = tx.objectStore('offline_tracks');
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  },

  async deleteTrack(trackId) {
    const db = await this.init();
    if (!db) return false;
    return new Promise((resolve) => {
      const tx = db.transaction('offline_tracks', 'readwrite');
      const store = tx.objectStore('offline_tracks');
      store.delete(trackId);
      tx.oncomplete = () => {
        showToastNotification('Removed track from offline storage.');
        if (state.activeLibraryTab === 'offline') renderOfflineTracks();
        resolve(true);
      };
      tx.onerror = () => resolve(false);
    });
  }
};

// ============================================================================
// Server-Synchronized User Library & Persistence
// ============================================================================
async function syncUserLibrary() {
  const token = localStorage.getItem('songbuddy_token');
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  try {
    // 1. Fetch custom playlists
    const plRes = await fetch('/api/user/playlists', { headers });
    if (plRes.ok) {
      state.userPlaylists = await plRes.json();
    }

    // 2. Fetch favorites
    const favRes = await fetch('/api/user/favorites', { headers });
    if (favRes.ok) {
      const serverFavs = await favRes.json();
      if (serverFavs && serverFavs.length > 0) {
        state.likedTracks = serverFavs;
        localStorage.setItem('songbuddy_liked_tracks', JSON.stringify(serverFavs));
        updateLikedCountDisplay();
      }
    }

    // 3. Fetch smart playlists ("On Repeat", "Recently Played", "Jump Back In")
    const smartRes = await fetch('/api/user/smart-playlists', { headers });
    if (smartRes.ok) {
      state.smartPlaylists = await smartRes.json();
    }
  } catch (err) {
    console.debug('[User library sync notice]:', err);
  }
}

function renderCustomPlaylistsShelf() {
  const shelf = $('custom-playlists-shelf');
  const grid = $('custom-playlists-grid');
  const list = $('liked-tracks-list');
  if (shelf) shelf.classList.remove('hidden');
  if (list) list.innerHTML = '';

  const playlists = state.userPlaylists || [];
  if ($('liked-count-display')) {
    $('liked-count-display').textContent = `${playlists.length} playlists created`;
  }

  if (!grid) return;
  grid.innerHTML = '';

  if (playlists.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align:center; padding: 48px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;">No custom playlists yet</p>
        <p style="font-size: 0.88rem; opacity: 0.8; margin-bottom: 16px;">Create your own playlist or import one from Spotify, YouTube, or Apple Music!</p>
        <button type="button" class="btn-import-submit" onclick="openCreatePlaylistModal()">+ Create Playlist</button>
      </div>
    `;
    return;
  }

  playlists.forEach(pl => {
    const card = document.createElement('div');
    card.className = 'playlist-card-custom';
    const thumb = pl.cover_url || (pl.tracks && pl.tracks[0]?.thumbnail) || 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80';
    const count = pl.track_count !== undefined ? pl.track_count : (pl.tracks ? pl.tracks.length : 0);

    card.innerHTML = `
      <img src="${thumb}" alt="${escapeHTML(pl.name)}" class="custom-pl-thumb" onerror="this.src='https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80';">
      <span class="custom-pl-title">${escapeHTML(pl.name)}</span>
      <span class="custom-pl-sub">${count} tracks • ${escapeHTML(pl.description || 'Personal Mix')}</span>
      <div class="custom-pl-actions">
        <button type="button" class="btn-custom-pl-play" title="Play Playlist">Play</button>
        <button type="button" class="btn-custom-pl-del" title="Delete Playlist">&times;</button>
      </div>
    `;

    card.querySelector('.btn-custom-pl-play')?.addEventListener('click', (e) => {
      e.stopPropagation();
      if (pl.tracks && pl.tracks.length > 0) {
        state.queue = [...pl.tracks];
        saveQueueToStorage();
        renderQueueDrawer();
        playTrack(pl.tracks[0]);
        showToastNotification(`Playing playlist "${pl.name}"`);
      } else {
        showToastNotification('Playlist is empty.');
      }
    });

    card.querySelector('.btn-custom-pl-del')?.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteCustomPlaylist(pl.id, pl.name);
    });

    card.addEventListener('click', () => {
      if (pl.tracks && pl.tracks.length > 0) {
        state.queue = [...pl.tracks];
        saveQueueToStorage();
        renderQueueDrawer();
        playTrack(pl.tracks[0]);
      }
    });

    grid.appendChild(card);
  });
}

async function deleteCustomPlaylist(plId, plName) {
  if (!confirm(`Delete playlist "${plName}"?`)) return;
  const token = localStorage.getItem('songbuddy_token');
  const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };

  try {
    const res = await fetch(`/api/user/playlists/delete`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ id: plId })
    });
    if (res.ok) {
      state.userPlaylists = (state.userPlaylists || []).filter(p => p.id !== plId);
      renderCustomPlaylistsShelf();
      showToastNotification(`Deleted playlist "${plName}".`);
    }
  } catch (err) {
    showToastNotification('Error deleting playlist.');
  }
}

function renderOnRepeatTracks() {
  const container = $('liked-tracks-list');
  const shelf = $('custom-playlists-shelf');
  if (shelf) shelf.classList.add('hidden');
  if (!container) return;
  container.innerHTML = '';

  const tracks = (state.smartPlaylists && state.smartPlaylists.on_repeat) || [];
  if ($('liked-count-display')) {
    $('liked-count-display').textContent = `${tracks.length} heavy rotation tracks`;
  }

  if (tracks.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;">No repeat tracks yet</p>
        <p style="font-size: 0.88rem; opacity: 0.8;">Play songs at least twice and SongBuddy will automatically generate your "On Repeat" heavy rotation!</p>
      </div>
    `;
    return;
  }

  tracks.forEach((track, index) => {
    const row = createTrackRow(track, index + 1);
    container.appendChild(row);
  });
}

async function renderOfflineTracks() {
  const container = $('liked-tracks-list');
  const shelf = $('custom-playlists-shelf');
  if (shelf) shelf.classList.add('hidden');
  if (!container) return;
  container.innerHTML = '';

  const tracks = await OfflineDB.getTracks();
  if ($('liked-count-display')) {
    $('liked-count-display').textContent = `${tracks.length} tracks cached for offline`;
  }

  if (tracks.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;">No offline songs downloaded</p>
        <p style="font-size: 0.88rem; opacity: 0.8;">Click the download icon on any track row to save it directly into device IndexedDB storage for offline playback!</p>
      </div>
    `;
    return;
  }

  tracks.forEach((track, index) => {
    // Attach offline blob URL for seamless zero-network playback
    const offlineItem = {
      ...track,
      offlineBlobUrl: URL.createObjectURL(track.audioBlob)
    };
    const row = createTrackRow(offlineItem, index + 1);
    container.appendChild(row);
  });
}

// ============================================================================
// Bulk Playlist Importer Modal Handlers
// ============================================================================
function openImportPlaylistModal() {
  const modal = $('import-playlist-modal');
  if (modal) modal.classList.remove('hidden');
  const input = $('import-playlist-url');
  if (input) {
    input.value = '';
    input.focus();
  }
  const msg = $('import-status-msg');
  if (msg) msg.classList.add('hidden');
}

function closeImportPlaylistModal() {
  const modal = $('import-playlist-modal');
  if (modal) modal.classList.add('hidden');
}

async function handleImportPlaylistSubmit() {
  const input = $('import-playlist-url');
  const msg = $('import-status-msg');
  const btn = $('btn-import-submit');
  const url = (input ? input.value : '').trim();

  if (!url) {
    if (msg) {
      msg.textContent = 'Please enter a valid Spotify, YouTube, or Apple Music link.';
      msg.className = 'import-status-message error';
      msg.classList.remove('hidden');
    }
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Importing...';
  }
  if (msg) {
    msg.textContent = 'Resolving tracklist & metadata...';
    msg.className = 'import-status-message';
    msg.classList.remove('hidden');
  }

  try {
    const res = await fetch('/api/import/playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || data.message || 'Import failed');

    const tracks = data.tracks || [];
    if (tracks.length === 0) throw new Error('No playable tracks found in playlist.');

    const newPlaylist = {
      name: data.title || 'Imported Playlist',
      description: `Imported from ${data.source ? data.source.toUpperCase() : 'URL'} (${tracks.length} tracks)`,
      tracks: tracks
    };

    const token = localStorage.getItem('songbuddy_token');
    const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };

    const saveRes = await fetch('/api/user/playlists', {
      method: 'POST',
      headers,
      body: JSON.stringify(newPlaylist)
    });
    if (saveRes.ok) {
      const saved = await saveRes.json();
      state.userPlaylists = state.userPlaylists || [];
      state.userPlaylists.unshift(saved);
    }

    if (state.queue.length === 0) {
      state.queue = [...tracks];
      saveQueueToStorage();
      renderQueueDrawer();
    }

    if (msg) {
      msg.textContent = `Successfully imported "${data.title}" with ${tracks.length} tracks!`;
      msg.className = 'import-status-message success';
    }

    showToastNotification(`Imported ${tracks.length} tracks from ${data.source.toUpperCase()}!`);
    setTimeout(() => {
      closeImportPlaylistModal();
      switchLibraryTab('custom');
    }, 1200);

  } catch (err) {
    console.warn('[Import error]:', err);
    if (msg) {
      msg.textContent = err.message || 'Failed to import playlist.';
      msg.className = 'import-status-message error';
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Import Tracks';
    }
  }
}

// ============================================================================
// Create Custom Playlist Modal Handlers
// ============================================================================
function openCreatePlaylistModal() {
  const modal = $('create-playlist-modal');
  if (modal) modal.classList.remove('hidden');
  const nameInput = $('create-playlist-name');
  if (nameInput) {
    nameInput.value = '';
    nameInput.focus();
  }
  const descInput = $('create-playlist-desc');
  if (descInput) descInput.value = '';
}

function closeCreatePlaylistModal() {
  const modal = $('create-playlist-modal');
  if (modal) modal.classList.add('hidden');
}

async function handleCreatePlaylistSubmit() {
  const nameInput = $('create-playlist-name');
  const descInput = $('create-playlist-desc');
  const name = (nameInput ? nameInput.value : '').trim();
  const desc = (descInput ? descInput.value : '').trim();

  if (!name) {
    showToastNotification('Please provide a playlist name');
    return;
  }

  const newPl = {
    name: name,
    description: desc,
    tracks: []
  };

  const token = localStorage.getItem('songbuddy_token');
  const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };

  try {
    const res = await fetch('/api/user/playlists', {
      method: 'POST',
      headers,
      body: JSON.stringify(newPl)
    });
    if (res.ok) {
      const saved = await res.json();
      state.userPlaylists = state.userPlaylists || [];
      state.userPlaylists.unshift(saved);
      showToastNotification(`Created playlist "${name}"!`);
      closeCreatePlaylistModal();
      switchLibraryTab('custom');
    }
  } catch (err) {
    console.warn('[Create playlist error]:', err);
    showToastNotification('Failed to create playlist');
  }
}

// ============================================================================
// Audio Stream Quality Selection
// ============================================================================
function setAudioQuality(quality) {
  state.audioEngine.quality = quality;
  localStorage.setItem('songbuddy_quality', quality);

  const valBadge = $('audio-quality-val');
  if (valBadge) {
    if (quality === 'low') valBadge.textContent = 'Data Saver (64k)';
    else if (quality === 'high') valBadge.textContent = 'Studio (160k)';
    else valBadge.textContent = 'Auto (Adaptive)';
  }

  document.querySelectorAll('#audio-quality-pills-row .dsp-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.quality === quality);
  });

  showToastNotification(`Audio stream quality: ${quality === 'low' ? 'Data Saver (64k Opus)' : (quality === 'high' ? 'Studio Hi-Fi (160k)' : 'Auto Adaptive')}`);
}

// ============================================================================
// Streaming Resilience & Cookie Health Check
// ============================================================================
async function checkStreamingResilienceHealth() {
  const dot = $('cookie-status-dot');
  const badge = $('cookie-status-badge');
  const sourceLabel = $('cookie-source-label');
  const expiryLabel = $('cookie-expiry-label');
  const fallbackLabel = $('cookie-fallback-label');

  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      const data = await res.json();
      const ch = data.cookie_health || {};
      const status = ch.status || 'healthy';

      if (dot) {
        dot.className = `resilience-indicator-dot ${status === 'healthy' ? 'healthy' : (status === 'expiring_soon' ? 'warning' : 'expired')}`;
      }
      if (badge) {
        badge.textContent = status === 'healthy' ? 'Session Healthy' : (status === 'expiring_soon' ? 'Expiring Soon' : 'Bypass Active');
      }
      if (sourceLabel) sourceLabel.textContent = ch.source ? ch.source.toUpperCase() : 'EMBEDDED';
      if (expiryLabel) expiryLabel.textContent = ch.days_remaining ? `${ch.days_remaining} days remaining` : 'Persistent';
      if (fallbackLabel) fallbackLabel.textContent = 'Piped / Invidious Active';
    }
  } catch (err) {
    if (badge) badge.textContent = 'Local Standalone';
  }
}

function renderMostPlayedTracks() {
  const container = $('liked-tracks-list');
  if (!container) return;
  container.innerHTML = '';

  const playCounts = state.listeningStats.playCounts || {};
  const sorted = Object.entries(playCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => {
      const parts = key.split(' - ');
      return {
        id: `scrobble-${encodeURIComponent(key)}`,
        artist: parts[0] || 'Unknown',
        title: parts.slice(1).join(' - ') || key,
        playCount: count,
        duration_formatted: `${count} plays`
      };
    });

  if ($('liked-count-display')) {
    $('liked-count-display').textContent = `${sorted.length} tracks scrobbled`;
  }

  if (sorted.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 48px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;">No listening telemetry recorded yet</p>
        <p style="font-size: 0.88rem; opacity: 0.8;">Play your favorite tracks to automatically generate personal listening stats!</p>
      </div>
    `;
    return;
  }

  sorted.forEach((track, index) => {
    const item = document.createElement('div');
    item.className = 'top-chart-item';
    item.innerHTML = `
      <span class="chart-rank">${String(index + 1).padStart(2, '0')}</span>
      <div class="chart-track-info">
        <span class="chart-track-name">${escapeHTML(track.title)}</span>
        <span class="chart-track-artist">${escapeHTML(track.artist)} • ${track.playCount} plays</span>
      </div>
      <button class="neu-card-play-btn" style="position:static;opacity:1;transform:none;" title="Search and play">
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <polygon points="8 5 19 12 8 19 8 5"></polygon>
        </svg>
      </button>
    `;
    item.querySelector('.neu-card-play-btn')?.addEventListener('click', () => {
      handleSearch(`${track.artist} ${track.title}`);
    });
    container.appendChild(item);
  });
}

function renderLocalLibraryTracks() {
  const container = $('liked-tracks-list');
  if (!container) return;
  container.innerHTML = '';

  const tracks = state.localLibrary || [];
  if ($('liked-count-display')) {
    $('liked-count-display').textContent = `${tracks.length} local track(s) indexed`;
  }

  if (tracks.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 32px 16px; color: var(--text-secondary);">
        <p style="font-size: 1.05rem; font-weight: 600; margin-bottom: 8px;">No local tracks loaded</p>
        <p style="font-size: 0.88rem; opacity: 0.8;">Drag & drop audio files (MP3, FLAC, WAV, AAC, OGG) above to extract tags and play offline.</p>
      </div>
    `;
    return;
  }

  tracks.forEach((track, index) => {
    const item = document.createElement('div');
    item.className = 'top-chart-item';
    const thumb = track.thumbnail || '/assets/icons/icon-192.png';
    item.innerHTML = `
      <span class="chart-rank">${String(index + 1).padStart(2, '0')}</span>
      <img src="${thumb}" alt="${escapeHTML(track.title)}" class="chart-thumb" onerror="this.src='/assets/icons/icon-192.png'">
      <div class="chart-track-info">
        <span class="chart-track-name">${escapeHTML(track.title)}</span>
        <span class="chart-track-artist">${escapeHTML(track.artist)}${track.album ? ' • ' + escapeHTML(track.album) : ''}</span>
      </div>
      <span class="chart-time">${track.duration_formatted || 'Local'}</span>
      <button class="neu-card-play-btn" style="position:static;opacity:1;transform:none;" title="Play local track">
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <polygon points="8 5 19 12 8 19 8 5"></polygon>
        </svg>
      </button>
    `;
    item.querySelector('.neu-card-play-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      playTrack(track);
    });
    item.addEventListener('click', () => {
      playTrack(track);
    });
    container.appendChild(item);
  });
}

// ============================================================================
// Client-Side Tag Parsing (ID3v2) & Embedded Cover Art Extraction
// ============================================================================
async function parseAudioFileMetadata(file) {
  try {
    const sliceSize = Math.min(file.size, 1024 * 1024); // 1MB buffer
    const buffer = await file.slice(0, sliceSize).arrayBuffer();
    const view = new DataView(buffer);

    if (view.byteLength >= 10 && view.getUint8(0) === 0x49 && view.getUint8(1) === 0x44 && view.getUint8(2) === 0x33) {
      const version = view.getUint8(3);
      const tagSize = ((view.getUint8(6) & 0x7F) << 21) |
                      ((view.getUint8(7) & 0x7F) << 14) |
                      ((view.getUint8(8) & 0x7F) << 7) |
                      (view.getUint8(9) & 0x7F);

      const utf8 = new TextDecoder('utf-8');
      const iso = new TextDecoder('iso-8859-1');
      const utf16 = new TextDecoder('utf-16le');

      let offset = 10;
      const maxOffset = Math.min(buffer.byteLength, tagSize + 10);
      const meta = {
        title: '',
        artist: '',
        album: '',
        year: '',
        genre: '',
        track: '',
        cover: ''
      };

      const decodeStr = (bytes) => {
        if (!bytes || bytes.length <= 1) return '';
        const enc = bytes[0];
        const raw = bytes.slice(1);
        try {
          if (enc === 0) return iso.decode(raw).replace(/\0+$/, '').trim();
          if (enc === 1) return utf16.decode(raw).replace(/\0+$/, '').trim();
          if (enc === 3) return utf8.decode(raw).replace(/\0+$/, '').trim();
          return utf8.decode(raw).replace(/\0+$/, '').trim();
        } catch (e) {
          return iso.decode(raw).replace(/\0+$/, '').trim();
        }
      };

      while (offset + 10 < maxOffset) {
        const frameId = String.fromCharCode(
          view.getUint8(offset),
          view.getUint8(offset + 1),
          view.getUint8(offset + 2),
          view.getUint8(offset + 3)
        );
        if (!/^[A-Z0-9]{4}$/.test(frameId)) break;

        let frameSize = 0;
        if (version === 4) {
          frameSize = ((view.getUint8(offset + 4) & 0x7F) << 21) |
                      ((view.getUint8(offset + 5) & 0x7F) << 14) |
                      ((view.getUint8(offset + 6) & 0x7F) << 7) |
                      (view.getUint8(offset + 7) & 0x7F);
        } else {
          frameSize = view.getUint32(offset + 4);
        }

        if (frameSize <= 0 || offset + 10 + frameSize > buffer.byteLength) break;
        const frameBody = new Uint8Array(buffer, offset + 10, frameSize);

        if (frameId === 'TIT2') meta.title = decodeStr(frameBody);
        else if (frameId === 'TPE1') meta.artist = decodeStr(frameBody);
        else if (frameId === 'TALB') meta.album = decodeStr(frameBody);
        else if (frameId === 'TYER' || frameId === 'TDRC') meta.year = decodeStr(frameBody);
        else if (frameId === 'TCON') meta.genre = decodeStr(frameBody);
        else if (frameId === 'TRCK') meta.track = decodeStr(frameBody);
        else if (frameId === 'APIC') {
          try {
            const enc = frameBody[0];
            let p = 1;
            let mime = '';
            while (p < frameBody.length && frameBody[p] !== 0) {
              mime += String.fromCharCode(frameBody[p]);
              p++;
            }
            p++; // skip null
            const picType = frameBody[p++];
            if (enc === 1) {
              while (p + 1 < frameBody.length && !(frameBody[p] === 0 && frameBody[p + 1] === 0)) p += 2;
              p += 2;
            } else {
              while (p < frameBody.length && frameBody[p] !== 0) p++;
              p++;
            }
            if (p < frameBody.length) {
              const imgBytes = frameBody.slice(p);
              const blob = new Blob([imgBytes], { type: mime || 'image/jpeg' });
              meta.cover = URL.createObjectURL(blob);
            }
          } catch (e) {
            console.warn('[ID3 APIC extraction error]:', e);
          }
        }

        offset += 10 + frameSize;
      }

      if (!meta.title) {
        const fallback = parseFilenameFallback(file.name);
        meta.title = fallback.title;
        if (!meta.artist) meta.artist = fallback.artist;
      }
      return meta;
    }
  } catch (err) {
    console.warn('[parseAudioFileMetadata error]:', err);
  }

  return parseFilenameFallback(file.name);
}

function parseFilenameFallback(fileName) {
  const clean = fileName.replace(/\.[^/.]+$/, '');
  const parts = clean.split(/\s*-\s*/);
  if (parts.length >= 2) {
    return {
      artist: parts[0].trim(),
      title: parts.slice(1).join(' - ').trim(),
      album: 'Local Audio',
      year: '',
      genre: '',
      track: '',
      cover: ''
    };
  }
  return {
    artist: 'Local Artist',
    title: clean,
    album: 'Local Audio',
    year: '',
    genre: '',
    track: '',
    cover: ''
  };
}

async function handleLocalAudioFiles(fileList) {
  const files = Array.from(fileList || []).filter(f => f.type.startsWith('audio/') || /\.(mp3|flac|wav|ogg|m4a|aac|opus)$/i.test(f.name));
  if (files.length === 0) {
    showToastNotification('Please select valid audio files (.mp3, .flac, .wav, .aac, .ogg)');
    return;
  }

  showToastNotification(`Extracting ID3 tags from ${files.length} audio file(s)...`);

  const parsedTracks = [];
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const meta = await parseAudioFileMetadata(file);
    const streamUrl = URL.createObjectURL(file);
    const trackObj = {
      id: `local-${Date.now()}-${i}-${Math.random().toString(36).substr(2, 5)}`,
      title: meta.title || file.name,
      artist: meta.artist || 'Local Audio',
      album: meta.album || 'Local Library',
      year: meta.year || '',
      genre: meta.genre || '',
      duration_formatted: 'Local',
      thumbnail: meta.cover || '/assets/icons/icon-192.png',
      streamUrl: streamUrl,
      isLocal: true
    };
    parsedTracks.push(trackObj);
  }

  state.localLibrary = [...parsedTracks, ...state.localLibrary];

  if (state.activeLibraryTab === 'local' && state.activeView === 'library') {
    renderLocalLibraryTracks();
  }

  if (!state.isPlaying && parsedTracks.length > 0) {
    playTrack(parsedTracks[0]);
    for (let j = 1; j < parsedTracks.length; j++) {
      state.queue.push(parsedTracks[j]);
    }
    updateQueueBadge();
    renderQueueDrawer();
  } else {
    for (let j = 0; j < parsedTracks.length; j++) {
      state.queue.push(parsedTracks[j]);
    }
    updateQueueBadge();
    renderQueueDrawer();
  }

  showToastNotification(`Successfully loaded ${parsedTracks.length} song(s) with embedded tags`);
}

// ============================================================================
// M3U Playlist Export & Import Engine
// ============================================================================
function exportPlaylistToM3U(tracks, filename = 'SongBuddy_Playlist.m3u') {
  if (!tracks || tracks.length === 0) {
    showToastNotification('No tracks to export in playlist');
    return;
  }
  let m3u = '#EXTM3U\n';
  tracks.forEach(track => {
    const title = track.title || 'Unknown Title';
    const artist = track.artist || 'Unknown Artist';
    const stream = track.streamUrl || `https://www.youtube.com/watch?v=${track.id}`;
    m3u += `#EXTINF:180,${artist} - ${title}\n${stream}\n`;
  });
  const blob = new Blob([m3u], { type: 'audio/x-mpegurl;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToastNotification(`Exported ${tracks.length} tracks as ${filename}`);
}

function parseM3UPlaylistContent(content) {
  const lines = content.split(/\r?\n/);
  const tracks = [];
  let currentTitle = '';
  let currentArtist = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    if (line.startsWith('#EXTINF:')) {
      const match = line.match(/#EXTINF:(-?\d+),(.*)/);
      if (match) {
        const fullTitle = match[2];
        const split = fullTitle.split(' - ');
        if (split.length >= 2) {
          currentArtist = split[0].trim();
          currentTitle = split.slice(1).join(' - ').trim();
        } else {
          currentArtist = 'Various Artists';
          currentTitle = fullTitle.trim();
        }
      }
    } else if (!line.startsWith('#')) {
      tracks.push({
        id: `m3u-${Date.now()}-${tracks.length}`,
        title: currentTitle || 'Imported Song',
        artist: currentArtist || 'Various Artists',
        duration_formatted: '3:30',
        streamUrl: line,
        thumbnail: '',
        isImported: true
      });
      currentTitle = '';
      currentArtist = '';
    }
  }
  return tracks;
}

function handleM3UFileUpload(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    const tracks = parseM3UPlaylistContent(content);
    if (tracks.length === 0) {
      showToastNotification('Could not find valid audio entries in M3U file');
      return;
    }
    tracks.forEach(t => state.queue.push(t));
    saveQueueToStorage();
    updateQueueBadge();
    renderQueueDrawer();
    showToastNotification(`Imported ${tracks.length} song(s) from ${file.name} to Queue`);
  };
  reader.readAsText(file);
}

function handleCustomLrcImport(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const text = e.target.result;
    state.lyrics.synced = parseLrc(text);
    if (state.lyrics.synced && state.lyrics.synced.length > 0) {
      renderSyncedLyrics();
      showToastNotification(`Imported ${state.lyrics.synced.length} synchronized lyric timestamps`);
    } else {
      state.lyrics.plain = text;
      renderPlainLyrics();
      showToastNotification('Imported custom text lyrics');
    }
  };
  reader.readAsText(file);
}

// ============================================================================
// Listening Analytics Telemetry & Scrobbler
// ============================================================================
function recordTrackListeningTelemetry(track, cur, dur) {
  if (!track || !track.id || track._recordedPlay) return;
  if (cur >= 30 || (dur > 0 && cur >= dur * 0.5)) {
    track._recordedPlay = true;
    state.listeningStats.tracksPlayed = (state.listeningStats.tracksPlayed || 0) + 1;
    const durMin = dur > 0 ? Math.round(dur / 60) : 3;
    state.listeningStats.totalMinutes = (state.listeningStats.totalMinutes || 0) + durMin;
    if (!state.listeningStats.playCounts) state.listeningStats.playCounts = {};
    const key = `${track.artist} - ${track.title}`;
    state.listeningStats.playCounts[key] = (state.listeningStats.playCounts[key] || 0) + 1;
    localStorage.setItem('songbuddy_listening_stats', JSON.stringify(state.listeningStats));
    updateStatsUI();

    // Persist to server user history for smart playlists
    const token = localStorage.getItem('songbuddy_token');
    const headers = { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) };
    fetch('/api/user/history', {
      method: 'POST',
      headers,
      body: JSON.stringify({ track })
    }).catch(() => {});
  }
}

function openStatsModal() {
  updateStatsUI();
  checkStreamingResilienceHealth();
  $('stats-modal')?.classList.remove('hidden');
}

function closeStatsModal() {
  $('stats-modal')?.classList.add('hidden');
}

function updateStatsUI() {
  const stats = state.listeningStats || { tracksPlayed: 0, totalMinutes: 0, playCounts: {} };
  if ($('stat-tracks-played')) $('stat-tracks-played').textContent = stats.tracksPlayed || 0;
  if ($('stat-minutes-listened')) {
    const mins = stats.totalMinutes || 0;
    $('stat-minutes-listened').textContent = mins >= 60 ? `${(mins / 60).toFixed(1)} hrs` : `${mins} min`;
  }

  const playCounts = stats.playCounts || {};
  const artistCounts = {};
  Object.entries(playCounts).forEach(([song, count]) => {
    const artist = song.split(' - ')[0] || 'Unknown';
    artistCounts[artist] = (artistCounts[artist] || 0) + count;
  });
  const topArtistEntry = Object.entries(artistCounts).sort((a, b) => b[1] - a[1])[0];
  if ($('stat-top-artist')) {
    $('stat-top-artist').textContent = topArtistEntry ? topArtistEntry[0] : 'None';
  }

  const topList = $('stats-top-list');
  if (topList) {
    topList.innerHTML = '';
    const sortedSongs = Object.entries(playCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
    if (sortedSongs.length === 0) {
      topList.innerHTML = '<p style="color:var(--text-muted);font-size:12px;text-align:center;padding:12px;">No plays scrobbled yet.</p>';
    } else {
      sortedSongs.forEach(([song, count]) => {
        const item = document.createElement('div');
        item.className = 'stat-top-item';
        item.innerHTML = `
          <span class="stat-item-name">${escapeHTML(song)}</span>
          <span class="stat-item-plays">${count} plays</span>
        `;
        topList.appendChild(item);
      });
    }
  }
}

function exportStatsJSON() {
  const data = JSON.stringify(state.listeningStats, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `SongBuddy_Listening_Telemetry_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToastNotification('Exported listening telemetry JSON');
}

// ============================================================================
// Modern Transport Controls: Stop, 3-State Repeat, Remaining Time & Wireless Cast
// ============================================================================
function stopPlayback() {
  if (isYTActive && ytPlayer && typeof ytPlayer.stopVideo === 'function') {
    try { ytPlayer.stopVideo(); } catch (e) {}
  }
  if (audio) {
    audio.pause();
    audio.currentTime = 0;
  }
  state.isPlaying = false;
  updatePlayPauseIcons(false);
  updateProgressUI(0, state.currentDuration || 0);
  if ('mediaSession' in navigator) {
    navigator.mediaSession.playbackState = 'none';
  }
  showToastNotification('Playback Stopped');
}

function cycleRepeatMode() {
  const current = state.audioEngine.repeatMode || 'off';
  let next = 'off';
  if (current === 'off') next = 'all';
  else if (current === 'all') next = 'one';
  else next = 'off';

  state.audioEngine.repeatMode = next;
  localStorage.setItem('songbuddy_repeat_mode', next);

  updateRepeatUI();

  if (next === 'off') showToastNotification('Repeat: Off');
  else if (next === 'all') showToastNotification('Repeat: Loop Queue / All Songs');
  else if (next === 'one') showToastNotification('Repeat: Current Song (Repeat 1)');
}

function updateRepeatUI() {
  const mode = state.audioEngine.repeatMode || 'off';
  const btn = $('btn-ctrl-repeat');
  const badge = $('repeat-mode-badge');

  if (btn) {
    btn.classList.toggle('active', mode !== 'off');
    btn.title = `Repeat Mode: ${mode.toUpperCase()} (Cycle: Off / All / 1)`;
  }
  if (badge) {
    badge.classList.toggle('hidden', mode !== 'one');
  }
}

function toggleRemainingTime() {
  state.audioEngine.showRemainingTime = !state.audioEngine.showRemainingTime;
  localStorage.setItem('songbuddy_show_remaining', String(state.audioEngine.showRemainingTime));
  const cur = isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function' ? ytPlayer.getCurrentTime() : (audio?.currentTime || 0);
  const dur = isYTActive && ytPlayer && typeof ytPlayer.getDuration === 'function' ? ytPlayer.getDuration() : (audio?.duration || 0);
  updateProgressUI(cur, dur);
  showToastNotification(state.audioEngine.showRemainingTime ? 'Showing Remaining Time (-MM:SS)' : 'Showing Total Duration (MM:SS)');
}

async function triggerWirelessCast() {
  if (audio && audio.remote && typeof audio.remote.prompt === 'function') {
    try {
      await audio.remote.prompt();
      showToastNotification('Connected to Wireless Streaming Target');
      return;
    } catch (e) {
      console.log('Remote playback prompt cancelled or unsupported:', e);
    }
  }
  if (audio && typeof audio.webkitShowPlaybackTargetPicker === 'function') {
    audio.webkitShowPlaybackTargetPicker();
    return;
  }
  if (navigator.share && state.currentTrack) {
    navigator.share({
      title: state.currentTrack.title,
      text: `Listening to ${state.currentTrack.title} on SongBuddy`,
      url: window.location.href
    }).catch(() => {});
  } else {
    showToastNotification('AirPlay & Google Cast: Connect via browser Cast icon or Bluetooth');
  }
}

function openShortcutsModal() {
  $('shortcuts-modal')?.classList.remove('hidden');
}

function closeShortcutsModal() {
  $('shortcuts-modal')?.classList.add('hidden');
}

function createCustomPlaylist(name) {
  const saved = JSON.parse(localStorage.getItem('songbuddy_custom_playlists') || '[]');
  saved.push(name);
  localStorage.setItem('songbuddy_custom_playlists', JSON.stringify(saved));
  renderSidebarPlaylists();
  showToastNotification(`Playlist "${name}" created!`);
}

function renderSidebarPlaylists() {
  const list = $('sidebar-playlists');
  if (!list) return;

  const saved = JSON.parse(localStorage.getItem('songbuddy_custom_playlists') || '[]');
  const createBtn = $('btn-create-playlist');
  list.innerHTML = '';
  if (createBtn) list.appendChild(createBtn);

  const defaults = [
    { title: 'Design Flow', query: 'Chill Electronic Beats Focus Study' },
    { title: 'Best of 2020', query: 'Best Pop and Hip Hop Hits 2020' }
  ];

  defaults.forEach(item => {
    const li = document.createElement('li');
    li.className = 'nav-item playlist-item';
    li.dataset.query = item.query;
    li.innerHTML = `<span class="bullet-dot"></span><span class="nav-label">${escapeHTML(item.title)}</span>`;
    li.addEventListener('click', () => {
      if ($('search-input')) $('search-input').value = item.query;
      handleSearch(item.query);
      showToastNotification(`Opening ${item.title}`);
    });
    list.appendChild(li);
  });

  saved.forEach(title => {
    const li = document.createElement('li');
    li.className = 'nav-item playlist-item';
    li.dataset.query = title;
    li.innerHTML = `<span class="bullet-dot" style="background:var(--accent-primary);"></span><span class="nav-label">${escapeHTML(title)}</span>`;
    li.addEventListener('click', () => {
      if ($('search-input')) $('search-input').value = title;
      handleSearch(title);
      showToastNotification(`Opening ${title}`);
    });
    list.appendChild(li);
  });
}

// ============================================================================
// Helpers: SVG Cover Fallback & Formatters
// ============================================================================
function generateFallbackCover(title, artist) {
  const initials = (title || 'SB').substring(0, 2).toUpperCase();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
    <defs>
      <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#27272a"/>
        <stop offset="100%" stop-color="#09090b"/>
      </linearGradient>
    </defs>
    <rect width="300" height="300" fill="url(#grad)"/>
    <text x="50%" y="54%" font-family="system-ui, sans-serif" font-size="72" font-weight="bold" fill="#ffffff" text-anchor="middle" dominant-baseline="middle">${initials}</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function escapeHTML(str) {
  return (str || '').replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
  })[m]);
}

// ============================================================================
// Dynamic Thumbnail Ambilight & Perimeter Roaming Light System
// ============================================================================
const VIBRANT_FALLBACK_PALETTES = [
  { r: 240, g: 30, b: 60, name: 'Crimson Starboy' },
  { r: 255, g: 45, b: 120, name: 'Neon Magenta' },
  { r: 139, g: 92, b: 246, name: 'Cyber Violet' },
  { r: 14, g: 165, b: 233, name: 'Electric Cyan' },
  { r: 245, g: 158, b: 11, name: 'Golden Amber' },
  { r: 16, g: 185, b: 129, name: 'Emerald Wave' },
  { r: 249, g: 115, b: 22, name: 'Sunset Flame' },
  { r: 99, g: 102, b: 241, name: 'Studio Indigo' }
];

function fallbackColorFromTrack(track) {
  const seed = `${track?.title || ''}-${track?.artist || ''}-${track?.id || 'sb'}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }
  const idx = Math.abs(hash) % VIBRANT_FALLBACK_PALETTES.length;
  return VIBRANT_FALLBACK_PALETTES[idx];
}

const trackColorsCache = new Map();

function updateAmbientThumbnailColors(track) {
  if (!track || !track.id) return;

  // 1. Instant cache hit
  if (trackColorsCache.has(track.id)) {
    applyAmbientColors(trackColorsCache.get(track.id));
    return;
  }

  const fallback = fallbackColorFromTrack(track);
  let src = track.thumbnail;
  if (src && src.includes('hq720.jpg')) {
    src = src.replace('hq720.jpg', 'hqdefault.jpg');
  }

  // 2. Query backend PIL color extractor concurrently (100% bypasses CORS & letters letterbox bars)
  if (track.id && !String(track.id).startsWith('local-')) {
    const thumbParam = src ? `&url=${encodeURIComponent(src)}` : '';
    fetch(`/api/thumb_color?id=${encodeURIComponent(track.id)}${thumbParam}`)
      .then(res => res.ok ? res.json() : null)
      .then(serverColor => {
        if (serverColor && !isNaN(serverColor.r)) {
          trackColorsCache.set(track.id, serverColor);
          if (state.currentTrack?.id === track.id) {
            applyAmbientColors(serverColor);
          }
        }
      })
      .catch(() => {});
  }

  if (!src) {
    applyAmbientColors(fallback);
    return;
  }

  // 3. Fast Client-side Canvas Extractor (runs in ~5ms)
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.src = src;

  img.onload = () => {
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const size = 32;
      canvas.width = size;
      canvas.height = size;

      // Crop out letterbox black bars if 4:3 YouTube thumbnail
      const isYT = src.includes('ytimg.com') || src.includes('youtube.com');
      if (isYT && img.naturalHeight > 0) {
        const sy = Math.floor(img.naturalHeight * 0.125);
        const sh = Math.floor(img.naturalHeight * 0.75);
        ctx.drawImage(img, 0, sy, img.naturalWidth, sh, 0, 0, size, size);
      } else {
        ctx.drawImage(img, 0, 0, size, size);
      }

      const data = ctx.getImageData(0, 0, size, size).data;
      let bestColor = null;
      let maxScore = -1;
      let rSum = 0, gSum = 0, bSum = 0, count = 0;

      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const a = data[i + 3];

        if (a < 128) continue;
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const delta = max - min;
        const sum = r + g + b;

        // Score vibrant accents
        if (sum > 35 && sum < 720 && delta > 18) {
          const score = delta * (1 + max / 255);
          if (score > maxScore) {
            maxScore = score;
            bestColor = { r, g, b };
          }
        }
        rSum += r;
        gSum += g;
        bSum += b;
        count++;
      }

      let chosen = bestColor;
      if (!chosen && count > 0) {
        chosen = {
          r: Math.round(rSum / count),
          g: Math.round(gSum / count),
          b: Math.round(bSum / count)
        };
      }
      if (!chosen) chosen = fallback;

      // Ensure rich luminescence
      if (chosen.r + chosen.g + chosen.b < 90) {
        const boost = 110 / Math.max(1, chosen.r + chosen.g + chosen.b);
        chosen = {
          r: Math.min(255, Math.round(chosen.r * boost)),
          g: Math.min(255, Math.round(chosen.g * boost)),
          b: Math.min(255, Math.round(chosen.b * boost))
        };
      }

      trackColorsCache.set(track.id, chosen);
      if (state.currentTrack?.id === track.id) {
        applyAmbientColors(chosen);
      }
    } catch (err) {
      // Handled by server probe or fallback
    }
  };

  img.onerror = () => {
    if (!trackColorsCache.has(track.id)) {
      applyAmbientColors(fallback);
    }
  };
}

function applyAmbientColors(rgb) {
  if (!rgb || isNaN(rgb.r)) return;
  const root = document.documentElement;
  const rgbStr = `${rgb.r}, ${rgb.g}, ${rgb.b}`;

  root.style.setProperty('--ambient-rgb', rgbStr);
  root.style.setProperty('--ambient-beam', `rgb(${rgbStr})`);
  root.style.setProperty('--ambient-glow', `rgba(${rgbStr}, 0.85)`);
  root.style.setProperty('--ambient-soft', `rgba(${rgbStr}, 0.35)`);
  root.style.setProperty('--ambient-bloom', `rgba(${rgbStr}, 0.16)`);

  // Direct SVG update for screen ambilight perimeter roaming light
  const screenAmbilight = $('screen-ambilight');
  if (screenAmbilight) {
    screenAmbilight.style.display = 'block';
    screenAmbilight.style.opacity = state.isPlaying ? '0.85' : '0.4';
  }

  document.querySelectorAll('.ambilight-beam, .cinema-beam-ambient, .cinema-beam-glow').forEach(el => {
    el.style.stroke = `rgb(${rgbStr})`;
  });
  document.querySelectorAll('.ambilight-beam-wide').forEach(el => {
    el.style.stroke = `rgb(${rgbStr})`;
  });
  document.querySelectorAll('.ambilight-track, .cinema-beam-track').forEach(el => {
    el.style.stroke = `rgba(${rgbStr}, 0.2)`;
  });

  // Update dynamic traveling bloom halo
  const bloom = $('ambilight-bloom');
  if (bloom) {
    bloom.style.background = `radial-gradient(circle, rgba(${rgbStr}, 0.75) 0%, rgba(${rgbStr}, 0.25) 45%, transparent 72%)`;
  }

  // Update dynamic atmospheric aura behind main feed
  const glow = $('ambient-glow');
  if (glow) {
    glow.style.background = `radial-gradient(circle, rgba(${rgbStr}, 0.24) 0%, rgba(${rgbStr}, 0.08) 45%, transparent 70%)`;
  }

  // Update cinema mode artwork backdrop glow
  const cinGlow = $('cinema-art-glow');
  if (cinGlow) {
    cinGlow.style.background = `radial-gradient(circle, rgba(${rgbStr}, 0.8) 0%, rgba(${rgbStr}, 0.32) 50%, transparent 75%)`;
  }

  // Update Right-Side Player Studio Disc Well Neuromorphic Border
  const discWell = $('neu-disc-well');
  if (discWell) {
    discWell.style.borderColor = `rgba(${rgbStr}, 0.45)`;
    discWell.style.boxShadow = `0 0 32px rgba(${rgbStr}, 0.3), inset 0 0 16px rgba(${rgbStr}, 0.18)`;
  }

  // Update Right-Side Player Studio Panel Border
  const playerPanel = $('player-panel');
  if (playerPanel) {
    playerPanel.style.borderLeftColor = `rgba(${rgbStr}, 0.25)`;
    playerPanel.style.boxShadow = `inset 1px 0 0 rgba(${rgbStr}, 0.12), -10px 0 40px rgba(0, 0, 0, 0.85)`;
  }
}

function shiftAmbientAura(seed) {
  // Legacy shim redirects to dynamic track color engine
  if (state.currentTrack) {
    updateAmbientThumbnailColors(state.currentTrack);
  }
}

// TV Mode / Cinema Ambilight Controller (Activated by 'F' button or key)
function openCinemaAmbilight(options = {}) {
  const modal = $('cinema-ambilight-modal');
  if (!modal) return;
  modal.classList.remove('hidden');

  if (state.currentTrack) {
    syncCinemaTrack(state.currentTrack);
  } else if (state.featuredTracks && state.featuredTracks.length > 0) {
    playTrack(state.featuredTracks[0]);
    syncCinemaTrack(state.featuredTracks[0]);
  } else {
    syncCinemaTrack(HERO_SLIDES[0]);
  }

  // Request browser Fullscreen for immersive TV experience
  if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
    document.documentElement.requestFullscreen().catch(() => {});
  }

  if (options.showToast !== false) {
    showToastNotification('TV Mode Activated (Press F or Esc to exit)');
  }
}

function closeCinemaAmbilight() {
  const modal = $('cinema-ambilight-modal');
  if (modal) {
    modal.classList.add('hidden');
  }

  // Exit browser Fullscreen if currently active
  if (document.fullscreenElement && document.exitFullscreen) {
    document.exitFullscreen().catch(() => {});
  }
}

function toggleCinemaAmbilight() {
  const modal = $('cinema-ambilight-modal');
  if (modal && !modal.classList.contains('hidden')) {
    closeCinemaAmbilight();
  } else {
    openCinemaAmbilight();
  }
}

function syncCinemaTrack(track) {
  if (!track) return;
  const title = $('cinema-track-title');
  const artist = $('cinema-track-artist');
  const cover = $('cinema-cover-art');
  if (title) title.textContent = track.title || 'Unknown Title';
  if (artist) artist.textContent = track.artist || 'Unknown Artist';
  if (cover) setSafeCoverArt(cover, track);
}

// ============================================================================
// MediaSession Integration & Background Audio Engine (Runs when Display is Off)
// ============================================================================
const SILENT_AUDIO_DATA = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';

function enableBackgroundAudioSession() {
  if (!state.screenOffPlayback) return;
  let bgKeeper = $('bg-audio-keeper');
  if (!bgKeeper) {
    bgKeeper = document.createElement('audio');
    bgKeeper.id = 'bg-audio-keeper';
    bgKeeper.preload = 'auto';
    bgKeeper.loop = true;
    bgKeeper.setAttribute('playsinline', '');
    bgKeeper.setAttribute('webkit-playsinline', '');
    bgKeeper.setAttribute('x-webkit-airplay', 'allow');
    document.body.appendChild(bgKeeper);
  }
  if (!bgKeeper.src || !bgKeeper.src.startsWith('data:audio/wav')) {
    bgKeeper.src = SILENT_AUDIO_DATA;
  }
  bgKeeper.volume = 0.01;
  bgKeeper.play().catch(() => {});
}

function stopBackgroundAudioSession() {
  const bgKeeper = $('bg-audio-keeper');
  if (bgKeeper) {
    try { bgKeeper.pause(); } catch (e) {}
  }
}

// Screen Wake Lock Controller
let wakeLockSentinel = null;
async function requestScreenWakeLock() {
  if ('wakeLock' in navigator && (state.keepScreenAwake || state.cinemaMode)) {
    try {
      wakeLockSentinel = await navigator.wakeLock.request('screen');
      console.log('[SongBuddy] Screen Wake Lock active');
      wakeLockSentinel.addEventListener('release', () => {
        wakeLockSentinel = null;
      });
    } catch (err) {
      console.warn('[SongBuddy] Wake lock error:', err);
    }
  }
}

function releaseScreenWakeLock() {
  if (wakeLockSentinel && !state.keepScreenAwake && !state.cinemaMode) {
    try { wakeLockSentinel.release(); } catch (e) {}
    wakeLockSentinel = null;
  }
}

function toggleScreenOffMode() {
  state.screenOffPlayback = !state.screenOffPlayback;
  localStorage.setItem('songbuddy_screenoff', state.screenOffPlayback ? 'true' : 'false');
  updateScreenOffUI();
  if (state.screenOffPlayback) {
    if (state.isPlaying) enableBackgroundAudioSession();
    showToastNotification('Screen-Off Playback: ON (Music continues when phone is locked)');
  } else {
    stopBackgroundAudioSession();
    showToastNotification('Screen-Off Playback: OFF (Music pauses on lock)');
  }
}

function updateScreenOffUI() {
  const btn = $('btn-screenoff-mode');
  const label = $('label-screenoff-status');
  if (btn) {
    btn.classList.toggle('active-mode', state.screenOffPlayback);
    btn.title = `Screen-Off Playback: ${state.screenOffPlayback ? 'ON (Plays while display is off)' : 'OFF'}`;
  }
  if (label) {
    label.textContent = `Screen-Off Audio: ${state.screenOffPlayback ? 'ON' : 'OFF'}`;
  }
}

function setupMediaSession() {
  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', () => togglePlayPause());
    navigator.mediaSession.setActionHandler('pause', () => togglePlayPause());
    navigator.mediaSession.setActionHandler('previoustrack', () => playPrevTrack());
    navigator.mediaSession.setActionHandler('nexttrack', () => playNextTrack(true));
    try {
      navigator.mediaSession.setActionHandler('seekto', (details) => {
        if (details.seekTime !== undefined) {
          seekPlayerTo(details.seekTime);
        }
      });
      navigator.mediaSession.setActionHandler('seekbackward', (details) => {
        const skip = details.seekOffset || 10;
        const cur = isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function' ? ytPlayer.getCurrentTime() : (audio?.currentTime || 0);
        seekPlayerTo(Math.max(0, cur - skip));
      });
      navigator.mediaSession.setActionHandler('seekforward', (details) => {
        const skip = details.seekOffset || 10;
        const cur = isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function' ? ytPlayer.getCurrentTime() : (audio?.currentTime || 0);
        seekPlayerTo(cur + skip);
      });
      navigator.mediaSession.setActionHandler('stop', () => {
        togglePlayPause();
      });
    } catch (e) {}
  }
}

function updateMediaSession(track) {
  if (!('mediaSession' in navigator) || !track) return;
  const thumb = track.thumbnail || '/assets/artists/travis_scott.jpg';
  try {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title || 'Unknown Title',
      artist: track.artist || 'Unknown Artist',
      album: track.album || 'SongBuddy Studio',
      artwork: [
        { src: thumb, sizes: '96x96', type: 'image/jpeg' },
        { src: thumb, sizes: '128x128', type: 'image/jpeg' },
        { src: thumb, sizes: '192x192', type: 'image/jpeg' },
        { src: thumb, sizes: '256x256', type: 'image/jpeg' },
        { src: thumb, sizes: '512x512', type: 'image/jpeg' }
      ]
    });
    navigator.mediaSession.playbackState = state.isPlaying ? 'playing' : 'paused';
  } catch (e) {}
}

function syncMediaSessionPosition(currentTime, duration) {
  if ('mediaSession' in navigator && 'setPositionState' in navigator.mediaSession) {
    if (duration && !isNaN(duration) && duration > 0) {
      try {
        navigator.mediaSession.setPositionState({
          duration: Math.max(duration, 0.1),
          playbackRate: 1,
          position: Math.min(Math.max(currentTime || 0, 0), duration)
        });
      } catch (e) {}
    }
  }
}

// ============================================================================
// Web Audio API DSP Engine, 5-Band Equalizer & Spectrum Visualizer
// ============================================================================
let audioCtx = null;
let audioSrcNode = null;
let eqFilterNodes = [];
let analyserNode = null;
let visualizerAnimFrame = null;
let visualizerPeaks = new Array(32).fill(0);
let isAudioCtxConnected = false;

const EQ_BANDS_CONFIG = [
  { freq: 60, type: 'lowshelf', name: '60 Hz', label: 'Sub-Bass' },
  { freq: 230, type: 'peaking', name: '230 Hz', label: 'Bass' },
  { freq: 910, type: 'peaking', name: '910 Hz', label: 'Mids' },
  { freq: 3600, type: 'peaking', name: '3.6 kHz', label: 'Presence' },
  { freq: 14000, type: 'highshelf', name: '14 kHz', label: 'Treble' }
];

const EQ_PRESETS = {
  flat: [0, 0, 0, 0, 0],
  'bass-boost': [7, 4.5, 0, 1.5, 2],
  vocal: [-2, 1.5, 5, 3.5, 1],
  rock: [4.5, 3, -1, 3, 5],
  pop: [2.5, 1.5, 4, 2.5, 2.5],
  electronic: [6, 4, 1, 3, 5],
  acoustic: [3.5, 1.5, 2.5, 3, 4],
  treble: [-1, 0, 2, 5, 7]
};

let preampNode = null;
let compressorNode = null;
let stereoPannerNode = null;
let crossfadeGainNode = null;
let karaokeFilterNode = null;
let karaokeDSP = null;
let eightDDSP = null;
let eightDOrbitFrameId = null;
let eightDOrbitAngle = 0;
let eightDLastTimestamp = 0;
let isCrossfading = false;

function initWebAudio() {
  if (isAudioCtxConnected) return;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;

    if (!audioCtx) {
      audioCtx = new AudioContextClass();
    }

    if (!audio) return;

    if (!audioSrcNode) {
      audioSrcNode = audioCtx.createMediaElementSource(audio);
    }

    // 1. Preamp Gain Node (-12dB to +12dB)
    preampNode = audioCtx.createGain();
    const initPreamp = Math.pow(10, (state.audioEngine.preampGain || 0) / 20);
    preampNode.gain.value = initPreamp;

    // 2. 5 BiquadFilterNodes (EQ)
    eqFilterNodes = EQ_BANDS_CONFIG.map((band, idx) => {
      const filter = audioCtx.createBiquadFilter();
      filter.type = band.type;
      filter.frequency.value = band.freq;
      const gainVal = state.equalizer.enabled ? (state.equalizer.bands[idx] || 0) : 0;
      filter.gain.value = gainVal;
      return filter;
    });

    // 3. DynamicsCompressorNode (ReplayGain / Loudness Normalization)
    compressorNode = audioCtx.createDynamicsCompressor();
    compressorNode.threshold.value = -24;
    compressorNode.knee.value = 30;
    compressorNode.ratio.value = 12;
    compressorNode.attack.value = 0.003;
    compressorNode.release.value = 0.25;

    // 4. StereoPannerNode (3D Spatial / Width)
    if (typeof audioCtx.createStereoPanner === 'function') {
      stereoPannerNode = audioCtx.createStereoPanner();
      stereoPannerNode.pan.value = state.audioEngine.spatialAudio || 0;
    }

    // 5. Crossfade Gain Node
    crossfadeGainNode = audioCtx.createGain();
    crossfadeGainNode.gain.value = 1;

    // 6. Professional Center-Channel Phase Inversion Karaoke DSP with Bass/Air Preservation
    karaokeDSP = createKaraokeDSP(audioCtx);

    // 7. 8D Spatial Audio 360-Degree Binaural Orbit DSP
    eightDDSP = create8DAudioDSP(audioCtx);

    // 8. AnalyserNode
    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 64;
    analyserNode.smoothingTimeConstant = 0.82;

    reconnectWebAudioChain();
    isAudioCtxConnected = true;
  } catch (err) {
    console.warn('[Web Audio initialization error]:', err);
  }
}

function createKaraokeDSP(ctx) {
  try {
    const input = ctx.createGain();
    const output = ctx.createGain();

    // 1. Vocal Bandpass (isolates human vocal spectrum 140Hz - 7000Hz)
    const bandHighpass = ctx.createBiquadFilter();
    bandHighpass.type = 'highpass';
    bandHighpass.frequency.value = 140;

    const bandLowpass = ctx.createBiquadFilter();
    bandLowpass.type = 'lowpass';
    bandLowpass.frequency.value = 7000;

    // 2. Channel Splitter & Phase Inversion (OOPS - Center Channel Nulling)
    const splitter = ctx.createChannelSplitter(2);
    const merger = ctx.createChannelMerger(2);

    const invR = ctx.createGain();
    invR.gain.value = -1; // -R
    const invL = ctx.createGain();
    invL.gain.value = -1; // -L

    // Vocal band wiring:
    input.connect(bandHighpass);
    bandHighpass.connect(bandLowpass);
    bandLowpass.connect(splitter);

    // Left output = Left + (-Right) = Left - Right
    splitter.connect(merger, 0, 0); // L -> Out L
    splitter.connect(invR, 1);       // R -> invR
    invR.connect(merger, 0, 0);      // -R -> Out L

    // Right output = Right + (-Left) = Right - Left
    splitter.connect(merger, 1, 1); // R -> Out R
    splitter.connect(invL, 0);       // L -> invL
    invL.connect(merger, 0, 1);      // -L -> Out R

    // 3. Bass Preservation Channel (< 140Hz) to keep kick drums & basslines punchy
    const bassFilter = ctx.createBiquadFilter();
    bassFilter.type = 'lowpass';
    bassFilter.frequency.value = 140;
    bassFilter.Q.value = 0.7;

    // 4. Air Preservation Channel (> 7000Hz) to keep hi-hats, air & reverb crisp
    const airFilter = ctx.createBiquadFilter();
    airFilter.type = 'highpass';
    airFilter.frequency.value = 7000;
    airFilter.Q.value = 0.7;

    input.connect(bassFilter);
    input.connect(airFilter);

    // Merge processed vocal-cancelled stereo + preserved bass + preserved air
    merger.connect(output);
    bassFilter.connect(output);
    airFilter.connect(output);

    return {
      input,
      output,
      disconnect: () => {
        try {
          input.disconnect();
          output.disconnect();
          bandHighpass.disconnect();
          bandLowpass.disconnect();
          splitter.disconnect();
          invR.disconnect();
          invL.disconnect();
          merger.disconnect();
          bassFilter.disconnect();
          airFilter.disconnect();
        } catch (e) {}
      }
    };
  } catch (err) {
    console.warn('[Karaoke DSP creation warning]:', err);
    return null;
  }
}

function reconnectWebAudioChain() {
  if (!audioCtx || !audioSrcNode) return;
  try {
    audioSrcNode.disconnect();
    if (preampNode) preampNode.disconnect();
    eqFilterNodes.forEach(f => f.disconnect());
    if (compressorNode) compressorNode.disconnect();
    if (stereoPannerNode) stereoPannerNode.disconnect();
    if (karaokeDSP) karaokeDSP.disconnect();
    if (karaokeFilterNode) karaokeFilterNode.disconnect();
    if (eightDDSP) eightDDSP.disconnect();
    if (crossfadeGainNode) crossfadeGainNode.disconnect();
    if (analyserNode) analyserNode.disconnect();

    // Audiophile Bit-Perfect Direct Passthrough Mode
    if (state.audioEngine.audiophilePassthrough) {
      audioSrcNode.connect(analyserNode);
      analyserNode.connect(audioCtx.destination);
      return;
    }

    // Connect: source -> preamp
    let current = audioSrcNode;
    if (preampNode) {
      current.connect(preampNode);
      current = preampNode;
    }

    // -> EQ filters
    if (state.equalizer.enabled) {
      eqFilterNodes.forEach(filter => {
        current.connect(filter);
        current = filter;
      });
    }

    // -> Loudness Normalization (ReplayGain)
    if (state.audioEngine.normalization && compressorNode) {
      current.connect(compressorNode);
      current = compressorNode;
    }

    // -> Stereo Spatial Pan
    if (stereoPannerNode) {
      current.connect(stereoPannerNode);
      current = stereoPannerNode;
    }

    // -> Karaoke Center-Channel Vocal Suppression DSP
    if (state.karaokeMode) {
      if (karaokeDSP) {
        current.connect(karaokeDSP.input);
        current = karaokeDSP.output;
      } else if (karaokeFilterNode) {
        current.connect(karaokeFilterNode);
        current = karaokeFilterNode;
      }
    }

    // -> 8D Spatial Audio 360-Degree Binaural Orbit DSP
    if (state.eightD && state.eightD.enabled && eightDDSP) {
      current.connect(eightDDSP.input);
      current = eightDDSP.output;
    }

    // -> Crossfade Gain
    if (crossfadeGainNode) {
      current.connect(crossfadeGainNode);
      current = crossfadeGainNode;
    }

    current.connect(analyserNode);
    analyserNode.connect(audioCtx.destination);
  } catch (e) {
    console.warn('[Web Audio reconnection error]:', e);
  }
}

async function switchToDirectStreamForKaraoke() {
  if (!state.currentTrack || !state.currentTrack.id) return;
  try {
    const curTime = (ytPlayer && typeof ytPlayer.getCurrentTime === 'function')
      ? ytPlayer.getCurrentTime()
      : (audio ? audio.currentTime : 0);

    const streamUrl = state.currentTrack.offlineBlobUrl || state.currentTrack.streamUrl || `/api/stream?id=${encodeURIComponent(state.currentTrack.id)}&quality=high`;
    if (ytPlayer && typeof ytPlayer.pauseVideo === 'function') {
      ytPlayer.pauseVideo();
    }
    stopYTProgressTracker();
    isYTActive = false;

    initWebAudio();
    resumeAudioContext();

    if (audio) {
      audio.src = streamUrl;
      const setTime = () => {
        try {
          if (curTime > 0 && (!audio.duration || curTime < audio.duration)) {
            audio.currentTime = curTime;
          }
        } catch (e) {}
      };
      if (audio.readyState >= 1) {
        setTime();
      } else {
        audio.addEventListener('loadedmetadata', setTime, { once: true });
      }
      reconnectWebAudioChain();
      await audio.play();
      updatePlayPauseIcons(true);
    }
  } catch (err) {
    console.warn('[Karaoke stream switch exception, continuing playback]:', err);
    isYTActive = true;
    if (ytPlayer && typeof ytPlayer.playVideo === 'function') {
      ytPlayer.playVideo();
      startYTProgressTracker();
    }
  }
}

function toggleKaraokeMode() {
  state.karaokeMode = !state.karaokeMode;
  const isActive = state.karaokeMode;

  $('chip-karaoke')?.classList.toggle('active', isActive);

  const btn = $('btn-toggle-karaoke');
  if (btn) btn.classList.toggle('active', isActive);
  const label = $('karaoke-btn-label');
  if (label) label.textContent = isActive ? 'Vocals Off' : 'Karaoke';

  const badge = $('karaoke-live-badge');
  if (badge) badge.classList.toggle('hidden', !isActive);

  $('lyrics-overlay')?.classList.toggle('karaoke-active', isActive);

  // If opening Karaoke and lyrics overlay is currently closed, automatically open it
  if (isActive && !state.lyrics.isOpen && typeof openLyrics === 'function') {
    openLyrics();
  }

  // Switch stream for Web Audio vocal suppression DSP if currently playing via YouTube
  if (isActive && isYTActive && state.currentTrack && state.currentTrack.id) {
    switchToDirectStreamForKaraoke();
  } else {
    reconnectWebAudioChain();
  }

  if (!isActive) {
    $('karaoke-countdown-badge')?.classList.add('hidden');
    document.querySelectorAll('.lyric-line.active').forEach(el => el.style.removeProperty('--karaoke-progress'));
  }

  showToastNotification(isActive ? 'Karaoke Mode: Vocals Suppressed (Sing Along)' : 'Karaoke Mode: Standard Playback');
}
window.toggleKaraokeMode = toggleKaraokeMode;

// ============================================================================
// 8D Spatial Audio Orbit Engine & Binaural Diffusion DSP
// ============================================================================
function create8DAudioDSP(ctx) {
  try {
    const input = ctx.createGain();
    const output = ctx.createGain();

    // 1. Stereo Panner for dynamic 360-degree circular orbit
    let panner = null;
    if (typeof ctx.createStereoPanner === 'function') {
      panner = ctx.createStereoPanner();
      panner.pan.value = 0;
    }

    // 2. Dynamic Depth Filter (simulates acoustic head shadow / HRTF rear occlusion)
    // Lowpass filter: sweeps between 20,000Hz (front) and 6,500Hz (rear)
    const depthFilter = ctx.createBiquadFilter();
    depthFilter.type = 'lowpass';
    depthFilter.frequency.value = 20000;
    depthFilter.Q.value = 0.7;

    // 3. Dynamic Distance Gain (subtle 0.93 - 1.0 attenuation as orbit moves behind)
    const depthGain = ctx.createGain();
    depthGain.gain.value = 1.0;

    // 4. Binaural Room Ambience & Haas Spatial Diffusion
    // Creates acoustic spaciousness so sound floats around the listener in a 3D sphere
    const dryGain = ctx.createGain();
    dryGain.gain.value = 0.82;

    const wetGain = ctx.createGain();
    wetGain.gain.value = 0.22;

    // Subtle stereo delay network (18ms Left / 27ms Right) + soft high-frequency dampening
    const delayL = ctx.createDelay();
    delayL.delayTime.value = 0.018;
    const delayR = ctx.createDelay();
    delayR.delayTime.value = 0.027;

    const delayFilter = ctx.createBiquadFilter();
    delayFilter.type = 'lowpass';
    delayFilter.frequency.value = 4500;

    const merger = ctx.createChannelMerger(2);
    delayL.connect(merger, 0, 0); // Out Left
    delayR.connect(merger, 0, 1); // Out Right

    // Wire: input -> panner -> depthFilter -> depthGain
    if (panner) {
      input.connect(panner);
      panner.connect(depthFilter);
    } else {
      input.connect(depthFilter);
    }
    depthFilter.connect(depthGain);

    // Dry path: depthGain -> dryGain -> output
    depthGain.connect(dryGain);
    dryGain.connect(output);

    // Wet spatial diffusion path: depthGain -> delayFilter -> delayL & delayR -> merger -> wetGain -> output
    depthGain.connect(delayFilter);
    delayFilter.connect(delayL);
    delayFilter.connect(delayR);
    merger.connect(wetGain);
    wetGain.connect(output);

    return {
      input,
      output,
      panner,
      depthFilter,
      depthGain,
      disconnect: () => {
        try {
          input.disconnect();
          output.disconnect();
          if (panner) panner.disconnect();
          depthFilter.disconnect();
          depthGain.disconnect();
          dryGain.disconnect();
          wetGain.disconnect();
          delayL.disconnect();
          delayR.disconnect();
          delayFilter.disconnect();
          merger.disconnect();
        } catch (e) {}
      }
    };
  } catch (err) {
    console.warn('[8D DSP creation exception]:', err);
    return null;
  }
}

function start8DOrbit() {
  stop8DOrbit();
  eightDLastTimestamp = performance.now();

  function tick(now) {
    if (!state.eightD || !state.eightD.enabled) {
      return;
    }

    if (!state.isPlaying) {
      eightDOrbitFrameId = requestAnimationFrame(tick);
      return;
    }

    const dt = Math.min(0.1, (now - eightDLastTimestamp) / 1000);
    eightDLastTimestamp = now;

    // Period: state.eightD.speed (e.g. 11s per full 360-degree rotation)
    const period = Math.max(4, state.eightD.speed || 11);
    const angularVelocity = (2 * Math.PI) / period;
    eightDOrbitAngle = (eightDOrbitAngle + angularVelocity * dt) % (2 * Math.PI);

    // Pan: sin(angle) -> -1.0 (Left) to +1.0 (Right)
    const pan = Math.sin(eightDOrbitAngle);

    // Depth: cos(angle) -> +1.0 (Front) to -1.0 (Rear)
    const depth = Math.cos(eightDOrbitAngle);

    if (eightDDSP && audioCtx) {
      const curTime = audioCtx.currentTime;

      // 1. Smooth 360-degree Panning
      if (eightDDSP.panner && eightDDSP.panner.pan) {
        eightDDSP.panner.pan.setTargetAtTime(pan, curTime, 0.04);
      }

      // 2. Head-shadow psychoacoustic filter: drops when sound is behind listener
      const cutoff = 13250 + 6750 * depth;
      eightDDSP.depthFilter.frequency.setTargetAtTime(cutoff, curTime, 0.04);

      // 3. Subtle distance attenuation
      const distGain = 0.93 + 0.07 * depth;
      eightDDSP.depthGain.gain.setTargetAtTime(distGain, curTime, 0.04);
    }

    eightDOrbitFrameId = requestAnimationFrame(tick);
  }

  eightDOrbitFrameId = requestAnimationFrame(tick);
}

function stop8DOrbit() {
  if (eightDOrbitFrameId) {
    cancelAnimationFrame(eightDOrbitFrameId);
    eightDOrbitFrameId = null;
  }
  if (eightDDSP && audioCtx) {
    const curTime = audioCtx.currentTime;
    if (eightDDSP.panner && eightDDSP.panner.pan) {
      eightDDSP.panner.pan.setTargetAtTime(0, curTime, 0.08);
    }
    eightDDSP.depthFilter.frequency.setTargetAtTime(20000, curTime, 0.08);
    eightDDSP.depthGain.gain.setTargetAtTime(1.0, curTime, 0.08);
  }
}

async function switchToDirectStreamFor8D() {
  if (!state.currentTrack || !state.currentTrack.id) return;
  try {
    const curTime = (ytPlayer && typeof ytPlayer.getCurrentTime === 'function')
      ? ytPlayer.getCurrentTime()
      : (audio ? audio.currentTime : 0);

    const streamUrl = state.currentTrack.offlineBlobUrl || state.currentTrack.streamUrl || `/api/stream?id=${encodeURIComponent(state.currentTrack.id)}&quality=high`;
    if (ytPlayer && typeof ytPlayer.pauseVideo === 'function') {
      ytPlayer.pauseVideo();
    }
    stopYTProgressTracker();
    isYTActive = false;

    initWebAudio();
    resumeAudioContext();

    if (audio) {
      audio.src = streamUrl;
      const setTime = () => {
        try {
          if (curTime > 0 && (!audio.duration || curTime < audio.duration)) {
            audio.currentTime = curTime;
          }
        } catch (e) {}
      };
      if (audio.readyState >= 1) {
        setTime();
      } else {
        audio.addEventListener('loadedmetadata', setTime, { once: true });
      }
      reconnectWebAudioChain();
      await audio.play();
      updatePlayPauseIcons(true);
    }
  } catch (err) {
    console.warn('[8D stream switch exception, continuing playback]:', err);
    isYTActive = true;
    if (ytPlayer && typeof ytPlayer.playVideo === 'function') {
      ytPlayer.playVideo();
      startYTProgressTracker();
    }
  }
}

function toggle8DAudio() {
  state.eightD.enabled = !state.eightD.enabled;
  localStorage.setItem('songbuddy_8d_enabled', String(state.eightD.enabled));
  const isActive = state.eightD.enabled;

  // Update chip button
  $('chip-8d')?.classList.toggle('active', isActive);

  // Update modal toggle & status badge
  const toggle = $('toggle-8d-audio');
  if (toggle) toggle.checked = isActive;
  const statusBadge = $('eight-d-status-val');
  if (statusBadge) {
    statusBadge.textContent = isActive ? '360° Orbit ON' : 'Bypass';
    statusBadge.style.color = isActive ? 'var(--accent-emerald, #10b981)' : '#ffffff';
  }

  initWebAudio();
  resumeAudioContext();

  if (isActive) {
    if (isYTActive && state.currentTrack && state.currentTrack.id) {
      switchToDirectStreamFor8D();
    } else {
      reconnectWebAudioChain();
    }
    start8DOrbit();
    showToastNotification('8D Spatial Audio Active: 360° Binaural Orbit (Best with Headphones)');
  } else {
    stop8DOrbit();
    reconnectWebAudioChain();
    showToastNotification('8D Spatial Audio: Standard Stereo Playback');
  }
}
window.toggle8DAudio = toggle8DAudio;

function set8DSpeed(speedSec) {
  const num = parseFloat(speedSec) || 11;
  state.eightD.speed = num;
  localStorage.setItem('songbuddy_8d_speed', String(num));
  document.querySelectorAll('#eight-d-speed-pills .dsp-pill').forEach(btn => {
    btn.classList.toggle('active', parseFloat(btn.dataset.speed) === num);
  });
  showToastNotification(`8D Orbit Speed: ${num}s per rotation`);
}
window.set8DSpeed = set8DSpeed;

function resumeAudioContext() {
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(console.warn);
  }
}

function applyEqualizerSettings() {
  if (!eqFilterNodes || eqFilterNodes.length === 0) return;
  const isEnabled = state.equalizer.enabled;
  eqFilterNodes.forEach((filter, idx) => {
    const targetGain = isEnabled ? (state.equalizer.bands[idx] || 0) : 0;
    if (audioCtx && filter.gain.setTargetAtTime) {
      filter.gain.setTargetAtTime(targetGain, audioCtx.currentTime, 0.05);
    } else {
      filter.gain.value = targetGain;
    }
  });
}

function setEqualizerPreset(presetName) {
  const gains = EQ_PRESETS[presetName] || EQ_PRESETS.flat;
  state.equalizer.preset = presetName;
  state.equalizer.bands = [...gains];
  localStorage.setItem('songbuddy_eq_preset', presetName);
  localStorage.setItem('songbuddy_eq_bands', JSON.stringify(state.equalizer.bands));

  updateEqualizerUI();
  applyEqualizerSettings();
  showToastNotification(`EQ Preset: ${presetName.charAt(0).toUpperCase() + presetName.slice(1).replace('-', ' ')}`);
}

function setEqualizerBand(bandIndex, gainDb) {
  state.equalizer.bands[bandIndex] = gainDb;
  state.equalizer.preset = 'custom';
  localStorage.setItem('songbuddy_eq_preset', 'custom');
  localStorage.setItem('songbuddy_eq_bands', JSON.stringify(state.equalizer.bands));

  document.querySelectorAll('.eq-preset-pill').forEach(pill => pill.classList.remove('active'));
  const valEl = $(`eq-val-${bandIndex}`);
  if (valEl) {
    valEl.textContent = `${gainDb > 0 ? '+' : ''}${gainDb.toFixed(1)} dB`;
  }
  applyEqualizerSettings();
}

function toggleEqualizerMaster(enabled) {
  state.equalizer.enabled = enabled;
  localStorage.setItem('songbuddy_eq_enabled', String(enabled));
  const toggleStatus = $('eq-toggle-status');
  if (toggleStatus) {
    toggleStatus.textContent = enabled ? 'EQ ON' : 'BYPASS';
    toggleStatus.style.color = enabled ? 'var(--accent-emerald, #10b981)' : 'var(--text-muted, #64748b)';
  }
  const checkbox = $('eq-master-toggle');
  if (checkbox) checkbox.checked = enabled;
  reconnectWebAudioChain();
  applyEqualizerSettings();
  showToastNotification(enabled ? 'Equalizer Activated' : 'Equalizer Bypassed (Flat Audio)');
}

function setPreampGain(db) {
  const numDb = parseFloat(db);
  state.audioEngine.preampGain = numDb;
  localStorage.setItem('songbuddy_preamp', String(numDb));
  if (preampNode && audioCtx) {
    const gainVal = Math.pow(10, numDb / 20);
    preampNode.gain.setTargetAtTime(gainVal, audioCtx.currentTime, 0.05);
  }
  const valEl = $('eq-preamp-val');
  if (valEl) valEl.textContent = `${numDb > 0 ? '+' : ''}${numDb.toFixed(1)} dB`;
}

function setSpatialPan(pan) {
  const numPan = parseFloat(pan);
  state.audioEngine.spatialAudio = numPan;
  localStorage.setItem('songbuddy_spatial', String(numPan));
  if (stereoPannerNode && audioCtx) {
    stereoPannerNode.pan.setTargetAtTime(numPan, audioCtx.currentTime, 0.05);
  }
  const valEl = $('eq-spatial-val');
  if (valEl) {
    if (numPan === 0) valEl.textContent = 'Center';
    else if (numPan < 0) valEl.textContent = `L ${Math.round(Math.abs(numPan) * 100)}%`;
    else valEl.textContent = `R ${Math.round(numPan * 100)}%`;
  }
}

function setCrossfadeSeconds(sec) {
  const numSec = parseInt(sec, 10);
  state.audioEngine.crossfadeSeconds = numSec;
  localStorage.setItem('songbuddy_crossfade', String(numSec));
  document.querySelectorAll('.dsp-pill[data-crossfade]').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.crossfade, 10) === numSec);
  });
  const valEl = $('crossfade-val');
  if (valEl) valEl.textContent = numSec === 0 ? 'Off' : `${numSec}s`;
  showToastNotification(`Crossfade: ${numSec === 0 ? 'Off (Gapless)' : numSec + ' seconds'}`);
}

function toggleNormalization(enabled) {
  state.audioEngine.normalization = enabled;
  localStorage.setItem('songbuddy_normalization', String(enabled));
  const checkbox = $('eq-normalization-toggle');
  if (checkbox) checkbox.checked = enabled;
  reconnectWebAudioChain();
  showToastNotification(enabled ? 'Volume Normalization (ReplayGain) Active' : 'Volume Normalization Bypassed');
}

function toggleAudiophilePassthrough(enabled) {
  state.audioEngine.audiophilePassthrough = enabled;
  localStorage.setItem('songbuddy_audiophile', String(enabled));
  const checkbox = $('eq-audiophile-toggle');
  if (checkbox) checkbox.checked = enabled;
  reconnectWebAudioChain();
  showToastNotification(enabled ? 'Bit-Perfect Direct Passthrough Mode (Bypasses DSP)' : 'Audio DSP Chain Active');
}

function checkCrossfadeTrigger(currentTime, duration) {
  const cfSec = state.audioEngine.crossfadeSeconds;
  if (!cfSec || cfSec <= 0 || isCrossfading || !state.isPlaying) return;
  if (duration && duration > cfSec * 2 && currentTime >= (duration - cfSec)) {
    isCrossfading = true;
    if (crossfadeGainNode && audioCtx) {
      crossfadeGainNode.gain.setValueAtTime(crossfadeGainNode.gain.value, audioCtx.currentTime);
      crossfadeGainNode.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + cfSec);
    }
    setTimeout(() => {
      isCrossfading = false;
      playNextTrack(false);
      if (crossfadeGainNode && audioCtx) {
        crossfadeGainNode.gain.setValueAtTime(0.01, audioCtx.currentTime);
        crossfadeGainNode.gain.linearRampToValueAtTime(1.0, audioCtx.currentTime + (cfSec / 2));
      }
    }, cfSec * 1000);
  }
}

function updateEqualizerUI() {
  const checkbox = $('eq-master-toggle');
  if (checkbox) checkbox.checked = state.equalizer.enabled;

  const toggleStatus = $('eq-toggle-status');
  if (toggleStatus) {
    toggleStatus.textContent = state.equalizer.enabled ? 'EQ ON' : 'BYPASS';
    toggleStatus.style.color = state.equalizer.enabled ? 'var(--accent-emerald, #10b981)' : 'var(--text-muted, #64748b)';
  }

  // Update slider positions and readouts
  state.equalizer.bands.forEach((gain, idx) => {
    const slider = $(`eq-slider-${idx}`);
    if (slider) slider.value = gain;
    const valEl = $(`eq-val-${idx}`);
    if (valEl) valEl.textContent = `${gain > 0 ? '+' : ''}${gain.toFixed(1)} dB`;
  });

  // Update preset pills
  document.querySelectorAll('.eq-preset-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.preset === state.equalizer.preset);
  });

  // Update DSP UI
  const preampSlider = $('eq-preamp-slider');
  if (preampSlider) preampSlider.value = state.audioEngine.preampGain || 0;
  const preampVal = $('eq-preamp-val');
  if (preampVal) {
    const p = state.audioEngine.preampGain || 0;
    preampVal.textContent = `${p > 0 ? '+' : ''}${p.toFixed(1)} dB`;
  }

  const spatialSlider = $('eq-spatial-slider');
  if (spatialSlider) spatialSlider.value = state.audioEngine.spatialAudio || 0;
  const spatialVal = $('eq-spatial-val');
  if (spatialVal) {
    const sp = state.audioEngine.spatialAudio || 0;
    if (sp === 0) spatialVal.textContent = 'Center';
    else if (sp < 0) spatialVal.textContent = `L ${Math.round(Math.abs(sp) * 100)}%`;
    else spatialVal.textContent = `R ${Math.round(sp * 100)}%`;
  }

  const crossfadeVal = $('crossfade-val');
  const cf = state.audioEngine.crossfadeSeconds || 0;
  if (crossfadeVal) crossfadeVal.textContent = cf === 0 ? 'Off' : `${cf}s`;
  document.querySelectorAll('.dsp-pill[data-crossfade]').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.crossfade, 10) === cf);
  });

  const normToggle = $('eq-normalization-toggle');
  if (normToggle) normToggle.checked = !!state.audioEngine.normalization;

  const audioToggle = $('eq-audiophile-toggle');
  if (audioToggle) audioToggle.checked = !!state.audioEngine.audiophilePassthrough;

  const toggle8D = $('toggle-8d-audio');
  if (toggle8D) toggle8D.checked = !!(state.eightD && state.eightD.enabled);
  const status8D = $('eight-d-status-val');
  if (status8D) {
    const is8D = !!(state.eightD && state.eightD.enabled);
    status8D.textContent = is8D ? '360° Orbit ON' : 'Bypass';
    status8D.style.color = is8D ? 'var(--accent-emerald, #10b981)' : '#ffffff';
  }
  const speed = state.eightD ? state.eightD.speed : 11;
  document.querySelectorAll('#eight-d-speed-pills .dsp-pill').forEach(btn => {
    btn.classList.toggle('active', parseFloat(btn.dataset.speed) === speed);
  });
}

function openEqualizerModal() {
  initWebAudio();
  resumeAudioContext();
  updateEqualizerUI();
  $('equalizer-modal')?.classList.remove('hidden');
  startSpectrumVisualizer();
}

function closeEqualizerModal() {
  $('equalizer-modal')?.classList.add('hidden');
  stopSpectrumVisualizer();
}

function startSpectrumVisualizer() {
  stopSpectrumVisualizer();
  const canvas = $('equalizer-visualizer-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dataArray = new Uint8Array(32);

  function renderFrame() {
    visualizerAnimFrame = requestAnimationFrame(renderFrame);

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    let hasLiveSignal = false;
    if (analyserNode && state.isPlaying && !isYTActive) {
      analyserNode.getByteFrequencyData(dataArray);
      hasLiveSignal = dataArray.some(val => val > 0);
    }

    if (!hasLiveSignal && state.isPlaying) {
      const time = performance.now() * 0.0035;
      for (let i = 0; i < 32; i++) {
        const bassFactor = (32 - i) / 32;
        const wave1 = Math.sin(time * 2.1 + i * 0.38) * 0.5 + 0.5;
        const wave2 = Math.cos(time * 2.8 - i * 0.22) * 0.5 + 0.5;
        const beat = (Math.sin(time * 3.2) > 0.65 ? 1.3 : 0.82);
        const synthVal = Math.min(255, Math.floor((wave1 * 0.6 + wave2 * 0.4) * 200 * bassFactor * beat + 24));
        dataArray[i] = synthVal;
      }
    } else if (!state.isPlaying) {
      for (let i = 0; i < 32; i++) {
        dataArray[i] = Math.max(0, dataArray[i] - 14);
      }
    }

    const barCount = 32;
    const totalGap = 4;
    const barWidth = (width - (barCount - 1) * totalGap) / barCount;

    const isNeumorphic = document.documentElement.getAttribute('data-theme') === 'neumorphic';
    const gradient = ctx.createLinearGradient(0, height, 0, 0);
    gradient.addColorStop(0, '#ffffff');
    gradient.addColorStop(0.5, '#a1a1aa');
    gradient.addColorStop(1, '#52525b');

    for (let i = 0; i < barCount; i++) {
      const val = dataArray[i];
      const barHeight = Math.max(3, (val / 255) * (height - 12));
      const x = i * (barWidth + totalGap);
      const y = height - barHeight;

      ctx.fillStyle = gradient;
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x, y, barWidth, barHeight, [3, 3, 0, 0]);
      } else {
        ctx.rect(x, y, barWidth, barHeight);
      }
      ctx.fill();

      if (barHeight > visualizerPeaks[i]) {
        visualizerPeaks[i] = barHeight;
      } else {
        visualizerPeaks[i] = Math.max(0, visualizerPeaks[i] - 1.2);
      }

      const peakY = height - visualizerPeaks[i] - 2;
      ctx.fillStyle = isNeumorphic ? '#2d3748' : '#ffffff';
      ctx.fillRect(x, Math.max(0, peakY), barWidth, 2);
    }
  }

  renderFrame();
}

function stopSpectrumVisualizer() {
  if (visualizerAnimFrame) {
    cancelAnimationFrame(visualizerAnimFrame);
    visualizerAnimFrame = null;
  }
}

// ============================================================================
// Playback Speed Controller Engine
// ============================================================================
function setPlaybackSpeed(speed) {
  const numSpeed = parseFloat(speed);
  state.playbackSpeed = numSpeed;
  localStorage.setItem('songbuddy_playback_speed', String(numSpeed));

  if (audio) {
    audio.playbackRate = numSpeed;
  }

  if (ytPlayer && typeof ytPlayer.setPlaybackRate === 'function') {
    try {
      ytPlayer.setPlaybackRate(numSpeed);
    } catch (e) {
      console.warn('[YT playbackRate error]:', e);
    }
  }

  const label = $('speed-badge-text');
  if (label) label.textContent = `${numSpeed}x`;

  document.querySelectorAll('.speed-option').forEach(btn => {
    btn.classList.toggle('active', parseFloat(btn.dataset.speed) === numSpeed);
  });

  closePlaybackSpeedPopover();
  showToastNotification(`Playback Speed: ${numSpeed}x`);
}

function openPlaybackSpeedPopover(anchorEl) {
  const popover = $('playback-speed-popover');
  if (!popover) return;

  if (anchorEl) {
    const rect = anchorEl.getBoundingClientRect();
    popover.style.bottom = `${Math.max(10, window.innerHeight - rect.top + 8)}px`;
    popover.style.right = `${Math.max(16, window.innerWidth - rect.right - 10)}px`;
  }

  popover.classList.remove('hidden');

  const handleOutsideClick = (e) => {
    if (!popover.contains(e.target) && e.target !== anchorEl && !anchorEl?.contains(e.target)) {
      closePlaybackSpeedPopover();
      document.removeEventListener('click', handleOutsideClick);
    }
  };
  setTimeout(() => document.addEventListener('click', handleOutsideClick), 50);
}

function closePlaybackSpeedPopover() {
  $('playback-speed-popover')?.classList.add('hidden');
}

function togglePlaybackSpeedPopover(anchorEl) {
  const popover = $('playback-speed-popover');
  if (!popover) return;
  if (popover.classList.contains('hidden')) {
    openPlaybackSpeedPopover(anchorEl);
  } else {
    closePlaybackSpeedPopover();
  }
}

// ============================================================================
// Sleep Timer Engine with Smooth Fade-Out
// ============================================================================
let sleepTimerTicker = null;

function setSleepTimer(option) {
  clearSleepTimer();

  if (option === 'track') {
    state.sleepTimer = {
      active: true,
      mode: 'track',
      remainingSeconds: 0
    };
    updateSleepTimerBanner();
    showToastNotification('Sleep Timer: Stops at end of current track');
    closeSleepTimerModal();
    return;
  }

  const minutes = parseInt(option, 10);
  if (!minutes || isNaN(minutes)) return;

  const totalSec = minutes * 60;
  state.sleepTimer = {
    active: true,
    mode: 'minutes',
    remainingSeconds: totalSec
  };

  updateSleepTimerBanner();
  showToastNotification(`Sleep Timer set for ${minutes} minutes`);

  sleepTimerTicker = setInterval(() => {
    if (!state.sleepTimer.active) {
      clearSleepTimer();
      return;
    }

    state.sleepTimer.remainingSeconds -= 1;
    updateSleepTimerBanner();

    if (state.sleepTimer.remainingSeconds <= 0) {
      triggerSleepTimerExecution();
    }
  }, 1000);

  closeSleepTimerModal();
}

function clearSleepTimer() {
  if (sleepTimerTicker) {
    clearInterval(sleepTimerTicker);
    sleepTimerTicker = null;
  }
  state.sleepTimer = {
    active: false,
    mode: null,
    remainingSeconds: 0
  };
  updateSleepTimerBanner();
}

function openSleepTimerModal() {
  updateSleepTimerBanner();
  $('sleep-timer-modal')?.classList.remove('hidden');
}

function closeSleepTimerModal() {
  $('sleep-timer-modal')?.classList.add('hidden');
}

function updateSleepTimerBanner() {
  const banner = $('sleep-timer-active-banner');
  const display = $('sleep-timer-display');
  const indicator = $('timer-active-indicator');

  if (!state.sleepTimer.active) {
    if (banner) banner.classList.add('hidden');
    if (indicator) indicator.classList.add('hidden');
    return;
  }

  if (indicator) indicator.classList.remove('hidden');

  if (banner) {
    banner.classList.remove('hidden');
    if (display) {
      if (state.sleepTimer.mode === 'track') {
        display.textContent = 'End of Track';
      } else {
        const mins = Math.floor(state.sleepTimer.remainingSeconds / 60);
        const secs = state.sleepTimer.remainingSeconds % 60;
        display.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      }
    }
  }
}

function triggerSleepTimerExecution() {
  clearSleepTimer();

  const startVolume = audio ? audio.volume : (state.volume || 0.8);
  const fadeSteps = 15;
  const fadeInterval = 200;
  let step = 0;

  const fadeTimer = setInterval(() => {
    step++;
    const currentVol = Math.max(0, startVolume * (1 - step / fadeSteps));
    if (audio) audio.volume = currentVol;
    if (ytPlayer && typeof ytPlayer.setVolume === 'function') {
      try { ytPlayer.setVolume(Math.floor(currentVol * 100)); } catch (e) {}
    }

    if (step >= fadeSteps) {
      clearInterval(fadeTimer);
      if (state.isPlaying) {
        togglePlayPause();
      }
      if (audio) audio.volume = startVolume;
      if (ytPlayer && typeof ytPlayer.setVolume === 'function') {
        try { ytPlayer.setVolume(Math.floor(startVolume * 100)); } catch (e) {}
      }
      showToastNotification('Sleep Timer: Music auto-paused. Good night!');
    }
  }, fadeInterval);
}

function initAudioSuiteUI() {
  const speedLabel = $('speed-badge-text');
  if (speedLabel) speedLabel.textContent = `${state.playbackSpeed || 1.0}x`;

  document.querySelectorAll('.speed-option').forEach(btn => {
    btn.classList.toggle('active', parseFloat(btn.dataset.speed) === (state.playbackSpeed || 1.0));
  });

  updateEqualizerUI();
  updateSleepTimerBanner();
  updateRepeatUI();
  updateStatsUI();
}

// ============================================================================
// Event Listeners Setup
// ============================================================================
function setupAudioListeners() {
  if (!audio) return;

  audio.addEventListener('timeupdate', () => {
    if (!isYTActive) {
      updateProgressUI(audio.currentTime, audio.duration);
    }
  });

  audio.addEventListener('progress', () => {
    if (audio.buffered.length > 0 && audio.duration) {
      const bufferedEnd = audio.buffered.end(audio.buffered.length - 1);
      const pct = (bufferedEnd / audio.duration) * 100;
      if ($('scrubber-buffer-bar')) $('scrubber-buffer-bar').style.width = `${pct}%`;
    }
  });

  audio.addEventListener('ended', async () => {
    if (state.sleepTimer && state.sleepTimer.active && state.sleepTimer.mode === 'track') {
      triggerSleepTimerExecution();
      return;
    }
    if (state.jukebox && state.jukebox.autoAdvance && state.jukebox.hostToken) {
      try {
        const advanced = await advanceJukeboxQueue();
        if (advanced) return;
      } catch (e) {
        console.warn('[Jukebox Auto-Advance Error]', e);
      }
    }
    if (!isYTActive) {
      if (state.isRepeat) {
        audio.currentTime = 0;
        audio.play();
      } else {
        playNextTrack(false);
      }
    }
  });

  audio.addEventListener('play', () => {
    if (!isYTActive) updatePlayPauseIcons(true);
  });
  audio.addEventListener('pause', () => {
    if (!isYTActive) updatePlayPauseIcons(false);
  });
  audio.addEventListener('error', () => {
    if (isYTActive) return;
    if (state.currentTrack && state.currentTrack.id) {
      if (!state.networkResilience.isRecovering) {
        console.warn('[Stream Error] Attempting CDN token refresh & byte resumption...');
        triggerStreamRecovery(audio.currentTime || 0);
        return;
      }
      if (ytPlayer && typeof ytPlayer.loadVideoById === 'function') {
        console.info('[Failover] Native stream unavailable; seamlessly switching to YouTube player engine.');
        isYTActive = true;
        ytPlayer.loadVideoById(state.currentTrack.id);
        ytPlayer.playVideo();
        updatePlayPauseIcons(true);
        startYTProgressTracker();
        return;
      }
    }
    updatePlayPauseIcons(false);
    state.isPlaying = false;
  });

  audio.addEventListener('stalled', () => {
    if (isYTActive || !state.isPlaying) return;
    if (state.currentTrack && state.currentTrack.id && !state.networkResilience.isRecovering) {
      clearTimeout(state.networkResilience.recoveryTimeout);
      state.networkResilience.recoveryTimeout = setTimeout(() => {
        if (state.isPlaying && audio.readyState < 3 && !state.networkResilience.isRecovering) {
          console.warn('[Stream Stalled] Triggering proactive token refresh...');
          triggerStreamRecovery(audio.currentTime || 0);
        }
      }, 3500);
    }
  });
}

function setupEventListeners() {
  // Unified Navigation links & items (All Sidebar Items)
  document.querySelectorAll('.nav-item[data-view]').forEach(item => {
    item.addEventListener('click', () => {
      const view = item.dataset.view;
      handleNavigationClick(view);
    });
  });
  $('brand-logo')?.addEventListener('click', () => switchView('home'));

  // Local Audio File Picker
  $('local-audio-file-input')?.addEventListener('change', (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    const tracks = files.map((file, idx) => {
      const objUrl = URL.createObjectURL(file);
      const name = file.name.replace(/\.[^/.]+$/, "");
      return {
        id: `local-${Date.now()}-${idx}`,
        title: name,
        artist: 'Local Device Audio',
        duration_formatted: 'Local',
        streamUrl: objUrl,
        thumbnail: '',
        isLocal: true
      };
    });

    playTrack(tracks[0]);
    for (let i = 1; i < tracks.length; i++) {
      state.queue.push(tracks[i]);
    }
    updateQueueBadge();
    renderQueueUI();
    showToastNotification(`Loaded ${tracks.length} local audio track(s)`);
  });

  // Playlist Management
  renderSidebarPlaylists();
  $('btn-create-playlist')?.addEventListener('click', () => {
    const name = prompt('Enter a name for your new playlist:');
    if (name && name.trim()) {
      createCustomPlaylist(name.trim());
    }
  });

  // See All Artists & Genres buttons
  $('btn-see-artists')?.addEventListener('click', () => {
    switchView('search');
    document.querySelectorAll('.filter-pill').forEach(p => p.classList.toggle('active', p.dataset.filter === 'artists'));
    state.activeSearchFilter = 'artists';
    if ($('search-input')) $('search-input').value = 'Top Trending Global Artists';
    handleSearch('Top Trending Global Artists');
  });

  $('btn-see-genres')?.addEventListener('click', () => {
    switchView('search');
    document.querySelectorAll('.filter-pill').forEach(p => p.classList.toggle('active', p.dataset.filter === 'all'));
    state.activeSearchFilter = 'all';
    if ($('search-input')) $('search-input').value = 'Popular Music Genres 2024';
    handleSearch('Popular Music Genres 2024');
  });

  // Center Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.tab;
      if (tab === 'music') switchView('home');
      else if (tab === 'podcast') {
        const input = $('search-input');
        if (input) input.value = 'Popular Music Podcasts & Interviews';
        handleSearch('Popular Music Podcasts & Interviews');
      } else if (tab === 'live') {
        const input = $('search-input');
        if (input) input.value = 'Live Concert Acoustic Sessions';
        handleSearch('Live Concert Acoustic Sessions');
      }
    });
  });

  // Hero Spotlight Buttons
  $('hero-listen-btn')?.addEventListener('click', () => {
    const slide = HERO_SLIDES[state.currentHeroIndex];
    if (slide) {
      playTrack({
        id: slide.id,
        title: slide.title,
        artist: slide.artist,
        thumbnail: slide.thumbnail,
        duration_formatted: slide.duration_formatted
      });
    }
  });

  $('hero-heart-btn')?.addEventListener('click', () => {
    const slide = HERO_SLIDES[state.currentHeroIndex];
    if (slide) {
      toggleLike({
        id: slide.id,
        title: slide.title,
        artist: slide.artist,
        thumbnail: slide.thumbnail,
        duration_formatted: slide.duration_formatted
      });
    }
  });

  $('hero-queue-btn')?.addEventListener('click', () => {
    const slide = HERO_SLIDES[state.currentHeroIndex];
    if (slide) {
      addToQueue({
        id: slide.id,
        title: slide.title,
        artist: slide.artist,
        thumbnail: slide.thumbnail,
        duration_formatted: slide.duration_formatted
      });
    }
  });

  document.querySelectorAll('.h-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      const idx = parseInt(dot.dataset.index, 10);
      updateHeroSlide(idx);
    });
  });

  // SongBuddy Top Nav Home Button
  $('btn-top-home')?.addEventListener('click', () => {
    switchView('home');
    const feed = $('view-home');
    if (feed) feed.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Search Browse Shortcut
  $('btn-search-browse')?.addEventListener('click', () => {
    switchView('search');
    const input = $('search-input');
    if (input) {
      input.focus();
      input.select();
    }
  });

  // Top Nav Studio Hi-Fi Equalizer Badge
  $('btn-studio-eq-top')?.addEventListener('click', () => {
    openEqualizerModal();
  });

  // SongBuddy Sound Capsule Vibe Filters
  document.querySelectorAll('.songbuddy-feed-pill, .spotify-feed-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.songbuddy-feed-pill, .spotify-feed-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const filter = pill.dataset.feedFilter;
      switchView('home');
      
      if (filter === 'trending') {
        showToastNotification('Loading Trending Chart Hits');
        quickPlaySpotifyCard('Top Trending Global & Indian Hits 2026', 'Trending Hits');
      } else if (filter === 'automix') {
        showToastNotification('Continuous Automix Activated');
        if (state.currentTrack) {
          state.radioEnabled = true;
          startRadioRecommendations(state.currentTrack);
        } else {
          quickPlaySpotifyCard('Continuous Electronic Chill Beats', 'Continuous Automix');
        }
      } else if (filter === 'lofi') {
        showToastNotification('Lo-Fi & Chill Station');
        quickPlaySpotifyCard('Lo-Fi Hip Hop Study Chill Relax Beats', 'Lo-Fi & Chill');
      } else if (filter === 'hiphop') {
        showToastNotification('Desi Hip Hop & Rap Drops');
        quickPlaySpotifyCard('Best Hip Hop and Rap hits 2026', 'Hip-Hop Station');
      } else if (filter === 'punjabi') {
        showToastNotification('Punjabi Wave Beats');
        quickPlaySpotifyCard('Trending Punjabi wave hits Karan Aujla Diljit', 'Punjabi Wave');
      } else if (filter === 'bollywood') {
        showToastNotification('Bollywood Classics & Retro');
        quickPlaySpotifyCard('Bollywood classic and retro hit songs', 'Bollywood Classics');
      } else {
        showToastNotification('Personalized Flow Active');
      }
    });
  });

  // Helper for 1-Click Instant Playback on Quick Cards & Station Cards
  async function quickPlaySpotifyCard(query, title) {
    showToastNotification(`Playing ${title}...`);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=5`);
      if (!res.ok) throw new Error('Search failed');
      const tracks = await res.json();
      if (Array.isArray(tracks) && tracks.length > 0) {
        playTrack(tracks[0], { startRadio: true });
      } else {
        const input = $('search-input');
        if (input) input.value = query;
        handleSearch(query, true);
      }
    } catch (e) {
      console.warn('[QuickPlay Error]:', e);
      const input = $('search-input');
      if (input) input.value = query;
      handleSearch(query, true);
    }
  }

  // Quick Flow Instant Station Cards
  document.querySelectorAll('.songbuddy-quick-card, .spotify-quick-card').forEach(card => {
    card.addEventListener('click', (e) => {
      const query = card.dataset.query || card.querySelector('.quick-card-title')?.textContent;
      const title = card.dataset.title || card.querySelector('.quick-card-title')?.textContent || 'Station';
      if (query) quickPlaySpotifyCard(query, title);
    });
  });

  // Curated Station Cards & Soundscapes
  document.querySelectorAll('.songbuddy-card, .spotify-album-card').forEach(card => {
    card.addEventListener('click', (e) => {
      const query = card.dataset.query || card.querySelector('.card-desc, .spotify-album-desc')?.textContent;
      const title = card.dataset.title || card.querySelector('.card-title, .spotify-album-title')?.textContent || 'Station Mix';
      if (query) quickPlaySpotifyCard(query, title);
    });
  });

  // Studio Highlights Carousel
  const STUDIO_HIGHLIGHTS = [
    {
      title: 'Continuous Audio Workstation',
      desc: 'Lossless in-memory bitstream buffering with continuous YouTube Automix, 5-band graphic equalizer, synced lyrics, and dynamic ambilight.',
      cta: 'Start Flow Radio'
    },
    {
      title: '5-Band Studio Equalizer',
      desc: 'Precision frequency sculpting: 60Hz Sub-Bass, 250Hz Punch, 1kHz Vocals, 4kHz Air, and 12kHz Brilliance with quick acoustic presets.',
      cta: 'Open Equalizer'
    },
    {
      title: 'Lossless Flow Automix',
      desc: 'Continuous smart radio that automatically queues harmonic acoustic matches so your session never goes silent.',
      cta: 'Launch Automix'
    },
    {
      title: 'Cinema Ambilight TV Mode',
      desc: 'Press "F" key or tap TV Mode button for synced fullscreen ambient reactive visuals and floating typography.',
      cta: 'Enter TV Mode'
    }
  ];
  let currentHighlightIndex = 0;

  function updateStudioHighlight(idx) {
    currentHighlightIndex = (idx + STUDIO_HIGHLIGHTS.length) % STUDIO_HIGHLIGHTS.length;
    const highlight = STUDIO_HIGHLIGHTS[currentHighlightIndex];
    if ($('getting-started-title')) $('getting-started-title').textContent = highlight.title;
    if ($('getting-started-desc')) $('getting-started-desc').textContent = highlight.desc;
    if ($('btn-browse-videos')) {
      const ctaSpan = $('btn-browse-videos').querySelector('span');
      if (ctaSpan) ctaSpan.textContent = highlight.cta;
      else $('btn-browse-videos').textContent = highlight.cta;
    }
  }

  $('btn-getting-started-prev')?.addEventListener('click', (e) => {
    e.stopPropagation();
    updateStudioHighlight(currentHighlightIndex - 1);
  });
  $('btn-getting-started-next')?.addEventListener('click', (e) => {
    e.stopPropagation();
    updateStudioHighlight(currentHighlightIndex + 1);
  });

  $('btn-browse-videos')?.addEventListener('click', () => {
    if (currentHighlightIndex === 0) {
      quickPlaySpotifyCard('Top Trending Global hits 2026', 'Flow Radio');
    } else if (currentHighlightIndex === 1) {
      openEqualizerModal();
    } else if (currentHighlightIndex === 2) {
      quickPlaySpotifyCard('Continuous Electronic Chill Beats', 'Continuous Automix');
    } else {
      toggleCinemaAmbilight();
    }
  });

  // Studio Hero Equalizer Button
  $('btn-hero-equalizer')?.addEventListener('click', () => {
    openEqualizerModal();
  });

  // Studio Hero TV Mode Button
  $('btn-hero-tv')?.addEventListener('click', () => {
    toggleCinemaAmbilight();
  });

  // Visualizer Orb Click
  $('getting-started-disc')?.addEventListener('click', () => {
    toggleCinemaAmbilight();
  });

  $('btn-show-tips')?.addEventListener('click', () => {
    updateStudioHighlight(currentHighlightIndex + 1);
  });

  $('btn-show-all-made-for')?.addEventListener('click', () => {
    const input = $('search-input');
    if (input) input.value = 'Trending Indie and Bollywood Melodies';
    handleSearch('Trending Indie and Bollywood Melodies', true);
  });

  $('btn-show-all-recents')?.addEventListener('click', () => {
    switchView('library', 'recent');
  });

  // Genre Cards
  document.querySelectorAll('.genre-card').forEach(card => {
    card.addEventListener('click', () => {
      const query = card.dataset.query;
      if (query) {
        const input = $('search-input');
        if (input) input.value = query;
        handleSearch(query);
      }
    });
  });

  // Search Input & Mobile Keyboard Actions
  const searchInput = $('search-input');
  const searchClearBtn = $('search-clear-btn');
  const searchSubmitBtn = $('search-submit-btn');

  // In-view Search Bar elements (inside #view-search)
  const inViewSearchInput = $('in-view-search-input');
  const inViewSearchClear = $('in-view-search-clear');
  const btnSearchAgain = $('btn-search-again');

  // Expand search popover on focus or click and select text for effortless subsequent searches
  searchInput?.addEventListener('focus', () => {
    openDesktopSearchDropdown();
    if (searchInput.value) {
      searchInput.select();
    }
  });

  searchInput?.addEventListener('click', () => {
    openDesktopSearchDropdown();
    if (searchInput.value) {
      searchInput.select();
    }
  });

  searchInput?.addEventListener('input', (e) => {
    const val = e.target.value;
    if (inViewSearchInput) {
      inViewSearchInput.value = val;
      inViewSearchClear?.classList.toggle('hidden', !val);
    }
    searchClearBtn?.classList.toggle('hidden', !val);
    handleSearch(val, false);

    // Live Instant matches in expanded dropdown
    clearTimeout(desktopSearchDebounce);
    desktopSearchDebounce = setTimeout(() => {
      searchDesktopInstantMatches(val);
    }, 220);
  });

  // Mobile virtual keyboard 'Enter' / 'Search' action
  searchInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const val = searchInput.value.trim();
      if (val) {
        clearTimeout(state.searchDebounceTimer);
        saveRecentSearch(val);
        handleSearch(val, true);
        closeDesktopSearchDropdown();
        searchInput.blur(); // Dismiss mobile on-screen keyboard so results are visible immediately!
      }
    } else if (e.key === 'Escape') {
      closeDesktopSearchDropdown();
      searchInput.blur();
    }
  });

  // Search Icon / Button Click
  searchSubmitBtn?.addEventListener('click', () => {
    const val = searchInput?.value.trim();
    if (val) {
      clearTimeout(state.searchDebounceTimer);
      saveRecentSearch(val);
      handleSearch(val, true);
      closeDesktopSearchDropdown();
      searchInput?.blur();
    } else {
      openDesktopSearchDropdown();
      searchInput?.focus();
    }
  });

  // Top Search Clear Button
  searchClearBtn?.addEventListener('click', () => {
    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }
    if (inViewSearchInput) {
      inViewSearchInput.value = '';
    }
    searchClearBtn.classList.add('hidden');
    inViewSearchClear?.classList.add('hidden');
    $('desktop-live-results-section')?.classList.add('hidden');
    // If on search view, show discovery state instead of kicking to home!
    if (state.activeView === 'search') {
      renderSearchDiscoveryState();
    }
    openDesktopSearchDropdown();
  });

  // In-View Search Input listeners
  inViewSearchInput?.addEventListener('input', (e) => {
    const val = e.target.value;
    if (searchInput) {
      searchInput.value = val;
      searchClearBtn?.classList.toggle('hidden', !val);
    }
    inViewSearchClear?.classList.toggle('hidden', !val);
    handleSearch(val, false);
  });

  inViewSearchInput?.addEventListener('focus', () => {
    if (inViewSearchInput.value) {
      inViewSearchInput.select();
    }
  });

  inViewSearchInput?.addEventListener('click', () => {
    if (inViewSearchInput.value) {
      inViewSearchInput.select();
    }
  });

  inViewSearchInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const val = inViewSearchInput.value.trim();
      if (val) {
        clearTimeout(state.searchDebounceTimer);
        saveRecentSearch(val);
        handleSearch(val, true);
        inViewSearchInput.blur();
      }
    } else if (e.key === 'Escape') {
      inViewSearchInput.blur();
    }
  });

  inViewSearchClear?.addEventListener('click', () => {
    if (inViewSearchInput) {
      inViewSearchInput.value = '';
      inViewSearchInput.focus();
    }
    if (searchInput) {
      searchInput.value = '';
    }
    inViewSearchClear.classList.add('hidden');
    searchClearBtn?.classList.add('hidden');
    renderSearchDiscoveryState();
  });

  // "Search Another Song" action button
  btnSearchAgain?.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      openMobileSearch();
    } else {
      const targetInput = inViewSearchInput || searchInput;
      if (targetInput) {
        targetInput.focus();
        targetInput.select();
      }
    }
  });

  // Desktop Search Trending Tags
  $('desktop-search-tags')?.addEventListener('click', (e) => {
    const tag = e.target.closest('.popover-tag');
    if (!tag) return;
    const q = tag.dataset.query || tag.textContent.trim();
    if (q) {
      if (searchInput) searchInput.value = q;
      searchClearBtn?.classList.remove('hidden');
      saveRecentSearch(q);
      handleSearch(q, true);
      closeDesktopSearchDropdown();
    }
  });

  // Desktop Clear All Recent Searches
  $('btn-clear-recent-search')?.addEventListener('click', (e) => {
    e.stopPropagation();
    clearAllRecentSearches();
  });

  // Close desktop dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#search-box-wrapper')) {
      closeDesktopSearchDropdown();
    }
  });

  // Search Category Filter Pills (All Tracks, Artists, Albums)
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeSearchFilter = pill.dataset.filter || 'all';
      if (state.lastSearchResults && state.lastSearchResults.length > 0) {
        renderSearchResults(state.lastSearchResults);
      }
    });
  });

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    const isEditing = e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable;

    // 1. Ctrl + K -> Focus Search
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      searchInput?.focus();
      searchInput?.select();
      return;
    }

    // 2. Ctrl + N -> Next Track
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'n' || e.code === 'KeyN')) {
      e.preventDefault();
      showToastNotification('Next Track (Ctrl + N)');
      playNextTrack(true);
      return;
    }

    // 3. Ctrl + B -> Back / Previous Track
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'b' || e.code === 'KeyB')) {
      e.preventDefault();
      showToastNotification('Previous Track (Ctrl + B)');
      playPrevTrack();
      return;
    }

    // 4. Single-key shortcuts (when not focused on a text input)
    if (!isEditing) {
      // 'P' or 'Space' -> Play / Pause
      if (e.key.toLowerCase() === 'p' || e.code === 'Space') {
        e.preventDefault();
        togglePlayPause();
        return;
      }

      // 'F' or 'C' -> TV Cinema Mode
      if (e.key.toLowerCase() === 'f' || e.key.toLowerCase() === 'c') {
        e.preventDefault();
        toggleCinemaAmbilight();
        return;
      }
      // 'E' -> Equalizer Studio
      if (e.key.toLowerCase() === 'e') {
        e.preventDefault();
        openEqualizerModal();
        return;
      }

      // 'T' -> Sleep Timer
      if (e.key.toLowerCase() === 't') {
        e.preventDefault();
        openSleepTimerModal();
        return;
      }

      // 'S' -> Shuffle
      if (e.key.toLowerCase() === 's') {
        e.preventDefault();
        state.isShuffle = !state.isShuffle;
        $('btn-ctrl-shuffle')?.classList.toggle('active', state.isShuffle);
        $('cinema-btn-shuffle')?.classList.toggle('active', state.isShuffle);
        showToastNotification(state.isShuffle ? 'Shuffle: On' : 'Shuffle: Off');
        return;
      }

      // 'R' -> Repeat mode cycle (off / all / one)
      if (e.key.toLowerCase() === 'r') {
        e.preventDefault();
        cycleRepeatMode();
        return;
      }

      // 'M' -> Mute / Unmute
      if (e.key.toLowerCase() === 'm') {
        e.preventDefault();
        $('btn-mute-toggle')?.click();
        return;
      }

      // 'Q' -> Queue drawer toggle
      if (e.key.toLowerCase() === 'q') {
        e.preventDefault();
        if ($('queue-drawer-overlay')?.classList.contains('hidden')) {
          openQueueDrawer();
        } else {
          closeQueueDrawer();
        }
        return;
      }

      // 'L' -> Synced Lyrics toggle
      if (e.key.toLowerCase() === 'l') {
        e.preventDefault();
        if (state.lyrics.isOpen) {
          closeLyrics();
        } else {
          openLyrics();
        }
        return;
      }

      // '?' -> Shortcuts Modal
      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault();
        openShortcutsModal();
        return;
      }

      // ArrowLeft / ArrowRight -> Seek -5s / +5s
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        const cur = isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function' ? ytPlayer.getCurrentTime() : (audio?.currentTime || 0);
        seekPlayerTo(Math.max(0, cur - 5));
        showToastNotification('Seek -5s');
        return;
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        const cur = isYTActive && ytPlayer && typeof ytPlayer.getCurrentTime === 'function' ? ytPlayer.getCurrentTime() : (audio?.currentTime || 0);
        seekPlayerTo(cur + 5);
        showToastNotification('Seek +5s');
        return;
      }

      // ArrowUp / ArrowDown -> Volume
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        const newVol = Math.min(1, Math.round((state.volume + 0.05) * 100) / 100);
        state.volume = newVol;
        if (audio) audio.volume = newVol;
        if ($('volume-slider')) $('volume-slider').value = newVol;
        showToastNotification(`Volume: ${Math.round(newVol * 100)}%`);
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const newVol = Math.max(0, Math.round((state.volume - 0.05) * 100) / 100);
        state.volume = newVol;
        if (audio) audio.volume = newVol;
        if ($('volume-slider')) $('volume-slider').value = newVol;
        showToastNotification(`Volume: ${Math.round(newVol * 100)}%`);
        return;
      }
    }

    // 5. Escape -> Close any open modals
    if (e.key === 'Escape') {
      closeQueueDrawer();
      closeLyrics();
      closeCinemaAmbilight();
      closeAuthModal();
      closeEqualizerModal();
      closeSleepTimerModal();
      closePlaybackSpeedPopover();
      closeShortcutsModal();
      closeStatsModal();
    }
  });

  // Player Transport Controls
  $('btn-ctrl-play')?.addEventListener('click', togglePlayPause);
  $('btn-ctrl-stop')?.addEventListener('click', stopPlayback);
  $('btn-ctrl-next')?.addEventListener('click', () => playNextTrack(true));
  $('btn-ctrl-prev')?.addEventListener('click', playPrevTrack);

  $('btn-ctrl-shuffle')?.addEventListener('click', () => {
    state.isShuffle = !state.isShuffle;
    $('btn-ctrl-shuffle')?.classList.toggle('active', state.isShuffle);
    $('cinema-btn-shuffle')?.classList.toggle('active', state.isShuffle);
    showToastNotification(state.isShuffle ? 'Shuffle: On' : 'Shuffle: Off');
  });

  $('btn-ctrl-repeat')?.addEventListener('click', cycleRepeatMode);

  // Remaining Time Toggle on Scrubber total timestamp
  $('scrub-total-time')?.addEventListener('click', toggleRemainingTime);

  // Wireless Cast & Streaming
  $('btn-neu-cast')?.addEventListener('click', triggerWirelessCast);

  // Shortcuts Modal Listeners
  $('btn-neu-shortcuts')?.addEventListener('click', openShortcutsModal);
  $('btn-close-shortcuts')?.addEventListener('click', closeShortcutsModal);
  $('shortcuts-backdrop')?.addEventListener('click', closeShortcutsModal);

  // Listening Stats Modal Listeners
  $('btn-view-stats')?.addEventListener('click', openStatsModal);
  $('btn-close-stats')?.addEventListener('click', closeStatsModal);
  $('stats-backdrop')?.addEventListener('click', closeStatsModal);
  $('btn-export-stats-json')?.addEventListener('click', exportStatsJSON);

  // M3U Playlist Export & Import Listeners
  $('btn-export-m3u')?.addEventListener('click', () => {
    const list = state.activeLibraryTab === 'local' ? state.localLibrary : (state.likedTracks.length ? state.likedTracks : state.queue);
    exportPlaylistToM3U(list, 'SongBuddy_Library.m3u');
  });
  $('btn-queue-export-m3u')?.addEventListener('click', () => {
    exportPlaylistToM3U(state.queue.length ? state.queue : (state.currentTrack ? [state.currentTrack] : []), 'SongBuddy_Queue.m3u');
  });
  $('btn-import-m3u')?.addEventListener('click', () => $('m3u-file-input')?.click());
  $('m3u-file-input')?.addEventListener('change', (e) => handleM3UFileUpload(e.target.files[0]));

  // Custom LRC Lyrics Import Listeners
  $('btn-load-custom-lrc')?.addEventListener('click', () => $('lrc-file-input')?.click());
  $('lrc-file-input')?.addEventListener('change', (e) => handleCustomLrcImport(e.target.files[0]));

  // Audio Quality Pills Listeners
  document.querySelectorAll('#audio-quality-pills-row .dsp-pill').forEach(btn => {
    btn.addEventListener('click', () => setAudioQuality(btn.dataset.quality));
  });

  // Custom Playlist Modal Listeners
  $('btn-create-playlist')?.addEventListener('click', openCreatePlaylistModal);
  $('btn-close-create-playlist')?.addEventListener('click', closeCreatePlaylistModal);
  $('btn-create-playlist-cancel')?.addEventListener('click', closeCreatePlaylistModal);
  $('create-playlist-backdrop')?.addEventListener('click', closeCreatePlaylistModal);
  $('btn-create-playlist-submit')?.addEventListener('click', handleCreatePlaylistSubmit);

  // Bulk Playlist Importer Modal Listeners
  $('btn-import-url-playlist')?.addEventListener('click', openImportPlaylistModal);
  $('btn-close-import-modal')?.addEventListener('click', closeImportPlaylistModal);
  $('btn-import-cancel')?.addEventListener('click', closeImportPlaylistModal);
  $('import-playlist-backdrop')?.addEventListener('click', closeImportPlaylistModal);
  $('btn-import-submit')?.addEventListener('click', handleImportPlaylistSubmit);

  // Library Navigation Sub-Tabs
  document.querySelectorAll('.lib-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchLibraryTab(btn.dataset.tab));
  });

  // Local Audio File Picker & Dropzone
  $('btn-browse-local')?.addEventListener('click', () => $('local-audio-file-input')?.click());
  const dropzone = $('local-dropzone');
  if (dropzone) {
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-active');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-active'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-active');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleLocalAudioFiles(e.dataTransfer.files);
      }
    });
  }

  // Global Audio File Drag & Drop onto Window
  window.addEventListener('dragover', (e) => {
    if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) {
      e.preventDefault();
    }
  });
  window.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const hasAudio = Array.from(e.dataTransfer.files).some(f => f.type.startsWith('audio/') || /\.(mp3|flac|wav|ogg|m4a|aac)$/i.test(f.name));
      if (hasAudio) {
        e.preventDefault();
        handleLocalAudioFiles(e.dataTransfer.files);
      }
    }
  });

  // Equalizer Advanced DSP Suite Listeners
  $('eq-preamp-slider')?.addEventListener('input', (e) => setPreampGain(e.target.value));
  $('eq-spatial-slider')?.addEventListener('input', (e) => setSpatialPan(e.target.value));
  document.querySelectorAll('.dsp-pill[data-crossfade]').forEach(btn => {
    btn.addEventListener('click', () => setCrossfadeSeconds(btn.dataset.crossfade));
  });
  $('eq-normalization-toggle')?.addEventListener('change', (e) => toggleNormalization(e.target.checked));
  $('eq-audiophile-toggle')?.addEventListener('change', (e) => toggleAudiophilePassthrough(e.target.checked));

  // TV Mode / Cinema Ambilight Mode Listeners (TV screen ambient roaming light experience)
  $('btn-cinema-mode')?.addEventListener('click', toggleCinemaAmbilight);
  $('btn-cinema-top')?.addEventListener('click', toggleCinemaAmbilight);
  $('cinema-tv-pill')?.addEventListener('click', closeCinemaAmbilight);
  $('dock-action-cinema')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    toggleCinemaAmbilight();
  });
  $('btn-close-cinema')?.addEventListener('click', closeCinemaAmbilight);
  $('cinema-btn-play')?.addEventListener('click', togglePlayPause);
  $('cinema-cover-art')?.addEventListener('click', togglePlayPause);
  $('cinema-btn-next')?.addEventListener('click', () => playNextTrack(true));
  $('cinema-btn-prev')?.addEventListener('click', playPrevTrack);
  $('cinema-btn-shuffle')?.addEventListener('click', () => {
    state.isShuffle = !state.isShuffle;
    $('btn-ctrl-shuffle')?.classList.toggle('active', state.isShuffle);
    $('cinema-btn-shuffle')?.classList.toggle('active', state.isShuffle);
  });
  $('cinema-btn-lyrics')?.addEventListener('click', () => {
    closeCinemaAmbilight();
    openLyrics();
  });

  // Cinema Scrubber Seeking
  $('cinema-scrubber-bar')?.addEventListener('click', (e) => {
    const bar = $('cinema-scrubber-bar');
    if (!bar) return;
    const rect = bar.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if (isYTActive && ytPlayer && typeof ytPlayer.getDuration === 'function') {
      const dur = ytPlayer.getDuration();
      if (dur > 0) {
        ytPlayer.seekTo(pos * dur, true);
        return;
      }
    }
    if (audio && audio.duration) {
      audio.currentTime = pos * audio.duration;
    }
  });

  // Scrubber seeking & tooltip
  const scrubber = $('scrubber-track-container');
  const tooltip = $('scrubber-tooltip');

  scrubber?.addEventListener('click', (e) => {
    const rect = scrubber.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    if (isYTActive && ytPlayer && typeof ytPlayer.getDuration === 'function') {
      const dur = ytPlayer.getDuration();
      if (dur > 0) {
        ytPlayer.seekTo(pos * dur, true);
        return;
      }
    }
    if (audio && audio.duration) {
      audio.currentTime = pos * audio.duration;
    }
  });

  scrubber?.addEventListener('mousemove', (e) => {
    const dur = (isYTActive && ytPlayer && typeof ytPlayer.getDuration === 'function')
      ? ytPlayer.getDuration()
      : (audio ? audio.duration : 0);
    if (!dur) return;
    const rect = scrubber.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const hoverTime = pos * dur;

    if (tooltip) {
      tooltip.textContent = formatTime(hoverTime);
      tooltip.style.left = `${pos * 100}%`;
      tooltip.classList.remove('hidden');
    }
  });

  scrubber?.addEventListener('mouseleave', () => {
    tooltip?.classList.add('hidden');
  });

  // Volume
  const volSlider = $('volume-slider');
  volSlider?.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    if (audio) audio.volume = val;
    if (ytPlayer && typeof ytPlayer.setVolume === 'function') {
      ytPlayer.setVolume(val * 100);
    }
    state.volume = val;
    localStorage.setItem('songbuddy_volume', val);
    const onIcon = $('vol-icon-on');
    const offIcon = $('vol-icon-off');
    if (val === 0) {
      onIcon?.classList.add('hidden');
      offIcon?.classList.remove('hidden');
    } else {
      onIcon?.classList.remove('hidden');
      offIcon?.classList.add('hidden');
    }
  });

  $('btn-mute-toggle')?.addEventListener('click', () => {
    state.isMuted = !state.isMuted;
    const onIcon = $('vol-icon-on');
    const offIcon = $('vol-icon-off');
    if (state.isMuted) {
      if (audio) audio.volume = 0;
      if (ytPlayer && typeof ytPlayer.mute === 'function') ytPlayer.mute();
      if (volSlider) volSlider.value = 0;
      onIcon?.classList.add('hidden');
      offIcon?.classList.remove('hidden');
    } else {
      if (audio) audio.volume = state.volume;
      if (ytPlayer && typeof ytPlayer.unMute === 'function') {
        ytPlayer.unMute();
        ytPlayer.setVolume(state.volume * 100);
      }
      if (volSlider) volSlider.value = state.volume;
      onIcon?.classList.remove('hidden');
      offIcon?.classList.add('hidden');
    }
  });

  // 3D Cover Flow perspective toggle
  $('btn-toggle-flow')?.addEventListener('click', () => {
    $('artwork-card-wrapper')?.classList.toggle('flow-active');
  });

  // Radio Station Regenerate button
  $('btn-refill-radio')?.addEventListener('click', () => {
    if (state.currentTrack) {
      state.radioQueue = [];
      loadRadioQueue(state.currentTrack.id, state.currentTrack.artist, state.currentTrack.title);
      showToastNotification(`Regenerating station for ${state.currentTrack.title}`);
    } else {
      showToastNotification('Play a track to seed the station');
    }
  });

  // Note: openLyrics() and closeLyrics() are globally defined for cross-component access

  // Theme Toggle Button
  $('btn-theme-toggle')?.addEventListener('click', toggleTheme);

  // Neumorphic Chips & Actions
  $('chip-lyrics')?.addEventListener('click', openLyrics);
  $('chip-karaoke')?.addEventListener('click', toggleKaraokeMode);
  $('btn-toggle-karaoke')?.addEventListener('click', toggleKaraokeMode);
  $('chip-8d')?.addEventListener('click', toggle8DAudio);
  $('toggle-8d-audio')?.addEventListener('change', toggle8DAudio);
  document.querySelectorAll('#eight-d-speed-pills .dsp-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const spd = e.currentTarget.dataset.speed;
      if (spd) set8DSpeed(spd);
    });
  });
  if (state.eightD && state.eightD.enabled) {
    $('chip-8d')?.classList.add('active');
    const toggle = $('toggle-8d-audio');
    if (toggle) toggle.checked = true;
    start8DOrbit();
  }
  $('chip-equalizer')?.addEventListener('click', (e) => {
    e.stopPropagation();
    openEqualizerModal();
  });

  // Queue Overlay Drawer & Nav Listeners
  $('btn-neu-queue')?.addEventListener('click', () => openQueueDrawer());
  $('nav-queue')?.addEventListener('click', () => openQueueDrawer());
  $('btn-close-queue')?.addEventListener('click', () => closeQueueDrawer());
  $('queue-drawer-backdrop')?.addEventListener('click', () => closeQueueDrawer());
  $('btn-clear-queue')?.addEventListener('click', () => clearQueue());
  $('btn-clear-auto-queue')?.addEventListener('click', () => clearRadioQueue());
  $('btn-queue-skip-np')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!state.currentTrack) return;
    const skippedTitle = state.currentTrack.title;
    playNextTrack(true);
    showToastNotification(`Skipped "${skippedTitle}"`);
  });

  // Autoplay Switch in Queue Drawer
  const autoplaySwitch = $('queue-autoplay-switch');
  if (autoplaySwitch) {
    autoplaySwitch.checked = (state.autoplay !== false);
    autoplaySwitch.addEventListener('change', (e) => {
      state.autoplay = e.target.checked;
      localStorage.setItem('songbuddy_autoplay', state.autoplay ? 'true' : 'false');
      showToastNotification(`Autoplay ${state.autoplay ? 'Enabled' : 'Disabled'}`);
      renderQueueDrawer();
    });
  }

  // Neumorphic Share Button (Opens Expirable Signed Link Modal)
  $('btn-neu-share')?.addEventListener('click', () => {
    if (!state.currentTrack) {
      showToastNotification('Select a track to share');
      return;
    }
    openShareLinkModal();
  });

  // Neumorphic Heart Button
  $('btn-neu-heart')?.addEventListener('click', () => {
    if (state.currentTrack) {
      toggleLike(state.currentTrack);
    }
  });

  // Audio Suite: Equalizer, Speed & Sleep Timer Buttons
  $('btn-neu-speed')?.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePlaybackSpeedPopover($('btn-neu-speed'));
  });

  $('btn-neu-timer')?.addEventListener('click', () => openSleepTimerModal());
  $('btn-neu-eq')?.addEventListener('click', () => openEqualizerModal());
  $('cinema-btn-eq')?.addEventListener('click', () => openEqualizerModal());
  $('btn-neu-sponsorblock')?.addEventListener('click', () => toggleSponsorBlock());
  $('btn-sb-undo')?.addEventListener('click', () => revertSponsorBlockSkip());

  // Equalizer Modal Controls
  $('btn-close-equalizer')?.addEventListener('click', closeEqualizerModal);
  $('equalizer-backdrop')?.addEventListener('click', closeEqualizerModal);
  $('eq-master-toggle')?.addEventListener('change', (e) => toggleEqualizerMaster(e.target.checked));
  $('btn-eq-reset')?.addEventListener('click', () => setEqualizerPreset('flat'));

  document.querySelectorAll('.eq-preset-pill').forEach(pill => {
    pill.addEventListener('click', () => setEqualizerPreset(pill.dataset.preset));
  });

  for (let b = 0; b <= 4; b++) {
    $(`eq-slider-${b}`)?.addEventListener('input', (e) => {
      setEqualizerBand(b, parseFloat(e.target.value));
    });
  }

  // Sleep Timer Controls
  $('btn-close-sleep-timer')?.addEventListener('click', closeSleepTimerModal);
  $('sleep-timer-backdrop')?.addEventListener('click', closeSleepTimerModal);
  $('btn-cancel-timer')?.addEventListener('click', () => {
    clearSleepTimer();
    showToastNotification('Sleep Timer turned off');
  });

  document.querySelectorAll('.sleep-option-btn').forEach(btn => {
    btn.addEventListener('click', () => setSleepTimer(btn.dataset.minutes));
  });

  // Playback Speed Options
  document.querySelectorAll('.speed-option').forEach(btn => {
    btn.addEventListener('click', () => setPlaybackSpeed(btn.dataset.speed));
  });

  // Floating Bottom Clay Dock
  // 1. Music / Now Playing & Lyrics Button
  $('dock-btn-music')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    updateDockActive('dock-btn-music');
    if (state.lyrics.isOpen) {
      closeLyrics();
      closeMobileSearch();
      closeQueueDrawer();
      if (!state.currentTrack) {
        playTrack(HERO_SLIDES[0]);
      }
      openLyrics();
      showToastNotification(`Now Playing: ${state.currentTrack ? state.currentTrack.title : 'Lyrics & Audio'}`);
    }
  });

  // 2. Home / Explore Feed Button
  $('dock-btn-home')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    if (state.lyrics.isOpen) {
      closeLyrics();
    }
    closeQueueDrawer();
    switchView('home');
    updateDockActive('dock-btn-home');
    const feed = $('main-feed');
    if (feed) feed.scrollTo({ top: 0, behavior: 'smooth' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToastNotification('Exploring Home Feed');
  });

  // Dedicated Dock Search Button (Mobile & Desktop)
  $('dock-btn-search')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    if (state.lyrics.isOpen) {
      closeLyrics();
    }
    closeQueueDrawer();
    if (window.innerWidth <= 768) {
      openMobileSearch();
      return;
    }
    switchView('search');
    updateDockActive('dock-btn-search');
    const input = $('in-view-search-input') || $('search-input');
    if (input) {
      if (input.value.trim()) {
        handleSearch(input.value.trim(), true);
      } else {
        renderSearchDiscoveryState();
      }
      setTimeout(() => {
        input.focus();
        input.select();
      }, 50);
    }
  });

  // Mobile Header Search Button
  $('btn-neu-search-mobile')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    openMobileSearch();
  });

  // Mobile Expandable Search Bar Pill
  const mobileSearchPill = $('mobile-search-pill-bar');
  mobileSearchPill?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    openMobileSearch();
  });
  mobileSearchPill?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleDockUserPopover(true);
      openMobileSearch();
    }
  });

  // Initialize swipe-to-dismiss gestures for mobile search drawer
  initMobileSearchGestures();

  // Mobile Search Drawer Event Listeners
  $('btn-close-mobile-search')?.addEventListener('click', closeMobileSearch);
  $('mobile-search-backdrop')?.addEventListener('click', closeMobileSearch);
  $('mobile-search-clear')?.addEventListener('click', () => {
    const input = $('mobile-search-input');
    if (input) {
      input.value = '';
      input.focus();
    }
    $('mobile-search-clear')?.classList.add('hidden');
    renderMobileSearchResults(HERO_SLIDES, 'Trending Hits (Tap to play)');
  });

  $('mobile-search-input')?.addEventListener('input', (e) => {
    clearTimeout(mobileSearchDebounce);
    const q = e.target.value;
    mobileSearchDebounce = setTimeout(() => {
      searchMobileMusic(q);
    }, 280);
  });

  document.querySelectorAll('.mobile-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      document.querySelectorAll('.mobile-tag').forEach(t => t.classList.remove('active'));
      tag.classList.add('active');
      const q = tag.dataset.query || tag.textContent.replace(/[^\w\s-]/g, '').trim();
      const input = $('mobile-search-input');
      if (input) input.value = (q === 'Trending') ? '' : q;
      searchMobileMusic((q === 'Trending') ? '' : q);
    });
  });

  // 3. User / Account Settings Button
  $('dock-btn-user')?.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDockUserPopover();
  });

  // Actions inside Dock User Popover
  $('dock-action-favs')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    switchView('library');
    updateDockActive('dock-btn-music');
  });

  $('dock-action-theme')?.addEventListener('click', () => {
    toggleTheme();
    toggleDockUserPopover(true);
  });

  $('dock-action-account')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    openAuthModal();
  });

  // Screen-Off Audio Playback Mode Toggles
  $('btn-screenoff-mode')?.addEventListener('click', () => {
    toggleScreenOffMode();
  });

  $('dock-action-screenoff')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    toggleScreenOffMode();
  });

  // Display-Off & Tab Visibility Monitor: Keeps audio running when display turns off
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      if (state.isPlaying && state.screenOffPlayback) {
        enableBackgroundAudioSession();
        if (isYTActive && ytPlayer && typeof ytPlayer.playVideo === 'function') {
          setTimeout(() => {
            if (state.isPlaying) {
              try { ytPlayer.playVideo(); } catch (e) {}
            }
          }, 80);
        }
        if ('mediaSession' in navigator) {
          navigator.mediaSession.playbackState = 'playing';
        }
      }
    } else {
      if (state.isPlaying) {
        updatePlayPauseIcons(true);
        if (isYTActive) startYTProgressTracker();
        if (state.keepScreenAwake || state.cinemaMode) {
          requestScreenWakeLock();
        }
      }
    }
  });

  // 3. Queue / Automix Drawer Button
  $('dock-btn-queue')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    openQueueDrawer();
  });

  // Mobile Mini-Player Controls
  $('mobile-mini-play')?.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePlayPause();
  });

  $('mobile-mini-next')?.addEventListener('click', (e) => {
    e.stopPropagation();
    playNextTrack(true);
  });

  $('mobile-mini-info-tap')?.addEventListener('click', () => {
    if (state.currentTrack) {
      openQueueDrawer();
    }
  });

  $('mobile-mini-thumb')?.addEventListener('click', () => {
    if (state.currentTrack) {
      openLyrics();
    }
  });

  // Close dock popover when clicking anywhere outside
  document.addEventListener('click', (e) => {
    const popover = $('dock-user-popover');
    if (popover && !popover.classList.contains('hidden')) {
      if (!popover.contains(e.target) && !$('dock-btn-user')?.contains(e.target)) {
        toggleDockUserPopover(true);
      }
    }
  });

  $('btn-lyrics-pullup')?.addEventListener('click', openLyrics);
  $('btn-open-lyrics')?.addEventListener('click', openLyrics);
  $('player-mini-lyrics')?.addEventListener('click', openLyrics);
  $('btn-close-lyrics-overlay')?.addEventListener('click', closeLyrics);
  $('lyrics-overlay-backdrop')?.addEventListener('click', closeLyrics);

  // Authentication & Login Modal Listeners
  $('btn-close-auth-overlay')?.addEventListener('click', closeAuthModal);
  $('auth-backdrop')?.addEventListener('click', closeAuthModal);
  $('btn-continue-guest')?.addEventListener('click', closeAuthModal);

  // Authentication & Login Modal Listeners
  $('tab-sign-in')?.addEventListener('click', () => setAuthMode('sign-in'));
  $('tab-register')?.addEventListener('click', () => setAuthMode('register'));
  $('btn-quick-demo')?.addEventListener('click', () => loginUser(DEFAULT_USER, true));
  $('btn-social-spotify')?.addEventListener('click', () => loginUser(SPOTIFY_USER, true));
  $('btn-social-google')?.addEventListener('click', () => loginUser(GOOGLE_USER, true));

  // Dynamically hide demo account button in production if disabled on backend
  fetch('/api/health')
    .then(r => r.json())
    .then(data => {
      if (data?.auth_storage?.demo_account_enabled === false) {
        const demoBox = document.querySelector('.quick-demo-box');
        if (demoBox) demoBox.style.display = 'none';
        const divider = document.querySelector('.auth-divider');
        if (divider) divider.style.display = 'none';
      }
    })
    .catch(() => {});

  // Password visibility eye toggle
  $('btn-toggle-password')?.addEventListener('click', () => {
    const pwInput = $('auth-input-password');
    const showIcon = $('eye-icon-show');
    const hideIcon = $('eye-icon-hide');
    if (!pwInput) return;
    const isPw = pwInput.type === 'password';
    pwInput.type = isPw ? 'text' : 'password';
    if (isPw) {
      showIcon?.classList.add('hidden');
      hideIcon?.classList.remove('hidden');
    } else {
      showIcon?.classList.remove('hidden');
      hideIcon?.classList.add('hidden');
    }
  });

  // Forgot password hint
  $('link-forgot-pw')?.addEventListener('click', (e) => {
    e.preventDefault();
    showAuthAlert('Reset instructions sent to your registered address (Demo).', 'success');
  });

  // Form submission
  $('auth-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    handleAuthFormSubmit();
  });

  // User Dropdown interactions
  $('user-profile-pill')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!state.user) {
      openAuthModal();
    } else {
      toggleUserDropdown();
    }
  });

  document.addEventListener('click', (e) => {
    const container = $('user-profile-container');
    if (container && !container.contains(e.target)) {
      closeUserDropdown();
    }
  });

  $('btn-menu-logout')?.addEventListener('click', () => {
    logoutUser();
  });

  $('btn-menu-switch-account')?.addEventListener('click', () => {
    closeUserDropdown();
    openAuthModal();
  });

  // Close modals on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const overlay = $('auth-overlay');
      if (overlay && !overlay.classList.contains('hidden')) {
        closeAuthModal();
      }
      const jbModal = $('jukebox-modal');
      if (jbModal && !jbModal.classList.contains('hidden')) {
        closeJukeboxModal();
      }
      const shModal = $('share-link-modal');
      if (shModal && !shModal.classList.contains('hidden')) {
        closeShareLinkModal();
      }
    }
  });

  $('btn-menu-liked')?.addEventListener('click', () => {
    closeUserDropdown();
    switchView('library');
  });

  // Social Jukebox and Expirable Public Share triggers
  $('btn-top-jukebox')?.addEventListener('click', () => openJukeboxModal());
  $('chip-jukebox')?.addEventListener('click', () => openJukeboxModal());
  $('nav-jukebox')?.addEventListener('click', () => openJukeboxModal());
  $('dock-action-jukebox')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    openJukeboxModal();
  });
}

// ============================================================================
// Progressive Web App (PWA) Controller & Installation Service
// ============================================================================
let deferredPWAInstallPrompt = null;

function initPWA() {
  // 1. Register Service Worker for offline resilience & PWA capabilities
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js')
        .then((registration) => {
          console.log('[SongBuddy PWA] Service Worker active with scope:', registration.scope);
          registration.update().catch(() => {});
          registration.onupdatefound = () => {
            const installingWorker = registration.installing;
            if (installingWorker) {
              installingWorker.onstatechange = () => {
                if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('[SongBuddy PWA] New update ready; activating immediately.');
                  installingWorker.postMessage({ type: 'SKIP_WAITING' });
                  showToastNotification('SongBuddy updated! Refreshing with latest features');
                  setTimeout(() => {
                    window.location.reload();
                  }, 1200);
                }
              };
            }
          };
        })
        .catch((err) => {
          console.warn('[SongBuddy PWA] Service Worker registration failed:', err);
        });
    });

    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) {
        refreshing = true;
        window.location.reload();
      }
    });
  }

  // 2. Capture install prompt
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPWAInstallPrompt = e;

    // Reveal install triggers in UI
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
    if (!isStandalone) {
      $('pwa-install-sidebar')?.classList.remove('hidden');
      $('btn-pwa-install-header')?.classList.remove('hidden');
      $('dock-action-install')?.classList.remove('hidden');

      // Show bottom toast banner if not recently dismissed
      const dismissed = localStorage.getItem('songbuddy_pwa_dismissed');
      const now = Date.now();
      if (!dismissed || (now - parseInt(dismissed, 10)) > 24 * 60 * 60 * 1000) {
        setTimeout(() => {
          if (deferredPWAInstallPrompt && !window.matchMedia('(display-mode: standalone)').matches) {
            $('pwa-install-toast')?.classList.remove('hidden');
            setTimeout(() => {
              $('pwa-install-toast')?.classList.add('hidden');
            }, 5500);
          }
        }, 3500);
      }
    }
  });

  // 3. Handle install completion
  window.addEventListener('appinstalled', () => {
    console.log('[SongBuddy PWA] Application successfully installed.');
    $('pwa-install-toast')?.classList.add('hidden');
    $('pwa-install-sidebar')?.classList.add('hidden');
    $('btn-pwa-install-header')?.classList.add('hidden');
    deferredPWAInstallPrompt = null;
    showToastNotification('SongBuddy successfully installed! Enjoy ad-free music.');
  });

  // 4. Hook up user trigger events
  const installElements = [
    $('pwa-install-sidebar'),
    $('btn-pwa-install-header'),
    $('btn-pwa-install-toast'),
    $('dock-action-install')
  ];

  installElements.forEach((btn) => {
    btn?.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleDockUserPopover(true);
      handlePWAInstallClick();
    });
  });

  $('btn-pwa-dismiss')?.addEventListener('click', () => {
    $('pwa-install-toast')?.classList.add('hidden');
    localStorage.setItem('songbuddy_pwa_dismissed', Date.now().toString());
  });
}

async function handlePWAInstallClick() {
  if (deferredPWAInstallPrompt) {
    deferredPWAInstallPrompt.prompt();
    const { outcome } = await deferredPWAInstallPrompt.userChoice;
    console.log('[SongBuddy PWA] User install response:', outcome);
    if (outcome === 'accepted') {
      $('pwa-install-toast')?.classList.add('hidden');
      $('pwa-install-sidebar')?.classList.add('hidden');
      $('btn-pwa-install-header')?.classList.add('hidden');
    }
    deferredPWAInstallPrompt = null;
  } else {
    // Fallback guidance for iOS Safari or browsers where prompt isn't directly invocable
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (isIOS) {
      alert('To install SongBuddy on iOS: Tap the Share button (square with arrow up) at the bottom of Safari, then tap "Add to Home Screen".');
    } else if (window.matchMedia('(display-mode: standalone)').matches) {
      showToastNotification('SongBuddy is already running as an installed App.');
    } else {
      showToastNotification('To install: click the Install icon in your browser address bar or menu.');
    }
  }
}

// ============================================================================
// OPENSUBSONIC MOBILE INTEGRATION CONTROLLER
// ============================================================================
function initSubsonicUI() {
  const modal = $('subsonic-modal');
  const backdrop = $('subsonic-backdrop');
  const btnClose = $('btn-close-subsonic');
  const btnDone = $('btn-done-subsonic');
  const btnOpenTop = $('btn-studio-subsonic');
  const chipOpen = $('chip-subsonic');

  const inputUrl = $('subsonic-input-url');
  const inputUser = $('subsonic-input-user');
  const inputPass = $('subsonic-input-pass');

  const btnCopyUrl = $('btn-copy-subsonic-url');
  const btnCopyUser = $('btn-copy-subsonic-user');
  const btnCopyPass = $('btn-copy-subsonic-pass');

  const btnPing = $('btn-test-subsonic-conn');
  const pingBtnText = $('subsonic-ping-btn-text');
  const statusText = $('subsonic-status-text');
  const liveIndicator = $('subsonic-indicator');

  // Dynamically set server URL based on current origin
  if (inputUrl) {
    const origin = window.location.origin;
    inputUrl.value = `${origin}/rest`;
  }

  function openSubsonicModal() {
    if (!modal) return;
    if (inputUrl) {
      inputUrl.value = `${window.location.origin}/rest`;
    }
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeSubsonicModal() {
    if (!modal) return;
    modal.classList.add('hidden');
    document.body.style.overflow = '';
  }

  btnOpenTop?.addEventListener('click', openSubsonicModal);
  chipOpen?.addEventListener('click', openSubsonicModal);
  btnClose?.addEventListener('click', closeSubsonicModal);
  btnDone?.addEventListener('click', closeSubsonicModal);
  backdrop?.addEventListener('click', closeSubsonicModal);

  // Copy helper with feedback
  function setupCopyButton(btn, input, label) {
    btn?.addEventListener('click', async () => {
      if (!input) return;
      try {
        await navigator.clipboard.writeText(input.value);
        const origText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.background = '#ffffff';
        btn.style.color = '#000000';
        showToastNotification(`Copied ${label} to clipboard`);
        setTimeout(() => {
          btn.textContent = origText;
          btn.style.background = '';
          btn.style.color = '';
        }, 1800);
      } catch (err) {
        input.select();
        document.execCommand('copy');
        showToastNotification(`Copied ${label}`);
      }
    });
  }

  setupCopyButton(btnCopyUrl, inputUrl, 'Server URL');
  setupCopyButton(btnCopyUser, inputUser, 'Username');
  setupCopyButton(btnCopyPass, inputPass, 'Password');

  // Test Ping handler
  btnPing?.addEventListener('click', async () => {
    if (!statusText) return;
    const startTime = performance.now();
    if (pingBtnText) pingBtnText.textContent = 'Pinging...';
    if (liveIndicator) liveIndicator.style.background = '#aaaaaa';

    try {
      const resp = await fetch('/rest/ping.view?u=admin&p=songbuddy&f=json');
      const latency = Math.round(performance.now() - startTime);
      if (resp.ok) {
        const data = await resp.json();
        const ver = data?.['subsonic-response']?.version || '1.16.1';
        statusText.textContent = `200 OK — ${latency}ms latency — v${ver} Ready`;
        if (liveIndicator) {
          liveIndicator.style.background = '#ffffff';
          liveIndicator.style.boxShadow = '0 0 10px #ffffff';
        }
        showToastNotification(`OpenSubsonic ping OK (${latency}ms)`);
      } else {
        statusText.textContent = `Status: HTTP ${resp.status}`;
      }
    } catch (e) {
      statusText.textContent = 'Ping failed: ' + e.message;
      if (liveIndicator) liveIndicator.style.background = '#ff4444';
    } finally {
      if (pingBtnText) pingBtnText.textContent = 'Test Ping';
    }
  });

  // ESC key listener
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
      closeSubsonicModal();
    }
  });
}

// ============================================================================
// SOCIAL JUKEBOX & PARTY VOTING ENGINE
// ============================================================================
function initJukeboxUI() {
  const modal = $('jukebox-modal');
  const backdrop = $('jukebox-backdrop');
  const btnClose = $('btn-close-jukebox');

  // Tabs
  const tabHost = $('tab-jukebox-host');
  const tabGuest = $('tab-jukebox-guest');

  // Host buttons & toggles
  const btnCopyCode = $('btn-copy-party-code');
  const btnCopyLink = $('btn-copy-party-link');
  const btnNewRoom = $('btn-jukebox-new-room');
  const btnNextTop = $('btn-jukebox-next-top');
  const btnClearQueue = $('btn-jukebox-clear-queue');
  const chkAutoAdvance = $('chk-jukebox-auto-advance');

  // Guest search
  const guestSearchInput = $('jukebox-guest-search');
  const guestSearchDropdown = $('jukebox-search-dropdown');

  let guestSearchTimer = null;

  // Persist guest ID in localStorage
  if (!localStorage.getItem('songbuddy_jukebox_guest_id')) {
    localStorage.setItem('songbuddy_jukebox_guest_id', state.jukebox.guestId);
  }

  // Load host token from localStorage if exists
  const storedHostToken = localStorage.getItem(`songbuddy_jukebox_host_${state.jukebox.currentRoomCode}`);
  if (storedHostToken) {
    state.jukebox.hostToken = storedHostToken;
  }

  // Auto-advance toggle sync
  if (chkAutoAdvance) {
    chkAutoAdvance.checked = state.jukebox.autoAdvance;
    chkAutoAdvance.addEventListener('change', (e) => {
      state.jukebox.autoAdvance = e.target.checked;
      showToastNotification(e.target.checked ? 'Party auto-advance enabled' : 'Party auto-advance disabled');
    });
  }

  // Close bindings
  btnClose?.addEventListener('click', closeJukeboxModal);
  backdrop?.addEventListener('click', closeJukeboxModal);

  // Tab switching
  tabHost?.addEventListener('click', () => switchJukeboxTab('host'));
  tabGuest?.addEventListener('click', () => switchJukeboxTab('guest'));

  // Host Actions
  btnCopyCode?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(state.jukebox.currentRoomCode);
      showToastNotification(`Room code copied: ${state.jukebox.currentRoomCode}`);
    } catch (e) {
      showToastNotification(`Party Room: ${state.jukebox.currentRoomCode}`);
    }
  });

  btnCopyLink?.addEventListener('click', async () => {
    const link = `${window.location.origin}/#party=${state.jukebox.currentRoomCode}`;
    try {
      await navigator.clipboard.writeText(link);
      showToastNotification('Party join link copied to clipboard!');
    } catch (e) {
      showToastNotification(`Join link: ${link}`);
    }
  });

  btnNewRoom?.addEventListener('click', async () => {
    const name = prompt('Enter a name for your party session:', 'Live Jukebox Party');
    if (name === null) return;
    try {
      const res = await fetch('/api/jukebox/room', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() || 'Live Jukebox Party' })
      });
      if (!res.ok) throw new Error('Failed to create room');
      const data = await res.json();
      state.jukebox.currentRoomCode = data.code;
      state.jukebox.hostToken = data.host_token;
      localStorage.setItem(`songbuddy_jukebox_host_${data.code}`, data.host_token);
      renderJukeboxRoomHeader();
      await fetchJukeboxRoom();
      showToastNotification(`Party room created: ${data.code}`);
    } catch (err) {
      showToastNotification('Error creating party room');
    }
  });

  btnNextTop?.addEventListener('click', async () => {
    await advanceJukeboxQueue(true);
  });

  btnClearQueue?.addEventListener('click', async () => {
    if (!state.jukebox.hostToken) {
      showToastNotification('Host permission required to clear queue');
      return;
    }
    if (!confirm('Clear all enqueued tracks in this party room?')) return;
    try {
      const res = await fetch('/api/jukebox/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: state.jukebox.currentRoomCode, host_token: state.jukebox.hostToken })
      });
      if (res.ok) {
        showToastNotification('Party queue cleared');
        await fetchJukeboxRoom();
      } else {
        showToastNotification('Failed to clear queue');
      }
    } catch (err) {
      showToastNotification('Error clearing queue');
    }
  });

  // Guest Search Input Handler
  guestSearchInput?.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    clearTimeout(guestSearchTimer);
    if (!query) {
      if (guestSearchDropdown) {
        guestSearchDropdown.innerHTML = '';
        guestSearchDropdown.classList.add('hidden');
      }
      return;
    }
    guestSearchTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=6`);
        if (!res.ok) return;
        const tracks = await res.json();
        renderGuestSearchDropdown(tracks);
      } catch (err) {
        console.warn('[Jukebox Search Error]', err);
      }
    }, 280);
  });

  // Close search dropdown on click outside
  document.addEventListener('click', (e) => {
    if (guestSearchDropdown && !guestSearchDropdown.contains(e.target) && e.target !== guestSearchInput) {
      guestSearchDropdown.classList.add('hidden');
    }
  });
}

function openJukeboxModal(targetTab = 'host') {
  const modal = $('jukebox-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  switchJukeboxTab(targetTab);
  renderJukeboxRoomHeader();
  fetchJukeboxRoom();
  startJukeboxPolling();
}

function closeJukeboxModal() {
  const modal = $('jukebox-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  document.body.style.overflow = '';
  stopJukeboxPolling();
}

function switchJukeboxTab(tab) {
  state.jukebox.activeTab = tab;
  const tabHost = $('tab-jukebox-host');
  const tabGuest = $('tab-jukebox-guest');
  const paneHost = $('pane-jukebox-host');
  const paneGuest = $('pane-jukebox-guest');

  tabHost?.classList.toggle('active', tab === 'host');
  tabGuest?.classList.toggle('active', tab === 'guest');
  paneHost?.classList.toggle('hidden', tab !== 'host');
  paneGuest?.classList.toggle('hidden', tab !== 'guest');
}

function renderJukeboxRoomHeader() {
  const codeVal = $('jukebox-code-val');
  if (codeVal) codeVal.textContent = state.jukebox.currentRoomCode;

  const qrBox = $('jukebox-qr-box');
  if (qrBox) {
    const qrUrl = `/api/jukebox/qr?code=${encodeURIComponent(state.jukebox.currentRoomCode)}`;
    qrBox.innerHTML = `<img src="${qrUrl}" alt="Party QR Code" class="jukebox-qr-img" width="160" height="160" style="display:block;border-radius:10px;background:#ffffff;padding:6px;">`;
  }
}

function startJukeboxPolling() {
  stopJukeboxPolling();
  state.jukebox.pollTimer = setInterval(() => {
    const modal = $('jukebox-modal');
    if (modal && !modal.classList.contains('hidden')) {
      fetchJukeboxRoom(true);
    } else {
      stopJukeboxPolling();
    }
  }, 3000);
}

function stopJukeboxPolling() {
  if (state.jukebox.pollTimer) {
    clearInterval(state.jukebox.pollTimer);
    state.jukebox.pollTimer = null;
  }
}

async function fetchJukeboxRoom(isBackground = false) {
  try {
    const code = state.jukebox.currentRoomCode;
    const guestId = state.jukebox.guestId;
    const res = await fetch(`/api/jukebox/room?code=${encodeURIComponent(code)}&guest_id=${encodeURIComponent(guestId)}`);
    if (!res.ok) {
      if (!isBackground) showToastNotification('Party room not found');
      return;
    }
    const data = await res.json();
    renderJukeboxQueue(data.queue || []);
  } catch (err) {
    if (!isBackground) console.warn('[Jukebox Fetch Error]', err);
  }
}

function renderJukeboxQueue(queue) {
  const countEl = $('jukebox-queue-count');
  if (countEl) countEl.textContent = queue.length;

  const hostList = $('jukebox-host-queue-list');
  const hostEmpty = $('jukebox-host-empty');
  const guestList = $('jukebox-guest-queue-list');
  const guestEmpty = $('jukebox-guest-empty');

  // Render Host Queue
  if (hostList) {
    hostList.innerHTML = '';
    if (queue.length === 0) {
      if (hostEmpty) {
        hostEmpty.classList.remove('hidden');
        hostList.appendChild(hostEmpty);
      }
    } else {
      queue.forEach((item, index) => {
        const row = createJukeboxQueueItem(item, index, false);
        hostList.appendChild(row);
      });
    }
  }

  // Render Guest Queue
  if (guestList) {
    guestList.innerHTML = '';
    if (queue.length === 0) {
      if (guestEmpty) {
        guestEmpty.classList.remove('hidden');
        guestList.appendChild(guestEmpty);
      }
    } else {
      queue.forEach((item, index) => {
        const row = createJukeboxQueueItem(item, index, true);
        guestList.appendChild(row);
      });
    }
  }
}

function createJukeboxQueueItem(item, index, isGuestMode) {
  const div = document.createElement('div');
  div.className = 'jukebox-queue-item';

  const isUpvoted = item.user_vote === 1;
  const isDownvoted = item.user_vote === -1;
  const scoreFormatted = item.score > 0 ? `+${item.score}` : `${item.score}`;

  const thumbSrc = item.thumbnail || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" fill="%23222"><rect width="100%" height="100%" fill="%23111"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23888" font-size="12">AUDIO</text></svg>';

  div.innerHTML = `
    <span class="jukebox-item-rank">#${index + 1}</span>
    <img src="${escapeHTML(thumbSrc)}" class="jukebox-item-art" alt="" loading="lazy">
    <div class="jukebox-item-info">
      <div class="jukebox-item-title" title="${escapeHTML(item.title)}">${escapeHTML(item.title)}</div>
      <div class="jukebox-item-sub">
        <span>${escapeHTML(item.artist)}</span>
        <span>•</span>
        <span>${escapeHTML(item.duration || '3:00')}</span>
        <span>•</span>
        <span class="jukebox-submitter-tag">by ${escapeHTML(item.submitter_name || 'Guest')}</span>
      </div>
    </div>
    <div class="jukebox-votes-wrap">
      <button type="button" class="jukebox-vote-btn upvote ${isUpvoted ? 'active' : ''}" title="Upvote" data-track-id="${escapeHTML(item.track_id)}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
          <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
      </button>
      <span class="jukebox-score-val ${item.score > 0 ? 'positive' : item.score < 0 ? 'negative' : ''}">${scoreFormatted}</span>
      <button type="button" class="jukebox-vote-btn downvote ${isDownvoted ? 'active' : ''}" title="Downvote" data-track-id="${escapeHTML(item.track_id)}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>
    </div>
  `;

  // Attach voting listeners
  const upBtn = div.querySelector('.upvote');
  const downBtn = div.querySelector('.downvote');

  upBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    handleCastVote(item.track_id, isUpvoted ? 0 : 1);
  });

  downBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    handleCastVote(item.track_id, isDownvoted ? 0 : -1);
  });

  return div;
}

async function handleCastVote(trackId, voteVal) {
  try {
    const res = await fetch('/api/jukebox/vote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: state.jukebox.currentRoomCode,
        track_id: trackId,
        vote: voteVal,
        guest_id: state.jukebox.guestId
      })
    });
    if (res.ok) {
      await fetchJukeboxRoom();
    } else {
      const err = await res.json();
      showToastNotification(err.error || 'Failed to register vote');
    }
  } catch (err) {
    showToastNotification('Network error casting vote');
  }
}

function renderGuestSearchDropdown(tracks) {
  const dropdown = $('jukebox-search-dropdown');
  if (!dropdown) return;
  dropdown.innerHTML = '';

  if (!Array.isArray(tracks) || tracks.length === 0) {
    dropdown.innerHTML = '<div style="padding:12px;color:var(--text-muted);font-size:0.85rem;">No matching songs found.</div>';
    dropdown.classList.remove('hidden');
    return;
  }

  tracks.forEach(track => {
    const item = document.createElement('div');
    item.className = 'jukebox-search-item';
    item.innerHTML = `
      <img src="${escapeHTML(track.thumbnail || '')}" class="jukebox-search-art" alt="">
      <div class="jukebox-search-meta">
        <div class="jukebox-search-title">${escapeHTML(track.title)}</div>
        <div class="jukebox-search-sub">${escapeHTML(track.artist)} • ${escapeHTML(track.duration_formatted || '3:00')}</div>
      </div>
      <button type="button" class="btn-jukebox-add-track" title="Add to Party Queue">+ Add</button>
    `;

    const addBtn = item.querySelector('.btn-jukebox-add-track');
    addBtn?.addEventListener('click', async (e) => {
      e.stopPropagation();
      await enqueueTrackToJukebox(track);
    });

    dropdown.appendChild(item);
  });

  dropdown.classList.remove('hidden');
}

async function enqueueTrackToJukebox(track) {
  try {
    const submitterName = (state.user && state.user.name) || 'Guest';
    const res = await fetch('/api/jukebox/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: state.jukebox.currentRoomCode,
        track_id: track.id,
        title: track.title,
        artist: track.artist,
        duration: track.duration_formatted || '3:00',
        thumbnail: track.thumbnail || '',
        guest_id: state.jukebox.guestId,
        guest_name: submitterName
      })
    });

    if (res.status === 409) {
      showToastNotification('Track is already in queue or currently playing!');
      return;
    }
    if (res.status === 429) {
      showToastNotification('Rate limit reached (max 5 songs in 10 minutes)');
      return;
    }
    if (res.status === 403) {
      showToastNotification('Guest submissions are currently disabled by the host.');
      return;
    }
    if (!res.ok) {
      const err = await res.json();
      showToastNotification(err.error || 'Failed to add track to queue');
      return;
    }

    showToastNotification(`Added "${track.title}" to party queue!`);
    const input = $('jukebox-guest-search');
    if (input) input.value = '';
    const dropdown = $('jukebox-search-dropdown');
    if (dropdown) {
      dropdown.innerHTML = '';
      dropdown.classList.add('hidden');
    }
    await fetchJukeboxRoom();
  } catch (err) {
    showToastNotification('Network error adding song to queue');
  }
}

async function advanceJukeboxQueue(userInitiated = false) {
  try {
    const res = await fetch('/api/jukebox/next', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: state.jukebox.currentRoomCode,
        host_token: state.jukebox.hostToken
      })
    });
    if (!res.ok) {
      if (userInitiated) {
        showToastNotification('No tracks waiting in party queue!');
      }
      return false;
    }
    const data = await res.json();
    if (data.track) {
      const t = data.track;
      const trackObj = {
        id: t.track_id || t.id,
        title: t.title,
        artist: t.artist,
        thumbnail: t.thumbnail || '',
        duration_formatted: t.duration || '3:00'
      };
      playTrack(trackObj);
      showToastNotification(`Playing top voted: "${t.title}"`);
      await fetchJukeboxRoom();
      return true;
    }
    return false;
  } catch (err) {
    if (userInitiated) showToastNotification('Failed to advance party queue');
    return false;
  }
}

// ============================================================================
// EXPIRABLE PUBLIC SHARE LINK CONTROLLER
// ============================================================================
function initShareLinkUI() {
  const modal = $('share-link-modal');
  const backdrop = $('share-link-backdrop');
  const btnClose = $('btn-close-share-link');
  const btnCancel = $('btn-share-link-cancel');
  const btnGenerate = $('btn-generate-share-link');
  const btnCopy = $('btn-copy-share-url');
  const inputResult = $('share-result-url');
  const containerResult = $('share-result-container');

  // Duration pills
  document.querySelectorAll('.share-duration-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.share-duration-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.shareModal.selectedHours = parseInt(pill.dataset.hours, 10) || 24;
    });
  });

  btnClose?.addEventListener('click', closeShareLinkModal);
  btnCancel?.addEventListener('click', closeShareLinkModal);
  backdrop?.addEventListener('click', closeShareLinkModal);

  btnGenerate?.addEventListener('click', async () => {
    if (!state.currentTrack) {
      showToastNotification('Play a track first to generate a share link');
      return;
    }
    const allowDl = $('chk-share-allow-download')?.checked !== false;
    try {
      btnGenerate.textContent = 'Minting...';
      const res = await fetch('/api/share/mint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: state.currentTrack.id,
          track_id: state.currentTrack.id,
          title: state.currentTrack.title,
          artist: state.currentTrack.artist,
          duration: state.currentTrack.duration_formatted || state.currentTrack.duration || '3:30',
          duration_hours: state.shareModal.selectedHours || 24,
          allow_download: allowDl
        })
      });
      if (!res.ok) throw new Error('Minting failed');
      const data = await res.json();
      const shareUrl = `${window.location.origin}/#share=${data.token}`;
      if (inputResult) inputResult.value = shareUrl;
      containerResult?.classList.remove('hidden');
      showToastNotification(`Expirable share link minted (${state.shareModal.selectedHours}h horizon)`);
    } catch (err) {
      showToastNotification('Failed to generate expirable share link');
    } finally {
      btnGenerate.textContent = 'Generate Share Link';
    }
  });

  btnCopy?.addEventListener('click', async () => {
    if (!inputResult || !inputResult.value) return;
    try {
      await navigator.clipboard.writeText(inputResult.value);
      showToastNotification('Share link copied to clipboard!');
    } catch (err) {
      inputResult.select();
      document.execCommand('copy');
      showToastNotification('Share link copied!');
    }
  });
}

function openShareLinkModal() {
  const modal = $('share-link-modal');
  if (!modal) return;
  if (!state.currentTrack) {
    showToastNotification('Select and play a track to share');
    return;
  }
  const previewTitle = $('share-preview-title');
  const previewArtist = $('share-preview-artist');
  if (previewTitle) previewTitle.textContent = state.currentTrack.title;
  if (previewArtist) previewArtist.textContent = state.currentTrack.artist;

  const resultContainer = $('share-result-container');
  if (resultContainer) resultContainer.classList.add('hidden');

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeShareLinkModal() {
  const modal = $('share-link-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  document.body.style.overflow = '';
}

// ============================================================================
// URL HASH ROUTING CONTROLLER (#party=CODE, #share=TOKEN)
// ============================================================================
async function handleUrlRouting() {
  const hash = window.location.hash;
  if (!hash) return;

  // 1. Party Room URL: #party=CODE
  if (hash.startsWith('#party=')) {
    const code = hash.replace('#party=', '').trim().toUpperCase();
    if (code) {
      state.jukebox.currentRoomCode = code;
      openJukeboxModal('guest');
      showToastNotification(`Joined Party Room: ${code}`);
    }
    return;
  }

  // 2. Expirable Public Share Link: #share=TOKEN
  if (hash.startsWith('#share=')) {
    const token = hash.replace('#share=', '').trim();
    if (!token) return;
    try {
      showToastNotification('Verifying expirable share link signature...');
      const res = await fetch(`/api/share/resolve?token=${encodeURIComponent(token)}`);
      if (res.status === 410) {
        showToastNotification('This shared song link has expired.');
        return;
      }
      if (res.status === 403 || !res.ok) {
        showToastNotification('Invalid or corrupted share link.');
        return;
      }
      const data = await res.json();
      const trackId = data?.item_id || data?.track?.id;
      if (data && trackId) {
        const trk = {
          id: trackId,
          title: data.title || data?.track?.title || 'Shared Track',
          artist: data.artist || data?.track?.artist || 'Unknown Artist',
          duration_formatted: data.duration || data?.track?.duration || '3:30',
          thumbnail: `https://i.ytimg.com/vi/${trackId}/hqdefault.jpg`,
          allowDownload: data.allow_download !== false
        };
        playTrack(trk);
        const hoursLeft = data.hours_remaining || Math.round((data.seconds_remaining || 0) / 3600);
        showToastNotification(`Streaming shared track (${hoursLeft}h validity remaining)`);
      }
    } catch (err) {
      showToastNotification('Error resolving shared link');
    }
  }
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
