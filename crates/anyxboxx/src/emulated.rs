//! Which imported functions count as emulated, for the reports that `rapport` shares with
//! `banc`, `carte` and `traduction`: VIctory's HLE registry by default, or another runtime's
//! table passed with `--emulated-list` (one `family!function` per line; the parity tests pass
//! the Python HLE registry this way).

use std::collections::BTreeSet;
use std::path::Path;

use anyxboxx_report::ReportError;

use crate::rapport::{family, table, victory_resolves};

pub enum Emulated {
    /// What VIctory binds when it runs the game.
    Victory,
    /// `family!function` lines of another runtime.
    Listed(BTreeSet<String>),
}

impl Emulated {
    pub fn load(list: Option<&Path>) -> Result<Self, ReportError> {
        Ok(match list {
            Some(path) => Self::Listed(table(path)?),
            None => Self::Victory,
        })
    }

    pub fn contains(&self, dll: &str, function: &str) -> bool {
        match self {
            Self::Victory => victory_resolves(dll, function),
            Self::Listed(known) => known.contains(&format!("{}!{function}", family(dll))),
        }
    }
}

/// Repository folders the reports read, with the environment variables of `scarlett.py`.
pub mod folders {
    use std::path::{Path, PathBuf};

    /// `os.environ.get(name) or default`: an empty variable counts as unset.
    pub fn from_env(name: &str, default: PathBuf) -> PathBuf {
        std::env::var_os(name)
            .filter(|v| !v.is_empty())
            .map_or(default, PathBuf::from)
    }

    /// `ANYXBOXX_RUNTIME`, or `runtime/build/bin`: the C++ runtime's DLLs.
    pub fn runtime(repo: &Path) -> PathBuf {
        from_env(
            "ANYXBOXX_RUNTIME",
            repo.join("runtime").join("build").join("bin"),
        )
    }

    /// `ANYXBOXX_TOMBOX_DIR`, or `runtime/build/tombox` (`tools/build_tombox.py`).
    pub fn tombox(repo: &Path) -> PathBuf {
        from_env(
            "ANYXBOXX_TOMBOX_DIR",
            repo.join("runtime").join("build").join("tombox"),
        )
    }

    /// The C++ runtime's sources that list the GDK functions.
    pub fn gdk_sources(repo: &Path) -> PathBuf {
        repo.join("runtime").join("xgameruntime")
    }
}
