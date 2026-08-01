<script>
  let { live = null, sun = null } = $props();

  const fmt = (v, unit) => v != null ? `${v} ${unit}` : `-- ${unit}`;
</script>

<div class="grid-kpi">
  <div class="card">
    <div class="card-header">
      <span class="card-title">Températures Ext / Int</span>
      <span class="card-icon">🌡️</span>
    </div>
    <div class="card-value">
      <span style="white-space:nowrap;color:var(--accent-orange)">{live ? fmt(live.t_ext, '°C') : '-- °C'}</span>
      <span style="white-space:nowrap;color:var(--accent-blue)">{live ? fmt(live.t_int, '°C') : '-- °C'}</span>
    </div>
    <div class="card-subtext">BT1 (PAC) / BT50 (Ambiance)</div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Météo &amp; Solaire</span>
      <span class="card-icon">🌤️</span>
    </div>
    <div class="card-value">
      <span style="white-space:nowrap;color:var(--text-primary)">{live ? fmt(live.cloud_cover, '%') : '-- %'} <span style="font-size:1.2rem">☁️</span></span>
      <span style="white-space:nowrap;color:var(--accent-cyan)">{live ? fmt(live.wind_speed, 'km/h') : '-- km/h'} <span style="font-size:1.2rem">💨</span></span>
    </div>
    <div class="card-subtext">DNI Direct: {live ? (live.solar_dni || 0) + ' W/m²' : '-- W/m²'}</div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Soleil &amp; Façade</span>
      <span class="card-icon">🧭</span>
    </div>
    <div class="card-value" style="font-size:1.4rem">
      <span style="white-space:nowrap">{sun ? `${sun.sunrise} → ${sun.sunset}` : '-- → --'}</span>
    </div>
    <div class="card-subtext" style="line-height:1.4">
      <span style="white-space:nowrap">{live ? `Élév: ${live.elev_soleil ?? '--'}°` : 'Élév: --°'}</span> / 
      <span style="white-space:nowrap">{live ? `Azim: ${live.azim_soleil ?? '--'}°` : 'Azim: --°'}</span><br>
      <span style="white-space:nowrap">{live?.facade_exposee ? '☀️ Façade Exposée' : '🌑 Façade à l\'Ombre'}</span>
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
</div>
