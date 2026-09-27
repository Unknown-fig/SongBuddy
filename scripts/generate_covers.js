const fs = require('fs');
const path = require('path');

const outDir = path.join(__dirname, '..', 'public', 'assets', 'spotify_covers');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Helper to create Spotify logo icon
const spotifyLogo = `
  <g transform="translate(18, 16) scale(0.65)">
    <circle cx="15" cy="15" r="15" fill="#1DB954"/>
    <path d="M21.8 11.2c-4.2-2.5-11.1-2.7-15.1-1.5-.6.2-1.3-.1-1.5-.8-.2-.6.1-1.3.8-1.5 4.6-1.4 12.3-1.1 17.1 1.7.6.3.8 1.1.4 1.7-.2.5-1 .7-1.7.4zm-.2 3.8c-.3.5-.9.7-1.4.3-3.5-2.1-8.8-2.8-12.9-1.5-.5.2-1.1-.1-1.3-.7-.2-.5.1-1.1.7-1.3 4.7-1.4 10.6-.7 14.6 1.8.5.3.7.9.3 1.4zm-1.6 3.8c-.3.4-.8.5-1.2.2-3.1-1.9-6.9-2.3-11.4-1.3-.4.1-.9-.2-1-.6-.1-.4.2-.9.6-1 5-1.1 9.3-.7 12.8 1.5.4.2.5.8.2 1.2z" fill="#000"/>
  </g>
`;

function createDailyMix(num, artistSilhouetteSvg, bgGrad, badgeLeftColor, badgeRightColor, badgeRightText) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="100%">
      ${bgGrad}
    </linearGradient>
    <linearGradient id="overlay" x1="0" y1="0" x2="0" y2="100%">
      <stop offset="0%" stop-color="#000" stop-opacity="0.1"/>
      <stop offset="60%" stop-color="#000" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.85"/>
    </linearGradient>
  </defs>
  <rect width="300" height="300" fill="url(#bg)"/>
  ${artistSilhouetteSvg}
  <rect width="300" height="300" fill="url(#overlay)"/>
  ${spotifyLogo}

  <!-- Split Banner at Bottom -->
  <g transform="translate(18, 230)">
    <!-- Left badge: Daily Mix -->
    <rect x="0" y="0" width="180" height="48" rx="4" fill="${badgeLeftColor}"/>
    <text x="14" y="32" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="24" font-weight="900" fill="#ffffff" letter-spacing="-0.5">Daily Mix</text>
    
    <!-- Right badge: Number -->
    <rect x="186" y="0" width="78" height="48" rx="4" fill="${badgeRightColor}"/>
    <text x="225" y="34" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="28" font-weight="900" fill="#000000" text-anchor="middle">${badgeRightText}</text>
  </g>
