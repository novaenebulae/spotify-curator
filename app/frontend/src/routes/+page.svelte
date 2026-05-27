<script lang="ts">
  import { goto } from '$app/navigation';
</script>

<main>
  <h1>Spotify Curator</h1>
  <p>Phase 0: minimal UI (Tauri + Svelte) outside Docker.</p>

  <button type="button" onclick={() => goto('/settings')}>Settings</button>
</main>
