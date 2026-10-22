# Local Mac task: diagnose TOTK exits and improve sustained 60 FPS

Read this file and `docs/macos15-metal3.md`, then work directly in the local
checkout. The user wants the agent to inspect files, edit source, run builds and
read logs without repeatedly asking them to copy terminal commands. They are a
beginner; communicate briefly in Chinese. Actual scene traversal/combat and
subjective heat assessment may still need their help.

## Machine, scope and constraints

- Apple M4 MacBook Air, 16 GB RAM, macOS 15.7.3; Command Line Tools SDK 15.5,
  Apple clang 17; Homebrew Python 3.14.
- Checkout: `~/MacNativeGames`, branch `macos15-metal3`.
- Keep macOS 26+ Metal 4 support. macOS 15 uses the Metal 3 backend. Do not enable
  unsupported MetalFX features on Metal 3.
- Maintain approximately 60 FPS; the user explicitly rejects a 30 FPS cap.
- Never delete or modify original game packages, keys, firmware, extracted fonts
  or saves. Do not print key contents. Do not ignore invalid memory accesses or
  invent a pointer correction to suppress a crash.
- Preserve the Xbox controller's original Switch position layout:
  `TOTK_FACE_BUTTONS=position`. Existing wrapper names include
  `~/Applications/王国 之泪 Xbox.app`; do not rebuild the wrapper or replace its
  icon unnecessarily.

## Local artifacts

- Packaged game: `~/TOTK Metal3.app`.
- Launcher: `~/TOTK Metal3.app/Contents/MacOS/TOTK`.
- Bundled native executable:
  `~/TOTK Metal3.app/Contents/Resources/totk/build/totk-native`.
- Work tree: `~/TOTK_build_metal3/totk`.
- Versioned executable: `build/totk-native-v143`; modules: `rewritten/v143`.
  `build/totk-native` and `rewritten/v0` are not the right work-tree pair.
- Build virtualenv: `~/TOTK_build_metal3/totk/.venv/bin/python` (Capstone installed).
- Logs: `~/Library/Logs/MacNativeGames/totk.log`. Preserve the fault log before
  launching again; consult existing previous logs or Desktop diagnostic reports.
- Protect all of `~/Library/Application Support/MacNativeGames/TOTK` (profiles,
  saves, shader cache and settings). Do not clear the shader cache as a routine fix.
- Known verified fonts: `~/TOTK_build_metal3/fonts_21_2_verified`.

## Verified and unverified changes

Metal 3 native compilation, argument binding smoke checks, async translation
tests and packaging have passed on this Mac. The region texel GPU probe passed
17 cases; the argument epoch probe passed 15,666 checks. Async shader preparation
and GPU-address lookup improved performance; the user reported approximately
60 FPS and much less stutter before the power-policy experiment.

Commit `5543e4a` enabled balanced defaults on Metal 3: a real render ceiling of
60 FPS (while preserving the original 120 Hz virtual guest clock), disabled GPU
keepalive, and enabled argument/resource caches. Compilation and pacing tests
passed but gameplay then exited. Performance mode ran successfully for a while.
A second test using performance mode and only `TOTK_GPU_KEEPALIVE=0` also crashed.
This is correlation, not proof that keepalive is the root cause.

Commit `2a7bce9` restored the previous default launch policy, making balanced mode
explicitly opt-in, and added a read-only fault inspection script. That source
change has passed the cloud suite (94 passed, 12 platform/tool skips) but the
existing Mac app may NOT have been rebuilt with it. Therefore continue using
explicit environment settings until the native app is rebuilt.

Known working comparison command (quit an existing game first; otherwise the
launcher may merely activate that process and ignore the new environment):

```sh
TOTK_POWER_MODE=performance TOTK_GPU_KEEPALIVE=1 \
TOTK_FACE_BUTTONS=position TOTK_ARG_EPOCH=1 TOTK_M3_RESOURCE_CACHE=1 \
"$HOME/TOTK Metal3.app/Contents/MacOS/TOTK"
```

## Actual crash evidence

An earlier exit log ended with `window closed; graceful guest shutdown pending`;
that was a window-close path and is distinct from the subsequently captured
SIGSEGV. There were no matching macOS DiagnosticReports. The runtime's signal
handler logs diagnostics and calls `_exit(128+num)`, so absence of an OS crash
report does not exclude a crash.

The actual failure log contained:

```text
signal=0xb
fault=0x0070716263900090
esr=0x92000004
pc=0x109a30464
main offset=0x2b8464
x0=0x0070716263900000
x8=0x0000007071626c9e
x19=0x000000035e801838
x21=0x0000000364c8a488
```

The exact rewritten instructions were read on the user's Mac:

