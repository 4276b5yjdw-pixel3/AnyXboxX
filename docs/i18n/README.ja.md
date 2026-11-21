# AnyXboxX — Xbox Series X エミュレーター（プロトタイプ）

[Français](../../README.md) · [English](README.en.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt-BR.md) · **日本語** · [中文](README.zh-CN.md)

AnyXboxX は Xbox GDK の実行ファイル（PE32+ x86-64 形式）を読み込み、そのコードを Unicorn で実行します。コンソールのシステム関数は Python のコードに置き換えられます（WinDurango や Wine と同じ高レベルエミュレーション）。このプログラムは Xbox Series X として振る舞い、`XSystemGetDeviceType` は `XboxScarlettAnaconda` を返します。

![AnyXboxX で実行された運転デモ](../images/demo-conduite.png)

## プロジェクトの進捗

| ステップ | 状態 |
|---|---|
| `MicrosoftGame.Config` の読み取り（TitleId、ID、Scarlett 実行ファイル） | ✅ 完了 |
| PE32+ の読み込み：セクションと保護属性、リロケーション、インポート、エクスポート | ✅ 完了 |
| TLS：テンプレートのコピー、インデックス、コールバック | ✅ 完了 |
| GS レジスタ経由で TEB と PEB にアクセス可能 | ✅ 完了 |
| HLE ページ：GDK、カーネル、CRT、数学関数の 135 個の関数名をエミュレート | ✅ 完了 |
| 未知の関数：拒否せず `E_NOTIMPL` を返しログに記録 | ✅ 完了 |
| グローバル C++ コンストラクター（`_initterm`）をゲストコードで実行 | ✅ 完了 |
| 互換性レポート（`--rapport`）とテストベンチ（`--banc`） | ✅ 完了 |
| 市販の Scarlett パッケージの 16/16 個の DLL を初期化（`DllMain` → `TRUE`） | ✅ 完了 |
| 49 件の自動テスト、カバレッジ 82 % | ✅ 完了 |
| リンクされた複数のモジュールを同一のマシンに読み込む | ⏳ 未着手 |
| フリーのサンプル `Xbox-GDK-Samples` をコンパイルしてベンチに追加 | ⏳ 未着手 |
| x64 SEH 例外（`.pdata`）、マルチスレッド | ⏳ 未着手 |
| パッケージ付属 DLL の読み込み | ⏳ 未着手 |
| D3D12.X から Direct3D 12 / Vulkan へのグラフィックス変換 | ⏳ 未着手 |
| オーディオ、コントローラー、`XGameSave` セーブデータ | ⏳ 未着手 |

<table>
<tr>
<td><img src="../images/demo-virage.png" alt="車が右に曲がる" width="380"></td>
<td><img src="../images/rapport-compatibilite.png" alt="デモの互換性レポート" width="380"></td>
</tr>
<tr>
<td align="center">デモはキーボードの矢印キーに反応します。</td>
<td align="center">ログに互換性レポートが表示されます。</td>
</tr>
</table>

## デモを試す

Windows で、Tcl/Tk 付きの 64 ビット版 Python 3.12 をインストールし、リポジトリのルートで PowerShell を開きます。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --demo
```

コンパイル済みのデモプログラムは `PrototypeScarlett/demo.pe` で、ソースコードは `PrototypeScarlett/demo.c` です。

## プログラムを解析する

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --rapport <dossier ou fichier .exe>
```

テストベンチは、フォルダー内のすべての PE モジュールを読み込み、その初期化を実行します。

```powershell
.\.venv\Scripts\python.exe .\PrototypeScarlett\scarlett.py --banc <dossier>
```

![Scarlett パッケージの DLL に対するテストベンチ](../images/banc-dll.svg)

詳細な結果とテスト用のフリーゲームの選定：[docs/avancee.md](../avancee.md)（フランス語）。

レポートには、インポートされた関数、すでにエミュレートされている割合、不足している関数が一覧表示されます。インターフェースでは、**Ouvrir un dossier Xbox…**（Xbox フォルダーを開く）ボタンが `MicrosoftGame.Config` を読み取り、このレポートを表示してからプログラムを起動します。エミュレートされていない呼び出しはすべてログに表示されます。

## アーキテクチャ

![AnyXboxX のモジュール構成図](../images/architecture.svg)

| モジュール | 役割 |
|---|---|
| `emu/config.py` | GDK パッケージのマニフェストを読み取る |
| `emu/loader.py` | PE イメージを読み込み、インポート、エクスポート、TLS を準備する |
| `emu/machine.py` | Unicorn プロセッサ、スタック、ヒープ、TEB/PEB、呼び出しの振り分け |
| `emu/hle/` | エミュレートされた関数：`gdk.py`、`kernel.py`、`crt.py`、`libm.py`、`guest.py` |
| `emu/report.py` | 互換性レポート |
| `emu/bench.py` | モジュールのフォルダーに対するテストベンチ |
| `scarlett.py` | Tkinter インターフェースとコマンドライン |

関数を追加するには、`emu/hle/` のハンドラーにデコレーターを付けます。

```python
@hle("gdk")
def XSystemGetDeviceType(c):
    return XBOX_SERIES_X
```

## 調査

- [Xbox Series X のハードウェアアーキテクチャ](../recherche/architecture-xbox-series-x.md)（フランス語）：Zen 2 CPU、RDNA 2 GPU、メモリ、Velocity Architecture、セキュリティ。
- [既存のエミュレーターと互換レイヤー](../recherche/etat-de-l-art.md)（フランス語）：WinDurango、XWine1、Xenia、XVD ツール。

## テスト

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

## コントリビュート

`main` ブランチは保護されています。すべての貢献はレビューされるプルリクエストを経由し、テストに合格する必要があります。バグやエミュレートすべき関数は issue で報告してください。詳しいルールは [CONTRIBUTING.md](../../CONTRIBUTING.md)（フランス語）にあります。

## 制限事項

AnyXboxX はプロトタイプです。市販のゲームは実行できません。市販のゲームにはコンソールの GPU（D3D12.X）と多数のシステムサービスが必要で、鍵がコンソール内に残る暗号化コンテナーで配布されているためです。このプロジェクトは保護されたコンテンツを含まず、受け付けることもありません。
