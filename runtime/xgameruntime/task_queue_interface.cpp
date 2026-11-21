// Interface XTaskQueue / XAsync / XThread du runtime GDK, servie par AnyXboxX.
//
// Le jeu (xgameruntime.lib) obtient l'objet par QueryApiImpl, puis appelle la
// méthode n° k avec this suivi des arguments de la fonction publique (vérifié
// au désassemblage). Les numéros viennent de gdk_api_table.inc ; le travail est
// fait par le module Task de libHttpClient (MIT, third_party/libhttpclient-task).
#include <windows.h>

#include <cstdio>

#include "XAsync.h"
#include "XAsyncProvider.h"
#include "XTaskQueue.h"
#include "interfaces.h"
#include "trace.h"

namespace {

// Ajoute le paramètre this devant une fonction publique : Adapter<signature>::Call<&F>(this, args...).
template <typename Signature>
struct Adapter;

template <typename Result, typename... Args>
struct Adapter<Result(Args...) noexcept> {
  template <Result (*Function)(Args...) noexcept>
  static Result WINAPI Call(void*, Args... args) noexcept {
    return Function(args...);
  }
};

#define ANYXBOXX_METHOD(function) \
  reinterpret_cast<void*>(&Adapter<decltype(function)>::template Call<&function>)

// --- XThread : marquage « sensible au temps » propre à chaque thread -------------
thread_local bool t_time_sensitive = false;

HRESULT XThreadSetTimeSensitive(bool value) noexcept {
  t_time_sensitive = value;
  return S_OK;
}

HRESULT XThreadVerifyNotTimeSensitive() noexcept { return t_time_sensitive ? E_FAIL : S_OK; }

void XThreadAssertNotTimeSensitive() noexcept {
  if (t_time_sensitive) ANYXBOXX_TRACE("[runtime] appel bloquant depuis un thread sensible au temps");
}

bool XThreadIsTimeSensitive() noexcept { return t_time_sensitive; }

// Méthode n° 8 : aucune fonction publique ne l'appelle dans le GDK 2610.
HRESULT WINAPI UnknownMethod(void*) noexcept {
  ANYXBOXX_TRACE("[runtime] XTaskQueue : méthode n° 8 inconnue appelée");
  return E_NOTIMPL;
}

// --- IUnknown d'un objet statique ------------------------------------------------
HRESULT WINAPI QueryInterface(void* self, REFIID iid, void** out) noexcept;
ULONG WINAPI AddRef(void*) noexcept { return 1; }
ULONG WINAPI Release(void*) noexcept { return 1; }

void* const kMethods[] = {
    reinterpret_cast<void*>(&QueryInterface),        // 0
    reinterpret_cast<void*>(&AddRef),                // 1
    reinterpret_cast<void*>(&Release),               // 2
    ANYXBOXX_METHOD(XAsyncGetStatus),                       // 3
    ANYXBOXX_METHOD(XAsyncGetResultSize),                   // 4
    ANYXBOXX_METHOD(XAsyncCancel),                          // 5
    ANYXBOXX_METHOD(XAsyncRun),                             // 6
    ANYXBOXX_METHOD(XAsyncBegin),                           // 7
    reinterpret_cast<void*>(&UnknownMethod),         // 8
    ANYXBOXX_METHOD(XAsyncSchedule),                        // 9
    ANYXBOXX_METHOD(XAsyncComplete),                        // 10
    ANYXBOXX_METHOD(XAsyncGetResult),                       // 11
    ANYXBOXX_METHOD(XTaskQueueCreate),                      // 12
    ANYXBOXX_METHOD(XTaskQueueCreateComposite),             // 13
    ANYXBOXX_METHOD(XTaskQueueGetPort),                     // 14
    ANYXBOXX_METHOD(XTaskQueueDuplicateHandle),             // 15
    ANYXBOXX_METHOD(XTaskQueueDispatch),                    // 16
    ANYXBOXX_METHOD(XTaskQueueCloseHandle),                 // 17
    ANYXBOXX_METHOD(XTaskQueueSubmitCallback),              // 18
    ANYXBOXX_METHOD(XTaskQueueSubmitDelayedCallback),       // 19
    ANYXBOXX_METHOD(XTaskQueueRegisterWaiter),              // 20
    ANYXBOXX_METHOD(XTaskQueueUnregisterWaiter),            // 21
    ANYXBOXX_METHOD(XTaskQueueTerminate),                   // 22
    ANYXBOXX_METHOD(XTaskQueueRegisterMonitor),             // 23
    ANYXBOXX_METHOD(XTaskQueueUnregisterMonitor),           // 24
    ANYXBOXX_METHOD(XTaskQueueGetCurrentProcessTaskQueue),  // 25
    ANYXBOXX_METHOD(XTaskQueueSetCurrentProcessTaskQueue),  // 26
    ANYXBOXX_METHOD(XThreadSetTimeSensitive),               // 27
    ANYXBOXX_METHOD(XThreadVerifyNotTimeSensitive),         // 28
    ANYXBOXX_METHOD(XThreadAssertNotTimeSensitive),         // 29
    ANYXBOXX_METHOD(XThreadIsTimeSensitive),                // 30
};

struct StaticInterface {
  void* const* methods;
};

const StaticInterface kTaskQueue{kMethods};

constexpr GUID kIUnknown = {0x00000000, 0x0000, 0x0000, {0xC0, 0, 0, 0, 0, 0, 0, 0x46}};
constexpr GUID kTaskQueueIid = {0x073B7DCB, 0x1FCF, 0x4030, {0x94, 0xBE, 0xE3, 0xC9, 0xEB, 0x62, 0x34, 0x28}};

HRESULT WINAPI QueryInterface(void* self, REFIID iid, void** out) noexcept {
  if (out == nullptr) return E_POINTER;
  if (IsEqualGUID(iid, kTaskQueueIid) || IsEqualGUID(iid, kIUnknown)) {
    *out = self;
    return S_OK;
  }
  *out = nullptr;
  return E_NOINTERFACE;
}

// « 073B7DCB-1FCF-4030-94BE-E3C9EB623428 » → GUID (sans dépendance à COM).
bool ParseGuid(const char* text, GUID* out) {
  unsigned long data1 = 0;
  unsigned int data2 = 0, data3 = 0, bytes[8] = {};
  const int fields = sscanf_s(text, "%8lx-%4x-%4x-%2x%2x-%2x%2x%2x%2x%2x%2x", &data1, &data2, &data3,
                                 &bytes[0], &bytes[1], &bytes[2], &bytes[3], &bytes[4], &bytes[5],
                                 &bytes[6], &bytes[7]);
  if (fields != 11) return false;
  out->Data1 = data1;
  out->Data2 = static_cast<unsigned short>(data2);
  out->Data3 = static_cast<unsigned short>(data3);
  for (int index = 0; index < 8; ++index) out->Data4[index] = static_cast<unsigned char>(bytes[index]);
  return true;
}

}  // namespace

