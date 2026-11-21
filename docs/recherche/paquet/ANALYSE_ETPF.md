# Tables ETPF et blocs TTPF

L'intervalle initial de chaque TTPF examiné commence par un en-tête ETPF. Sur les 57 fichiers du layout, les quatre premiers mots de 32 bits little-endian suivent les mêmes contraintes.

| Décalage relatif | Observation |
| --- | --- |
| 0x00 | Signature `ETPF`. |
| 0x04 | Valeur 634, soit `0x27a`. Sa signification reste à établir. |
| 0x08 | Valeur N. Au moins N groupes de 16 octets suivent l'en-tête dans l'intervalle ETPF. Leur structure exacte et leur rôle restent à établir. |
| 0x0c | Valeur S, multiple de 16, supérieure ou égale à N × 16. L'intervalle ETPF contient au moins 16 + S octets. La signification de S reste à établir. |

On peut examiner ces groupes bruts et l'empreinte de tout l'intervalle ETPF avec Python 3.10 ou ultérieur.

```powershell
python .\inspect_etpf.py .\data\ttdb\ui\platform.ttpf
python .\inspect_etpf.py .\data\ttdb\graphics\ttdb_graphics.ttpf --debut 910 --limite 3
```

Pour `platform.ttpf`, l'intervalle occupe les offsets 256 à 4351 inclus. N vaut 1 et S vaut 16. Le groupe de 16 octets commence à l'offset 272 et contient `ffc37f00110320000100000000000000`. L'empreinte SHA-256 de l'intervalle complet est `eaf3e96c3e305a2715654bb9bfb24b8a37c3ea1868ce1ba68d8af4b1b1ae51fc`. Les octets après ce groupe incluent des données supplémentaires et du remplissage. Leurs limites et leur signification n'ont pas été établies.

Pour `ttdb_graphics.ttpf`, N vaut 912 et S vaut 17040. L'intervalle ETPF complet occupe 49152 octets. Le dernier groupe, numéro 911, commence à l'offset fichier 27136.

## Table triée et limite candidate de l'index

Dans chacun des 57 fichiers, les N lignes de 16 octets sont immédiatement suivies de N valeurs de 64 bits little-endian **strictement croissantes**. Cette suite commence à l'offset relatif `16 + 16 × N` depuis la signature ETPF et finit à `16 + 24 × N` exclu. Leur rôle est inconnu : leur ordre ne prouve pas une correspondance avec les lignes ETPF du même numéro.

La position relative `16 + 32 × N + S` est contenue dans les 57 intervalles ETPF : dans chaque fichier examiné, tous les octets entre cette position et la fin de l'intervalle sont nuls, et l'octet qui précède est non nul. Cela décrit une borne candidate pour la zone de données de l'index, pas la structure des octets entre la table triée et cette borne. Dans 55 fichiers, la taille de l'intervalle correspond à cette borne arrondie au multiple supérieur de 4 096 ; deux intervalles possèdent davantage de zéros de remplissage. La formule d'arrondi ne vaut donc pas pour tous les fichiers.

Pour `ttdb_graphics.ttpf`, la table triée de 912 valeurs occupe les offsets fichier **27 152 à 34 448 exclu** ; son SHA-256 est `a8cb17ad49574247d8735b26aa967daf5b89bcc20776c3b700de183881ac879b`. La borne candidate est à l'offset fichier 58 784 ; les 2 912 octets restants jusqu'à la fin de l'intervalle sont nuls. `inspect_etpf.py` affiche ces bornes, l'empreinte de la table et les valeurs sélectionnées séparément des lignes ETPF.

### Lien candidat avec les lignes de même rang

`python .\comparer_cles_etpf.py . --comparer-blocs` compare les valeurs entre les 57 fichiers et, pour chaque répétition, les lignes ETPF de même rang que la valeur dans leur table respective. Les 357 115 valeurs comprennent 357 067 valeurs distinctes : **48 valeurs apparaissent deux fois**, chacune dans deux fichiers différents.

