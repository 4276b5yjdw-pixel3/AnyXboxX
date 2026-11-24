> English: [running-gta6.md](../running-gta6.md)

# Lancer GTA VI (build Xbox Series 1.0.2.1) avec AnyXboxX

Ce guide explique comment installer et lancer le projet, et tout ce qu'il faut installer pour refaire nos essais sur le build Xbox Series 1.0.2.1 de GTA VI, jusqu'au point où nous en sommes : la première cinématique. Il ne fournit pas le jeu et n'explique pas comment l'obtenir : vous apportez votre propre copie. Ne mettez jamais de fichier du jeu dans ce dépôt et ne les joignez à aucune issue.

Le lancement passe par [VIctory](https://github.com/Marvisak/VIctory) (Marvisak, GPL-3.0 ou ultérieure), suivi ici comme sous-module `third_party/victory` (fork `LooperSalty/victory`, branche `anyxboxx/stable`). Le script `tools/lancer_victory.ps1` le compile et le lance sur votre dossier du jeu.

## Ce que vous obtenez aujourd'hui

Mesuré le 2026-11-24 sur i7-13700KF + RTX 4070 SUPER, Windows 11 :

- Le démarrage, l'écran de profil, les réglages de première exécution, les écrans légaux, le chargement et le menu pause fonctionnent, à 30 i/s dans les menus.
- La première cinématique (crédits d'ouverture de la mission 1) est atteinte.
- La scène 3D derrière les crédits est noire (les passes d'éclairage ne sont pas encore traduites).
- Dans le monde, le jeu tourne à 0,3 à 0,6 image par seconde.
- Il n'est pas jouable.

## Prérequis

- Windows 10 ou 11 x64.
- Un processeur avec AVX2. Intel convient : les instructions propres à AMD sont émulées.
- Un GPU Direct3D 12 avec shader model 6.6 et mesh shaders (NVIDIA RTX série 20 ou plus récent, AMD RDNA 2 ou plus récent).
- 32 Go de RAM conseillés et un fichier d'échange Windows assez grand : le jeu engage plusieurs Gio au démarrage. Sinon, `crashes.log` signale l'erreur Windows 1455 : fermez d'autres applications ou agrandissez le fichier d'échange.
- Votre propre copie du build Xbox Series 1.0.2.1 : un dossier qui contient `game_scarlett_master.exe`. Non fournie, non expliquée ici.
- De l'espace disque pour le cache de shaders (il grossit au fil du jeu ; voir la page d'état pour les chiffres à prévoir).

## Installation

1. [Git](https://git-scm.com/).
2. Rust via [rustup](https://rustup.rs/). La toolchain exacte est fixée par le `rust-toolchain.toml` du sous-module et s'installe seule à la première commande `cargo`.
3. Visual Studio 2022 ou 2026 Build Tools avec la charge « Développement Desktop en C++ » (MSVC).
4. Windows SDK 10.0.26100 (fournit `dxc`).
5. Optionnel : la fonctionnalité Windows « Graphics Tools » (couche de débogage D3D12, utile seulement pour `VICTORY_D3D12_DEBUG`).
6. Python 3.12, seulement pour la suite de tests d'AnyXboxX (voir Tests).

Récupérer le code avec son sous-module :

```powershell
git clone --recurse-submodules https://github.com/LooperSalty/AnyXboxX.git
cd AnyXboxX
# ou, dans un clone existant :
git submodule update --init third_party/victory
```

## Compilation

```powershell
cargo build --profile diag -p victory --features diagnostics --manifest-path third_party/victory/Cargo.toml
```

Le profil `diag` est nécessaire pour les touches scriptées, les captures d'images et les options de diagnostic ci-dessous. La première compilation télécharge et compile toutes les dépendances : comptez plusieurs minutes. L'exécutable est `third_party\victory\target\diag\victory.exe` (ou `%CARGO_TARGET_DIR%\diag\victory.exe` si cette variable est définie). `tools/lancer_victory.ps1` lance cette compilation à votre place quand l'exécutable manque.

## Lancement

```powershell
.\tools\lancer_victory.ps1 -GameDir <dossier du jeu>
```

Le script règle trois variables puis exécute `victory.exe run <dossier du jeu>\game_scarlett_master.exe --execute` :

| Variable | Valeur | Pourquoi |
| --- | --- | --- |
| `VICTORY_GAME_DIR` | votre dossier du jeu | Aucun `victory.toml` n'est nécessaire. |
| `VICTORY_CAPPED_DYNAMIC` | `262144` | NVIDIA plafonne le tas de descripteurs à 1 000 000 d'entrées. Avec la plage dynamique par défaut, environ 720 dessins indirects par image étaient abandonnés ; avec 262 144 emplacements, ils ne le sont plus. |
| `VICTORY_SHADER_LOOP_LIMIT` | `32` | Les boucles des shaders traduits étaient quasi infinies ; avec une limite de 32 itérations, le GPU est environ 6 fois plus rapide. |

`-SkipPipelines <hash,...>` est transmis à `VICTORY_SKIP_PIPELINES` (voir plus bas).

Où sont les choses :

- Sauvegardes, réglages et `crashes.log` : `%LOCALAPPDATA%\victory\data`.
- Données dérivées (caches de shaders et de pipelines) : `%LOCALAPPDATA%\victory\cache`.

Les deux sont volontairement hors du dépôt. Supprimez le dossier du cache pour repartir d'un cache vide ; gardez le dossier des données si vous voulez conserver votre sauvegarde.

## Arriver à la première cinématique

Le titre de la fenêtre affiche la fréquence d'images. La fenêtre doit avoir le focus.

1. Écran de profil : Entrée.
2. Réglages de première exécution : Entrée à chaque écran.
3. Mentions légales : descendre sur « Suivant », attendre la fin du compte à rebours de l'avertissement de photosensibilité, cocher les deux cases, puis « Confirmer ».
4. Chargement, puis la première cinématique (crédits d'ouverture).
5. Échap ouvre le menu pause.

Clavier ou manette. Sans manette XInput branchée, le clavier sert de manette tant que la fenêtre du titre a le focus :

| Touches | Manette |
| --- | --- |
| Entrée, Retour arrière, X, Y | A, B, X, Y |
| Flèches | croix directionnelle |
| W A S D / I J K L | stick gauche / stick droit |
| Q / E, Z / C | gâchettes hautes, gâchettes basses |
| F / H | clics de sticks |
| Échap | Menu |
| Tab | View |

Maintenez chaque touche un instant : le jeu lit l'entrée à 30 Hz, un appui très bref peut être manqué. Les lancements suivants reprennent directement la sauvegarde.

## Lancements scriptés et diagnostics

Ils demandent le build `diag`.

| Variable | Effet |
| --- | --- |
| `VICTORY_KEYS=40:Enter,55:Enter,70:Enter` | Appuie sur les touches à ces secondes, avec ou sans focus. |
| `VICTORY_CAPTURE=<dossier>` et `VICTORY_CAPTURE_FRAMES=<liste>` | Enregistre les images présentées (ces numéros d'image). |
| `VICTORY_SHOW_TARGET=busiest` | Affiche la cible de rendu la plus chargée à la place de l'image finale (par exemple le G-buffer). |
| `VICTORY_D3D12_DRED=1` | En cas de panne du GPU, donne les commandes en cours. |
| `VICTORY_D3D12_DEBUG=1` | Couche de débogage D3D12 (Graphics Tools requis). |
| `VICTORY_GPU_TIMING=1` | Chronomètre chaque liste de commandes et journalise les lentes. |
| `VICTORY_SKIP_PIPELINES=<hash,...>` | Omet les dessins et dispatchs qui utilisent les hash de shader à 16 chiffres listés. |
| `VICTORY_LOG=<cible>=debug,...` | Sortie debug et trace. |

Pour arrêter le jeu : `taskkill /F /IM victory.exe`. La commande `timeout` de Git Bash ne tue pas l'exécutable.

## Branche expérimentale

```powershell
git -C third_party/victory fetch origin anyxboxx/essai
git -C third_party/victory checkout FETCH_HEAD
```

C'est la branche `anyxboxx/essai` du fork : la stable plus la prise en charge des UAV racine et des accès LDS octet et demi-mot. Lancez-la avec `VICTORY_SKIP_BVH_BUILDER=1` : le constructeur BVH du ray tracing du jeu, traduit à moitié, bloquait le GPU au début de la cinématique. Sans cette option, `DXGI_ERROR_DEVICE_HUNG` est garanti à ce moment. Ensuite, revenez à la branche stable (`git -C third_party/victory checkout anyxboxx/stable`).

## Sécurité

- Sur NVIDIA, rester longtemps dans le monde peut provoquer une réinitialisation du pilote d'affichage (tous les écrans noirs un instant), et un testeur a eu un écran bleu (0x119). Arrêtez le jeu après quelques minutes dans le monde.
- Ne lancez qu'une instance à la fois.

## Tests

```powershell
cargo test -p victory-gpu -p victory-shader --manifest-path third_party/victory/Cargo.toml
```

AnyXboxX lui-même (voir la section Setup d'[AGENTS.md](../../AGENTS.md)) :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check --select W605,F,E9 PrototypeScarlett tests tools
```

## Où signaler un problème

Ouvrez une issue sur [AnyXboxX](https://github.com/LooperSalty/AnyXboxX/issues) ou sur [VIctory](https://github.com/Marvisak/VIctory/issues) (l'issue #264 regroupe les blocages GPU sur NVIDIA). Décrivez le symptôme, votre GPU et votre pilote, et les lignes utiles de `crashes.log`. Ne joignez jamais de fichier du jeu.
