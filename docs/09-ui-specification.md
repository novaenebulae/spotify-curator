# 09 — Spécification UI enrichie

Tags: #ui #svelte #tauri #screens #design-system #spotify-curator

## Statut du document

Ce document est la source de vérité pour l’interface Svelte/Tauri du projet **Spotify Library Curator & Playlist Engine**.

Il complète les spécifications fonctionnelles existantes avec :

- une direction visuelle cohérente ;
- un design system minimal ;
- des règles de composition des écrans ;
- les états UI obligatoires ;
- les composants communs ;
- les règles d’affichage des covers Spotify ;
- les règles d’affichage des doublons ;
- les règles de performance frontend ;
- les attentes UI pour toutes les phases.

La documentation projet reste en français. L’interface applicative peut rester en anglais si l’implémentation actuelle l’utilise déjà. Dans ce cas, tous les libellés visibles dans l’application doivent rester cohérents en anglais.

---

## 1. Positionnement UI

### 1.1 Objectif produit

L’application est une **application desktop locale** destinée à explorer, sauvegarder, enrichir et organiser une bibliothèque Spotify.

Elle ne doit pas ressembler à :

- un panneau d’administration brut ;
- une console technique ;
- une application SaaS web générique ;
- un clone de Spotify.

Elle doit ressembler à :

- un outil desktop spécialisé ;
- une bibliothèque musicale personnelle ;
- un cockpit de curation ;
- un outil fiable pour manipuler des données sensibles localement.

### 1.2 Intentions visuelles

Priorités :

1. Lisibilité des données musicales.
2. Confiance avant toute action destructive.
3. Navigation claire entre les phases du workflow.
4. Interface agréable mais sobre.
5. Performance visible sur 5000+ titres.
6. Détails techniques accessibles, mais jamais dominants par défaut.

Mots-clés :

```text
local, desktop, curated, musical, precise, calm, data-rich, safe
```

### 1.3 Ton rédactionnel UI

L’UI doit utiliser des textes courts, explicites et orientés action.

Exemples :

| Mauvais | Préféré |
|---|---|
| Error occurred | Import failed |
| Run | Import liked tracks |
| Data | Library overview |
| Diagnostics JSON | Developer diagnostics |
| Delete | Prepare unlike dry-run |
| Confirm | Confirm dry-run |

Toute action Spotify potentiellement destructive doit mentionner explicitement :

- le nombre de titres concernés ;
- le fait que l’action est en dry-run ;
- le fait qu’aucune écriture Spotify réelle n’est faite en phase 2 ;
- les scopes requis si une future écriture est possible.

---

## 2. Principes UI globaux

### 2.1 Règles obligatoires

- Application desktop claire, locale, non web SaaS.
- Navigation par écrans principaux.
- États visibles : loading, empty, error, offline core, retry, progression job.
- Toute action dangereuse nécessite confirmation.
- Toute écriture Spotify nécessite dry-run préalable.
- Les vues complexes doivent fonctionner avec 5000+ tracks.
- Les détails techniques doivent être accessibles mais repliés par défaut.
- Les erreurs doivent être compréhensibles sans lire les logs.
- Les écrans principaux doivent avoir un objectif unique.
- Le mode debug ne doit pas polluer l’usage normal.

### 2.2 Hiérarchie d’information

Chaque écran doit respecter cette hiérarchie :

1. **Titre et intention de l’écran**.
2. **Statut synthétique**.
3. **Actions principales**.
4. **Contenu principal**.
5. **Détails secondaires**.
6. **Diagnostics techniques repliés**.

### 2.3 Règle anti-debug panel

Les JSON bruts, payloads, diagnostics Docker, traces ou détails techniques doivent être placés dans :

```html
<details>
  <summary>Developer diagnostics</summary>
</details>
```

Ils ne doivent jamais être l’élément visuel dominant d’un écran utilisateur.

---

## 3. Design system minimal

### 3.1 Architecture CSS

Le projet doit éviter une dépendance UI lourde.

Approche recommandée :

```text
app/frontend/src/app.css
app/frontend/src/lib/components/common/*.svelte
app/frontend/src/lib/components/library/*.svelte
```

`app.css` doit contenir :

- variables CSS ;
- resets légers ;
- styles globaux typographiques ;
- classes utilitaires limitées ;
- styles de base pour boutons, inputs, cards et tables.

Les composants Svelte doivent limiter les styles locaux aux besoins spécifiques du composant.

### 3.2 Thème

Thème recommandé : sombre sobre avec surfaces contrastées.

Le thème clair peut être différé.

Variables CSS recommandées :

