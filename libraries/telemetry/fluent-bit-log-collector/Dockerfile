FROM debian:bullseye

RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    gnupg
COPY ./config.conf /etc/fluent-bit/config.conf
COPY ./run.sh /run.sh
RUN chmod +x /run.sh

RUN curl https://packages.fluentbit.io/fluentbit.key | gpg --dearmor > /usr/share/keyrings/fluentbit-keyring.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/fluentbit-keyring.gpg] https://packages.fluentbit.io/debian/bullseye bullseye main" | tee /etc/apt/sources.list.d/fluent.list
RUN apt-get update && apt-get install -y fluent-bit

CMD [ "/run.sh" ]
