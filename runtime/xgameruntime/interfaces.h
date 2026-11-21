// Objets d'interface du runtime GDK servis par AnyXboxX (voir served_interfaces.inc).
#pragma once

#include <windows.h>

namespace anyxboxx {

// XTaskQueue, XAsync et XThread : interface {073B7DCB-1FCF-4030-94BE-E3C9EB623428}.
void* TaskQueueInterface();

// Renvoie l'objet qui sert (fournisseur, interface), ou nullptr.
void* ServedInterface(const GUID& provider, const GUID& iid);

}  // namespace anyxboxx