```css
:root {
  --color-bg: #0f1115;
  --color-bg-subtle: #141821;
  --color-surface: #181d27;
  --color-surface-elevated: #1f2633;
  --color-border: #2a3242;
  --color-border-strong: #3a4558;

  --color-text: #f3f5f7;
  --color-text-muted: #a8b0bf;
  --color-text-subtle: #7f8898;

  --color-accent: #62d26f;
  --color-accent-muted: rgba(98, 210, 111, 0.14);
  --color-accent-border: rgba(98, 210, 111, 0.35);

  --color-info: #6ab7ff;
  --color-warning: #f4c76b;
  --color-danger: #ff6b7a;
  --color-success: #62d26f;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  --shadow-soft: 0 8px 30px rgba(0, 0, 0, 0.25);
  --shadow-card: 0 1px 0 rgba(255, 255, 255, 0.04) inset;
}
```

Les couleurs peuvent être ajustées, mais tous les composants doivent utiliser des variables sémantiques plutôt que des valeurs dispersées.

### 3.3 Typographie

Stack recommandée :

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

Échelle recommandée :

| Usage | Taille | Poids |
|---|---:|---:|
| Page title | 28–32px | 700 |
| Section title | 18–22px | 650 |
| Card title | 15–17px | 650 |
| Body | 14px | 400 |
| Table | 13–14px | 400 |
| Metadata | 12–13px | 400 |
| Badge | 11–12px | 600 |

### 3.4 Espacement

- Padding page : `24px` desktop, `16px` fenêtre étroite.
- Espacement entre sections : `24px` à `32px`.
- Padding card : `16px` à `20px`.
- Gap entre contrôles toolbar : `8px` à `12px`.
- Hauteur ligne table avec cover : `56px` minimum.

### 3.5 Boutons

Variantes obligatoires :

| Variante | Usage |
|---|---|
| primary | action principale positive |
| secondary | action secondaire |
| ghost | navigation ou action légère |
| danger | action destructive réelle, rarement visible |
| danger-soft | dry-run ou préparation action sensible |
| disabled | action indisponible |

Règles :

- Un écran ne doit pas avoir plus d’un bouton `primary` visible dans une même section.
- Les actions destructives doivent utiliser `danger-soft` tant qu’elles sont en dry-run.
- Les boutons doivent avoir un état `loading` quand ils déclenchent un job ou un fetch.
- Les boutons doivent rester nommés explicitement.

### 3.6 Inputs, selects et filtres

- Tous les inputs doivent avoir un label visible ou accessible.
- La recherche texte doit être debouncée.
- Les filtres actifs doivent être résumés sous forme de chips.
- Un bouton `Clear filters` doit être disponible quand au moins un filtre est actif.
- Les filtres avancés peuvent être dans un panneau repliable.

### 3.7 Badges

Types de badges :

| Badge | Couleur | Usage |
|---|---|---|
| Connected | success | Spotify connecté |
| Offline | danger | core API inaccessible |
| Running | info | job en cours |
| Warning | warning | action possible mais avec réserve |
| Dry-run | info/warning | action non appliquée |
| Unavailable | warning | track indisponible |
| Missing | danger-soft | track absente/disparue |
| Duplicate | warning | doublon potentiel |
| Local only | muted | donnée locale |

Les badges ne doivent pas remplacer les messages détaillés quand l’utilisateur doit agir.

---

## 4. Layout global

### 4.1 Shell applicatif

Le layout global doit contenir :

- sidebar ou navigation latérale ;
- header de statut global ;
- zone de contenu ;
- toasts/alerts ;
- panneau global de progression des jobs si nécessaire.

Structure recommandée :

```text
AppShell
  SidebarNav
  MainArea
    TopStatusBar
    PageContent
  ToastRegion
  GlobalJobProgress optional
```

### 4.2 Sidebar

Largeur recommandée : `220–260px`.

Contenu :

1. Logo / nom court de l’application.
2. Navigation principale.
3. Statut compact Core / Spotify.
4. Version ou mode dev en bas.

Navigation principale :

| Label UI | Route | Phase |
|---|---|---|
| Home | `/` | 0 |
| Import | `/import` | 1 |
| Library | `/library` | 2 |
| Enrichment | `/features` | 3 |
| Explorer | `/explorer` | 5+ |
| Similarity Map | `/map` | 6 |
| Playlist Builder | `/playlists` | 5/8 |
| Sync | `/sync` | 5/9 |
| Settings | `/settings` | 0+ |

Les routes non encore implémentées doivent être :

- soit absentes ;
- soit affichées comme `Coming soon` sans casser la navigation.

### 4.3 Header statut

Le header doit afficher au minimum :

- statut Core API ;
- statut Spotify ;
- dernier job actif si présent ;
- bouton refresh global si utile.

Exemple :

```text
Core: Online · Spotify: Connected · Last import: 12 min ago
```

### 4.4 Contenu

Largeur :

