# macOS 15 / Metal 3 port — awaiting Mac validation

This is a source port, not a verified macOS 15 release. Current work was performed
on Linux x86_64. No Xcode compilation, GPU smoke test or game run has completed on
the target Apple M4 / 16 GB / macOS 15.7.3 machine yet. Passing Python tests and a
preprocessor audit do not establish native compilation or rendering correctness.

## Backend and source

The adapter originally came from d2r-mobile commit
`9f0c25768ac4b231c6f4cb0a9f182ded68d0e7cf`. The older-API port follows
[d2r-mobile's DM_NVN_M3 implementation](https://github.com/jhaizhou-ops/d2r-mobile/commit/d9e95c33812faaf58ddedf53772c8d0b43c9a685),
with the current upstream implementation at `1ceaa6b` consulted for fixes.
Its MIT notices remain in place. This port retains TOTK's replay, shader reflection,
texture storage, uniform snapshots, game patches and deferred resource retirement.

The build selects Metal 3 on macOS 15–25 and Metal 4 on macOS 26+. Selection is at
**build time**, not a runtime loader switching a single executable between APIs.
`--metal-backend 3` permits building the fallback on a newer Mac; `4` on macOS below
26 is rejected. Rebuild after upgrading the OS to get the default Metal 4 backend.
The original iOS 26 path still uses Metal 4.

Metal 3 uses a single ordinary command queue for game work, uploads and presentation,
ordinary render/compute/blit encoders, command-buffer completion handlers, indexed
buffer-object/offset draws, and per-resource `useResource` declarations for guest
argument blocks. Copy and compute work are split into separate encoders. Small host
kernels and presentation use an adapter that translates argument-table updates into
ordinary buffer/texture/sampler bindings. Ending an encoder detaches these tables,
so later setters do not send commands to an ended encoder.

Metal 3 disables this project's MetalFX interpolation and upscaling paths, including
runtime requests. The game keeps its original scaler; presentation uses the existing
bilinear shader. Key 3 cycles native 2K/off, and key 2 cannot enable interpolation.
The native canvas option retains its existing game-version requirements. Metal 4
retains its MetalFX implementation. Metal 4 render-stream and timestamp instrumentation
are not enabled in the Metal 3 path; cube-copy compute optimization uses its existing
blit fallback there.

## First compile check on the Mac — no game inputs needed

From the repository root:

```sh
bash games/totk/scripts/check_macos_backend.sh 3
```

This records OS, architecture, SDK and compiler, compiles the graphics translation
units and checks macOS frontend syntax. It then builds/runs a standalone GPU probe
with Metal validation enabled. The probe renders a value into an integer texture,
reads it with two compute encoders through the production legacy argument adapter,
and requires readback values `38,40`. It tests rebinding after an encoder ends as
well as buffer/texture binding and render-to-compute ordering. It does not read
an XCI/NSP, `prod.keys`, firmware, or saves. Failures preserve their exit status.

Return the complete `games/totk/build/check-metal3.log`, including the first compiler
error. Continue fixing compilation before treating this port as ready. On a macOS
26+ machine, also run `bash games/totk/scripts/check_macos_backend.sh 4` to validate
the original backend. Its API requires an SDK exposing Metal 4.

## Full app build command after the compile check

Install Apple's command line tools and the documented Homebrew packages if missing:

```sh
xcode-select --install
brew install opus libvpx python@3.14
python3.14 build_app.py /path/to/totk.xci -k /path/to/prod.keys \
  --metal-backend 3 --work /path/to/TOTK_build_metal3 \
  -o '/path/to/Tears of the Kingdom Metal3.app'
```

Replace paths with existing local inputs. A separate work/output path preserves an
existing work folder/app. For NSP, add the existing `--firmware` or `--shared-fonts`
option. For an update, add `--update /path/to/update.nsp` (or NSZ). Inputs are read;
this change does not move or modify game files, keys or saves. The existing save
location and bundle identifier remain unchanged. Runtime logs must still confirm
correct gameplay, image output, audio and save/reload behavior on the Mac.

The deployment minimum is 15.0 for the Metal 3 runtime, launcher, warm-cache helper,
SPIRV-Cross executable, offline shader libraries and app manifest. Metal 4 uses 26.0.
Graphics objects are stored in separate `build/gfx-metal3` / `gfx-metal4` trees;
a backend stamp also forces relinking. Shader/compiler stamps include the deployment
minimum, preventing reuse of an SDK-26-only metallib on macOS 15. Builds cap parallel
compilers at four for the 16 GB machine (the initial check uses two).
The bundled native shader translator's Mach-O `LC_BUILD_VERSION` minimum is macOS
12.0; its SDK field is 26.2, which is not its minimum OS requirement. Actual execution
of that translator on macOS 15 remains unverified here.

## Current validation

- Python suite: 88 tests, 77 passed, 11 skipped (10 Apple-only, one optional rsync).
- Both backend branches: all six graphics Objective-C translation units preprocess.
  The Metal 3 active source contains no Metal 4 types/queue/allocator APIs.
- ARM64 call-window suite: six tests passed during environment setup; unchanged by this port.
- Native compile script on Linux: correctly stops with exit 2 before native commands.
- Apple SDK compilation, native linking, GPU probe and full app/game: **not run**.

The preprocessor audit is available on either host:

```sh
python3 games/totk/scripts/check_metal_api.py --backend 3
python3 games/totk/scripts/check_metal_api.py --backend 4
python3.14 -m unittest discover -s tests -v
```

The audit deliberately omits unavailable system headers; it checks API isolation,
not Objective-C types or Apple API availability. Tests never use personal game data.

## Files changed

| Files | Change |
|---|---|
| `build_app.py` | OS/backend selection, CLI flag, helper and shader deployment targets, bounded compilation, app minimum |
| `games/totk/Makefile` | Per-backend object paths, flags/frameworks, relink stamp, compile and GPU-check targets |
| `games/totk/third_party/d2r_gfx/gfx/nvn/nvn_backend.h` | Shared backend types and API-isolation macros |
| `games/totk/third_party/d2r_gfx/gfx/nvn/nvn_legacy_arguments.inc` | Metal 3 host argument bindings and encoder detachment |
| `games/totk/third_party/d2r_gfx/gfx/nvn/nvn_mtl.m` | Queues, callbacks, resource declarations, uploads, copies, dispatches, presentation and diagnostics |
| `games/totk/third_party/d2r_gfx/gfx/nvn/nvn_rtex.inc` | Ordinary render encoder and argument binding path |
| `games/totk/third_party/d2r_gfx/gfx/nvn/nvn_cube_group.h` | Shared types and Metal 3 copy fallback |
| `games/totk/third_party/d2r_gfx/gfx/nvn/nvn_cube_group_probe.h`, `nvn_tex_slots_probe.h` | Backend-independent probe types |
| `games/totk/third_party/d2r_gfx/gfx/nvn/totk_mfx.h`, `totk_mfx.m`, `totk_mfx_up.h`, `totk_mfx_up.m` | Compile-time MetalFX isolation and disabled fallbacks |
| `games/totk/third_party/d2r_gfx/gfx/tex/nvn_deswizzle_gpu.h`, `nvn_deswizzle_gpu.m` | SDK-15-safe declarations; existing ordinary compute deswizzle |
| `games/totk/runtime/game_patches.c`, `game_patches_v143.c`, `frontend.m` | Metal 3 picture-mode cycle and shortcut text |
| `games/totk/scripts/check_metal_api.py`, `check_macos_backend.sh` | Reproducible API audit and Mac compile/GPU log collection |
| `games/totk/tests/metal3_backend/probe.m` | Real GPU host-binding smoke test, pending Mac execution |
| `tests/test_metal_backend.py` | Selection boundaries, Make flags/isolation, shader-cache retargeting and API audits |
| `README.md`, `docs/macos15-metal3.md` | Experimental status, commands, validation and limitations |

## First macOS 15 compiler feedback

The user ran the check with macOS 15.7.3, SDK 15.5 and Apple clang 17. The initial
attempt stopped with six errors: the compressed-texture conversion used a blit
protocol variable for compute commands, and sampler reduction API declarations
were absent from SDK 15. The conversion now uses separately typed blit/compute
variables, ending the compute encoder through the normal detachment helper.
Metal 3 uses the default weighted-average sampler without referencing the newer
reduction property. MIN/MAX reduction requests stop with an explicit error;
correct shader emulation for those requests is still outstanding if the game
uses them. No averaging approximation is silently substituted. Metal 4 retains
its native reduction modes. A fresh Mac compile/GPU result is still required.

## Verified base-game NPDM variant

A second supplied base-game metadata file has SHA-256
`890c6174a31605519d82361fd5e2e941d684601f6aec317caa67b7e1a60b0c5a`.
Its RSA-2048/PSS-SHA256 ACID signature verifies with retail key 0 from the pinned
hactool `pki.c` public verification moduli. Its META/ACI0 sections and permission
payload match the earlier supplied file; the 509 byte differences are confined
to the 512 byte signature/public-modulus area. The earlier supplied file
(`e78c4097...`) did not verify with the four retail/development public roots tested.
Neither comparison supplies the bytes of the repository's original `f5a5eecc...`
reference; that reference remains unchanged and supported.

The additional exact digest is supported only as `main.npdm` for base version
`v0`. When selected, `verify_npdm_signature.py` also checks title ID, section
bounds and the retail signature during every build, including cached extraction.
Other metadata digests remain rejected; program-module and game-data hash checks
are unchanged. No supplied game metadata or console/decryption key is committed.
The verifier's public modulus is a verification key, not a game-decryption key.

## Newer firmware fonts: authenticity check pending

The supplied 21.2.0 extraction matches four original font digests. Its simplified
Chinese fonts differ (`a04eb490...` and `f5784e7a...`). These digests have **not**
been added to the accepted fonts. To distinguish a supported firmware variant
from unverified replacements, extraction now offers `--verify-retail-signatures`.
This verifies each source font NCA's RSA-PSS-SHA256 header signature with pinned
hactool retail public roots, in addition to the existing FS-header and six-level
IVFC checks. The signed header binds the FS hash to the verified RomFS bytes.
The output manifest reports whether this stronger check completed. Existing
font allowlists and runtime integrity checks remain unchanged while awaiting
that local check. No font payload or console/decryption key is committed.

## Verified 21.2.0 font variants

The target Mac completed `--verify-retail-signatures` successfully for all five
source font NCAs. Retail signatures, FS header hashes, all six IVFC levels and
BFTTF headers verified, and the resulting six file digests match the previously
reported extraction. Four match the original font set. Two additional exact
variants are now supported:

| Type | File bytes (including BFTTF header) | SHA-256 |
|---|---:|---|
| chinese-simplified | 7848208 | `a04eb490283d8393b2c49c52e315132461d790ac73996cb43ac869ce72003938` |
| chinese-simplified-extension | 123920 | `f5784e7a553fef9a05b3b7dba94e77e79162ace9db8dafc715ace0be1fd9b9ff` |

The original font references remain unchanged. The variant must match its type,
exact digest and size. The generated manifest and runtime header record the
actual selected file's digest/size, so the existing runtime checksum protection
continues to apply. No font payload is included in the repository. This confirms
font input integrity; gameplay and glyph appearance still need target validation.

### Optional Metal 3 argument reuse experiment

`TOTK_ARG_EPOCH=1` now permits reuse of read-only shader argument blocks on
Metal 3 when all existing binding/resource/snapshot generations still match.
The block must also have been built on the exact same render encoder. Encoder
creation advances a monotonic generation, so a replacement encoder cannot skip
its indirect-resource `useResource` declarations, even within one logical pass.
Writable/image/indirect-pointer bindings and compute dispatches still rebuild.
Default behavior remains unchanged; Metal 4 retains its existing reuse policy.
`DM_NVN_AB_NOREUSE=1` also disables this experiment.

The production `probe-gpu-arg-epoch` readback test now replaces an encoder without
changing the logical pass or bindings, requires a rebuild, and checks the pixels.
After rebuilding, quit the game and run on the Mac:

```sh
cd "$HOME/TOTK_build_metal3/totk"
MTL_DEBUG_LAYER=1 MTL_DEBUG_LAYER_ERROR_MODE=assert TOTK_HEADLESS=1 \
  build/totk-native rewritten/v0 probe-gpu-arg-epoch
```

Only after the GPU probe passes, compare the same stationary gameplay scene:

```sh
TOTK_ARG_EPOCH=1 "$HOME/TOTK Metal3.app/Contents/MacOS/TOTK"
```

Normal Finder launch restores the default (experiment off). Check argument reuse
counts and frame-time percentiles, and inspect the image for rendering errors;
a speedup is not guaranteed. Linux validation: both API branch audits passed;
101 Python tests ran successfully (11 platform/tool-dependent skips). Native
compilation, GPU readback, and gameplay measurements for this change still need
the user's Mac. No game data, keys, fonts, or saves are modified by this change.

### Optional encoder-local Metal 3 resource declarations

`TOTK_M3_RESOURCE_CACHE=1` skips duplicate `useResource` declarations for the
same resource and usage within one render encoder. A bounded 256-slot cache
retains its entries only until encoder end. Collisions cause extra declarations,
never skipped declarations. Usage upgrades emit the union of prior/new usage;
compute encoders are unchanged. Default off; Metal 4 is unchanged. Diagnostics
report `[m3-resource-cache]` declaration and skip totals.

The argument epoch GPU probe additionally checks duplicate suppression, a
read-to-read/write upgrade, and redeclaration after replacing the encoder.
For the user's **1.4.3** build, the correct command (rather than the v0 example
above) is:

