<script lang="ts">
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import { downloadProfile, type ModelsStatusResponse } from '$lib/modelsApi';
	import { ApiClientError } from '$lib/apiErrors';

	type Props = {
		status: ModelsStatusResponse | null;
		loading?: boolean;
		error?: string | null;
		onRefresh?: () => void | Promise<void>;
	};

	let { status, loading = false, error = null, onRefresh }: Props = $props();

	let acceptLicense = $state(false);
	let downloadBusy = $state(false);
	let downloadError = $state<string | null>(null);
	let downloadMessage = $state<string | null>(null);
	let selectedProfile = $state('phase6-recommended');

	const missingModels = $derived(
		status?.models.filter((m) => m.status === 'missing').slice(0, 12) ?? []
	);

	async function confirmDownload() {
		if (!acceptLicense) {
			downloadError = 'You must accept the CC BY-NC-SA 4.0 license before downloading.';
			return;
		}
		const ok = confirm(
			`Download profile "${selectedProfile}"? This may take several minutes and download large files.`
		);
		if (!ok) return;
		downloadBusy = true;
		downloadError = null;
		downloadMessage = null;
		try {
			const res = await downloadProfile(selectedProfile, { accept_license: true });
			downloadMessage = `Profile ${res.profile}: ${res.models.length} model(s) processed.`;
			await onRefresh?.();
		} catch (e) {
			if (e instanceof ApiClientError) downloadError = e.message;
			else downloadError = e instanceof Error ? e.message : String(e);
		} finally {
			downloadBusy = false;
		}
	}
</script>

<CollapsibleSection title="Essentia TensorFlow models" storageKey="features_models_open">
	{#if loading}
		<p class="muted">Loading model status…</p>
	{:else if error}
		<p class="error">{error}</p>
		{#if onRefresh}
			<button type="button" class="secondary" onclick={() => onRefresh?.()}>Retry</button>
		{/if}
	{:else if status}
		<div class="summary-row">
			<p>
				<strong>{status.summary.available}</strong> / {status.summary.total} available ·
				<StatusBadge
					variant={status.summary.real_inference_ready ? 'idle' : 'warning'}
					label={status.summary.real_inference_ready ? 'Inference ready' : 'Inference not ready'}
				/>
			</p>
			{#if onRefresh}
				<button type="button" class="secondary" onclick={() => onRefresh?.()}>Refresh</button>
			{/if}
		</div>

		<div class="profiles">
			{#each status.profiles as p}
				<div class="profile-chip">
					<strong>{p.name}</strong>
					<span class="muted">{p.available_count}/{p.available_count + p.missing_count}</span>
					<StatusBadge variant={p.status === 'available' ? 'idle' : 'warning'} label={p.status} />
				</div>
			{/each}
		</div>

		{#if missingModels.length > 0}
			<details class="missing-details">
				<summary>Missing models ({status.summary.missing})</summary>
				<ul>
					{#each missingModels as m}
						<li>{m.display_name}</li>
					{/each}
					{#if status.summary.missing > missingModels.length}
						<li class="muted">…and {status.summary.missing - missingModels.length} more</li>
					{/if}
				</ul>
			</details>
		{/if}

		<div class="download-box">
			<p class="muted license">
				Models are licensed under <strong>CC BY-NC-SA 4.0</strong>. Downloads are stored locally only
				(not committed to Git).
			</p>
			<label class="license-check">
				<input type="checkbox" bind:checked={acceptLicense} />
				I accept the license terms for Essentia model downloads
			</label>
			<div class="download-row">
				<select bind:value={selectedProfile} disabled={downloadBusy}>
					<option value="phase6-minimal">phase6-minimal</option>
					<option value="phase6-recommended">phase6-recommended</option>
					<option value="phase6-full">phase6-full</option>
				</select>
				<button type="button" disabled={downloadBusy || !acceptLicense} onclick={confirmDownload}>
					{downloadBusy ? 'Downloading…' : 'Download profile'}
				</button>
			</div>
			<p class="muted hint">Download can take several minutes. Keep Docker running.</p>
			{#if downloadMessage}
				<p class="ok-msg">{downloadMessage}</p>
			{/if}
			{#if downloadError}
				<p class="error">{downloadError}</p>
			{/if}
		</div>
	{:else}
		<p class="muted">No model status available.</p>
	{/if}
</CollapsibleSection>

<style>
	.summary-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		flex-wrap: wrap;
		margin-bottom: var(--space-md);
	}
	.profiles {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-sm);
		margin-bottom: var(--space-md);
	}
	.profile-chip {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.65rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
	}
	.missing-details {
		margin-bottom: var(--space-md);
	}
	.missing-details ul {
		margin: 0.5rem 0 0 1.25rem;
		font-size: 0.9rem;
	}
	.download-box {
		margin-top: var(--space-md);
		padding-top: var(--space-md);
		border-top: 1px solid var(--color-border);
	}
	.license-check {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		margin: var(--space-sm) 0;
	}
	.download-row {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-sm);
		align-items: center;
	}
	.hint {
		font-size: 0.85rem;
	}
	.ok-msg {
		color: var(--color-ok, #6c6);
	}
</style>
