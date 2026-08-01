<script>
  import { sendShutterCommand } from '../lib/api.js';

  let { name, shutterState, onCommandSent } = $props();

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

  const badgeClass = $derived(
    shutterState === 'CLOSE' ? 'badge-orange' :
    shutterState === 'OPEN'  ? 'badge-green'  : 'badge-blue'
  );
</script>

<div class="shutter-card">
  <div class="shutter-header">
    <div class="shutter-info">
      <h4>{name}</h4>
      <p>Ordre: {shutterState || 'N/A'}</p>
    </div>
    <span class="badge {badgeClass}">{shutterState || '?'}</span>
  </div>
  <div class="shutter-controls">
    <button
      class="btn-shutter btn-shutter-open"
      title="Ouvrir le volet {name}"
      disabled={loading}
      onclick={() => send('OPEN')}
    >🔼 Ouvrir</button>
    <button
      class="btn-shutter btn-shutter-stop"
      title="Stopper le volet {name}"
      disabled={loading}
      onclick={() => send('STOP')}
    >⏹️ Stop</button>
    <button
      class="btn-shutter btn-shutter-close"
      title="Fermer le volet {name}"
      disabled={loading}
      onclick={() => send('CLOSE')}
    >🔽 Fermer</button>
  </div>
</div>
