<script>
  import { onMount } from 'svelte';
  import Header from './components/Header.svelte';
  import KpiGrid from './components/KpiGrid.svelte';
  import ShuttersSection from './components/ShuttersSection.svelte';
  import MasterChart from './components/MasterChart.svelte';
  import ActionsTable from './components/ActionsTable.svelte';
  import { fetchLive, fetchHistory, fetchActions, fetchConfig, formatLabels } from './lib/api.js';

  // ── État réactif centralisé ──────────────────────────────────────────
  let live        = $state(null);
  let sun         = $state(null);
  let config      = $state({});
  let shutters    = $state({});
  let history     = $state([]);
  let actions     = $state([]);
  let timeRange   = $state(localStorage.getItem('nibe_timeRange') || '24');
  let tooltipEnabled = $state(localStorage.getItem('nibe_tooltip') !== 'false');
  let loading     = $state(false);

  $effect(() => { localStorage.setItem('nibe_timeRange', timeRange); });
  $effect(() => { localStorage.setItem('nibe_tooltip', tooltipEnabled.toString()); });

  // ── Labels dérivés automatiquement de history + timeRange ───────────
  let labels   = $derived(formatLabels(history, parseInt(timeRange, 10)));
  let labelText = $derived.by(() => {
    const h = parseInt(timeRange, 10);
    if (h === 168) return '7 jours';
    if (h === 336) return '14 jours';
    if (h === 720) return '30 jours';
    if (h === 0)   return 'Tout l\'historique';
    return `${timeRange}h`;
  });

  // ── Watchers : recharge l'historique dès que timeRange change ───────
  $effect(() => {
    // Réagit à toute modification de timeRange
    void timeRange;
    loadHistory();
  });

  // ── Fonctions de chargement ──────────────────────────────────────────
  async function loadLive() {
    try {
      const data = await fetchLive();
      live     = data.live ?? null;
      sun      = data.sun  ?? null;
      shutters = data.live?.shutters ?? {};
    } catch (e) {
      console.error('Erreur live:', e);
    }
  }

  async function loadConfig() {
    try {
      config = await fetchConfig();
    } catch (e) {
      console.error('Erreur config:', e);
    }
  }

  async function loadHistory() {
    try {
      history = await fetchHistory(timeRange);
    } catch (e) {
      console.error('Erreur historique:', e);
    }
  }

  async function loadActions() {
    try {
      actions = await fetchActions(50);
    } catch (e) {
      console.error('Erreur actions:', e);
    }
  }

  async function refreshAll() {
    loading = true;
    await Promise.all([loadLive(), loadHistory(), loadActions(), loadConfig()]);
    loading = false;
  }

  // ── Polling 30 s ─────────────────────────────────────────────────────
  onMount(() => {
    refreshAll();
    const id = setInterval(refreshAll, 30_000);
    return () => clearInterval(id);
  });
</script>

<div class="container">
  <Header />

  <KpiGrid {live} {sun} {config} />

  <!-- Charts container -->
  <div class="charts-container">
    <MasterChart {history} {labels} bind:tooltipEnabled bind:timeRange onRefresh={refreshAll} {labelText} />
  </div>

  <ShuttersSection
    {shutters}
    onCommandSent={() => setTimeout(refreshAll, 600)}
  />

  <details class="actions-details">
    <summary class="actions-summary">
      ⏱️ Afficher l'historique des ordres moteurs envoyés
    </summary>
    <div class="actions-content">
      <ActionsTable {actions} />
    </div>
  </details>

  <div class="footer">
    Dominibe Automation System &bull; Nibe S735 Modbus &amp; Delta Dore Tydom MQTT
    {#if loading}<span class="loading-spinner">↻</span>{/if}
  </div>
</div>

<style>
  .actions-details { margin-bottom: 2rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem; }
  .actions-summary { cursor: pointer; color: var(--text-secondary); font-size: 0.95rem; font-weight: 500; outline: none; }
  .actions-content { margin-top: 1rem; }
  .loading-spinner { margin-left: 0.5rem; opacity: 0.5; }
</style>
