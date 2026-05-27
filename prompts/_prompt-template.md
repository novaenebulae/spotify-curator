# Modèle de prompt Cursor — tâche incrémentale

Tags: #cursor #prompt-template

```text
Phase : [numéro + nom]
Tâche : [code + nom depuis backlog/phase-X.md]

Contexte :
- Lis AGENTS.md.
- Lis docs/00-project-brief.md.
- Lis docs/01-architecture.md.
- Lis docs/03-development-workflow.md.
- Lis docs/12-decisions.md.
- Lis backlog/phase-X.md.
- Lis les règles Cursor applicables.

Objectif :
[objectif précis]

Contraintes :
- Ne travaille que sur cette tâche.
- Ne modifie pas les décisions d’architecture.
- Ne génère pas les phases futures.
- Ne crée pas de dépendances non demandées.
- Ne commite aucun secret, cache, modèle ou fichier audio.
- Propose un plan avant de coder.
- Liste les fichiers à créer/modifier.

Critères d’acceptation :
- ...

Tests attendus :
- ...

Livrable attendu :
- Plan.
- Fichiers.
- Implémentation après validation.
- Commandes de validation.
- Limites.
```
