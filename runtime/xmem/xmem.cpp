// xmem.dll d'AnyXboxX : allocateur mémoire de la console, traduit vers le tas du PC.
//
// Signatures publiques : XMemAlloc(taille, attributs) et XMemFree(pointeur, attributs),
// redirigées vers des crochets que le jeu peut remplacer (XMemSetAllocationHooks).
// Les attributs (type de mémoire, alignement) ne sont pas documentés publiquement :
// on aligne de façon prudente et on les ignore.
//
// Chaque bloc revient à l'allocateur qui l'a produit : les blocs par défaut sont
// enregistrés, et les deux crochets sont publiés ensemble (une seule paire atomique).
#include <windows.h>

#include <malloc.h>

#include <atomic>
#include <unordered_set>

#include "trace.h"

namespace {

using AllocRoutine = void*(WINAPI*)(SIZE_T, ULONGLONG);
using FreeRoutine = void(WINAPI*)(void*, ULONGLONG);

struct Hooks {
  AllocRoutine alloc;
  FreeRoutine release;
};

constexpr SIZE_T kSmallAlignment = 64;    // ligne de cache, suffisant pour SIMD
constexpr SIZE_T kPageAlignment = 4096;   // gros blocs : alignés comme une page
constexpr SIZE_T kPageThreshold = 4096;

constexpr Hooks kNoHooks{nullptr, nullptr};
std::atomic<const Hooks*> g_hooks{&kNoHooks};

SRWLOCK g_blocks_lock = SRWLOCK_INIT;
std::unordered_set<void*>& DefaultBlocks() {
  static auto* blocks = new std::unordered_set<void*>();  // jamais détruit : vit jusqu'à la fin du processus
  return *blocks;
}

void Remember(void* block) {
  AcquireSRWLockExclusive(&g_blocks_lock);
  DefaultBlocks().insert(block);
  ReleaseSRWLockExclusive(&g_blocks_lock);
}

bool Forget(void* block) {
  AcquireSRWLockExclusive(&g_blocks_lock);
  const bool known = DefaultBlocks().erase(block) != 0;
  ReleaseSRWLockExclusive(&g_blocks_lock);
  return known;
}

}  // namespace

extern "C" {

void* WINAPI XMemAllocDefault(SIZE_T size, ULONGLONG attributes) {
  const SIZE_T alignment = size >= kPageThreshold ? kPageAlignment : kSmallAlignment;
  void* block = _aligned_malloc(size == 0 ? 1 : size, alignment);
  if (block != nullptr) Remember(block);
  ANYXBOXX_TRACE("[xmem] XMemAlloc %zu octets (attributs 0x%llx) -> %p", size, attributes, block);
  return block;
}

void WINAPI XMemFreeDefault(void* address, ULONGLONG) {
  if (address == nullptr) return;
  if (Forget(address)) {
    _aligned_free(address);
  } else {
    anyxboxx::Log("[xmem] XMemFreeDefault : bloc %p inconnu, ignoré", address);
  }
}

void* WINAPI XMemAlloc(SIZE_T size, ULONGLONG attributes) {
  const Hooks* hooks = g_hooks.load(std::memory_order_acquire);
  return hooks->alloc != nullptr ? hooks->alloc(size, attributes) : XMemAllocDefault(size, attributes);
}

void WINAPI XMemFree(void* address, ULONGLONG attributes) {
  if (address == nullptr) return;
  if (Forget(address)) {  // alloué par défaut, même si des crochets ont été posés depuis
    _aligned_free(address);
    return;
  }
  const Hooks* hooks = g_hooks.load(std::memory_order_acquire);
  if (hooks->release != nullptr) {
    hooks->release(address, attributes);
  } else {
    anyxboxx::Log("[xmem] XMemFree : bloc %p inconnu (crochets retirés ?), ignoré", address);
  }
}

void WINAPI XMemSetAllocationHooks(AllocRoutine alloc, FreeRoutine release) {
  // Paires jamais libérées : un autre thread peut encore lire l'ancienne (quelques octets par appel).
  const Hooks* hooks = (alloc == nullptr && release == nullptr) ? &kNoHooks : new Hooks{alloc, release};
  g_hooks.store(hooks, std::memory_order_release);
}

void WINAPI XMemGetAllocationHooks(AllocRoutine* alloc, FreeRoutine* release) {
  const Hooks* hooks = g_hooks.load(std::memory_order_acquire);
  if (alloc != nullptr) *alloc = hooks->alloc;
  if (release != nullptr) *release = hooks->release;
}

// Même contrat que VirtualQuery (hypothèse : la console reprend l'API Windows).
SIZE_T WINAPI XMemVirtualQuery(const void* address, MEMORY_BASIC_INFORMATION* info, SIZE_T size) {
  return VirtualQuery(address, info, size);
}

// La structure XMEM_WORKING_SET_STATISTICS n'est pas publique : on signale l'échec
// (FALSE), que les appelants connus traitent comme « mémoire utilisée inconnue ».
BOOL WINAPI XMemGetWorkingSetStatistics(int type, void*) {
  ANYXBOXX_TRACE("[xmem] XMemGetWorkingSetStatistics(%d) non disponible", type);
  SetLastError(ERROR_NOT_SUPPORTED);
  return FALSE;
}

}  // extern "C"
