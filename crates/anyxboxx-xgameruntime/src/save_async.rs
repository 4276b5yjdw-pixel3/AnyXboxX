//! The asynchronous save calls (C++ `async_call.h`): the result is fixed when the call starts, and
//! VIctory's XAsync delivers it on the task queue. The title reads it with the matching `*Result`
//! function, which copies the bytes into its own buffer.

use std::ffi::c_void;
use std::mem::size_of;

use victory_hle::modules::xasync::{self, AsyncBlock, ProviderData};

use crate::object::{HResult, S_OK};

/// XAsyncOp values, as VIctory's provider receives them.
const OP_BEGIN: u32 = 0;
const OP_DO_WORK: u32 = 1;
const OP_GET_RESULT: u32 = 2;
const OP_CLEANUP: u32 = 4;

/// A computed result. `write` fills the title's buffer (`size` bytes) when the title reads it;
/// `discard` releases a result the title never reads (a handle, say).
pub struct Completion {
    pub result: HResult,
    pub size: usize,
    pub write: Option<Box<dyn FnOnce(*mut c_void)>>,
    pub discard: Option<Box<dyn FnOnce()>>,
}

impl Completion {
    /// A result with no data.
    pub fn status(result: HResult) -> Completion {
        Completion {
            result,
            size: 0,
            write: None,
            discard: None,
        }
    }

    /// A result that is one value of type `T`.
    pub fn value<T: Copy + 'static>(result: HResult, value: T) -> Completion {
        Completion {
            result,
            size: size_of::<T>(),
            write: Some(Box::new(move |buffer| {
                // SAFETY: the title's buffer holds `size` bytes, as XAsync checks before reading.
                unsafe { buffer.cast::<T>().write_unaligned(value) };
            })),
            discard: None,
        }
    }
}

/// The provider of every save call: it schedules, completes, copies and frees the result.
extern "system" fn provider(op: u32, data: *const ProviderData) -> HResult {
    // SAFETY: XAsync passes its own provider data, with the context given to `begin`.
    let data = unsafe { &*data };
    let state = data.context.cast::<Completion>();
    match op {
        OP_BEGIN => xasync::XAsyncSchedule(data.block, 0),
        OP_DO_WORK => {
            // SAFETY: the state lives until cleanup, which XAsync calls after completion.
            let state = unsafe { &*state };
            let size = if state.result >= 0 { state.size } else { 0 };
            xasync::XAsyncComplete(data.block, state.result, size);
            S_OK
        }
        OP_GET_RESULT => {
            // SAFETY: as above; the result is copied once, then the title owns its bytes.
            let state = unsafe { &mut *state };
            if let Some(write) = state.write.take() {
                write(data.buffer);
            }
            state.discard = None;
            S_OK
        }
        OP_CLEANUP => {
            // SAFETY: `begin` leaked the state; it is freed exactly once, here.
            let state = unsafe { Box::from_raw(state) };
            if let Some(discard) = state.discard {
                discard();
            }
            S_OK
        }
        _ => S_OK,
    }
}

/// Starts a call whose result is `completion`. On failure the state is freed here.
pub fn begin(block: *mut AsyncBlock, identity: *const c_void, completion: Completion) -> HResult {
    let state = Box::into_raw(Box::new(completion));
    let begun = xasync::XAsyncBegin(
        block,
        state.cast(),
        identity,
        std::ptr::null(),
        Some(provider),
    );
    if begun < 0 {
        // SAFETY: XAsync did not take the state; we free it ourselves.
        let state = unsafe { Box::from_raw(state) };
        if let Some(discard) = state.discard {
            discard();
        }
    }
    begun
}

/// The result of a call started with `identity`, copied into `buffer` (`size` bytes).
pub fn result(
    block: *mut AsyncBlock,
    identity: *const c_void,
    size: usize,
    buffer: *mut c_void,
) -> HResult {
    xasync::XAsyncGetResult(block, identity, size, buffer, std::ptr::null_mut())
}

/// The status of a call with no data, waiting for it if needed as the C++ `XAsyncGetStatus` does.
pub fn status(block: *mut AsyncBlock) -> HResult {
    xasync::XAsyncGetStatus(block, false)
}
