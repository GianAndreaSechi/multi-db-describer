FROM python:3.11-slim-bookworm

WORKDIR /app

# The installed CLI imports the package exposed by core as ``core.*``.
ENV PYTHONPATH=/app

COPY core/ /app/core/
COPY cli/ /app/cli/

# Install core first, then the CLI.  The latter has no dependencies other than
# the locally installed irides-core distribution.
RUN pip install --no-cache-dir -e /app/core \
 && pip install --no-cache-dir --no-deps -e /app/cli

ENTRYPOINT ["irides"]
CMD ["configurations"]
