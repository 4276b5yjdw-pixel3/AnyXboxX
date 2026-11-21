from pathlib import Path
import struct
import sys
import tkinter as tk
from tkinter import filedialog, ttk
import xml.etree.ElementTree as ET

import pefile
from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.x86_const import (
    UC_X86_REG_RAX, UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8,
    UC_X86_REG_RIP, UC_X86_REG_RSP,
)

WIDTH, HEIGHT = 160, 96
PAGE = 4096
MAX_IMAGE = 256 * 1024 * 1024
RW = UC_PROT_READ | UC_PROT_WRITE
RX = UC_PROT_READ | UC_PROT_EXEC
DEMO = Path(__file__).with_name("demo.pe")
ERRORS = (ValueError, OSError, ET.ParseError, pefile.PEFormatError, UcError)


def align(size):
    return (size + PAGE - 1) // PAGE * PAGE


def package_entry(folder):
    folder = folder.resolve()
    manifest = folder / "MicrosoftGame.Config"
    if not manifest.is_file():
        raise ValueError("Le dossier choisi ne contient pas MicrosoftGame.Config.")
    root = ET.parse(manifest).getroot()
    for entry in root.findall(".//{*}ExecutableList/{*}Executable"):
        if entry.get("TargetDeviceFamily", "").lower() == "scarlett":
            name = entry.get("Name", "")
            path = (folder / name).resolve()
            if not path.is_relative_to(folder):
                raise ValueError("Le manifeste désigne un fichier hors du dossier.")
            if not path.is_file():
                title = entry.get("OverrideDisplayName", "Jeu")
                raise ValueError(f"{title} : le fichier {name} manque dans ce dossier.")
            return path
    raise ValueError("Aucun programme Scarlett déclaré dans le manifeste.")


class Machine:
    def __init__(self, path):
        if path.stat().st_size > MAX_IMAGE:
            raise ValueError("Ce prototype accepte des exécutables de 256 Mio au maximum.")
        with pefile.PE(str(path), fast_load=True) as pe:
            header = pe.OPTIONAL_HEADER
            if pe.FILE_HEADER.Machine != 0x8664 or header.Magic != 0x20B:
                raise ValueError("Le programme doit être un exécutable x86-64 au format PE32+.")
            base, size = header.ImageBase, header.SizeOfImage
            if (base % PAGE or not 0 < header.SizeOfHeaders <= size <= MAX_IMAGE
                    or not 0 < header.AddressOfEntryPoint < size):
                raise ValueError("Image PE incompatible ou point d’entrée absent.")
            for index, feature in ((9, "TLS"), (13, "imports différés"), (14, ".NET")):
                if index < len(header.DATA_DIRECTORY) and header.DATA_DIRECTORY[index].VirtualAddress:
                    raise ValueError(f"Fonctionnalité non émulée : {feature}.")
            pe.parse_data_directories(directories=[0, 1])
            self.cpu = Uc(UC_ARCH_X86, UC_MODE_64)
            self.entry = base + header.AddressOfEntryPoint
            self.cpu.mem_map(base, align(header.SizeOfHeaders), UC_PROT_READ)
            self.cpu.mem_write(base, pe.get_data(0, header.SizeOfHeaders))
            for section in pe.sections:
                rva = section.VirtualAddress
                length = max(section.Misc_VirtualSize, section.SizeOfRawData)
                if not length:
                    continue
                if rva % PAGE or rva + length > size:
                    raise ValueError("Section PE incompatible.")
                flags = section.Characteristics
                prot = ((UC_PROT_READ if flags & 0x40000000 else 0)
                        | (UC_PROT_WRITE if flags & 0x80000000 else 0)
                        | (UC_PROT_EXEC if flags & 0x20000000 else 0))
                self.cpu.mem_map(base + rva, align(length), prot)
                data = section.get_data()
                if data:
                    self.cpu.mem_write(base + rva, data)

            # La page après l’image contient les routines GDK émulées et l’adresse de retour.
            service = base + align(size) + PAGE
            self.cpu.mem_map(service, PAGE, RX)
            # XSystemGetDeviceType renvoie XboxScarlettAnaconda (7) dans EAX.
            self.cpu.mem_write(service, bytes.fromhex("b8 07 00 00 00 c3"))
            self.stop = service + 16
            if len(header.DATA_DIRECTORY) > 1 and header.DATA_DIRECTORY[1].VirtualAddress and not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                raise ValueError("Table des imports PE illisible.")
            for library in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
                for item in library.imports:
                    if (library.dll.lower(), item.name) != (b"xgameruntime.dll", b"XSystemGetDeviceType"):
                        symbol = item.name.decode(errors="replace") if item.name else f"#{item.ordinal}"
                        raise ValueError(f"Import non émulé : {library.dll.decode(errors='replace')} / {symbol}")
                    self.cpu.mem_write(item.address, struct.pack("<Q", service))
            stack = service + 2 * PAGE
            self.cpu.mem_map(stack, 256 * PAGE, RW)
            self.stack_top = stack + 256 * PAGE - 40
            self.pixels = stack + 257 * PAGE
            self.cpu.mem_map(self.pixels, align(WIDTH * HEIGHT * 3), RW)
            exports = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
            self.draw = next((base + s.address for s in exports.symbols if s.name == b"DrawFrame"), None) if exports else None

    def call(self, address, *arguments):
        self.cpu.mem_write(self.stack_top, struct.pack("<Q", self.stop))
        self.cpu.reg_write(UC_X86_REG_RSP, self.stack_top)
        for register, value in zip((UC_X86_REG_RCX, UC_X86_REG_RDX, UC_X86_REG_R8), arguments):
            self.cpu.reg_write(register, value & 0xffffffffffffffff)
        self.cpu.emu_start(address, self.stop, timeout=500_000, count=3_000_000)
        if self.cpu.reg_read(UC_X86_REG_RIP) != self.stop:
            raise ValueError("Exécution interrompue avant le retour du programme.")
        return self.cpu.reg_read(UC_X86_REG_RAX)

    def frame(self, tick, direction):
        self.call(self.draw, self.pixels, tick, direction)
        return bytes(self.cpu.mem_read(self.pixels, WIDTH * HEIGHT * 3))


