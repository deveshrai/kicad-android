// libkrtrunner.so: runs a Python program for RouterService, in the ":router" process only.
// Links libpython3.14.so (python.org's Android build), so loading it brings Python into that
// process and never into KiCad's.

#include <Python.h>

#include <fcntl.h>
#include <stdio.h>
#include <jni.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static char* dupString( JNIEnv* env, jstring s )
{
    const char* utf = ( *env )->GetStringUTFChars( env, s, NULL );
    char*       copy = strdup( utf );
    ( *env )->ReleaseStringUTFChars( env, s, utf );
    return copy;
}


JNIEXPORT jint JNICALL Java_io_github_deveshrai_kicadandroid_RouterService_runPython(
        JNIEnv* env, jclass cls, jobjectArray jargv, jobjectArray jenv, jstring jlog )
{
    (void) cls;

    // Environment first: PYTHONHOME, PYTHONPATH, HOME and so on, as "NAME=value".
    jsize nenv = jenv ? ( *env )->GetArrayLength( env, jenv ) : 0;

    for( jsize i = 0; i < nenv; i++ )
    {
        char* kv = dupString( env, (jstring) ( *env )->GetObjectArrayElement( env, jenv, i ) );
        char* eq = strchr( kv, '=' );

        if( eq )
        {
            *eq = 0;
            setenv( kv, eq + 1, 1 );
        }

        free( kv );
    }

    // The step's working directory (the tools write side files such as redo_commands.sh there).
    const char* cwd = getenv( "KRT_CWD" );

    if( cwd && chdir( cwd ) != 0 )
        cwd = NULL;

    // stdout and stderr go to the step's log, which KiCad reads while the step runs.
    char* log = dupString( env, jlog );
    int   fd = open( log, O_WRONLY | O_CREAT | O_TRUNC, 0644 );
    free( log );

    if( fd >= 0 )
    {
        dup2( fd, 1 );
        dup2( fd, 2 );
        close( fd );
    }

    jsize  argc = ( *env )->GetArrayLength( env, jargv );
    char** argv = calloc( argc + 1, sizeof( char* ) );

    for( jsize i = 0; i < argc; i++ )
        argv[i] = dupString( env, (jstring) ( *env )->GetObjectArrayElement( env, jargv, i ) );

    // Like Py_BytesMain(), but with output to our log rather than Android's system log:
    // python.org's Android build sends stdout and stderr to logcat when sys.executable is empty
    // (Lib/_android_support.py, "embedded in an app"), so give it an executable name.
    PyConfig config;
    PyConfig_InitPythonConfig( &config );

    PyStatus status = PyConfig_SetBytesString( &config, &config.executable, "python3" );

    if( !PyStatus_Exception( status ) )
        status = PyConfig_SetBytesArgv( &config, argc, argv );

    if( !PyStatus_Exception( status ) )
        status = Py_InitializeFromConfig( &config );

    PyConfig_Clear( &config );

    if( PyStatus_Exception( status ) )
    {
        fprintf( stderr, "Python failed to start: %s\n", status.err_msg ? status.err_msg : "" );
        return 1;
    }

    int code = Py_RunMain();

    fflush( stdout );
    fflush( stderr );
    return code;
}
