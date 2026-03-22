FROM caddy:latest

COPY Caddyfile /etc/caddy/Caddyfile
COPY hostflow-frontend/dist /var/www/hostflow-frontend
