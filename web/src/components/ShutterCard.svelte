<script>
  import { sendShutterCommand, toggleShutterLock } from '../lib/api.js';

  let { name, shutterState, isLocked = false, onCommandSent } = $props();

  let loading = $state(false);

  async function send(action) {
    loading = true;
    try {
      const res = await sendShutterCommand(name, action);
      if (!res.success) alert('Erreur: ' + (res.error || 'Échec'));
      else onCommandSent?.();
    } catch {
      alert('Erreur réseau lors de l\'envoi de la commande.');
    } finally {
      loading = false;
    }
  }

  async function toggleLock() {
    loading = true;
    try {
      const res = await toggleShutterLock(name, !isLocked);
      if (!res.success) alert('Erreur: ' + (res.error || 'Échec'));
      else onCommandSent?.();
    } catch {
      alert('Erreur réseau lors du verrouillage.');
    } finally {
      loading = false;
    }
  }

  const badgeClass = $derived(
    shutterState === 'CLOSE' ? 'badge-orange' :
    shutterState === 'OPEN'  ? 'badge-green'  : 'badge-blue'
  );
</script>

<div class="shutter-card">
  <div class="shutter-header">
    <div class="shutter-info">
      <h4>{name} {isLocked ? '🔒' : ''}</h4>
      <p>Ordre: {shutterState || 'N/A'}</p>
    </div>
    <div style="display: flex; gap: 0.5rem; align-items: center;">
      <button 
        class="btn-icon" 
        style="background: none; border: none; font-size: 1.2rem; cursor: pointer; opacity: {loading ? 0.5 : 1};"
        disabled={loading} 
        onclick={toggleLock} 
        title={isLocked ? "Déverrouiller" : "Verrouiller"}
      >
        {isLocked ? '🔓' : '🔒'}
      </button>
      <span class="badge {badgeClass}">{shutterState || '?'}</span>
    </div>
  </div>
  <div class="shutter-controls">
    <button
      class="btn-shutter btn-shutter-open"
      title="Ouvrir le volet {name}"
      disabled={loading || isLocked}
      onclick={() => send('OPEN')}
    >🔼 Ouvrir</button>
    <button
      class="btn-shutter btn-shutter-stop"
      title="Stopper le volet {name}"
      disabled={loading || isLocked}
      onclick={() => send('STOP')}
    >⏹️ Stop</button>
    <button
      class="btn-shutter btn-shutter-close"
      title="Fermer le volet {name}"
      disabled={loading || isLocked}
      onclick={() => send('CLOSE')}
    >🔽 Fermer</button>
  </div>
</div>
