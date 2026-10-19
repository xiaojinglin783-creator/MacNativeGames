#pragma once
#include <TargetConditionals.h>
// 编译期开关 DM_NVN_M3=1：图形后端走老接口（普通命令队列 / 命令缓冲 / 渲染与计算与拷贝编码器，逐槽绑定缓冲，对参数块引用的资源逐个声明），
// 目标 macOS 15 / iOS 18。缺省 0 = Metal 4（macOS 26 / iOS 26）。两支共用同一份回放逻辑，分叉处都在 #if DM_NVN_M3 里
// Compile-time switch DM_NVN_M3=1: the graphics backend uses the older API (ordinary command queue / command buffers / render, compute and copy encoders, buffers bound per slot, each resource referenced by an argument block declared individually),
// target macOS 15 / iOS 18. Default 0 = Metal 4 (macOS 26 / iOS 26). Both branches share the same replay logic, and every divergence is inside #if DM_NVN_M3
#ifndef DM_NVN_M3
#define DM_NVN_M3 0
#endif
#if DM_NVN_M3
#define RENC id<MTLRenderCommandEncoder>
#define CENC id<MTLComputeCommandEncoder>
#define BENC id<MTLBlitCommandEncoder>
#define CBUF id<MTLCommandBuffer>
#define RPD MTLRenderPassDescriptor
#define FB_ON(o, cb) cb
#define M4_ONLY(...)
#define M3_PRESENT(cb, dr) [cb presentDrawable:dr]
#define FB_SEL addCompletedHandler
#define FB_ARG id<MTLCommandBuffer>
#else
#define RENC id<MTL4RenderCommandEncoder>
#define CENC id<MTL4ComputeCommandEncoder>
#define BENC id<MTL4ComputeCommandEncoder>
#define CBUF id<MTL4CommandBuffer>
#define RPD MTL4RenderPassDescriptor
#define FB_ON(o, cb) o
#define M4_ONLY(...) __VA_ARGS__
#define M3_PRESENT(cb, dr) [dr present]
#define FB_SEL addFeedbackHandler
#define FB_ARG id<MTL4CommitFeedback>
#endif

#if DM_NVN_M3
#define GPU_RESOURCE(r) (r)
#define ARG_TABLE TotkArgumentTable
#define ARG_DESC TotkLegacyArgumentDescriptor
@class TotkLegacyArguments;
typedef TotkLegacyArguments *TotkArgumentTable;
@interface TotkLegacyArgumentDescriptor : NSObject
@property NSUInteger maxBufferBindCount, maxTextureBindCount, maxSamplerStateBindCount;
@end
@interface TotkLegacyArguments : NSObject
- (void)setAddress:(uint64_t)address atIndex:(NSUInteger)index;
- (void)setTexture:(id<MTLTexture>)texture atIndex:(NSUInteger)index;
- (void)setSamplerState:(id<MTLSamplerState>)sampler atIndex:(NSUInteger)index;
- (void)unbindEncoder:(id)encoder;
- (void)bindCompute:(id<MTLComputeCommandEncoder>)encoder;
- (void)bindRender:(id<MTLRenderCommandEncoder>)encoder stages:(MTLRenderStages)stages;
@end
#else
#define GPU_RESOURCE(r) ((r).gpuResourceID)
#define ARG_TABLE id<MTL4ArgumentTable>
#define ARG_DESC MTL4ArgumentTableDescriptor
#endif

#if DM_NVN_M3
#define M4_BARRIER(...) do {} while (0)
#define STREAM_QUEUE g_q
#define QUEUE_WAIT(cb, ev, amount) [(id<MTLCommandBuffer>)(cb) encodeWaitForEvent:(ev) value:(amount)]
#define MFX_HEAP id
#else
#define M4_BARRIER(...) do { __VA_ARGS__; } while (0)
#define STREAM_QUEUE g_q4
#define QUEUE_WAIT(cb, ev, amount) [g_q4 waitForEvent:(ev) value:(amount)]
#define MFX_HEAP id<MTL4CounterHeap>
#endif
