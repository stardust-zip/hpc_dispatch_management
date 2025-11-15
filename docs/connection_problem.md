# Connection problem

## Behavior
(Postman)
1. `GET http://0.0.0.0:8888/dispatches`
2. Response:
```json
{
    "detail": "Could not connect to user service: [Errno -2] Name or service not known"
}
```

## User service
### docker-compose.yaml
```yaml
services:
    app:
        build:
            context: .
            dockerfile: Dockerfile
        container_name: hpc_app
        restart: unless-stopped
        working_dir: /var/www
        volumes:
            - .:/var/www
        networks:
            - hpc_network

    webserver:
        image: nginx:alpine
        container_name: hpc_web
        restart: unless-stopped
        ports:
            - "8082:80"
        volumes:
            - .:/var/www
            - ./nginx.conf:/etc/nginx/conf.d/default.conf
        depends_on:
            - app
        networks:
            - hpc_network

    db:
        image: mysql:8.0
        container_name: hpc_db
        restart: unless-stopped
        environment:
            MYSQL_ROOT_PASSWORD: root
            MYSQL_DATABASE: system_services
            MYSQL_USER: system_services
            MYSQL_PASSWORD: hpc123
        ports:
            - "3307:3306"
            - "3307:3306"
        volumes:
            - db_data:/var/lib/mysql
        networks:
            - hpc_network

    redis:
        image: redis:alpine
        container_name: hpc_redis
        restart: unless-stopped
        ports:
            - "6380:6379"
        networks:
            - hpc_network

    reverb:
        build:
            context: .
            dockerfile: Dockerfile
        container_name: hpc_reverb
        command: php artisan reverb:start
        working_dir: /var/www
        volumes:
            - .:/var/www
        depends_on:
            - app
            - redis
        ports:
            - "8081:8080"
        networks:
            - hpc_network

    zookeeper:
        image: confluentinc/cp-zookeeper:latest
        container_name: hpc_zookeeper
        restart: unless-stopped
        healthcheck:
          test: ["CMD", "bash", "-c", "echo 'ruok' | nc -w 2 localhost 2181"]
          interval: 10s
          timeout: 5s
          retries: 5
        environment:
            ZOOKEEPER_CLIENT_PORT: 2181
            ZOOKEEPER_TICK_TIME: 2000
        ports:
            - "2181:2181"
        networks:
            - hpc_network

    kafka:
        image: confluentinc/cp-kafka:6.2.10
        container_name: hpc_kafka
        restart: unless-stopped
        depends_on:
          zookeeper:
            condition: service_healthy
        ports:
          - "9092:9092" # Port for external connections
        environment:
          KAFKA_BROKER_ID: 1
          KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
          # --- START OF THE CORRECT CONFIGURATION ---
          KAFKA_LISTENERS: INTERNAL://0.0.0.0:29092,EXTERNAL://0.0.0.0:9092
          KAFKA_ADVERTISED_LISTENERS: INTERNAL://kafka:29092,EXTERNAL://localhost:9092
          KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT
          KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
          # --- END OF THE CORRECT CONFIGURATION ---
          KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
          KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
          KAFKA_NUM_PARTITIONS: 3
          KAFKA_DEFAULT_REPLICATION_FACTOR: 1
        networks:
          - hpc_network

    queue:
        build:
            context: .
            dockerfile: Dockerfile
        container_name: hpc_queue
        restart: unless-stopped
        working_dir: /var/www
        volumes:
            - .:/var/www
        command: sh -c "while ! nc -z kafka 29092; do echo 'Waiting for Kafka...'; sleep 1; done; echo 'Kafka is up!'; php artisan queue:work --queue=emails --verbose --tries=3 --timeout=90"
        depends_on:
            - app
            - redis
        networks:
            - hpc_network

    queue_default:
        build:
            context: .
            dockerfile: Dockerfile
        container_name: hpc_queue_default
        restart: unless-stopped
        working_dir: /var/www
        volumes:
            - .:/var/www
        command: sh -c "while ! nc -z kafka 29092; do echo 'Waiting for Kafka...'; sleep 1; done; echo 'Kafka is up!'; php artisan queue:work --verbose --tries=3 --timeout=90"
        depends_on:
            - app
            - redis
        networks:
            - hpc_network

    kafka_consumer:
        build:
            context: .
            dockerfile: Dockerfile
        container_name: hpc_kafka_consumer
        restart: unless-stopped
        working_dir: /var/www
        volumes:
            - .:/var/www
        command: php artisan kafka:consume
        depends_on:
            - app
            - kafka
        networks:
            - hpc_network

networks:
    hpc_network:

volumes:
    db_data:
```

### .env
```env
APP_NAME="System Management"
APP_ENV=local
APP_KEY=base64:mcpsuBdzZrrNWgkeea8LsQGnKPMMFnwRBgPiwI68NXc=
APP_DEBUG=true
APP_URL=http://localhost:8080

LOG_CHANNEL=stack
LOG_DEPRECATIONS_CHANNEL=null
LOG_LEVEL=debug

DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=system_services
DB_USERNAME=system_services
DB_PASSWORD=hpc123

BROADCAST_DRIVER=reverb
CACHE_DRIVER=redis
FILESYSTEM_DISK=local
QUEUE_CONNECTION=redis
SESSION_DRIVER=redis
SESSION_LIFETIME=120
QUEUE_FAILED_DRIVER=database-uuids
CACHE_PREFIX=system_services
SESSION_PREFIX=system_services

MEMCACHED_HOST=127.0.0.1

REDIS_HOST=hpc_redis
REDIS_PASSWORD=null
REDIS_PORT=6379

MAIL_MAILER=smtp
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=dovananh145203@gmail.com
MAIL_PASSWORD=xmcmiigbugedgsyd
MAIL_ENCRYPTION=tls
MAIL_FROM_ADDRESS=dovananh145203@gmail.com
MAIL_FROM_NAME="System Service"


AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
AWS_BUCKET=
AWS_USE_PATH_STYLE_ENDPOINT=false

REVERB_APP_ID=local_app_id
REVERB_APP_KEY=local_app_key
REVERB_APP_SECRET=local_app_secret
REVERB_HOST=localhost
REVERB_PORT=8081
REVERB_SCHEME=http

PUSHER_APP_CLUSTER=mt1

VITE_APP_NAME="${APP_NAME}"

VITE_PUSHER_APP_KEY="${REVERB_APP_KEY}"
VITE_PUSHER_HOST="${REVERB_HOST}"
VITE_PUSHER_PORT="${REVERB_PORT}"
VITE_PUSHER_SCHEME="${REVERB_SCHEME}"

VITE_PUSHER_APP_CLUSTER="${PUSHER_APP_CLUSTER}"

JWT_SECRET=feufiwfiobdsfoiwehoasdfiuafasdhfbsdhjfgfbsdkvjbefheibsdf
JWT_ALGO=HS256
JWT_TTL=3600
JWT_REFRESH_TTL=20160

KAFKA_BROKERS=kafka:29092
```
