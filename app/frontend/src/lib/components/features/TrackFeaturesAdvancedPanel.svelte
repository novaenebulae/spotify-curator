<script lang="ts">
	import StatusBadge from '$lib/components/common/StatusBadge.svelte';
	import { getTrackFeatures, type TrackFeaturesResponse } from '$lib/featuresApi';
	import { formatPercent } from '$lib/featureFormat';

	type Props = {
		data: TrackFeaturesResponse | null;
		trackId: number;
		loading?: boolean;
		error?: string | null;
		offline?: boolean;
	};

	let { data, trackId, loading = false, error = null, offline = false }: Props = $props();

	let showVector = $state(false);
	let vectorLoading = $state(false);
	let vectorError = $state<string | null>(null);
	let vectorSample = $state<number[] | null>(null);

	const advanced = $derived(data?.advanced ?? null);

	const moodFeatures = $derived(
		advanced?.scalar_features.filter(
			(f) =>
				f.feature_name.startsWith('mood_') ||
				f.feature_name.includes('voice_') ||
				f.feature_name.includes('danceability') ||
				f.feature_name.includes('approachability') ||
				f.feature_name.includes('engagement') ||
				f.feature_name.includes('acoustic') ||
				f.feature_name.includes('electronic')
		) ?? []
	);

	function formatScalarValue(f: { value?: number | string | null }): string {
		if (f.value == null) return '—';
		if (typeof f.value === 'number' && f.value >= 0 && f.value <= 1) {
			return formatPercent(f.value) ?? String(f.value);
		}
		return String(f.value);
	}

	function statusVariant(status: string): 'idle' | 'warning' | 'unavailable' | 'neutral' {
		if (status === 'success' || status === 'available') return 'idle';
		if (status === 'model_missing' || status === 'missing') return 'warning';
		if (status === 'failed') return 'unavailable';
		return 'neutral';
	}

	async function loadVectorSample() {
		if (!showVector) {
			vectorSample = null;
			vectorError = null;
			return;
		}
		vectorLoading = true;
		vectorError = null;
		try {
			const res = await getTrackFeatures(trackId, { include_embedding_vector: true });
			vectorSample = res.advanced?.embedding?.vector?.slice(0, 16) ?? null;
			if (!vectorSample?.length) {
				vectorError = 'No embedding vector in response.';
			}
		} catch (e) {
			vectorError = e instanceof Error ? e.message : String(e);
		} finally {
			vectorLoading = false;
		}
	}

	$effect(() => {
		if (showVector) void loadVectorSample();
	});
</script>

{#if offline}
	<p class="error">Cannot reach the core API. Start Docker to load advanced features.</p>
{:else if loading}
	<p class="muted">Loading advanced features…</p>
{:else if error}
	<p class="error">{error}</p>
{:else if !advanced}
	<p class="muted">Advanced analysis not run for this track.</p>
	<p><a href="/features">Run advanced pipeline on Features →</a></p>
{:else}
	<p class="row-meta">
		<StatusBadge variant={statusVariant(advanced.status)} label={advanced.status} />
		<span class="muted">{advanced.display_name}</span>
	</p>

	{#if moodFeatures.length > 0}
		<h4>Moods & classifiers</h4>
		<div class="metric-grid">
			{#each moodFeatures as f}
				<div class="metric" class:missing={f.status === 'model_missing' || f.status === 'missing'}>
					<span class="name">{f.feature_name.replace(/_/g, ' ')}</span>
					<span class="value">{formatScalarValue(f)}</span>
					<StatusBadge variant={statusVariant(f.status)} label={f.status} />
					{#if f.missing_reason}
						<p class="reason muted">{f.missing_reason}</p>
					{:else if f.model_name}
						<p class="reason muted">{f.model_name}</p>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<p class="muted">No scalar TensorFlow features yet.</p>
	{/if}

	{#if advanced.genre}
		<h4>Genre (Discogs519)</h4>
		{#if advanced.genre.label}
			<p>
				<strong>{advanced.genre.label}</strong>
				{#if advanced.genre.score != null}
					<span class="muted">({(advanced.genre.score * 100).toFixed(1)}%)</span>
				{/if}
			</p>
		{/if}
		{#if advanced.genre.top_k?.length}
			<details>
				<summary>Top {advanced.genre.top_k.length} labels</summary>
				<ul>
					{#each advanced.genre.top_k as item}
						<li>
							{item.label ?? '—'}
							{#if item.score != null}
								<span class="muted">{(item.score * 100).toFixed(1)}%</span>
							{/if}
						</li>
					{/each}
				</ul>
			</details>
		{:else if !advanced.genre.label}
			<p class="muted">Genre not available (model missing or segment too short).</p>
		{/if}
	{/if}

	{#if advanced.embedding}
		<h4>Embedding</h4>
		<div class="embed-meta">
			<StatusBadge variant={statusVariant(advanced.embedding.status)} label={advanced.embedding.status} />
			{#if advanced.embedding.model_name}
				<span class="muted">{advanced.embedding.model_name}</span>
			{/if}
			{#if advanced.embedding.dimension}
				<span class="muted">dim {advanced.embedding.dimension}</span>
			{/if}
			{#if advanced.embedding.segments_used != null}
				<span class="muted">{advanced.embedding.segments_used} segment(s)</span>
			{/if}
		</div>
		<label class="vector-toggle">
			<input type="checkbox" bind:checked={showVector} />
			Show vector sample (first 16 values; large payload)
		</label>
		{#if showVector}
			{#if vectorLoading}
				<p class="muted">Loading vector…</p>
			{:else if vectorError}
				<p class="error">{vectorError}</p>
			{:else if vectorSample}
				<details>
					<summary>Vector sample</summary>
					<pre class="vector-pre">{JSON.stringify(vectorSample, null, 2)}</pre>
				</details>
			{/if}
		{/if}
	{/if}
{/if}

<style>
	.row-meta {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-bottom: var(--space-md);
	}
	h4 {
		margin: var(--space-md) 0 var(--space-sm);
		font-size: 0.95rem;
	}
	.metric-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
		gap: var(--space-sm);
	}
	.metric {
		padding: 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
	}
	.metric.missing {
		border-color: var(--color-warn, #a80);
	}
	.metric .name {
		display: block;
		font-weight: 600;
		text-transform: capitalize;
	}
	.metric .value {
		font-size: 1.1rem;
	}
	.reason {
		margin: 0.25rem 0 0;
		font-size: 0.75rem;
	}
	.embed-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		align-items: center;
		margin-bottom: var(--space-sm);
	}
	.vector-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.85rem;
	}
	.vector-pre {
		font-size: 0.75rem;
		max-height: 8rem;
		overflow: auto;
	}
	ul {
		margin: 0.5rem 0 0 1.25rem;
		font-size: 0.9rem;
	}
</style>
