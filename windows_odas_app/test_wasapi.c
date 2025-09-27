#include <stdio.h>
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>

int main() {
    printf("WASAPI header test program\n");

    // Test if we can use the GUID values directly
    printf("Testing GUID usage...\n");

    // Use the actual GUID values instead of referencing symbols
    const IID test_iid = {0x1cb9ad4c, 0xdbfa, 0x4c32, {0xb1,0x78,0xc2,0xf5,0x68,0xa7,0x03,0xb2}};
    const CLSID test_clsid = {0xbcde0395, 0xe52f, 0x467c, {0x8e,0x3d,0xc4,0x57,0x92,0x91,0x69,0x2e}};

    printf("GUID test completed!\n");
    printf("IID test: Data1=%08X\n", test_iid.Data1);
    printf("CLSID test: Data1=%08X\n", test_clsid.Data1);

    printf("WASAPI test completed successfully!\n");
    return 0;
}