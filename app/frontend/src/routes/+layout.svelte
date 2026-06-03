<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import favicon from '$lib/assets/favicon.svg';
	import GlobalJobBar from '$lib/components/common/GlobalJobBar.svelte';
	import { resumeTrackedJobIfAny } from '$lib/jobTracker';
	import '../app.css';

	let { children } = $props();

	onMount(() => {
		void resumeTrackedJobIfAny();
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="app-shell">
	<nav class="app-nav">
		<a href="/" class="app-nav-brand">Spotify Curator</a>
		<a href="/" class:active={$page.url.pathname === '/'}>Home</a>
		<a href="/import" class:active={$page.url.pathname.startsWith('/import')}>Import</a>
		<a href="/library" class:active={$page.url.pathname.startsWith('/library')}>Library</a>
		<a href="/features" class:active={$page.url.pathname.startsWith('/features')}>Features</a>
		<a href="/playlists" class:active={$page.url.pathname.startsWith('/playlists')}>Playlists</a>
		<a href="/settings" class:active={$page.url.pathname.startsWith('/settings')}>Settings</a>
	</nav>
	<div class="layout-main">
		<GlobalJobBar />
		{@render children()}
	</div>
</div>