- max width standard : `1280px` pour écrans dashboard ;
- width full pour table bibliothèque et carte de similarité ;
- padding cohérent.

---

## 5. États communs

Chaque écran et composant data-driven doit gérer les états suivants.

### 5.1 Loading initial

Utiliser :

- skeleton card pour dashboard ;
- skeleton rows pour table ;
- spinner seulement pour action ponctuelle.

Éviter les grands spinners centrés pour les tables si une structure skeleton est possible.

### 5.2 Refreshing

Quand des données déjà affichées sont rechargées :

- conserver l’ancienne donnée visible ;
- afficher un indicateur discret `Refreshing…` ;
- éviter le flash complet de la page.

### 5.3 Empty

Chaque empty state doit contenir :

- un titre ;
- une phrase d’explication ;
- une action recommandée.

Exemple bibliothèque vide :

```text
No tracks imported yet.
Import your Spotify library to start exploring your collection.
[Go to Import]
```

### 5.4 Error

Chaque erreur doit contenir :

- message humain ;
- action possible ;
- détails techniques repliés si disponibles.

### 5.5 Offline core

Si le core API ne répond pas :

- afficher un message clair ;
- proposer d’ouvrir Settings ;
- proposer de relancer Docker si documenté ;
- ne pas afficher de stack trace par défaut.

### 5.6 Job running

Les jobs doivent afficher :

- type de job ;
- étape actuelle ;
- progression si connue ;
- état final ;
- erreur lisible en cas d’échec.

---

## 6. Règles Spotify metadata et covers

### 6.1 Principe

Les covers d’albums doivent être affichées depuis des **URLs distantes Spotify** ou issues du payload Spotify.

Interdictions :

- ne pas télécharger les covers ;
- ne pas stocker les covers localement ;
- ne pas commiter d’images ;
- ne pas transformer les covers ;
- ne pas ajouter d’overlay visuel sur la cover elle-même.

Autorisé :

- stocker l’URL de cover ;
- afficher l’image en miniature ;
- utiliser un placeholder si aucune URL ;
- rendre la cover ou le titre cliquable vers Spotify si `external_url` existe.

### 6.2 Données attendues côté API

Les DTO affichant des tracks doivent exposer au minimum :

```json
{
  "album": {
    "name": "...",
    "cover_image_url": "...",
    "cover_image_width": 64,
    "cover_image_height": 64
  },
  "external_url": "https://open.spotify.com/track/..."
}
```

Pour les listes de doublons, chaque track doit exposer :

```json
{
  "title": "...",
  "artist_names": ["..."],
  "album_name": "...",
  "cover_image_url": "...",
  "duration_ms": 0,
  "isrc": "...",
  "spotify_track_id": "...",
  "external_url": "..."
}
```

### 6.3 Composant AlbumCover

Créer un composant commun :

```text
app/frontend/src/lib/components/common/AlbumCover.svelte
```

Props recommandées :

```ts
src?: string | null;
alt: string;
size?: 'xs' | 'sm' | 'md' | 'lg';
href?: string | null;
rounded?: boolean;
```

Comportement :

- `loading="lazy"` ;
- fallback visuel en cas d’erreur ;
- taille fixe pour éviter le layout shift ;
- `object-fit: cover` seulement si la miniature conserve le ratio carré standard ;
- aucun overlay ;
- lien externe optionnel ;
- alt text : `Album cover for <album name>`.

Tailles recommandées :

| Size | Pixels | Usage |
|---|---:|---|
| xs | 32 | listes compactes |
| sm | 40 | table library |
| md | 56 | duplicates cards |
| lg | 96 | détail track |

### 6.4 Placeholder cover

Le placeholder doit être neutre et musicalement identifiable.

Exemple :

- carré sombre ;
- icône disque ou note simple si icône disponible ;
- initiales non recommandées pour albums.

---

## 7. Composants communs

### 7.1 Composants base

| Composant | Rôle |
|---|---|
| `AppShell` | layout global |
| `SidebarNav` | navigation principale |
| `TopStatusBar` | statut Core/Spotify/jobs |
| `PageHeader` | titre, description, actions |
| `SectionHeader` | titre de section + aide |
| `Card` | surface de contenu |
| `MetricCard` | métrique dashboard |
| `StatusBadge` | statut court |
| `ErrorAlert` | erreur lisible |
| `EmptyState` | état vide actionnable |
| `LoadingSkeleton` | skeleton générique |
| `ConfirmDialog` | confirmation action sensible |
| `ToastRegion` | notifications temporaires |
| `AlbumCover` | cover distante + fallback |

### 7.2 Composants data

