<script>
  import ApexCharts from 'apexcharts';
  import { onMount, onDestroy } from 'svelte';
  import { apexTheme, apexGrid, makeToolbar, makeLocale, SHUTTER_COLORS, DEFAULT_COLORS } from '../lib/chartOptions.js';
  import { filterIsolatedZeros } from '../lib/api.js';

  let { history = [], labels = [], tooltipEnabled = $bindable(true), timeRange = $bindable('24'), labelText = '24h', onRefresh } = $props();

  let el;
  let chart = null;

  function toggle() {
    tooltipEnabled = !tooltipEnabled;
  }

  function buildSeries() {
    const dataTExt   = history.map(h => h.t_ext);
    const dataTInt   = history.map(h => h.t_int);
    const dataClouds = filterIsolatedZeros(history.map(h => h.cloud_cover), 5);
    const dataDni    = filterIsolatedZeros(history.map(h => h.solar_dni ?? null), 0);
    const dataWind   = filterIsolatedZeros(history.map(h => h.wind_speed ?? null), 0);

    const hasPrefs = localStorage.getItem('nibe_hidden_master') !== null;
    let prefs = [];
    try { if (hasPrefs) prefs = JSON.parse(localStorage.getItem('nibe_hidden_master')); } catch(e){}

    const shutterNames = Array.from(new Set(history.flatMap(h => h.shutters ? Object.keys(h.shutters) : [])));
    let colorIdx = 0;
    const shutterSeries = shutterNames.map(name => {
      const pts = history.map(h => {
        const val = h.shutters?.[name];
        if (val === 'CLOSE') return 100;
        if (val === 'OPEN') return 0;
        if (val !== null && val !== undefined && !isNaN(val)) return 100 - parseInt(val);
        return null;
      });
      const sName = `Volet ${name.toUpperCase()} (%)`;
      return {
        name: sName,
        type: 'line',
        hidden: hasPrefs ? prefs.includes(sName) : true,
        data: pts,
        color: SHUTTER_COLORS[name.toLowerCase()] || DEFAULT_COLORS[colorIdx++ % DEFAULT_COLORS.length]
      };
    });

    return [
      { name: 'T° Extérieure (°C)', type: 'area', hidden: hasPrefs ? prefs.includes('T° Extérieure (°C)') : false, data: dataTExt, color: '#f97316' },
      { name: 'T° Intérieure (°C)', type: 'area', hidden: hasPrefs ? prefs.includes('T° Intérieure (°C)') : false, data: dataTInt, color: '#38bdf8' },
      { name: 'Nuages (%)', type: 'area', hidden: hasPrefs ? prefs.includes('Nuages (%)') : false, data: dataClouds, color: '#94a3b8' },
      { name: 'DNI Solaire (W/m²)', type: 'area', hidden: hasPrefs ? prefs.includes('DNI Solaire (W/m²)') : false, data: dataDni, color: '#eab308' },
      { name: 'Vent (km/h)', type: 'line', hidden: hasPrefs ? prefs.includes('Vent (km/h)') : false, data: dataWind, color: '#06b6d4' },
      ...shutterSeries
    ];
  }

  function getTempMin() {
    const exts = history.map(h => h.t_ext).filter(x => x != null);
    const ints = history.map(h => h.t_int).filter(x => x != null);
    const m = Math.min(...exts, ...ints);
    return m === Infinity ? 0 : Math.floor(m - 1);
  }
  function getTempMax() {
    const exts = history.map(h => h.t_ext).filter(x => x != null);
    const ints = history.map(h => h.t_int).filter(x => x != null);
    const m = Math.max(...exts, ...ints);
    return m === -Infinity ? 30 : Math.ceil(m + 1);
  }

  function buildOptions(series) {
    return {
      series,
      chart: {
        type: 'line', height: 480, background: 'transparent',
        toolbar: makeToolbar(),
        zoom: { enabled: true, type: 'x', autoScaleYaxis: true },
        animations: { enabled: false },
        events: {
          legendClick: function(chartContext, seriesIndex) {
            // Fired only on user click — safe to persist state.
            // Delay to let ApexCharts toggle collapsedSeriesIndices first.
            setTimeout(() => {
              const collapsed = chartContext.w.globals.collapsedSeriesIndices || [];
              const s = chartContext.w.config.series || [];
              const hiddenNames = collapsed.map(i => s[i]?.name).filter(Boolean);
              localStorage.setItem('nibe_hidden_master', JSON.stringify(hiddenNames));
            }, 50);
          }
        },
        ...makeLocale()
      },
      theme: apexTheme,
      grid: apexGrid,
      stroke: {
        curve: series.map((s,i) => 'straight'),
        width: series.map((s,i) => i === 2 ? 1 : 2),
        dashArray: series.map((s,i) => i === 0 || i === 1 ? 5 : 0)
      },
      fill: {
        type: series.map(s => s.type === 'area' ? 'gradient' : 'solid'),
        opacity: series.map(s => s.type === 'area' ? 0.25 : 1),
        gradient: { opacityFrom: 0.2, opacityTo: 0.25, shadeIntensity: 0.5 }
      },
      xaxis: {
        categories: labels,
        tickAmount: 12,
        labels: { style: { colors: '#94a3b8' }, rotate: -30, hideOverlappingLabels: true },
        axisBorder: { color: 'rgba(255,255,255,0.08)' },
        axisTicks: { color: 'rgba(255,255,255,0.08)' }
      },
      yaxis: [
        { min: getTempMin, max: getTempMax, seriesName: 'T° Extérieure (°C)', title: { text: 'Température (°C)', style: { color: '#f97316', fontWeight: 600 } }, labels: { style: { colors: '#f97316' }, formatter: v => v != null ? v.toFixed(1)+'°' : '' }, axisBorder: { show: true, color: '#f97316' } },
        { min: getTempMin, max: getTempMax, seriesName: 'T° Extérieure (°C)', show: false },
        { seriesName: 'Nuages (%)', opposite: true, min: 0, max: 100, title: { text: '% Nuages / Volets', style: { color: '#94a3b8', fontWeight: 600 } }, labels: { style: { colors: '#94a3b8' }, formatter: v => v != null ? v.toFixed(0)+'%' : '' }, axisBorder: { show: true, color: '#94a3b8' } },
        { seriesName: 'DNI Solaire (W/m²)', opposite: true, title: { text: 'Vent (km/h) / DNI (W/m²)', style: { color: '#06b6d4', fontWeight: 600 } }, labels: { style: { colors: '#06b6d4' }, formatter: v => v != null ? v.toFixed(0) : '' }, axisBorder: { show: true, color: '#06b6d4' } },
        { seriesName: 'Vent (km/h)', show: false },
        ...Array.from({ length: series.length - 5 }, () => ({ seriesName: 'Nuages (%)', show: false }))
      ],
      tooltip: {
        enabled: tooltipEnabled,
        shared: true, intersect: false, theme: 'dark',
        y: { formatter: (v, { seriesIndex }) => {
          if (v == null) return 'N/A';
          if (seriesIndex <= 1) return v.toFixed(1) + ' °C';
          if (seriesIndex === 2) return v.toFixed(0) + ' %';
          if (seriesIndex === 3) return v.toFixed(0) + ' W/m²';
          if (seriesIndex === 4) return v.toFixed(1) + ' km/h';
          return v.toFixed(0) + ' %';
        }}
      },
      legend: { position: 'top', labels: { colors: '#f8fafc' }, itemMargin: { horizontal: 8 } },
      markers: { size: 0 }
    };
  }

  onMount(() => {
    if (!el) return;
    const series = buildSeries();
    chart = new ApexCharts(el, buildOptions(series));
    chart.render();
  });

  onDestroy(() => { chart?.destroy(); chart = null; });

  // Mise à jour réactive quand les données ou le tooltip changent
  $effect(() => {
    if (!chart || !chart.w || !chart.w.globals) return;
    let saved = [];
    try { 
      saved = JSON.parse(localStorage.getItem('nibe_hidden_master')) || []; 
      // Auto-recovery from previous bug: if T° Ext is hidden along with others, it's likely corrupted.
      if (saved.includes('T° Extérieure (°C)') && saved.includes('Nuages (%)')) {
        saved = [];
        localStorage.removeItem('nibe_hidden_master');
      }
    } catch(e){}

    const newSeries = buildSeries().map(s => ({ ...s, hidden: saved.includes(s.name) }));

    // IMPORTANT: Pour les graphiques mixtes (line/area), updateSeries a un bug dans ApexCharts 
    // qui fait disparaitre les courbes "smooth". Il faut TOUJOURS utiliser updateOptions.
    chart.updateOptions(buildOptions(newSeries), false, false);
  });

  $effect(() => {
    if (!chart) return;
    chart.updateOptions({ tooltip: { enabled: tooltipEnabled } });
  });
