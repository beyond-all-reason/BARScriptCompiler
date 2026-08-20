# GLTF axis swapping (`--gltf-swap`)

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

## Usage

```
python bos2cob_py3.py --gltf-swap myunit.bos
python bos2cob_py3.py --gltf-swap-s3o myunit.bos
```

Mutually exclusive; pick the one matching your model's export (`s3ocompat` in the
`.lua` metafile / scene extras selects the s3o orientation on the engine side).

Without either flag, scripts are compiled verbatim — assume the script was written
directly in Spring axes (forward +X, up +Y, left +Z).
