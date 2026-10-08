# Fish Speech API client

A lightweight Python client for a **self-hosted Fish Speech server**. Supports
speech generation, WAV streaming, saved voices, codec operations, health checks,
and the server WebUI route. No Torch, CUDA, or model dependencies on the client.

This is an independent community client, not the official Fish Audio cloud SDK.
It targets the server routes in the
[DGX Spark fork](https://github.com/lambdawalker/dgxspark.fish-speech).

## Install

Requires Python 3.10+. Until the first PyPI release, install from GitHub:

```bash
uv add 'fish-speech-api @ git+https://github.com/lambdawalker/python.fish-speech.api.git'
```

After publishing to PyPI:

```bash
uv add fish-speech-api
# Include audio-token encoding/decoding support:
uv add 'fish-speech-api[codec]'
```

With pip, use `pip install fish-speech-api` after publication.

## Usage

```python
from fishapi import FishAPI

api = FishAPI('192.168.1.50')  # Defaults to port 8080 for a bare host.
print(api.health())

# Register once using a WAV and its exact transcript.
api.add_voice('alice', 'alice.wav', 'The words spoken in the recording.')
# api.addvoice(...) is an alias.

api.generate(
    'I agree to deliver the furniture on Friday.',
    voice='alice',
    output='agreement.wav',
    seed=42,
)
```

`generate()` returns audio bytes and optionally writes a file. The server's
model and checkpoints are selected when launching the server, not by this client.
For authentication or longer compilation warm-up:

```python
api = FishAPI('http://192.168.1.50:8080', api_key='your-server-key', timeout=1200)
```

| Method | Purpose |
| --- | --- |
| `generate()` | Generate speech; optionally save audio |
| `generate_stream()` | Iterate over WAV stream bytes |
| `add_voice()` / `addvoice()` | Upload reference WAV and transcript |
| `list_voices()` | List reference IDs |
| `rename_voice()` | Rename a reference |
| `delete_voice()` | Delete a reference |
| `encode()` | Audio file bytes to token arrays; requires `codec` extra |
| `decode()` | Token arrays to raw float16 PCM; requires `codec` extra |
| `health()` | GET or POST server health |
| `webui()` | Fetch the server's built UI HTML |

See [the full API guide](docs/api.md) for endpoint mappings, streaming, errors,
and codec formats. Decode does not return WAV files or sample-rate metadata.

## Development with uv

```bash
git clone https://github.com/lambdawalker/python.fish-speech.api.git
cd python.fish-speech.api
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv build
uv run --locked twine check --strict dist/*
```

The lockfile records development dependencies; normal installations have no
required third-party dependencies. Codec support is optional. Tests use a local
HTTP fixture and do not require a running model or GPU. CI tests Python 3.10,
3.12, and 3.14 and validates the built package.

## Releases

First planned version: `0.1.0`. Conventional Commits on `main` let Release Please
prepare version/changelog PRs. Merging a release PR creates the tag/release,
validates the exact source, and publishes through PyPI Trusted Publishing.
The final job verifies the public files and a clean installation.

Configure the publisher and GitHub settings first; see
[automated publishing and recovery](docs/publishing.md). No PyPI API token is
needed. Release PRs are not auto-merged, and setting up the workflow itself
does not upload a package.

## License

MIT for this independently written HTTP client. Fish Speech server code, model
weights, and generated content remain subject to their respective terms; this
package does not bundle the server or model weights.