```sh
cd "$HOME/TOTK_build_metal3/totk"
MTL_DEBUG_LAYER=1 MTL_DEBUG_LAYER_ERROR_MODE=assert TOTK_HEADLESS=1 \
  TOTK_M3_RESOURCE_CACHE=1 \
  ./build/totk-native-v143 rewritten/v143 probe-gpu-arg-epoch
```

After a successful native probe, compare the same gameplay scene using:

```sh
TOTK_ARG_EPOCH=1 TOTK_M3_RESOURCE_CACHE=1 \
  "$HOME/TOTK Metal3.app/Contents/MacOS/TOTK"
```

No performance claim is made before the user's GPU/gameplay measurements.
Linux branch audits and the 101-test Python suite pass (11 skips); native
compilation and GPU readback remain to be run on macOS.

### Sampling-guided GPU address lookup

A 20-second user `sample` captured 435 leaf samples in `m3_buf`, including
212 beneath indexed drawing alone. This identifies a sustained CPU hotspot;
it does not identify the cause of every 100–300 ms gameplay stall. GUI-thread
and idle worker waits in the same sample are not evidence of deadlock.

The Metal 3 buffer registry is now sorted by GPU base. The last-hit fast path
remains, and a miss uses binary search before the prior range-scan fallback.
The fallback preserves overlapping interval support; range checks still use
subtraction to avoid end-address overflow. Registration/deletion preserve order,
all access retains the same lock, and buffer ownership is unchanged. Metal 4
does not compile this registry. No additional gameplay switch is required.

