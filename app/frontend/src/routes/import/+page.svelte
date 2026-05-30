<script lang="ts">
	import { onDestroy } from 'svelte';
	import AuthStatusCard from '$lib/components/import/AuthStatusCard.svelte';
	import ExportPanel from '$lib/components/import/ExportPanel.svelte';
	import JobProgress from '$lib/components/import/JobProgress.svelte';
	import LastRunSummary from '$lib/components/import/LastRunSummary.svelte';
	import SnapshotPanel from '$lib/components/import/SnapshotPanel.svelte';
	import { pollJobUntilDone } from '$lib/jobPoller';
	import {
		createSnapshot,
		diffSnapshots,
		fetchAuthStatus,
		importLikedTracks,
		importPlaylists,
		listSnapshots,
		logout,
		startAuth,
		type AuthStatus,
		type DiffResult,
		type Job,
		type SnapshotMeta
	} from '$lib/spotifyApi';

	let auth: AuthStatus | null = $state(null);
	let authLoading = $state(true);
	let authError: string | null = $state(null);

	let busy = $state(false);
	let activeJob: Job | null = $state(null);
	let lastJob: Job | null = $state(null);
	let actionError: string | null = $state(null);

	let snapshots: SnapshotMeta[] = $state([]);
	let snapshotsLoading = $state(false);
	let snapshotError: string | null = $state(null);

	let fromSnapshotId = $state('');
	let toSnapshotId = $state('');
	let diff: DiffResult | null = $state(null);
	let diffLoading = $state(false);
	let diffError: string | null = $state(null);

	const controller = new AbortController();

	async function refreshAuth(): Promise<void> {
		authLoading = true;
		authError = null;
		try {
			auth = await fetchAuthStatus(controller.signal);
		} catch (e) {
			auth = null;
			authError = e instanceof Error ? e.message : String(e);
		} finally {
			authLoading = false;
		}
	}

	async function refreshSnapshots(): Promise<void> {
		snapshotsLoading = true;
		snapshotError = null;
		try {
			snapshots = await listSnapshots(controller.signal);
			if (!fromSnapshotId && snapshots.length >= 2) {
				fromSnapshotId = snapshots[1].id;
				toSnapshotId = snapshots[0].id;
			}
		} catch (e) {
			snapshotError = e instanceof Error ? e.message : String(e);
		} finally {
			snapshotsLoading = false;
		}
	}

	async function connect(): Promise<void> {
		busy = true;
		actionError = null;
		try {
			const start = await startAuth(controller.signal);
			window.open(start.authorize_url, '_blank', 'noopener,noreferrer');
		} catch (e) {
			actionError = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function disconnect(): Promise<void> {
		busy = true;
		actionError = null;
		try {
			await logout(controller.signal);
			await refreshAuth();
		} catch (e) {
			actionError = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function runJob(startFn: () => Promise<{ job_id: string }>, label: string): Promise<void> {
		busy = true;
		actionError = null;
		activeJob = null;
		try {
			const { job_id } = await startFn();
			const final = await pollJobUntilDone(
				job_id,
				(job) => {
					activeJob = job;
				},
				{ signal: controller.signal }
			);
			lastJob = final;
			activeJob = null;
			if (final.status === 'failed') {
				actionError = `${label} failed: ${final.last_error || 'Unknown error'}`;
			}
		} catch (e) {
			actionError = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function importLiked(): Promise<void> {
		await runJob(() => importLikedTracks(controller.signal), 'Liked tracks import');
	}

	async function importPlaylistsAction(): Promise<void> {
		await runJob(() => importPlaylists(controller.signal), 'Playlists import');
	}

	async function createSnap(type: 'full' | 'liked' | 'playlists'): Promise<void> {
		busy = true;
		snapshotError = null;
		try {
			await createSnapshot(type, controller.signal);
			await refreshSnapshots();
		} catch (e) {
			snapshotError = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	async function compareSnapshots(): Promise<void> {
		diffLoading = true;
		diffError = null;
		diff = null;
		try {
			diff = await diffSnapshots(fromSnapshotId, toSnapshotId, controller.signal);
		} catch (e) {
			diffError = e instanceof Error ? e.message : String(e);
		} finally {
			diffLoading = false;
		}
	}

	refreshAuth();
	refreshSnapshots();
	onDestroy(() => controller.abort());
</script>

<main class="import-page">
	<header>
		<h1>Import library</h1>
		<p class="muted">Back up your Spotify library locally via the core API on 127.0.0.1:8765.</p>
	</header>

	<AuthStatusCard
		{auth}
		loading={authLoading}
		error={authError}
		onConnect={connect}
		onDisconnect={disconnect}
		{busy}
	/>

	<section class="card">
		<h2>Import actions</h2>
		<p class="muted">Imports run as background jobs. Progress updates automatically.</p>
		<div class="row actions">
			<button type="button" onclick={importLiked} disabled={busy || !auth?.connected}>
				Import liked tracks
			</button>
			<button type="button" onclick={importPlaylistsAction} disabled={busy || !auth?.connected}>
				Import playlists
			</button>
			<button type="button" class="secondary" onclick={refreshAuth} disabled={busy}>
				Refresh auth status
			</button>
		</div>
		{#if !auth?.connected && !authLoading}
			<p class="warn">Connect Spotify before running imports.</p>
		{/if}
		{#if actionError}
			<pre class="error">{actionError}</pre>
		{/if}
	</section>

	<JobProgress job={activeJob} label="Running job" />
	<LastRunSummary job={lastJob} />

	<SnapshotPanel
		{snapshots}
		loading={snapshotsLoading}
		{busy}
		error={snapshotError}
		{diff}
		{diffLoading}
		{diffError}
		fromId={fromSnapshotId}
		toId={toSnapshotId}
		onFromChange={(id) => (fromSnapshotId = id)}
		onToChange={(id) => (toSnapshotId = id)}
		onRefresh={refreshSnapshots}
		onCreate={createSnap}
		onCompare={compareSnapshots}
	/>

	<ExportPanel
		busy={busy}
		{fromSnapshotId}
		{toSnapshotId}
		latestSnapshotId={snapshots[0]?.id ?? ''}
	/>
</main>
