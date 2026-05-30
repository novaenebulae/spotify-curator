<script lang="ts">
	import { page } from '$app/stores';
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<nav>
	<a href="/" class:active={$page.url.pathname === '/'}>Home</a>
	<a href="/import" class:active={$page.url.pathname.startsWith('/import')}>Import</a>
	<a href="/library" class:active={$page.url.pathname.startsWith('/library')}>Library</a>
	<a href="/settings" class:active={$page.url.pathname.startsWith('/settings')}>Settings</a>
</nav>

{@render children()}
