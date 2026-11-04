// Isolated calling-thread diagnostics only. Never linked into the application.
#include <xmmintrin.h>
extern "C" __declspec(dllexport) unsigned int fem_probe_x87() {
    unsigned short control=0;asm volatile("fnstcw %0" : "=m"(control));return control;
}
extern "C" __declspec(dllexport) unsigned int fem_probe_mxcsr() {return _mm_getcsr();}
extern "C" __declspec(dllexport) void fem_probe_set_x87(unsigned int value) {
    const unsigned short control=static_cast<unsigned short>(value);asm volatile("fldcw %0" : : "m"(control));
}
extern "C" __declspec(dllexport) void fem_probe_set_mxcsr(unsigned int value) {_mm_setcsr(value);}