class Window:
    def __init__(self, root, folder):
        self.root = root
        self.folder = folder
        self.timer = None
        self.keys = set()
        root.title("Scarlett — prototype x86-64")
        panel = ttk.Frame(root, padding=12)
        panel.pack()
        self.screen = tk.Canvas(panel, width=WIDTH*3, height=HEIGHT*3, bg="#222536", highlightthickness=0)
        self.screen.pack()
        self.picture = self.screen.create_image(0, 0, anchor="nw")
        self.caption = self.screen.create_text(WIDTH*1.5, HEIGHT*1.5, text="Écran du prototype", fill="white")
        self.message = tk.StringVar()
        ttk.Label(panel, textvariable=self.message, wraplength=465).pack(fill="x", pady=8)
        buttons = ttk.Frame(panel)
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Lancer la démo", command=self.demo).pack(side="left")
        ttk.Button(buttons, text="Ouvrir un dossier Xbox…", command=self.choose).pack(side="left", padx=6)
        root.bind("<KeyPress>", lambda event: self.keys.add(event.keysym))
        root.bind("<KeyRelease>", lambda event: self.keys.discard(event.keysym))
        root.bind("<FocusOut>", lambda event: self.keys.clear())
        self.open_package(folder)

    def reset(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.screen.itemconfigure(self.picture, image="")
        self.screen.itemconfigure(self.caption, state="normal")
        self.keys.clear()
        self.machine = None

    def choose(self):
        folder = filedialog.askdirectory(initialdir=self.folder)
        if folder:
            self.open_package(Path(folder))

    def open_package(self, folder):
        self.reset()
        try:
            path = package_entry(folder)
            result = Machine(path)
            code = result.call(result.entry)
            self.message.set(f"{path.name} a terminé. Valeur de retour : {code:#x}.")
        except ERRORS as error:
            self.message.set(str(error))

    def demo(self):
        self.reset()
        try:
            self.machine = Machine(DEMO)
            if self.machine.call(self.machine.entry) != 7 or self.machine.draw is None:
                raise ValueError("La démo ne reconnaît pas le périphérique émulé.")
            self.tick = 0
            self.screen.itemconfigure(self.caption, state="hidden")
            self.message.set("Démo de conduite · Utilise les flèches gauche et droite.")
            self.screen.focus_set()
            self.update_frame()
        except ERRORS as error:
            self.message.set(str(error))

    def update_frame(self):
        self.timer = None
        try:
            direction = int("Right" in self.keys) - int("Left" in self.keys)
            data = self.machine.frame(self.tick, direction)
            image = tk.PhotoImage(data=b"P6\n160 96\n255\n" + data, format="PPM")
            self.image = image.zoom(3)
            self.screen.itemconfigure(self.picture, image=self.image)
            self.tick += 1
            self.timer = self.root.after(33, self.update_frame)
        except ERRORS as error:
            self.message.set(str(error))


if __name__ == "__main__":
    folder = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    folder = next((candidate for candidate in (folder, folder.parent, folder.parent.parent)
                   if (candidate / "MicrosoftGame.Config").is_file()), folder)
    root = tk.Tk()
    window = Window(root, folder)
    if sys.argv[1:] == ["--demo"]:
        root.after_idle(window.demo)
    root.mainloop()