Pour ces 48 paires, les deux premiers mots des lignes de même rang sont identiques dans **46 cas**, les tailles logiques totales dans **46 cas** et le nombre de blocs dans **47 cas**. Les tailles physiques totales sont identiques dans 22 cas ; dans ces 22 cas, tous les octets stockés, y compris l'éventuel remplissage, sont identiques.

Pour les 42 paires dont tous les blocs sont marqués zlib et respectent la limite de 64 Mio par bloc, la commande vérifie la fin et la taille de chaque flux, puis compare les empreintes SHA-256 des concaténations de données décompressées. **39 paires ont la même empreinte et trois ont des empreintes différentes.** Les six autres paires ne sont pas comparées après décompression par cette méthode. Les trois différences et leurs empreintes sont listées dans la sortie JSON.

Ces résultats constituent un indice fort que la valeur triée et la ligne du même rang sont associées, mais montrent qu'une valeur répétée ne garantit pas un contenu identique. Le sens de la valeur elle-même et la cause des différences restent inconnus.

## Correspondance avec les blocs

Pour chaque groupe de 16 octets, lire son troisième mot comme un entier 32 bits little-endian et calculer `page = mot & 0x1fffff`. La position logique correspondante en octets est `page * 4096`. Sur les 357 115 groupes des 57 fichiers, toutes ces positions correspondent à une borne de début d'un bloc de données de la table RDS5. Dans chacun des fichiers, les positions sont strictement croissantes et la première correspond au bloc 1.

Cette correspondance permet de partitionner les blocs de données en groupes successifs. Pour un groupe ETPF, son premier bloc est celui qui commence à sa position logique. La borne de fin est le premier bloc du groupe ETPF suivant ou, pour le dernier groupe, la borne de fin du fichier logique. C'est une association structurelle vérifiée sur cette copie. Le sens métier des groupes et leurs autres champs restent à établir.

Dans `ttdb_graphics.ttpf`, les premières pages sont 12, 13, 15, 16, 17, 18, 19 et 21, et elles correspondent respectivement aux blocs de données 1 à 8. Dans `ttdb_vehicles.ttpf`, les premières pages sont 11, 183, 535 et 578, correspondant aux blocs 1, 5, 9 et 13. Le lecteur `inspect_etpf.py` affiche maintenant le premier bloc, la borne de fin exclue et le nombre de blocs de chaque groupe.

## Dimensions candidates

Le premier mot little-endian `x` de chaque groupe présente deux champs compatibles avec des dimensions. La largeur candidate vaut `(x & 0x3fff) + 1`, et la hauteur candidate vaut `((x >> 14) & 0x3fff) + 1`. Les quatre bits de poids fort restent distincts. Sur les 357 115 groupes, les deux dimensions candidates sont toujours des puissances de deux. Les couples les plus fréquents sont 1024 × 1024 pour 97 910 groupes, 512 × 512 pour 80 975 et 256 × 256 pour 58 442.

Dans les 832 groupes dont le deuxième mot est `0x012000e0` et qui comportent un seul bloc, la taille logique de ce bloc correspond exactement à `largeur × hauteur × 4` octets arrondis au multiple supérieur de 4096. Par exemple, le premier groupe de `ttdb_graphics.ttpf` donne 32 × 32 et un bloc de 4096 octets. Sa décompression produit effectivement 4096 octets. Cette corrélation appuie l'interprétation comme dimensions et pixels de quatre octets pour ce sous-ensemble. L'ordre des canaux, l'agencement des pixels et le sens exact du deuxième mot restent à vérifier.

Le lecteur affiche ces deux valeurs comme `largeur_candidate` et `hauteur_candidate`, ainsi que les quatre bits de poids fort sous `bits_28_31`. Les 357 115 groupes se répartissent notamment entre 60 873 groupes à un bloc, 89 116 à deux blocs, 41 968 à trois blocs et 164 939 à quatre blocs.

