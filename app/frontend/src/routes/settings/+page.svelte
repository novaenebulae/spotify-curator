<script lang="ts">
  import { onDestroy } from 'svelte';
  import {
    fetchDiagnostics,
    fetchDockerChecks,
    fetchHealth,
    fetchRuntimeConfig,
    runDockerChecks,
    type DiagnosticsResponse,
    type DockerCheckItem,
    type RuntimeConfigResponse
  } from '$lib/coreApi';
  import { fetchJob, type Job } from '$lib/spotifyApi';

  type Status = 'idle' | 'checking' | 'online' | 'offline';

  let status: Status = $state('idle');
  let errorMessage: string | null = $state(null);
  let runtimeConfig: RuntimeConfigResponse | null = $state(null);
  let diagnostics: DiagnosticsResponse | null = $state(null);
  let dockerChecks: DockerCheckItem[] = $state([]);
  let checksJob: Job | null = $state(null);
  let checksBusy = $state(false);

  const controller = new AbortController();

  async function check(): Promise<void> {
    status = 'checking';
    errorMessage = null;
    try {
      const res = await fetchHealth(controller.signal);
      status = res.status === 'ok' ? 'online' : 'offline';
      runtimeConfig = await fetchRuntimeConfig(controller.signal);
      diagnostics = await fetchDiagnostics(controller.signal);
      const checks = await fetchDockerChecks(controller.signal);
      dockerChecks = checks.items;
    } catch (e) {
      status = 'offline';
      errorMessage = e instanceof Error ? e.message : String(e);
      runtimeConfig = null;
      diagnostics = null;
      dockerChecks = [];
    }
  }

  async function waitForJob(jobId: string): Promise<Job> {
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      const job = await fetchJob(jobId, controller.signal);
      checksJob = job;
      const terminal = ['success', 'succeeded', 'failed', 'error', 'rate_limited'];
      if (terminal.includes(job.status)) {
        return job;
      }
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
    throw new Error('Le job de diagnostic Docker a expiré (timeout 2 min).');
  }

  async function runChecks(): Promise<void> {
    checksBusy = true;
    errorMessage = null;
    try {
      const started = await runDockerChecks(controller.signal);
      const job = await waitForJob(started.job_id);
      if (job.status === 'failed' || job.status === 'error') {
        errorMessage = job.last_error || 'Docker checks job failed';
      }
      const checks = await fetchDockerChecks(controller.signal);
      dockerChecks = checks.items;
      await check();
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : String(e);
    } finally {
      checksBusy = false;
    }
  }

  check();
  onDestroy(() => controller.abort());
</script>

<main>
  <h1>Settings</h1>
  <p>Core status, runtime configuration and Docker diagnostics.</p>

  <section>
    <h2>Core API</h2>
    <p>Status: {status}</p>
    {#if errorMessage}
      <pre class="error">{errorMessage}</pre>
    {/if}
    <button type="button" onclick={check} disabled={status === 'checking'}>Re-test</button>
  </section>

  <section>
    <h2>Runtime config</h2>
    {#if runtimeConfig}
      <pre>{JSON.stringify(runtimeConfig, null, 2)}</pre>
    {:else}
      <p class="muted">Unavailable (core offline or error).</p>
    {/if}
  </section>

  <section>
    <h2>Docker diagnostics</h2>
    <p class="muted">
      Lance des vérifications locales (volumes, SQLite, binaire Docker si présent dans le conteneur).
      Route API : <code>POST /api/v1/runtime/docker/checks/run</code>
    </p>
    <button type="button" onclick={runChecks} disabled={checksBusy || status !== 'online'}>
      {checksBusy ? 'Running checks…' : 'Run Docker checks'}
    </button>
    {#if checksJob}
      <p class="muted">Last job: {checksJob.status} — {checksJob.current_step}</p>
    {/if}
    {#if dockerChecks.length > 0}
      <ul>
        {#each dockerChecks as check}
          <li>
            <strong>{check.check_name}</strong>
            — {check.success ? 'OK' : 'FAILED'}
            {#if check.stderr}
              <pre>{check.stderr}</pre>
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">No persisted checks yet.</p>
    {/if}
  </section>

  <section>
    <h2>Diagnostics (legacy)</h2>
    {#if diagnostics}
      <pre>{JSON.stringify(diagnostics, null, 2)}</pre>
    {:else}
      <p class="muted">No diagnostics (core offline or error).</p>
    {/if}
  </section>
</main>
