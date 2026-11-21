// xgameruntime.dll d'AnyXboxX : le runtime GDK vu par le jeu.
//
// Sur PC, le jeu ne lie pas les API X* directement : la bibliothèque statique
// xgameruntime.lib charge cette DLL, appelle InitializeApiImpl*, puis demande
// chaque interface par QueryApiImpl(fournisseur, interface).
//
// AnyXboxX ne sert encore aucune interface lui-même. Si le runtime GDK de
// Windows est installé (Gaming Services, System32\xgameruntime.dll), les
// demandes lui sont déléguées : le jeu fonctionne, et la trace liste chaque
// interface déléguée, c'est-à-dire ce qu'il reste à écrire. Sans lui, ou avec
// ANYXBOXX_SYSTEM_RUNTIME=0, la réponse est E_NOINTERFACE.
#include <windows.h>

#include <cstdio>

#include "trace.h"

namespace {

constexpr int kXboxScarlettAnaconda = 7;  // XSystemDeviceType::XboxScarlettAnaconda
constexpr int kGuidText = 40;

// Arité réelle non documentée : 8 paramètres relayés couvrent les 4 registres et 4 emplacements
// de pile ; en x64, lire un argument que l'appelant n'a pas passé reste sans danger.
using InitializeRoutine = HRESULT(WINAPI*)(void*, void*, void*, void*, void*, void*, void*, void*);
using QueryRoutine = HRESULT(WINAPI*)(const GUID*, const GUID*, void**, void*);

// Runtime GDK de Windows, chargé par son chemin complet (sinon Windows rendrait le nôtre).
HMODULE SystemRuntime() {
  static const HMODULE module = []() -> HMODULE {
    char flag[4] = {};
    if (GetEnvironmentVariableA("ANYXBOXX_SYSTEM_RUNTIME", flag, sizeof flag) == 1 && flag[0] == '0') {
      return nullptr;
    }
    wchar_t path[MAX_PATH];
    const UINT length = GetSystemDirectoryW(path, MAX_PATH);
    if (length == 0 || length > MAX_PATH - 20) return nullptr;
    wcscat_s(path, L"\\xgameruntime.dll");
    HMODULE loaded = LoadLibraryExW(path, nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    ANYXBOXX_TRACE("[runtime] runtime GDK de Windows %s", loaded ? "trouvé : délégation active" : "absent");
    return loaded;
  }();
  return module;
}

template <typename Routine>
Routine SystemFunction(const char* name) {
  const HMODULE module = SystemRuntime();
  return module ? reinterpret_cast<Routine>(GetProcAddress(module, name)) : nullptr;
}

// Vrai la première fois qu'un couple (fournisseur, interface) est vu : la file de
// tâches est demandée des milliers de fois par seconde, la trace n'en garde qu'une.
bool FirstQuery(const GUID* provider, const GUID* iid) {
  constexpr int kMaxRemembered = 128;
  static SRWLOCK lock = SRWLOCK_INIT;
  static GUID seen[kMaxRemembered][2];
  static int count = 0;
  if (provider == nullptr || iid == nullptr) return true;
  AcquireSRWLockExclusive(&lock);
  bool first = true;
  for (int index = 0; index < count && first; ++index) {
    first = !(IsEqualGUID(seen[index][0], *provider) && IsEqualGUID(seen[index][1], *iid));
  }
  if (first && count >= kMaxRemembered) {
    first = false;  // table pleine : on se tait plutôt que d'inonder la trace
  } else if (first) {
    seen[count][0] = *provider;
    seen[count][1] = *iid;
    ++count;
  }
  ReleaseSRWLockExclusive(&lock);
  return first;
}

HRESULT Initialize(const char* name, void* a, void* b, void* c, void* d, void* e, void* f,
                   void* g, void* h) {
  const auto system = SystemFunction<InitializeRoutine>(name);
  const HRESULT result = system ? system(a, b, c, d, e, f, g, h) : S_OK;
  ANYXBOXX_TRACE("[runtime] %s -> 0x%08lX%s", name, static_cast<unsigned long>(result),
                 system ? " (Windows)" : "");
  return result;
}

void FormatGuid(const GUID* guid, char (&out)[kGuidText]) {
  if (guid == nullptr) {
    std::snprintf(out, kGuidText, "{null}");
    return;
  }
  std::snprintf(out, kGuidText, "{%08lX-%04hX-%04hX-%02X%02X-%02X%02X%02X%02X%02X%02X}",
                guid->Data1, guid->Data2, guid->Data3, guid->Data4[0], guid->Data4[1],
                guid->Data4[2], guid->Data4[3], guid->Data4[4], guid->Data4[5],
                guid->Data4[6], guid->Data4[7]);
}

}  // namespace

extern "C" {

// Paramètres non documentés : transmis tels quels au runtime de Windows s'il est là.
HRESULT WINAPI InitializeApiImpl(void* a, void* b, void* c, void* d, void* e, void* f, void* g, void* h) {
  return Initialize("InitializeApiImpl", a, b, c, d, e, f, g, h);
}

HRESULT WINAPI InitializeApiImplEx(void* a, void* b, void* c, void* d, void* e, void* f, void* g, void* h) {
  return Initialize("InitializeApiImplEx", a, b, c, d, e, f, g, h);
}

HRESULT WINAPI InitializeApiImplEx2(void* a, void* b, void* c, void* d, void* e, void* f, void* g, void* h) {
  return Initialize("InitializeApiImplEx2", a, b, c, d, e, f, g, h);
}

HRESULT WINAPI UninitializeApiImpl(void* a, void* b, void* c, void* d, void* e, void* f, void* g, void* h) {
  return Initialize("UninitializeApiImpl", a, b, c, d, e, f, g, h);
}

HRESULT WINAPI QueryApiImpl(const GUID* provider, const GUID* iid, void** out, void* reserved) {
  if (out != nullptr) *out = nullptr;
  if (provider == nullptr || iid == nullptr || out == nullptr) return E_NOINTERFACE;
  const auto system = SystemFunction<QueryRoutine>("QueryApiImpl");
  const HRESULT result = system ? system(provider, iid, out, reserved) : E_NOINTERFACE;
  if (anyxboxx::TraceEnabled() && FirstQuery(provider, iid)) {
    char provider_text[kGuidText];
    char iid_text[kGuidText];
    FormatGuid(provider, provider_text);
    FormatGuid(iid, iid_text);
    anyxboxx::Log("[runtime] QueryApiImpl %s %s -> 0x%08lX%s", provider_text, iid_text,
                  static_cast<unsigned long>(result), system ? " (délégué à Windows)" : "");
  }
  return result;
}

void WINAPI XErrorReport(HRESULT code, const char* message) {
  anyxboxx::Log("[XErrorReport] 0x%08lX %s", static_cast<unsigned long>(code),
                message != nullptr ? message : "");
}

HRESULT WINAPI XGameRuntimeInitialize() { return S_OK; }

void WINAPI XGameRuntimeUninitialize() {}

int WINAPI XSystemGetDeviceType() { return kXboxScarlettAnaconda; }

}  // extern "C"
