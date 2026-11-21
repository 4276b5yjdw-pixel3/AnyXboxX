# Jeu de test : SimpleTriangle

Un jeu de test légal qui tourne déjà à 100 % sur PC, pour comparer le comportement natif et celui d'AnyXboxX. Mesures du 21 novembre 2026.

## Pourquoi celui-ci

- **SimpleTriangle** est un échantillon officiel de Microsoft, publié sous licence MIT dans [microsoft/Xbox-GDK-Samples](https://github.com/microsoft/Xbox-GDK-Samples).
- Il existe en deux versions : `SimpleTriangle` pour Xbox Series X|S et `SimpleTriangleDesktop` pour PC. Le code de jeu est le même ; seule la couche plateforme change.
- La version Series X ne se compile qu'avec le GDKX, réservé aux studios sous accord de confidentialité. La version PC se compile avec le [GDK public](https://github.com/microsoft/GDK) : c'est elle qui sert de référence.
- Il est minuscule (une fenêtre, DirectX 12, deux shaders) mais passe par toutes les couches d'un vrai jeu GDK : démarrage C, `xgameruntime.dll`, fenêtre Win32, DirectX 12.

## Référence native

![SimpleTriangleDesktop exécuté nativement sur PC](images/simpletriangle-natif.png)

## Résultat dans AnyXboxX

| Étape du jeu | État |
|---|---|
| Chargement : exécutable + `libHttpClient`, `vcruntime140`, `vcruntime140_1`, `msvcp140` liés | ✅ |
| Démarrage C (`_initterm`, `argv`, locale, `_errno`…) puis entrée dans `WinMain` | ✅ |
| Chargement de `xgameruntime.dll` et `InitializeApiImplEx2` (initialisation GDK) | ✅ |
| Création de la fenêtre (`RegisterClassExW`, `CreateWindowExW`, boucle de messages) | ❌ prochaine étape |
| Création du périphérique DirectX 12 (`CreateDXGIFactory2`, `D3D12CreateDevice`…) | ❌ |
| Affichage du triangle | ❌ |

Fonctions importées : 202, dont **157 résolues (77,7 %)** : 75 émulées en Python et 82 fournies par les DLL Visual C++. Les 45 restantes sont surtout `USER32` (fenêtre, souris, messages), `d3d12`, `dxgi` et les fichiers du CRT.

## Ce que le test a appris

1. **Sur PC, le GDK passe par une interface interne.** Le jeu ne lie pas `XGameRuntimeInitialize` directement : `xgameruntime.lib` charge `xgameruntime.dll`, puis demande `QueryApiImpl`, `InitializeApiImpl`, `InitializeApiImplEx`, `InitializeApiImplEx2`, `XErrorReport` et `UninitializeApiImpl` par `GetProcAddress`. Chaque API `X*` obtient ensuite une interface par `QueryApiImpl`. AnyXboxX accepte l'initialisation et ne fournit pas encore d'interface.
2. **Les DLL Visual C++ ne sont pas dans le dossier du jeu sur PC**, contrairement à un paquet console. Il faut donner leur dossier à AnyXboxX.
3. **Une fonction absente qui renvoie un pointeur fait planter** à l'adresse `0x80004001`. Le traçage a permis d'émuler chaque fonction dans l'ordre où le jeu en a besoin.

## Reproduire

Prérequis : Visual Studio 2022 ou 2026 avec la charge C++, et le GDK public (`winget install Microsoft.Gaming.GDK`).

```powershell
git clone --filter=blob:none --sparse https://github.com/microsoft/Xbox-GDK-Samples.git
cd Xbox-GDK-Samples
git sparse-checkout set --no-cone /Samples/IntroGraphics/SimpleTriangleDesktop/ /Kits/ATGTK/ /Kits/ATGTelemetry/ /Kits/DirectXTK12/
```

Ensuite :

1. Placer le paquet NuGet `WinPixEventRuntime.1.0.240308001` dans `Samples\packages\`.
2. Lancer `Kits\DirectXTK12\Src\Shaders\CompileShaders.cmd dxil` avec son chemin complet.
3. Compiler `SimpleTriangleDesktop.sln` en `Release|x64`, avec `-p:PlatformToolset=v145` sous VS 2026.

Analyse dans AnyXboxX, avec le dossier des DLL Visual C++ en second argument :

```powershell
python PrototypeScarlett\scarlett.py --rapport <...>\x64\Release\SimpleTriangleDesktop.exe "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Redist\MSVC\<version>\x64\Microsoft.VC145.CRT"
```

## Instructions processeur et shaders

- **Processeur** : la Series X utilise un AMD Zen 2 en x86-64, le même jeu d'instructions qu'un PC. Rien n'est à traduire. Seules les extensions AVX/AVX2 manquent dans Unicorn ; l'exécution native les apportera.
- **Shaders** : la version PC utilise des shaders DXIL standard (`VertexShader.cso`, `PixelShader.cso`) que le pilote du PC exécute. Sur console, les shaders seraient livrés compilés pour le GPU RDNA 2 (à vérifier sur un binaire Scarlett légal). Les traduire demanderait un recompilateur RDNA 2 → SPIR-V ou DXIL, comme celui de l'émulateur PS4 libre shadPS4 pour le GPU GCN. AMD publie la documentation du jeu d'instructions RDNA 2.
