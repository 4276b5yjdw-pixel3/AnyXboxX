// D3D12ConfigureVirtualMemoryX de d3d12_xs.dll : configuration de la mémoire graphique, appelée
// par le titre avant la création du périphérique (sans cet export, le titre s'arrête en
// « UNIMPLEMENTED d3d12_xs.dll!D3D12ConfigureVirtualMemoryX »).
//
// Disposition de la structure, d'après TomBox (crates/compat/d3d12_xs/src/vmem_x.rs, struct
// VirtualMemoryConfiguration) : flags, page_table_pages, frame_buffer_preserve_bytes, reserved
// (quatre mots de 32 bits), output0 et output1 (deux mots de 64 bits).
//
// Ce que le titre remplit et lit dans cette structure n'est pas mesuré par AnyXboxX : on suppose
// que le pointeur reçu ne couvre pas forcément les 32 octets (il peut viser le cadre de pile de
// l'appelant). Choix prudent : on ne lit que flags et page_table_pages (tracés), on n'écrit
// aucune sortie et on rend S_OK. Un pointeur nul est refusé.
#include <windows.h>

#include <cstdint>

#include "trace.h"

namespace {

struct VirtualMemoryConfigurationHead {
  std::uint32_t flags;
  std::uint32_t page_table_pages;
};

}  // namespace

extern "C" {

HRESULT WINAPI D3D12ConfigureVirtualMemoryX(VirtualMemoryConfigurationHead* description) {
  if (description == nullptr) return E_INVALIDARG;
  anyxboxx::Log("[d3d12_xs] D3D12ConfigureVirtualMemoryX : drapeaux %u, pages %u",
                description->flags, description->page_table_pages);
  return S_OK;
}

}  // extern "C"