| Composant | Rôle |
|---|---|
| `DataTable` | table générique contrôlée |
| `PaginationControls` | page/page_size |
| `FilterPanel` | filtres visibles/repliables |
| `FilterChipBar` | résumé filtres actifs |
| `TrackIdentityCell` | cover + titre + artistes + album |
| `TrackListTable` | table tracks |
| `JobProgressCard` | job courant |
| `SnapshotSelector` | choix snapshot |
| `ExportPanel` | cible + format + bouton export |

### 7.3 Composants library

| Composant | Rôle |
|---|---|
| `LibraryToolbar` | recherche, refresh, compteurs |
| `LibraryFilters` | filtres tracks |
| `LibraryTable` | table bibliothèque (preview ▶, colonne Features RB/ES/PV, badge Liked) |
| `TrackPreviewButton` | lecture preview Deezer (streaming) |
| `JobRunStatsBar` | tuiles compactes résultat job (Processed / Succeeded / Failed + extra selon type) |
| `CollapsibleSection` | sections repliables (Field coverage, Recent failures, Last runs) |
| `JobRunSummary` | Last runs (hydrate `GET /jobs/insights/latest`) |
| `LibrarySelectionBar` | sélection page et actions |
| `DuplicatesPanel` | onglet doublons |
| `DuplicateGroupCard` | affichage groupe doublons |
| `MissingTracksPanel` | onglet absents/disparus |
| `DryRunModal` | confirmation dry-run |
| `TrackFeaturesDrawer` | panneau latéral features (Fusion + Sources) au clic titre |
| `FeatureMetricGrid` | grille métriques BPM / tonalité / mood |
| `SourceFeatureCard` | carte par provider (ReccoBeats, Essentia) |
| `ActionsHistoryPanel` | historique actions |
| `ActionDetailDrawer` | détail action si nécessaire |

---

## 8. Écran 1 — Accueil

### 8.1 Objectif

La page d’accueil doit donner une vue synthétique de l’état du projet et orienter vers la prochaine action utile.

Elle ne doit pas être vide.

### 8.2 Contenu cible

Sections :

1. Hero compact.
2. Status overview.
3. Library summary.
4. Quick actions.
5. Recent activity.
6. Next steps.

### 8.3 Hero

Contenu :

```text
Spotify Library Curator
Local backup, analysis and playlist generation for your Spotify library.
```

Actions :

- `Open Library` ;
- `Import Library` ;
- `Settings`.

### 8.4 Status overview

Cards :

- Core API status ;
- Spotify connection ;
- Storage mode ;
- Last job status.

### 8.5 Library summary

Cards :

- Tracks imported ;
- Playlists imported ;
- Latest snapshot ;
- Feature coverage.

Si les features ne sont pas encore disponibles : afficher `Not available yet` plutôt qu’une valeur vide.

### 8.5.1 Implémenté — enrichissement & audio (2026-06)

Section **Enrichment & audio** (si `tracks_total > 0`) :

- tuile **ReccoBeats** — % couverture + lien `/features` ;
- tuile **Essentia (local)** — % pistes analysées ;
- tuile **Deezer previews** — % + lien `/library` (bouton resolve) ;
- tuile **Feature enrichment** — raccourci `/features`.

Quick actions : **Features** ajouté à côté Library / Import / Settings.

Nav shell : route **`/features`**.

### 8.6 Recent activity

Afficher :

- dernier import ;
- dernier snapshot ;
- dernier dry-run ;
- dernier export si disponible.

### 8.7 Empty states

Si aucune donnée n’est importée :

```text
Your local library is empty.
Start by importing your Spotify liked tracks and playlists.
[Go to Import]
```

---

## 9. Écran 2 — Connexion Spotify

### 9.1 Objectif

Permettre de connecter ou déconnecter Spotify sans exposer de secrets.

Cette section peut être intégrée à la page Import ou Settings, mais doit rester visuellement claire.

### 9.2 Contenu

- statut connexion ;
- profil utilisateur ;
- scopes actifs ;
- expiration token ;
- bouton connexion ;
- bouton déconnexion ;
- message si client ID absent ;
- lien ou aide configuration.

### 9.3 États

- not configured ;
- disconnected ;
- connected ;
- token expired ;
- callback error ;
- missing scopes.

### 9.4 Sécurité UI

Ne jamais afficher :

- access token ;
- refresh token ;
- code verifier ;
- client secret.

---

## 10. Écran 3 — Import bibliothèque

### 10.1 Objectif

Importer et sauvegarder la bibliothèque Spotify locale.

### 10.2 Organisation cible

Sections :

1. Spotify connection.
2. Import actions.
3. Import progress.
4. Snapshots.
5. Snapshot diff.
6. Exports.
7. Developer details repliés.

### 10.3 Import actions

Actions principales :

- Import liked tracks ;
- Import playlists ;
- Import full library si implémenté ;
- Create snapshot.

Les actions longues doivent créer un job et afficher la progression.

### 10.4 Exports

Remplacer les boutons répétitifs par un panneau unique.

