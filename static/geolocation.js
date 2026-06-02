let userMarker = null;
let watchId    = null;

const userIcon = L.divIcon({
  className: '',
  html: '<div style="width:16px;height:16px;background:#3b82f6;border:3px solid #fff;border-radius:50%;box-shadow:0 0 0 3px rgba(59,130,246,.35);"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8]
});

function updateUserLocation(position) {
  const { latitude, longitude, accuracy } = position.coords;
  if (userMarker) {
    userMarker.setLatLng([latitude, longitude]);
  } else {
    userMarker = L.marker([latitude, longitude], { icon: userIcon })
      .addTo(map)
      .bindPopup(`📍 ${window.i18n ? window.i18n.youAreHere : 'Ви тут'}<br><small style="color:#64748b">±${Math.round(accuracy)} м</small>`)
      .openPopup();
    map.setView([latitude, longitude], 14);
  }
}

function handleLocationError(error) {
  console.warn('Geo error:', error.code);
  hideBanner();
}

function showGeoBanner() {
  const b = document.getElementById('geoBanner');
  if (b) b.style.display = 'flex';
}

function hideBanner() {
  const b = document.getElementById('geoBanner');
  if (b) b.style.display = 'none';
}

function startTracking() {
  hideBanner();
  if (!navigator.geolocation) return;
  watchId = navigator.geolocation.watchPosition(
    updateUserLocation,
    handleLocationError,
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
  );
}

function denyTracking() {
  hideBanner();
  sessionStorage.setItem('geo_denied', '1');
}

document.addEventListener('DOMContentLoaded', () => {
  if (!navigator.geolocation) return;
  if (sessionStorage.getItem('geo_denied')) return;
  if (navigator.permissions) {
    navigator.permissions.query({ name: 'geolocation' }).then(result => {
      if (result.state === 'granted') startTracking();
      else if (result.state === 'prompt') showGeoBanner();
    });
  } else {
    showGeoBanner();
  }
});