`nvn_gpu_lookup.h` provides the upper-bound search. A portable compiled C test
checks 20,000 insertion/deletion sequences against a linear reference, including
empty tables, duplicate bases, boundaries, and UINT64_MAX. The existing native
argument probe now also checks real Metal buffer offsets, removal, re-insertion,
and last-hit validity after sorted entries shift. Repeat that probe on the Mac
after rebuilding. Both API branch audits and the 102-test Python suite passed
(11 platform/tool-dependent skips); native validation/performance remain pending.

### 2026-10-22: scoped upstream stutter backport

This branch backports the following changes from `ly05010419/MacNativeGames`,
without merging unrelated game ports, changing the translation chain, or enabling
newer MetalFX features:

- `646ce29`: opt-in cached shader library prefetch (`TOTK_SHADER_PREFETCH=1`).
- `b5cbbca`: bounded pipeline prediction rescans; in-flight slots remain protected.
- `bfdd085`: background translation/library/pipeline preparation on Mac. Pure
  colour draws may appear a few frames late while their shaders compile. Compute,
  storage-writing/stream-output programs, occlusion-counting draws and persistent
  cube/array/3D targets keep the synchronous correctness path.
- `bc461fc`: look ahead and prioritise required shader jobs on separate services.
- Relevant parts of `7305d4e`: background jobs own their code bytes and write the
  code file themselves; prediction checks the clock every 64 commands.
