ARG SPARK_BASE_IMAGE=bitnamilegacy/spark:3.5.1
FROM ${SPARK_BASE_IMAGE}

USER root
COPY certs /usr/local/share/ca-certificates/local
RUN if command -v update-ca-certificates >/dev/null 2>&1; then update-ca-certificates; fi \
    && find /usr/local/share/ca-certificates/local -name '*.crt' -type f -print | while read -r cert; do \
        alias="local-$(basename "$cert" .crt | tr -c 'A-Za-z0-9_' '_')"; \
        /opt/bitnami/java/bin/keytool -importcert -noprompt -trustcacerts \
          -alias "$alias" \
          -file "$cert" \
          -keystore /opt/bitnami/java/lib/security/cacerts \
          -storepass changeit || true; \
      done

USER 1001
