# Prompt Cursor — Phase 5.5 — UI Playlist Builder

Objectif : implémenter l'interface phase 5 pour créer, valider, prévisualiser et dry-run des playlists.

## À lire avant de coder

```text
docs/09-ui-specification.md
docs/08-playlist-engine.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Préconditions

Les endpoints backend doivent exister :

```text
POST /api/v1/playlist-rules/validate
POST /api/v1/playlist-rules
GET /api/v1/playlist-rules
GET /api/v1/playlist-rules/{rule_id}
PUT /api/v1/playlist-rules/{rule_id}
POST /api/v1/generated-playlists/preview
GET /api/v1/generated-playlists/{id}
POST /api/v1/sync/dry-run
GET /api/v1/sync/jobs/{id}
```

Si un endpoint manque, signale-le avant de coder l'UI correspondante.

## Route

Ajouter ou activer :

```text
/playlists
```

Ajouter la navigation dans le shell si absent :

```text
Playlist Builder
```

## UX attendue

L'écran doit contenir :

```text
PageHeader
Presets
Rule editor simple
Advanced JSON/YAML editor
Validation panel
Preview panel
Score details
Exclusions/warnings
Dry-run sync panel
```

## États obligatoires

- loading initial ;
- refreshing ;
- empty ;
- error ;
- offline core ;
- validation errors ;
- validation warnings ;
- preview running/loading ;
- dry-run loading ;
- dry-run result.

## Règles UI

- Ne jamais afficher d'action Spotify réelle.
- Afficher clairement `Dry-run only`.
- Les warnings de features futures doivent être lisibles et non bloquants.
- Les score details doivent être accessibles par item.
- Les exclusions doivent être consultables.
- Les JSON techniques doivent être repliés par défaut.
- Respecter le design system existant.

## Composants suggérés

```text
PlaylistBuilderPage.svelte
PlaylistPresetGrid.svelte
PlaylistRuleEditor.svelte
PlaylistAdvancedEditor.svelte
PlaylistValidationPanel.svelte
GeneratedPlaylistPreview.svelte
PlaylistScoreDetailsDrawer.svelte
PlaylistExclusionsPanel.svelte
PlaylistDryRunPanel.svelte
```

Adapter aux conventions existantes.

## API frontend

Créer ou compléter :

```text
app/frontend/src/lib/api/playlists.ts
app/frontend/src/lib/types/playlists.ts
```

## Presets initiaux UI

Afficher au minimum :

```text
Dark / Intense
Calm / Focus
High Energy
Recently Added
Discover Forgotten Likes
Clean Library
```

Optionnel avec warning :

```text
Low Vocal
Instrumental Focus
Electronic / Synthetic
Acoustic / Organic
```

## Tests / validation

Minimum :

```bash
cd app/frontend
npm run check
npm run build
```

Si tests frontend existent, ajouter tests pour :

```text
validation errors
warnings features futures
preview result display
score details display
dry-run result display
```

## Réponse attendue

Fournis :

```text
- pages/composants ajoutés ;
- clients API ajoutés ;
- états UI gérés ;
- limites restantes ;
- commandes exécutées ;
- risques restants.
```
