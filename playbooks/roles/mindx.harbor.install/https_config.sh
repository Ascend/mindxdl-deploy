cd /tmp
rm -rf tmp_cert
mkdir -p -m 700 tmp_cert
cd tmp_cert

openssl genrsa -out ca.key 4096

openssl req -x509 -new -nodes -sha512 -days 3650 -subj "/C=CN/ST=Chengdu/L=Chengdu/O=example/OU=Personal/CN=harbor" -key ca.key -out ca.crt

openssl genrsa -out harbor.key 4096

openssl req -sha512 -new -subj "/C=CN/ST=Chengdu/L=Chengdu/O=example/OU=Personal/CN=harbor" -key harbor.key -out harbor.csr

cat > v3.ext <<-EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP=192.168.56.10
EOF

openssl x509 -req -sha512 -days 3650 -extfile v3.ext -CA ca.crt -CAkey ca.key -CAcreateserial -in harbor.csr -out harbor.crt

mkdir -p -m 700 /data/cert
rm /data/cert/harbor.crt /data/cert/harbor.key
cp harbor.crt /data/cert/
cp harbor.key /data/cert/

openssl x509 -inform PEM -in harbor.crt -out harbor.cert

docker_harbor=/etc/docker/certs.d/192.168.56.10:7443
mkdir -p -m 700 ${docker_harbor}
rm ${docker_harbor}/harbor.cert ${docker_harbor}/harbor.key ${docker_harbor}/ca.crt
cp harbor.cert ${docker_harbor}
cp harbor.key ${docker_harbor}
cp ca.crt ${docker_harbor}

rm -rf tmp_cert

mkdir -p -m 700 /var/log/harbor

exit 0