</svg>`;
}

// 1. Daily Mix 1
const dm1 = createDailyMix(
  '01',
  `
  <g opacity="0.95">
    <!-- Teal stage backlight -->
    <circle cx="150" cy="110" r="100" fill="#14b8a6" opacity="0.3"/>
    <!-- Head & Sunglasses -->
    <path d="M125 70 C125 50, 175 50, 175 70 C175 88, 170 105, 150 115 C130 105, 125 88, 125 70 Z" fill="#f87171"/>
    <!-- Hair -->
    <path d="M120 65 C122 42, 178 42, 180 65 C175 52, 125 52, 120 65 Z" fill="#18181b"/>
    <!-- Sunglasses -->
    <rect x="132" y="72" width="16" height="9" rx="2" fill="#09090b"/>
    <rect x="152" y="72" width="16" height="9" rx="2" fill="#09090b"/>
    <line x1="148" y1="76" x2="152" y2="76" stroke="#09090b" stroke-width="2"/>
    <!-- Red Jacket and White Shirt -->
    <path d="M90 220 L120 135 L140 145 L150 170 L160 145 L180 135 L210 220 Z" fill="#ef4444"/>
    <path d="M140 145 L150 170 L160 145 L150 120 Z" fill="#ffffff"/>
  </g>
  `,
  `<stop offset="0%" stop-color="#0f766e"/><stop offset="100%" stop-color="#134e48"/>`,
  '#0d9488',
  '#2dd4bf',
  '01'
);

// 2. MTV Hustle 5
const hustle5 = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <linearGradient id="bgHustle" x1="0" y1="0" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#180d2b"/>
      <stop offset="50%" stop-color="#3b0764"/>
      <stop offset="100%" stop-color="#09090b"/>
    </linearGradient>
    <linearGradient id="neonText" x1="0" y1="0" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f43f5e"/>
      <stop offset="50%" stop-color="#eab308"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>
  <rect width="300" height="300" fill="url(#bgHustle)"/>
  
  <!-- Neon Graffiti Splatters -->
  <path d="M30 60 Q 70 20 120 50 T 220 30 T 280 80" stroke="#ec4899" stroke-width="8" fill="none" opacity="0.4"/>
  <path d="M10 210 Q 80 180 140 220 T 260 190" stroke="#06b6d4" stroke-width="12" fill="none" opacity="0.35"/>
  <circle cx="230" cy="90" r="45" fill="#facc15" opacity="0.25" filter="blur(10px)"/>
  <circle cx="70" cy="180" r="55" fill="#ec4899" opacity="0.25" filter="blur(10px)"/>

  <!-- MTV Block Logo -->
  <rect x="30" y="70" width="60" height="48" rx="6" fill="#000" stroke="#facc15" stroke-width="3"/>
  <text x="60" y="104" font-family="Impact, Arial Black, sans-serif" font-size="28" font-weight="900" fill="#facc15" text-anchor="middle">MTV</text>

  <!-- Big Typography HUSTLE 5 -->
  <text x="30" y="155" font-family="Impact, Arial Black, sans-serif" font-size="44" font-style="italic" fill="url(#neonText)" letter-spacing="2">HUSTLE 5</text>
  <rect x="30" y="172" width="240" height="6" fill="#ec4899" rx="3"/>
  <text x="30" y="210" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" font-weight="900" fill="#ffffff" letter-spacing="1">~ ALL SONGS ~</text>
  <text x="30" y="235" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14" font-weight="700" fill="#a1a1aa" letter-spacing="2">ALL EPISODES</text>

  <rect x="30" y="255" width="90" height="24" rx="12" fill="#f43f5e"/>
  <text x="75" y="271" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="11" font-weight="800" fill="#fff" text-anchor="middle">RAP HITS</text>
</svg>`;

// 3. Seedhe Maut
const seedheMaut = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <rect width="300" height="300" fill="#0d0d0e"/>
  <!-- Architectural Archway -->
  <path d="M50 280 L50 140 A100 100 0 0 1 250 140 L250 280 Z" fill="#1c1c1f" stroke="#3f3f46" stroke-width="2"/>
  <path d="M75 280 L75 150 A75 75 0 0 1 225 150 L225 280 Z" fill="#27272a" stroke="#52525b" stroke-width="1.5"/>
  <path d="M100 280 L100 160 A50 50 0 0 1 200 160 L200 280 Z" fill="#3f3f46"/>

  <!-- Silhouettes of Duo Calm & Encore -->
  <path d="M110 280 L115 200 Q125 190 135 200 L140 280 Z" fill="#000"/>
  <circle cx="125" cy="185" r="10" fill="#000"/>
  
  <path d="M160 280 L165 195 Q175 185 185 195 L190 280 Z" fill="#000"/>
  <circle cx="175" cy="180" r="10" fill="#000"/>

  <!-- Minimalist Title -->
  <rect x="25" y="35" width="250" height="45" fill="rgba(0,0,0,0.6)" rx="4"/>
  <text x="150" y="65" font-family="'Courier New', Courier, monospace, sans-serif" font-size="22" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="4">SEEDHE MAUT</text>
  <text x="150" y="260" font-family="sans-serif" font-size="11" font-weight="700" fill="#a1a1aa" text-anchor="middle" letter-spacing="3">TBSM • LUNCH BREAK</text>
