//! XPackage identity and installed-package queries. Unported slots retain the logged E_NOTIMPL stub.
use crate::object::{E_INVALIDARG, E_NOT_SUFFICIENT_BUFFER, HResult, S_OK};
use std::ffi::{c_char, c_void};

unsafe extern "system" fn identifier(
    _this: *mut c_void,
    size: usize,
    buffer: *mut c_char,
) -> HResult {
    let name = crate::game_config::package_name();
    let bytes = if name.is_empty() {
        b"AnyXboxX.Game".as_slice()
    } else {
        name.as_bytes()
    };
    let bytes = &bytes[..bytes.len().min(32)];
    if buffer.is_null() || size <= bytes.len() {
        return E_NOT_SUFFICIENT_BUFFER;
    }
    // SAFETY: caller supplies a buffer of at least size bytes.
    unsafe {
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), buffer.cast(), bytes.len());
        buffer.add(bytes.len()).write(0);
    }
    S_OK
}

unsafe extern "system" fn packaged(_this: *mut c_void) -> bool {
    true
}
unsafe extern "system" fn package_kind(
    _this: *mut c_void,
    _id: *const c_char,
    kind: *mut u32,
) -> HResult {
    if kind.is_null() {
        return E_INVALIDARG;
    }
    // SAFETY: the output is non-null and writable under the caller's contract.
    unsafe {
        *kind = 0;
    }
    S_OK
}
unsafe extern "system" fn chunk_availability(
    _this: *mut c_void,
    _id: *const c_char,
    _count: u32,
    _selectors: *mut c_void,
    availability: *mut u32,
) -> HResult {
    if availability.is_null() {
        return E_INVALIDARG;
    }
    // SAFETY: the output is non-null and writable under the caller's contract.
    unsafe {
        *availability = 0;
    }
    S_OK
}
#[repr(C)]
struct WriteStats {
    interval: u64,
    budget: u64,
    elapsed: u64,
    bytes_written: u64,
}
unsafe extern "system" fn write_stats(_this: *mut c_void, stats: *mut WriteStats) -> HResult {
    if stats.is_null() {
        return E_INVALIDARG;
    }
    // SAFETY: the output is non-null and writable under the caller's contract.
    unsafe {
        *stats = WriteStats {
            interval: 0,
            budget: u64::MAX,
            elapsed: 0,
            bytes_written: 0,
        };
    }
    S_OK
}
pub fn methods() -> Vec<(usize, *const c_void)> {
    vec![
        (3, identifier as *const c_void),
        (4, packaged as *const c_void),
        (12, chunk_availability as *const c_void),
        (30, write_stats as *const c_void),
        (41, package_kind as *const c_void),
    ]
}