- `42d3c4f` (Dormon Zhou): GPU conversion of texel subregions with CPU fallback,
  bounds/overlap guards and a production read/write GPU probe.

The async shader commits are authored by Yong Li and the prefetch commit by
lakuch; see their original commit messages for measurements. Those measurements
are not validation of this macOS 15 backport. This port keeps the conservative
occlusion-query behavior; it does not import `311f7ec`'s query-result substitution,
the newer border-colour pipeline machinery, or the pipeline archive dependency.

Metal 3 keeps the previous argument reuse/resource-declaration switches and
binary-search buffer registry. Background and urgent translators default to two
services each on Metal 3 for the 16 GB target (four each on Metal 4); adjust with
`TOTK_RT_BG_WORKERS` / `TOTK_RT_URGENT_WORKERS` (1–8). Fewer workers may make newly
encountered objects appear later. Child processes get an empty signal mask and
close-on-exec file descriptors so background service pipes do not hang.
`TOTK_ASYNC_SHADERS=0` disables async draw skipping; `TOTK_TEXELS_GPU=0` returns to
the CPU texel conversion path. Cached-library prefetch remains opt-in because it
can compile variants never used and increase CPU/memory load.

Changed production files:
`games/totk/Makefile`, `runtime/loader.c`, `runtime/gpu_path_probe.m`,
`third_party/d2r_gfx/gfx/nvn/{hle_nvn.c,nvn_mtl.h,nvn_mtl.m,nvn_obj.h,totk_shader_rt.h,totk_shader_rt.m}`,
and `third_party/d2r_gfx/gfx/tex/{nvn_deswizzle_gpu.h,nvn_deswizzle_gpu.m}`.
Tests/checks: `scripts/check_macos_backend.sh`, `nvn_texels_region_probe.h`,
`tests/async_shaders/probe.m`, and repository-level
`tests/test_async_shader_{policy,rt}.py`. Documentation also updates
`docs/pipeline-prediction-stalls.md` and this file. No game/key/save files change.

