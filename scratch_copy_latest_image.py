import os
import shutil

def main():
    artifacts_dir = r"C:\Users\jeon0\.gemini\antigravity-ide\brain\9511c7e2-27e6-46b9-8d7d-73635a564d80"
    target_path = r"f:\app\4. AHP마스터\manual_sheet_url_guide.png"
    
    files = [f for f in os.listdir(artifacts_dir) if f.startswith("media__") and f.endswith(".png")]
    if not files:
        print("No media files found in artifacts directory.")
        return
        
    # Find the newest file by modification time
    newest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(artifacts_dir, f)))
    newest_path = os.path.join(artifacts_dir, newest_file)
    
    print(f"Newest media file: {newest_file} (Size: {os.path.getsize(newest_path)} bytes)")
    shutil.copy2(newest_path, target_path)
    print(f"Copied to {target_path} successfully.")

if __name__ == "__main__":
    main()
