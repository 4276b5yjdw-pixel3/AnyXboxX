// Identité du jeu lue dans son MicrosoftGame.config (dossier donné par ANYXBOXX_GAME_DIR,
// que le mode natif d'AnyXboxX renseigne avant de lancer le jeu).
#pragma once

#include <cstdint>

namespace anyxboxx {

// Title ID déclaré par <TitleId>, ou 0 si le fichier ou l'élément manque.
uint32_t GameTitleId();

// Taille de <PersistentLocalStorage><SizeMB> en octets, ou 0 si non déclarée.
uint64_t GameLocalStorageBytes();

}  // namespace anyxboxx
