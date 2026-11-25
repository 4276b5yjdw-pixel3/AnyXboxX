//! The interfaces AnyXboxX serves itself (`served_interfaces.inc`), and their IUnknown.
//!
//! One static object per C++ object name (`TaskQueueInterface`, `UserInterface`…): it answers
//! every (provider, interface) pair the table gives it, and its method table is sized from the
//! largest slot the GDK table gives those pairs.

use std::collections::BTreeMap;
use std::ffi::c_void;
use std::sync::OnceLock;

use crate::guid::Guid;
use crate::object::{self, E_NOINTERFACE, E_POINTER, HResult, Object, S_OK};
use crate::tables;

const IUNKNOWN: Guid = Guid {
    data1: 0,
    data2: 0,
    data3: 0,
    data4: [0xC0, 0, 0, 0, 0, 0, 0, 0x46],
};

/// One served pair and the object that answers it.
pub struct Served {
    pub provider: Guid,
    pub iid: Guid,
    pub object: &'static Object,
}

fn table() -> &'static [Served] {
    static TABLE: OnceLock<Vec<Served>> = OnceLock::new();
    TABLE.get_or_init(build_table)
}

/// Builds one object per C++ object name, in the order of the table.
fn build_table() -> Vec<Served> {
    let served = tables::served();
    let gdk = tables::gdk();
    let mut pairs_by_object: BTreeMap<String, Vec<(Guid, Guid)>> = BTreeMap::new();
    let mut order = Vec::new();
    for entry in &served {
        if !pairs_by_object.contains_key(&entry.object) {
            order.push(entry.object.clone());
        }
        pairs_by_object
            .entry(entry.object.clone())
            .or_default()
            .push((entry.provider, entry.iid));
    }
    let mut table = Vec::new();
    for name in order {
        let pairs = &pairs_by_object[&name];
        let slots = gdk
            .iter()
            .filter(|api| pairs.contains(&(api.provider, api.iid)))
            .map(|api| api.slot + 1)
            .max()
            .unwrap_or(0);
        let object = object::build(slots, query_interface as *const c_void, &[]);
        table.extend(pairs.iter().map(|&(provider, iid)| Served {
            provider,
            iid,
            object,
        }));
    }
    table
}

/// The served object for `(provider, iid)`, if AnyXboxX serves that pair.
pub fn find(provider: &Guid, iid: &Guid) -> Option<&'static Object> {
    table()
        .iter()
        .find(|served| served.provider == *provider && served.iid == *iid)
        .map(|served| served.object)
}

/// Every served pair, for the tests.
#[cfg(test)]
pub fn pairs() -> impl Iterator<Item = (Guid, Guid)> {
    table().iter().map(|served| (served.provider, served.iid))
}

/// IUnknown::QueryInterface of a served object: itself for IUnknown and for each interface the
/// table gives that object, `E_NOINTERFACE` otherwise.
///
/// # Safety
/// `this` is a served object (the title got it from [`find`]); `iid` and `out` are valid pointers
/// or null, as the COM calling convention allows.
pub unsafe extern "system" fn query_interface(
    this: *mut c_void,
    iid: *const Guid,
    out: *mut *mut c_void,
) -> HResult {
    if out.is_null() {
        return E_POINTER;
    }
    // SAFETY: `out` is non-null and points at one pointer-sized slot, per this function's contract.
    unsafe { *out = std::ptr::null_mut() };
    // SAFETY: `iid` is null or points at a GUID, per this function's contract.
    let Some(&iid) = (unsafe { iid.as_ref() }) else {
        return E_NOINTERFACE;
    };
    let this = this as *const Object;
    let answers = iid == IUNKNOWN
        || table()
            .iter()
            .any(|served| std::ptr::eq(served.object, this) && served.iid == iid);
    if answers {
        // SAFETY: `out` was checked non-null above.
        unsafe { *out = this.cast_mut().cast() };
        S_OK
    } else {
        E_NOINTERFACE
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn serves_each_pair_of_the_cpp_table_and_nothing_else() {
        assert_eq!(pairs().count(), tables::served().len());
        for entry in tables::served() {
            assert!(
                find(&entry.provider, &entry.iid).is_some(),
                "{}",
                entry.object
            );
        }
        let unknown = Guid::parse("00000000-0000-0000-0000-000000000001").unwrap();
        assert!(find(&unknown, &unknown).is_none());
    }

    #[test]
    fn query_interface_answers_iunknown_and_the_served_iid_only() {
        let task_queue = tables::served()
            .into_iter()
            .find(|e| e.object == "TaskQueueInterface")
            .unwrap();
        let object = find(&task_queue.provider, &task_queue.iid).unwrap();
        let this = object as *const Object as *mut c_void;
        let mut out: *mut c_void = std::ptr::null_mut();
        // SAFETY: `this` is a served object and the GUID and out pointers are valid.
        let hr = unsafe { query_interface(this, &IUNKNOWN, &mut out) };
        assert_eq!((hr, out), (S_OK, this));
        // SAFETY: as above.
        let hr = unsafe { query_interface(this, &task_queue.iid, &mut out) };
        assert_eq!((hr, out), (S_OK, this));
        let other = Guid::parse("01ACD177-91F9-4763-A38E-CCBB55CE32E0").unwrap();
        out = std::ptr::dangling_mut::<c_void>();
        // SAFETY: as above.
        let hr = unsafe { query_interface(this, &other, &mut out) };
        assert_eq!((hr, out), (E_NOINTERFACE, std::ptr::null_mut()));
    }
}
