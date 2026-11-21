# AnyXboxX — emulatore Xbox Series X (prototipo)

[Français](../../README.md) · [English](README.en.md) · [Español](README.es.md) · [Deutsch](README.de.md) · **Italiano** · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [中文](README.zh-CN.md)

AnyXboxX carica eseguibili Xbox GDK (formato PE32+ x86-64) ed esegue il loro codice con Unicorn. Le funzioni di sistema della console sono sostituite da un runtime C++ in modalità nativa e da codice Python nella macchina isolata (emulazione ad alto livello, come WinDurango o Wine). Il programma si presenta come una Xbox Series X: `XSystemGetDeviceType` restituisce `XboxScarlettAnaconda`.

![Demo di guida eseguita in AnyXboxX](../images/demo-conduite.png)

## Avanzamento della traduzione

![Avanzamento della traduzione di Xbox Series X](../images/traduction.svg)

- **Istruzioni del processore: 100%.** La Series X usa un AMD Zen 2 in x86-64, lo stesso set di istruzioni di un PC: in modalità nativa il codice del gioco viene eseguito così com'è, senza traduzione.
- **Istruzioni della GPU: 0%.** Gli shader di un gioco per console sono compilati per la GPU RDNA 2 della Series X. Serve un ricompilatore RDNA 2 → DXIL, non ancora iniziato.
- **Funzioni di sistema: 66%** delle 1 337 funzioni importate dalle DLL del pacchetto di prova sono risolte in modalità isolata.
- **DLL proprie della console**: `xmem.dll` (3/4) e `d3d12_xs.dll` (2/2) sono tradotte per le funzioni che il pacchetto usa. La creazione del dispositivo D3D12.X resta da scrivere.
- **Runtime GDK: 71 delle 396 funzioni** sono scritte in AnyXboxX, in C++: la coda di attività (`XTaskQueue`, `XAsync`, `XThread`) e l'utente (`XUser`, un profilo locale offline). Entrano in gioco quando AnyXboxX gestisce il runtime da solo: senza Gaming Services, oppure con `ANYXBOXX_SYSTEM_RUNTIME=0`. Se il runtime GDK di Windows è presente, serve tutte le interfacce, coda di attività compresa, perché le sue API accettano solo le proprie code. La traccia (`ANYXBOXX_TRACE=1`) nomina ogni interfaccia richiesta.

Il grafico viene rigenerato con `scarlett.py --traduction <cartella del pacchetto> docs/images/traduction.svg`.

## Avanzamento del progetto

