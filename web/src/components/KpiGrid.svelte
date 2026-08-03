<script>
  import { updateConfig } from '../lib/api.js';
  let { live = null, sun = null, config = {} } = $props();

  const fmt = (v, unit) => v != null ? `${v} ${unit}` : `-- ${unit}`;

  let sensitivity = $state(0);
  $effect(() => {
    if (config && config.solar_response_factor !== undefined) {
      sensitivity = config.solar_response_factor;
    }
  });

  async function onSensitivityChange(e) {
    const val = parseFloat(e.target.value);
    sensitivity = val;
    await updateConfig({ solar_response_factor: val });
  }
</script>

<div class="grid-kpi">
  <div class="card">
    <div class="card-header">
      <span class="card-title">Températures Ext / Int</span>
      <span class="card-icon">🌡️</span>
    </div>
    <div class="card-value">
      <span class="val-ext">{live ? fmt(live.t_ext, '°C') : '-- °C'}</span>
      <span class="val-int">{live ? fmt(live.t_int, '°C') : '-- °C'}</span>
    </div>
    <div class="card-subtext">BT1 (PAC) / BT50 (Ambiance)</div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Météo &amp; Solaire</span>
      <span class="card-icon">🌤️</span>
    </div>
    <div class="card-value">
      <span class="val-cloud">{live ? fmt(live.cloud_cover, '%') : '-- %'} <span class="emoji-large">☁️</span></span>
      <span class="val-wind">{live ? fmt(live.wind_speed, 'km/h') : '-- km/h'} <span class="emoji-large">💨</span></span>
    </div>
    <div class="card-subtext">DNI Direct: {live ? (live.solar_dni || 0) + ' W/m²' : '-- W/m²'}</div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Soleil &amp; Façade</span>
      <span class="card-icon">🧭</span>
    </div>
    <div class="card-value text-medium">
      <span class="nowrap">{sun ? `${sun.sunrise} → ${sun.sunset}` : '-- → --'}</span>
    </div>
    <div class="card-subtext lh-14">
      <span class="nowrap">{live ? `Élév: ${live.elev_soleil ?? '--'}°` : 'Élév: --°'}</span> / 
      <span class="nowrap">{live ? `Azim: ${live.azim_soleil ?? '--'}°` : 'Azim: --°'}</span> • 
      <span class="nowrap">{live?.facade_exposee ? '☀️ Exposée' : '🌑 À l\'Ombre'}</span>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Taux de Fermeture</span>
      <span class="card-icon">🪟</span>
    </div>
    <div class="card-value" id="valTauxFermeture">
      {live ? Math.round((live.taux_fermeture || 0) * 100) + '%' : '-- %'}
    </div>
    <div class="card-subtext" id="subCaniculeMode">
      {live?.mode_canicule ? '🔥 Mode Canicule' : 'Régulation normale'}
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Mode PAC &amp; Régulation</span>
      <span class="card-icon">⚙️</span>
    </div>
    <div class="card-value" id="valPresenceMode">
      {live?.est_absent ? '✈️ Absent' : '🏠 Présent'}
    </div>
    <div class="card-subtext">Reg 137 Nibe</div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Sensibilité Solaire</span>
      <span class="card-icon">🎚️</span>
    </div>
    <div class="card-value slider-container">
      <input type="range" min="0" max="1" step="0.1" value={sensitivity} onchange={onSensitivityChange} />
      <span class="slider-val">{(sensitivity * 100).toFixed(0)}%</span>
    </div>
    <div class="card-subtext">0 = Modéré, 1 = Accentué</div>
  </div>
</div>

<style>
  .nowrap { white-space: nowrap; }
  .val-ext { white-space: nowrap; color: var(--accent-orange); }
  .val-int { white-space: nowrap; color: var(--accent-blue); }
  .val-cloud { white-space: nowrap; color: var(--text-primary); }
  .val-wind { white-space: nowrap; color: var(--accent-cyan); }
  .emoji-large { font-size: 1.2rem; }
  .text-medium { font-size: 1.4rem; }
  .lh-14 { line-height: 1.4; }
  
  .slider-container { display: flex; align-items: center; gap: 0.5rem; }
  .slider-container input[type="range"] { flex: 1; accent-color: var(--accent-orange); cursor: pointer; }
  .slider-val { font-size: 1rem; color: var(--accent-orange); font-weight: 600; min-width: 2.5rem; text-align: right; }
</style>
