/* Optional render ceiling, independent of the guest's virtual present tick rate. */
#pragma once
#include <stdint.h>
#include <stdlib.h>

static inline int nvn_frame_limit_parse(const char *text) {
    if (!text || !*text) return 0;
    char *end;
    long value = strtol(text, &end, 10);
    return *end == '\0' && value >= 30 && value <= 120 ? (int)value : 0;
}
static inline uint64_t nvn_frame_limit_period(uint64_t period, int fps,
                                             int uncapped, int deterministic) {
    // Keep profiling/no-pacing, deterministic clocks, vsync and interpolation
    // semantics. A slower guest interval must remain slower (never force 30 -> 60).
    if (!period || !uncapped || deterministic || fps < 30 || fps > 120) return period;
    uint64_t floor = (UINT64_C(1000000000) + (unsigned)fps - 1) / (unsigned)fps;
    return period < floor ? floor : period;
}