Un échantillon supplémentaire reproductible de blocs TTPF a été tiré avec Python, `random.seed(42)` et jusqu'à 40 blocs par fichier dans l'ordre de parcours local. Les 2 160 blocs retenus avaient des tailles stockées et logiques inférieures ou égales à 2 000 000 octets. Dans cet échantillon, les 1 889 blocs dont le bit 29 est actif ont produit un flux zlib complet à la taille logique attendue. Les 271 blocs restants n'ont pas été décodés par zlib. Le format de ces 271 blocs reste inconnu, et les 2 160 essais représentent un échantillon.

Un essai LZ4 bloc brut avec 0 à 255 octets retirés en fin de bloc n'a pas décodé les blocs `ttdb_graphics.ttpf` numéro 1150 et `ttdb_vehicles.ttpf` numéro 6. Ce résultat porte sur ces deux échantillons et cette méthode de décodage.

## Comparaison des tailles des groupes à un bloc

Le script `python .\stats_etpf.py .` parcourt les 57 TTPF de ce dossier et compare, pour chacun des groupes associés à un seul bloc, sa taille logique à plusieurs multiples de la surface candidate, arrondis à 4 096 octets. Il regroupe les résultats selon le deuxième mot de la ligne ETPF. Sur les 357 115 groupes examinés :

| Deuxième mot | Groupes à un bloc | Correspondance avec la taille logique |
| --- | ---: | --- |
| `0x00200239` | 5 490 | 5 480 correspondent à une demi-surface arrondie. |
| `0x00200241` | 1 218 | 1 217 correspondent à une demi-surface arrondie. |
| `0x00200311` | 2 654 | 2 652 correspondent à une surface arrondie. |
| `0x012001b0` | 733 | Les 733 correspondent à deux fois la surface arrondie. |
| `0x002001b1` | 213 | Les 213 correspondent à deux fois la surface arrondie. |
| `0x002000e1` | 772 | Les 772 correspondent à quatre fois la surface arrondie. |

Ces corrélations suggèrent que le deuxième mot distingue des catégories de données ayant des tailles par surface différentes. Elles ne déterminent pas à elles seules un format de pixels, un codec ou le sens des bits. L'arrondi peut faire correspondre un même petit bloc à plusieurs multiples : les catégories ne sont donc pas exclusives. Les exceptions et les groupes à plusieurs blocs demandent une analyse séparée.

Exemple : la ligne 485 de `data/ttdb/graphics/ttdb_graphics.ttpf` porte le mot `0x00200239`, les dimensions candidates 1 024 × 1 024 et correspond au seul bloc 780, dont la taille logique vaut 524 288 octets. Le script de statistiques fournit jusqu'à trois exemples par valeur du mot pour faciliter les vérifications.

### Hypothèse sur les exceptions

Les dimensions candidates des dix exceptions pour `0x00200239` sont toutes étroites : cinq font 4 × 2 048 et cinq font 256 × 1 024. La seule exception pour `0x00200241` fait 256 × 1 024. Dans l'ensemble des groupes à un bloc des deux catégories, les tailles logiques correspondent toutes à `ceil4096(max(largeur, 512) × hauteur / 2)` : respectivement **5 490/5 490** et **1 218/1 218**. Par exemple, la ligne 1 183 de `data/ttdb/peds/ttdb_peds_0_3.ttpf` donne 4 × 2 048, un bloc logique de 524 288 octets et cette formule prédit bien 512 × 2 048 / 2 = 524 288.

Les deux exceptions pour `0x00200311` ont des hauteurs candidates de 128 et 64. Sur les **2 654 groupes à un bloc** portant ce mot, `ceil4096(largeur × max(hauteur, 256))` correspond à toutes les tailles logiques.

