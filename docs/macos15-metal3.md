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
