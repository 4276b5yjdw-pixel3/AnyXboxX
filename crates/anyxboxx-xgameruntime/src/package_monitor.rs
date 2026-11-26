//! Monitors for the package that is already installed locally.
use crate::object::{E_INVALIDARG, HResult, S_OK};
use std::collections::HashSet;
use std::ffi::{c_char, c_void};
use std::sync::{Mutex, OnceLock};

fn monitors() -> &'static Mutex<HashSet<usize>> {
    static MONITORS: OnceLock<Mutex<HashSet<usize>>> = OnceLock::new();
    MONITORS.get_or_init(|| Mutex::new(HashSet::new()))
}
pub unsafe extern "system" fn create(
    _this: *mut c_void,
    _id: *const c_char,
    _count: u32,
    _selectors: *mut c_void,
    _interval: u32,
    _queue: *mut c_void,
    output: *mut *mut c_void,
) -> HResult {
    if output.is_null() {
        return E_INVALIDARG;
    }
    let monitor = Box::into_raw(Box::new(0u8)).cast::<c_void>();
    monitors().lock().unwrap().insert(monitor as usize);
    // SAFETY: the caller provides a writable output pointer.
    unsafe {
        *output = monitor;
    }
    S_OK
}
pub unsafe extern "system" fn install(
    this: *mut c_void,
    id: *const c_char,
    count: u32,
    selectors: *mut c_void,
    interval: u32,
    _suppress_ui: bool,
    queue: *mut c_void,
    output: *mut *mut c_void,
) -> HResult {
    // SAFETY: arguments follow create's contract.
    unsafe { create(this, id, count, selectors, interval, queue, output) }
}
pub unsafe extern "system" fn close(_this: *mut c_void, monitor: *mut c_void) {
    if monitors().lock().unwrap().remove(&(monitor as usize)) {
        // SAFETY: a registered monitor was allocated above and is removed only once.
        drop(unsafe { Box::from_raw(monitor.cast::<u8>()) });
    }
}
#[repr(C)]
pub struct InstallationProgress {
    total: u64,
    installed: u64,
    launch: u64,
    launchable: bool,
    completed: bool,
}
pub unsafe extern "system" fn progress(
    _this: *mut c_void,
    _monitor: *mut c_void,
    progress: *mut InstallationProgress,
) {
    if !progress.is_null() {
        // SAFETY: the caller supplies writable progress storage.
        unsafe {
            *progress = InstallationProgress {
                total: 1,
                installed: 1,
                launch: 1,
                launchable: true,
                completed: true,
            };
        }
    }
}
pub unsafe extern "system" fn update(_this: *mut c_void, _monitor: *mut c_void) -> bool {
    false
}