Composant :

```text
ExportPanel
```

Champs :

- export target : liked tracks, playlists, latest snapshot, snapshot diff ;
- format : CSV, JSON ;
- snapshot selector si nécessaire ;
- diff selector si nécessaire ;
- bouton `Export` ;
- résultat : filename, row count, path.

Règle : ne pas afficher 6 boutons d’export similaires côte à côte.

### 10.5 Snapshots

La table snapshots doit afficher :

- type ;
- created_at ;
- track_count ;
- playlist_count ;
- status ;
- actions : details, compare, export.

---

## 11. Écran 4 — Gestion bibliothèque

Route : `/library`.

### 11.1 Objectif

Explorer les titres importés, détecter doublons/absents et préparer des actions dry-run.

### 11.2 Onglets

Onglets :

1. Tracks.
2. Duplicates.
3. Missing tracks.
4. Action history.

Chaque onglet doit conserver son état local si possible : recherche, page, filtres.

### 11.3 États obligatoires

- loading ;
- refreshing ;
- empty ;
- error ;
- offline core.

### 11.4 Limites phase 2

- Sélection multi-page non conservée par défaut.
- Pas de bouton `Apply to Spotify`.
- Dry-run obligatoire.
- Colonne **Features** compacte (RB / Essentia / Preview) + détails via drawer ; pas de colonnes BPM/energy détaillées en table.
- Pas de clustering.

### 11.5 Drawer features par titre (implémenté)

- **Ouverture** : clic sur le titre dans l’onglet Tracks (`LibraryTable` → `TrackFeaturesDrawer`).
- **Fermeture** : Escape, clic overlay, changement d’onglet ou de page bibliothèque.
- **Onglets** :
  - **Fusion** : ligne `audio_features` active (`is_active=true`) — source gagnante après merge (priorité Essentia > ReccoBeats).
  - **Sources** : une carte par provider (`SourceFeatureCard`), y compris sources inactives.
- **États** : loading, empty (« Not analysed yet » + lien `/features`), error, offline core.
- **Données** : `GET /api/v1/features/tracks/{track_id}` via `featuresApi.getTrackFeatures`.
- Checkbox, preview play et tri de colonnes **n’ouvrent pas** le drawer.

### 11.6 Écran Features — couverture et derniers jobs (implémenté)

- **Last runs** : section repliable (fermée par défaut, `features_last_runs_open`) ; hydrate depuis `GET /api/v1/jobs/insights/latest` ; tuiles compactes par type de job (Processed, Succeeded, Failed + Not found ou Skipped selon le job).
- **Accueil** : tuiles ReccoBeats, Essentia local, Deezer previews et lien Features (couverture via `/api/v1/features/coverage` et `/api/v1/previews/coverage`).
- **Field coverage** : section repliable (fermée par défaut) ; grille compacte ReccoBeats vs Essentia (`fields_by_source` sur `/api/v1/features/coverage`).
- **Recent failures** : section repliable ; sources `reccobeats`, `essentia_lowlevel`, `deezer_preview`, `audio_download` ; colonne date ; bouton **Clear list** = masquage des échecs antérieurs (`failures_after` + `localStorage` `features_failures_cleared_at`).
- Scrollbars des tableaux scrollables alignées sur le thème sombre (`app.css`).

---

## 12. Library — Onglet Tracks

### 12.1 Toolbar

La toolbar doit contenir :

- recherche globale ;
- bouton refresh ;
- compteur total ;
- compteur sélection ;
- bouton filtres avancés ;
- actions groupées si sélection non vide.

### 12.2 Filtres

Filtres visibles :

- recherche texte ;
- liked ;
- availability ;
- duplicate status ;
- playlist source ;
- date ajout.

Filtres avancés :

- artiste ;
- album ;
- ISRC ;
- présent dans une playlist ;
- absent des playlists ;
- statut snapshot ;
- durée min/max.

### 12.3 Table tracks

Colonnes recommandées :

| Colonne | Contenu |
|---|---|
| select | checkbox |
| track | cover + title + artists + album |
| duration | format mm:ss |
| liked | date ajout + badge current/historical |
| playlists | count + optional tooltip |
| ISRC | valeur courte ou empty muted |
| status | availability / missing / duplicate badges |
| actions | view / prepare action |

La cellule `track` doit utiliser :

```text
TrackIdentityCell
  AlbumCover
  title
  artist_names
  album_name
```

### 12.4 Covers

- Taille recommandée : `40px`.
- Lazy loading obligatoire.
- Placeholder si absent.
- Le titre ou la cover peut ouvrir Spotify si `external_url` existe.

### 12.5 Tri

Champs triables :

- title ;
- artist ;
- album ;
- duration ;
- liked_added_at ;
- popularity ;
- playlist_count ;
- last_seen_at.

