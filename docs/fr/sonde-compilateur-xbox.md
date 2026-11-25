# Sonde locale du compilateur Xbox

`tools/sonde_compilateur_xbox.py` compile un petit pixel shader HLSL original avec les bibliotheques graphiques Xbox fournies localement. L'outil copie les fichiers necessaires dans un dossier temporaire, lance `dxc.exe` du SDK Windows avec les DLL locales `dxcompiler_xs.dll`, `xbsc_xs.dll` et `newbe_xs.dll`, puis efface les sorties temporaires. Il n'extrait aucun shader de jeu. Les DLL ne sont ni incluses ni telechargees.

```powershell
python tools/sonde_compilateur_xbox.py --dxc "C:\chemin\dxc.exe" --dll-dir "C:\chemin\dll-locales" --victory "C:\chemin\victory.exe"
```

`dxil.dll` doit se trouver a cote de `dxc.exe`. L'argument facultatif `--victory` verifie la sortie avec `victory shader-info` et exige la reconnaissance d'un shader pixel natif. La sonde signale les fichiers absents et les erreurs de compilation ; sa reussite ne prouve ni la traduction d'un shader du jeu, ni son execution sur GPU PC, ni la correction des graphismes.

Mesure sur Windows 11 avec les DLL locales de l'utilisateur : sans `newbe_xs.dll`, la compilation complete signalait l'absence du backend. Avec elle, le shader synthetique a compile et VIctory a reconnu un conteneur pixel avec du code natif. Un seul shader et ces versions locales des DLL ont ete testes.
