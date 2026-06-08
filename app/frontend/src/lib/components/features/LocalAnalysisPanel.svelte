<script lang="ts">
	import {
		downloadMissingSegments,
		runLowlevelAnalysis,
		startAdvancedAnalysis,
		type ModelProfileName
	} from '$lib/audioApi';
	import { profileDisplayName, profileModelsFor } from '$lib/profileLabels';
	import type { ModelsStatusResponse } from '$lib/modelsApi';
	import { ApiClientError } from '$lib/apiErrors';
	import { jobTracker, trackJob } from '$lib/jobTracker';

	type Props = {
		busy?: boolean;
		modelsStatus?: ModelsStatusResponse | null;
		onJobComplete?: () => void | Promise<void>;
	};

	let { busy = false, modelsStatus = null, onJobComplete }: Props = $props();

	let fullLibrary = $state(true);
	let limit = $state<number | null>(10);
	let onlyMissing = $state(true);
	let modelProfile = $state<ModelProfileName>('phase6-recommended');
	let analysisMode = $state<'fast' | 'precise'>('fast');
	let useRecentLiked = $state(true);
	let showPowerUser = $state(false);
	let actionError = $state<string | null>(null);
	let actionMessage = $state<string | null>(null);
	let actionBusy = $state(false);

	const trackerBusy = $derived($jobTracker.busy || busy);

	const profileModelNames = $derived(
		modelsStatus
			? profileModelsFor(modelProfile, modelsStatus.models)
			: []
	);

	function trackSelectionFilter(): Record<string, unknown> | undefined {
		if (!useRecentLiked) return undefined;
		return { liked: true, sort: 'liked_added_at', order: 'desc' };
	}

	function applyTrackScope(opts: {
		limit?: number;
		filter?: Record<string, unknown>;
	}): void {
		if (fullLibrary) {
			return;
		}
		const filter = trackSelectionFilter();
		if (filter) opts.filter = filter;
		if (limit != null && limit > 0) opts.limit = limit;
	}

	function jobOpts(): {
		analysis_mode: 'fast' | 'precise';
		limit?: number;
		only_missing?: boolean;
		filter?: Record<string, unknown>;
	} {
		const opts: {
			analysis_mode: 'fast' | 'precise';
			limit?: number;
			only_missing?: boolean;
			filter?: Record<string, unknown>;
		} = { analysis_mode: analysisMode, only_missing: onlyMissing };
		applyTrackScope(opts);
		return opts;
	}

	function formatJobError(e: unknown): string {
		if (e instanceof ApiClientError) {
			const msg = e.message.replace(/\s*\(\d{3}\)\s*$/, '');
			if (e.code === 'NO_TRACKS') {
				return `${msg} Try disabling "Only missing", increasing the limit, or selecting tracks that still need analysis.`;
			}
			if (e.code === 'JOB_ALREADY_RUNNING') {
				return `${msg} Wait for the current job to finish or cancel it from the progress bar above.`;
			}
			if (e.code === 'MODEL_MISSING') {
				return `${msg} Download the model profile below, then retry.`;
			}
			return msg;
		}
		return e instanceof Error ? e.message : String(e);
	}

	async function runFullLocalAnalysis() {
		actionError = null;
		actionMessage = null;
		actionBusy = true;
		jobTracker.update((s) => ({ ...s, error: null }));
		try {
			const opts: Parameters<typeof startAdvancedAnalysis>[0] = {
				only_missing: onlyMissing,
				analysis_mode: analysisMode,
				model_profile: modelProfile,
				require_real_tensorflow: true,
				include_tensorflow: true,
				include_lowlevel: true
			};
			applyTrackScope(opts);
			const { job_id } = await startAdvancedAnalysis(opts);
			actionMessage = 'Local analysis pipeline started.';
			await trackJob(job_id, 'Local analysis pipeline', {
				onComplete: async (job) => {
					if (job.status === 'failed' || job.status === 'error') {
						actionError =
							job.last_error?.trim() ||
							'Pipeline failed. Check models and Docker workers on Features page.';
					}
					await onJobComplete?.();
				}
			});
		} catch (e) {
			actionError = formatJobError(e);
		} finally {
			actionBusy = false;
		}
	}

	async function runLegacyJob(
		label: string,
		startFn: (opts: ReturnType<typeof jobOpts>) => Promise<{ job_id: string }>
	) {
		actionBusy = true;
		actionError = null;
		try {
			const { job_id } = await startFn(jobOpts());
			await trackJob(job_id, label, { onComplete: () => onJobComplete?.() });
			actionMessage = `${label} finished.`;
		} catch (e) {
			actionError = e instanceof Error ? e.message : String(e);
		} finally {
			actionBusy = false;
		}
	}
