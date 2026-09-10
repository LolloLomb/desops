import sys
import yaml
import tempfile
import base64
import subprocess
import os

import json

def write_env_files(secrets_name_env_map, secrets):
    generated_dir = os.path.join(os.getcwd(), "generated")
    os.makedirs(generated_dir, exist_ok=True)

    for secret_name, filename in secrets_name_env_map.items():
        if secret_name not in secrets:
            continue

        filepath = os.path.join(generated_dir, filename)

        if filename.endswith(".json") or filename == ".dockerconfigjson":
            value = next(iter(secrets[secret_name].values()))

            with open(filepath, "w") as f:
                f.write(value)
        else:
            with open(filepath, "w") as f:
                for key, value in secrets[secret_name].items():
                    f.write(f"{key}={value}\n")

def decode_secrets(content):
    secrets = {}

    for secret in yaml.safe_load_all(content):
        name = secret["metadata"]["name"]

        secrets[name] = {}

        for key, value in secret["data"].items():
            secrets[name][key] = base64.b64decode(value).decode("utf-8")

    return secrets

def decrypt_file(enc_file):
    result = subprocess.run(
        ["sops", "-d", enc_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Decrypt failed.")
        return None

    return result.stdout

def read_secret_blocks(enc_file):
    blocks = []
    current_block = []

    with open(enc_file, "r") as f:
        for line in f:
            if line.startswith("apiVersion:"):
                if current_block:
                    blocks.append("".join(current_block))
                    current_block = []

            current_block.append(line)

    if current_block:
        blocks.append("".join(current_block))

    return blocks

def check_gpg_key(fp):
    result = subprocess.run(
        ["gpg", "--list-keys", "--with-colons", fp],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("GPG key found in the keyring.")
        return True

    print("GPG key not found in the keyring.")
    return False

def read_kustomization(kust_file):
    with open(kust_file, "r") as f:
        kust = yaml.safe_load(f)

    secrets = {}

    for secret in kust.get("secretGenerator", []):
        name = secret["name"]

        if "envs" in secret:
            secrets[name] = secret["envs"][0]

        elif "files" in secret:
            secrets[name] = secret["files"][0]

    return secrets

def read_secrets(fp):
    return check_gpg_key(fp)

def desops(enc_file, kust_file):
    secrets_name_env_map = read_kustomization(kust_file)
    content = decrypt_file(enc_file)

    if content is None:
        return 1

    secrets = decode_secrets(content)

    write_env_files(secrets_name_env_map, secrets)
    
def main():
    if len(sys.argv) != 3:
        print(f"Usage: desops <encrypted_file.yaml> <kustomization_file_path.yaml>")
        return 1

    enc_file = sys.argv[1]
    kust_file = sys.argv[2]

    desops(enc_file, kust_file)

    return 0

if __name__ == "__main__":
    sys.exit(main())