| Fase | Stato |
|---|---|
| Lettura di `MicrosoftGame.Config` (TitleId, identità, eseguibile Scarlett) | ✅ fatto |
| Caricamento PE32+: sezioni e protezioni, rilocazioni, importazioni, esportazioni | ✅ fatto |
| TLS: copia del modello, indice, callback | ✅ fatto |
| TEB e PEB accessibili tramite il registro GS | ✅ fatto |
| Pagina HLE: 158 nomi di funzioni GDK, kernel, CRT e matematiche emulati | ✅ fatto |
| Funzioni sconosciute: `E_NOTIMPL` e voce nel registro invece di un rifiuto | ✅ fatto |
| Costruttori C++ globali (`_initterm`) eseguiti come codice guest | ✅ fatto |
| Rapporto di compatibilità (`--rapport`) e banco di prova (`--banc`) | ✅ fatto |
| Più moduli collegati nella stessa macchina: DLL del pacchetto, ordinali, reindirizzamenti, rilocazione in caso di conflitto | ✅ fatto |
| `GetModuleHandle`, `GetProcAddress`, `LoadLibrary`, `RtlPcToFileHeader` | ✅ fatto |
| 16/16 DLL di un pacchetto Scarlett inizializzate con le loro dipendenze, 0 chiamate non emulate | ✅ fatto |
| Gioco di test libero `SimpleTriangle` compilato: l'avvio C e l'inizializzazione GDK funzionano in AnyXboxX | ✅ fatto |
| Esecuzione nativa in stile Wine (`--natif`): **SimpleTriangle viene mostrato**, runtime GDK fornito da AnyXboxX | ✅ fatto |
| Secondo gioco di prova libero, `testgdk` di SDL3: **funziona in modalità nativa** (finestra, sprite, audio) | ✅ fatto |
| Avvio isolato di un pacchetto o di un exe (`--lancer`) con l'elenco delle chiamate da emulare | ✅ fatto |
| Runtime C++ (`runtime/`): `xgameruntime.dll`, `xmem.dll`, `d3d12_xs.dll` precaricate in modalità nativa e servite a tutte le DLL del gioco | ✅ fatto |
| `xmem.dll`: `XMemAlloc`, `XMemFree`, hook, `XMemVirtualQuery` | ✅ fatto |
| `d3d12_xs.dll`: serializzazione delle root signature, reindirizzata al D3D12 del PC | ✅ fatto |
| Tabella delle 396 funzioni GDK: interfaccia e numero di metodo, estratti da `xgameruntime.lib` (`tools/gdk_interfaces.py`) | ✅ fatto |
| `XTaskQueue`, `XAsync`, `XThread` servite da AnyXboxX: testgdk funziona senza il runtime di Windows | ✅ fatto |
| Altre interfacce GDK: delegate al runtime GDK di Windows, nominate dalla traccia | 🟡 in corso |
| 129 test automatizzati | ✅ fatto |
| D3D12.X: `D3D12XboxCreateDevice` e interfacce `ID3D12*` della console | ⏳ da fare |
| `XUser` offline: profilo locale sempre connesso, gamertag configurabile (`ANYXBOXX_GAMERTAG`), accesso di testgdk riuscito | ✅ fatto |
| Altre interfacce GDK scritte da AnyXboxX (`XGameSave`, `XSystem`, `XStore`…) | ⏳ da fare |
| Ricompilatore di shader RDNA 2 → DXIL | ⏳ da fare |
| Eccezioni SEH x64 (`.pdata`), thread multipli | ⏳ da fare |
| Caricamento dinamico di una DLL durante l'esecuzione (`LoadLibrary` + `DllMain`) | ⏳ da fare |
| Grafica D3D12.X verso Direct3D 12 / Vulkan | ⏳ da fare |
| Audio, controller, salvataggi `XGameSave` | ⏳ da fare |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="L'auto gira verso destra" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="Rapporto di compatibilità della demo" width="380"></td>
</tr>
<tr>
<td align="center">La demo risponde alle frecce della tastiera.</td>
<td align="center">Il registro mostra il rapporto di compatibilità.</td>
</tr>
</table>

## Provare la demo

Su Windows, installa Python 3.12 a 64 bit con Tcl/Tk, poi apri PowerShell nella radice del repository.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

La modalità nativa ha bisogno del runtime C++. Si compila con Visual Studio 2022 o 2026 (carico di lavoro C++) e CMake:

```powershell
cmake -S runtime -B runtime/build -A x64
cmake --build runtime/build --config Release
```

