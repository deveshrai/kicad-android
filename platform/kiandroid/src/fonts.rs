//! Android system font database: a replacement for the slice of fontconfig KiCad uses.
//!
//! Android ships no fontconfig. Its font configuration lives in `/system/etc/fonts.xml`
//! (named families, fallback families and aliases), with font files in `/system/fonts`.
//! This module parses that file and adds any extra font files (user fonts, fonts embedded
//! in a KiCad project) by reading their `name` tables. It then answers the two questions
//! KiCad asks of fontconfig: "which file and face index for family X, bold/italic?" and
//! "which families exist?".

use std::collections::{BTreeSet, HashMap};
use std::fs;
use std::path::{Path, PathBuf};

/// Mirrors `fontconfig::FONTCONFIG::FF_RESULT` in KiCad (`include/font/fontconfig.h`).
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FindResult {
    Ok = 0,
    Error = 1,
    Substitute = 2,
    MissingBold = 3,
    MissingItalic = 4,
    MissingBoldItalic = 5,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FontFace {
    pub path: PathBuf,
    pub index: u32,
    pub weight: u16,
    pub italic: bool,
}

#[derive(Debug, Clone, Default)]
pub struct Family {
    /// Display name as it should appear in KiCad's font picker.
    pub name: String,
    pub faces: Vec<FontFace>,
}

#[derive(Debug, Clone)]
struct Alias {
    to: String,
    weight: Option<u16>,
}

/// Family used when nothing matches. Every Android device defines it.
pub const DEFAULT_FAMILY: &str = "sans-serif";

#[derive(Debug, Default)]
pub struct FontDb {
    /// Keyed by lower-cased family name.
    families: HashMap<String, Family>,
    /// Keyed by lower-cased alias name.
    aliases: HashMap<String, Alias>,
}

const REGULAR: u16 = 400;
const BOLD: u16 = 700;
/// Faces at or above this weight are accepted as "bold" without synthesis.
const BOLD_THRESHOLD: u16 = 600;

fn key(name: &str) -> String {
    name.trim().to_lowercase()
}

impl FontDb {
    pub fn new() -> Self {
        Self::default()
    }

    /// Loads an Android `fonts.xml`. Relative font file names resolve against `fonts_dir`.
    /// Faces whose files don't exist are dropped unless `keep_missing` is set (for tests).
    pub fn load_fonts_xml(&mut self, xml: &str, fonts_dir: &Path, keep_missing: bool) -> Result<(), String> {
        let doc = roxmltree::Document::parse(xml).map_err(|e| e.to_string())?;
        let root = doc.root_element();

        for node in root.children().filter(|n| n.is_element()) {
            match node.tag_name().name() {
                "family" => self.load_family(node, None, fonts_dir, keep_missing),
                // Android 15+: a named list of families, for example one per script.
                "family-list" => {
                    let name = node.attribute("name");
                    for fam in node.children().filter(|n| n.has_tag_name("family")) {
                        self.load_family(fam, name, fonts_dir, keep_missing);
                    }
                }
                "alias" => {
                    if let (Some(name), Some(to)) = (node.attribute("name"), node.attribute("to")) {
                        let weight = node.attribute("weight").and_then(|w| w.parse().ok());
                        self.aliases.insert(key(name), Alias { to: to.to_string(), weight });
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }

    fn load_family(&mut self, node: roxmltree::Node, list_name: Option<&str>, fonts_dir: &Path, keep_missing: bool) {
        let mut faces = Vec::new();

        for font in node.children().filter(|n| n.has_tag_name("font")) {
            // The file name is the element's direct text; <axis> children may follow it.
            let file: String = font
                .children()
                .filter(|c| c.is_text())
                .filter_map(|c| c.text())
                .collect::<String>()
                .trim()
                .to_string();

            if file.is_empty() {
                continue;
            }

            let path = fonts_dir.join(&file);

            if !keep_missing && !path.exists() {
                continue;
            }

            faces.push(FontFace {
                path,
                index: font.attribute("index").and_then(|i| i.parse().ok()).unwrap_or(0),
                weight: font.attribute("weight").and_then(|w| w.parse().ok()).unwrap_or(REGULAR),
                italic: font.attribute("style") == Some("italic"),
            });
        }

        if faces.is_empty() {
            return;
        }

        // Fallback families (per-script Noto fonts) have no name attribute. Name them
        // after the font's own family name so users can still pick them.
        let name = node
            .attribute("name")
            .or(list_name)
            .map(str::to_string)
            .or_else(|| family_name_from_file(&faces[0].path, faces[0].index));

        if let Some(name) = name {
            self.add_faces(&name, faces);
        }
    }

    fn add_faces(&mut self, name: &str, faces: Vec<FontFace>) {
        let fam = self.families.entry(key(name)).or_insert_with(|| Family { name: name.to_string(), faces: vec![] });

        for f in faces {
            if !fam.faces.contains(&f) {
                fam.faces.push(f);
            }
        }
    }

    /// Registers a single font file (a TTF/OTF, or every face of a TTC/OTC) under the
    /// family names read from its `name` table. Returns the number of faces added.
    pub fn add_font_file(&mut self, path: &Path) -> usize {
        let Ok(data) = fs::read(path) else { return 0 };
        let count = ttf_parser::fonts_in_collection(&data).unwrap_or(1);
        let mut added = 0;

        for index in 0..count {
            let Ok(face) = ttf_parser::Face::parse(&data, index) else { continue };
            let Some(name) = face_family_name(&face) else { continue };

            self.add_faces(
                &name,
                vec![FontFace {
                    path: path.to_path_buf(),
                    index,
                    weight: face.weight().to_number(),
                    italic: face.is_italic(),
                }],
            );
            added += 1;
        }

        added
    }

    /// Adds every font file found (non-recursively) in `dir`.
    pub fn add_font_dir(&mut self, dir: &Path) -> usize {
        let Ok(entries) = fs::read_dir(dir) else { return 0 };
        let mut added = 0;

        for e in entries.flatten() {
            let p = e.path();
            let is_font = p
                .extension()
                .and_then(|x| x.to_str())
                .map(|x| matches!(x.to_ascii_lowercase().as_str(), "ttf" | "otf" | "ttc" | "otc"))
                .unwrap_or(false);

            if is_font {
                added += self.add_font_file(&p);
            }
        }

        added
    }

    /// Resolves aliases (chained at most a few levels) to a family and an optional weight hint.
    fn resolve(&self, name: &str) -> Option<(&Family, Option<u16>)> {
        let mut k = key(name);
        let mut weight = None;

        for _ in 0..8 {
            if let Some(f) = self.families.get(&k) {
                return Some((f, weight));
            }

            let alias = self.aliases.get(&k)?;
            weight = weight.or(alias.weight);
            k = key(&alias.to);
        }

        None
    }

    /// Finds the best face for `name`. Same semantics as KiCad's `FONTCONFIG::FindFont`:
    /// `Substitute` when the family is unknown (the default family is returned instead),
    /// `Missing*` when the family exists but lacks the requested style (KiCad synthesizes it).
    pub fn find(&self, name: &str, bold: bool, italic: bool) -> (FindResult, Option<&FontFace>) {
        let (family, alias_weight, substituted) = match self.resolve(name) {
            Some((f, w)) => (f, w, false),
            None => match self.resolve(DEFAULT_FAMILY) {
                Some((f, w)) => (f, w, true),
                None => match self.families.values().next() {
                    Some(f) => (f, None, true),
                    None => return (FindResult::Error, None),
                },
            },
        };

        let want_weight = if bold { BOLD } else { alias_weight.unwrap_or(REGULAR) };

        // Prefer matching slant, then nearest weight; ties go to the heavier face when bold.
        let best = family.faces.iter().min_by_key(|f| {
            let slant_penalty = if f.italic == italic { 0 } else { 10_000 };
            let dist = (f.weight as i32 - want_weight as i32).abs();
            let tie = if bold { -(f.weight as i32) } else { f.weight as i32 };
            (slant_penalty + dist, tie)
        });

        let Some(best) = best else { return (FindResult::Error, None) };

        if substituted {
            return (FindResult::Substitute, Some(best));
        }

        let missing_bold = bold && best.weight < BOLD_THRESHOLD;
        let missing_italic = italic && !best.italic;

        let result = match (missing_bold, missing_italic) {
            (false, false) => FindResult::Ok,
            (true, false) => FindResult::MissingBold,
            (false, true) => FindResult::MissingItalic,
            (true, true) => FindResult::MissingBoldItalic,
        };

        (result, Some(best))
    }

    /// Sorted, de-duplicated display names of all families (aliases excluded).
    pub fn family_names(&self) -> Vec<String> {
        self.families.values().map(|f| f.name.clone()).collect::<BTreeSet<_>>().into_iter().collect()
    }

    /// Loads the device's system font configuration from the standard locations.
    pub fn system() -> Self {
        let mut db = Self::new();
        let fonts_dir = Path::new("/system/fonts");

        for cfg in ["/system/etc/fonts.xml", "/system/etc/font_fallback.xml"] {
            if let Ok(xml) = fs::read_to_string(cfg) {
                let _ = db.load_fonts_xml(&xml, fonts_dir, false);
            }
        }

        // Fonts delivered by updatable APEX/module (Android 12+), not listed in fonts.xml.
        db.add_font_dir(Path::new("/data/fonts/files"));
        db
    }
}

fn face_family_name(face: &ttf_parser::Face) -> Option<String> {
    use ttf_parser::name_id;

    // Prefer the typographic family (groups Light/Medium/... under one name).
    for id in [name_id::TYPOGRAPHIC_FAMILY, name_id::FAMILY] {
        let found = face
            .names()
            .into_iter()
            .filter(|n| n.name_id == id && n.is_unicode())
            .find_map(|n| n.to_string());

        if found.is_some() {
            return found;
        }
    }

    None
}

fn family_name_from_file(path: &Path, index: u32) -> Option<String> {
    let data = fs::read(path).ok()?;
    let face = ttf_parser::Face::parse(&data, index).ok()?;
    face_family_name(&face)
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = r#"<?xml version="1.0" encoding="utf-8"?>
<familyset version="23">
    <family name="sans-serif">
        <font weight="100" style="normal">Roboto-Regular.ttf
            <axis tag="wdth" stylevalue="100" />
            <axis tag="wght" stylevalue="100" />
        </font>
        <font weight="400" style="normal">Roboto-Regular.ttf</font>
        <font weight="400" style="italic">Roboto-Italic.ttf</font>
        <font weight="700" style="normal">Roboto-Bold.ttf</font>
    </family>
    <family name="serif">
        <font weight="400" style="normal">NotoSerif-Regular.ttf</font>
    </family>
    <family-list name="monospace">
        <family>
            <font weight="400" style="normal">DroidSansMono.ttf</font>
        </family>
    </family-list>
    <family lang="und-Arab" variant="elegant">
        <font weight="400" style="normal" index="0">MissingNoNameFont.ttf</font>
    </family>
    <alias name="sans-serif-thin" to="sans-serif" weight="100" />
    <alias name="arial" to="sans-serif" />
    <alias name="helvetica" to="arial" />
    <alias name="courier new" to="monospace" />
</familyset>"#;

    fn db() -> FontDb {
        let mut db = FontDb::new();
        db.load_fonts_xml(SAMPLE, Path::new("/system/fonts"), true).unwrap();
        db
    }

    fn file(r: (FindResult, Option<&FontFace>)) -> (FindResult, String) {
        (r.0, r.1.unwrap().path.file_name().unwrap().to_string_lossy().into_owned())
    }

    #[test]
    fn exact_matches() {
        let db = db();
        assert_eq!(file(db.find("sans-serif", false, false)), (FindResult::Ok, "Roboto-Regular.ttf".into()));
        assert_eq!(file(db.find("Sans-Serif", true, false)), (FindResult::Ok, "Roboto-Bold.ttf".into()));
        assert_eq!(file(db.find("sans-serif", false, true)), (FindResult::Ok, "Roboto-Italic.ttf".into()));
    }

    #[test]
    fn regular_prefers_400_over_thin() {
        let db = db();
        let r = db.find("sans-serif", false, false);
        assert_eq!(r.1.unwrap().weight, 400);
    }

    #[test]
    fn aliases_resolve_and_chain() {
        let db = db();
        assert_eq!(db.find("Arial", false, false).0, FindResult::Ok);
        assert_eq!(file(db.find("Helvetica", true, false)).1, "Roboto-Bold.ttf");
        assert_eq!(file(db.find("Courier New", false, false)).1, "DroidSansMono.ttf");
        assert_eq!(db.find("sans-serif-thin", false, false).1.unwrap().weight, 100);
    }

    #[test]
    fn missing_styles_are_reported() {
        let db = db();
        assert_eq!(db.find("serif", true, false).0, FindResult::MissingBold);
        assert_eq!(db.find("serif", false, true).0, FindResult::MissingItalic);
        assert_eq!(db.find("serif", true, true).0, FindResult::MissingBoldItalic);
        // Bold italic in sans-serif: italic exists, bold italic doesn't.
        assert_eq!(db.find("sans-serif", true, true).0, FindResult::MissingBold);
    }

    #[test]
    fn unknown_family_substitutes_default() {
        let db = db();
        let r = db.find("Comic Sans MS", false, false);
        assert_eq!(file(r), (FindResult::Substitute, "Roboto-Regular.ttf".into()));
    }

    #[test]
    fn family_list_and_names() {
        // Unnamed fallback family can't be named (file missing) and is skipped.
        assert_eq!(db().family_names(), vec!["monospace", "sans-serif", "serif"]);
    }

    #[test]
    fn empty_db_errors() {
        assert_eq!(FontDb::new().find("x", false, false).0, FindResult::Error);
    }

    #[test]
    fn reads_real_font_files() {
        // Host smoke test: use whatever system fonts exist (macOS/Linux), if any.
        let mut db = FontDb::new();
        let n = ["/System/Library/Fonts", "/usr/share/fonts/truetype/dejavu"]
            .iter()
            .map(|d| db.add_font_dir(Path::new(d)))
            .sum::<usize>();

        if n > 0 {
            assert!(!db.family_names().is_empty());
            let name = db.family_names()[0].clone();
            assert!(db.find(&name, false, false).1.is_some());
        }
    }
}
