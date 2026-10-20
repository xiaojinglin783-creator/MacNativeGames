#ifndef NVN_GPU_LOOKUP_H
#define NVN_GPU_LOOKUP_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
/* Records start with a uint64_t GPU base and are sorted ascending. Return the
   first record whose base is greater than address (count if none). Reading via
   memcpy avoids aliasing/alignment assumptions about the caller's record type. */
static inline size_t nvn_gpu_upper_bound(const void *records, size_t count,
                                         size_t stride, uint64_t address) {
    size_t lo = 0, hi = count;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        uint64_t base;
        memcpy(&base, (const unsigned char *)records + mid * stride, sizeof base);
        if (base <= address) lo = mid + 1; else hi = mid;
    }
    return lo;
}
#endif
