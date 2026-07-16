# DEV-ONLY signing fixture — DO NOT TRUST, DO NOT SHIP

`sprig-dev-TEST-ONLY.key` / `.pub` are an **unencrypted, committed** minisign
keypair used exclusively by the smoke gates (`make sprig_signing`) to prove the
sign→verify mechanism end to end. The private key is public by definition; a
signature from it proves nothing.

Production signing uses a real keypair that is NEVER in this repo:

```bash
# [MANUALLY] one-time, on the operator's machine; passphrase in the password manager
docker run --rm -it -v "$HOME/sage-keys:/keys" alpine:3.20 sh -c \
  "apk add --no-cache minisign && minisign -G -p /keys/sprig.pub -s /keys/sprig.key"
```

Then sign + republish the catalog (`SIGN_KEY=~/sage-keys/sprig.key make sprig_sign`),
pin the `.pub`'s base64 line as `_DEFAULT_PUBKEY` in
`app/backend/sage_is_ai/sprigs/artifact.py`, and flip catalog entries to
`signed: True`.

Anyone can verify a published artifact with the stock CLI:

```bash
minisign -Vm sprig-<name>.tar.zst -P <the public key line>
```