La coda di attività riprende il modulo `Task` di [libHttpClient](https://github.com/microsoft/libHttpClient) (licenza MIT, `runtime/third_party/libhttpclient-task`). Le DLL finiscono in `runtime/build/bin`, o nella cartella indicata da `ANYXBOXX_RUNTIME`. `ANYXBOXX_SYSTEM_RUNTIME=0` disattiva la delega al runtime GDK di Windows.

Il programma dimostrativo compilato è `PrototypeScarlett/demo.pe`; il suo codice sorgente è `PrototypeScarlett/demo.c`.

## Avviare un gioco in modalità nativa

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --natif <dossier ou fichier .exe> [dossiers de DLL…]
```

![SimpleTriangle avviato da AnyXboxX in modalità nativa](../images/simpletriangle-anyxboxx.png)

AnyXboxX carica l'eseguibile stesso e lo esegue direttamente sul processore, come Wine. Il runtime Xbox (`xgameruntime.dll`) è fornito da AnyXboxX; la finestra e DirectX 12 sono quelli del PC. **Attenzione: in modalità nativa il programma non è isolato.** Riserva questa modalità ai programmi di fiducia; `--rapport` e `--banc` restano isolati in Unicorn. `ANYXBOXX_TRACE=1` mostra le chiamate intercettate. Dettagli: [docs/jeu-de-test.md](../jeu-de-test.md) (in francese).

## Avviare un pacchetto in modalità isolata

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --lancer <dossier du paquet ou fichier .exe> [dossiers de DLL…]
```

Con una cartella, AnyXboxX legge `MicrosoftGame.Config`, prende l'eseguibile dichiarato per `Scarlett` e lo avvia nella macchina isolata (Unicorn): il programma non tocca il PC. Il resoconto indica prima gli import non risolti, poi le chiamate non emulate, dalla più frequente alla più rara: è l'elenco di lavoro per completare l'emulatore. Se l'eseguibile manca, il messaggio lo nomina.

## Analizzare un programma

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

Il banco di prova carica tutti i moduli PE di una cartella e avvia la loro inizializzazione:

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Banco di prova sulle DLL di un pacchetto Scarlett](../images/banc-dll.svg)

Risultati dettagliati: [docs/avancee.md](../avancee.md) (in francese). Gioco di test libero confrontato con la sua esecuzione nativa: [docs/jeu-de-test.md](../jeu-de-test.md) (in francese). Una cartella di DLL aggiuntiva (per esempio le DLL di Visual C++) può seguire il bersaglio: `--rapport <cible> <dossier>`.

Il rapporto elenca le funzioni importate, la percentuale già emulata e le funzioni mancanti. Nell'interfaccia, il pulsante **Ouvrir un dossier Xbox…** (Apri una cartella Xbox) legge `MicrosoftGame.Config`, mostra questo rapporto e poi avvia il programma; ogni chiamata non emulata compare nel registro.

## Architettura

![Schema dei moduli di AnyXboxX](../images/architecture.svg)

| Modulo | Ruolo |
|---|---|
| `emu/config.py` | legge il manifesto del pacchetto GDK |
| `emu/loader.py` | carica l'immagine PE e prepara importazioni, esportazioni e TLS |
| `emu/machine.py` | processore Unicorn, stack, heap, TEB/PEB, smistamento delle chiamate |
| `emu/hle/` | funzioni emulate: `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | rapporto di compatibilità |
| `emu/modules.py` | carica le DLL del pacchetto, collega le importazioni, ordina le inizializzazioni |
| `emu/bench.py` | banco di prova su una cartella di moduli |
| `emu/native/` | esecuzione nativa in stile Wine: caricatore, importazioni reali, runtime GDK di AnyXboxX |
| `scarlett.py` | interfaccia Tkinter e riga di comando |

Per aggiungere una funzione, decora un gestore in `emu/hle/`:

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## Ricerca

- [Architettura hardware della Xbox Series X](../recherche/architecture-xbox-series-x.md) (in francese): CPU Zen 2, GPU RDNA 2, memoria, Velocity Architecture, sicurezza.
- [Emulatori e livelli di compatibilità esistenti](../recherche/etat-de-l-art.md) (in francese): WinDurango, XWine1, Xenia, strumenti XVD.

## Test

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Contribuire

Il ramo `main` è protetto: ogni contributo passa da una pull request revisionata e i test devono passare. I bug e le funzioni da emulare si segnalano nelle issue. Le regole complete sono in [CONTRIBUTING.md](../../CONTRIBUTING.md) (in francese).

## Limiti

AnyXboxX è un prototipo. Non esegue giochi commerciali: richiedono la GPU della console (D3D12.X) e numerosi servizi di sistema, e sono distribuiti in contenitori cifrati le cui chiavi restano nella console. Il progetto non contiene e non accetta alcun contenuto protetto.