</svg>`;

// 4. Discover Weekly
const discoverWeekly = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <rect width="300" height="300" fill="#121212"/>
  <defs>
    <linearGradient id="dwGrad" x1="0" y1="0" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ec4899"/>
      <stop offset="40%" stop-color="#a855f7"/>
      <stop offset="70%" stop-color="#eab308"/>
      <stop offset="100%" stop-color="#22c55e"/>
    </linearGradient>
  </defs>

  <!-- Left stylized block grid -->
  <g transform="translate(25, 30)">
    <rect x="0" y="0" width="100" height="240" fill="#000" rx="4"/>
    <rect x="0" y="0" width="100" height="60" fill="#ec4899"/>
    <text x="50" y="42" font-family="Impact, Arial Black, sans-serif" font-size="28" fill="#fff" text-anchor="middle">DIS</text>
    
    <rect x="0" y="60" width="100" height="60" fill="#eab308"/>
    <text x="50" y="102" font-family="Impact, Arial Black, sans-serif" font-size="28" fill="#000" text-anchor="middle">COV</text>
    
    <rect x="0" y="120" width="100" height="60" fill="#a855f7"/>
    <text x="50" y="162" font-family="Impact, Arial Black, sans-serif" font-size="28" fill="#fff" text-anchor="middle">ER</text>
    
    <rect x="0" y="180" width="100" height="60" fill="#22c55e"/>
    <text x="50" y="222" font-family="Impact, Arial Black, sans-serif" font-size="24" fill="#000" text-anchor="middle">WKLY</text>
  </g>

  <!-- Right text info -->
  <text x="140" y="90" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="22" font-weight="900" fill="#ffffff" letter-spacing="-0.5">Discover</text>
  <text x="140" y="118" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="22" font-weight="900" fill="#ffffff" letter-spacing="-0.5">Weekly</text>

  <text x="140" y="160" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" font-weight="500" fill="#a1a1aa">Your weekly</text>
  <text x="140" y="180" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" font-weight="500" fill="#a1a1aa">mixtape of</text>
  <text x="140" y="200" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" font-weight="500" fill="#a1a1aa">fresh music.</text>

  <rect x="140" y="230" width="120" height="30" rx="15" fill="#22c55e"/>
  <text x="200" y="250" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" font-weight="800" fill="#000" text-anchor="middle">UPDATED MON</text>
</svg>`;

// 5. Dhurandhar 2 All Song
const dhurandhar = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <radialGradient id="fireGrad" cx="50%" cy="50%" r="60%">
      <stop offset="0%" stop-color="#ffedd5"/>
      <stop offset="25%" stop-color="#f97316"/>
      <stop offset="60%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#0a0a0a"/>
    </radialGradient>
  </defs>
  <rect width="300" height="300" fill="url(#fireGrad)"/>

  <!-- Sparks and Embers -->
  <circle cx="80" cy="110" r="3" fill="#fef08a"/>
  <circle cx="210" cy="80" r="2.5" fill="#fed7aa"/>
  <circle cx="160" cy="50" r="4" fill="#fef08a"/>
  <circle cx="240" cy="160" r="2" fill="#fef08a"/>

  <!-- Dramatic Typography -->
  <text x="150" y="110" font-family="Impact, Arial Black, sans-serif" font-size="18" fill="#fde047" text-anchor="middle" letter-spacing="6">REVENGE</text>
  <text x="150" y="160" font-family="Impact, Arial Black, sans-serif" font-size="34" fill="#ffffff" text-anchor="middle" letter-spacing="2">DHURANDHAR</text>
  <text x="150" y="210" font-family="Impact, Arial Black, sans-serif" font-size="48" fill="#f97316" text-anchor="middle" letter-spacing="1">CHAPTER 2</text>
  <rect x="75" y="230" width="150" height="26" rx="4" fill="#000000" opacity="0.75"/>
  <text x="150" y="248" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="12" font-weight="900" fill="#ffffff" text-anchor="middle" letter-spacing="2">ALL SONGS OST</text>
</svg>`;

// 6. New Music Friday India
const nmfIndia = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <linearGradient id="nmfBg" x1="0" y1="0" x2="0" y2="100%">
      <stop offset="0%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="300" height="300" fill="url(#nmfBg)"/>
  
  <!-- Stylized Studio Portrait -->
  <circle cx="150" cy="120" r="65" fill="#fca5a5" opacity="0.9"/>
  <!-- Hair & Headphone -->
  <path d="M90 120 C90 60, 210 60, 210 120 C200 150, 100 150, 90 120 Z" fill="#18181b"/>
  <!-- Headphone arch -->
  <path d="M75 125 A75 75 0 0 1 225 125" stroke="#facc15" stroke-width="8" fill="none"/>
  <rect x="70" y="115" width="16" height="30" rx="6" fill="#facc15"/>
  <rect x="214" y="115" width="16" height="30" rx="6" fill="#facc15"/>

  <!-- NMF Yellow Signature Badge -->
  <g transform="translate(18, 220)">
    <rect x="0" y="0" width="180" height="52" fill="#facc15" rx="4"/>
    <text x="10" y="24" font-family="Impact, Arial Black, sans-serif" font-size="18" fill="#000000" letter-spacing="0.5">NEW MUSIC FRIDAY</text>
    <text x="10" y="44" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14" font-weight="900" fill="#000000" letter-spacing="3">INDIA</text>
  </g>
</svg>`;

