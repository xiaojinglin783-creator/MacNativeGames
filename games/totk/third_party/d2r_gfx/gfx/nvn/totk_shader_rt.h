// TOTK runtime shader translation (totk_shader_rt.m).
#pragma once
#ifdef __OBJC__
#import <Foundation/Foundation.h>
#include <stdint.h>
NSString *totk_rt_dir(void);
// Returns the variant name whose <dir>/<variant>_b.{metal,json} match the answers, translating when needed.
// stage: NVN shader stage (0 vertex, 1 fragment, 5 compute). answers: {"tex","img","attr","fout"} dictionaries.
NSArray<NSString *> *totk_rt_known_variants(NSString *shader);
// nil on iOS when the variant is not translated yet (request recorded). may_defer (Mac, async shaders): instead of
// translating now, queue the translation in the background and return nil; once it is recorded, totk_rt_ready_gen()
// moves. Without may_defer a running background job of the same shader is waited for.
// may_defer 2: urgent, a draw further on cannot go without it: run now on the urgent services (a queued job of the shader too).
NSString *totk_rt_variant(NSString *shader, int stage, const uint8_t *control, const uint8_t *code, NSDictionary *answers, NSArray *local, int may_defer);
void totk_rt_urgent_stats(uint64_t *n, uint64_t *ns);   // urgent jobs done and their time from queued to recorded
// Called on the background worker after a translation, before the variant is recorded: compile its Metal library there.
void totk_rt_set_ready_hook(void (*hook)(NSString *variant, int stage));
#endif
#include <stdint.h>
/* Variants new to the translation cache this run, the variants in the cache (-1 until counted in the background) and
   the CLOCK_UPTIME_RAW time of the last new one (0: none yet). Any pointer may be NULL. */
void totk_rt_counts(uint64_t *fresh, int64_t *total, uint64_t *last_new_ns);
uint64_t totk_rt_ready_gen(void);   // moves each time a background translation has been recorded
int totk_rt_can_translate(void);   // 0 on iOS and with TOTK_SHADER_NO_TRANSLATE=1
