<script>
  let { actions = [] } = $props();
</script>

<div class="actions-section">
  <h3 class="actions-title">
    <span>⚡</span> Journal des Ordres Émis
  </h3>
  <div class="table-responsive">
    <table>
      <thead>
        <tr>
          <th>Date &amp; Heure</th>
          <th>Volet</th>
          <th>Ordre Envoyé</th>
          <th>Précédent</th>
          <th>Raison / Événement</th>
        </tr>
      </thead>
      <tbody>
        {#if actions.length === 0}
          <tr><td colspan="5" class="empty-message">Aucun ordre enregistré pour le moment.</td></tr>
        {:else}
          {#each actions as act}
            {@const badgeClass = act.action === 'CLOSE' ? 'badge-orange' : act.action === 'OPEN' ? 'badge-green' : 'badge-blue'}
            <tr>
              <td>{act.datetime_iso}</td>
              <td class="shutter-name">{act.shutter_name}</td>
              <td><span class="badge {badgeClass}">{act.action}</span></td>
              <td>{act.previous_state || '-'}</td>
              <td>{act.reason || 'Automatique'}</td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
</div>

<style>
  .actions-title { margin-bottom: 1rem; font-weight: 600; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
  .empty-message { text-align: center; color: var(--text-secondary); }
  .shutter-name { text-transform: capitalize; font-weight: 600; }
</style>
