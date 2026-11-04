// Isolated calling-thread diagnostics only. Never linked into the application.
#include <xmmintrin.h>
#include "../contact_guard.h"
extern "C" __declspec(dllexport) unsigned int fem_probe_x87() {
    unsigned short control=0;asm volatile("fnstcw %0" : "=m"(control));return control;
}
extern "C" __declspec(dllexport) unsigned int fem_probe_mxcsr() {return _mm_getcsr();}
extern "C" __declspec(dllexport) void fem_probe_set_x87(unsigned int value) {
    const unsigned short control=static_cast<unsigned short>(value);asm volatile("fldcw %0" : : "m"(control));
}
extern "C" __declspec(dllexport) void fem_probe_set_mxcsr(unsigned int value) {_mm_setcsr(value);}
extern "C" __declspec(dllexport) int fem_probe_raw_interval(double a,double b) {
    const auto sum=membrane::guard::Bound(static_cast<long double>(a))+membrane::guard::Bound(static_cast<long double>(b));
    const __float128 exact=static_cast<__float128>(a)+static_cast<__float128>(b);
    return static_cast<__float128>(sum.lo)<=exact && exact<=static_cast<__float128>(sum.hi);
}

extern "C" __declspec(dllexport) int fem_probe_boundary(int mode,double a,double b) {
    int inside=0;
    try {
        membrane::numeric::Scope environment;
        inside=(fem_probe_x87()&0xf00)==0x300 && (fem_probe_mxcsr()&0xe040)==0;
        if(mode==1) throw 1;
        if(mode==2) return inside;
        if(mode==3) {
            const unsigned int inner_cw=(fem_probe_x87()&~0xf00u)|0x600u;
            const unsigned int inner_mx=fem_probe_mxcsr()|0xc040u;
            fem_probe_set_x87(inner_cw);fem_probe_set_mxcsr(inner_mx);
            {membrane::numeric::Scope nested;inside=inside && (fem_probe_x87()&0xf00)==0x300 && (fem_probe_mxcsr()&0xe040)==0;}
            return inside && fem_probe_x87()==inner_cw && fem_probe_mxcsr()==inner_mx;
        }
        const auto sum=membrane::guard::Bound(static_cast<long double>(a))+membrane::guard::Bound(static_cast<long double>(b));
        const __float128 exact=static_cast<__float128>(a)+static_cast<__float128>(b);
        return inside && static_cast<__float128>(sum.lo)<=exact && exact<=static_cast<__float128>(sum.hi);
    } catch(...) {return inside;}
}