namespace anyxboxx {

void* TaskQueueInterface() { return const_cast<StaticInterface*>(&kTaskQueue); }

namespace {

struct ServedEntry {
  GUID provider;
  GUID iid;
  void* (*object)();
  bool valid;
};

ServedEntry MakeEntry(const char* provider, const char* iid, void* (*object)()) {
  ServedEntry entry{};
  entry.object = object;
  entry.valid = ParseGuid(provider, &entry.provider) && ParseGuid(iid, &entry.iid);
  return entry;
}

}  // namespace

void* ServedInterface(const GUID& provider, const GUID& iid) {
  // Lu une seule fois (initialisation statique sûre entre threads) : QueryApiImpl
  // est appelée à chaque fonction X*, des milliers de fois par seconde.
  static const ServedEntry kServed[] = {
#define ANYXBOXX_SERVED_INTERFACE(object, provider_text, iid_text) \
  MakeEntry(provider_text, iid_text, &object),
#include "served_interfaces.inc"
#undef ANYXBOXX_SERVED_INTERFACE
  };
  for (const ServedEntry& entry : kServed) {
    if (entry.valid && IsEqualGUID(provider, entry.provider) && IsEqualGUID(iid, entry.iid)) {
      return entry.object();
    }
  }
  return nullptr;
}

}  // namespace anyxboxx
