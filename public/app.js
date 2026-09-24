/**
 * SongBuddy Studio — Premium 3-Column Workstation ("Groovvy" UI Engine)
 * Client-side State Manager, Audio Driver & Interactive Player
 */

// ============================================================================
// State Definition
// ============================================================================
const state = {
  theme: localStorage.getItem('songbuddy_theme') || 'neumorphic',
  currentTrack: null,
  isPlaying: false,
  queue: [],
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
  searchDebounceTimer: null,
  currentHeroIndex: 0,
  user: JSON.parse(localStorage.getItem('songbuddy_user') || 'null')
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
  } else if (event.data === 2) {
    state.isPlaying = false;
    updatePlayPauseIcons(false);
    stopYTProgressTracker();
  } else if (event.data === 0) {
    stopYTProgressTracker();
    if (state.isRepeat) {
      if (ytPlayer && typeof ytPlayer.seekTo === 'function') {
        ytPlayer.seekTo(0, true);
        ytPlayer.playVideo();
      }
    } else {
      playNextTrack();
    }
  }
}

function onYTPlayerError(e) {
  console.warn('[YouTube Player Error, falling back to direct stream]:', e);
  isYTActive = false;
  if (state.currentTrack) {
    audio.src = `/api/stream?id=${encodeURIComponent(state.currentTrack.id)}`;
    audio.load();
    audio.play().then(() => updatePlayPauseIcons(true)).catch(console.warn);
  }
}

function updateProgressUI(cur, dur) {
  if ($('scrub-current-time')) $('scrub-current-time').textContent = formatTime(cur);
  if (!isNaN(dur) && dur > 0) {
    if ($('scrub-total-time')) $('scrub-total-time').textContent = formatTime(dur);
    const pct = (cur / dur) * 100;
    if ($('scrubber-played-bar')) $('scrubber-played-bar').style.width = `${pct}%`;
  }
  updateLyricsSync(cur);
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
  if (audio && audio.duration) {
    audio.currentTime = seconds;
  }
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
};

const SPOTIFY_USER = {
  id: 'usr_spotify_alex',
  name: 'Alex Rivera (Spotify)',
  email: 'alex.rivera@spotify.com',
  avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80',
  plan: 'Spotify Premium Hi-Fi'
};

