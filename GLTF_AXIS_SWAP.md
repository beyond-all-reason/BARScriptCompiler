# GLTF axis swapping (`--gltf-swap` / `#define GLTF`)

## The problem

The RecoilEngine loads GLTF/GLB models in a **Z-up** authoring frame and rotates the
*entire model* into Spring's **Y-up** frame at load time. However, COB/BOS piece
animations (`turn`, `move`, `spin`) always animate pieces about **Spring-space**
axes. So a BOS script written while looking at the model in its GLTF authoring axes
(yaw around Z, pitch around X, recoil along Y, ...) will animate the wrong axes
unless it is re-mapped.

This is what the `--gltf-swap` flag of `bos2cob_py3.py` is for: it rewrites every
axis reference in the script from **GLTF-space axes to Spring-space axes**, and
multiplies signed on-axis values by `-1` wherever the swap flips the axis direction.

## What the engine does

`RecoilEngine/rts/Rendering/Models/GLTFParser.cpp` (in `CGLTFParser::Load`):

```cpp
// GLTF model MUST be exported with Z axis UP. We will rotate it here by ourselves
const auto initTransform = (optionalModelParams.s3oCompat.value_or(false)) ?
	Transform(CQuaternion(0, -math::HALFSQRT2, -math::HALFSQRT2, 0)): // Rotate so xyz ==> (-x,z, y)
	Transform(CQuaternion( math::HALFSQRT2, 0, 0, -math::HALFSQRT2)); // Rotate so xyz ==> ( x,z,-y)
```

Notes:

- `CQuaternion(x, y, z, w)` — the last constructor argument is the real part `w`
  (see `RecoilEngine/rts/System/Quaternion.h`).
