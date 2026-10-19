# Training2-D1-Lab: the interoperability lab on IRIS for Health Community.
#
# Base: the extended-maintenance (EM) release, pinned by its multi-arch digest,
# so every attendee gets the same build on Intel and Apple silicon.
# Everything this image adds is under /opt/insurligent: your classes (src/),
# the CPF merge file that makes the INSURLIGENT namespace, and the first-start
# setup code.
#
# No IRIS commands run at build time. The CPF merge makes the namespace (before
# the superserver opens). The -a hook loads the classes (after IRIS is live).
FROM containers.intersystems.com/intersystems/irishealth-community:latest-em@sha256:c4d31e2388a7e29762fcd7d9f416ef16a89203481152beabeb740c5a9dafc2c0

USER root

COPY src /opt/insurligent/src
COPY setup /opt/insurligent/setup
COPY merge.cpf /opt/insurligent/merge.cpf

# irisowner is uid 51773 in every IRIS image.
RUN chmod +x /opt/insurligent/setup/after-start.sh \
 && chown -R 51773:51773 /opt/insurligent

USER 51773
