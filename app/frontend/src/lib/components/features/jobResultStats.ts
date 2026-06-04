/** Normalize job result_json for job run stat tiles. */
export type JobRunStats = {
	succeeded?: number;
	failed?: number;
	not_found?: number;
	partial?: number;
	skipped?: number;
	http_batches?: number;
	errors_sample?: { track_id: number; error: string }[];
	track_count?: number;
};

export type StatTileVariant = 'ok' | 'warn' | 'danger' | 'neutral';

export type StatTile = {
	key: string;
	label: string;
	value: number;
	variant?: StatTileVariant;
};

export function jobRunStats(result: Record<string, unknown>): JobRunStats {
	const succeeded = Number(result.succeeded ?? 0);
	const failed = Number(result.failed ?? 0);
	const not_found = Number(result.not_found ?? 0);
	const skipped = Number(result.skipped ?? 0);
	const partial = Number(result.partial ?? 0);
	if (succeeded + failed + not_found + skipped + partial > 0) {
		return {
			succeeded,
			failed,
			not_found,
			skipped,
			partial,
			http_batches: result.http_batches as number | undefined,
			errors_sample: result.errors_sample as JobRunStats['errors_sample'],
			track_count: result.track_count as number | undefined
		};
	}
	return {};
}

export function hasJobRunStats(stats: JobRunStats): boolean {
	return (
		(stats.succeeded ?? 0) +
			(stats.failed ?? 0) +
			(stats.not_found ?? 0) +
			(stats.skipped ?? 0) +
			(stats.partial ?? 0) >
			0
	);
}

export function processedCount(stats: JobRunStats): number {
	return (
		(stats.succeeded ?? 0) +
		(stats.failed ?? 0) +
		(stats.not_found ?? 0) +
		(stats.partial ?? 0) +
		(stats.skipped ?? 0)
	);
}

/** Processed + Succeeded + Failed, plus one optional tile per job type. */
export function statTilesForJob(jobType: string, stats: JobRunStats): StatTile[] {
	const tiles: StatTile[] = [
		{ key: 'processed', label: 'Processed', value: processedCount(stats) },
		{ key: 'succeeded', label: 'Succeeded', value: stats.succeeded ?? 0, variant: 'ok' },
		{ key: 'failed', label: 'Failed', value: stats.failed ?? 0, variant: 'danger' }
	];

	if (jobType === 'reccobeats_enrichment' || jobType === 'preview_resolve') {
		tiles.push({
			key: 'not_found',
			label: jobType === 'preview_resolve' ? 'No preview' : 'Not found',
			value: stats.not_found ?? 0,
			variant: 'warn'
		});
	} else if (
		jobType === 'audio_download' ||
		jobType === 'essentia_lowlevel_analysis' ||
		jobType === 'audio_analysis_pipeline'
	) {
		tiles.push({
			key: 'skipped',
			label: 'Skipped',
			value: stats.skipped ?? 0,
			variant: 'neutral'
		});
	}

	return tiles;
}
