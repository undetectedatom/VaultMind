import os
import shutil
import zipfile
import requests

# Direct link to the source code archive (Much more stable than git clone)
REPO_ZIP_URL = "https://github.com/kubernetes/website/archive/refs/heads/main.zip"
ZIP_FILENAME = "k8s_docs.zip"
TARGET_DIR = "data/user_troubleshooting"
MAX_FILES = 100


def download_and_extract_mds():
    print("🚀 Bypassing Git: Downloading repository ZIP directly...")

    # 1. Download the ZIP securely in chunks
    if not os.path.exists(ZIP_FILENAME):
        with requests.get(REPO_ZIP_URL, stream=True) as r:
            r.raise_for_status()
            with open(ZIP_FILENAME, "wb") as f:
                # 1MB chunks to handle network drops gracefully
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
        print("✅ ZIP Download complete.")

    os.makedirs(TARGET_DIR, exist_ok=True)
    count = 0

    # 2. Extract ONLY the markdown files directly from the ZIP
    print(f"📂 Extracting exactly {MAX_FILES} Markdown files...")
    with zipfile.ZipFile(ZIP_FILENAME, "r") as zip_ref:
        all_files = zip_ref.namelist()

        for file_path in all_files:
            # Target the official English docs, ignore structure/index files
            if (
                file_path.endswith(".md")
                and "content/en/docs" in file_path
                and not file_path.endswith("_index.md")
            ):

                # Extract the file and give it a clean, unique name
                target_path = os.path.join(TARGET_DIR, f"k8s_doc_{count}.md")

                with zip_ref.open(file_path) as source, open(
                    target_path, "wb"
                ) as target:
                    shutil.copyfileobj(source, target)

                count += 1
                if count >= MAX_FILES:
                    break

    # 3. Clean up the massive ZIP file to save disk space
    print("🧹 Cleaning up temporary ZIP file...")
    if os.path.exists(ZIP_FILENAME):
        os.remove(ZIP_FILENAME)

    print(f"✅ Success! {count} Markdown files saved to {TARGET_DIR}")


if __name__ == "__main__":
    download_and_extract_mds()
