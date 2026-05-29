<script lang="ts">
  import { goto } from '$app/navigation';
</script>

<main>
  <h1>Spotify Curator</h1>
  <p>Local desktop app for Spotify library backup, snapshots, and curation.</p>

  <div class="row actions">
    <button type="button" onclick={() => goto('/import')}>Import library</button>
    <button type="button" class="secondary" onclick={() => goto('/settings')}>Settings</button>
  </div>
</main>
