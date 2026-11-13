# Lesson 9: Layer 5: Encrypted, Verified Traffic Between Services

Since Part 3, every request to Weaviate needs an API key. But those requests travel over the private Docker network as **plain HTTP**. Anyone who can watch that traffic sees the keys in the `Authorization` header and every document the chatbot retrieves.

"It never leaves the Docker network" is a reasonable argument on one laptop. It is a weak one in production, where services run on different machines, networks are shared, and an attacker inside any container on the network could watch or alter traffic.

---

## See the current state

With Layers 1 to 4 on, ask Weaviate if it is ready over plain HTTP from inside the API container:

```bash
bin/harden.sh 4
docker exec rag-api python -c "import httpx; print(httpx.get('http://weaviate:8080/v1/.well-known/ready').status_code)"
```

```
200
```

Weaviate answers unencrypted requests. So does every request the API makes, keys included: each one carries `Authorization: Bearer <key>` in plain text.

---

## The certificates

`bin/setup_secrets.sh` created a small **private certificate authority** (CA) and used it to sign a certificate for Weaviate:

```bash
openssl verify -CAfile secrets/tls_ca.crt secrets/weaviate_server.crt
openssl x509 -in secrets/weaviate_server.crt -noout -text | grep -A1 "Alternative Name"
```

```
secrets/weaviate_server.crt: OK
            X509v3 Subject Alternative Name:
                DNS:weaviate
```

- The CA is the thing the API **trusts**. Anything the CA signed is accepted
- Weaviate's certificate is valid for the name `weaviate`, which is exactly the hostname the API connects to
- `secrets/tls_ca.key` (the CA's private key) is never mounted into any container. Whoever holds it can create certificates the API would trust

---

## Read the layer

Open `hardening/05-internal-tls.yml`.

### Weaviate turns on TLS

```yaml
  weaviate:
    command: ["--host", "0.0.0.0", "--scheme", "https", "--tls-host", "0.0.0.0", "--tls-port", "8080",
              "--tls-certificate", "/run/secrets/weaviate_server_crt", "--tls-key", "/run/secrets/weaviate_server_key"]
```

These are Weaviate's own startup options. `--scheme https` means it serves **only** HTTPS, and `--tls-port 8080` keeps the same port, so nothing else has to change. There is no plain-HTTP listener left to turn off.

The health check runs inside the Weaviate container and only asks "are you ready?", so it skips the certificate check (`--no-check-certificate`). The API never does.

### The API verifies Weaviate

```yaml
  ingestion-api:
    environment:
      WEAVIATE_URL: "https://weaviate:8080"
      WEAVIATE_CA_CERT: /run/secrets/tls_ca_crt
```

`ingestion-api/app/db.py` passes `WEAVIATE_CA_CERT` to the HTTP client as the **only** certificate authority it trusts. `weaviate-init` gets the same two settings.

| Client setting | Encrypted? | Checks the certificate? | Checks the hostname? |
|---|:-:|:-:|:-:|
| `http://` (Layers 0 to 4) | no | no | no |
| `https://`, certificate checking turned off | yes | no | no |
| `https://`, trusting only the lab CA (this layer) | yes | yes | yes |

Only the last row stops an attacker who can intercept traffic from pretending to be the database. Encryption without verification just means you have an encrypted conversation with whoever answered.

---

## Apply it

```bash
bin/harden.sh 5
bin/smoke_test.sh
```

## Verify the connection is encrypted and verified

Make three requests from inside the API container: plain HTTP, HTTPS trusting the lab CA, and HTTPS trusting only the usual public authorities:

```bash
docker exec rag-api python -c "
import httpx
for url, v, label in [('http://weaviate:8080/v1/.well-known/ready', True, 'plain http'),
                      ('https://weaviate:8080/v1/.well-known/ready', '/run/secrets/tls_ca_crt', 'https, lab CA'),
                      ('https://weaviate:8080/v1/.well-known/ready', True, 'https, public CAs')]:
    try:
        r = httpx.get(url, verify=v, timeout=5); print(f'{label:<18} {r.status_code} {r.text!r}')
    except Exception as e:
        print(f'{label:<18} refused: {str(e)[:70]}')
"
```

```
plain http         400 'Client sent an HTTP request to an HTTPS server.\n'
https, lab CA      200 ''
https, public CAs  refused: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable
```

- **Plain HTTP is refused.** Weaviate answers only to say it speaks HTTPS now
- **The lab CA works.** This is what the API and `bin/weaviate.sh` use
- **A public CA does not.** No outside authority vouches for this certificate, and none should

## Verify an impostor is refused (expected to fail)

Hostname checking matters too. Connect to the same Weaviate, with the right CA, but by its IP address instead of its name:

```bash
IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' rag-weaviate)
docker exec rag-api python -c "
import httpx
try:
    httpx.get('https://$IP:8080/v1/.well-known/ready', verify='/run/secrets/tls_ca_crt', timeout=5); print('CONNECTED (bad)')
except Exception as e:
    print('refused:', str(e)[:110])
"
```

```
refused: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: IP address mismatch, certificate is not valid for '172.18.0.3'
```

The certificate says `weaviate`, so the client refuses anything else, even the right server under a different name. An attacker with a certificate for some other name gets the same answer.

## Audit

```bash
python3 bin/audit.py
```

The score does not change: TLS is not on the checklist, because the checklist looks at containers, not connections. Not everything important fits on one scorecard.

Next: [Layer 6: Scan and Pin Your Images](10-scan-and-pin.md)