```text
main+0x9a89d4: ldr x8, [x0, #0x228]
main+0x9a89d8: cbz x8, #0x9a89e4
main+0x9a89dc: ldr x0, [x8, #0xb0]
main+0x9a89e0: ret
main+0x9a89e4: mov x0, xzr
main+0x9a89e8: ret

main+0x1bd01bc: ldr x8, [x19, #0x6b0]
main+0x1bd01c0: cbz x8, #0x1bd01f0
main+0x1bd01c4: ldr x21, [x8]
main+0x1bd01c8: cbz x21, #0x1bd01f0
main+0x1bd01d4: mov x1, x21
main+0x1bd01d8: mov x2, xzr
main+0x1bd01dc: bl #0x155ec
main+0x1bd01e0: mov x0, x21
main+0x1bd01e4: bl #0x9a89d4
main+0x1bd01e8: cbz x0, #0x1bd01f0
main+0x1bd01ec: bl #0x2b8464

main+0x2b8464: ldr w10, [x0, #0x90]!
main+0x2b8468: mov w8, w10
main+0x2b846c: ldxr w10, [x0]
```

Stack offsets also include `0x1bd0100`, `0x241594c`, `0x1066bb8`, `0x9fd758`,
`0x50b548`, `0x50afe4`, `0x50acdc`, `0x2becc4`, `0x443b3c`, `0x43c7d8`,
`0x420ff4`. The actual fault precedes the exclusive atomic instruction. The
getter merely loads pointers; do not assume that right-shifting the invalid
value or aligning its parent address is a valid repair.

There is an existing narrowly guarded invalid optional-menu-reference handler
in `runtime/loader.c`; the 1.4.3 mapping of its PC is `0x1bd01c4`. It only handles
the exact sentinel `0xffff0000ffffffff`. The current crash is a different fault;
do not broaden that handler to silently skip arbitrary bad pointers.

The last proposed diagnostic launch retained the working settings and added:

```sh
TOTK_CRASH_MEM=21:0x200:0x80 TOTK_CRASH_MEM_FOLLOW=5
```

This would dump the parent field at `x21+0x228` and follow it if another crash
occurs. No resulting diagnostic dump has yet been received. These flags only
read memory after a fault. Prefer preserving current logs and inspecting the
local executable/original NSO before asking the user to reproduce a crash.

Read-only static inspection is available through:
`games/totk/scripts/diagnose_guest_fault.py --image <main.patched.bin> --offset <hex>`.

## Thermal and timing observations

The machine reported mild thermal pressure twice during one minute of gameplay,
with approximately 264–316 MB swap, not the historical 18 GB memory pressure.
`pmset -g therm` returned no recorded warning information; that is not proof that
no frequency reduction occurred. Another empty-gameplay report cooled to normal
after the process had apparently stopped; do not count it as a successful
in-game thermal improvement. No actual temperature in degrees was measured.

Performance-mode logs showed GPU keepalive ~3–7 spin kernels per frame, averaging
~1 ms each. Sample gameplay had frame p50 ~13–18 ms and GPU p50 ~8–11 ms, occasional
25–40 ms spikes and 9–26% longer presentation intervals in selected 600-frame
windows. The sampled spikes had zero new pipelines/libraries, so shader
compilation does not explain every stutter. Some texture uploads took 6–8 ms.
Do not treat asynchronous GPU and CPU times as strictly additive, or equate the
inverse of a frame-time median with measured displayed average FPS.

## Native checks and build

Run `bash games/totk/scripts/check_macos_backend.sh 3` in the local checkout after
source fixes. Use native probes appropriate to changes. For example, from the
work tree (after rebuilding):

```sh
MTL_DEBUG_LAYER=1 MTL_DEBUG_LAYER_ERROR_MODE=assert TOTK_HEADLESS=1 \
TOTK_M3_RESOURCE_CACHE=1 \
./build/totk-native-v143 rewritten/v143 probe-gpu-arg-epoch
```

Existing successful packaging command (retain the final app path so Metal's
location-specific startup shader cache stays warm):

```sh
cd "$HOME/MacNativeGames"
python3.14 build_app.py \
  "$HOME/Downloads/塞尔达/薩爾達傳說 王國之淚 - v1.0.0 [0100F2C0115B6000][v0].nsp" \
  --update "$HOME/Downloads/塞尔达/The Legend of Zelda Tears of the Kingdom v1.4.3 [0100F2C0115B6800][v720896][UPD].nsp" \
  -k "$HOME/Downloads/prodkeys-main/prod.keys" \
  --shared-fonts "$HOME/TOTK_build_metal3/fonts_21_2_verified" \
  --metal-backend 3 --work "$HOME/TOTK_build_metal3" \
  -o "$HOME/TOTK Metal3.app"
```

An incremental package previously took ~6 minutes, including the OS bundle check;
17,035 startup shaders were found in Metal's cache. The optional offline Metal
toolchain warning does not block this build. Check current disk availability;
do not clean data without authorization.

Find the cause, fix it where evidence supports a change, run local compile/tests,
and describe what is actually validated. Do not claim the crash or thermal
problem is resolved merely because compilation passes.
