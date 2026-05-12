FROM node:20-slim AS builder

# Accept (but currently ignore) the fingerprint build-arg passed by
# build-and-push-images.sh. The frontend build does not need extra-CA injection
# today; declaring the ARG silences podman's "build args were not consumed"
# warning and reserves the slot for future cert injection if needed.
ARG EXTRA_CA_FINGERPRINT=none

WORKDIR /app

COPY package*.json .
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
