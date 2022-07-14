FROM ubuntu:18.04
RUN useradd -d /home/hwMindX -u 9000 -m -s  /usr/sbin/nologin hwMindX &&\
    usermod root -s /usr/sbin/nologin
COPY ./esn  /mindx-dl/
COPY ./license-manager  /mindx-dl/
COPY ./lib  /mindx-dl/lib
COPY ./liblic_release.so  /mindx-dl/
# maybe need config apt source and proxy by yourself here
RUN apt-get update && apt-get install -y sudo
RUN echo  "hwMindX ALL=(ALL) NOPASSWD: /mindx-dl/esn" >> /etc/sudoers
RUN chown -R hwMindX:hwMindX /mindx-dl/ &&\
    # the parent directory owner need be the max premissions user
    chown root:root /mindx-dl/ &&\
    chown -R root:root /mindx-dl/esn  &&\
    chmod 750 -R /home/hwMindX &&\
    # hwMindX and root user need execute program in the directory
    chmod 755 /mindx-dl &&\
    chmod 700 /mindx-dl/lib &&\
    chmod 500 /mindx-dl/* &&\
    # hwMindX need check the sha256 of esn
    chmod 504 /mindx-dl/esn &&\
    chmod 500 /mindx-dl/lib/* &&\
    echo 'umask 027' >> /etc/profile && \
    echo 'source /etc/profile' >> ~/.bashrc
ENV LD_LIBRARY_PATH=/mindx-dl:/mindx-dl/lib:${LD_LIBRARY_PATH}
USER hwMindX
CMD /mindx-dl/license-manager
