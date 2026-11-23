// « Will my PC run it? » : détecte ce que le navigateur révèle (GPU par WebGL, threads, RAM plafonnée à 8 Go
// par Chrome), laisse corriger dans les listes, puis affiche l'estimation. Rien n'est envoyé nulle part.
import { CPUS, GPUS, detectGpu, estimate } from "./estimate.js";

const RAM_CHOICES = [8, 16, 32, 64];
const $ = (id) => document.getElementById(id);

function webglRenderer() {
  try {
    const gl = document.createElement("canvas").getContext("webgl");
    const ext = gl && gl.getExtension("WEBGL_debug_renderer_info");
    return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "";
  } catch (erreur) {
    console.warn("WebGL unavailable:", erreur);
    return "";
  }
}

function option(value, label) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}

function fillSelects(detected, threads, ramGb) {
  $("gpu").append(option("", "Choose your graphics card"), ...GPUS.map((g) => option(g[0], g[1])));
  const auto = threads ? `Not listed / unknown (${threads} threads detected)` : "Not listed / unknown";
  $("cpu").append(option("", auto), ...CPUS.map((c) => option(c[0], c[0])));
  $("ram").append(...RAM_CHOICES.map((gb) => option(String(gb), `${gb} GB`)));
  if (detected) $("gpu").value = detected.key;
  $("laptop").checked = Boolean(detected && detected.laptop);
  $("ram").value = String(RAM_CHOICES.find((gb) => gb >= (ramGb || 16)) || 16);
}

const item = (texte) => Object.assign(document.createElement("li"), { textContent: texte });

function render(threads) {
  const gpuKey = $("gpu").value;
  $("empty").hidden = Boolean(gpuKey);
  $("answer").hidden = !gpuKey;
  if (!gpuKey) return;
  const r = estimate({
    gpuKey, cpuLabel: $("cpu").value || null, threads, ramGb: Number($("ram").value), laptop: $("laptop").checked,
  });
  $("fps").textContent = r.fpsLow === r.fpsHigh ? `~${r.fpsLow} fps` : `~${r.fpsLow}–${r.fpsHigh} fps`;
  $("quality").textContent = r.quality;
  $("bottleneck").textContent = r.bottleneck ? `Limited by your ${r.bottleneck}.` : "";
  $("notes").replaceChildren(...r.notes.map(item));
}

function main() {
  const renderer = webglRenderer();
  const detected = detectGpu(renderer);
  const threads = navigator.hardwareConcurrency || null;
  const ramGb = navigator.deviceMemory || null;
  $("detected").replaceChildren(...[
    `Graphics: ${detected ? detected.label + (detected.laptop ? " (laptop)" : "") : renderer || "not revealed by this browser"}`,
    `CPU threads: ${threads ?? "not revealed"}`,
    `RAM: ${ramGb ? `about ${ramGb} GB (browsers round this value, check below)` : "not revealed"}`,
  ].map(item));
  fillSelects(detected, threads, ramGb);
  for (const id of ["gpu", "cpu", "ram", "laptop"]) $(id).addEventListener("change", () => render(threads));
  render(threads);
}

main();
