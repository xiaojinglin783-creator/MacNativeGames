/* Launcher defaults only. The renderer's virtual clock stays at its original
   rate, avoiding interval=2 becoming 30 FPS when the render ceiling is 60. */
#pragma once
#include <stdlib.h>
#include <string.h>

static inline int totk_power_defaults(int metal3) {
    const char *mode = getenv("TOTK_POWER_MODE");
    /* Keep the previously working launch policy unless explicitly requested.
       Disabling keepalive has not passed real-game stability validation. */
    int balanced = mode && !strcmp(mode, "balanced");
    if (!balanced) return 0;
    setenv("TOTK_MAX_FPS", "60", 0);
    setenv("TOTK_GPU_KEEPALIVE", "0", 0);
    if (metal3) {
        setenv("TOTK_ARG_EPOCH", "1", 0);
        setenv("TOTK_M3_RESOURCE_CACHE", "1", 0);
    }
    return 1;
}
