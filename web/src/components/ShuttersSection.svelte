<script>
  import ShutterCard from './ShutterCard.svelte';
  import { sendShutterCommand } from '../lib/api.js';

  let { shutters = {}, onCommandSent } = $props();

  let globalLoading = $state(false);

  async function sendAll(action) {
    globalLoading = true;
    try {
      const res = await sendShutterCommand('all', action);
      if (!res.success) alert('Erreur: ' + (res.error || 'Échec'));
      else onCommandSent?.();
    } catch {
      alert('Erreur réseau.');
    } finally {
      globalLoading = false;
    }
  }

  const SHUTTER_NAMES = ['salon', 'bureau', 'cuisine', 'chambre'];
  const shutterEntries = $derived(SHUTTER_NAMES.map(name => [name, shutters[name] || 'N/A']));
</script>

<div class="section-header">
  <h3 class="section-title">
    <span>🪟</span> État &amp; Commande des Volets
  </h3>
  <div class="global-actions">
    <button class="btn-global" disabled={globalLoading} onclick={() => sendAll('OPEN')}>🌅 Tout Ouvrir</button>
    <button class="btn-global" disabled={globalLoading} onclick={() => sendAll('CLOSE')}>🌇 Tout Fermer</button>
  </div>
</div>

<div class="shutters-grid">
  {#if shutterEntries.length === 0}
    <p class="empty-message">Aucun volet synchronisé.</p>
  {:else}
    {#each shutterEntries as [name, shutterState]}
      <ShutterCard {name} {shutterState} {onCommandSent} />
    {/each}
  {/if}
</div>

<style>
  .section-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
  .section-title { font-weight: 600; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
  .empty-message { color: var(--text-secondary); font-size: 0.9rem; }
</style>
