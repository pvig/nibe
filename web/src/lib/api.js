// Couche API centralisée — tous les appels fetch vers server.py

export const fetchLive = () =>
  fetch('/api/live').then(r => r.json());

export const fetchHistory = (hours, maxPoints = 250) =>
  fetch(`/api/history?hours=${hours}&max_points=${maxPoints}`).then(r => r.json());

export const fetchActions = (limit = 50) =>
  fetch(`/api/actions?limit=${limit}`).then(r => r.json());

export const fetchConfig = () =>
  fetch('/api/config').then(r => r.json());

export const updateConfig = (configObj) =>
  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(configObj)
  }).then(r => r.json());

export const sendShutterCommand = (name, action) =>
  fetch('/api/shutter/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, action })
  }).then(r => r.json());

export const sendVmcCommand = (mode) =>
  fetch('/api/vmc/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode })
  }).then(r => r.json());

// Filtre les points à 0 isolés et interpole les valeurs nulles pour éviter les trous dans les graphiques
export function filterIsolatedZeros(arr, minValidNeighbor = 1) {
  // 1. Remplacer uniquement les undefined par null (les vrais zéros sont maintenant légitimes)
  let cleaned = arr.map((v) => (v === undefined ? null : v));

  let result = [...cleaned];
  for (let i = 0; i < result.length; i++) {
    if (result[i] === null) {
      let prevIdx = -1;
      for (let j = i - 1; j >= 0; j--) {
        if (cleaned[j] !== null) { prevIdx = j; break; }
      }
      let nextIdx = -1;
      for (let j = i + 1; j < cleaned.length; j++) {
        if (cleaned[j] !== null) { nextIdx = j; break; }
      }

      if (prevIdx !== -1 && nextIdx !== -1) {
        let fraction = (i - prevIdx) / (nextIdx - prevIdx);
        result[i] = cleaned[prevIdx] + fraction * (cleaned[nextIdx] - cleaned[prevIdx]);
      } else if (prevIdx !== -1) {
        result[i] = cleaned[prevIdx];
      } else if (nextIdx !== -1) {
        result[i] = cleaned[nextIdx];
      } else {
        result[i] = 0;
      }
    }
  }
  return result;
}

// Formate les labels de l'axe X selon la plage temporelle
export function formatLabels(history, hoursNum) {
  return history.map(item => {
    if (!item.datetime_iso) return '';
    const parts = item.datetime_iso.split(' ');
    const dateStr = parts[0] || '';
    const timeStr = parts[1] ? parts[1].substring(0, 5) : '';
    const dateParts = dateStr.split('-');
    const mm = dateParts[1] || '';
    const dd = dateParts[2] || '';
    return (hoursNum > 0 && hoursNum <= 24) ? timeStr : `${dd}/${mm} ${timeStr}`;
  });
}
