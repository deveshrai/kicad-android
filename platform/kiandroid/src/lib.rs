//! Android platform layer for KiCad.
//!
//! Exposed to KiCad's C++ through the C ABI declared in `include/kiandroid.h`.
//! Every exported function is panic-safe: panics abort (release profile) rather than
//! unwinding across the FFI boundary.

pub mod fonts;

use std::ffi::{CStr, CString, c_char, c_int};
use std::path::Path;

use fonts::{FindResult, FontDb};

/// Opaque font database handle: owns the db plus a cache of C strings for family names.
pub struct KiaFontDb {
    db: FontDb,
    names: Vec<CString>,
}

impl KiaFontDb {
    fn refresh_names(&mut self) {
        self.names = self
            .db
            .family_names()
            .into_iter()
            .filter_map(|n| CString::new(n).ok())
            .collect();
    }
}

unsafe fn cstr<'a>(p: *const c_char) -> Option<&'a str> {
    if p.is_null() {
        return None;
    }

    unsafe { CStr::from_ptr(p) }.to_str().ok()
}

/// Creates a font database from the device's system font configuration.
#[unsafe(no_mangle)]
pub extern "C" fn kia_fontdb_new_system() -> *mut KiaFontDb {
    let mut h = KiaFontDb { db: FontDb::system(), names: vec![] };
    h.refresh_names();
    Box::into_raw(Box::new(h))
}

/// Creates a font database from an explicit fonts.xml and font directory (for testing or
/// non-standard ROMs). Either may be NULL.
///
/// # Safety
/// Arguments must be NULL or valid NUL-terminated strings.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_new(fonts_xml_path: *const c_char, fonts_dir: *const c_char) -> *mut KiaFontDb {
    let mut db = FontDb::new();

    if let (Some(xml_path), Some(dir)) = unsafe { (cstr(fonts_xml_path), cstr(fonts_dir)) } {
        if let Ok(xml) = std::fs::read_to_string(xml_path) {
            let _ = db.load_fonts_xml(&xml, Path::new(dir), false);
        }
    }

    let mut h = KiaFontDb { db, names: vec![] };
    h.refresh_names();
    Box::into_raw(Box::new(h))
}

/// # Safety
/// `db` must come from a `kia_fontdb_new*` call and not be used afterwards.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_free(db: *mut KiaFontDb) {
    if !db.is_null() {
        drop(unsafe { Box::from_raw(db) });
    }
}

/// Registers a font file (e.g. a font embedded in a KiCad project). Returns faces added.
///
/// # Safety
/// `db` must be valid; `path` a valid NUL-terminated string.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_add_file(db: *mut KiaFontDb, path: *const c_char) -> c_int {
    let (Some(h), Some(path)) = (unsafe { db.as_mut() }, unsafe { cstr(path) }) else { return 0 };
    let n = h.db.add_font_file(Path::new(path));

    if n > 0 {
        h.refresh_names();
    }

    n as c_int
}

/// Registers every font file in a directory. Returns faces added.
///
/// # Safety
/// `db` must be valid; `dir` a valid NUL-terminated string.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_add_dir(db: *mut KiaFontDb, dir: *const c_char) -> c_int {
    let (Some(h), Some(dir)) = (unsafe { db.as_mut() }, unsafe { cstr(dir) }) else { return 0 };
    let n = h.db.add_font_dir(Path::new(dir));

    if n > 0 {
        h.refresh_names();
    }

    n as c_int
}

/// Looks up a face. Writes the file path (NUL-terminated, truncated never: returns
/// `Error` if it doesn't fit) and the face index. Returns a `FindResult` value.
///
/// # Safety
/// `db` must be valid, `name` a valid string, `out_path` writable for `out_path_len` bytes,
/// `out_index` NULL or writable.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_find(
    db: *const KiaFontDb,
    name: *const c_char,
    bold: bool,
    italic: bool,
    out_path: *mut c_char,
    out_path_len: usize,
    out_index: *mut c_int,
) -> c_int {
    let (Some(h), Some(name)) = (unsafe { db.as_ref() }, unsafe { cstr(name) }) else {
        return FindResult::Error as c_int;
    };

    let (result, face) = h.db.find(name, bold, italic);

    let Some(face) = face else { return FindResult::Error as c_int };
    let path = face.path.to_string_lossy();
    let bytes = path.as_bytes();

    if out_path.is_null() || bytes.len() + 1 > out_path_len {
        return FindResult::Error as c_int;
    }

    unsafe {
        std::ptr::copy_nonoverlapping(bytes.as_ptr(), out_path as *mut u8, bytes.len());
        *out_path.add(bytes.len()) = 0;

        if !out_index.is_null() {
            *out_index = face.index as c_int;
        }
    }

    result as c_int
}

/// Number of font families.
///
/// # Safety
/// `db` must be valid or NULL.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_family_count(db: *const KiaFontDb) -> usize {
    unsafe { db.as_ref() }.map_or(0, |h| h.names.len())
}

/// Family name `i` (sorted). The pointer stays valid until the db is modified or freed.
///
/// # Safety
/// `db` must be valid or NULL.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kia_fontdb_family_name(db: *const KiaFontDb, i: usize) -> *const c_char {
    unsafe { db.as_ref() }
        .and_then(|h| h.names.get(i))
        .map_or(std::ptr::null(), |s| s.as_ptr())
}
