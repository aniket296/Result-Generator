"""
installer/generate_assets.py
Generates high-resolution application icons and graphical assets for the Inno Setup Windows installer.
Creates a professional multi-resolution .ico (16x16, 32x32, 48x48, 64x64, 128x128, 256x256)
representing the Teacher Result Card Generator.
"""
import os
from PIL import Image, ImageDraw


def generate_app_icon(output_path: str) -> str:
    """
    Draws a modern gradient emblem with an academic mortarboard / result card icon
    and saves it as a multi-resolution Windows .ico file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Rounded rectangle background with deep indigo-blue gradient
    margin = 12
    corner_radius = 48
    
    # Draw rounded rectangle base
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=corner_radius,
        fill=(30, 58, 138, 255),  # Deep Blue #1e3a8a
        outline=(79, 70, 229, 255),  # Indigo border #4f46e5
        width=6,
    )

    # Inner badge accent
    inner_margin = 24
    draw.rounded_rectangle(
        [(inner_margin, inner_margin), (size - inner_margin, size - inner_margin)],
        radius=36,
        fill=(37, 99, 235, 230),  # Royal Blue #2563eb
    )

    # 2. Draw Result Card sheet (white paper with folded top-right corner)
    doc_left = 68
    doc_top = 64
    doc_right = 188
    doc_bottom = 200
    doc_corner = 28

    # Document body
    paper_points = [
        (doc_left, doc_top),
        (doc_right - doc_corner, doc_top),
        (doc_right, doc_top + doc_corner),
        (doc_right, doc_bottom),
        (doc_left, doc_bottom),
    ]
    draw.polygon(paper_points, fill=(255, 255, 255, 255))
    draw.line(paper_points + [(doc_left, doc_top)], fill=(203, 213, 225, 255), width=3)

    # Folded corner triangle
    fold_points = [
        (doc_right - doc_corner, doc_top),
        (doc_right - doc_corner, doc_top + doc_corner),
        (doc_right, doc_top + doc_corner),
    ]
    draw.polygon(fold_points, fill=(226, 232, 240, 255))
    draw.line(fold_points, fill=(148, 163, 184, 255), width=2)

    # 3. Document text lines & Grade badge
    # Text lines
    draw.rounded_rectangle([(82, 100), (145, 108)], radius=4, fill=(59, 130, 246, 255))
    draw.rounded_rectangle([(82, 120), (160, 128)], radius=4, fill=(148, 163, 184, 255))
    draw.rounded_rectangle([(82, 140), (135, 148)], radius=4, fill=(148, 163, 184, 255))

    # Grade "A+" Badge / Checkmark Circle
    badge_center_x = 145
    badge_center_y = 168
    badge_r = 18
    draw.ellipse(
        [
            (badge_center_x - badge_r, badge_center_y - badge_r),
            (badge_center_x + badge_r, badge_center_y + badge_r),
        ],
        fill=(16, 185, 129, 255),  # Emerald Green #10b981
        outline=(255, 255, 255, 255),
        width=3,
    )
    # Checkmark inside badge
    check_points = [
        (badge_center_x - 8, badge_center_y),
        (badge_center_x - 2, badge_center_y + 6),
        (badge_center_x + 8, badge_center_y - 5),
    ]
    draw.line(check_points, fill=(255, 255, 255, 255), width=3)

    # 4. Academic Graduation Cap / Mortarboard at top
    mortar_top = 44
    mortar_center_x = 128
    mortar_width = 80
    mortar_height = 24

    cap_points = [
        (mortar_center_x, mortar_top),  # Top point
        (mortar_center_x + mortar_width // 2, mortar_top + mortar_height // 2),  # Right
        (mortar_center_x, mortar_top + mortar_height),  # Bottom
        (mortar_center_x - mortar_width // 2, mortar_top + mortar_height // 2),  # Left
    ]
    draw.polygon(cap_points, fill=(245, 158, 11, 255))  # Amber/Gold #f59e0b
    draw.line(cap_points + [(mortar_center_x, mortar_top)], fill=(217, 119, 6, 255), width=2)

    # Cap skull cap underneath
    draw.chord(
        [
            (mortar_center_x - 24, mortar_top + mortar_height // 2),
            (mortar_center_x + 24, mortar_top + mortar_height + 12),
        ],
        0, 180,
        fill=(217, 119, 6, 255),
    )

    # Save multi-size icon
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(
        output_path,
        format="ICO",
        sizes=icon_sizes,
    )
    return output_path


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, "assets")
    ico_dest = os.path.join(assets_dir, "app_icon.ico")
    generate_app_icon(ico_dest)
    print(f"[OK] Application icon generated at: {ico_dest}")

