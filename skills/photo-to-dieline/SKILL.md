---
name: photo-to-dieline
description: Convert a photo of a flat-packed box into a precise parametric dieline (DXF/SVG). Workflow: photo → scanner effect (perspective correction, shadow removal, contrast enhance) → crease/edge detection → LWH-mapped parametric vector output. Trigger when user uploads a box unfold photo + provides inner/outer dimensions (L,W,H).
---

# Photo-to-Dieline

Convert a photo of a folded/flat box into a precise 2D dieline (DXF/SVG).

## Trigger

User uploads a box unfold photo AND provides dimensions (inner/outer L,W,H).

## Workflow

### Step 1: Scanner Effect (`scripts/apply_scanner_effect.py`)

Transform photo into clean high-contrast scan-like image:
- Perspective correction (4-point homography)
- Shadow removal (inpainting)
- Adaptive contrast enhancement (CLAHE)
- Binarization / high-contrast white background

```bash
python3 scripts/apply_scanner_effect.py <input_photo> <output_clean.png>
```

### Step 2: Line Detection (`scripts/detect_lines.py`)

From clean image, detect:
- **CUT lines**: outer contour (Canny + contour extraction)
- **SCORE lines**: fold/crease lines (HoughLinesP + LSD)
- Classify by angle: horizontal, vertical, diagonal
- Topology analysis: identify panels, flaps, glue tabs

```bash
python3 scripts/detect_lines.py <clean_image> <output_data.json>
```

Output JSON structure:
```json
{
  "contours": [{"points": [[x,y],...], "type": "CUT|SCORE", "length_mm": ...}],
  "panels": [{"bbox": [x,y,w,h], "role": "base|wall|flap|glue_tab", "dims_mm": [w,h]}],
  "scale": 0.3358,
  "scale_ref": {"px": 402, "mm": 135, "desc": "seg17=outer_length"}
}
```

### Step 3: Dieline Generation (`scripts/generate_dieline.py`)

Combine detected structure with user-provided dimensions:
- Map pixel coords → mm using scale factor (calibrated from known dimension)
- Override detected panel sizes with exact LWH-derived dimensions
- Generate DXF with layers: CUT (red), SCORE (green), DIM (blue)

```bash
python3 scripts/generate_dieline.py --inner 107.9 116.7 --outer 123 135 --height 46.78 --structure <data.json> -o output.dxf
```

### Step 4: Verification

Before final output, show user:
1. The scanner-effect image (confirm cleaning quality)
2. Detected line overlay on original (confirm detection accuracy)
3. Key dimensions for verification

## Dimension Math

From user-provided dimensions, derive:
```
t_w = (outer_w - inner_w) / 2   # width-side wall thickness
t_l = (outer_l - inner_l) / 2   # length-side wall thickness
H = height                       # wall height
base_w = outer_w                 # base panel width
base_l = outer_l                 # base panel length
```

## Scale Calibration

Find a long straight edge in the image that matches a known dimension:
- Longest vertical edge → likely = base_l + H or base_l
- Longest horizontal edge → likely = base_w
- Pick the clearest match, compute: `scale = known_mm / detected_px`

## Common Box Topologies

Reference templates in `resources/box_net_templates/`:
- `rsc_standard.md` - Regular Slotted Container (RSC)
- `crash_protection.md` - Box with corner reinforcement flaps
- `tray.md` - Tray style (no top flaps)
- `tuck_end.md` - Tuck-end carton

## Limitations

- Photo angle too extreme → prompt user to retake or manually specify 4 corners
- Accuracy: ±1-2mm after scanner effect processing
- Works best with: single-color cardboard, clear fold lines, good lighting
- Fails with: heavily printed patterns, glossy surfaces, multiple overlapping boxes

## Tips for User

- Photograph from directly above (minimize perspective)
- Use solid background (white table/paper)
- Ensure all edges are visible
- Include a ruler or known-size reference if possible
- Cover dimension annotations if they overlap with dielines