`ceil4096` arrondit à l'entier multiple de 4 096 supérieur ou égal. Ces formules décrivent les tailles observées dans ces sous-ensembles ; elles ne prouvent pas un alignement matériel, un format graphique précis ni la disposition des octets. D'autres formules peuvent aussi convenir : le script compare plusieurs minima et retourne les exceptions à la formule sans minimum pour permettre leur examen.

Les blocs 4051 de `ttdb_peds_0_3.ttpf` et 5477 de `ttdb_ui.ttpf`, correspondant à deux exceptions, sont marqués par le bit 29 et se décompressent complètement en zlib, respectivement à 524 288 et 262 144 octets. Les empreintes SHA-256 des données décompressées sont `52c79048e8ab11d010c70a103b0426ccfc4b1973ef7f4987435b3f9931533794` et `542744f291a7a0dadef72723df00997b24acb80f8397201bcc93a7460f947ac1`. La validation des tailles ne révèle pas l'agencement du contenu.

Un nouvel échantillon reproductible, `python .\inspect_zlib_padding.py .`, sélectionne avec la graine 42 jusqu'à 40 blocs marqués par le bit 29 par fichier parmi ceux dont les tailles physique et logique ne dépassent pas 2 000 000 octets. Les 2 159 blocs sélectionnés se décodent à la taille logique attendue. Pour 2 152 d'entre eux, les octets restants après le flux sont tous nuls ; les sept autres n'ont pas d'octets après le flux. Ce résultat est limité à cet échantillon et ne prouve pas que le remplissage est toujours nul. Cet échantillon est distinct de celui portant sur les 2 160 blocs de tous types cité plus haut.

Le bit 29 n'est pas déterminé par le seul deuxième mot ETPF : sur les groupes à un bloc de type `0x00200239`, il est actif 2 357 fois et inactif 3 133 fois. Il s'agit d'un comptage de drapeau sur l'ensemble de ces groupes ; le décodage zlib reste validé par échantillonnage, pas sur tous les blocs.

Sur les 57 fichiers, 108 610 blocs de données ont le bit 29 inactif. Leur taille physique bornée est inférieure à la taille logique pour 108 521 blocs, égale pour 46 et supérieure pour 43. Les bornes physiques peuvent inclure du remplissage. Pour la plupart de ces blocs, une simple copie des octets stockés ne pourrait donc pas produire la taille logique annoncée ; le codec ou la transformation nécessaire reste inconnu. `stats_etpf.py` reproduit ces comptes en parcourant toutes les tables, sans décoder ces blocs.

La lecture des deux premiers octets de chacun de ces 108 610 blocs donne 197 préfixes distincts ; **102 802** ont `de` comme deuxième octet. Les préfixes les plus fréquents sont `32de` (27 705), `31de` (22 165) et `33de` (15 860). Pour reproduire ce relevé, ajouter `--prefixes` à `stats_etpf.py`. La répétition suggère une structure commune, sans identifier le codec : 5 808 blocs possèdent un autre deuxième octet et les préfixes seuls ne valident aucune méthode de décompression.

Le relevé par deuxième mot ETPF fait apparaître plusieurs familles. Tous les blocs sans bit 29 des groupes dont le mot vaut `0x0220023b` (47 691 blocs), `0x0120023b` (20 373) ou `0x0320023b` (11 677) ont `de` en deuxième position. En revanche, parmi les 1 812 blocs sans bit 29 des groupes `0x00200313`, 1 751 ont `30` en deuxième position et 51 ont `31`. Ces comptes incluent les groupes à un ou plusieurs blocs. Ils indiquent une relation entre le champ ETPF et les octets stockés ; ils n'établissent pas si ces familles utilisent un même codec ou si leurs données représentent des pixels.

### Bits 24 à 29 de la table RDS5

Sur tous les blocs de données, la valeur `(mot_RDS5 >> 24) & 0x3f` prend huit valeurs seulement. Leur relation avec le deuxième octet physique est particulièrement nette :

