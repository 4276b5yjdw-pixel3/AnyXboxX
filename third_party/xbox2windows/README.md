# Xbox2Windows : retarget du DXIL console (copie)

Fichiers copiés **sans modification** depuis [R0Y00/Xbox2Windows](https://github.com/R0Y00/Xbox2Windows),
commit `bc24dfd7eb` (21 novembre 2026). Licence : MIT (fichier `LICENSE`). Tout le mérite de ce code
revient aux contributeurs de Xbox2Windows.

| Fichier | Rôle |
| --- | --- |
| `tools/dxil_retarget.py` | réécrit un module DXIL console (`dxil-ms-xb2`) en DXIL du PC (`dxil-ms-dx`), sans repasser par HLSL ; mode `--pe` pour les conteneurs embarqués dans un exécutable |
| `tools/resource_inventory.py`, `tools/verify_build.py` | lecture des parties d'un conteneur DXBC, dépendances du précédent |
| `tests/dxil_retarget_check.py` | leur test : modules DXIL fabriqués en mémoire, contrôles positifs et négatifs |

Utilisation : `python third_party/xbox2windows/tools/dxil_retarget.py <entrée.dxbc> <sortie.dxbc>`, ou
`--pe <jeu.exe> --output-dir <dossier>` sur un exécutable console. AnyXboxX lance leur test dans sa suite
(`tests/test_dxil_retarget.py`). Pour mettre à jour : recopier ces fichiers depuis un commit plus récent.
