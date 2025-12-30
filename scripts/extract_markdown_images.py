import re
import os
import base64

def extract_images(markdown_path, images_dir):
    """
    Extracts base64 encoded images from a markdown file, saves them to a directory,
    and replaces the base64 strings with relative file paths in the markdown file.
    """
    
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find lines like: [image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAeUAAAEZC>
    # Note: The user example showed the line starting with [image1]: <data...
    # and possibly spanning multiple lines if the base64 string is very long, 
    # but strictly speaking, markdown references are usually single lines. 
    # However, usually base64 strings in this context might be on one line.
    # Let's assume standard reference format: [id]: <url> or [id]: url
    # The user provided: [image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAeUAAAEZC
    # We will look for the pattern and extract the full base64 string.
    
    # We'll stick to line-by-line processing to be safe with large files and strictly target the pattern described.
    
    new_lines = []
    
    # Pattern to match the start of the image definition
    # Group 1: Image ID (e.g. image1)
    # Group 2: Extension (e.g. png)
    # Group 3: Base64 data
    pattern = re.compile(r'^\[(image\d+)\]:\s*<data:image/(png|jpeg|jpg|gif);base64,([a-zA-Z0-9+/=]+)>?\s*$')

    # To handle potential multiline or unknown closure, let's read non-linearly or just handle the user specific format.
    # The user said: "[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAeUAAAEZC"
    # It seems to be standard markdown reference link format.
    
    lines = content.splitlines()
    modified = False
    
    for line in lines:
        match = pattern.match(line)
        if match:
            img_id = match.group(1)
            ext = match.group(2)
            b64_data = match.group(3)
            
            # Use 'jpg' for 'jpeg' to be concise, or keep original. Let's keep original extension.
            
            filename = f"{img_id}.{ext}"
            file_path = os.path.join(images_dir, filename)
            
            try:
                img_data = base64.b64decode(b64_data)
                with open(file_path, 'wb') as img_f:
                    img_f.write(img_data)
                
                # Create relative path for markdown
                rel_path = f"images/{filename}"
                new_line = f"[{img_id}]: {rel_path}"
                new_lines.append(new_line)
                modified = True
                print(f"Extracted {filename}")
            except Exception as e:
                print(f"Failed to extract {img_id}: {e}")
                new_lines.append(line) # Keep original if failed
        else:
            new_lines.append(line)

    if modified:
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines) + '\n')
            # ensure final newline matches original style roughly or just ensure it exists
        print(f"Successfully updated {markdown_path}")
    else:
        print("No images found to extract.")

if __name__ == "__main__":
    # markdown_file = "/Users/mac/Documents/genetics/WGSExtract/WGSExtractRepo/docs/WGS Extract Manual Alphav4.md" # hardcoded for this task
    # We should make paths relative or absolute as needed.
    # Repo root assumption based on user context: /Users/mac/Documents/genetics/WGSExtract/WGSExtractRepo
    
    base_dir = "/Users/mac/Documents/genetics/WGSExtract/WGSExtractRepo"
    doc_path = os.path.join(base_dir, "docs/WGS Extract Manual Alphav4.md")
    img_dir = os.path.join(base_dir, "docs/images")
    
    extract_images(doc_path, img_dir)
