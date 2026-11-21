"""Mesure de l'avancée de la traduction des DLL console Xbox."""
import xml.etree.ElementTree as ET

import pytest

from emu import translation
from emu.translation import Area
from pe_builder import Asm, build_pe

CODE = Asm().mov_eax(1).ret().build()


@pytest.fixture
def folders(tmp_path):
    package = tmp_path / "package"
    runtime = tmp_path / "runtime"
    package.mkdir()
    runtime.mkdir()
    build_pe(package / "game.exe", lambda iat: CODE, dll=False, imports=[
        ("xmem.dll", "XMemAlloc"), ("xmem.dll", "XMemFree"),
        ("d3d12_xs.dll", "D3D12SerializeVersionedRootSignature"),
        ("kernel32.dll", "GetTickCount")])
    (package / "notes.dll").write_bytes(b"pas un PE")
    build_pe(runtime / "xmem.dll", lambda iat: CODE, exports=[("XMemAlloc", 0)])
    return package, runtime


def test_package_imports_keeps_console_dlls_only(folders):
    imports = translation.package_imports(folders[0])
    assert imports == {
        "xmem.dll": frozenset({"XMemAlloc", "XMemFree"}),
        "d3d12_xs.dll": frozenset({"D3D12SerializeVersionedRootSignature"})}


def test_ordinal_imports_are_prefixed(tmp_path):
    build_pe(tmp_path / "a.exe", lambda iat: CODE, dll=False, imports=[("xmem.dll", 7)])
    assert translation.package_imports(tmp_path) == {"xmem.dll": frozenset({"#7"})}


def test_runtime_exports(folders):
    assert translation.runtime_exports(folders[1]) == {"xmem.dll": frozenset({"XMemAlloc"})}


def test_runtime_exports_includes_forwarders(tmp_path):
    build_pe(tmp_path / "kernelx.dll", lambda iat: CODE,
             exports=[("A", 0), ("B", "KERNEL32.Sleep")])
    assert translation.runtime_exports(tmp_path)["kernelx.dll"] == frozenset({"A", "B"})


def test_runtime_exports_missing_folder(tmp_path):
    assert translation.runtime_exports(None) == {}
    assert translation.runtime_exports(tmp_path / "absent") == {}


def test_measure(folders):
    areas = translation.measure(*folders)
    by_name = {a.name: a for a in areas}
    assert (by_name["xmem.dll"].done, by_name["xmem.dll"].total) == (1, 2)
    assert "XMemFree" in by_name["xmem.dll"].note
    assert (by_name["d3d12_xs.dll"].done, by_name["d3d12_xs.dll"].total) == (0, 1)


def test_measure_appends_extra(folders):
    areas = translation.measure(*folders, extra=translation.STATIC_AREAS)
    assert areas[-len(translation.STATIC_AREAS):] == translation.STATIC_AREAS


def test_complete_note():
    assert Area("x", 0, 0, "").share == 0
    assert Area("x", 1, 2, "").share == 0.5


def test_table(folders):
    text = translation.table(translation.measure(*folders))
    assert text.startswith("| Domaine | Traduit | Total | Part | Reste |")
    assert "| xmem.dll | 1 | 2 | 50 % |" in text


def test_svg_is_valid_xml(folders):
    areas = translation.measure(*folders, extra=translation.STATIC_AREAS)
    root = ET.fromstring(translation.svg(areas, "Titre <test>"))
    content = "".join(root.itertext())
    assert "xmem.dll" in content and "Titre <test>" in content
    assert "D3D12.X" in content
    assert "<script" not in translation.svg(areas, "t")


def test_non_pe_ignored(folders):
    assert "notes.dll" not in translation.package_imports(folders[0])


def test_partial_functions_are_not_counted_as_translated(tmp_path):
    """Une fonction exportée mais seulement amorcée (échec signalé) reste à traduire."""
    package, runtime = tmp_path / "p", tmp_path / "r"
    package.mkdir()
    runtime.mkdir()
    build_pe(package / "game.exe", lambda iat: CODE, dll=False,
             imports=[("xmem.dll", "XMemAlloc"), ("xmem.dll", "XMemGetWorkingSetStatistics")])
    build_pe(runtime / "xmem.dll", lambda iat: CODE,
             exports=[("XMemAlloc", 0), ("XMemGetWorkingSetStatistics", 0)])
    (area,) = translation.measure(package, runtime)
    assert (area.done, area.total) == (1, 2)
    assert "XMemGetWorkingSetStatistics (partial" in area.note


def test_functions_area_sums_bench_rows():
    from emu.bench import BenchRow

    rows = (BenchRow("a.dll", 100, 50.0, True, True, ""), BenchRow("b.dll", 20, 100.0, True, True, ""))
    area = translation.functions_area(rows)
    assert (area.done, area.total) == (70, 120)


def test_instruction_areas_show_a_share_only():
    image = translation.svg((translation.CPU_AREA, translation.GPU_AREA), "Avancée")
    assert "100%" in image and "0%" in image
    assert "1/1" not in image and "0/1" not in image
    assert translation.CPU_AREA.share == 1.0 and translation.GPU_AREA.share == 0.0


def test_gdk_runtime_area_counts_functions_of_served_interfaces(tmp_path):
    table = tmp_path / "table.inc"
    table.write_text('// commentaire\n'
                     'ANYXBOXX_GDK_API(XTaskQueueCreate, "AAAA", "AAAA", 12)\n'
                     'ANYXBOXX_GDK_API(XTaskQueueDispatch, "AAAA", "AAAA", 16)\n'
                     'ANYXBOXX_GDK_API(XUserAddAsync, "BBBB", "BBBB", 7)\n', encoding="utf-8")
    served = tmp_path / "served.inc"
    served.write_text('ANYXBOXX_SERVED_INTERFACE(TaskQueueInterface, "AAAA", "AAAA")\n', encoding="utf-8")
    area = translation.gdk_runtime_area(table, served)
    assert (area.done, area.total) == (2, 3)
    assert "1/2 interfaces" in area.note


def test_repository_tables_are_consistent():
    """La table générée couvre les 396 API du GDK 2610 et XTaskQueue y est servie."""
    area = translation.gdk_runtime_area()
    assert area.total >= 396 and area.done >= 27
