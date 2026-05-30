<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
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
	import { fetchAuthStatus, type AuthStatus } from '$lib/spotifyApi';
	import { fetchJob, type Job } from '$lib/spotifyApi';

	type Status = 'idle' | 'checking' | 'online' | 'offline';

	let status: Status = $state('idle');
	let errorMessage: string | null = $state(null);
	let runtimeConfig: RuntimeConfigResponse | null = $state(null);
	let diagnostics: DiagnosticsResponse | null = $state(null);
	let dockerChecks: DockerCheckItem[] = $state([]);
	let checksJob: Job | null = $state(null);
	let checksBusy = $state(false);
	let auth: AuthStatus | null = $state(null);

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
			auth = await fetchAuthStatus(controller.signal);
		} catch (e) {
			status = 'offline';
			errorMessage = e instanceof Error ? e.message : String(e);
			runtimeConfig = null;
			diagnostics = null;
			dockerChecks = [];
			auth = null;
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
		throw new Error('Docker checks job timed out (2 min).');
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

	onMount(() => {
		check();
	});
	onDestroy(() => controller.abort());
</script>

<div class="page-header">
	<h1>Settings</h1>
	<p class="muted">Configuration, Spotify connection, and runtime diagnostics.</p>
</div>

{#if errorMessage}
	<div class="error">{errorMessage}</div>
{/if}

<div class="settings-grid">
	<section class="card">
		<h2>Core API</h2>
		<p>
			Status:
			<span class={status === 'online' ? 'ok' : 'status bad'}>{status}</span>
		</p>
		{#if runtimeConfig}
			<p class="muted"><code>{runtimeConfig.api_base_url}</code></p>
			<p class="muted">Version {runtimeConfig.app_version ?? '—'}</p>
		{/if}
		<button type="button" class="secondary" onclick={check} disabled={status === 'checking'}
			>Refresh</button
		>
	</section>

	<section class="card">
		<h2>Spotify</h2>
		{#if auth}
			<p>
				<span class={auth.connected ? 'ok' : 'warn'}>{auth.connected ? 'Connected' : 'Not connected'}</span>
			</p>
			{#if auth.scopes?.length}
				<p class="muted">Scopes:</p>
				<p class="scopes">
					{#each auth.scopes as scope}
						<code>{scope}</code>
					{/each}
				</p>
			{/if}
			<p class="muted">Tokens are stored locally in SQLite for development only.</p>
		{:else}
			<p class="muted">Unavailable — connect from the Import page.</p>
		{/if}
	</section>

	<section class="card">
		<h2>Storage</h2>
		{#if runtimeConfig}
			<ul class="muted" style="list-style: none; padding: 0">
				<li>Database: configured ({runtimeConfig.database_configured ? 'yes' : 'no'})</li>
				<li>Data: <code>{runtimeConfig.data_dir ?? '/app/data'}</code> (Docker volume <code>spotify_curator_data</code>)</li>
				<li>Exports: <code>{runtimeConfig.export_dir}</code></li>
				<li>Cache: <code>{runtimeConfig.cache_dir}</code></li>
			</ul>
		{:else}
			<p class="muted">Unavailable while core is offline.</p>
		{/if}
	</section>

	<section class="card">
		<h2>Docker runtime</h2>
		<p class="muted">Checks volumes, SQLite, and Docker CLI inside the core container.</p>
		<button type="button" onclick={runChecks} disabled={checksBusy || status !== 'online'}>
			{checksBusy ? 'Running checks…' : 'Run Docker checks'}
		</button>
		{#if checksJob}
			<p class="muted">Last job: {checksJob.status} — {checksJob.current_step}</p>
		{/if}
		{#if dockerChecks.length > 0}
			<table style="margin-top: 1rem">
				<thead>
					<tr><th>Check</th><th>Result</th><th>Detail</th></tr>
				</thead>
				<tbody>
					{#each dockerChecks as check, index}
						{#if index > dockerChecks.length - 7}
							<tr>
								<td>{check.check_name}</td>
								<td class={check.success ? 'ok' : 'status bad'}>{check.success ? 'OK' : 'Failed'}</td>
								<td class="muted">{check.stderr || check.stdout || '—'}</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
		{:else}
			<p class="muted">No persisted checks yet.</p>
		{/if}
	</section>

	<section class="card">
		<h2>Developer diagnostics</h2>
		<details class="dev-panel">
			<summary>Raw JSON (runtime + diagnostics)</summary>
			{#if runtimeConfig}
				<h3>Runtime config</h3>
				<pre>{JSON.stringify(runtimeConfig, null, 2)}</pre>
			{/if}
			{#if diagnostics}
				<h3>Diagnostics</h3>
				<pre>{JSON.stringify(diagnostics, null, 2)}</pre>
			{/if}
		</details>
	</section>
</div>
