# AnyXboxX — emulador de Xbox Series X (protótipo)

[Français](../../README.md) · [English](README.en.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Português** · [日本語](README.ja.md) · [中文](README.zh-CN.md)

O AnyXboxX carrega executáveis Xbox GDK (formato PE32+ x86-64) e executa o código deles com o Unicorn. As funções de sistema do console são substituídas por código Python (emulação de alto nível, como o WinDurango ou o Wine). O programa se apresenta como um Xbox Series X: `XSystemGetDeviceType` retorna `XboxScarlettAnaconda`.

![Demo de direção executada no AnyXboxX](../images/demo-conduite.png)

## Andamento do projeto

| Etapa | Estado |
|---|---|
| Leitura de `MicrosoftGame.Config` (TitleId, identidade, executável Scarlett) | ✅ feito |
| Carregamento PE32+: seções e proteções, realocações, importações, exportações | ✅ feito |
| TLS: cópia do modelo, índice, callbacks | ✅ feito |
| TEB e PEB acessíveis pelo registrador GS | ✅ feito |
| Página HLE: 135 nomes de funções GDK, kernel, CRT e matemáticas emulados | ✅ feito |
| Funções desconhecidas: `E_NOTIMPL` e registro no log em vez de uma recusa | ✅ feito |
| Construtores globais de C++ (`_initterm`) executados como código convidado | ✅ feito |
| Relatório de compatibilidade (`--rapport`) e bancada de testes (`--banc`) | ✅ feito |
| 16/16 DLLs de um pacote Scarlett comercial inicializadas (`DllMain` → `TRUE`) | ✅ feito |
| 49 testes automatizados, 82 % de cobertura | ✅ feito |
| Carregamento de vários módulos vinculados em uma mesma máquina | ⏳ a fazer |
| Amostra livre `Xbox-GDK-Samples` compilada e adicionada à bancada | ⏳ a fazer |
| Exceções SEH x64 (`.pdata`), múltiplas threads | ⏳ a fazer |
| Carregamento das DLLs auxiliares do pacote | ⏳ a fazer |
| Gráficos D3D12.X para Direct3D 12 / Vulkan | ⏳ a fazer |
| Áudio, controle, saves `XGameSave` | ⏳ a fazer |

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

O programa de demonstração compilado é `PrototypeScarlett/demo.pe`; o código-fonte dele é `PrototypeScarlett/demo.c`.

## Analisar um programa

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

A bancada de testes carrega todos os módulos PE de uma pasta e executa a inicialização deles:

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Bancada de testes nas DLLs de um pacote Scarlett](../images/banc-dll.svg)

Resultados detalhados e escolha de um jogo livre para os testes: [docs/avancee.md](../avancee.md) (em francês).

O relatório lista as funções importadas, a porcentagem já emulada e as funções que faltam. Na interface, o botão **Ouvrir un dossier Xbox…** (Abrir uma pasta Xbox) lê `MicrosoftGame.Config`, exibe esse relatório e depois inicia o programa; cada chamada não emulada aparece no log.

## Arquitetura

![Esquema dos módulos do AnyXboxX](../images/architecture.svg)

| Módulo | Função |
|---|---|
| `emu/config.py` | lê o manifesto do pacote GDK |
| `emu/loader.py` | carrega a imagem PE e prepara importações, exportações e TLS |
| `emu/machine.py` | processador Unicorn, pilha, heap, TEB/PEB, despacho das chamadas |
| `emu/hle/` | funções emuladas: `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | relatório de compatibilidade |
| `emu/bench.py` | bancada de testes sobre uma pasta de módulos |
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

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Contribuir

A branch `main` é protegida: toda contribuição passa por uma pull request revisada, e os testes precisam passar. Bugs e funções a emular são reportados nas issues. As regras completas estão em [CONTRIBUTING.md](../../CONTRIBUTING.md) (em francês).

## Limites

O AnyXboxX é um protótipo. Ele não executa jogos comerciais: eles exigem a GPU do console (D3D12.X) e muitos serviços de sistema, e são distribuídos em contêineres criptografados cujas chaves permanecem dentro do console. O projeto não contém nem aceita nenhum conteúdo protegido.
