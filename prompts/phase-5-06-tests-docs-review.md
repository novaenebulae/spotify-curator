# Prompt Cursor — Phase 5.6 — Tests, documentation et revue finale

Objectif : finaliser la phase 5 après implémentation backend + UI.

## À lire avant de commencer

```text
docs/03-development-workflow.md
docs/04-backlog-by-phase.md
docs/05-domain-model.md
docs/06-api-contract.md
docs/08-playlist-engine.md
docs/09-ui-specification.md
docs/18-feature-consumption-contract.md
backlog/phase-5.md
```

## Audit final attendu

Vérifie que la phase 5 respecte :

```text
- FeatureRegistry utilisé ;
- FeatureResolver utilisé ;
- TrackFeatureView utilisé ;
- pas de lecture raw payload dans le moteur playlist ;
- règles validées ;
- CRUD règles ;
- preview persistée ;
- score details ;
- exclusions ;
- dry-run sync sans écriture ;
- UI utilisable ;
- features futures phase 7 gérées avec warnings ;
- docs à jour.
```

## Tests backend à compléter

Ajouter ou vérifier :

```text
FeatureRegistry
FeatureResolver
PlaylistRule validation
PlaylistRule CRUD
Source selection
Filters
Scoring
Weight renormalization
Diversity
Ordering
Preview persistence
Dry-run sync
API error formats
No Spotify write call
```

## Tests frontend à compléter si infrastructure disponible

```text
Playlist route renders
Presets visible
Validation errors visible
Warnings visible
Preview visible
Score details visible
Dry-run result visible
Offline/error states
```

## Documentation à mettre à jour

Mettre à jour selon l'implémentation réelle :

```text
docs/04-backlog-by-phase.md
docs/05-domain-model.md
docs/06-api-contract.md
docs/08-playlist-engine.md
docs/09-ui-specification.md
docs/18-feature-consumption-contract.md
docs/14-configuration.md si variables ajoutées
backlog/phase-5.md
```

Ne pas marquer `DONE` sans validation/test.

## Commandes de validation

Backend :

```bash
cd core
uv run alembic upgrade head
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Frontend :

```bash
cd app/frontend
npm run check
npm run build
```

Smoke API :

```bash
curl http://127.0.0.1:8765/api/v1/health
curl http://127.0.0.1:8765/api/v1/playlist-rules
```

## Revue de phase attendue

Produis un rapport :

```text
# Phase 5 review

## Livrables réalisés
## Endpoints ajoutés
## Tables/migrations ajoutées
## UI ajoutée
## Tests exécutés
## Résultats
## Documentation modifiée
## Écarts restants
## Risques phase 6
## Risques phase 7
## Décision GO/NO-GO phase 6
```

## Contraintes

- Ne pas commencer phase 6.
- Ne pas commencer phase 7.
- Ne pas ajouter d'écriture Spotify réelle.
- Ne pas masquer les tests échoués.
- Ne pas modifier l'architecture sans documenter.
