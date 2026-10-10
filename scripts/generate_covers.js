const fs = require('fs');
const path = require('path');
const https = require('https');

const outDir = path.join(__dirname, '..', 'public', 'assets', 'spotify_covers');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// 18 High-Res Authentic Music Covers (iTunes 600x600 & Spotify Official CDN)
const coverSources = {
  'daily_mix_1.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/ec/9a/1f/ec9a1fb9-dc98-cd4f-d4c9-01eed5e67b19/859778016276_cover.jpg/600x600bb.jpg',
    isDailyMix: true,
    num: '01',
    badgeColor: '#10b981',
    textColor: '#ffffff',
    sub: 'Diljit Dosanjh • AP Dhillon • Arijit Singh'
  },
  'mtv_hustle_5.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/04/b2/79/04b279ee-8fd8-0dd8-a50e-0e4cc54b187d/8903246794578_cover.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'seedhe_maut.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/60/51/e8/6051e86e-9c3e-3187-e629-546ced4cfab7/cover.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'discover_weekly.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/18/c3/ea/18c3eaae-229c-c529-634c-d6219e161ccb/5059805957458_cover.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'dhurandhar_2.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/fd/32/5b/fd325b02-ac02-22b0-71aa-1e0f87a2ed49/820233852487.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'new_music_friday.jpg': {
    url: 'https://i.scdn.co/image/ab67706f000000020408713c731caaf1f800615a',
    isDailyMix: false
  },
  'trending_punjabi.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/d3/08/bc/d308bc6a-20e1-6532-d933-35d1b429210e/5054197755538.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'daily_mix_2.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/1e/ff/32/1eff3216-190d-6fd9-8f68-acbba846e6ee/8903431956026_cover.jpg/600x600bb.jpg',
    isDailyMix: true,
    num: '02',
    badgeColor: '#f43f5e',
    textColor: '#ffffff',
    sub: 'Arijit Singh • Shreya Ghoshal • Jasleen'
  },
  'daily_mix_3.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/5d/1a/eb/5d1aeb19-f324-686b-ae15-849cee4b4dbd/cover.jpg/600x600bb.jpg',
    isDailyMix: true,
    num: '03',
    badgeColor: '#f59e0b',
    textColor: '#ffffff',
    sub: 'Emiway Bantai • Dino James • MC Stan'
  },
  'daily_mix_4.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/fc/bc/64/fcbc6417-8a88-7b5e-4490-8f53e537ffb0/859770181552_cover.jpg/600x600bb.jpg',
    isDailyMix: true,
    num: '04',
    badgeColor: '#a855f7',
    textColor: '#ffffff',
    sub: 'Karan Aujla • Sidhu Moose Wala'
  },
  'daily_mix_5.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/11/e3/9c/11e39c6d-0ac9-8728-cb9e-94197f645bfd/8903431012173_cover.jpg/600x600bb.jpg',
    isDailyMix: true,
    num: '05',
    badgeColor: '#06b6d4',
    textColor: '#ffffff',
    sub: 'Yo Yo Honey Singh • Badshah • Paradox'
  },
  'daily_mix_6.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/5d/8b/b8/5d8bb828-6871-0390-52b1-714a7ed0e38f/artwork.jpg/600x600bb.jpg',
    isDailyMix: true,
    num: '06',
    badgeColor: '#ec4899',
    textColor: '#ffffff',
    sub: 'Abdul Hannan • Hasan Raheem • Asim'
  },
  'recent_1.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/c5/6f/48/c56f48df-93e8-0231-8196-e387a821fa54/085365577756.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'recent_2.jpg': {
    url: 'https://charts-images.scdn.co/assets/locale_en/regional/daily/region_global_default.jpg',
    isDailyMix: false
  },
  'recent_3.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/9b/30/4f/9b304f6f-2ecb-6b27-a0f1-1435392ecc44/4550756509402_cover.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'recent_4.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music126/v4/a7/dc/0b/a7dc0bf3-aeeb-f56d-710e-bd874bcbb160/12UMGIM44705.rgb.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'recent_5.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/67/37/31/67373108-1018-da3f-7220-4515137e5e5e/859766525070_cover.jpg/600x600bb.jpg',
    isDailyMix: false
  },
  'recent_6.jpg': {
    url: 'https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/91/36/0d/91360db9-2c5a-6b60-ad0e-d1f229210246/artwork.jpg/600x600bb.jpg',
    isDailyMix: false
  }
};

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    if (fs.existsSync(dest) && fs.statSync(dest).size > 1000) {
      return resolve();
    }
    const file = fs.createWriteStream(dest);
    https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
      if (res.statusCode !== 200) {
        file.close();
        return reject(new Error(`Failed to download ${url}: status ${res.statusCode}`));
      }
      res.pipe(file);
      file.on('finish', () => {
        file.close(resolve);
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

// Generate high-resolution SVG with embedded base64 image & SongBuddy Studio branding
function createSvgForCover(b64, config) {
  if (config.isDailyMix) {
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600">
  <defs>
    <linearGradient id="overlayGrad" x1="0" y1="0" x2="0" y2="100%">
      <stop offset="0%" stop-color="#000000" stop-opacity="0.15"/>
      <stop offset="45%" stop-color="#000000" stop-opacity="0.3"/>
      <stop offset="78%" stop-color="#000000" stop-opacity="0.75"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0.95"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.5"/>
    </filter>
  </defs>
  <!-- Background High-Res Photograph -->
  <image href="data:image/jpeg;base64,${b64}" width="600" height="600" preserveAspectRatio="xMidYMid slice"/>
  <!-- Cinematic Contrast Gradient -->
  <rect width="600" height="600" fill="url(#overlayGrad)"/>
  
  <!-- SongBuddy Studio Emblem Top Left -->
  <g transform="translate(32, 28)" filter="url(#shadow)">
    <rect width="144" height="38" rx="19" fill="#0f172a" fill-opacity="0.88" stroke="rgba(255,255,255,0.22)" stroke-width="1.5"/>
    <circle cx="22" cy="19" r="6" fill="${config.badgeColor}"/>
    <text x="38" y="24" font-family="-apple-system, BlinkMacSystemFont, 'Plus Jakarta Sans', 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="800" fill="#ffffff" letter-spacing="0.5">SONGBUDDY</text>
  </g>

  <!-- Modern Station Pill Banner at Bottom -->
  <g transform="translate(32, 474)" filter="url(#shadow)">
    <!-- Left pill: Studio Mix -->
    <rect x="0" y="0" width="380" height="88" rx="16" fill="#0f172a" fill-opacity="0.92" stroke="rgba(255,255,255,0.12)" stroke-width="1.5"/>
    <text x="24" y="44" font-family="-apple-system, BlinkMacSystemFont, 'Plus Jakarta Sans', 'Segoe UI', Roboto, sans-serif" font-size="32" font-weight="800" fill="#ffffff" letter-spacing="-0.5">Studio Mix</text>
    <text x="24" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Plus Jakarta Sans', 'Segoe UI', Roboto, sans-serif" font-size="15" font-weight="500" fill="rgba(255,255,255,0.7)">Continuous Radio Flow</text>
    
    <!-- Right pill: Number -->
    <rect x="394" y="0" width="142" height="88" rx="16" fill="${config.badgeColor}"/>
    <text x="465" y="58" font-family="-apple-system, BlinkMacSystemFont, 'Plus Jakarta Sans', 'Segoe UI', Roboto, sans-serif" font-size="44" font-weight="900" fill="${config.textColor}" text-anchor="middle">${config.num}</text>
  </g>
</svg>`;
  }

  // Full-bleed album / playlist artwork
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600">
  <image href="data:image/jpeg;base64,${b64}" width="600" height="600" preserveAspectRatio="xMidYMid slice"/>
</svg>`;
}

async function main() {
  console.log('Generating premium, authentic music covers...');
  
  for (const [jpgName, config] of Object.entries(coverSources)) {
    const jpgPath = path.join(outDir, jpgName);
    const svgName = jpgName.replace('.jpg', '.svg');
    const svgPath = path.join(outDir, svgName);

    // Download if not already present
    if (!fs.existsSync(jpgPath) || fs.statSync(jpgPath).size < 1000) {
      console.log(`Downloading ${jpgName}...`);
      try {
        await downloadFile(config.url, jpgPath);
      } catch (err) {
        console.error(`Error downloading ${jpgName}:`, err.message);
      }
    }

    if (fs.existsSync(jpgPath)) {
      const imgBuffer = fs.readFileSync(jpgPath);
      const b64 = imgBuffer.toString('base64');
      const svgContent = createSvgForCover(b64, config);
      fs.writeFileSync(svgPath, svgContent, 'utf8');
      console.log(`Generated ${svgName} (${(svgContent.length / 1024).toFixed(1)} KB)`);
    }
  }

  console.log('\nAll 18 Spotify covers updated successfully with authentic artwork!');
}

main().catch(console.error);
