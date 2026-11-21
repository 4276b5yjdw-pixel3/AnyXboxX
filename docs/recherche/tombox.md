# TomBox et sa suite : ce que nous reprenons

[TomBox](https://github.com/drycheetah84/TomBox) (drycheetah84) et sa suite [omonkeyz/xbox-emulator](https://github.com/omonkeyz/xbox-emulator) (licence MIT ou Apache-2.0) réimplémentent en Rust la couche plateforme de la Xbox Series X|S. Chaque DLL console (`d3d12_xs`, `xg_xs`, `xmem`, `xma`…) y devient une DLL de remplacement, et `tombox-xshader` traduit les shaders RDNA 2 en HLSL. AnyXboxX reprend leur code et leurs observations publiées, en les citant ; aucun fichier de jeu ou de console n'est repris.

État relevé le 21 novembre 2026 (commit `fef9a6e` de omonkeyz/xbox-emulator), d'après leurs fichiers `README.md`, `docs/MILESTONES.md`, `docs/BLOCKERS.md` et `docs/DEVELOPMENT_LOG.md`.

## Ce qu'ils ont établi

| Domaine | Leur état | Pour AnyXboxX |
| --- | --- | --- |
| Fonctions système importées (Fortnite) | 671 sur 671 couvertes | modèle pour nos #12 et #13 |
| Méthodes Direct3D 12.x console | 185 sur 200, emplacements de vtable mesurés | débloque nos #18 (périphérique) et #19 (PresentX) |
| Instructions RDNA 2 vérifiées | 573 sur 721 | à croiser avec notre banc de 34 948 encodages LLVM |
| Étages de shaders | 6 sur 8 (mesh et amplification incomplets) | au-delà de notre recompilateur de calcul (#21) |
| Shaders d'un titre traduits | 105 506 sur 105 506 (Fortnite) | à valider avec notre interpréteur de référence |
| Bibliothèques console | 2 076 sur 2 141 exports | nos #13, #14, #26 |
| Titre lancé | Fortnite : démarrage, connexion, sélection du mode, salon Battle Royale | aucun titre console chez nous |

## Observations sur le paquet GTA VI 1.0.2.1

Ils ont examiné le même paquet que celui étudié par AnyXboxX et arrivent à la même conclusion : il ne peut pas être lancé, l'exécutable est absent.

- 26 503 shaders, dans des conteneurs de shaders Xbox compressés. Sur un échantillon de 4 000, tous se désassemblent ; environ un tiers des shaders de sommets se traduisent.
- 8 765 programmes mesh : ils en ont tiré l'ABI console des mesh shaders (`v5` = identifiant de sommet du groupe, `s3[27:24]` = numéro de wave, `s_sendmsg 9` pour réserver la sortie, exports de position 12, de découpe 13 à 15 et de primitives 20).
- Blocage : aucun de ces programmes mesh n'a de bloc `RTS0` (root signature). Sans la root signature du titre, leurs ressources en SGPR utilisateur (s16 et suivants) ne peuvent pas être liées ; elle se trouve dans l'exécutable manquant.

## Différences de méthode

- Ils travaillent sur des copies déjà déchiffrées de jeux du commerce. AnyXboxX n'utilise que des sources publiques (documentation d'AMD et de Microsoft, tests de LLVM) et des programmes de test libres.
- Leurs vérifications passent par des lancements de titres. AnyXboxX vérifie chaque traduction de shader contre un interpréteur de référence, à l'octet près, et son décodeur contre les tests d'encodage de LLVM : ces deux outils peuvent valider leur traducteur.

## Reprise dans AnyXboxX

1. Ce document et [THIRD_PARTY.md](../../THIRD_PARTY.md) : citation et licences.
2. Leur dépôt en sous-module Git (`third_party/tombox`), compilé avec `cargo`.
3. Le lanceur `anyxboxx.exe` charge leurs DLL Rust pour les bibliothèques console qu'AnyXboxX ne couvre pas.
4. Leur traducteur `tombox-xshader` vérifié par notre interpréteur de référence sur le GPU.