// 7. Trending Now Punjabi
const trendingPunjabi = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <linearGradient id="pbBg" x1="0" y1="0" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
  </defs>
  <rect width="300" height="300" fill="url(#pbBg)"/>

  <!-- Swag artist silhouette -->
  <circle cx="150" cy="100" r="50" fill="#fdba74"/>
  <!-- Turban/Beanie & Sunglasses -->
  <path d="M100 95 C100 50, 200 50, 200 95 C190 70, 110 70, 100 95 Z" fill="#0284c7"/>
  <rect x="120" y="95" width="25" height="12" rx="3" fill="#0f172a"/>
  <rect x="155" y="95" width="25" height="12" rx="3" fill="#0f172a"/>
  <!-- Beard -->
  <path d="M120 120 C130 150, 170 150, 180 120 Z" fill="#18181b"/>
  <!-- Denim Jacket -->
  <path d="M70 230 L110 160 L190 160 L230 230 Z" fill="#0369a1"/>

  <!-- Neon Green Badge -->
  <g transform="translate(18, 225)">
    <rect x="0" y="0" width="220" height="48" rx="6" fill="#10b981"/>
    <text x="14" y="24" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="13" font-weight="800" fill="#000" letter-spacing="1">TRENDING NOW</text>
    <text x="14" y="42" font-family="Impact, Arial Black, sans-serif" font-size="20" fill="#000" letter-spacing="1">PUNJABI</text>
  </g>
</svg>`;

// 8. Daily Mix 2
const dm2 = createDailyMix(
  '02',
  `
  <g opacity="0.95">
    <circle cx="150" cy="110" r="90" fill="#f59e0b" opacity="0.3"/>
    <path d="M125 70 C125 50, 175 50, 175 70 C175 88, 170 105, 150 115 C130 105, 125 88, 125 70 Z" fill="#fca5a5"/>
    <path d="M120 65 C122 42, 178 42, 180 65 C175 52, 125 52, 120 65 Z" fill="#18181b"/>
    <path d="M80 230 L120 140 L180 140 L220 230 Z" fill="#b91c1c"/>
  </g>
  `,
  `<stop offset="0%" stop-color="#991b1b"/><stop offset="100%" stop-color="#450a0a"/>`,
  '#dc2626',
  '#facc15',
  '02'
);

// 9. Daily Mix 03 (Emiway Bantai)
const dm3 = createDailyMix(
  '03',
  `
  <g opacity="0.95">
    <!-- Moody Black & White Emiway Portrait -->
    <circle cx="150" cy="105" r="55" fill="#d4d4d8"/>
    <!-- Curls / Hair -->
    <path d="M95 105 C95 40, 205 40, 205 105 C185 60, 115 60, 95 105 Z" fill="#18181b"/>
    <!-- Sunglasses -->
    <rect x="118" y="98" width="28" height="15" rx="4" fill="#09090b"/>
    <rect x="154" y="98" width="28" height="15" rx="4" fill="#09090b"/>
    <!-- Beard -->
    <path d="M115 125 C125 155, 175 155, 185 125 Z" fill="#27272a"/>
    <!-- Black Leather Puffer Jacket -->
    <path d="M65 240 L105 160 L195 160 L235 240 Z" fill="#18181b"/>
  </g>
  `,
  `<stop offset="0%" stop-color="#27272a"/><stop offset="100%" stop-color="#09090b"/>`,
  '#dc2626',
  '#fb923c',
  '03'
);

// 10. Daily Mix 04 (Karan Aujla)
const dm4 = createDailyMix(
  '04',
  `
  <g opacity="0.95">
    <!-- Dark Side Profile Karan Aujla -->
    <path d="M110 60 C130 45, 185 55, 180 110 C175 135, 140 145, 120 140 Z" fill="#e4e4e7"/>
    <!-- Fade Hair & Beard -->
    <path d="M115 65 C130 50, 180 50, 175 75 Z" fill="#09090b"/>
    <path d="M120 115 C135 145, 165 140, 170 120 Z" fill="#18181b"/>
    <!-- Black Coat -->
    <path d="M70 240 L115 165 L185 165 L230 240 Z" fill="#0f172a"/>
  </g>
  `,
  `<stop offset="0%" stop-color="#1e1b4b"/><stop offset="100%" stop-color="#09090b"/>`,
  '#db2777',
  '#f472b6',
  '04'
);

// 11. Daily Mix 05 (Yo Yo Honey Singh)
const dm5 = createDailyMix(
  '05',
  `
  <g opacity="0.95">
    <!-- Golden Aura Sunburst -->
    <circle cx="150" cy="110" r="95" fill="#facc15" opacity="0.45" filter="blur(15px)"/>
    <!-- Golden Blonde Hair & Shades -->
    <circle cx="150" cy="105" r="50" fill="#fde047"/>
    <!-- Platinum Hair -->
    <path d="M100 100 C105 45, 195 45, 200 100 C185 65, 115 65, 100 100 Z" fill="#fef08a"/>
    <rect x="120" y="98" width="26" height="14" rx="4" fill="#000"/>
    <rect x="154" y="98" width="26" height="14" rx="4" fill="#000"/>
    <!-- Gold Chain -->
    <path d="M125 170 Q150 205 175 170" stroke="#facc15" stroke-width="6" fill="none"/>
    <!-- Sleeveless / Tank -->
    <path d="M85 240 L115 160 L185 160 L215 240 Z" fill="#18181b"/>
  </g>
  `,
  `<stop offset="0%" stop-color="#854d0e"/><stop offset="100%" stop-color="#1c1917"/>`,
  '#65a30d',
  '#a3e635',
  '05'
);

// 12. Daily Mix 06 (Abdul Hannan / Pakistani Pop)
const dm6 = createDailyMix(
  '06',
  `
  <g opacity="0.95">
    <circle cx="150" cy="110" r="85" fill="#818cf8" opacity="0.3"/>
    <circle cx="150" cy="105" r="50" fill="#fed7aa"/>
    <path d="M105 105 C105 50, 195 50, 195 105 Z" fill="#18181b"/>
    <path d="M75 240 L115 165 L185 165 L225 240 Z" fill="#312e81"/>
  </g>
  `,
  `<stop offset="0%" stop-color="#4338ca"/><stop offset="100%" stop-color="#0f172a"/>`,
  '#7c3aed',
  '#c084fc',
  '06'
);

// Recents covers
function createRecentCover(title, artist, color1, color2, iconType) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <defs>
    <linearGradient id="rcGrad_${title.replace(/\s+/g, '')}" x1="0" y1="0" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${color1}"/>
      <stop offset="100%" stop-color="${color2}"/>
    </linearGradient>
  </defs>
  <rect width="300" height="300" fill="url(#rcGrad_${title.replace(/\s+/g, '')})" rx="8"/>
  <circle cx="150" cy="120" r="60" fill="rgba(255,255,255,0.12)"/>
  <circle cx="150" cy="120" r="30" fill="rgba(255,255,255,0.2)"/>
  <text x="24" y="230" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="20" font-weight="900" fill="#ffffff">${title}</text>
  <text x="24" y="260" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14" font-weight="600" fill="rgba(255,255,255,0.75)">${artist}</text>
</svg>`;
}

