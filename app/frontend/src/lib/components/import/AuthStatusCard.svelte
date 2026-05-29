<script lang="ts">
	import type { AuthStatus } from '$lib/spotifyApi';

	type Props = {
		auth: AuthStatus | null;
		loading?: boolean;
		error?: string | null;
		onConnect: () => void;
		onDisconnect: () => void;
		busy?: boolean;
	};

	let { auth, loading = false, error = null, onConnect, onDisconnect, busy = false }: Props =
		$props();
</script>

<section class="card">
	<h2>Spotify account</h2>
	{#if loading}
		<p class="muted">Checking connection…</p>
	{:else if auth?.connected}
		<p class="status ok">Connected</p>
		{#if auth.user?.id}
			<p>User: <code>{auth.user.id}</code></p>
		{/if}
		{#if auth.token_expires_at}
			<p class="muted">Token expires: {auth.token_expires_at}</p>
		{/if}
		{#if auth.scopes.length > 0}
			<p class="scopes">
				Scopes:
				{#each auth.scopes as scope}
					<code>{scope}</code>
				{/each}
			</p>
		{/if}
		<button type="button" class="secondary" onclick={onDisconnect} disabled={busy}>
			Disconnect
		</button>
	{:else}
		<p class="status warn">Not connected</p>
		<p class="muted">Connect with Spotify (PKCE). A browser window will open for authorization.</p>
		<button type="button" onclick={onConnect} disabled={busy}>Connect Spotify</button>
	{/if}
	{#if error}
		<pre class="error">{error}</pre>
	{/if}
</section>
