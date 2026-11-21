# AnyXboxX — Xbox-Series-X-Emulator (Prototyp)

[Français](../../README.md) · [English](README.en.md) · [Español](README.es.md) · **Deutsch** · [Italiano](README.it.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [中文](README.zh-CN.md)

AnyXboxX lädt Xbox-GDK-Programmdateien (Format PE32+ x86-64) und führt deren Code mit Unicorn aus. Die Systemfunktionen der Konsole werden im nativen Modus durch eine C++-Runtime und in der isolierten Maschine durch Python-Code ersetzt (High-Level-Emulation, wie bei WinDurango oder Wine). Das Programm gibt sich als Xbox Series X aus: `XSystemGetDeviceType` liefert `XboxScarlettAnaconda` zurück.

![Fahrdemo, die in AnyXboxX läuft](../images/demo-conduite.png)

## Fortschritt der Übersetzung

![Fortschritt der Übersetzung der Xbox Series X](../images/traduction.svg)

- **Prozessorbefehle: 100 %.** Die Series X nutzt einen AMD Zen 2 in x86-64, denselben Befehlssatz wie ein PC: Im nativen Modus läuft der Code des Spiels unverändert, ohne Übersetzung.
- **GPU-Befehle: 0 %.** Die Shader eines Konsolenspiels sind für die RDNA-2-GPU der Series X kompiliert. Nötig ist ein Rekompilierer RDNA 2 → DXIL, der noch nicht begonnen wurde.
- **Systemfunktionen: 66 %** der 1 337 Funktionen, die von den DLLs des Testpakets importiert werden, sind im isolierten Modus aufgelöst.
- **Konsolenspezifische DLLs**: `xmem.dll` (3/4) und `d3d12_xs.dll` (2/2) sind für die vom Paket genutzten Funktionen übersetzt. Die Erstellung des D3D12.X-Geräts muss noch geschrieben werden.
- **GDK-Runtime: 27 der 396 Funktionen** (Aufgabenwarteschlange `XTaskQueue`, `XAsync`, `XThread`) sind in AnyXboxX in C++ geschrieben. Sie kommen zum Einsatz, wenn AnyXboxX die Runtime allein verwaltet: ohne Gaming Services oder mit `ANYXBOXX_SYSTEM_RUNTIME=0`. Ist die GDK-Runtime von Windows vorhanden, bedient sie alle Schnittstellen, auch die Aufgabenwarteschlange, da ihre APIs nur ihre eigenen Warteschlangen akzeptieren. Die Ablaufverfolgung (`ANYXBOXX_TRACE=1`) nennt jede angeforderte Schnittstelle.

Die Grafik wird mit `scarlett.py --traduction <Paketordner> docs/images/traduction.svg` neu erzeugt.

## Projektfortschritt

| Schritt | Status |
|---|---|
| `MicrosoftGame.Config` einlesen (TitleId, Identität, Scarlett-Programmdatei) | ✅ erledigt |
| PE32+-Laden: Sektionen und Schutzattribute, Relokationen, Importe, Exporte | ✅ erledigt |
| TLS: Kopie der Vorlage, Index, Callbacks | ✅ erledigt |
| TEB und PEB über das GS-Register erreichbar | ✅ erledigt |
| HLE-Seite: 158 emulierte Funktionsnamen aus GDK, Kernel, CRT und Mathematik | ✅ erledigt |
| Unbekannte Funktionen: `E_NOTIMPL` und Protokolleintrag statt Ablehnung | ✅ erledigt |
| Globale C++-Konstruktoren (`_initterm`) als Gast-Code | ✅ erledigt |
| Kompatibilitätsbericht (`--rapport`) und Prüfstand (`--banc`) | ✅ erledigt |
| Mehrere verknüpfte Module in derselben Maschine: DLLs des Pakets, Ordinale, Weiterleitungen, Relokation bei Konflikten | ✅ erledigt |
| `GetModuleHandle`, `GetProcAddress`, `LoadLibrary`, `RtlPcToFileHeader` | ✅ erledigt |
| 16/16 DLLs eines Scarlett-Pakets samt Abhängigkeiten initialisiert, 0 nicht emulierte Aufrufe | ✅ erledigt |
| Freies Testspiel `SimpleTriangle` kompiliert: C-Start und GDK-Initialisierung laufen in AnyXboxX | ✅ erledigt |
| Native Ausführung nach Wine-Art (`--natif`): **SimpleTriangle wird angezeigt**, GDK-Runtime von AnyXboxX bereitgestellt | ✅ erledigt |
| Zweites freies Testspiel, `testgdk` aus SDL3: **läuft im nativen Modus** (Fenster, Sprites, Ton) | ✅ erledigt |
| Isolierter Start eines Pakets oder einer exe (`--lancer`) mit der Liste der zu emulierenden Aufrufe | ✅ erledigt |
| C++-Runtime (`runtime/`): `xgameruntime.dll`, `xmem.dll`, `d3d12_xs.dll` im nativen Modus vorgeladen und allen DLLs des Spiels bereitgestellt | ✅ erledigt |
| `xmem.dll`: `XMemAlloc`, `XMemFree`, Hooks, `XMemVirtualQuery` | ✅ erledigt |
| `d3d12_xs.dll`: Serialisierung der Root-Signaturen, umgeleitet auf das D3D12 des PCs | ✅ erledigt |
| Tabelle der 396 GDK-Funktionen: Schnittstelle und Methodennummer, aus `xgameruntime.lib` extrahiert (`tools/gdk_interfaces.py`) | ✅ erledigt |
| `XTaskQueue`, `XAsync`, `XThread` von AnyXboxX bereitgestellt: testgdk läuft ohne die Runtime von Windows | ✅ erledigt |
| Übrige GDK-Schnittstellen: an die GDK-Runtime von Windows delegiert, von der Ablaufverfolgung benannt | 🟡 in Arbeit |
| 123 automatisierte Tests | ✅ erledigt |
| D3D12.X: `D3D12XboxCreateDevice` und die `ID3D12*`-Schnittstellen der Konsole | ⏳ offen |
| Übrige von AnyXboxX geschriebene GDK-Schnittstellen (`XUser`, `XGameSave`, `XSystem`…) | ⏳ offen |
| Shader-Rekompilierer RDNA 2 → DXIL | ⏳ offen |
| x64-SEH-Ausnahmen (`.pdata`), mehrere Threads | ⏳ offen |
| Dynamisches Laden einer DLL zur Laufzeit (`LoadLibrary` + `DllMain`) | ⏳ offen |
| D3D12.X-Grafik nach Direct3D 12 / Vulkan | ⏳ offen |
| Audio, Controller, `XGameSave`-Spielstände | ⏳ offen |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="Das Auto biegt nach rechts ab" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="Kompatibilitätsbericht der Demo" width="380"></td>
</tr>
<tr>
<td align="center">Die Demo reagiert auf die Pfeiltasten der Tastatur.</td>
<td align="center">Das Protokoll zeigt den Kompatibilitätsbericht an.</td>
</tr>
</table>

## Die Demo ausprobieren

Installiere unter Windows 64-Bit-Python 3.12 mit Tcl/Tk und öffne dann PowerShell im Stammverzeichnis des Repositorys.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

Der native Modus braucht die C++-Runtime. Sie wird mit Visual Studio 2022 oder 2026 (C++-Workload) und CMake kompiliert:

```powershell
cmake -S runtime -B runtime/build -A x64
cmake --build runtime/build --config Release
```

Die Aufgabenwarteschlange übernimmt das Modul `Task` von [libHttpClient](https://github.com/microsoft/libHttpClient) (MIT-Lizenz, `runtime/third_party/libhttpclient-task`). Die DLLs landen in `runtime/build/bin` oder in dem Ordner, den `ANYXBOXX_RUNTIME` angibt. `ANYXBOXX_SYSTEM_RUNTIME=0` schaltet die Delegation an die GDK-Runtime von Windows ab.

Das kompilierte Demoprogramm ist `PrototypeScarlett/demo.pe`; sein Quellcode ist `PrototypeScarlett/demo.c`.

## Ein Spiel im nativen Modus starten

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --natif <dossier ou fichier .exe> [dossiers de DLL…]
```

![SimpleTriangle, von AnyXboxX im nativen Modus gestartet](../images/simpletriangle-anyxboxx.png)

AnyXboxX lädt die Programmdatei selbst und führt sie direkt auf dem Prozessor aus, wie Wine. Die Xbox-Runtime (`xgameruntime.dll`) wird von AnyXboxX bereitgestellt; das Fenster und DirectX 12 stammen vom PC. **Achtung: Im nativen Modus ist das Programm nicht isoliert.** Verwende diesen Modus nur für vertrauenswürdige Programme; `--rapport` und `--banc` bleiben in Unicorn isoliert. `ANYXBOXX_TRACE=1` zeigt die abgefangenen Aufrufe an. Details: [docs/jeu-de-test.md](../jeu-de-test.md) (auf Französisch).

## Ein Paket im isolierten Modus starten

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --lancer <dossier du paquet ou fichier .exe> [dossiers de DLL…]
```

Bei einem Ordner liest AnyXboxX `MicrosoftGame.Config`, nimmt die für `Scarlett` deklarierte ausführbare Datei und startet sie in der isolierten Maschine (Unicorn): Das Programm berührt den PC nicht. Der Bericht nennt zuerst die nicht aufgelösten Importe, dann die nicht emulierten Aufrufe, vom häufigsten zum seltensten: Das ist die Arbeitsliste zur Vervollständigung des Emulators. Fehlt die ausführbare Datei, nennt die Meldung sie beim Namen.

## Ein Programm analysieren

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

Der Prüfstand lädt alle PE-Module eines Ordners und führt deren Initialisierung aus:

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Prüfstand für die DLLs eines Scarlett-Pakets](../images/banc-dll.svg)

Detaillierte Ergebnisse: [docs/avancee.md](../avancee.md) (auf Französisch). Freies Testspiel im Vergleich zu seiner nativen Ausführung: [docs/jeu-de-test.md](../jeu-de-test.md) (auf Französisch). Ein zusätzlicher DLL-Ordner (zum Beispiel die Visual-C++-DLLs) kann auf das Ziel folgen: `--rapport <cible> <dossier>`.

Der Bericht listet die importierten Funktionen, den bereits emulierten Anteil in Prozent und die fehlenden Funktionen auf. In der Oberfläche liest die Schaltfläche **Ouvrir un dossier Xbox…** (Xbox-Ordner öffnen) die Datei `MicrosoftGame.Config`, zeigt diesen Bericht an und startet dann das Programm; jeder nicht emulierte Aufruf erscheint im Protokoll.

## Architektur

![Schema der Module von AnyXboxX](../images/architecture.svg)

| Modul | Aufgabe |
|---|---|
| `emu/config.py` | liest das Manifest des GDK-Pakets |
| `emu/loader.py` | lädt das PE-Image und bereitet Importe, Exporte und TLS vor |
| `emu/machine.py` | Unicorn-Prozessor, Stack, Heap, TEB/PEB, Verteilung der Aufrufe |
| `emu/hle/` | emulierte Funktionen: `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | Kompatibilitätsbericht |
| `emu/modules.py` | lädt die DLLs des Pakets, bindet die Importe und ordnet die Initialisierungen |
| `emu/bench.py` | Prüfstand für einen Ordner mit Modulen |
| `emu/native/` | native Ausführung nach Wine-Art: Loader, echte Importe, GDK-Runtime von AnyXboxX |
| `scarlett.py` | Tkinter-Oberfläche und Kommandozeile |

Um eine Funktion hinzuzufügen, dekoriere einen Handler in `emu/hle/`:

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## Recherche

- [Hardware-Architektur der Xbox Series X](../recherche/architecture-xbox-series-x.md) (auf Französisch): Zen-2-CPU, RDNA-2-GPU, Speicher, Velocity Architecture, Sicherheit.
- [Bestehende Emulatoren und Kompatibilitätsschichten](../recherche/etat-de-l-art.md) (auf Französisch): WinDurango, XWine1, Xenia, XVD-Werkzeuge.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Mitwirken

Der Branch `main` ist geschützt: Jeder Beitrag läuft über einen geprüften Pull Request, und die Tests müssen bestehen. Fehler und zu emulierende Funktionen werden in den Issues gemeldet. Die vollständigen Regeln stehen in [CONTRIBUTING.md](../../CONTRIBUTING.md) (auf Französisch).

## Einschränkungen

AnyXboxX ist ein Prototyp. Er führt keine kommerziellen Spiele aus: Diese benötigen die GPU der Konsole (D3D12.X) und zahlreiche Systemdienste und werden in verschlüsselten Containern ausgeliefert, deren Schlüssel in der Konsole verbleiben. Das Projekt enthält und akzeptiert keine geschützten Inhalte.
