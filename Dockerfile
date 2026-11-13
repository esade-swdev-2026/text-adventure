FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv

WORKDIR /app
# Dependencies first: this layer is rebuilt only when pyproject.toml or uv.lock change,
# so a code change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Then our own package. pyproject.toml names README.md, so the build needs it.
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev

# Run as an ordinary user, not root. The game only reads its files, so it needs no
# writable folder.
RUN useradd --create-home app
USER app

ENV PATH="/app/.venv/bin:$PATH"
# docker run -t sets TERM=xterm, which makes rich fall back to 16 colours.
# The noir palette needs 256, which every modern terminal supports.
ENV TERM=xterm-256color
ENTRYPOINT ["text-adventure"]
CMD ["--help"]
