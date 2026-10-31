/*
 * libkimalloc: C++ operator new/delete backed by mimalloc, for the KiCad Android app.
 *
 * Why: Android's scudo allocator caps every small size class at a 256 MB region. Once a class
 * is full, scudo falls back to one mmap per allocation until the process hits the kernel's
 * map-count limit and aborts. KiCad holding the full symbol and footprint libraries needs more
 * than 256 MB in several classes, so the app aborts at about 3 GB no matter how much RAM the
 * device has. mimalloc has no per-class cap.
 *
 * How: the Qt loader loads this library first, before libc++_shared (see
 * scripts/build-kicad-apk.sh). It is linked with -z global, so every library loaded after it,
 * libc++_shared included (it calls operator new/delete through its PLT), binds to these
 * definitions. Pointers that did not come from mimalloc are passed on to free(), so a block
 * allocated before this library was loaded can still be released safely.
 *
 * This file must not depend on libc++: it is built with -nostdlib++ and loaded ahead of it.
 */

#include <cstddef>
#include <cstdlib>
#include <new>

#include <mimalloc.h>

namespace
{
[[noreturn]] void outOfMemory()
{
    // Without libc++ we cannot throw std::bad_alloc; KiCad does not recover from it anyway
    abort();
}

inline void* allocOrDie( std::size_t aSize )
{
    if( void* p = mi_malloc( aSize ) )
        return p;

    outOfMemory();
}

inline void* allocAlignedOrDie( std::size_t aSize, std::size_t aAlign )
{
    if( void* p = mi_malloc_aligned( aSize, aAlign ) )
        return p;

    outOfMemory();
}

inline void release( void* aPtr )
{
    if( !aPtr )
        return;

    if( mi_is_in_heap_region( aPtr ) )
        mi_free( aPtr );
    else
        free( aPtr );
}
} // namespace


#define KIMALLOC_EXPORT __attribute__( ( visibility( "default" ) ) )

KIMALLOC_EXPORT void* operator new( std::size_t n ) { return allocOrDie( n ); }
KIMALLOC_EXPORT void* operator new[]( std::size_t n ) { return allocOrDie( n ); }
KIMALLOC_EXPORT void* operator new( std::size_t n, const std::nothrow_t& ) noexcept { return mi_malloc( n ); }
KIMALLOC_EXPORT void* operator new[]( std::size_t n, const std::nothrow_t& ) noexcept { return mi_malloc( n ); }

KIMALLOC_EXPORT void* operator new( std::size_t n, std::align_val_t a )
{
    return allocAlignedOrDie( n, static_cast<std::size_t>( a ) );
}

KIMALLOC_EXPORT void* operator new[]( std::size_t n, std::align_val_t a )
{
    return allocAlignedOrDie( n, static_cast<std::size_t>( a ) );
}

KIMALLOC_EXPORT void* operator new( std::size_t n, std::align_val_t a, const std::nothrow_t& ) noexcept
{
    return mi_malloc_aligned( n, static_cast<std::size_t>( a ) );
}

KIMALLOC_EXPORT void* operator new[]( std::size_t n, std::align_val_t a, const std::nothrow_t& ) noexcept
{
    return mi_malloc_aligned( n, static_cast<std::size_t>( a ) );
}

KIMALLOC_EXPORT void operator delete( void* p ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete[]( void* p ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete( void* p, std::size_t ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete[]( void* p, std::size_t ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete( void* p, const std::nothrow_t& ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete[]( void* p, const std::nothrow_t& ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete( void* p, std::align_val_t ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete[]( void* p, std::align_val_t ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete( void* p, std::size_t, std::align_val_t ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete[]( void* p, std::size_t, std::align_val_t ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete( void* p, std::align_val_t, const std::nothrow_t& ) noexcept { release( p ); }
KIMALLOC_EXPORT void operator delete[]( void* p, std::align_val_t, const std::nothrow_t& ) noexcept { release( p ); }
