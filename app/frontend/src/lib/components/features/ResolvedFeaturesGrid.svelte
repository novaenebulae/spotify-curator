<script lang="ts">
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import type { ResolvedFeature } from '$lib/featuresApi';

	type Props = {
		features: ResolvedFeature[];
		loading?: boolean;
	};

	let { features, loading = false }: Props = $props();

	function formatValue(f: ResolvedFeature): string {
		if (f.value == null) return '—';
		if (typeof f.value === 'boolean') return f.value ? 'Yes' : 'No';
		if (typeof f.value === 'number') {
			if (f.value >= 0 && f.value <= 1) return f.value.toFixed(3);
			return String(Math.round(f.value * 1000) / 1000);
		}
		return String(f.value);
	}

	function statusVariant(status: string): 'idle' | 'warning' | 'unavailable' | 'neutral' {
		if (status === 'available') return 'idle';
		if (status === 'model_missing' || status === 'missing') return 'warning';
		if (status === 'not_available_yet') return 'neutral';
		if (status === 'source_failed' || status === 'failed') return 'unavailable';
		return 'neutral';
	}

	const available = $derived(features.filter((f) => f.status === 'available'));
	const other = $derived(features.filter((f) => f.status !== 'available'));
</script>

{#if loading}
	<p class="muted">Loading features…</p>
{:else if features.length === 0}
	<p class="muted">No resolved features for this track yet.</p>
	<p class="hint"><a href="/features">Run local analysis on Features →</a></p>
{:else}
	<p class="muted intro">
		Values below follow playlist engine priority (ReccoBeats, Essentia low-level, TensorFlow, metadata).
	</p>
	{#if available.length > 0}
		<h4>Available</h4>
		<div class="grid">
			{#each available as f (f.name)}
				<div class="cell">
					<span class="label">{f.label}</span>
					<span class="value">{formatValue(f)}</span>
					{#if f.confidence != null}
						<span class="conf muted">conf {f.confidence.toFixed(2)}</span>
					{/if}
					<span class="src muted">{f.source ?? '—'}</span>
				</div>
			{/each}
		</div>
	{/if}
	{#if other.length > 0}
		<h4>Missing or unavailable</h4>
		<div class="grid">
			{#each other as f (f.name)}
				<div class="cell dim">
					<span class="label">{f.label}</span>
					<StatusBadge variant={statusVariant(f.status)} label={f.status} />
					{#if f.missing_reason}
						<span class="reason muted">{f.missing_reason}</span>
					{/if}
					{#if f.model_name}
						<span class="reason muted">{f.model_name}</span>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{/if}

<style>
	.intro {
		font-size: 0.9rem;
		margin-bottom: var(--space-md);
	}
	h4 {
		margin: var(--space-md) 0 var(--space-sm);
		font-size: 0.95rem;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
		gap: var(--space-sm);
	}
	.cell {
		padding: 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
	}
	.cell.dim {
		opacity: 0.9;
	}
	.label {
		display: block;
		font-weight: 600;
	}
	.value {
		font-size: 1.05rem;
	}
	.conf,
	.src,
	.reason {
		display: block;
		font-size: 0.75rem;
		margin-top: 0.15rem;
	}
	.hint {
		font-size: 0.9rem;
	}
</style>