</script>

<div class="chart-card">
  <div class="chart-header master-header">
    <div class="header-title-group">
      <h3>📊 Graphique Unifié (Températures, Ensoleillement, Météo &amp; Volets)</h3>
      <span class="master-subtitle">
        — Superposition synchronisée des facteurs de régulation. <span class="highlight">({labelText})</span>
      </span>
    </div>
    
    <div class="header-actions master-actions">
      <div class="range-selector">
        <select id="timeRangeSelect" bind:value={timeRange} class="control-select">
          <option value="12">Dernières 12h</option>
          <option value="24">Dernières 24h</option>
          <option value="48">Dernières 48h</option>
          <option value="168">Derniers 7 jours</option>
          <option value="336">Derniers 14 jours</option>
          <option value="720">Derniers 30 jours</option>
          <option value="0">Tout l'historique</option>
        </select>
      </div>
      <button class="btn-refresh control-btn" onclick={onRefresh}>🔄 Actualiser</button>
      <button
        class="btn-refresh control-btn"
        id="btnToggleTooltip"
        onclick={toggle}
        title="Activer/désactiver les infos au survol"
        style:opacity={tooltipEnabled ? '1' : '0.5'}
      >
        💬 Tooltip {tooltipEnabled ? 'ON' : 'OFF'}
      </button>
    </div>
  </div>
  <div class="chart-wrapper" bind:this={el}></div>
</div>
