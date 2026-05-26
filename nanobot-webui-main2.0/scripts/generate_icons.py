from PIL import Image
import os

def resize_icon(source_path, sizes, bg_color=(255, 255, 255, 255)):
    if not os.path.exists(source_path):
        print(f"Error: {source_path} not found.")
        return

    try:
        with Image.open(source_path) as img:
            img = img.convert("RGBA")

            # Standard PWA sizes + iOS sizes + favicon sizes
            # 64: favicon (Windows)
            # 120: iPhone Retina @2x
            # 144: Android/Tablet
            # 152: iPad Retina
            # 167: iPad Pro Retina
            # 180: iPhone Retina @3x (standard apple-touch-icon)
            # 192: Android Chrome
            # 512: Android Chrome (splash)

            for size in sizes:
                # Create white background canvas
                canvas = Image.new("RGBA", (size, size), bg_color)
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                # Composite icon over background (handles transparency correctly)
                canvas.paste(resized, (0, 0), resized)
                # Convert to RGB for PNG without alpha (avoids browser fringe issues)
                output = canvas.convert("RGB")
                output_filename = f"web/public/app-{size}x{size}.png"
                output.save(output_filename, "PNG", optimize=True)
                print(f"Generated {output_filename}")

    except Exception as e:
        print(f"Failed to process image: {e}")

if __name__ == "__main__":
    # Ensure web/public exists
    os.makedirs("web/public", exist_ok=True)
    resize_icon("scripts/logo.png", [64, 120, 144, 152, 167, 180, 192, 512])