Le tri actif doit être visible.

### 12.6 Pagination

- page size défaut : 50 ;
- options : 25, 50, 100 ;
- max 200 ;
- pagination en haut ou bas, mais au moins visible en bas ;
- changement de page rapide sans flash complet.

### 12.7 Sélection

- sélection page courante ;
- select all page ;
- clear selection ;
- compteur sélection ;
- sélection réinitialisée au changement de page sauf décision contraire documentée.

### 12.8 Actions groupées

Actions disponibles en phase 2 :

- prepare unlike dry-run ;
- prepare restore dry-run ;
- prepare backup playlist dry-run.

La barre d’action groupée ne doit apparaître que si sélection non vide.

---

## 13. Library — Onglet Duplicates

### 13.1 Objectif

Permettre d’auditer les doublons potentiels sans donner l’impression qu’ils doivent être supprimés automatiquement.

### 13.2 Problème à éviter

Ne jamais afficher une répétition brute du type :

```text
isrc — same_isrc (1)
Fantas — Caterina Barbieri (ATE691925901)
Fantas — Caterina Barbieri (ATE691925901)
Fantas — Caterina Barbieri (ATE691925901)
```

Cet affichage est insuffisant car :

- il répète les mêmes informations ;
- il ne distingue pas occurrence et track unique ;
- il n’explique pas le risque réel ;
- il ne montre pas l’album, la durée, les covers ou les contextes.

### 13.3 Règle de déduplication UI

Dans chaque groupe, l’UI doit regrouper les tracks par clé stable :

1. `track_id` si disponible ;
2. sinon `spotify_track_id` ;
3. sinon `title + artist + album + duration_ms`.

Afficher :

- nombre d’occurrences ;
- nombre de tracks uniques ;
- contextes si disponibles.

### 13.4 Types de groupes

| Reason backend | Label UI | Interprétation |
|---|---|---|
| same_isrc | Same ISRC | doublon fort possible |
| same_spotify_track_id | Repeated occurrence | même track présente plusieurs fois |
| same_title_primary_artist | Same title and artist | doublon possible |
| same_title_artist_similar_duration | Similar title, artist and duration | doublon possible avec confiance moyenne |

### 13.5 DuplicateGroupCard

Créer :

```text
app/frontend/src/lib/components/library/DuplicateGroupCard.svelte
```

Header :

- label humain ;
- confidence ;
- ISRC si présent ;
- occurrences count ;
- unique tracks count ;
- strategy badge.

Body : une carte par track unique.

Track card :

- cover `56px` ;
- titre ;
- artistes ;
- album ;
- durée ;
- ISRC ;
- Spotify link ;
- contextes : liked, playlist names, occurrences.

### 13.6 Cas repeated occurrence

Si un groupe a plusieurs occurrences mais une seule track unique :

- afficher `Repeated occurrence` ;
- ne pas utiliser un style danger ;
- expliquer : `This looks like the same Spotify track appearing in multiple contexts.` ;
- afficher les contextes si disponibles.

### 13.7 Actions

Actions possibles :

- filter these tracks in Library ;
- prepare backup playlist dry-run ;
- prepare unlike dry-run si sélection explicite ;
- open on Spotify.

Aucune suppression automatique.

---

## 14. Library — Onglet Missing tracks

### 14.1 Objectif

Lister les titres absents, retirés, indisponibles ou relinkés à partir des snapshots/diffs.

### 14.2 Résumé

Afficher des cartes :

- removed from liked ;
- missing from current import ;
- unavailable on Spotify ;
- null playlist track ;
- possibly relinked.

### 14.3 Table

Colonnes :

- track identity ;
- status ;
- source snapshot ;
- target snapshot ;
- detected_at ;
- action.

### 14.4 Actions

- prepare restore liked dry-run ;
- prepare backup playlist dry-run ;
- open snapshot diff.

---

## 15. Library — Actions dry-run

### 15.1 Modale dry-run

La modale doit afficher :

- type d’action ;
- dry-run badge ;
- nombre de tracks ;
- échantillon des tracks affectées avec covers si disponibles ;
- warnings ;
- scopes requis ;
- confirmation explicite.

### 15.2 Texte obligatoire

Pour les actions sensibles :

```text
This is a dry-run. No changes will be applied to Spotify.
```

Si scopes write absents :

```text
Spotify write scope is not available. This action can only be previewed.
```

### 15.3 Boutons

- `Cancel` ;
- `Confirm dry-run`.

Ne pas afficher `Apply` en phase 2.

---

## 16. Library — Historique actions

### 16.1 Objectif

Afficher l’historique local des dry-runs et futures actions.

### 16.2 Liste

Colonnes :

- action type ;
- created_at ;
- affected_count ;
- dry-run ;
- status ;
- warnings count ;
- details.

