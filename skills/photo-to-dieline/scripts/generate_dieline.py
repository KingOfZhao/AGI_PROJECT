#!/usr/bin/env python3
"""
Generate Dieline DXF from detected structure + user dimensions.

Usage:
    python3 generate_dieline.py --inner 107.9 116.7 --outer 123 135 --height 46.78 \
        --structure data.json -o output.dxf

Or from direct pixel coordinates:
    python3 generate_dieline.py --outer 123 135 --height 46.78 \
        --contour-file contour_coords.txt -o output.dxf
"""

import sys, os, json, argparse, math
import ezdxf
from ezdxf import colors

def create_base_dieline(outer_w, outer_l, height, flap_depth=None, glue_width=15):
    """Create a standard cross-layout dieline with crash protection flaps."""
    
    W, L, H = outer_w, outer_l, height
    
    # Derived dimensions
    t_w = 0  # placeholder
    t_l = 0
    
    doc = ezdxf.new(dxfversion='R2000')
    msp = doc.modelspace()
    doc.layers.add('CUT', color=colors.RED)
    doc.layers.add('SCORE', color=colors.GREEN)
    doc.layers.add('DIM', color=3)
    
    def cut(a, b):
        msp.add_line(a, b, dxfattribs={'layer': 'CUT'})
    def score(a, b):
        msp.add_line(a, b, dxfattribs={'layer': 'SCORE'})
    
    # Base panel score lines
    score((0, 0), (W, 0))
    score((W, 0), (W, L))
    score((W, L), (0, L))
    score((0, L), (0, 0))
    
    # Top wall (width direction)
    cut((0, L), (W, L))
    cut((W, L), (W, L + H))
    cut((W, L + H), (0, L + H))
    cut((0, L + H), (0, L))
    
    # Bottom wall (width direction)
    cut((0, 0), (W, 0))
    cut((W, 0), (W, -H))
    cut((W, -H), (0, -H))
    cut((0, -H), (0, 0))
    
    # Left wall (length direction)
    cut((0, 0), (0, L))
    cut((0, L), (-H, L))
    cut((-H, L), (-H, 0))
    cut((-H, 0), (0, 0))
    
    # Right wall (length direction)
    cut((W, 0), (W, L))
    cut((W, L), (W + H, L))
    cut((W + H, L), (W + H, 0))
    cut((W + H, 0), (W, 0))
    
    # Crash protection flaps (if specified)
    if flap_depth and flap_depth > 0:
        fd = flap_depth
        # Top-left
        cut((0, L + H), (-fd, L + H - fd))
        cut((-fd, L + H - fd), (-fd, L))
        # Top-right
        cut((W, L + H), (W + fd, L + H - fd))
        cut((W + fd, L + H - fd), (W + fd, L))
        # Bottom-left
        cut((0, -H), (-fd, -H + fd))
        cut((-fd, -H + fd), (-fd, 0))
        # Bottom-right
        cut((W, -H), (W + fd, -H + fd))
        cut((W + fd, -H + fd), (W + fd, 0))
    
    # Glue tab (right wall outside)
    cut((W + H, 0), (W + H + glue_width, -3))
    cut((W + H + glue_width, -3), (W + H + glue_width, L + 3))
    cut((W + H + glue_width, L + 3), (W + H, L))
    score((W + H, 0), (W + H, L))
    
    return doc

def create_from_contour(contour_pts_mm, structure_data=None, output_path="output.dxf"):
    """Create DXF from detected contour coordinates (in mm)."""
    
    doc = ezdxf.new(dxfversion='R2000')
    msp = doc.modelspace()
    doc.layers.add('CUT', color=colors.RED)
    doc.layers.add('SCORE', color=colors.GREEN)
    
    # Draw outer contour
    for i in range(len(contour_pts_mm)):
        p1 = tuple(contour_pts_mm[i])
        p2 = tuple(contour_pts_mm[(i + 1) % len(contour_pts_mm)])
        msp.add_line(p1, p2, dxfattribs={'layer': 'CUT'})
    
    # Draw score lines from structure data
    if structure_data and "lines" in structure_data:
        scale = structure_data.get("scale", {}).get("scale", 1)
        for line in structure_data["lines"]:
            if line["kind"] in ("H", "V"):
                p1 = [line["p1"][0] * scale, line["p1"][1] * scale]
                p2 = [line["p2"][0] * scale, line["p2"][1] * scale]
                msp.add_line(tuple(p1), tuple(p2), dxfattribs={'layer': 'SCORE'})
    
    doc.saveas(output_path)
    return doc

def main():
    parser = argparse.ArgumentParser(description='Generate dieline DXF')
    parser.add_argument('-o', '--output', default='output.dxf', help='Output DXF path')
    parser.add_argument('--outer', nargs=2, type=float, help='Outer width length (mm)')
    parser.add_argument('--inner', nargs=2, type=float, help='Inner width length (mm)')
    parser.add_argument('--height', type=float, help='Wall height (mm)')
    parser.add_argument('--flap-depth', type=float, help='Crash flap depth (mm)')
    parser.add_argument('--glue-width', type=float, default=15, help='Glue tab width (mm)')
    parser.add_argument('--structure', help='JSON structure data from detect_lines.py')
    parser.add_argument('--contour-file', help='File with contour coords (one x,y per line)')
    args = parser.parse_args()
    
    if args.contour_file:
        # Direct contour mode
        pts = []
        with open(args.contour_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    x, y = map(float, line.split(','))
                    pts.append([x, y])
        
        structure = None
        if args.structure:
            with open(args.structure) as f:
                structure = json.load(f)
        
        doc = create_from_contour(pts, structure, args.output)
        print(f"From contour: {len(pts)} points → {args.output}")
    
    elif args.outer and args.height:
        # Parametric mode
        doc = create_base_dieline(
            args.outer[0], args.outer[1], args.height,
            flap_depth=args.flap_depth,
            glue_width=args.glue_width
        )
        doc.saveas(args.output)
        
        W, L, H = args.outer[0], args.outer[1], args.height
        t_w = (W - args.inner[0]) / 2 if args.inner else 0
        t_l = (L - args.inner[1]) / 2 if args.inner else 0
        
        print(f"Parametric dieline → {args.output}")
        print(f"  Base: {W}×{L}mm, Height: {H}mm")
        if args.inner:
            print(f"  t_w: {t_w:.2f}mm, t_l: {t_l:.2f}mm")
        if args.flap_depth:
            print(f"  Flap depth: {args.flap_depth:.1f}mm")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
