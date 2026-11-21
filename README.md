# Émulateur Xbox — prototype Scarlett

Ce prototype Windows charge des exécutables PE x86-64 et exécute leurs instructions avec Unicorn. Il émule l’appel GDK `XSystemGetDeviceType` avec la valeur correspondant à une Xbox Series X. La démo de conduite incluse dessine chaque image dans un tampon de pixels et répond aux flèches gauche et droite.

## Essayer la démo

Sous Windows, installe Python 3.12 64 bits avec Tcl/Tk et le lanceur Python, puis ouvre PowerShell à la racine du dépôt.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

Le programme invité compilé est inclus dans `PrototypeScarlett/demo.pe`. Son code source se trouve dans `PrototypeScarlett/demo.c`.

## Ouvrir un programme

Le bouton **Ouvrir un dossier Xbox…** lit le fichier `MicrosoftGame.Config` du dossier choisi et recherche un exécutable déclaré pour `Scarlett`. La fenêtre affiche le nom du fichier manquant ou le premier import non pris en charge.

La démo utilise un affichage logiciel propre au prototype. Les jeux commerciaux, dont GTA VI, demandent des fonctions graphiques et des services système que ce prototype ne prend pas en charge.