- The rotation is an *active* rotation (v' = q v q⁻¹) and it is applied once as the
  **root piece's baked transform**, which chains down through every piece
  (`3DModelPiece.cpp`, `S3DModelPiece::SetPieceTransform` / `ComposeTransform`).
  Node TRS quaternions are read verbatim in GLTF space on top of it.
- Per the comment in `float3.h`: **Spring unit models face +X, +Y is up, +Z is
  left.** GLTF models must be exported **Z-up** (X forward, Y right, Z up).
- `s3ocompat` is set by the model's `.lua` metafile or the scene JSON `extras`
  (`ModelUtils::GetModelParams`, `GLTFParser.cpp` `ParseSceneExtra`) and selects the
  alternate orientation for models authored in the old S3O direction (forward = -x).
- Animation tracks: the engine never reads GLTF `animations` arrays at all — piece
  motion is 100% driven by the COB script at runtime, which is why the script's axes
  alone decide where a piece actually rotates.

### Resulting axis mapping

Because the whole hierarchy is rotated, an authoring-frame (GLTF) axis points along
this Spring axis after loading:

| | default (Z-up export) | `s3ocompat = true` |
|---|---|---|
| **Spring X** = | +GLTF X | −GLTF X |
| **Spring Y** = | +GLTF Z | +GLTF Z |
| **Spring Z** = | −GLTF Y | +GLTF Y |

## Mapping the script axes

A `turn`/`move`/`spin` about a GLTF axis must be emitted as a rotation/translation
about the corresponding Spring axis. If the same physical axis comes out *negated*,
the on-axis value (angle for turn/spin, distance for move) must be multiplied by
`-1`, because rotating θ about −A equals rotating −θ about +A.

`--gltf-swap` (default engine path):

| Script axis (GLTF) | Compiled axis (Spring) | Value |
|---|---|---|
| `x-axis` | `x-axis` | unchanged |
| `y-axis` | `z-axis` | × −1 |
| `z-axis` | `y-axis` | unchanged |

`--gltf-swap-s3o` (`s3ocompat` models):

| Script axis (GLTF) | Compiled axis (Spring) | Value |
|---|---|---|
| `x-axis` | `x-axis` | × −1 |
| `y-axis` | `z-axis` | unchanged |
| `z-axis` | `y-axis` | unchanged |

### Which statements are affected

Axis *references* are re-mapped in: `turn` (incl. `turn ... now`), `move`
(incl. `move ... now`), `spin`, `stop-spin`, `scale`, `wait-for-turn`,
`wait-for-move` — i.e. **every** statement the grammar gives an `axis` in, so a
`wait-for-turn` can never hang waiting on an axis that nothing rotates.

Values are multiplied by `−1` (as an extra `PUSH_CONSTANT −1` / `MUL` in the
bytecode, so it also works on variable/`get`-based expressions) **only** for the
signed on-axis values of:

- `turn` / `move now`: the target angle / target position
- `spin`: the initial rotation speed (the optional `accelerate <...>` value is a
  magnitude and is left untouched)

Values that are *not* on-axis magnitudes are never negated: `speed <...>` of a
turn/move, `decelerate <...>` of `stop-spin`, `scale` amounts.

## Example

Lines from `Beyond-All-Reason/scripts/Units/armstump.bos`, rewritten as if the
model and script were authored in GLTF space (Z-up in the editor):

```
	turn turret to y-axis <0.0> speed <90.021978>;
	turn sleeve to x-axis <0.0> speed <50.010989>;
	turn turret to y-axis heading speed <90.0>;
	turn sleeve to x-axis <0.0> - pitch speed <50.0>;
	move barrel to z-axis [-2.400000] speed [500.0];
```

With `--gltf-swap` these compile to (decompiled):

```
	turn turret to z-axis <-0.0> speed <90.021978>;   // y -> z, value inverted
	turn sleeve to x-axis <0.0> speed <50.010989>;    // x -> x, unchanged
	turn turret to z-axis (-heading) speed <90.0>;    // y -> z, value inverted (runtime * -1)
	turn sleeve to x-axis <0.0> - pitch speed <50.0>; // x -> x, unchanged
	move barrel to y-axis [-2.400000] speed [500.0];  // z -> y, value unchanged (GLTF Z = +Spring Y)
```

i.e. a turret that yaws about GLTF Z (the model's vertical as seen in the editor)
is compiled to a rotation about Spring Y (the engine's up axis), so it lines up
with where the engine's root rotation has put that axis of the loaded geometry.
Note that on the default path *only* `y-axis` statements get a sign flip; `x`
and `z` change axis without one (the flip lands on whatever Spring axis ends up
antiparallel to the script axis).

## Enabling

There are two equivalent ways to turn axis remapping on for a compile:

### 1. `#define GLTF` in the `.bos` file (per-file, recommended)

Add a `#define GLTF` line anywhere the preprocessor sees it (top of the `.bos`,
or in a `#include`d header). The define is read from the preprocessor's macro
table, so it also works when it comes from an `#include` and is correctly
ignored when it sits in a dead `#if 0` block.

```
#define GLTF
```

A **bare** `#define GLTF` (no value) activates the default engine path (see the
table above: `x -> x, y -> -z, z -> y`). A value gives full control (next
section). A file-level `#define GLTF` takes precedence over the CLI flags;
the flags remain as a fallback for files without the define.

### 2. Command line flags (whole compile)

```
python bos2cob_py3.py --gltf-swap myunit.bos
python bos2cob_py3.py --gltf-swap-s3o myunit.bos
```

Mutually exclusive; pick the one matching your model's export (`s3ocompat` in the
`.lua` metafile / scene extras selects the s3o orientation on the engine side).

Without a `#define GLTF` or either flag, scripts are compiled verbatim — assume
the script was written directly in Spring axes (forward +X, up +Y, left +Z).

## Custom axis specs (`#define GLTF <spec>`)

Instead of fixed remapping tables, the GLTF define can carry an arbitrary axis
spec as its value. The spec is a series of `;`-separated fields (case-insensitive,
whitespace around fields is ignored):

```
#define GLTF <remap_x>;<remap_y>;<remap_z>[;<turn_x>;<turn_y>;<turn_z>[;<move_x>;<move_y>;<move_z>]]
```

- Fields 1–3 (**remap**, always required): which engine axis the script's
  `x` / `y` / `z` axis maps to. Each is one of `x`, `y`, `z`. Any permutation or
  even repeated target works — full arbitrary remapping. The remap is applied to
  *every* statement that carries an axis: `turn`, `move`, `spin`, `stop-spin`,
  `scale`, `wait-for-turn`, `wait-for-move`, `wait-for-scale`.
- Fields 4–6 (**turn signs**, optional): `+` or `-` per script axis. `-` negates
  the signed on-axis value of the *angular* commands — `turn` (incl. `turn ... now`)
  and `spin`'s initial speed — for that axis.
- Fields 7–9 (**move signs**, optional): `+` or `-` per script axis. `-` negates
  the signed on-axis value of `move` (incl. `move ... now`) for that axis.

The sign split exists because a mirror/reflection between frames flips axial
vectors (turn/spin) and polar vectors (move) differently, so the two channels
can genuinely disagree. Values that are magnitudes (`speed <...>`,
`accelerate <...>`, `decelerate <...>`, `scale` amounts) are never negated.

Omitted sign fields default to `+` (no negation):

| # of fields | Meaning |
|---|---|
| 3 | remap only, no value negation |
| 6 | remap + one sign set applied to **both** turn and move |
| 9 | remap + separate turn and move sign sets |

### Examples

```
#define GLTF                          // default engine path  (x->x, y->-z, z->y)
#define GLTF x;z;y;+;-;+              // same as --gltf-swap  (only y negated)
#define GLTF x;z;y;-;+;+              // same as --gltf-swap-s3o (only x negated)
#define GLTF x;z;y                    // plain z/y swap, no negation
#define GLTF z;y;x;-;+;-;+;+;-;+      // full 9-field spec: custom remap + per-channel signs
```

The spec is validated at parse time; an invalid field count, axis letter or sign
aborts the compile with the line number of the offending `#define GLTF`.
