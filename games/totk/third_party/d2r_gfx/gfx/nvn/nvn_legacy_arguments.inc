/* Host-kernel argument bindings. Guest shader argument blocks use m3_rbuf and
   encode_args' per-resource useResource declarations, as in d2r-mobile. */
#if DM_NVN_M3
static NSHashTable<TotkLegacyArguments *> *g_legacy_tables;
@implementation TotkLegacyArgumentDescriptor @end
@implementation TotkLegacyArguments {
    id<MTLBuffer> _buffers[31]; NSUInteger _offsets[31];
    id<MTLTexture> _textures[128]; id<MTLSamplerState> _samplers[16];
    __weak id<MTLComputeCommandEncoder> _compute;
    __weak id<MTLRenderCommandEncoder> _render;
    MTLRenderStages _stages;
}
- (void)setAddress:(uint64_t)address atIndex:(NSUInteger)i {
    if (i >= 31) MDIE("Metal 3 buffer slot out of range");
    NSUInteger off = 0; id<MTLBuffer> b = m3_buf(address, &off);
    if (address && !b) MDIE("Metal 3 unregistered buffer address %#llx", (unsigned long long)address);
    _buffers[i] = b; _offsets[i] = off;
    [_compute setBuffer:b offset:off atIndex:i];
    if (_stages & MTLRenderStageVertex) [_render setVertexBuffer:b offset:off atIndex:i];
    if (_stages & MTLRenderStageFragment) [_render setFragmentBuffer:b offset:off atIndex:i];
}
- (void)setTexture:(id<MTLTexture>)t atIndex:(NSUInteger)i {
    if (i >= 128) MDIE("Metal 3 texture slot out of range");
    _textures[i] = t; [_compute setTexture:t atIndex:i];
    if (_stages & MTLRenderStageVertex) [_render setVertexTexture:t atIndex:i];
    if (_stages & MTLRenderStageFragment) [_render setFragmentTexture:t atIndex:i];
}
- (void)setSamplerState:(id<MTLSamplerState>)sampler atIndex:(NSUInteger)i {
    if (i >= 16) MDIE("Metal 3 sampler slot out of range");
    _samplers[i] = sampler; [_compute setSamplerState:sampler atIndex:i];
    if (_stages & MTLRenderStageVertex) [_render setVertexSamplerState:sampler atIndex:i];
    if (_stages & MTLRenderStageFragment) [_render setFragmentSamplerState:sampler atIndex:i];
}
- (void)unbindEncoder:(id)encoder { if (_compute == encoder) _compute = nil; if (_render == encoder) { _render = nil; _stages = 0; } }
- (void)bindCompute:(id<MTLComputeCommandEncoder>)encoder {
    _render = nil; _stages = 0; _compute = encoder;
    for (NSUInteger i = 0; i < 31; i++) if (_buffers[i]) [encoder setBuffer:_buffers[i] offset:_offsets[i] atIndex:i];
    for (NSUInteger i = 0; i < 128; i++) if (_textures[i]) [encoder setTexture:_textures[i] atIndex:i];
    for (NSUInteger i = 0; i < 16; i++) if (_samplers[i]) [encoder setSamplerState:_samplers[i] atIndex:i];
}
- (void)bindRender:(id<MTLRenderCommandEncoder>)encoder stages:(MTLRenderStages)stages {
    _compute = nil; _render = encoder; _stages = stages;
    for (NSUInteger i = 0; i < 31; i++) if (_buffers[i]) {
        if (stages & MTLRenderStageVertex) [encoder setVertexBuffer:_buffers[i] offset:_offsets[i] atIndex:i];
        if (stages & MTLRenderStageFragment) [encoder setFragmentBuffer:_buffers[i] offset:_offsets[i] atIndex:i];
    }
    for (NSUInteger i = 0; i < 128; i++) if (_textures[i]) {
        if (stages & MTLRenderStageVertex) [encoder setVertexTexture:_textures[i] atIndex:i];
        if (stages & MTLRenderStageFragment) [encoder setFragmentTexture:_textures[i] atIndex:i];
    }
    for (NSUInteger i = 0; i < 16; i++) if (_samplers[i]) {
        if (stages & MTLRenderStageVertex) [encoder setVertexSamplerState:_samplers[i] atIndex:i];
        if (stages & MTLRenderStageFragment) [encoder setFragmentSamplerState:_samplers[i] atIndex:i];
    }
}
@end
static ARG_TABLE arg_table_new(id<MTLDevice> dev, ARG_DESC *d, NSError **error) {
    (void)dev; (void)d; (void)error;
    TotkLegacyArguments *table = [TotkLegacyArguments new];
    @synchronized([TotkLegacyArguments class]) { if (!g_legacy_tables) g_legacy_tables = [NSHashTable weakObjectsHashTable]; [g_legacy_tables addObject:table]; }
    return table;
}
static void legacy_tables_end(id encoder) { if (!encoder) return; @synchronized([TotkLegacyArguments class]) { for (TotkLegacyArguments *table in g_legacy_tables) [table unbindEncoder:encoder]; } }
static void arg_table_compute(CENC encoder, ARG_TABLE table) { [table bindCompute:encoder]; }
static void arg_table_render(RENC encoder, ARG_TABLE table, MTLRenderStages stages) { [table bindRender:encoder stages:stages]; }
#else
static ARG_TABLE arg_table_new(id<MTLDevice> dev, ARG_DESC *d, NSError **error) { return [dev newArgumentTableWithDescriptor:d error:error]; }
static void arg_table_compute(CENC encoder, ARG_TABLE table) { [encoder setArgumentTable:table]; }
static void arg_table_render(RENC encoder, ARG_TABLE table, MTLRenderStages stages) { [encoder setArgumentTable:table atStages:stages]; }
#endif
