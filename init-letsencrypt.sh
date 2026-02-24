#!/bin/bash

if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: docker is not installed.' >&2
  exit 1
fi

domains=(meshify.sytes.net)
rsa_key_size=4096
data_path="./cert-data"
email="galiottonicolo@gmail.com"
staging=0 # Set to 1 if you're testing your setup to avoid hitting request limits

if [ -d "$data_path/conf/live/${domains[0]}" ]; then
  read -p "Existing data found for ${domains[0]}. Continue and replace existing certificate? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi

if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nodejs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
  echo
fi

echo "### Creating dummy certificate for ${domains[0]} ..."
path="/etc/letsencrypt/live/${domains[0]}"
mkdir -p "$data_path/conf/live/${domains[0]}"
docker compose -f wpex-stack.yml run --rm --entrypoint "openssl" certbot req -x509 -nodes -newkey rsa:$rsa_key_size -days 1 -keyout "$path/privkey.pem" -out "$path/fullchain.pem" -subj "/CN=localhost"
echo

echo "### Starting nginx ..."
docker compose -f wpex-stack.yml up --force-recreate -d nginx
echo

echo "### Waiting for Nginx to initialize ..."
sleep 3
echo

echo "### Deleting dummy certificate for ${domains[0]} ..."
docker compose -f wpex-stack.yml run --rm --entrypoint "sh" certbot -c "rm -Rf /etc/letsencrypt/live/${domains[0]} && rm -Rf /etc/letsencrypt/archive/${domains[0]} && rm -Rf /etc/letsencrypt/renewal/${domains[0]}.conf"
echo


echo "### Requesting Let's Encrypt certificate for ${domains[0]} ..."
#Join $domains to -d args
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Select appropriate email arg
case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

# Enable staging mode if needed
if [ $staging != "0" ]; then staging_arg="--staging"; fi

docker compose -f wpex-stack.yml run --rm --entrypoint "certbot" certbot certonly --webroot -w /var/www/certbot $staging_arg $email_arg $domain_args --rsa-key-size $rsa_key_size --agree-tos --force-renewal
echo

echo "### Reloading nginx ..."
docker compose -f wpex-stack.yml exec nginx nginx -s reload
