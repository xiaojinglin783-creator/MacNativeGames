#include <assert.h>
#include <stdio.h>
#include "nvn_frame_limit.h"
#include "nvn_pace.h"
#include "power_policy.h"

static void reset(void) {
    const char *names[] = {"TOTK_POWER_MODE", "TOTK_MAX_FPS", "TOTK_GPU_KEEPALIVE", "TOTK_ARG_EPOCH", "TOTK_M3_RESOURCE_CACHE"};
    for (unsigned i=0; i<sizeof names/sizeof names[0]; i++) unsetenv(names[i]);
}
/* Exercise the production pacer and two-image availability policy at a known
   CPU work duration. Measure elapsed virtual time rather than sleeping. */
static uint64_t simulate(uint64_t work, uint64_t period) {
    nvn_pacer p = {0}; uint64_t available[2] = {0}, now = 1;
    for (int frame=0; frame<600; frame++) {
        unsigned image = (unsigned)frame % 2;
        if (now < available[image]) now = available[image];
        now += work;
        uint64_t slot = now + nvn_pace(&p, now, period);
        available[image] = period ? slot + period : 0;
    }
    return now-1;
}
int main(void) {
    assert(nvn_frame_limit_parse(NULL)==0 && nvn_frame_limit_parse("")==0);
    assert(nvn_frame_limit_parse("60")==60 && nvn_frame_limit_parse("120")==120);
    assert(nvn_frame_limit_parse("0")==0 && nvn_frame_limit_parse("60junk")==0);
    assert(nvn_frame_limit_parse("-30")==0 && nvn_frame_limit_parse("121")==0);
    assert(nvn_frame_limit_parse("99999999999999999999999999")==0);
    for (int ticks=1; ticks<=4; ticks++) {
        uint64_t original = (uint64_t)ticks*1000000000ull/120;
        uint64_t limited = nvn_frame_limit_period(original,60,1,0);
        assert(limited == (original<16666667ull?16666667ull:original));
        assert(nvn_frame_limit_period(original,60,0,0)==original);
        assert(nvn_frame_limit_period(original,60,1,1)==original);
        assert(nvn_frame_limit_period(original,0,1,0)==original);
    }
    assert(nvn_frame_limit_period(0,60,1,0)==0);
    // Fast scenes average at most 60 FPS, including when the guest says one
    // 120 Hz tick; interval 2 stays around 60, interval 4 stays around 30.
    for (int ticks=1; ticks<=2; ticks++) {
        uint64_t limited=nvn_frame_limit_period((uint64_t)ticks*1000000000ull/120,60,1,0);
        uint64_t elapsed=simulate(1000000,limited);
        assert(elapsed>=598ull*16666667 && elapsed<=600ull*16666667);
        assert(simulate(20000000,limited)==600ull*20000000); // no extra slowdown when already below 60
    }
    uint64_t slow=simulate(1000000,nvn_frame_limit_period(1000000000ull/30,60,1,0));
    assert(slow>=598ull*(1000000000ull/30));
    reset(); assert(!totk_power_defaults(0)); assert(!getenv("TOTK_MAX_FPS"));
    reset(); assert(!totk_power_defaults(1));
    assert(!getenv("TOTK_MAX_FPS") && !getenv("TOTK_GPU_KEEPALIVE"));
    assert(!getenv("TOTK_ARG_EPOCH") && !getenv("TOTK_M3_RESOURCE_CACHE"));
    reset(); setenv("TOTK_POWER_MODE","balanced",1); assert(totk_power_defaults(1));
    assert(!strcmp(getenv("TOTK_MAX_FPS"),"60"));
    assert(!strcmp(getenv("TOTK_GPU_KEEPALIVE"),"0"));
    assert(!strcmp(getenv("TOTK_ARG_EPOCH"),"1"));
    reset(); setenv("TOTK_POWER_MODE","balanced",1);
    setenv("TOTK_MAX_FPS","90",1); setenv("TOTK_GPU_KEEPALIVE","1",1);
    setenv("TOTK_ARG_EPOCH","0",1); assert(totk_power_defaults(1));
    assert(!strcmp(getenv("TOTK_MAX_FPS"),"90"));
    assert(!strcmp(getenv("TOTK_GPU_KEEPALIVE"),"1"));
    assert(!strcmp(getenv("TOTK_ARG_EPOCH"),"0"));
    reset(); setenv("TOTK_POWER_MODE","performance",1);
    assert(!totk_power_defaults(1) && !getenv("TOTK_MAX_FPS") && !getenv("TOTK_GPU_KEEPALIVE"));
    reset(); setenv("TOTK_POWER_MODE","balanced",1);
    assert(totk_power_defaults(0) && !getenv("TOTK_ARG_EPOCH"));
    puts("PASS: 60 FPS render ceiling, swapchain pacing, legacy clocks and launcher defaults");
}
