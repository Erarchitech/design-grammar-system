FROM python:3.11-slim

# OS deps: build tooling + headless JRE (HermiT via owlready2 shells out to java).
# NOTE: python:3.11-slim is Debian trixie, which dropped openjdk-17-jre-headless from
# its apt repos. Falling back to openjdk-21-jre-headless per the 820 spike (proven
# compatible — HermiT's floor is Java 1.5+). See SUMMARY for the substitution note.
RUN apt-get update && apt-get install -y \
    build-essential \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Service code
COPY . .

# Launch
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
