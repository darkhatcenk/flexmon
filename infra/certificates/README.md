# TLS Certificates

This directory contains TLS certificates for FlexMON services.

## Auto-Generated Certificates

During installation, the following self-signed certificates are automatically generated:

- `server.key` - Private key for the API server
- `server.crt` - Self-signed certificate for the API server (valid 365 days)
- `ca.key` - Certificate Authority private key (for mTLS)
- `ca.crt` - Certificate Authority certificate (for mTLS)

## Using Custom Certificates

For production environments, you should replace the self-signed certificates with certificates from a trusted CA.

### Option 1: Upload via UI

1. Log in as `platform_admin`
2. Navigate to **Settings** → **Security**
3. Upload your certificate files:
   - Server Certificate (`.crt` or `.pem`)
   - Private Key (`.key`)
   - CA Certificate (for mTLS, optional)
4. Click **Apply & Restart**

The system will validate and apply your certificates.

### Option 2: Manual Replacement

Replace the following files before starting services:

```bash
# Backup existing certs
mv certificates/server.crt certificates/server.crt.backup
mv certificates/server.key certificates/server.key.backup

# Copy your certificates
cp /path/to/your/certificate.crt certificates/server.crt
cp /path/to/your/private.key certificates/server.key

# Set permissions
chmod 644 certificates/server.crt
chmod 600 certificates/server.key

# Restart services
make restart
```

## Mutual TLS (mTLS)

To enable mutual TLS authentication:

1. Generate client certificates signed by the CA
2. Set `ENABLE_MTLS=true` in `.env`
3. Restart services: `make restart`
4. Configure agents with client certificates

### Generating Client Certificates

```bash
# Generate client private key
openssl genrsa -out client.key 4096

# Generate certificate signing request
openssl req -new -key client.key -out client.csr \
  -subj "/C=TR/ST=Istanbul/O=CloudFlex/CN=agent-hostname"

# Sign with CA
openssl x509 -req -days 365 -in client.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt

# Clean up
rm client.csr
```

## Certificate Expiration

Self-signed certificates are valid for 365 days. Monitor expiration:

```bash
# Check expiration date
openssl x509 -in certificates/server.crt -noout -enddate
```

## Security Notes

- **Never commit private keys to version control**
- Keep `ca.key` secure (needed for mTLS)
- Rotate certificates before expiration
- Use strong passwords for key encryption
- Monitor certificate expiration alerts

## Troubleshooting

### Certificate Validation Errors

If clients cannot connect:

```bash
# Verify certificate
openssl x509 -in certificates/server.crt -text -noout

# Test TLS connection
openssl s_client -connect localhost:8000 -CAfile certificates/ca.crt
```

### Permission Issues

Ensure proper permissions:

```bash
chmod 600 certificates/*.key
chmod 644 certificates/*.crt
```

## References

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [Let's Encrypt](https://letsencrypt.org/) - Free TLS certificates
- [FlexMON Security Guide](../docs/SECURITY.md)
