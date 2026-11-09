# Per-job sandbox image. Contains only CPython's standard library and the trusted harness.
# No package manager use at runtime, no network, read-only root filesystem (set by the runner).
FROM python:3.12-slim
RUN rm -rf /usr/local/lib/python3.12/ensurepip /usr/local/lib/python3.12/site-packages/pip* /usr/local/bin/pip* \
 && mkdir -p /sandbox
COPY harness.py driver.py /sandbox/
RUN chmod 0555 /sandbox && chmod 0444 /sandbox/*.py
USER 65534:65534
ENTRYPOINT ["/usr/local/bin/python3", "-I", "-S", "/sandbox/harness.py"]
