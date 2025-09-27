// WASAPI IID definitions for MinGW cross-compilation
// These are required when cross-compiling with MinGW as the standard
// Windows SDK libraries may not provide these symbols at link time

#ifdef _WIN32

// Force the GUIDs to be instantiated in this compilation unit
// This ensures they're available at link time
#define INITGUID

#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <functiondiscoverykeys_devpkey.h>

// The GUIDs are now defined in the headers with INITGUID set,
// which will cause them to be instantiated as actual symbols
// that can be linked against

#endif // _WIN32