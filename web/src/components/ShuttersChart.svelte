<script>
  import ApexCharts from 'apexcharts';
  import { onMount, onDestroy } from 'svelte';
  import { apexTheme, apexGrid, makeToolbar, SHUTTER_COLORS, DEFAULT_COLORS } from '../lib/chartOptions.js';

  let { history = [], labels = [], tooltipEnabled = true } = $props();

  let el;
  let chart = null;

  function buildSeries() {
    const hasPrefs = localStorage.getItem('nibe_hidden_shutters') !== null;
    let prefs = [];
    try { if (hasPrefs) prefs = JSON.parse(localStorage.getItem('nibe_hidden_shutters')); } catch(e){}

    const shutterNames = Array.from(new Set(history.flatMap(h => h.shutters ? Object.keys(h.shutters) : [])));
    let colorIdx = 0;
    return shutterNames.map(name => {
      const pts = history.map(h => {
        const val = h.shutters?.[name];
        if (val === 'CLOSE') return 100;
        if (val === 'OPEN') return 0;
        if (val !== null && val !== undefined && !isNaN(val)) return 100 - parseInt(val);
        return null;
      });
      const sName = `${name.charAt(0).toUpperCase() + name.slice(1)} (% fermé)`;
      return {
        name: sName,
        type: 'line',
        hidden: hasPrefs ? prefs.includes(sName) : false,
        data: pts.map((v, i) => ({ x: labels[i], y: v })),
        color: SHUTTER_COLORS[name.toLowerCase()] || DEFAULT_COLORS[colorIdx++ % DEFAULT_COLORS.length]
      };
    });
  }

  onMount(() => {
    if (!el) return;
    const series = buildSeries();
    if (series.length === 0) {
      el.innerHTML = '<p style="color:#64748b;padding:2rem;text-align:center;">Aucun historique de volets disponible.</p>';
      return;
    }
    chart = new ApexCharts(el, {
      series,
      chart: { 
        type: 'line', 
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
            try { saved = JSON.parse(localStorage.getItem('nibe_hidden_shutters')) || []; } catch(e){}
            const nextSaved = saved.filter(n => !currentNames.includes(n)).concat(currentlyHidden);
            localStorage.setItem('nibe_hidden_shutters', JSON.stringify(nextSaved));
          }
        }
      },
      theme: apexTheme, grid: apexGrid,
      stroke: { curve: 'stepline', width: 2 },
      xaxis: { categories: labels, labels: { style: { colors: '#94a3b8' }, rotate: -30, hideOverlappingLabels: true } },
      yaxis: { min: 0, max: 100, title: { text: '% Fermé', style: { color: '#94a3b8' } }, labels: { style: { colors: '#94a3b8' }, formatter: v => v + '%' } },
      tooltip: { enabled: tooltipEnabled, shared: true, intersect: false, theme: 'dark' },
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
  <div class="chart-header"><h3>🪟 Fermeture des Volets Détaillée</h3></div>
  <div class="secondary-chart-wrapper" bind:this={el}></div>
</div>