</script>

<section class="card local-analysis">
	<h2>Local analysis</h2>
	<p class="muted intro">
		<strong>Complete local analysis</strong> runs segment download, Essentia low-level, TensorFlow
		(moods, genre, embeddings), aggregation and cleanup. Requires Docker profiles
		<code>audio</code> and <code>advanced-analysis</code>.
	</p>

	<label class="checkbox-row">
		<input type="checkbox" bind:checked={fullLibrary} />
		<span>Full library (all tracks with incomplete local analysis, max 10 000 per job)</span>
	</label>

	{#if !fullLibrary}
		<label class="limit-row">
			<span>Limit (tracks)</span>
			<input type="number" min="1" bind:value={limit} />
		</label>

		<label class="checkbox-row">
			<input type="checkbox" bind:checked={useRecentLiked} />
			<span>Target: most recently liked tracks</span>
		</label>
	{/if}

	<label class="checkbox-row">
		<input type="checkbox" bind:checked={onlyMissing} />
		<span>Only missing (skip tracks already analysed)</span>
	</label>
	<label class="checkbox-row">
		<input
			type="checkbox"
			checked={analysisMode === 'precise'}
			onchange={(e) =>
				(analysisMode = (e.currentTarget as HTMLInputElement).checked ? 'precise' : 'fast')}
		/>
		<span>Mode: {analysisMode === 'fast' ? 'Fast (1 segment)' : 'Precise (3 segments)'}</span>
	</label>

	<label class="profile-row">
		<span>Model profile</span>
		<select bind:value={modelProfile}>
			<option value="phase6-minimal">{profileDisplayName('phase6-minimal')}</option>
			<option value="phase6-recommended">{profileDisplayName('phase6-recommended')}</option>
			<option value="phase6-full">{profileDisplayName('phase6-full')}</option>
		</select>
	</label>
	{#if profileModelNames.length > 0}
		<p class="muted profile-models">{profileModelNames.join(' · ')}</p>
	{/if}

	<div class="actions">
		<button
			type="button"
			class="primary"
			disabled={actionBusy || trackerBusy}
			onclick={runFullLocalAnalysis}
		>
			Run complete local analysis
		</button>
	</div>

	{#if actionError}
		<p class="error">{actionError}</p>
	{:else if actionMessage}
		<p class="message">{actionMessage}</p>
	{/if}

	<details class="power-user" bind:open={showPowerUser}>
		<summary>Optional steps (power user)</summary>
		<div class="power-actions">
			<button
				type="button"
				class="secondary"
				disabled={actionBusy || trackerBusy}
				onclick={() => runLegacyJob('Download segments', downloadMissingSegments)}
			>
				Download segments only
			</button>
			<button
				type="button"
				class="secondary"
				disabled={actionBusy || trackerBusy}
				onclick={() => runLegacyJob('Essentia low-level', runLowlevelAnalysis)}
			>
				Low-level only
			</button>
		</div>
	</details>
</section>

<style>
	.local-analysis h2 {
		margin-top: 0;
		font-size: 1.25rem;
	}
	.intro {
		margin-bottom: var(--space-md);
		font-size: 0.9rem;
	}
	.limit-row,
	.profile-row,
	.checkbox-row {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		margin: 0.75rem 0;
		flex-wrap: wrap;
	}
	.checkbox-row {
		font-size: 0.9rem;
		color: var(--color-muted);
	}
	.profile-models {
		font-size: 0.8rem;
		margin: -0.25rem 0 var(--space-md);
	}
	.actions .primary {
		font-weight: 600;
	}
	.power-user {
		margin-top: var(--space-md);
		font-size: 0.9rem;
	}
	.power-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 0.5rem;
	}
	.error {
		color: var(--color-danger);
	}
	.message {
		margin-top: 0.5rem;
	}
</style>
