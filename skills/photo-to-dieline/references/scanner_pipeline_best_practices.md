# Scanner Pipeline Best Practices

## Photo Requirements

### Ideal Conditions
- **Angle**: Directly above, camera parallel to subject
- **Background**: Solid white/light gray, no patterns
- **Lighting**: Even, no shadows or hotspots
- **Focus**: Sharp, no motion blur
- **Coverage**: All edges of the unfolded box visible

### Minimum Acceptable
- Angle within 15° of perpendicular
- At least 3 corners visible
- No heavy shadows crossing dielines
- Resolution: ≥ 1000px on longest edge

## Pipeline Tuning

### Perspective Correction
- Auto-detection works for ≥80% of the document area
- Manual 4-point override when auto fails
- Homography quality check: output aspect ratio should match expected (W:L ratio)

### Shadow Removal
- Morphological opening kernel size = image_size / 10
- For textured backgrounds: increase kernel to image_size / 6
- For very dark shadows: apply CLAHE before morphological opening

### Binarization
- Otsu threshold works for bimodal histograms (clear line/background separation)
- For non-bimodal: use adaptive threshold (blockSize=31, C=5)
- For very faint lines: lower Canny thresholds (30, 100)

### Line Detection
- HoughLinesP: threshold=50, minLineLength=30px, maxLineGap=10px
- For noisy images: increase threshold to 80
- For fine lines: decrease minLineLength to 20

## Scale Calibration

Always calibrate from the LONGEST detected straight edge:
1. Longest horizontal → likely base width or wall length
2. Longest vertical → likely base length + wall height
3. Match to user-provided dimension with smallest error

Verification: check that multiple detected edges produce consistent scale factors (±5%).
