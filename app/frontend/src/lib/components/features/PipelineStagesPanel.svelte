<script lang="ts">
	import type { Job, StageCounts } from '$lib/spotifyApi';

	const STAGE_LABELS: Record<string, string> = {
		segment_download: 'Segment download',
		essentia_lowlevel: 'Essentia low-level',
		essentia_tensorflow_embeddings: 'TF embeddings',
		essentia_tensorflow_classifiers: 'TF classifiers',
		feature_aggregation: 'Feature aggregation',
		audio_cleanup: 'Audio cleanup'
	};

	const STAGE_ORDER = [
		'segment_download',
		'essentia_lowlevel',
		'essentia_tensorflow_embeddings',
		'essentia_tensorflow_classifiers',
		'feature_aggregation',
		'audio_cleanup'
	];

	type Props = {
		job: Job | null;
	};

	let { job }: Props = $props();

	function stageLabel(name: string): string {
		return STAGE_LABELS[name] ?? name.replace(/_/g, ' ');
	}

	function dominantStatus(counts: StageCounts): string {
		if ((counts.failed ?? 0) > 0) return 'failed';
		if ((counts.running ?? 0) > 0) return 'running';
		if ((counts.pending ?? 0) > 0 || (counts.blocked ?? 0) > 0) return 'pending';
		if ((counts.success ?? 0) > 0) return 'success';
		if ((counts.skipped ?? 0) > 0) return 'skipped';
		return '—';
	}

	const rows = $derived.by(() => {
		if (!job?.stages) return [];
		return STAGE_ORDER.filter((k) => job.stages![k]).map((k) => ({
			name: k,
			counts: job.stages![k]
		}));
	});
</script>

{#if job && rows.length > 0}
	<section class="card stages">
		<h3>Pipeline stages</h3>
		<p class="muted">
			Job {job.id.slice(0, 8)}… — {job.status}
			{#if job.current_step}
				· {job.current_step}
			{/if}
		</p>
		<div class="table-sticky-wrap">
			<table>
				<thead>
					<tr>
						<th>Stage</th>
						<th>Status</th>
						<th>OK</th>
						<th>Failed</th>
						<th>Pending</th>
						<th>Skipped</th>
					</tr>
				</thead>
				<tbody>
					{#each rows as row}
						<tr>
							<td>{stageLabel(row.name)}</td>
							<td><strong>{dominantStatus(row.counts)}</strong></td>
							<td>{row.counts.success ?? 0}</td>
							<td>{row.counts.failed ?? 0}</td>
							<td>{(row.counts.pending ?? 0) + (row.counts.blocked ?? 0)}</td>
							<td>{row.counts.skipped ?? 0}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>
{/if}

<style>
	.stages h3 {
		margin-top: 0;
	}
	.stages table {
		width: 100%;
		font-size: 0.9rem;
	}
</style>
