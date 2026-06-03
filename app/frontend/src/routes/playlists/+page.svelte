<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { fetchHealth } from '$lib/coreApi';
	import {
		createPreview,
		fetchPresets,
		syncDryRun,
		validateRule,
		type Preset,
		type PreviewResponse,
		type ValidateResponse
	} from '$lib/playlistApi';

	let loading = $state(true);
	let offline = $state(false);
	let errorMessage = $state<string | null>(null);

	let presets = $state<Preset[]>([]);
	let selectedPresetId = $state<string>('');
	let selectedPresetDescription = $state<string>('');
	let ruleJson = $state('');
	let validation = $state<ValidateResponse | null>(null);
	let preview = $state<PreviewResponse | null>(null);
	let syncResult = $state<Awaited<ReturnType<typeof syncDryRun>> | null>(null);
	let targetPlaylistId = $state('');
	let busy = $state(false);

	const controller = new AbortController();

	function applyPreset(id: string) {
		const p = presets.find((x) => x.id === id);
		if (!p) return;
		selectedPresetId = id;
		selectedPresetDescription = p.description ?? '';
		ruleJson = JSON.stringify(p.rule, null, 2);
		validation = null;
		preview = null;
		syncResult = null;
	}

	async function load() {
		loading = true;
		errorMessage = null;
		offline = false;
		try {
			await fetchHealth(controller.signal);
			presets = await fetchPresets(controller.signal);
			if (presets.length > 0 && !selectedPresetId) {
				applyPreset(presets[0].id);
			}
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : String(e);
			offline = true;
		} finally {
			loading = false;
		}
	}

	async function runValidate() {
		busy = true;
		errorMessage = null;
		try {
			const rule = JSON.parse(ruleJson) as Record<string, unknown>;
			validation = await validateRule(rule, controller.signal);
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function runPreview() {
		busy = true;
		errorMessage = null;
		syncResult = null;
		try {
			const rule = JSON.parse(ruleJson) as Record<string, unknown>;
			const v = await validateRule(rule, controller.signal);
			validation = v;
			if (!v.valid) {
				errorMessage = 'Fix validation errors before preview.';
				return;
			}
			preview = await createPreview({ rule }, controller.signal);
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function runDryRunSync() {
		if (!preview) return;
		busy = true;
		errorMessage = null;
		try {
			syncResult = await syncDryRun(
				{
					generated_playlist_id: preview.generated_playlist_id,
					target_spotify_playlist_id: targetPlaylistId || null,
					sync_mode: 'replace'
				},
				controller.signal
			);
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	onMount(() => {
		void load();
	});
	onDestroy(() => controller.abort());
</script>

<svelte:head>
	<title>Playlist Builder — Spotify Curator</title>
</svelte:head>

<main class="page playlists-page">
	<header class="page-header">
		<h1>Playlist Builder</h1>
		<p class="muted">Generate local previews from rules. Dry-run only — no Spotify writes in phase 5.</p>
	</header>

	{#if loading}
		<p class="state-msg">Loading…</p>
	{:else if offline}
		<p class="state-msg error">Core offline. {errorMessage}</p>
	{:else}
		{#if errorMessage}
			<p class="state-msg error">{errorMessage}</p>
		{/if}

		<section class="panel">
			<h2>Presets</h2>
			<div class="preset-row">
				<select
					bind:value={selectedPresetId}
					onchange={() => applyPreset(selectedPresetId)}
					disabled={busy}
				>
					{#each presets as p}
						<option value={p.id}>{p.label}</option>
					{/each}
				</select>
			</div>
			{#if selectedPresetDescription}
				<p class="muted preset-hint">{selectedPresetDescription}</p>
			{/if}
		</section>

		<section class="panel">
			<h2>Rule (JSON)</h2>
			<textarea bind:value={ruleJson} rows="18" spellcheck="false" disabled={busy}></textarea>
			<div class="actions">
				<button type="button" onclick={runValidate} disabled={busy}>Validate</button>
				<button type="button" class="primary" onclick={runPreview} disabled={busy}>Generate preview</button>
			</div>
		</section>

		{#if validation}
			<section class="panel">
				<h2>Validation</h2>
				<p class:ok={validation.valid} class:bad={!validation.valid}>
					{validation.valid ? 'Valid' : 'Invalid'}
				</p>
				{#if validation.errors.length}
					<ul class="issues errors">
						{#each validation.errors as issue}
							<li><code>{issue.code}</code> — {issue.message}</li>
						{/each}
					</ul>
				{/if}
				{#if validation.warnings.length}
					<ul class="issues warnings">
						{#each validation.warnings as issue}
							<li><code>{issue.code}</code> — {issue.message}</li>
						{/each}
					</ul>
				{/if}
			</section>
		{/if}

		{#if preview}
			<section class="panel">
				<h2>Preview</h2>
				<p class="muted">
					Candidates: {preview.summary.candidate_count} · Selected: {preview.summary.selected_count}
					· Excluded: {preview.summary.excluded_count}
				</p>
				<table class="preview-table">
					<thead>
						<tr>
							<th>#</th>
							<th>Track</th>
							<th>Artists</th>
							<th>Score</th>
						</tr>
					</thead>
					<tbody>
						{#each preview.items as item}
							<tr>
								<td>{item.position + 1}</td>
								<td>{item.title ?? `Track ${item.track_id}`}</td>
								<td>{(item.artist_names ?? []).join(', ')}</td>
								<td>{item.final_score.toFixed(3)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>

			<section class="panel dry-run-panel">
				<h2>Spotify sync (dry-run only)</h2>
				<label>
					Target Spotify playlist ID
					<input type="text" bind:value={targetPlaylistId} placeholder="Spotify playlist ID" />
				</label>
				<button type="button" onclick={runDryRunSync} disabled={busy}>Run dry-run diff</button>
				{#if syncResult}
					<pre class="diff-json">{JSON.stringify(syncResult.diff, null, 2)}</pre>
					{#if syncResult.warnings.length}
						<ul class="issues warnings">
							{#each syncResult.warnings as w}
								<li>{w}</li>
							{/each}
						</ul>
					{/if}
				{/if}
			</section>
		{/if}
	{/if}
</main>

<style>
	.playlists-page {
		max-width: 960px;
		margin: 0 auto;
		padding: 1.5rem;
	}
	.page-header h1 {
		margin: 0 0 0.25rem;
	}
	.muted {
		color: var(--color-text-muted, #888);
	}
	.panel {
		margin-top: 1.25rem;
		padding: 1rem;
		border: 1px solid var(--color-border, #333);
		border-radius: 8px;
	}
	textarea {
		width: 100%;
		font-family: ui-monospace, monospace;
		font-size: 0.85rem;
	}
	.actions {
		margin-top: 0.75rem;
		display: flex;
		gap: 0.5rem;
	}
	button.primary {
		font-weight: 600;
	}
	.issues {
		font-size: 0.9rem;
	}
	.issues.errors {
		color: #f66;
	}
	.issues.warnings {
		color: #fa0;
	}
	.ok {
		color: #6c6;
	}
	.bad {
		color: #f66;
	}
	.preview-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.9rem;
	}
	.preview-table th,
	.preview-table td {
		text-align: left;
		padding: 0.35rem 0.5rem;
		border-bottom: 1px solid var(--color-border, #333);
	}
	.diff-json {
		font-size: 0.8rem;
		overflow: auto;
		max-height: 240px;
	}
	.dry-run-panel input {
		display: block;
		width: 100%;
		margin: 0.5rem 0;
	}
	.state-msg.error {
		color: #f66;
	}
</style>
