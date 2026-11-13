FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv

WORKDIR /app
COPY . .
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
# docker run -t sets TERM=xterm, which makes rich fall back to 16 colours.
# The noir palette needs 256, which every modern terminal supports.
ENV TERM=xterm-256color
ENTRYPOINT ["text-adventure"]
CMD ["--help"]
