# Test tooling: the Python package, Nextflow and nf-test on one image.
FROM eclipse-temurin:17-jre-noble

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# CalliNGS-NF still needs the `phase` operator, so the image pins a Nextflow that has it.
ENV NXF_VER=24.04.4 NXF_HOME=/opt/nextflow
RUN curl -fsSL https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin/ \
    && nextflow -version \
    && curl -fsSL https://get.nf-test.com | bash -s 0.9.5 \
    && mv nf-test /usr/local/bin/

WORKDIR /opt/nf-retrofit
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python3 -m pip install --no-cache-dir --break-system-packages .

ENTRYPOINT ["nf-retrofit"]
