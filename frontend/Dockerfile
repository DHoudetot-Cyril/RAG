FROM nginx:alpine

ARG LEVEL=niveau1

# Copy static files
COPY ${LEVEL} /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
