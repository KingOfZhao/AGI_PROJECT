#!/usr/bin/env python3
"""
Photo → Scanner Effect Pipeline
Transforms a box unfold photo into a clean, high-contrast scan-like image.

Usage:
    python3 apply_scanner_effect.py <input_photo> <output_clean.png> [--corners x1,y1 x2,y2 x3,y3 x4,y4]

If --corners not provided, auto-detects the largest quadrilateral.
"""

import sys, os, argparse
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def auto_detect_corners(img, max_area_ratio=0.95):
    """Auto-detect the largest quadrilateral in the image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = list(contours)
    if not contours:
        return None
    
    # Find largest contour
    contours.sort(key=lambda c: cv2.contourArea(c), reverse=True)
    img_area = img.shape[0] * img.shape[1]
    
    for c in contours[:10]:
        area = cv2.contourArea(c)
        if area < img_area * 0.1:  # too small
            continue
        
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        
        if len(approx) == 4:
            return approx.reshape(4, 2)
    
    return None

def order_corners(pts):
    """Order corners: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left (min x+y)
    rect[2] = pts[np.argmax(s)]  # bottom-right (max x+y)
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]  # top-right (min y-x)
    rect[3] = pts[np.argmax(d)]  # bottom-left (max y-x)
    return rect

def apply_scanner_effect(img, corners=None):
    """Apply scanner-like effect to image."""
    
    # Step 1: Perspective correction
    if corners is not None:
        src = order_corners(corners.astype(np.float32))
        w1 = np.hypot(src[3][0]-src[0][0], src[3][1]-src[0][1])
        w2 = np.hypot(src[2][0]-src[1][0], src[2][1]-src[1][1])
        h1 = np.hypot(src[1][0]-src[0][0], src[1][1]-src[0][1])
        h2 = np.hypot(src[2][0]-src[3][0], src[2][1]-src[3][1])
        dst_w, dst_h = int(max(w1, w2)), int(max(h1, h2))
        
        dst = np.array([
            [0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]
        ], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(src, dst)
        img = cv2.warpPerspective(img, M, (dst_w, dst_h), flags=cv2.INTER_LANCZOS4)
    
    # Step 2: Shadow removal (simple approach)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Morphological opening to estimate background
    kernel_size = max(img.shape) // 10
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    bg = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
    # Normalize
    diff = cv2.absdiff(gray, bg)
    result = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    
    # Step 3: CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    result = clahe.apply(result)
    
    # Step 4: Binarization with Otsu
    _, binary = cv2.threshold(result, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Step 5: Clean up - remove small noise
    kernel_small = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_small, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small, iterations=1)
    
    return binary, result  # binary and enhanced grayscale

def main():
    parser = argparse.ArgumentParser(description='Photo to Scanner Effect')
    parser.add_argument('input', help='Input photo path')
    parser.add_argument('output', help='Output clean image path')
    parser.add_argument('--corners', nargs=4, help='4 corner points as x,y pairs (TL TR BR BL)')
    parser.add_argument('--enhanced', help='Output enhanced grayscale (non-binary)', action='store_true')
    args = parser.parse_args()
    
    img = cv2.imread(args.input)
    if img is None:
        print(f"Error: cannot read {args.input}", file=sys.stderr)
        sys.exit(1)
    
    corners = None
    if args.corners:
        corners = np.array([list(map(int, c.split(','))) for c in args.corners])
    else:
        corners = auto_detect_corners(img)
        if corners is not None:
            print(f"Auto-detected corners: {corners.tolist()}")
        else:
            print("Warning: could not auto-detect corners, skipping perspective correction")
    
    binary, enhanced = apply_scanner_effect(img, corners)
    
    if args.enhanced:
        cv2.imwrite(args.output, enhanced)
    else:
        cv2.imwrite(args.output, binary)
    
    print(f"Output: {args.output} ({binary.shape[1]}x{binary.shape[0]})")

if __name__ == '__main__':
    main()
