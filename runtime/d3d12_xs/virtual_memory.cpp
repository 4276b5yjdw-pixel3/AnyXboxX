// D3D12ConfigureVirtualMemoryX de d3d12_xs.dll : configuration de la mémoire graphique, appelée
// par le titre avant la création du périphérique (sans cet export, le titre s'arrête en
// « UNIMPLEMENTED d3d12_xs.dll!D3D12ConfigureVirtualMemoryX »).
//
// Structure de 32 octets : quatre mots de 32 bits (drapeaux, pages de la table, octets à
// préserver pour le tampon d'images, réservé), puis deux mots de 64 bits de sortie. Un pointeur
// nul est refusé ; sinon les sorties sont remises à zéro, comme TomBox. Les valeurs reçues sont
// tracées mais ne règlent encore aucune table : la mémoire graphique passe par xmem.dll.
#include <windows.h>

#include <cstdint>

#include "trace.h"

namespace {

struct VirtualMemoryConfiguration {
  std::uint32_t flags;
  std::uint32_t page_table_pages;
  std::uint32_t frame_buffer_preserve_bytes;
  std::uint32_t reserved;
  std::uint64_t output0;
  std::uint64_t output1;
};

}  // namespace

extern "C" {

HRESULT WINAPI D3D12ConfigureVirtualMemoryX(VirtualMemoryConfiguration* description) {
  if (description == nullptr) return E_INVALIDARG;
  anyxboxx::Log("[d3d12_xs] D3D12ConfigureVirtualMemoryX : drapeaux %u, pages %u, tampon %u",
                description->flags, description->page_table_pages, description->frame_buffer_preserve_bytes);
  description->output0 = 0;
  description->output1 = 0;
  return S_OK;
}

}  // extern "C"
