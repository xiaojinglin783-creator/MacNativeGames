/* Production translation queue, synthetic requests/service, no game or keys. */
#import <Foundation/Foundation.h>
#include <assert.h>
#include <stdatomic.h>
#include <unistd.h>
#include "totk_shader_rt.h"
/* The standalone executable has no boot-screen frontend. Resolve its optional
   progress hooks explicitly; weak_import alone does not satisfy this linker. */
void runtime_boot_status(const char *stage, const char *detail) { (void)stage; (void)detail; }
void runtime_boot_count(const char *stage, uint64_t done, uint64_t total) { (void)stage; (void)done; (void)total; }
int totk_depth_near_minus_w(void) { return 0; }
uint64_t dm_nvn_frame_count(void) { return 1; }
static dispatch_semaphore_t entered, release_hook;
static _Atomic unsigned hooks;
static void ready(NSString *variant, int stage) {
    assert(stage == 0);
    NSString *source = [totk_rt_dir() stringByAppendingFormat:@"/%@_b.metal", variant];
    assert([NSFileManager.defaultManager fileExistsAtPath:source]);
    if (atomic_fetch_add(&hooks, 1) == 0) {
        dispatch_semaphore_signal(entered);
        assert(dispatch_semaphore_wait(release_hook, dispatch_time(DISPATCH_TIME_NOW, 5*NSEC_PER_SEC)) == 0);
    }
}
static void await_generation(uint64_t generation) {
    for (int i = 0; i < 5000 && totk_rt_ready_gen() < generation; i++) usleep(1000);
    assert(totk_rt_ready_gen() >= generation);
}
int main(void) { @autoreleasepool {
    assert(totk_rt_can_translate());
    entered = dispatch_semaphore_create(0); release_hook = dispatch_semaphore_create(0);
    totk_rt_set_ready_hook(ready);
    uint8_t control[0x880] = {0}, code[0x80] = {0};
    uint32_t start = 0x50, length = sizeof code;
    memcpy(control+0x700, &start, 4); memcpy(control+0x704, &length, 4);
    NSDictionary *answers = @{@"tex":@{}, @"img":@{}, @"attr":@{}, @"fout":@{}};
    NSString *a = [NSString stringWithFormat:@"%064d", 1];
    assert(totk_rt_variant(a,0,control,code,answers,nil,1) == nil);
    assert(dispatch_semaphore_wait(entered,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC)) == 0);
    // A job is not published before its ready hook finishes; repeated requests
    // must not launch another service or block the submission thread.
    assert(totk_rt_ready_gen() == 0);
    assert(totk_rt_variant(a,0,control,code,answers,nil,1) == nil);
    dispatch_semaphore_signal(release_hook); await_generation(1);
    NSString *cached = totk_rt_variant(a,0,control,code,answers,nil,0);
    assert(cached && totk_rt_known_variants(a).count == 1 && atomic_load(&hooks) == 1);
    NSString *b = [NSString stringWithFormat:@"%064d", 2];
    assert(totk_rt_variant(b,0,control,code,answers,nil,2) == nil);
    await_generation(2);
    assert(totk_rt_variant(b,0,control,code,answers,nil,0));
    // Several services must run without inheriting one another's pipe ends or
    // blocked SIGCHLD. A synchronous caller waits for/adopts a queued job.
    for (int i = 3; i < 11; i++) {
        NSString *key = [NSString stringWithFormat:@"%064d", i];
        assert(totk_rt_variant(key,0,control,code,answers,nil,i&1?1:2) == nil);
    }
    for (int i = 3; i < 11; i++) {
        NSString *key = [NSString stringWithFormat:@"%064d", i];
        assert(totk_rt_variant(key,0,control,code,answers,nil,0));
        assert(totk_rt_known_variants(key).count == 1);
    }
    // The same shader with different bound texture types must resolve to a
    // distinct variant, without replacing the earlier answers' cached variant.
    NSDictionary *cube = @{@"tex":@{@"0":@"cube"}, @"img":@{}, @"attr":@{}, @"fout":@{}};
    assert(totk_rt_variant(a,0,control,code,cube,nil,1) == nil);
    NSString *other = totk_rt_variant(a,0,control,code,cube,nil,0);
    assert(other && ![other isEqualToString:cached]);
    assert([totk_rt_variant(a,0,control,code,answers,nil,0) isEqualToString:cached]);
    assert(totk_rt_known_variants(a).count == 2);
    uint64_t fresh; totk_rt_counts(&fresh,NULL,NULL);
    assert(fresh == 11);
    puts("PASS: production async shader queues, publication, deduplication, urgent jobs and synchronous adoption");
} }
