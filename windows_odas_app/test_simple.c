#include <stdio.h>
#include <windows.h>

int main() {
    printf("Simple test program\n");
    printf("Testing basic Windows functionality...\n");

    // Test basic Windows types
    DWORD test_dword = 123;
    HANDLE test_handle = NULL;

    printf("DWORD test: %lu\n", test_dword);
    printf("HANDLE test: %p\n", test_handle);

    printf("Test completed successfully!\n");
    return 0;
}