const rc1 = createRecentCover('Coke Studio 15', 'Season 15 Fusion', '#e11d48', '#881337', 'vinyl');
const rc2 = createRecentCover('Global Top 50', 'Daily Chart Hits', '#10b981', '#064e3b', 'chart');
const rc3 = createRecentCover('Lo-Fi Cafe', 'Rainy Chill Beats', '#f59e0b', '#78350f', 'coffee');
const rc4 = createRecentCover('Bollywood Retro', 'Kishore & RD Burman', '#8b5cf6', '#4c1d95', 'retro');
const rc5 = createRecentCover('Punjabi Wave', 'AP Dhillon & Diljit', '#06b6d4', '#164e63', 'wave');
const rc6 = createRecentCover('Synthwave 80s', 'Neon Night Drive', '#ec4899', '#581c87', 'synth');

const files = {
  'daily_mix_1.svg': dm1,
  'mtv_hustle_5.svg': hustle5,
  'seedhe_maut.svg': seedheMaut,
  'discover_weekly.svg': discoverWeekly,
  'dhurandhar_2.svg': dhurandhar,
  'new_music_friday.svg': nmfIndia,
  'trending_punjabi.svg': trendingPunjabi,
  'daily_mix_2.svg': dm2,
  'daily_mix_3.svg': dm3,
  'daily_mix_4.svg': dm4,
  'daily_mix_5.svg': dm5,
  'daily_mix_6.svg': dm6,
  'recent_1.svg': rc1,
  'recent_2.svg': rc2,
  'recent_3.svg': rc3,
  'recent_4.svg': rc4,
  'recent_5.svg': rc5,
  'recent_6.svg': rc6
};

for (const [name, content] of Object.entries(files)) {
  fs.writeFileSync(path.join(outDir, name), content.trim(), 'utf8');
}

console.log(`Generated ${Object.keys(files).length} Spotify covers successfully in ${outDir}`);