Validation in Linux: both backend API audits, shell syntax and Make dry runs
pass; 104 Python tests run, 92 pass and 12 skip because Apple APIs or another
platform/tool are unavailable. The portable safety test compiles the actual SPH
classifier. The Apple-only queue test exercises production Objective-C with a
synthetic translator in a temporary folder (no game data/keys): publication only
after the callback, duplicate requests, urgent work, synchronous adoption and
child signal/pipe setup. Native compilation and GPU/gameplay verification remain
pending on the user's Mac.

First, quit the game and check compilation plus the isolated queue test:

```sh
cd "$HOME/MacNativeGames"
git pull --ff-only
bash games/totk/scripts/check_macos_backend.sh 3
```

Then use the existing `build_app.py ... --metal-backend 3` command and unchanged
work/output paths. With the rebuilt 1.4.3 executable, run the probes separately:

```sh
cd "$HOME/TOTK_build_metal3/totk"
MTL_DEBUG_LAYER=1 MTL_DEBUG_LAYER_ERROR_MODE=assert TOTK_HEADLESS=1 \
  TOTK_M3_RESOURCE_CACHE=1 \
  ./build/totk-native-v143 rewritten/v143 probe-gpu-arg-epoch
MTL_DEBUG_LAYER=1 MTL_DEBUG_LAYER_ERROR_MODE=assert TOTK_HEADLESS=1 \
  ./build/totk-native-v143 rewritten/v143 probe-gpu-texels-region
```

Existing launchers retain their input and optimization flags. Async shaders and
the texel-region path are enabled by default; compare the same combat/traversal
route with the window in front and report actual long-frame logs. Neither the
Linux checks nor a successful GPU probe guarantee that every scene is stutter-free.

### 2026-10-22: experimental 60 FPS launch policy (opt-in)

The packaged launcher retains its previous launch policy on both backends.
Explicit `TOTK_POWER_MODE=balanced` requests the experimental defaults:
`TOTK_MAX_FPS=60`, `TOTK_GPU_KEEPALIVE=0`, `TOTK_ARG_EPOCH=1`, and
`TOTK_M3_RESOURCE_CACHE=1`. These are defaults only: an explicitly supplied value
wins. An unset mode or `TOTK_POWER_MODE=performance` retains the previous launch
policy (no new defaults). The launcher logs the effective ceiling and keepalive
value when balanced mode is explicitly requested.

