# AnyXboxX — emulador de Xbox Series X (prototipo)

[Français](../../README.md) · [English](README.en.md) · **Español** · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [中文](README.zh-CN.md)

AnyXboxX carga ejecutables de Xbox GDK (formato PE32+ x86-64) y ejecuta su código con Unicorn. Las funciones de sistema de la consola se sustituyen por código Python (emulación de alto nivel, como WinDurango o Wine). El programa se presenta como una Xbox Series X: `XSystemGetDeviceType` devuelve `XboxScarlettAnaconda`.

![Demo de conducción ejecutándose en AnyXboxX](../images/demo-conduite.png)

## Avance del proyecto

| Etapa | Estado |
|---|---|
| Lectura de `MicrosoftGame.Config` (TitleId, identidad, ejecutable Scarlett) | ✅ hecho |
| Carga PE32+: secciones y protecciones, reubicaciones, importaciones, exportaciones | ✅ hecho |
| TLS: copia de la plantilla, índice, callbacks | ✅ hecho |
| TEB y PEB accesibles mediante el registro GS | ✅ hecho |
| Página HLE: 158 nombres de funciones GDK, kernel, CRT y matemáticas emulados | ✅ hecho |
| Funciones desconocidas: `E_NOTIMPL` y registro en el diario en lugar de un rechazo | ✅ hecho |
| Constructores globales de C++ (`_initterm`) ejecutados como código invitado | ✅ hecho |
| Informe de compatibilidad (`--rapport`) y banco de pruebas (`--banc`) | ✅ hecho |
| Varios módulos enlazados en una misma máquina: DLL del paquete, ordinales, redirecciones, reubicación en caso de conflicto | ✅ hecho |
| `GetModuleHandle`, `GetProcAddress`, `LoadLibrary`, `RtlPcToFileHeader` | ✅ hecho |
| 16/16 DLL de un paquete Scarlett inicializadas con sus dependencias, 0 llamadas no emuladas | ✅ hecho |
| Juego de prueba libre `SimpleTriangle` compilado: el arranque en C y la inicialización de GDK funcionan en AnyXboxX | ✅ hecho |
| 74 pruebas automatizadas, 83 % de cobertura | ✅ hecho |
| Ventana Win32 (`USER32`) y DirectX 12 (`d3d12`, `dxgi`) para mostrar el triángulo | ⏳ pendiente |
| Ejecución nativa del código (enfoque Wine) en lugar de Unicorn | ⏳ pendiente |
| Excepciones SEH x64 (`.pdata`), múltiples hilos | ⏳ pendiente |
| Carga dinámica de una DLL durante la ejecución (`LoadLibrary` + `DllMain`) | ⏳ pendiente |
| Gráficos D3D12.X hacia Direct3D 12 / Vulkan | ⏳ pendiente |
| Audio, mando, partidas guardadas `XGameSave` | ⏳ pendiente |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="El coche gira hacia la derecha" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="Informe de compatibilidad de la demo" width="380"></td>
</tr>
<tr>
<td align="center">La demo responde a las flechas del teclado.</td>
<td align="center">El diario muestra el informe de compatibilidad.</td>
</tr>
</table>

## Probar la demo

En Windows, instala Python 3.12 de 64 bits con Tcl/Tk y abre PowerShell en la raíz del repositorio.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

El programa de demostración compilado es `PrototypeScarlett/demo.pe`; su código fuente es `PrototypeScarlett/demo.c`.

## Analizar un programa

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

El banco de pruebas carga todos los módulos PE de una carpeta y ejecuta su inicialización:

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Banco de pruebas sobre las DLL de un paquete Scarlett](../images/banc-dll.svg)

Resultados detallados: [docs/avancee.md](../avancee.md) (en francés). Juego de prueba libre comparado con su ejecución nativa: [docs/jeu-de-test.md](../jeu-de-test.md) (en francés). Una carpeta de DLL adicional (por ejemplo, las DLL de Visual C++) puede seguir al objetivo: `--rapport <cible> <dossier>`.

El informe enumera las funciones importadas, el porcentaje ya emulado y las funciones que faltan. En la interfaz, el botón **Ouvrir un dossier Xbox…** (Abrir una carpeta Xbox) lee `MicrosoftGame.Config`, muestra este informe y luego lanza el programa; cada llamada no emulada aparece en el diario.

## Arquitectura

![Esquema de los módulos de AnyXboxX](../images/architecture.svg)

| Módulo | Función |
|---|---|
| `emu/config.py` | lee el manifiesto del paquete GDK |
| `emu/loader.py` | carga la imagen PE y prepara importaciones, exportaciones y TLS |
| `emu/machine.py` | procesador Unicorn, pila, heap, TEB/PEB, despacho de llamadas |
| `emu/hle/` | funciones emuladas: `gdk.py`, `kernel.py`, `crt.py`, `libm.py`, `guest.py` |
| `emu/report.py` | informe de compatibilidad |
| `emu/modules.py` | carga las DLL del paquete, enlaza las importaciones, ordena las inicializaciones |
| `emu/bench.py` | banco de pruebas sobre una carpeta de módulos |
| `scarlett.py` | interfaz Tkinter y línea de comandos |

Para añadir una función, decora un manejador en `emu/hle/`:

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## Investigación

- [Arquitectura de hardware de la Xbox Series X](../recherche/architecture-xbox-series-x.md) (en francés): CPU Zen 2, GPU RDNA 2, memoria, Velocity Architecture, seguridad.
- [Emuladores y capas de compatibilidad existentes](../recherche/etat-de-l-art.md) (en francés): WinDurango, XWine1, Xenia, herramientas XVD.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## Contribuir

La rama `main` está protegida: toda contribución pasa por una pull request revisada, y las pruebas deben pasar. Los errores y las funciones por emular se notifican en las issues. Las reglas completas están en [CONTRIBUTING.md](../../CONTRIBUTING.md) (en francés).

## Límites

AnyXboxX es un prototipo. No ejecuta juegos comerciales: exigen la GPU de la consola (D3D12.X) y numerosos servicios del sistema, y se distribuyen en contenedores cifrados cuyas claves permanecen dentro de la consola. El proyecto no contiene ni acepta ningún contenido protegido.
