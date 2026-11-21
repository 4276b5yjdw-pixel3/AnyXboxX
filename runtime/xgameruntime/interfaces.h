// Objets d'interface du runtime GDK servis par AnyXboxX (voir served_interfaces.inc).
#pragma once

#include <windows.h>

namespace anyxboxx {

// XTaskQueue, XAsync et XThread : interface {073B7DCB-1FCF-4030-94BE-E3C9EB623428}.
void* TaskQueueInterface();

// XUser : profil local hors ligne, fournisseur {01ACD177…} (5 versions d'interface).
void* UserInterface();

// XUserGetGamertag : interface {CEF4FAC0…} du même fournisseur.
void* GamertagInterface();

// Identité Xbox Series X (system_interface.cpp) : XSystem, analytique, Title ID et
// lancement, fonctionnalités du runtime, report d'extinction de l'écran et XLaunchUri.
void* SystemInterface();
void* AnalyticsInterface();
void* GameInterface();
void* FeatureInterface();
void* DisplayInterface();

// Renvoie l'objet qui sert (fournisseur, interface), ou nullptr.
void* ServedInterface(const GUID& provider, const GUID& iid);

}  // namespace anyxboxx
