//! Test bench of a package folder (`scarlett.py --banc`, `emu/bench.py`): every PE32+ module,
//! its imports and the share the runtime resolves.
//!
//! The Python bench also loads each module in the Unicorn sandbox and runs its initialisation.
//! The sandbox is dropped (decision D2 of docs/architecture-rust.md), so only the static columns
//! are measured here; see `anyxboxx banc` for how the other columns are reported.

use std::path::Path;

use crate::analyse;
use crate::modules::{file_name, package_modules};

/// One module: imported functions and the share resolved (emulated or provided by the package).
#[derive(Debug, Clone, PartialEq)]
pub struct BenchRow {
    pub name: String,
    pub imports: usize,
    pub coverage: f64,
    /// The analysis failed: the module counts 0 imports, like the Python row "analyse : …".
    pub error: Option<String>,
}

impl BenchRow {
    pub fn new(name: &str, imports: usize, coverage: f64) -> Self {
        Self {
            name: name.into(),
            imports,
            coverage,
            error: None,
        }
    }
}

/// `bench.run` without the sandbox: the static analysis of every module of `folder`.
pub fn rows(
    folder: &Path,
    extra_dirs: &[&Path],
    emulated: &dyn Fn(&str, &str) -> bool,
) -> Vec<BenchRow> {
    package_modules(folder)
        .iter()
        .map(|path| match analyse(path, extra_dirs, emulated) {
            Ok(report) => BenchRow::new(&file_name(path), report.total, report.coverage()),
            Err(error) => BenchRow {
                error: Some(error.to_string()),
                ..BenchRow::new(&file_name(path), 0, 0.0)
            },
        })
        .collect()
}
