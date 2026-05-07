import os
import json
import time
import requests
import mimetypes  # Added to dynamically detect Markdown, PDF, HTML, etc.

CONFIG_PATH = "experiment_config.json"
BATCH_SIZE = 5  # Upload 5 files per HTTP request to prevent timeout/size errors


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def setup_environment():
    config = load_config()
    base_url = config["api_base_url"]

    print("🚀 Starting Environment Initialization...\n")

    for cluster_name, cluster_config in config["clusters"].items():
        print(f"--- Initializing Knowledge Base: {cluster_name} ---")

        # 1. Register User
        user_data = {
            "username": cluster_config["username"],
            "password": cluster_config["password"],
            "email": cluster_config["email"],
        }
        res_reg = requests.post(f"{base_url}/v1/users/register", json=user_data)
        if res_reg.status_code == 201:
            print(f"✅ User '{user_data['username']}' registered.")
        else:
            print(f"⚠️ User might exist or error: {res_reg.text}")

        # 2. Login to get token for upload
        res_auth = requests.post(
            f"{base_url}/auth/token",
            data={"username": user_data["username"], "password": user_data["password"]},
        )
        token = res_auth.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Target Directory Check
        data_dir = cluster_config["data_dir"]
        if not os.path.exists(data_dir):
            print(f"❌ Directory not found: {data_dir}. Skipping uploads.")
            continue

        files_in_dir = [
            f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))
        ]

        if not files_in_dir:
            print(f"⚠️ No files found in {data_dir}.")
            continue

        # 4. Process files in batches to match the endpoint's list[UploadFile]
        for i in range(0, len(files_in_dir), BATCH_SIZE):
            batch = files_in_dir[i : i + BATCH_SIZE]
            files_payload = []
            opened_files = []  # Keep track of file objects so we can close them later

            for filename in batch:
                file_path = os.path.join(data_dir, filename)
                f = open(file_path, "rb")
                opened_files.append(f)

                # Dynamically guess the MIME type (e.g., text/markdown, application/pdf)
                mime_type, _ = mimetypes.guess_type(file_path)
                mime_type = mime_type or "application/octet-stream"

                # To send a list of files in requests, append tuples with the exact same key: "files"
                files_payload.append(("files", (filename, f, mime_type)))

            try:
                print(f"   📤 Uploading batch of {len(batch)} files...")
                res_up = requests.post(
                    f"{base_url}/v1/documents/upload",
                    headers=headers,
                    files=files_payload,
                )

                if res_up.status_code == 200:
                    print(f"   ✅ Batch uploaded successfully.")
                else:
                    print(f"   ❌ Failed to upload batch: {res_up.text}")
            finally:
                # Safely close all files in the current batch to prevent memory leaks
                for f in opened_files:
                    f.close()

        print(f"⏳ Waiting for ChromaDB to finish embedding {cluster_name}...\n")
        # You may want to increase this sleep time if you are uploading hundreds of files
        time.sleep(10)

    print("🎉 Initialization Complete. You can now run the experiment.")


if __name__ == "__main__":
    setup_environment()
