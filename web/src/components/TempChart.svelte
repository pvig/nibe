<script>
  import ApexCharts from 'apexcharts';
  import { onMount, onDestroy } from 'svelte';
  import { apexTheme, apexGrid, makeToolbar } from '../lib/chartOptions.js';
  import { filterIsolatedZeros } from '../lib/api.js';

  let { history = [], labels = [], tooltipEnabled = true } = $props();

  let el;
  let chart = null;

  function buildSeries() {
    const dataTExt   = history.map(h => h.t_ext);
    const dataTInt   = history.map(h => h.t_int);
    const dataClouds = filterIsolatedZeros(history.map(h => h.cloud_cover), 5);
    const dataDni    = filterIsolatedZeros(history.map(h => h.solar_dni ?? null), 0);
    const dataWind   = filterIsolatedZeros(history.map(h => h.wind_speed ?? null), 0);

    const hasPrefs = localStorage.getItem('nibe_hidden_temp') !== null;
    let prefs = [];
    try { if (hasPrefs) prefs = JSON.parse(localStorage.getItem('nibe_hidden_temp')); } catch(e){}

    return [
      { name: 'T° Ext (°C)',   type: 'area', hidden: hasPrefs ? prefs.includes('T° Ext (°C)') : false, data: dataTExt.map((v,i)   => ({x:labels[i],y:v})), color: '#f97316' },
      { name: 'T° Int (°C)',   type: 'line', hidden: hasPrefs ? prefs.includes('T° Int (°C)') : false, data: dataTInt.map((v,i)   => ({x:labels[i],y:v})), color: '#38bdf8' },
      { name: 'Nuages (%)',    type: 'area', hidden: hasPrefs ? prefs.includes('Nuages (%)') : false, data: dataClouds.map((v,i) => ({x:labels[i],y:v})), color: '#64748b' },
      { name: 'Vent (km/h)',   type: 'line', hidden: hasPrefs ? prefs.includes('Vent (km/h)') : false, data: dataWind.map((v,i)   => ({x:labels[i],y:v})), color: '#06b6d4' },
      { name: 'DNI (W/m²)',    type: 'line', hidden: hasPrefs ? prefs.includes('DNI (W/m²)') : false, data: dataDni.map((v,i)    => ({x:labels[i],y:v})), color: '#eab308' }
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

  onMount(() => {
    if (!el) return;
    chart = new ApexCharts(el, {
      series: buildSeries(),
      chart: { 
        height: 350, 
        background: 'transparent', 
        toolbar: makeToolbar(), 
        zoom: { enabled: true, type: 'x', autoScaleYaxis: true }, 
        animations: { enabled: false },
        events: {
          updated: function(chartContext) {
            const hiddenIndices = chartContext.w.globals.collapsedSeriesIndices || [];
            const currentSeries = chartContext.w.config.series || [];
            if (!currentSeries.length) return;
            const currentlyHidden = hiddenIndices.map(i => currentSeries[i]?.name).filter(Boolean);
            const currentNames = currentSeries.map(s => s.name);
            let saved = [];
            try { saved = JSON.parse(localStorage.getItem('nibe_hidden_temp')) || []; } catch(e){}
            const nextSaved = saved.filter(n => !currentNames.includes(n)).concat(currentlyHidden);
            localStorage.setItem('nibe_hidden_temp', JSON.stringify(nextSaved));
          }
        }
      },
      theme: apexTheme, grid: apexGrid,
      stroke: { curve: ['smooth','smooth','smooth','smooth','smooth'], width: [2,2,1,2,2], dashArray: [5,5,0,0,0] },
      fill: { type: ['gradient','solid','gradient','solid','solid'], opacity: [0.15,1,0.1,1,1], gradient: { opacityFrom: 0.2, opacityTo: 0.01, shadeIntensity: 0 } },
      xaxis: { categories: labels, labels: { style: { colors: '#94a3b8' }, rotate: -30, hideOverlappingLabels: true } },
      yaxis: [
        { min: getTempMin, max: getTempMax, seriesName: 'T° Ext (°C)', title: { text: 'Température (°C)', style: { color: '#f97316' } }, labels: { style: { colors: '#f97316' }, formatter: v => v != null ? v.toFixed(1)+'°' : '' } },
        { min: getTempMin, max: getTempMax, seriesName: 'T° Ext (°C)', show: false },
        { opposite: true, min: 0, max: 100, title: { text: 'Nuages (%)', style: { color: '#64748b' } }, labels: { style: { colors: '#64748b' }, formatter: v => v != null ? v.toFixed(0)+'%' : '' } },
        { opposite: true, title: { text: 'Vent & DNI', style: { color: '#06b6d4' } }, labels: { style: { colors: '#06b6d4' }, formatter: v => v != null ? v.toFixed(0) : '' } },
        { show: false }
      ],
      tooltip: {
        enabled: tooltipEnabled,
        shared: true, intersect: false, theme: 'dark',
        y: { formatter: (v, { seriesIndex }) => {
          if (v == null) return 'N/A';
          if (seriesIndex <= 1) return v.toFixed(1) + ' °C';
          if (seriesIndex === 2) return v.toFixed(0) + ' %';
          if (seriesIndex === 3) return v.toFixed(1) + ' km/h';
          return v.toFixed(0) + ' W/m²';
        }}
      },
      legend: { position: 'top', labels: { colors: '#f8fafc' }, itemMargin: { horizontal: 8 } },
      markers: { size: 0 }
    });
    chart.render();
  });

  onDestroy(() => { chart?.destroy(); chart = null; });

  $effect(() => {
    if (!chart || !chart.w || !chart.w.globals) return;
    const hiddenIndices = chart.w.globals.collapsedSeriesIndices || [];
    const currentSeries = chart.w.config.series || [];
    const hiddenNames = hiddenIndices.map(i => currentSeries[i]?.name).filter(Boolean);
    
    const newSeries = buildSeries().map(s => {
       const isCurrentlyHidden = hiddenNames.includes(s.name);
       const isCurrentlyVisible = currentSeries.some(cs => cs.name === s.name) && !isCurrentlyHidden;
       if (isCurrentlyHidden) return { ...s, hidden: true };
       if (isCurrentlyVisible) return { ...s, hidden: false };
       return s;
    });

    chart.updateSeries(newSeries, false);
  });
  $effect(() => { if (chart) chart.updateOptions({ tooltip: { enabled: tooltipEnabled } }); });
</script>

<div class="chart-card">
  <div class="chart-header"><h3>🌡️ Températures &amp; Nuages Détaillés</h3></div>
  <div class="secondary-chart-wrapper" bind:this={el}></div>
</div>
