# AnyXboxX — emulador de Xbox Series X (protótipo)

[English](../../README.md) · [Français](README.fr.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Português** · [日本語](README.ja.md) · [中文](README.zh-CN.md)

O AnyXboxX carrega executáveis Xbox GDK (formato PE32+ x86-64) e executa o código deles com o Unicorn. As funções de sistema do console são substituídas por um runtime C++ em modo nativo e por código Python na máquina isolada (emulação de alto nível, como o WinDurango ou o Wine). O programa se apresenta como um Xbox Series X: `XSystemGetDeviceType` retorna `XboxScarlettAnaconda`.

## Andamento da tradução

![Mapa do andamento: uma célula por função, verde se traduzida](../images/carte-avancee.svg)

Regenerar: `scarlett.py --carte <pasta do pacote> docs/images/carte-avancee.svg`.

![Andamento da tradução do Xbox Series X](../images/traduction.svg)

- **Instruções do processador: 100%.** O Series X usa um AMD Zen 2 em x86-64, o mesmo conjunto de instruções de um PC: no modo nativo, o código do jogo é executado como está, sem tradução.
- **Instruções da GPU: 0%.** Os shaders de um jogo de console são compilados para a GPU RDNA 2 do Series X. É preciso um recompilador RDNA 2 → DXIL, ainda não iniciado.
- **Funções de sistema: 66%** das 1 337 funções importadas pelas DLLs do pacote de teste são resolvidas no modo isolado.
- **DLLs próprias do console**: `xmem.dll` (3/4) e `d3d12_xs.dll` (2/2) estão traduzidas para as funções que o pacote usa. A criação do dispositivo D3D12.X ainda precisa ser escrita.
- **Runtime GDK: 152 das 396 funções** estão escritas no AnyXboxX, em C++: a fila de tarefas (`XTaskQueue`, `XAsync`, `XThread`), o usuário (`XUser`, um perfil local offline), a identidade do Xbox Series X (`XSystem`, Title ID, análise de uso, recursos do runtime), os saves (`XGameSave`, `XGameSaveFiles`, `XPersistentLocalStorage`) e o pacote do jogo (`XPackage`). Elas são usadas quando o AnyXboxX gerencia o runtime sozinho: sem o Gaming Services, ou com `ANYXBOXX_SYSTEM_RUNTIME=0`. Se o runtime GDK do Windows estiver presente, ele fornece todas as interfaces, inclusive a fila de tarefas, pois suas APIs só aceitam as próprias filas. O rastreamento (`ANYXBOXX_TRACE=1`) nomeia cada interface solicitada.

O gráfico é regenerado por `scarlett.py --traduction <pasta do pacote> docs/images/traduction.svg`.

## Desempenho (meta: 60 quadros por segundo constantes)

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc-perf <jeu.exe> [secondes] [courbe.svg]
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --natif <jeu.exe> --fps
```

O runtime C++ cronometra cada `Present` da swap chain DXGI do jogo, inclusive quando o DXGI é carregado dinamicamente por uma DLL do jogo (SDL3). Dele saem os quadros por segundo, o tempo médio de um quadro e o «1% baixo» (a cadência dos 1% de quadros mais lentos, que revela as travadas). `--fps` mostra esses valores no título da janela. `--banc-perf` mede durante N segundos, sem contar o primeiro (carregamento), e dá um veredito «60 q/s constantes» (código de saída 2 se a meta não for atingida). Sem essas opções, nada é interceptado.

![SimpleTriangle: quadros por segundo](../images/fps-simpletriangle.svg)

![testgdk: quadros por segundo](../images/fps-testgdk.svg)

Os dois jogos de teste rodam sem sincronização vertical: cerca de 11 700 q/s no SimpleTriangle e 12 600 q/s no testgdk, em modo nativo.

## Andamento do projeto

| Etapa | Estado |
|---|---|
| Leitura de `MicrosoftGame.Config` (TitleId, identidade, executável Scarlett) | ✅ feito |
| Carregamento PE32+: seções e proteções, realocações, importações, exportações | ✅ feito |
| TLS: cópia do modelo, índice, callbacks | ✅ feito |
| TEB e PEB acessíveis pelo registrador GS | ✅ feito |
| Página HLE: 158 nomes de funções GDK, kernel, CRT e matemáticas emulados | ✅ feito |
| Funções desconhecidas: `E_NOTIMPL` e registro no log em vez de uma recusa | ✅ feito |
| Construtores globais de C++ (`_initterm`) executados como código convidado | ✅ feito |
| Relatório de compatibilidade (`--rapport`) e bancada de testes (`--banc`) | ✅ feito |
| Vários módulos vinculados em uma mesma máquina: DLLs do pacote, ordinais, redirecionamentos, realocação em caso de conflito | ✅ feito |
| `GetModuleHandle`, `GetProcAddress`, `LoadLibrary`, `RtlPcToFileHeader` | ✅ feito |
| 16/16 DLLs de um pacote Scarlett inicializadas com suas dependências, 0 chamadas não emuladas | ✅ feito |
| Jogo de teste livre `SimpleTriangle` compilado: a inicialização em C e a inicialização do GDK funcionam no AnyXboxX | ✅ feito |
| Execução nativa no estilo Wine (`--natif`): **o SimpleTriangle é exibido**, runtime GDK fornecido pelo AnyXboxX | ✅ feito |
| Segundo jogo de teste livre, `testgdk` do SDL3: **roda em modo nativo** (janela, sprites, som) | ✅ feito |
| Execução isolada de um pacote ou de um exe (`--lancer`) com a lista das chamadas a emular | ✅ feito |
| Runtime C++ (`runtime/`): `xgameruntime.dll`, `xmem.dll`, `d3d12_xs.dll` pré-carregadas em modo nativo e fornecidas a todas as DLLs do jogo | ✅ feito |
| `xmem.dll`: `XMemAlloc`, `XMemFree`, ganchos, `XMemVirtualQuery` | ✅ feito |
| `d3d12_xs.dll`: serialização das assinaturas raiz, redirecionada para o D3D12 do PC | ✅ feito |
| Tabela das 396 funções do GDK: interface e número do método, extraídos de `xgameruntime.lib` (`tools/gdk_interfaces.py`) | ✅ feito |
| `XTaskQueue`, `XAsync`, `XThread` fornecidas pelo AnyXboxX: o testgdk roda sem o runtime do Windows | ✅ feito |
| Outras interfaces do GDK: delegadas ao runtime GDK do Windows, nomeadas pelo rastreamento | 🟡 em andamento |
| 214 testes automatizados | ✅ feito |
| D3D12.X: `D3D12XboxCreateDevice` e interfaces `ID3D12*` do console | ⏳ a fazer |
| `XUser` offline: perfil local sempre conectado, gamertag configurável (`ANYXBOXX_GAMERTAG`), login do testgdk bem-sucedido | ✅ feito |
| Identidade do Xbox Series X: tipo de console (valor de registro `ConsoleMode` simulado, inclusive nas DLLs do jogo), `XSystem`, Title ID lido de `MicrosoftGame.config`, análise de uso «Xbox Series X» | ✅ feito |
| Mapa do andamento: uma célula por função (`--carte`) | ✅ feito |
| Controle (`GameInput`) e áudio (`XAudio2`): a mesma API no console e no PC, ligados às DLLs do Windows em modo nativo | ✅ feito |
| Relatório Markdown das importações ausentes por DLL e das chamadas não emuladas (`--lancer … --md rapport.md`) | ✅ feito |
| Contador de quadros (`--fps`) e bancada de desempenho com veredito «60 q/s constantes» e curva (`--banc-perf`) | ✅ feito |
| Saves `XGameSave` (contêineres, blobs, cota, leitura assíncrona) e armazenamento local persistente, no disco do PC (`%LOCALAPPDATA%\AnyXboxX\<TitleId>`, ou `ANYXBOXX_SAVE_DIR`) | ✅ feito |
| `XPackage`: pacote instalado localmente (identificador, idioma, blocos prontos, montagem na pasta do jogo) | ✅ feito |
| `kernelx.dll` (kernel do console): 2 661 funções redirecionadas para `kernel32`/`kernelbase` do Windows | ✅ feito |
| TLS implícito (`thread_local`) dos jogos no modo nativo: DLL portadora `anyxboxx_tls.dll`, cada thread recebe sua cópia (até 256 KiB) | ✅ feito |
| Inicializador nativo em C++ sem Python (`runtime/build/bin/anyxboxx.exe <jogo.exe \| pasta> [--fps]`): SimpleTriangle e testgdk a ~12 000 qps | ✅ feito |
| Desmontador de GPU RDNA 2: 1.444 mnemônicos e operandos na sintaxe do LLVM (escalares, VOP1/VOP2/VOPC/VOP3 com modificadores), verificado em 34.948 codificações públicas do LLVM: `scarlett.py --rdna2 <shader.bin> [--liste]` | 🟡 em andamento |
| Outras interfaces do GDK escritas pelo AnyXboxX (`XStore`, `XGameUi`, `XNetworking`…) | ⏳ a fazer |
| Recompilador de shaders RDNA 2 → DXIL: primeiros programas traduzidos para HLSL, compilados para DXIL e executados na GPU do PC com D3D12 (`--hlsl`, `anyxboxx_gpu_run.exe`, WARP sem GPU), memória idêntica a um interpretador de referência wave32 que executa 519 de 1.444 codificações (escalares, VOP1/VOP2/VOPC/VOP3, memória: SMEM, LDS, GLOBAL, MUBUF com limites V#, atômicas, desvios, divergência por `exec`): `scarlett.py --rdna2 <shader.bin> --executer` | 🟡 em andamento |
| Exceções SEH x64 (`.pdata`), múltiplas threads | ⏳ a fazer |
| Carregamento dinâmico de uma DLL durante a execução (`LoadLibrary` + `DllMain`) | ⏳ a fazer |
| Gráficos D3D12.X para Direct3D 12 / Vulkan | ⏳ a fazer |
| Decodificação de áudio XMA do console (o restante do áudio passa pelo XAudio2) | ⏳ a fazer |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="O carro vira para a direita" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="Relatório de compatibilidade da demo" width="380"></td>
</tr>
<tr>
<td align="center">A demo responde às setas do teclado.</td>
<td align="center">O log exibe o relatório de compatibilidade.</td>
</tr>
</table>

## Experimentar a demo

No Windows, instale o Python 3.12 de 64 bits com Tcl/Tk e abra o PowerShell na raiz do repositório.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

O modo nativo precisa do runtime C++. Ele é compilado com o Visual Studio 2022 ou 2026 (carga de trabalho C++) e o CMake:

```powershell
cmake -S runtime -B runtime/build -A x64
cmake --build runtime/build --config Release
```

A fila de tarefas reaproveita o módulo `Task` da [libHttpClient](https://github.com/microsoft/libHttpClient) (licença MIT, `runtime/third_party/libhttpclient-task`). As DLLs vão para `runtime/build/bin`, ou para a pasta indicada por `ANYXBOXX_RUNTIME`. `ANYXBOXX_SYSTEM_RUNTIME=0` desativa a delegação ao runtime GDK do Windows.

O programa de demonstração compilado é `PrototypeScarlett/demo.pe`; o código-fonte dele é `PrototypeScarlett/demo.c`.

## Executar um jogo em modo nativo

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --natif <dossier ou fichier .exe> [dossiers de DLL…]
```

![SimpleTriangle iniciado pelo AnyXboxX em modo nativo](../images/simpletriangle-anyxboxx.png)

O AnyXboxX carrega o próprio executável e o executa diretamente no processador, como o Wine. O runtime do Xbox (`xgameruntime.dll`) é fornecido pelo AnyXboxX; a janela e o DirectX 12 são os do PC. **Atenção: no modo nativo, o programa não é isolado.** Reserve esse modo para programas de confiança; `--rapport` e `--banc` continuam isolados dentro do Unicorn. `ANYXBOXX_TRACE=1` exibe as chamadas interceptadas. Detalhes: [docs/jeu-de-test.md](../jeu-de-test.md) (em francês).

## Executar um pacote em modo isolado

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --lancer <dossier du paquet ou fichier .exe> [dossiers de DLL…]
```

Com uma pasta, o AnyXboxX lê o `MicrosoftGame.Config`, pega o executável declarado para `Scarlett` e o executa na máquina isolada (Unicorn): o programa não toca no PC. O relatório indica as importações não resolvidas e depois as chamadas não emuladas, da mais frequente à mais rara: é a lista de trabalho para completar o emulador. Se o executável estiver ausente, a mensagem o nomeia. Com `--md rapport.md`, o mesmo relatório é escrito em Markdown, com as importações ausentes agrupadas por DLL.

## Analisar um programa

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

A bancada de testes carrega todos os módulos PE de uma pasta e executa a inicialização deles:

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Bancada de testes nas DLLs de um pacote Scarlett](../images/banc-dll.svg)

Resultados detalhados: [docs/avancee.md](../avancee.md) (em francês). Jogo de teste livre comparado com a execução nativa dele: [docs/jeu-de-test.md](../jeu-de-test.md) (em francês). Uma pasta de DLLs adicional (por exemplo, as DLLs do Visual C++) pode acompanhar o alvo: `--rapport <cible> <dossier>`.

O relatório lista as funções importadas, a porcentagem já emulada e as funções que faltam. Na interface, o botão **Open an Xbox folder…** (Abrir uma pasta Xbox) lê `MicrosoftGame.Config`, exibe esse relatório e depois inicia o programa; cada chamada não emulada aparece no log.

## Arquitetura

![Esquema dos módulos do AnyXboxX](../images/architecture.svg)

| Módulo | Função |
|---|---|
| `emu/config.py` | lê o manifesto do pacote GDK |
| `emu/loader.py` | carrega a imagem PE e prepara importações, exportações e TLS |
| `emu/machine.py` | processador Unicorn, pilha, heap, TEB/PEB, despacho das chamadas |
| `emu/hle/` | funções emuladas: `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | relatório de compatibilidade |
| `emu/modules.py` | carrega as DLLs do pacote, vincula as importações, ordena as inicializações |
| `emu/bench.py` | bancada de testes sobre uma pasta de módulos |
| `emu/native/` | execução nativa no estilo Wine: carregador, importações reais, runtime GDK do AnyXboxX |
| `scarlett.py` | interface Tkinter e linha de comando |

Para adicionar uma função, decore um manipulador em `emu/hle/`:

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## Pesquisa

- [Arquitetura de hardware do Xbox Series X](../recherche/architecture-xbox-series-x.md) (em francês): CPU Zen 2, GPU RDNA 2, memória, Velocity Architecture, segurança.
- [Emuladores e camadas de compatibilidade existentes](../recherche/etat-de-l-art.md) (em francês): WinDurango, XWine1, Xenia, ferramentas XVD.
- [Notas de engenharia reversa do pacote Scarlett estudado](../recherche/paquet/README.md) (em francês, escritas pelo Codex): tabelas RDS5/ETPF, cabeçalhos RPF, organização do pacote.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Contribuir

A branch `main` é protegida: toda contribuição passa por uma pull request revisada, e os testes precisam passar. Bugs e funções a emular são reportados nas issues. As regras completas estão em [CONTRIBUTING.md](../../CONTRIBUTING.md) (em francês).
