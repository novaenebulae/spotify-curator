<script lang="ts">
	type EnrichStats = {
		succeeded?: number;
		failed?: number;
		not_found?: number;
		partial?: number;
		skipped?: number;
		http_batches?: number;
		errors_sample?: { track_id: number; error: string }[];
	};

	type Props = {
		result: Record<string, unknown>;
		status: string;
	};

	let { result, status }: Props = $props();

	const stats = $derived(result as EnrichStats);

	const processed = $derived(
		(stats.succeeded ?? 0) +
			(stats.failed ?? 0) +
			(stats.not_found ?? 0) +
			(stats.partial ?? 0) +
			(stats.skipped ?? 0)
	);
</script>

<div class="enrich-result">
	<p class="muted note">
		These counts apply to <strong>this job run only</strong>. Library coverage cards above reflect
		your full database (including tracks not processed in this run).
	</p>

	<div class="stat-grid">
		<div class="stat-card">
			<h3>Processed</h3>
			<p class="stat-value">{processed.toLocaleString()}</p>
		</div>
		<div class="stat-card stat-ok">
			<h3>Succeeded</h3>
			<p class="stat-value">{(stats.succeeded ?? 0).toLocaleString()}</p>
			<p class="muted">Features saved</p>
		</div>
		<div class="stat-card stat-warn">
			<h3>Not on ReccoBeats</h3>
			<p class="stat-value">{(stats.not_found ?? 0).toLocaleString()}</p>
			<p class="muted">No match this run</p>
		</div>
		<div class="stat-card stat-danger">
			<h3>Failed</h3>
			<p class="stat-value">{(stats.failed ?? 0).toLocaleString()}</p>
			<p class="muted">API or network errors</p>
		</div>
		<div class="stat-card">
			<h3>Partial</h3>
			<p class="stat-value">{(stats.partial ?? 0).toLocaleString()}</p>
		</div>
		<div class="stat-card">
			<h3>Skipped</h3>
			<p class="stat-value">{(stats.skipped ?? 0).toLocaleString()}</p>
			<p class="muted">No Spotify ID</p>
		</div>
		{#if stats.http_batches != null}
			<div class="stat-card">
				<h3>API batches</h3>
				<p class="stat-value">{stats.http_batches.toLocaleString()}</p>
				<p class="muted">Up to 40 tracks per request</p>
			</div>
		{/if}
	</div>

	{#if status === 'cancelled'}
		<p class="muted">Job was cancelled before completion. Counts may be partial.</p>
	{/if}

	{#if stats.errors_sample && stats.errors_sample.length > 0}
		<h4 class="errors-title">Sample errors</h4>
		<ul class="error-list">
			{#each stats.errors_sample as sample}
				<li>
					<span class="track-id">Track #{sample.track_id}</span>
					<span class="error-msg">{sample.error}</span>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.note {
		margin-top: 0;
		font-size: 0.9rem;
	}
	.stat-ok .stat-value {
		color: var(--color-success);
	}
	.stat-warn .stat-value {
		color: var(--color-warning);
	}
	.stat-danger .stat-value {
		color: var(--color-danger);
	}
	.errors-title {
		margin: var(--space-lg) 0 var(--space-sm);
		font-size: 0.95rem;
	}
	.error-list {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.error-list li {
		padding: var(--space-sm) var(--space-md);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		margin-bottom: var(--space-xs);
		background: var(--color-surface-elevated);
	}
	.track-id {
		display: block;
		font-weight: 600;
		font-size: 0.85rem;
	}
	.error-msg {
		color: var(--color-muted);
		font-size: 0.85rem;
	}
</style>
