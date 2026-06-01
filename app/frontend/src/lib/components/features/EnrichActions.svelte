<script lang="ts">
	type Props = {
		busy?: boolean;
		batchSize?: number;
		limit?: number | null;
		onBatchSizeChange?: (n: number) => void;
		onLimitChange?: (n: number | null) => void;
		onEnrichMissing?: () => void;
		onRetryFailed?: () => void;
		onForceRefresh?: () => void;
	};

	let {
		busy = false,
		batchSize = 50,
		limit = null,
		onBatchSizeChange,
		onLimitChange,
		onEnrichMissing,
		onRetryFailed,
		onForceRefresh
	}: Props = $props();

	let confirmRefresh = $state(false);

	function handleForceRefresh() {
		if (!confirmRefresh) {
			confirmRefresh = true;
			return;
		}
		confirmRefresh = false;
		onForceRefresh?.();
	}
</script>

<section class="card">
	<h2>Enrichment actions</h2>
	<p class="muted">
		ReccoBeats enrichment runs as a background job (up to 40 tracks per API request). “Batch
		size” below is only the pause interval between groups of processed tracks, not the HTTP batch
		size.
	</p>

	<div class="row actions">
		<button type="button" disabled={busy} onclick={() => onEnrichMissing?.()}>
			Enrich missing tracks
		</button>
		<button type="button" class="secondary" disabled={busy} onclick={() => onRetryFailed?.()}>
			Retry failed
		</button>
		<button
			type="button"
			class={confirmRefresh ? 'danger' : 'secondary'}
			disabled={busy}
			onclick={handleForceRefresh}
		>
			{confirmRefresh ? 'Confirm force refresh' : 'Force refresh all'}
		</button>
		{#if confirmRefresh}
			<button type="button" class="secondary" disabled={busy} onclick={() => (confirmRefresh = false)}>
				Cancel
			</button>
		{/if}
	</div>

	<div class="row filters">
		<label>
			Batch size
			<input
				type="number"
				min="1"
				max="500"
				value={batchSize}
				disabled={busy}
				onchange={(e) => onBatchSizeChange?.(Number(e.currentTarget.value))}
			/>
		</label>
		<label>
			Limit (tests)
			<input
				type="number"
				min="1"
				placeholder="All"
				value={limit ?? ''}
				disabled={busy}
				onchange={(e) => {
					const v = e.currentTarget.value;
					onLimitChange?.(v ? Number(v) : null);
				}}
			/>
		</label>
	</div>
</section>

<style>
	.filters label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		font-size: 0.85rem;
	}
	.filters input {
		width: 6rem;
	}
	button.danger {
		background: var(--color-danger, #c44);
	}
</style>
