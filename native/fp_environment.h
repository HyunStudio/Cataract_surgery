// Verified boundary for the pinned GNU/Clang x86-64 numerical toolchain.
// The host owns its controls: every nested call restores them exactly.
#pragma once
#include <cstdint>
#include <limits>
#include <xmmintrin.h>
#if !defined(__x86_64__) || !defined(__GNUC__)
#error The verified numerical boundary requires GNU-compatible x86-64 assembly.
#endif
static_assert(std::numeric_limits<long double>::digits==64,"Interval arithmetic requires the verified 80-bit long-double format");

namespace membrane::numeric {
class Scope final {
    std::uint16_t x87_;
    std::uint32_t sse_;
public:
    // Keep explicit compiler barriers at a non-inlined entry/exit. Numerical
    // APIs construct this before reading their input arrays or doing arithmetic.
    __attribute__((noinline)) Scope() noexcept {
        __asm__ __volatile__("fnstcw %0" : "=m"(x87_) : : "memory");
        sse_=_mm_getcsr();
        const std::uint16_t target=static_cast<std::uint16_t>((x87_&~0x0f00u)|0x0300u);
        if(target!=x87_) __asm__ __volatile__("fldcw %0" : : "m"(target) : "memory");
        const std::uint32_t scalar=sse_&~0xe040u; // RN, gradual underflow, DAZ off
        if(scalar!=sse_) _mm_setcsr(scalar);
        __asm__ __volatile__("" : : : "memory");
    }
    __attribute__((noinline)) ~Scope() noexcept {
        __asm__ __volatile__("" : : : "memory");
        if(_mm_getcsr()!=sse_) _mm_setcsr(sse_);
        std::uint16_t current;
        __asm__ __volatile__("fnstcw %0" : "=m"(current) : : "memory");
        if(current!=x87_) __asm__ __volatile__("fldcw %0" : : "m"(x87_) : "memory");
    }
    Scope(const Scope&)=delete;
    Scope& operator=(const Scope&)=delete;
};
} // namespace membrane::numeric
