# Nano Banana Pro Brand Book v1.0

This directory contains the locked brand template for Stage 6 visual asset generation.
All infographics must adhere to these specifications.

## Quick Reference

| Element | Specification |
|---------|--------------|
| **Background** | Dark charcoal `#1e1e1e` to `#252525` (solid, NO gradients) |
| **Frame** | Rounded rectangle, 1–2px border, 15–20% white opacity, radius 20–30px |
| **Typography** | Geometric sans (Inter/SF Pro/Outfit), max 3 sizes |
| **Title** | Bold, centered in top 15–25%, WCAG AA 4.5:1 contrast |
| **Icons** | Line-art only, 2–3px stroke, NO fills, accent color |
| **Spacing** | 8% safe-zone margins, 30–40% negative space |
| **Thumbnail** | Must be readable at 100px |

## Files

- `brand_template.json` — Machine-readable brand specifications
- `accent_palette.json` — Approved accent colors (pick ONE per asset)
- `style_variants.json` — Minimal / Data-heavy / Quote-focused templates
- `restrictions.json` — Negative prompts and forbidden elements

## Usage

Stage 6 (`stage_6_visuals.py`) automatically loads these specifications through
`branding_book/brand_loader.py` to ensure all generated assets are brand-compliant.
