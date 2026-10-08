import base64
import os
import subprocess
import sys
import yaml


def write_env_files(secrets_name_env_map, secrets):
    generated_dir = os.path.join(os.getcwd(), "generated")
    os.makedirs(generated_dir, exist_ok=True)

    # Estensioni di file che devono contenere unicamente il valore decodificato (raw)
    RAW_FILE_EXTENSIONS = (".p12", ".json", ".dockerconfigjson", ".crt", ".key", ".pem")

    for secret_name, filename in secrets_name_env_map.items():
        if secret_name not in secrets:
            continue

        filepath = os.path.join(generated_dir, filename)

        # Se il file ha un'estensione "raw" o corrisponde a nomi specifici
        if filename.endswith(RAW_FILE_EXTENSIONS) or filename == ".dockerconfigjson":
            # Estrae il primo (e solitamente unico) valore presente nel Secret
            value = next(iter(secrets[secret_name].values()))

            with open(filepath, "wb") as f:
                f.write(value)
        else:
            # Per i file di tipo .env, scrive le coppie KEY=VALUE codificate in byte
            with open(filepath, "wb") as f:
                for key, value in secrets[secret_name].items():
                    line = f"{key}=".encode("utf-8") + value + b"\n"
                    f.write(line)


def decode_secrets(content):
    secrets = {}

    for secret in yaml.safe_load_all(content):
        # Ignora blocchi vuoti o manifest non formattati come Secret
        if not secret or "metadata" not in secret or "data" not in secret:
            continue

        name = secret["metadata"]["name"]
        secrets[name] = {}

        for key, value in secret["data"].items():
            # Mantiene il valore decodificato come sequenza di byte (bytes)
            secrets[name][key] = base64.b64decode(value)

    return secrets


def decrypt_file(enc_file):
    result = subprocess.run(
        ["sops", "-d", enc_file], capture_output=True, text=True
    )

    if result.returncode != 0:
        print("Decrypt failed.")
        return None

    return result.stdout


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


def desops(enc_file, kust_file):
    secrets_name_env_map = read_kustomization(kust_file)
    content = decrypt_file(enc_file)

    if content is None:
        return 1

    secrets = decode_secrets(content)
    write_env_files(secrets_name_env_map, secrets)
    return 0


def main():
    if len(sys.argv) != 3:
        print("Usage: desops <encrypted_file.yaml> <kustomization_file_path.yaml>")
        return 1

    enc_file = sys.argv[1]
    kust_file = sys.argv[2]

    return desops(enc_file, kust_file)


if __name__ == "__main__":
    sys.exit(main())