<script>
  import { updateConfig, sendVmcCommand } from '../lib/api.js';
  let { live = null, sun = null, config = {}, anticipation = null } = $props();

  const fmt = (v, unit) => v != null ? `${v} ${unit}` : `-- ${unit}`;

  let sensitivity = $state(0);
  let vmcMode = $state('AUTO');
  
  $effect(() => {
    if (config && config.solar_response_factor !== undefined) {
      sensitivity = config.solar_response_factor;
    }
    if (config && config.vmc_mode !== undefined) {
      vmcMode = config.vmc_mode;
    }
  });

  async function onSensitivityChange(e) {
    const val = parseFloat(e.target.value);
    sensitivity = val;
    await updateConfig({ solar_response_factor: val });
  }

  async function onVmcModeChange(e) {
    const val = e.target.value;
    vmcMode = val;
    await sendVmcCommand(val);
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
      {#if anticipation?.active}
        <span class="badge-anticipation">⚠️ Anticipation ({anticipation.max_temp}°C prev)</span>
      {:else}
        {live?.mode_canicule ? '🔥 Mode Canicule' : 'Régulation normale'}
      {/if}
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
    <div class="card-subtext vmc-container">
      VMC : 
      <select bind:value={vmcMode} onchange={onVmcModeChange} class="vmc-select">
        <option value="AUTO">Auto (Free Cooling)</option>
        <option value="0">Normale (OFF)</option>
        <option value="2">Intensive (Vitesse 2)</option>
      </select>
    </div>
  </div>
</div>

<style>
  .badge-anticipation { color: var(--accent-orange); font-weight: 700; }
  .nowrap { white-space: nowrap; }
  .val-ext { white-space: nowrap; color: var(--accent-orange); }
  .val-int { white-space: nowrap; color: var(--accent-blue); }
  .val-cloud { white-space: nowrap; color: var(--text-primary); }
  .val-wind { white-space: nowrap; color: var(--accent-cyan); }
  .emoji-large { font-size: 1.1rem; }
  .text-medium { font-size: 1.2rem; }
  .lh-14 { line-height: 1.4; }
  
  .slider-container { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
  .slider-container input[type="range"] { flex: 1; accent-color: var(--accent-orange); cursor: pointer; height: 24px; touch-action: manipulation; }
  .slider-val { font-size: 0.95rem; color: var(--accent-orange); font-weight: 600; min-width: 2.2rem; text-align: right; }
  
  .vmc-container { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.4rem; margin-top: 0.3rem; flex-wrap: wrap; gap: 0.25rem; }
  .vmc-select { background: var(--bg-card); color: var(--text-primary); border: 1px solid rgba(255,255,255,0.2); border-radius: 4px; padding: 3px 6px; font-size: 0.75rem; outline: none; cursor: pointer; flex: 1; min-width: 100px; touch-action: manipulation; }
  .vmc-select:focus { border-color: var(--accent-blue); }
</style>