const GOOGLE_USER = {
  id: 'usr_google_dave',
  name: 'Dave Cooper (Google)',
  email: 'dave.cooper@gmail.com',
  avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80',
  plan: 'Google Hi-Fi Member'
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
    if ($('user-name')) $('user-name').textContent = user.name;
    if ($('user-avatar')) $('user-avatar').src = user.avatar;
    if ($('dropdown-user-name')) $('dropdown-user-name').textContent = user.name;
    if ($('dropdown-user-email')) $('dropdown-user-email').textContent = user.email;
    if ($('dropdown-avatar')) $('dropdown-avatar').src = user.avatar;
  } else {
    if ($('user-name')) $('user-name').textContent = 'Guest';
    if ($('user-avatar')) $('user-avatar').src = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80';
    if ($('dropdown-user-name')) $('dropdown-user-name').textContent = 'Guest Listener';
    if ($('dropdown-user-email')) $('dropdown-user-email').textContent = 'Click to sign in';
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
  showToastNotification(`Welcome back, ${userData.name}! 🎵`);
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
  const savedTheme = localStorage.getItem('songbuddy_theme') || 'neumorphic';
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
    showToastNotification(themeName === 'neumorphic' ? '🌿 Neumorphic Sage Theme Activated' : '🌑 Obsidian Dark Theme Activated');
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

  // Load live trending tracks from server
  await loadTrendingTracks();
  renderLikedTracks();

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
    <img src="${thumb}" alt="${track.title}" class="chart-thumb" loading="lazy" onerror="if(this.src.includes('hq720.jpg')){this.src=this.src.replace('hq720.jpg','hqdefault.jpg');}else{this.onerror=null;this.src=generateFallbackCover('${escapeHTML(track.title)}','${escapeHTML(track.artist)}');}">
    <div class="chart-info">
      <span class="chart-title">${escapeHTML(track.title)}</span>
      <span class="chart-artist">${escapeHTML(track.artist)}</span>
    </div>
    <span class="chart-time">${duration}</span>
    <button class="chart-play-icon" title="Play">
      <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
    </button>
  `;

  row.addEventListener('click', () => {
    playTrack(track);
  });

  return row;
}

// ============================================================================
// Audio Engine & Playback
// ============================================================================
async function playTrack(track, options = { startRadio: true }) {
  if (!track || !track.id) return;

  state.currentTrack = track;
  state.isPlaying = true;

  // Add to history
  if (!state.history.some(t => t.id === track.id)) {
    state.history.unshift(track);
  }

  updatePlayerUI(track);
  updateMediaSession(track);

  // Primary: Use YouTube Official Player for 100% genuine song playback (zero bot blocks / zero test sounds)
  if (track.id && (!track.streamUrl || track.id.length === 11)) {
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
      const streamUrl = `/api/stream?id=${encodeURIComponent(track.id)}`;
      audio.src = streamUrl;
      audio.load();
      audio.play().then(() => updatePlayPauseIcons(true)).catch(console.warn);
    }
  } else {
    isYTActive = false;
    stopYTProgressTracker();
    if (ytPlayer && typeof ytPlayer.pauseVideo === 'function') ytPlayer.pauseVideo();
    const streamUrl = track.streamUrl || `/api/stream?id=${encodeURIComponent(track.id)}`;
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

  // Fetch automix recommendations in the background
  if (options.startRadio) {
    loadRadioQueue(track.id);
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

  // Animate mini equalizer bars when playing
  const eqChip = $('chip-equalizer');
  if (eqChip) {
    eqChip.classList.toggle('playing', !!isPlaying);
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

  // Fallback to native audio
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

function playNextTrack() {
  if (state.queue.length > 0) {
    const next = state.isShuffle
      ? state.queue.splice(Math.floor(Math.random() * state.queue.length), 1)[0]
      : state.queue.shift();
    playTrack(next, { startRadio: false });
  } else if (state.featuredTracks.length > 0) {
    const currentIdx = state.featuredTracks.findIndex(t => t.id === state.currentTrack?.id);
    const nextIdx = (currentIdx + 1) % state.featuredTracks.length;
    playTrack(state.featuredTracks[nextIdx]);
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
// Radio & Automix
// ============================================================================
async function loadRadioQueue(seedId) {
  try {
    const res = await fetch(`/api/radio?id=${encodeURIComponent(seedId)}`);
    if (!res.ok) return;
    const tracks = await res.json();
    state.queue = tracks;

    const list = $('radio-tracks-list');
    if (list) {
      list.innerHTML = '';
      tracks.forEach((track, idx) => {
        const row = createTrackRow(track, idx + 1);
        list.appendChild(row);
      });
    }

    const radioHeading = $('radio-seed-heading');
    if (radioHeading && state.currentTrack) {
      radioHeading.textContent = `Automix: ${state.currentTrack.title}`;
    }
  } catch (err) {
    console.warn('[Automix error]:', err);
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

  if ($('lyrics-track-title')) $('lyrics-track-title').textContent = track.title;
  if ($('lyrics-track-artist')) $('lyrics-track-artist').textContent = track.artist;
  const wrapper = $('lyrics-lines-wrapper');

  const cleanTitle = cleanTitleForLyrics(track.title);
  const cleanArtist = cleanTitleForLyrics(track.artist);
  const cacheKey = `${cleanTitle.toLowerCase()}|||${cleanArtist.toLowerCase()}`;

  // 1. Instant Cache Hit (0ms)
  if (clientLyricsCache.has(cacheKey)) {
    const cachedData = clientLyricsCache.get(cacheKey);
    if (cachedData.syncedLyrics) {
      state.lyrics.synced = parseLrc(cachedData.syncedLyrics);
      renderSyncedLyrics();
    } else if (cachedData.plainLyrics) {
      state.lyrics.plain = cachedData.plainLyrics;
      renderPlainLyrics();
    }
    return;
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

  if ($('mini-lyrics-current')) $('mini-lyrics-current').textContent = 'Fetching synchronized lyrics...';
  if ($('mini-lyrics-next')) $('mini-lyrics-next').textContent = '♫ Direct Audio Opus Stream';

  // 3. Fast Server Call without strict duration constraint
  try {
    const res = await fetch(`/api/lyrics?title=${encodeURIComponent(cleanTitle)}&artist=${encodeURIComponent(cleanArtist)}`);
    if (!res.ok) throw new Error('Lyrics not found');
    const data = await res.json();
    clientLyricsCache.set(cacheKey, data);

    // Only render if this track is still the active one
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
        if ($('mini-lyrics-next')) $('mini-lyrics-next').textContent = '♫ Direct Audio Opus Stream';
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
      miniNext.textContent = nextLine ? `"${nextLine.text}"` : '♫ Direct Audio Opus Stream';
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
        }
      });
    }
  }
}

// ============================================================================
// Search Engine
// ============================================================================
function handleSearch(query) {
  if (!query || !query.trim()) {
    switchView('home');
    return;
  }

  switchView('search');
  const loading = $('search-loading');
  const resultsList = $('search-results-list');

  if (loading) loading.classList.remove('hidden');
  if (resultsList) resultsList.innerHTML = '';

  clearTimeout(state.searchDebounceTimer);
  state.searchDebounceTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      if (loading) loading.classList.add('hidden');
      if (!res.ok) throw new Error('Search failed');
      const tracks = await res.json();
      renderSearchResults(tracks);
    } catch (err) {
      if (loading) loading.classList.add('hidden');
      if (resultsList) resultsList.innerHTML = `<p style="color:var(--text-muted); padding:20px;">No tracks found.</p>`;
    }
  }, 350);
}

function renderSearchResults(tracks) {
  const container = $('search-results-list');
  if (!container) return;
  container.innerHTML = '';

  if (!tracks.length) {
    container.innerHTML = `<p style="color:var(--text-muted); padding:20px;">No matching tracks found.</p>`;
    return;
  }

  tracks.forEach((track, index) => {
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
function switchView(viewName) {
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

  // Update active navigation item
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.dataset.view === viewName) {
      item.classList.add('active');
    } else if (item.dataset.view) {
      item.classList.remove('active');
    }
  });

  // Sync floating dock active status
  if (viewName === 'home') {
    updateDockActive('dock-btn-home');
  } else {
    updateDockActive('dock-btn-music');
  }
}

// ============================================================================
// Liked Songs Management
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
  if (display) display.textContent = `${state.likedTracks.length} songs saved`;
  const list = $('liked-tracks-list');
  if (!list) return;
  list.innerHTML = '';

  state.likedTracks.forEach((track, index) => {
    const row = createTrackRow(track, index + 1);
    list.appendChild(row);
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
        <stop offset="0%" stop-color="#3f56f6"/>
        <stop offset="100%" stop-color="#14151c"/>
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

function shiftAmbientAura(seed) {
  const glow = $('ambient-glow');
  if (!glow) return;
  const hues = [
    'rgba(63, 86, 246, 0.14)',
    'rgba(140, 50, 220, 0.12)',
    'rgba(29, 185, 84, 0.12)',
    'rgba(240, 70, 110, 0.12)'
  ];
  const hash = seed.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const chosenHue = hues[hash % hues.length];
  glow.style.background = `radial-gradient(circle, ${chosenHue} 0%, rgba(20, 22, 30, 0.05) 50%, transparent 70%)`;
}

// ============================================================================
// MediaSession Integration
// ============================================================================
function setupMediaSession() {
  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', () => togglePlayPause());
    navigator.mediaSession.setActionHandler('pause', () => togglePlayPause());
    navigator.mediaSession.setActionHandler('previoustrack', () => playPrevTrack());
    navigator.mediaSession.setActionHandler('nexttrack', () => playNextTrack());
  }
}

function updateMediaSession(track) {
  if ('mediaSession' in navigator && track) {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: track.album || 'SongBuddy',
      artwork: [{ src: track.thumbnail || '', sizes: '512x512', type: 'image/jpeg' }]
    });
  }
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

  audio.addEventListener('ended', () => {
    if (!isYTActive) {
      if (state.isRepeat) {
        audio.currentTime = 0;
        audio.play();
      } else {
        playNextTrack();
      }
    }
  });

  audio.addEventListener('play', () => {
    if (!isYTActive) updatePlayPauseIcons(true);
  });
  audio.addEventListener('pause', () => {
    if (!isYTActive) updatePlayPauseIcons(false);
  });
}

function setupEventListeners() {
  // Navigation Links
  $('nav-explore')?.addEventListener('click', () => switchView('home'));
  $('nav-radio')?.addEventListener('click', () => switchView('radio'));
  $('nav-favourites')?.addEventListener('click', () => switchView('library'));
  $('nav-recent')?.addEventListener('click', () => switchView('library'));
  $('brand-logo')?.addEventListener('click', () => switchView('home'));

  // Playlist Items
  document.querySelectorAll('.playlist-item').forEach(item => {
    item.addEventListener('click', () => {
      const q = item.dataset.query;
      if (q) {
        const input = $('search-input');
        if (input) input.value = q;
        handleSearch(q);
      }
    });
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

  document.querySelectorAll('.h-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      const idx = parseInt(dot.dataset.index, 10);
      updateHeroSlide(idx);
    });
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

  // Search Input
  const searchInput = $('search-input');
  const searchClearBtn = $('search-clear-btn');

  searchInput?.addEventListener('input', (e) => {
    const val = e.target.value;
    searchClearBtn?.classList.toggle('hidden', !val);
    handleSearch(val);
  });

  searchClearBtn?.addEventListener('click', () => {
    if (searchInput) searchInput.value = '';
    searchClearBtn?.classList.add('hidden');
    switchView('home');
  });

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      searchInput?.focus();
      searchInput?.select();
    } else if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      togglePlayPause();
    }
  });

  // Player Controls
  $('btn-ctrl-play')?.addEventListener('click', togglePlayPause);
  $('btn-ctrl-next')?.addEventListener('click', playNextTrack);
  $('btn-ctrl-prev')?.addEventListener('click', playPrevTrack);

  $('btn-ctrl-shuffle')?.addEventListener('click', () => {
    state.isShuffle = !state.isShuffle;
    $('btn-ctrl-shuffle')?.classList.toggle('active', state.isShuffle);
  });

  $('btn-ctrl-repeat')?.addEventListener('click', () => {
    state.isRepeat = !state.isRepeat;
    $('btn-ctrl-repeat')?.classList.toggle('active', state.isRepeat);
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

  // Synchronized Lyrics Overlay
  const overlay = $('lyrics-overlay');
  function openLyrics() {
    overlay?.classList.remove('hidden');
    state.lyrics.isOpen = true;
    updateDockActive('dock-btn-music');
  }
  function closeLyrics() {
    overlay?.classList.add('hidden');
    state.lyrics.isOpen = false;
    if (state.activeView === 'home') {
      updateDockActive('dock-btn-home');
    } else {
      updateDockActive('dock-btn-music');
    }
  }

  // Theme Toggle Button
  $('btn-theme-toggle')?.addEventListener('click', toggleTheme);

  // Neumorphic Chips & Actions
  $('chip-lyrics')?.addEventListener('click', openLyrics);
  $('chip-equalizer')?.addEventListener('click', () => togglePlayPause());
  $('btn-neu-queue')?.addEventListener('click', () => switchView('radio'));

  // Neumorphic Share Button
  $('btn-neu-share')?.addEventListener('click', async () => {
    if (!state.currentTrack) {
      showToastNotification('Select a track to share');
      return;
    }
    const shareData = {
      title: `SongBuddy — ${state.currentTrack.title}`,
      text: `Listening to ${state.currentTrack.title} by ${state.currentTrack.artist} on SongBuddy Studio`,
      url: window.location.href
    };
    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        // User cancelled share
      }
    } else if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(`${shareData.text} • ${shareData.url}`);
        showToastNotification('Track link copied to clipboard! 📋');
      } catch (e) {
        showToastNotification(`Shared: ${state.currentTrack.title}`);
      }
    } else {
      showToastNotification(`Shared: ${state.currentTrack.title}`);
    }
  });

  // Neumorphic Heart Button
  $('btn-neu-heart')?.addEventListener('click', () => {
    if (state.currentTrack) {
      toggleLike(state.currentTrack);
    }
  });

  // Floating Bottom Clay Dock
  // 1. Music / Now Playing & Lyrics Button
  $('dock-btn-music')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    updateDockActive('dock-btn-music');
    if (state.lyrics.isOpen) {
      closeLyrics();
    } else {
      if (!state.currentTrack) {
        playTrack(HERO_SLIDES[0]);
      }
      openLyrics();
      showToastNotification(`Now Playing: ${state.currentTrack ? state.currentTrack.title : 'Lyrics & Audio'} 🎵`);
    }
  });

  // 2. Home / Explore Feed Button
  $('dock-btn-home')?.addEventListener('click', () => {
    toggleDockUserPopover(true);
    if (state.lyrics.isOpen) {
      closeLyrics();
    }
    switchView('home');
    updateDockActive('dock-btn-home');
    const feed = $('main-feed');
    if (feed) feed.scrollTo({ top: 0, behavior: 'smooth' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToastNotification('Exploring Home Feed 🏠');
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
    }
  });

  $('btn-menu-liked')?.addEventListener('click', () => {
    closeUserDropdown();
    switchView('library');
  });
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
