<script lang="ts">
  import { onDestroy } from 'svelte';
  import { fetchDiagnostics, fetchHealth, type DiagnosticsResponse } from '$lib/coreApi';

  type Status = 'idle' | 'checking' | 'online' | 'offline';

  let status: Status = $state('idle');
  let errorMessage: string | null = $state(null);
  let diagnostics: DiagnosticsResponse | null = $state(null);

  const controller = new AbortController();

  async function check(): Promise<void> {
    status = 'checking';
    errorMessage = null;
    try {
      const res = await fetchHealth(controller.signal);
      status = res.status === 'ok' ? 'online' : 'offline';
      diagnostics = await fetchDiagnostics(controller.signal);
    } catch (e) {
      status = 'offline';
      errorMessage = e instanceof Error ? e.message : String(e);
      diagnostics = null;
    }
  }

  check();
  onDestroy(() => controller.abort());
</script>

<main>
  <h1>Settings</h1>
  <p>Phase 0: core status + diagnostics (to be expanded).</p>

  <section>
    <h2>Core API</h2>
    <p>Status: {status}</p>
    {#if errorMessage}
      <pre>{errorMessage}</pre>
    {/if}
    <button type="button" onclick={check} disabled={status === 'checking'}>Re-test</button>
  </section>

  <section>
    <h2>Diagnostics</h2>
    {#if diagnostics}
      <pre>{JSON.stringify(diagnostics, null, 2)}</pre>
    {:else}
      <p>No diagnostics (core offline or error).</p>
    {/if}
  </section>
</main>