### 16.3 Détail

Le détail doit afficher :

- paramètres de l’action ;
- tracks affectées ;
- warnings ;
- result JSON replié ;
- absence d’écriture Spotify.

---

## 17. Écran 5 — Enrichissement features

Phase 3/4/7.

### 17.1 Objectif

Piloter l’enrichissement des données musicales depuis ReccoBeats, analyse locale et modèles avancés.

### 17.2 Sections

- Coverage globale ;
- Coverage par feature ;
- Sources disponibles ;
- Jobs enrichissement ;
- Tracks sans features ;
- Failed jobs ;
- Actions relance ;
- Developer raw payloads repliés.

### 17.3 Règles UI

- Afficher la source de chaque feature : Spotify, ReccoBeats, Essentia local, Essentia TF.
- Afficher un score de confiance si disponible.
- Ne pas afficher les payloads raw par défaut.
- Les actions longues créent des jobs.

---

## 18. Écran 6 — Explorateur musical

Phase 5+.

### 18.1 Objectif

Explorer les titres par features musicales et tags.

### 18.2 Table enrichie

Colonnes possibles :

- track identity ;
- BPM ;
- energy ;
- valence ;
- danceability ;
- key/Camelot ;
- mood ;
- vocal/instrumental ;
- tags ;
- cluster ;
- score.

### 18.3 Interaction

- filtres features ;
- colonnes configurables ;
- ajout à playlist candidate ;
- exclusion manuelle ;
- édition tags utilisateur.

---

## 19. Écran 7 — Carte de similarité

Phase 6.

### 19.1 Objectif

Explorer la bibliothèque par similarité via UMAP/HDBSCAN.

### 19.2 Visualisation

- projection 2D ;
- clusters ;
- zoom/pan ;
- sélection points ;
- tooltip léger ;
- détail sélection dans panneau latéral.

### 19.3 Colorations

- cluster ;
- playlist ;
- genre ;
- année ;
- source features ;
- mood ;
- energy ;
- vocal/acoustic/electronic.

### 19.4 Performance

- minimum 5000 points ;
- Canvas recommandé si SVG devient lent ;
- tooltips sans requête backend par hover ;
- chargement progressif si nécessaire.

---

## 20. Écran 8 — Générateur de playlists

Phase 5/8.

### 20.1 Objectif

Créer des playlists candidates à partir de règles, presets et scores explicables.

### 20.2 Sections

- Presets ;
- Rule editor ;
- YAML advanced editor ;
- Validation ;
- Preview ;
- Score details ;
- Exclusions ;
- Ordering ;
- Dry-run sync.

### 20.3 Presets initiaux

- Dark / Intense ;
- Calm / Focus ;
- Ambient / Drone ;
- IDM / Experimental ;
- EBM / Industrial ;
- Pop / Vocal ;
- Acoustic / Organic ;
- Electronic / Synthetic ;
- High Energy ;
- Low Vocal ;
- Instrumental Focus ;
- Discover Forgotten Likes ;
- Recently Added ;
- Clean Library ;
- Missing Tracks Recovery.

### 20.4 Preview

La preview doit afficher :

- tracks sélectionnées ;
- score total ;
- raisons de sélection ;
- raisons d’exclusion ;
- contraintes appliquées ;
- ordering proposé.

---

## 21. Écran 9 — Synchronisation Spotify

Phase 5/9.

### 21.1 Objectif

Préparer et éventuellement appliquer une synchronisation Spotify sécurisée.

### 21.2 Règles sécurité

- dry-run obligatoire ;
- diff visible ;
- confirmation explicite ;
- scopes write vérifiés ;
- historique sync ;
- rollback local si possible.

### 21.3 Modes

- create playlist ;
- replace contents ;
- append only ;
- remove obsolete ;
- export local only.

---

## 22. Écran 10 — Settings

### 22.1 Objectif

Configurer et diagnostiquer l’application sans donner l’impression d’un écran de debug.

### 22.2 Structure cible

Sections :

1. Core API.
2. Spotify account.
3. Storage.
4. Docker runtime.
5. Cache and cleanup.
6. Backup and restore.
7. Versions.
8. Developer diagnostics.

### 22.3 Core API

Afficher :

- status ;
- base URL ;
- version ;
- health last checked ;
- bouton refresh.

### 22.4 Spotify account

Afficher :

- connected/disconnected ;
- user id/display name ;
- scopes ;
- token expiry ;
- bouton connect/logout.

Ne jamais afficher les tokens.

### 22.5 Storage

Afficher :

- SQLite storage mode ;
- data path ;
- exports path ;
- logs path ;
- cache path ;
- models path ;
- backups path.

Si volume Docker nommé utilisé : l’indiquer clairement.

### 22.6 Docker runtime

Afficher :