| Bits 24 à 29 | Nombre de blocs | Deuxième octet observé |
| --- | ---: | --- |
| `0x20` | 918 223 | Non relevé par cette analyse des préfixes. Le bit 29 est actif ; les essais zlib décrits plus haut sont échantillonnés. |
| `0x04` | 102 725 | `de` pour les 102 725. |
| `0x10` | 77 | `de` pour les 77. |
| `0x14` | 333 | `db` pour les 333. |
| `0x0c` | 35 | `db` pour les 35. |
| `0x1c` | 5 167 | Plusieurs valeurs, surtout `30` (2 633) et `31` (2 003). |
| `0x18` | 268 | Plusieurs valeurs, surtout `31` (132) et `30` (67). |
| `0x00` | 5 | Plusieurs valeurs. |

Les 1 026 833 blocs comptés ici excluent les 57 intervalles initiaux ETPF. Les six bits constituent une classification candidate des données stockées, mais leur interprétation précise reste inconnue. La correspondance des octets est une observation sur cette copie, pas une preuve de codec. La commande `python .\stats_etpf.py . --prefixes` reproduit ce tableau et les distributions complètes.

Pour orienter la recherche, la documentation Microsoft indique que DirectStorage sur Xbox Series prend en charge plusieurs étapes, dont DEFLATE, BCPack et des réarrangements de données ([vue d'ensemble](https://learn.microsoft.com/en-us/gaming/gdk/docs/features/console/storage/directstorage/directstorage-overview), [modes BCPack](https://learn.microsoft.com/en-us/gaming/gdk/docs/reference/system/dstorage/enums/dstorage_bcpack_mode)). BCPack est une piste à examiner pour des données de texture, pas une identification de ces blocs : aucun décodage BCPack n'a été vérifié sur cette copie et les préfixes seuls ne démontrent pas son utilisation.

## Essai d'agencement de pixels

`python .\comparer_agencements_etpf.py .` sélectionne avec la graine 42 jusqu'à cinq groupes par fichier ayant les dimensions candidates 32 × 32, le deuxième mot `0x012000e0`, un seul bloc zlib et une taille logique de 4 096 octets. Sur cette copie, cela donne sept blocs. Le script traite les données comme quatre octets par pixel et calcule, pour les trois premiers octets de chaque pixel, l'écart absolu moyen entre voisins horizontaux et verticaux. Il compare un parcours linéaire et un parcours Morton dans des tuiles carrées de 4, 8, 16 ou 32 pixels ; un score plus petit indique des voisins plus similaires pour cette mesure.

Pour six des sept blocs, les variantes Morton 16 et Morton 32 obtiennent à égalité le meilleur score. Pour le dernier, la variante linéaire 32 est la meilleure. Les scores moyens sont environ 11,54 pour Morton 16 ou 32, contre 17,01 pour linéaire 32. Pour une image 32 × 32, les deux variantes Morton 16 et 32 produisent ici le même ordre ; cet essai ne les distingue donc pas.

Avec `--largeur 64 --hauteur 64`, l'échantillon contient 24 blocs : Morton 32 et 64 sont ex æquo pour le meilleur score sur 14 blocs, Morton 16 sur deux, Morton 8 sur trois et linéaire 4 sur cinq. Avec `--largeur 128 --hauteur 128`, l'échantillon contient 18 blocs : Morton 64 et 128 sont ex æquo pour le meilleur score sur sept blocs, Morton 32 sur quatre, Morton 4 sur un, linéaire 32 sur trois et linéaire 4 sur trois. À chaque taille carrée, les deux plus grandes tuiles Morton testées produisent le même ordre dans cette implémentation. La mesure de continuité et ces petits échantillons ne prouvent ni l'ordre réel des canaux, ni le type de pixel, ni une disposition générale. Ils justifient de tester ces agencements sur des ressources dont l'image de référence est connue.
