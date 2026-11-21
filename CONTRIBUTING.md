# Contribuer à AnyXboxX

Merci de ton intérêt. Ces règles s'appliquent à toute personne autre que le mainteneur.

## Règle principale : tout passe par une pull request

La branche `main` est protégée. **Personne ne peut y pousser directement.** Pour proposer un changement :

1. Fais un fork du dépôt.
2. Crée une branche depuis `main` : `git checkout -b feat/ma-fonction`.
3. Ajoute tes commits, avec des messages au format `type: description` (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`).
4. Lance les tests : `python -m pytest`, puis `python -m ruff check --select W605,F,E9 PrototypeScarlett tests tools`. Tout doit passer.
5. Ouvre une pull request vers `main` et remplis le modèle proposé : les commandes lancées et leur résultat exact.

Une pull request n'est fusionnée qu'après la relecture et l'accord du mainteneur, et quand les deux checks de la CI passent :

- `lint` (Linux, ~1 min) : ruff et cohérence des README dans les 8 langues ;
- `pytest` (Windows) : build du runtime C++ et du Rust, puis toute la suite. Elle vérifie aussi que le nombre de tests annoncé dans les README est exact.

### Bonnes pratiques

- **Une PR = un comportement.** Deux corrections indépendantes vont dans deux PR, plus faciles à relire.
- **Conflit avec `main`** : fais un rebase (`git fetch && git rebase origin/main`), garde les deux versions quand elles se complètent, relance les tests, puis `git push --force-with-lease`.
- **Check en échec sans rapport avec ta PR** (test GPU sur WARP, par exemple) : signale-le dans la PR, avec le nom du test et la ligne d'erreur ; le mainteneur relancera le job.
- **Aide d'une IA** : indique-le dans la description de la PR.

## Issues

Avant d'écrire du code, tu peux ouvrir une issue :

- **Bogue** : ce que tu as lancé, ce que tu attendais, ce qui s'est passé, le journal ou le rapport `--rapport`.
- **Fonction à émuler** : le nom exact de la fonction (`dll!Fonction`), sa documentation GDK et le programme qui l'appelle.
- **Idée** : le problème que l'idée règle.

Pour un changement important, ouvre d'abord une issue pour en discuter.

## Ce qui est refusé

- Tout contenu protégé : jeux, fichiers système ou clés de la console, exécutables commerciaux, même partiels.
- Les liens vers des copies illégales de jeux.
- Le code sans test pour une nouvelle fonction émulée.

## Ajouter une fonction émulée

Ajoute un gestionnaire décoré par `@hle(...)` dans `PrototypeScarlett/emu/hle/` et un test dans `tests/test_hle.py`. Cite la signature publique de la fonction (documentation Microsoft GDK ou Win32) en commentaire.
