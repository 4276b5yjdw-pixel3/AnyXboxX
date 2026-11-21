# AnyXboxX — Xbox Series X 模拟器（原型）

[Français](../../README.md) · [English](README.en.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · **中文**

AnyXboxX 加载 Xbox GDK 可执行文件（PE32+ x86-64 格式），并用 Unicorn 执行其代码。主机的系统函数由 Python 代码替代（高级别模拟，与 WinDurango 或 Wine 类似）。该程序会表现为一台 Xbox Series X：`XSystemGetDeviceType` 返回 `XboxScarlettAnaconda`。

![在 AnyXboxX 中运行的驾驶演示](../images/demo-conduite.png)

## 项目进展

| 步骤 | 状态 |
|---|---|
| 读取 `MicrosoftGame.Config`（TitleId、标识、Scarlett 可执行文件） | ✅ 已完成 |
| PE32+ 加载：节与保护属性、重定位、导入、导出 | ✅ 已完成 |
| TLS：模板复制、索引、回调 | ✅ 已完成 |
| 可通过 GS 寄存器访问 TEB 和 PEB | ✅ 已完成 |
| HLE 页：模拟了 158 个 GDK、内核、CRT 和数学函数名 | ✅ 已完成 |
| 未知函数：返回 `E_NOTIMPL` 并写入日志，而不是拒绝 | ✅ 已完成 |
| 全局 C++ 构造函数（`_initterm`）以客体代码方式运行 | ✅ 已完成 |
| 兼容性报告（`--rapport`）和测试台（`--banc`） | ✅ 已完成 |
| 在同一台机器中运行多个相互链接的模块：包中的 DLL、序号、转发、冲突时重定位 | ✅ 已完成 |
| `GetModuleHandle`、`GetProcAddress`、`LoadLibrary`、`RtlPcToFileHeader` | ✅ 已完成 |
| Scarlett 包中的 16/16 个 DLL 连同依赖项完成初始化，0 个未模拟的调用 | ✅ 已完成 |
| 61 个自动化测试，83 % 覆盖率 | ✅ 已完成 |
| 原生执行代码（Wine 方式），取代 Unicorn | ⏳ 待完成 |
| x64 SEH 异常（`.pdata`）、多线程 | ⏳ 待完成 |
| 在运行时动态加载 DLL（`LoadLibrary` + `DllMain`） | ⏳ 待完成 |
| 编译免费示例 `Xbox-GDK-Samples` 并加入测试台 | ⏳ 待完成 |
| 将 D3D12.X 图形转换为 Direct3D 12 / Vulkan | ⏳ 待完成 |
| 音频、手柄、`XGameSave` 存档 | ⏳ 待完成 |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="汽车向右转弯" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="演示的兼容性报告" width="380"></td>
</tr>
<tr>
<td align="center">演示会响应键盘方向键。</td>
<td align="center">日志中显示兼容性报告。</td>
</tr>
</table>

## 试用演示

在 Windows 上，安装带有 Tcl/Tk 的 64 位 Python 3.12，然后在仓库根目录打开 PowerShell。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

编译好的演示程序是 `PrototypeScarlett/demo.pe`，其源代码是 `PrototypeScarlett/demo.c`。

## 分析程序

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

测试台会加载文件夹中的所有 PE 模块并运行它们的初始化：

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![针对 Scarlett 包中 DLL 的测试台](../images/banc-dll.svg)

详细结果以及用于测试的免费游戏的选择：[docs/avancee.md](../avancee.md)（法语）。

报告会列出导入的函数、已模拟的百分比以及缺失的函数。在界面中，**Ouvrir un dossier Xbox…**（打开 Xbox 文件夹）按钮会读取 `MicrosoftGame.Config`，显示该报告，然后启动程序；每个未模拟的调用都会出现在日志中。

## 架构

![AnyXboxX 模块示意图](../images/architecture.svg)

| 模块 | 作用 |
|---|---|
| `emu/config.py` | 读取 GDK 包的清单 |
| `emu/loader.py` | 加载 PE 映像，并准备导入、导出和 TLS |
| `emu/machine.py` | Unicorn 处理器、栈、堆、TEB/PEB、调用分发 |
| `emu/hle/` | 被模拟的函数：`gdk.py`、`kernel.py`、`crt.py`、`libm.py`、`guest.py` |
| `emu/report.py` | 兼容性报告 |
| `emu/modules.py` | 加载包中的 DLL、链接导入、安排初始化顺序 |
| `emu/bench.py` | 针对模块文件夹的测试台 |
| `scarlett.py` | Tkinter 界面和命令行 |

要添加一个函数，请在 `emu/hle/` 中为处理函数加上装饰器：

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## 调研

- [Xbox Series X 的硬件架构](../recherche/architecture-xbox-series-x.md)（法语）：Zen 2 CPU、RDNA 2 GPU、内存、Velocity Architecture、安全性。
- [现有的模拟器和兼容层](../recherche/etat-de-l-art.md)（法语）：WinDurango、XWine1、Xenia、XVD 工具。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## 参与贡献

`main` 分支受到保护：所有贡献都必须经过审阅的 pull request，并且测试必须通过。缺陷和需要模拟的函数请在 issue 中提交。完整规则见 [CONTRIBUTING.md](../../CONTRIBUTING.md)（法语）。

## 局限

AnyXboxX 只是一个原型。它不能运行商业游戏：这些游戏需要主机的 GPU（D3D12.X）和大量系统服务，并且以加密容器的形式发行，密钥保留在主机内部。本项目不包含也不接受任何受保护的内容。
