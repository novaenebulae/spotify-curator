<script lang="ts">
	import CollapsibleSection from '$lib/components/common/CollapsibleSection.svelte';
	import { startAdvancedAnalysis, type ModelProfileName } from '$lib/audioApi';
	import { ApiClientError } from '$lib/apiErrors';
	import { jobTracker, trackJob } from '$lib/jobTracker';

	type Props = {
		busy?: boolean;
		modelsReady?: boolean;
		onJobComplete?: () => void | Promise<void>;
	};

	let { busy = false, modelsReady = false, onJobComplete }: Props = $props();

	let limit = $state<number | null>(10);
	let onlyMissing = $state(true);
	let requireRealTf = $state(false);
	let modelProfile = $state<ModelProfileName>('phase6-recommended');
	let analysisMode = $state<'fast' | 'precise'>('fast');
	let useRecentLiked = $state(true);
	let actionError = $state<string | null>(null);
	let actionMessage = $state<string | null>(null);
	let actionBusy = $state(false);

	const trackerBusy = $derived($jobTracker.busy || busy);

	function trackSelectionFilter(): Record<string, unknown> | undefined {
		if (!useRecentLiked) return undefined;
		return { liked: true, sort: 'liked_added_at', order: 'desc' };
	}

	async function runAdvancedPipeline() {
		actionError = null;
		actionMessage = null;
		actionBusy = true;
		jobTracker.update((s) => ({ ...s, error: null }));
		try {
			const opts: Parameters<typeof startAdvancedAnalysis>[0] = {
				only_missing: onlyMissing,
				analysis_mode: analysisMode,
				model_profile: modelProfile,
				require_real_tensorflow: requireRealTf,
				include_tensorflow: true,
				include_lowlevel: true
			};
			const filter = trackSelectionFilter();
			if (filter) opts.filter = filter;
			if (limit != null && limit > 0) opts.limit = limit;
			const { job_id } = await startAdvancedAnalysis(opts);
			actionMessage = 'Advanced pipeline started.';
			await trackJob(job_id, 'Advanced audio pipeline', {
				onComplete: async (job) => {
					if (job.status === 'failed' || job.status === 'error') {
						actionError = job.last_error?.trim() || 'Pipeline failed.';
					}
					await onJobComplete?.();
				}
			});
		} catch (e) {
			if (e instanceof ApiClientError) {
				actionError =
					e.code === 'MODEL_MISSING'
						? `${e.message} Download models above or disable "Require real TensorFlow".`
						: e.message;
			} else {
				actionError = e instanceof Error ? e.message : String(e);
			}
		} finally {
			actionBusy = false;
		}
	}
</script>

<CollapsibleSection title="Advanced audio pipeline" storageKey="features_advanced_pipeline_open">
	<p class="muted intro">
		Runs segment download, Essentia low-level, TensorFlow (embeddings, moods, genre), aggregation and
		cleanup in parallel. Requires Docker profiles <code>audio</code> and
		<code>advanced-analysis</code>.
	</p>

	<div class="form-grid">
		<label>
			Limit tracks
			<input type="number" min="1" max="500" bind:value={limit} />
		</label>
		<label class="check">
			<input type="checkbox" bind:checked={onlyMissing} />
			Only tracks missing advanced features
		</label>
		<label class="check">
			<input type="checkbox" bind:checked={useRecentLiked} />
			Recent liked tracks only
		</label>
		<label>
			Analysis mode
			<select bind:value={analysisMode}>
				<option value="fast">Fast</option>
				<option value="precise">Precise</option>
			</select>
		</label>
		<label>
			Model profile
			<select bind:value={modelProfile}>
				<option value="phase6-minimal">phase6-minimal</option>
				<option value="phase6-recommended">phase6-recommended</option>
				<option value="phase6-full">phase6-full</option>
			</select>
		</label>
		<label class="check">
			<input type="checkbox" bind:checked={requireRealTf} />
			Require real TensorFlow (blocks if models missing)
		</label>
	</div>

	{#if !modelsReady && requireRealTf}
		<p class="warn">Models are not ready for real inference. Uncheck the option above or download a profile.</p>
	{/if}

	<button
		type="button"
		disabled={trackerBusy || actionBusy}
		onclick={runAdvancedPipeline}
	>
		{actionBusy || trackerBusy ? 'Running…' : 'Run advanced pipeline'}
	</button>

	{#if actionMessage}
		<p class="muted">{actionMessage}</p>
	{/if}
	{#if actionError}
		<pre class="error">{actionError}</pre>
	{/if}
</CollapsibleSection>

<style>
	.intro {
		margin-bottom: var(--space-md);
		font-size: 0.9rem;
	}
	.form-grid {
		display: grid;
		gap: var(--space-sm);
		margin-bottom: var(--space-md);
	}
	label.check {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.warn {
		color: var(--color-warn, #ca8);
		font-size: 0.9rem;
		margin-bottom: var(--space-sm);
	}
</style>
