"""AnyXboxX — prototype d'émulateur Xbox Series X (interface et ligne de commande)."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# Le lanceur démarre Python en mode isolé (-I), qui n'ajoute pas ce dossier au chemin.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pefile  # noqa: E402
from unicorn import UcError  # noqa: E402

from emu.config import MANIFEST, read_package  # noqa: E402
from emu.machine import Machine  # noqa: E402
from emu.report import analyse  # noqa: E402

WIDTH, HEIGHT, ZOOM = 160, 96, 3
FRAME_MS = 33
DEMO = HERE / "demo.pe"
XBOX_SERIES_X = 7
ERRORS = (ValueError, OSError, ET.ParseError, pefile.PEFormatError, UcError)
TITLE = "AnyXboxX — émulateur Xbox Series X (prototype)"


def resolve_target(path):
    """Accepte un dossier de paquet GDK ou directement un exécutable."""
    path = Path(path)
    if path.is_dir():
        package = read_package(path)
        return package.scarlett_entry(), package.title_id
    return path, 0


def print_report(path, extra_dirs=()):
    try:
        exe, _ = resolve_target(path)
        print(analyse(exe, extra_dirs).text())
        return 0
    except ERRORS as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1


class Window:
    def __init__(self, root, folder):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.folder = folder
        self.timer = None
        self.keys = set()
        self.machine = None
        root.title(TITLE)
        panel = ttk.Frame(root, padding=12)
        panel.pack(fill="both", expand=True)
        self.screen = tk.Canvas(panel, width=WIDTH * ZOOM, height=HEIGHT * ZOOM,
                                bg="#222536", highlightthickness=0)
        self.screen.pack()
        self.picture = self.screen.create_image(0, 0, anchor="nw")
        self.caption = self.screen.create_text(WIDTH * ZOOM / 2, HEIGHT * ZOOM / 2,
                                               text="Écran Xbox Series X émulé", fill="white")
        self.message = tk.StringVar()
        ttk.Label(panel, textvariable=self.message, wraplength=465).pack(fill="x", pady=8)
        buttons = ttk.Frame(panel)
        buttons.pack(anchor="w")
        ttk.Button(buttons, text="Lancer la démo", command=self.demo).pack(side="left")
        ttk.Button(buttons, text="Ouvrir un dossier Xbox…", command=self.choose).pack(
            side="left", padx=6)
        self.journal = tk.Text(panel, height=10, width=60, state="disabled",
                               bg="#14161f", fg="#d7dae6", font=("Consolas", 9))
        self.journal.pack(fill="both", expand=True, pady=(8, 0))
        root.bind("<KeyPress>", lambda event: self.keys.add(event.keysym))
        root.bind("<KeyRelease>", lambda event: self.keys.discard(event.keysym))
        root.bind("<FocusOut>", lambda event: self.keys.clear())
        if (folder / MANIFEST).is_file():
            self.open_package(folder)

    def write(self, text):
        self.journal.configure(state="normal")
        self.journal.insert("end", text + "\n")
        self.journal.see("end")
        self.journal.configure(state="disabled")

    def reset(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.screen.itemconfigure(self.picture, image="")
        self.screen.itemconfigure(self.caption, state="normal")
        self.keys.clear()
        self.machine = None
        self.journal.configure(state="normal")
        self.journal.delete("1.0", "end")
        self.journal.configure(state="disabled")

    def choose(self):
        from tkinter import filedialog

        folder = filedialog.askdirectory(initialdir=self.folder)
        if folder:
            self.open_package(Path(folder))

    def open_package(self, folder):
        self.reset()
        try:
            exe, title_id = resolve_target(folder)
            self.write(analyse(exe).text())
            machine = Machine(exe, title_id=title_id, log=self.write)
            code = machine.start()
            self.message.set(f"{exe.name} a terminé. Valeur de retour : {code:#x}.")
        except ERRORS as error:
            self.message.set(str(error))

    def demo(self):
        self.reset()
        try:
            self.machine = Machine(DEMO, log=self.write)
            draw = self.machine.image.exports.get("DrawFrame")
            if self.machine.start() != XBOX_SERIES_X or draw is None:
                raise ValueError("La démo ne reconnaît pas la Xbox Series X émulée.")
            self.draw = draw
            self.pixels = self.machine.heap.alloc(WIDTH * HEIGHT * 3)
            self.tick = 0
            self.screen.itemconfigure(self.caption, state="hidden")
            self.message.set("Démo de conduite · Utilise les flèches gauche et droite.")
            self.write("Démo lancée : XSystemGetDeviceType → XboxScarlettAnaconda (7).")
            self.screen.focus_set()
            self.update_frame()
        except ERRORS as error:
            self.message.set(str(error))

    def update_frame(self):
        self.timer = None
        try:
            direction = int("Right" in self.keys) - int("Left" in self.keys)
            self.machine.call(self.draw, self.pixels, self.tick, direction)
            data = bytes(self.machine.cpu.mem_read(self.pixels, WIDTH * HEIGHT * 3))
            header = f"P6\n{WIDTH} {HEIGHT}\n255\n".encode()
            self.image = self.tk.PhotoImage(data=header + data, format="PPM").zoom(ZOOM)
            self.screen.itemconfigure(self.picture, image=self.image)
            self.tick += 1
            self.timer = self.root.after(FRAME_MS, self.update_frame)
        except ERRORS as error:
            self.message.set(str(error))


def find_package_folder():
    start = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    return next((c for c in (start, start.parent, start.parent.parent)
                 if (c / MANIFEST).is_file()), start)


def main(argv):
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # --rapport/--banc <cible> [dossiers de DLL supplémentaires…]
    extra_dirs = tuple(Path(d) for d in argv[2:])
    if len(argv) >= 2 and argv[0] == "--rapport":
        return print_report(argv[1], extra_dirs)
    if len(argv) >= 2 and argv[0] == "--banc":
        from emu import bench

        print(bench.table(bench.run(Path(argv[1]), extra_dirs)))
        return 0
    import tkinter as tk

    root = tk.Tk()
    window = Window(root, find_package_folder())
    if argv == ["--demo"]:
        root.after_idle(window.demo)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
