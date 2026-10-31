/*
 * C ABI of the kiandroid Rust platform library (platform/kiandroid/src/lib.rs).
 * Keep in sync by hand; the surface is intentionally small.
 */

#ifndef KIANDROID_H
#define KIANDROID_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Fonts: replacement for the fontconfig subset used by KiCad ---- */

/** Values match fontconfig::FONTCONFIG::FF_RESULT. */
typedef enum
{
    KIA_FONT_OK = 0,
    KIA_FONT_ERROR = 1,
    KIA_FONT_SUBSTITUTE = 2,
    KIA_FONT_MISSING_BOLD = 3,
    KIA_FONT_MISSING_ITALIC = 4,
    KIA_FONT_MISSING_BOLD_ITALIC = 5
} KIA_FONT_RESULT;

typedef struct KiaFontDb KiaFontDb;

/** Loads /system/etc/fonts.xml (+ font_fallback.xml) and updatable system fonts. */
KiaFontDb* kia_fontdb_new_system( void );

/** Loads an explicit fonts.xml; font file names resolve against @p fonts_dir. */
KiaFontDb* kia_fontdb_new( const char* fonts_xml_path, const char* fonts_dir );

void kia_fontdb_free( KiaFontDb* db );

/** Adds a TTF/OTF/TTC file under the family names in its name table. Returns faces added. */
int kia_fontdb_add_file( KiaFontDb* db, const char* path );

/** Adds every font file in @p dir (non-recursive). Returns faces added. */
int kia_fontdb_add_dir( KiaFontDb* db, const char* dir );

/**
 * Finds the face for a family name (aliases such as "Arial" resolve to system families).
 * On success writes a NUL-terminated path to @p out_path and the face index to @p out_index.
 * @return a KIA_FONT_RESULT; KIA_FONT_ERROR if nothing found or the buffer is too small.
 */
int kia_fontdb_find( const KiaFontDb* db, const char* name, bool bold, bool italic,
                     char* out_path, size_t out_path_len, int* out_index );

size_t kia_fontdb_family_count( const KiaFontDb* db );

/** Sorted family name; valid until the db is modified or freed. */
const char* kia_fontdb_family_name( const KiaFontDb* db, size_t i );

#ifdef __cplusplus
}
#endif

#endif // KIANDROID_H
