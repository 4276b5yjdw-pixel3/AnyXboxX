# Contribuer à AnyXboxX

Merci de ton intérêt. Ces règles s'appliquent à toute personne autre que le mainteneur.

## Règle principale : tout passe par une pull request

La branche `main` est protégée. **Personne ne peut y pousser directement.** Pour proposer un changement :

1. Fais un fork du dépôt.
2. Crée une branche depuis `main` : `git checkout -b feat/ma-fonction`.
3. Ajoute tes commits, avec des messages au format `type: description` (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`).
4. Lance les tests : `python -m pytest`. Ils doivent tous passer.
5. Ouvre une pull request vers `main` et remplis le modèle proposé.

Une pull request n'est fusionnée qu'après la relecture et l'accord du mainteneur, et quand les tests passent.

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