- dernier check ;
- statut résumé ;
- bouton run checks ;
- liste checks sous forme de cards/table lisible.

### 22.7 Developer diagnostics

Contient :

- diagnostics JSON ;
- runtime config JSON ;
- raw errors ;
- feature flags.

Toujours replié par défaut.

---

## 23. Performance frontend

### 23.1 Règles générales

- Ne pas refetch toute la page si seul un onglet change.
- Utiliser `AbortController` pour annuler les fetchs obsolètes.
- Debounce recherche texte : `250–400 ms`.
- Conserver les données visibles pendant refresh.
- Lazy load images.
- Limiter la taille des payloads liste.
- Éviter les rendus de JSON brut massifs.

### 23.2 Tables

Pour 5000+ titres :

- pagination serveur obligatoire ;
- page size défaut 50 ;
- ne pas charger toutes les tracks côté client ;
- éviter les tableaux imbriqués lourds dans chaque ligne ;
- éviter de recalculer les données dérivées au render si elles peuvent venir de l’API.

### 23.3 Covers

- Utiliser l’URL petite/moyenne ;
- `loading="lazy"` ;
- placeholder taille fixe ;
- pas de préchargement massif ;
- pas de stockage local.

---

## 24. Accessibilité minimale

### 24.1 Obligatoire

- boutons nommés ;
- labels visibles ou aria-label ;
- états disabled explicites ;
- contraste suffisant ;
- focus visible ;
- navigation clavier basique ;
- messages d’erreur lisibles ;
- modales fermables au clavier ;
- tables utilisables sans souris pour actions principales.

### 24.2 Tables

- Les colonnes triables doivent indiquer leur état.
- Les checkboxes doivent avoir un label accessible.
- Les actions par ligne doivent être nommées.

### 24.3 Images

- Cover alt : `Album cover for <album>`.
- Si album inconnu : `Album cover`.
- Placeholder décoratif possible avec `aria-hidden="true"` si le texte adjacent décrit la track.

---

## 25. Tests UI et validation

### 25.1 Validation manuelle tant que Vitest absent

Pour chaque changement UI :

```bash
cd app/frontend
npm run check
npm run build
npm run dev
```

Tester :

- `/` ;
- `/import` ;
- `/library` ;
- `/settings`.

### 25.2 Scénarios obligatoires

- core offline ;
- Spotify disconnected ;
- Spotify connected ;
- bibliothèque vide ;
- bibliothèque avec données ;
- recherche ;
- pagination ;
- filtres ;
- sélection ;
- dry-run ;
- duplicate group avec une seule track unique répétée ;
- duplicate group avec plusieurs tracks uniques ;
- cover présente ;
- cover absente ;
- image cover en erreur ;
- settings sans mode debug visible par défaut.

### 25.3 Tests automatisés futurs

Quand Vitest sera ajouté :

- navigation ;
- StatusBadge ;
- AlbumCover fallback ;
- TrackIdentityCell ;
- ExportPanel ;
- LibraryTable ;
- DuplicateGroupCard ;
- DryRunModal ;
- Settings sections.

---

## 26. Critères d’acceptation design

Une modification UI est acceptée si :

- l’écran est lisible sans connaître le code ;
- l’action principale est évidente ;
- les données techniques sont secondaires ;
- les états loading/empty/error/offline sont gérés ;
- les actions sensibles sont protégées ;
- les pages principales partagent les mêmes composants visuels ;
- les covers s’affichent sans stockage local ;
- les doublons sont compréhensibles sans répétition brute ;
- `npm run check` et `npm run build` passent ;
- la documentation est mise à jour.

---

## 27. Ordre recommandé pour le rework UI actuel

Pour améliorer l’UI après la phase 2, procéder dans cet ordre :

1. Ajouter support backend/API des cover URLs si absent.
2. Créer `AlbumCover` et `TrackIdentityCell`.
3. Revoir la table Library Tracks.
4. Revoir l’onglet Duplicates avec `DuplicateGroupCard`.
5. Simplifier les exports dans Import avec `ExportPanel`.
6. Refaire Settings en sections utilisateur + diagnostics repliés.
7. Refaire Home en dashboard.
8. Harmoniser layout global et design tokens.
9. Mettre à jour docs et backlog.

Ne pas refactorer toutes les pages en une seule passe Cursor. Découper en commits courts.

---

## 28. Prompt court de contrôle pour Cursor

À utiliser avant tout rework UI :

```text
Avant de coder, vérifie docs/09-ui-specification.md.
Respecte le design system minimal, les états UI obligatoires, les règles de covers distantes, les règles d’affichage des doublons et les limites de phase.
Ne stocke aucune image localement.
Ne transforme pas les covers Spotify.
Ne rends pas les diagnostics techniques visibles par défaut.
Propose un plan avant modification.
```