Native Mac graphics compilation, GPU binding smoke tests, async shader tests and
power-policy tests passed, and packaging succeeded. Subsequent gameplay reports
included exits with balanced mode and again with only keepalive disabled. One
captured exit is SIGSEGV in the rewritten 1.4.3 main at `0x2b8464`, accessing
`0x0070716263900090`; this does not establish that keepalive is the root cause.
The previous performance policy was reported to run successfully. Balanced mode
is therefore no longer enabled automatically, pending diagnosis and gameplay
validation. Existing packages need a rebuild to adopt the restored default; use
the explicit performance command below in the meantime. Do not paper over this
fault by ignoring the memory access or changing game data.

This is a render ceiling, not a new guest clock. Previously the default uncapped
clock could run at 120 Hz while a 60 Hz screen showed the latest image and discarded
older ones. Reducing `TOTK_UNCAPPED_HZ` directly can turn a two-tick interval into
30 FPS. Instead `nvn_frame_limit_period` applies a minimum render period to the
existing real-time uncapped pacer while keeping its virtual tick frequency and
requested interval. At 120 Hz, both one- and two-tick intervals are limited to a
60 FPS ceiling; a four-tick 30 FPS interval remains unchanged. This does not force
slow scenes to render faster, skip draws, lower resolution, change the game-speed
patch or modify input. Deterministic clocks, explicit no-pacing benchmarks,
display-synchronised modes and MetalFX half/30 pacing retain their behavior.
`TOTK_MAX_FPS=0` disables the new ceiling. Turning off keepalive can reduce clock
boosting and may reduce performance in some scenes; compare rather than assuming
that temperature or sustained FPS will improve.

Changes: `build_app.py` passes the selected backend to `app/launcher.m`;
`app/power_policy.h` supplies the defaults; `nvn_frame_limit.h` and `hle_nvn.c`
implement the ceiling. `Makefile` checks launcher syntax; the Mac check script
runs `tests/test_power_policy.py` and its compiled `tests/power_policy_probe.c`.
The production present-interval probe also checks the new ceiling with the
120 Hz virtual clock. No system power settings, game data, keys, saves, wrapper
apps or controller mappings are edited.

Linux validation: 106 tests, 94 passed and 12 skipped for unavailable platforms or
tools. Both graphics backend audits, shell syntax and Make dry runs pass. The C
probe checks parsing/overrides, preservation of Metal 4 defaults, the real pacer
with two swapchain images over 600 frames, no halving of 60 to 30, and no extra
slowdown when CPU work already exceeds the target. Native checks and packaging
also passed, but neither establishes crash-free gameplay or a thermal benefit.

Quit the game, pull this branch, and run `bash games/totk/scripts/check_macos_backend.sh 3`.
After that succeeds, rebuild using the existing `build_app.py` command and output
path. The existing wrapper will retain the prior policy on its next launch.
Do not opt into balanced mode while diagnosing the reported exits. To inspect logs:

```sh
grep -E '\[power\]|GPU 保活|计时 至帧|上屏节奏' \
  "$HOME/Library/Logs/MacNativeGames/totk.log" | tail -n 16
```

Compare the same combat/traversal route after 10–15 minutes under similar ambient
conditions. To compare against the prior behavior (or if frame pacing gets worse):

```sh
TOTK_POWER_MODE=performance TOTK_FACE_BUTTONS=position \
  TOTK_ARG_EPOCH=1 TOTK_M3_RESOURCE_CACHE=1 \
  "$HOME/TOTK Metal3.app/Contents/MacOS/TOTK"
```

Fanless hardware can still become warm at 60 FPS; these code changes are not a
promise of low surface temperature or a guaranteed FPS increase.

For guest fault diagnosis, `scripts/diagnose_guest_fault.py` reads at most 52 bytes
around each requested offset from a local rewritten module and prints instruction
words, with disassembly when Capstone is available in the build virtualenv. It
never executes or modifies the module, and does not access keys, saves or fonts.
