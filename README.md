# desops

`desops` decrypts SOPS-encrypted Kubernetes secrets and recreates the corresponding `.env`, `.json`, and `.dockerconfigjson` files defined by a Kustomize configuration.

## How it works

The tool follows a simple workflow:

1. Reads the Kustomization file and builds a mapping between Kubernetes Secret names and output files.
2. Decrypts the SOPS-encrypted YAML file using `sops`.
3. Decodes Base64-encoded Secret values.
4. Matches each Secret with its corresponding output file.
5. Creates the `generated/` directory in the current working directory.
6. Writes the decoded values using the appropriate format:

   * `.env` files → `KEY=VALUE`
   * `.json` files → JSON content
   * `.dockerconfigjson` → raw JSON content

## Main functions

### `read_kustomization()`

Reads the `secretGenerator` section from the Kustomize configuration and creates a mapping between Secret names and generated files.

Example:

```yaml
secretGenerator:
  - name: backend-secret
    envs:
      - backend.env

  - name: firebase-credentials
    files:
      - credentials.json
```

Produces:

```text
backend-secret → backend.env
firebase-credentials → credentials.json
```

### `decrypt_file()`

Uses SOPS to decrypt the encrypted YAML file and returns the decrypted content.

### `decode_secrets()`

Parses the decrypted YAML, extracts the Secret data and Base64-decodes each value.

The returned structure is:

```python
{
    "backend-secret": {
        "DATABASE_URL": "...",
        "CLIENT_SECRET": "..."
    },
    "portal-secret": {
        "API_KEY": "..."
    }
}
```

### `write_env_files()`

Uses the mapping from the Kustomization and writes the decoded Secret data to the appropriate files inside `generated/`.

`.env` files are written as:

```text
KEY=VALUE
```

JSON-based files are written as their raw JSON value.

## Use cases

`desops` is useful when:

* Kubernetes Secrets are stored encrypted with SOPS.
* Secrets need to be temporarily restored to their original configuration files.
* A Kustomize configuration already defines how Secrets map to files.
* You want to avoid manually decoding Base64 values.
* `.env`, JSON credentials, and Docker registry credentials need to be recreated automatically.

A typical project structure might look like:

```text
project/
├── secrets/
│   └── secrets.yaml
├── secrets-tpl/
│   └── kustomization.yaml
└── generated/
```

## Requirements

The following tools must be available on the system:

* `sops`
* `gpg`

The generated binary does not bundle these external executables.

## Usage

The binary accepts two arguments:

```bash
./desops <encrypted_secrets_file> <kustomization_file>
```

For example:

```bash
./desops secrets/secrets.yaml secrets-tpl/kustomization.yaml
```

The generated files will be created relative to the directory from which the command is executed:

```text
./generated/
```

For example, when running from `project/secrets/`:

```bash
cd project/secrets

./desops secrets.yaml ../secrets-tpl/kustomization.yaml
```

the output will be:

```text
project/secrets/generated/
├── backend.env
├── portal.env
├── ticketwallet_backend_credentials.json
└── .dockerconfigjson
```

## Output formats

### Environment files

```text
DATABASE_URL=...
CLIENT_SECRET=...
```

### JSON files

The Secret value is written directly as JSON:

```json
{
  "client_id": "...",
  "client_secret": "..."
}
```

### Docker configuration

`.dockerconfigjson` is written directly as the JSON value contained in the Kubernetes Secret.

## Security

The generated files contain decrypted secrets.

Make sure the `generated/` directory is properly protected and avoid committing generated secret files to version control.

Consider adding it to `.gitignore`:

```gitignore
generated/
```
