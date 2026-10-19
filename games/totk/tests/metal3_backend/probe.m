/* No game inputs. Render -> compute -> compute readback through the production
   legacy argument adapter, including rebinding after an encoder has ended. */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdio.h>
#include <stdlib.h>
#include "nvn_backend.h"
#if !DM_NVN_M3
#error This probe tests the Metal 3 backend; build with DM_NVN_M3=1.
#endif
#define MDIE(...) do { fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); exit(1); } while (0)
static NSMutableArray<id<MTLBuffer>> *buffers;
static id<MTLBuffer> m3_buf(uint64_t address, NSUInteger *off) {
    *off = 0;
    for (id<MTLBuffer> b in buffers) if (address >= b.gpuAddress && address - b.gpuAddress < b.length) { *off = address - b.gpuAddress; return b; }
    return nil;
}
#include "nvn_legacy_arguments.inc"
static id<MTLBuffer> buffer(id<MTLDevice> dev, const void *bytes, NSUInteger size) {
    id<MTLBuffer> b = [dev newBufferWithBytes:bytes length:size options:MTLResourceStorageModeShared];
    if (!b) MDIE("buffer allocation failed"); [buffers addObject:b]; return b;
}
int main(void) { @autoreleasepool {
    id<MTLDevice> dev = MTLCreateSystemDefaultDevice(); if (!dev) MDIE("no Metal device; GPU test did not execute");
    buffers = [NSMutableArray array];
    NSError *error = nil;
    NSString *source = @"#include <metal_stdlib>\nusing namespace metal;\n"
        "vertex float4 vs(uint i [[vertex_id]]) { float2 p[3]={float2(-1,-1),float2(3,-1),float2(-1,3)}; return float4(p[i],0,1); }\n"
        "fragment uint fs(constant uint &n [[buffer(0)]]) { return n; }\n"
        "kernel void cs(constant uint2 &n [[buffer(0)]], device uint *out [[buffer(1)]], texture2d<uint> t [[texture(0)]]) { out[n.y]=t.read(uint2(0)).x+n.x; }\n";
    id<MTLLibrary> lib = [dev newLibraryWithSource:source options:nil error:&error]; if (!lib) MDIE("MSL: %s", error.description.UTF8String);
    MTLRenderPipelineDescriptor *pd = [MTLRenderPipelineDescriptor new]; pd.vertexFunction = [lib newFunctionWithName:@"vs"]; pd.fragmentFunction = [lib newFunctionWithName:@"fs"]; pd.colorAttachments[0].pixelFormat = MTLPixelFormatR32Uint;
    id<MTLRenderPipelineState> rps = [dev newRenderPipelineStateWithDescriptor:pd error:&error];
    id<MTLComputePipelineState> cps = [dev newComputePipelineStateWithFunction:[lib newFunctionWithName:@"cs"] error:&error];
    if (!rps || !cps) MDIE("pipeline: %s", error.description.UTF8String);
    uint32_t color = 31, first[2] = {7,0}, second[2] = {9,1}, zeros[2] = {0,0};
    id<MTLBuffer> cb = buffer(dev,&color,sizeof color), a = buffer(dev,first,sizeof first), b = buffer(dev,second,sizeof second), out = buffer(dev,zeros,sizeof zeros);
    MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatR32Uint width:4 height:4 mipmapped:NO]; td.storageMode = MTLStorageModePrivate; td.usage = MTLTextureUsageShaderRead | MTLTextureUsageRenderTarget;
    id<MTLTexture> tex = [dev newTextureWithDescriptor:td]; if (!tex) MDIE("texture allocation failed");
    ARG_DESC *ad = [ARG_DESC new]; ARG_TABLE table = arg_table_new(dev, ad, &error);
    id<MTLCommandQueue> queue = [dev newCommandQueue]; id<MTLCommandBuffer> work = [queue commandBuffer];
    MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor new]; rp.colorAttachments[0].texture = tex; rp.colorAttachments[0].loadAction = MTLLoadActionClear; rp.colorAttachments[0].storeAction = MTLStoreActionStore;
    id<MTLRenderCommandEncoder> re = [work renderCommandEncoderWithDescriptor:rp];
    [table setAddress:cb.gpuAddress atIndex:0]; arg_table_render(re,table,MTLRenderStageFragment);
    [re setRenderPipelineState:rps]; [re drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3]; legacy_tables_end(re); [re endEncoding];
    for (int i=0;i<2;i++) {
        [table setAddress:(i?b:a).gpuAddress atIndex:0]; [table setAddress:out.gpuAddress atIndex:1]; [table setTexture:tex atIndex:0];
        id<MTLComputeCommandEncoder> ce = [work computeCommandEncoder]; arg_table_compute(ce,table); [ce setComputePipelineState:cps];
        [ce dispatchThreadgroups:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(1,1,1)]; legacy_tables_end(ce); [ce endEncoding];
    }
    [work commit]; [work waitUntilCompleted]; if (work.status != MTLCommandBufferStatusCompleted) MDIE("GPU: %s", work.error.description.UTF8String);
    const uint32_t *result = out.contents; if (result[0]!=38 || result[1]!=40) MDIE("readback: %u,%u; expected 38,40",result[0],result[1]);
    puts("PASS: Metal 3 render -> compute dependencies, buffer/texture bindings, ended-encoder rebinding (38,40)");
    return 0;
} }
