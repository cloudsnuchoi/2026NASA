FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 TZ=Asia/Seoul
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bridge.py .
# Repo docs + members.tsv are mounted read-only at /repo; state at /state (see infra/RUNBOOK.md).
ENV REPO_DIR=/repo MEMBERS_TSV=/repo/infra/chat/members.tsv STATE_PATH=/state/context.json
ENTRYPOINT ["python", "bridge.py", "--env", "/dev/null"]
