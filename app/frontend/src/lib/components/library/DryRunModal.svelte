<script lang="ts">
	import type { DryRunResponse } from '$lib/libraryApi';

	let {
		open,
		result,
		actionLabel,
		onClose
	}: {
		open: boolean;
		result: DryRunResponse | null;
		actionLabel: string;
		onClose: () => void;
	} = $props();
</script>

{#if open && result}
	<div class="modal-backdrop" role="presentation" onclick={onClose}>
		<div class="modal card" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()}>
			<h2>Dry-run — {actionLabel}</h2>
			<p class="muted">Preview only. No Spotify changes are applied in phase 2.</p>
			<p><strong>{result.affected_count}</strong> track(s) affected</p>
			{#if result.warnings.length}
				<div class="warn-box">
					<h3>Warnings</h3>
					<ul>
						{#each result.warnings as w}
							<li><code>{w.code}</code> — {w.message}</li>
						{/each}
					</ul>
				</div>
			{/if}
			<ul class="track-list">
				{#each result.affected_tracks.slice(0, 20) as t}
					<li>{t.title} — {t.artist_names.join(', ')}</li>
				{/each}
				{#if result.affected_tracks.length > 20}
					<li class="muted">… and {result.affected_tracks.length - 20} more</li>
				{/if}
			</ul>
			<div class="row actions">
				<button type="button" onclick={onClose}>Close</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.65);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: 1rem;
	}
	.modal {
		max-width: 560px;
		width: 100%;
		max-height: 90vh;
		overflow: auto;
	}
	.warn-box {
		background: #2a2210;
		padding: 0.75rem;
		border-radius: 6px;
		margin: 0.75rem 0;
	}
	.track-list {
		max-height: 200px;
		overflow: auto;
		padding-left: 1.25rem;
	}
</style>
