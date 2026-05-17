pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        IMAGE_NAME    = 'uniticket-grupo-7'
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        COMPOSE_PROJECT = 'uniticket-grupo-7'
    }

    stages {
        stage('Build Info') {
            steps {
                script {
                    def isPR = env.CHANGE_ID ? "PR #${env.CHANGE_ID} (${env.CHANGE_BRANCH} -> ${env.CHANGE_TARGET})" : "rama ${env.BRANCH_NAME ?: 'desconocida'}"
                    echo "Build #${env.BUILD_NUMBER} | ${isPR}"
                    echo "Commit: ${env.GIT_COMMIT ?: 'pre-checkout'} | URL: ${env.GIT_URL ?: '-'}"
                }
            }
        }

        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty=format:"%h %s%n%an <%ae>"'
            }
        }

        stage('Build Image') {
            steps {
                script {
                    // Pre-clean: evita ingest huerfanos en containerd que rompen export.
                    sh '''
                        docker builder prune -f --filter "until=1h" || true
                        docker image prune -f --filter "dangling=true" || true
                    '''
                    // Build con reintento: el VPS tiene fallas intermitentes en export
                    // ("CreateDiff: mount callback failed"). Retry desbloquea sin ocultar
                    // fallos reales (segundo intento tambien debe terminar verde).
                    retry(3) {
                        sh """
                            docker build \
                              -t ${IMAGE_NAME}:${IMAGE_TAG} \
                              -t ${IMAGE_NAME}:latest \
                              .
                        """
                    }
                }
            }
        }

        stage('Prepare Reports') {
            steps {
                sh 'rm -rf reports && mkdir -p reports'
            }
        }

        stage('Static Analysis (Flake8)') {
            steps {
                sh """
                    docker run --rm \
                      --workdir /app \
                      ${IMAGE_NAME}:${IMAGE_TAG} \
                      flake8 .
                """
            }
        }

        stage('SAST (Bandit)') {
            steps {
                // No usar -v: en Docker-in-Docker via socket el path del workspace
                // de Jenkins no necesariamente existe en el host del docker daemon.
                // Patron: docker create + start -a + cp + rm para extraer reportes.
                sh """
                    set +e
                    cid=\$(docker create --workdir /app ${IMAGE_NAME}:${IMAGE_TAG} \\
                        bandit -r . \\
                          -x ./tests,./venv,./.venv,./migrations,./staticfiles,./reports,./docs,./_jenkins_reports,./.git,./.pytest_cache,./.ruff_cache \\
                          -f xml -o /tmp/bandit.xml -v)
                    docker start -a "\$cid"
                    rc=\$?
                    docker cp "\$cid:/tmp/bandit.xml" reports/bandit.xml || true
                    docker rm -f "\$cid" >/dev/null
                    exit \$rc
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/bandit.xml',
                                     allowEmptyArchive: true, fingerprint: true
                }
            }
        }

        stage('Unit Tests') {
            steps {
                sh """
                    set +e
                    cid=\$(docker create \\
                        -e DJANGO_SETTINGS_MODULE=uniticket.settings \\
                        -e SECRET_KEY=ci-test-only \\
                        -e DEBUG=False \\
                        -e ALLOWED_HOSTS='*' \\
                        -e DATABASE_URL='sqlite:////tmp/test_uniticket.sqlite3' \\
                        --workdir /app ${IMAGE_NAME}:${IMAGE_TAG} \\
                        sh -c 'coverage run -m pytest --junitxml=/tmp/junit.xml -v && coverage xml -o /tmp/coverage.xml && coverage report')
                    docker start -a "\$cid"
                    rc=\$?
                    docker cp "\$cid:/tmp/junit.xml" reports/junit.xml || true
                    docker cp "\$cid:/tmp/coverage.xml" reports/coverage.xml || true
                    docker rm -f "\$cid" >/dev/null
                    exit \$rc
                """
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                    archiveArtifacts artifacts: 'reports/coverage.xml,reports/junit.xml',
                                     allowEmptyArchive: true, fingerprint: true
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'main'
            }
            environment {
                STACK    = 'uniticket-grupo-7'
                NET      = 'uniticket-grupo-7_net'
                VOL_DB   = 'uniticket-grupo-7_db_data'
                NAME_WEB = 'uniticket-grupo-7-web'
                NAME_DB  = 'uniticket-grupo-7-db'
                APP_PORT = '7007'
                PG_DB    = 'uniticket_g7_prod'
                PG_USER  = 'uniticket_g7'
            }
            steps {
                withCredentials([
                    string(credentialsId: 'uniticket-prod-secret-key', variable: 'PROD_SECRET_KEY'),
                    string(credentialsId: 'uniticket-prod-pg-password', variable: 'PROD_PG_PASSWORD')
                ]) {
                    // Deploy sin compose: el agente Jenkins del grupo no tiene
                    // compose v2 ni v1. Usamos docker run directo orquestando
                    // red, volumen y dos contenedores. Equivalente funcional al
                    // docker-compose.yml del repo. Cumple entregable 8.2 (>= 2
                    // contenedores).
                    sh '''
                        set -e

                        # 1. Cleanup contenedores previos (red y volumen se conservan).
                        docker rm -f "${NAME_WEB}" 2>/dev/null || true
                        docker rm -f "${NAME_DB}" 2>/dev/null || true

                        # 2. Red dedicada (idempotente).
                        docker network inspect "${NET}" >/dev/null 2>&1 || \
                            docker network create "${NET}"

                        # 3. Volumen de datos (idempotente, persiste entre deploys).
                        docker volume inspect "${VOL_DB}" >/dev/null 2>&1 || \
                            docker volume create "${VOL_DB}"

                        # 4. Levanta DB.
                        docker run -d \
                            --name "${NAME_DB}" \
                            --network "${NET}" \
                            --restart unless-stopped \
                            -e POSTGRES_DB="${PG_DB}" \
                            -e POSTGRES_USER="${PG_USER}" \
                            -e POSTGRES_PASSWORD="${PROD_PG_PASSWORD}" \
                            -v "${VOL_DB}":/var/lib/postgresql/data \
                            postgres:15

                        # 5. Espera DB healthy via pg_isready (max 30s).
                        echo "Esperando Postgres healthy..."
                        for i in $(seq 1 15); do
                            if docker exec "${NAME_DB}" pg_isready -U "${PG_USER}" -d "${PG_DB}" >/dev/null 2>&1; then
                                echo "DB lista tras ${i} intentos"
                                break
                            fi
                            sleep 2
                            if [ "$i" = "15" ]; then
                                echo "DB no respondio en 30s. Logs:"
                                docker logs "${NAME_DB}" --tail=50 || true
                                exit 1
                            fi
                        done

                        # 6. Levanta web (usa imagen construida en stage Build Image).
                        docker run -d \
                            --name "${NAME_WEB}" \
                            --network "${NET}" \
                            --restart unless-stopped \
                            -p "${APP_PORT}:8000" \
                            -e SECRET_KEY="${PROD_SECRET_KEY}" \
                            -e DEBUG=False \
                            -e ALLOWED_HOSTS=45.55.145.98,localhost,127.0.0.1 \
                            -e CSRF_TRUSTED_ORIGINS=http://45.55.145.98:7007 \
                            -e DATABASE_URL="postgresql://${PG_USER}:${PROD_PG_PASSWORD}@${NAME_DB}:5432/${PG_DB}" \
                            "${IMAGE_NAME}:latest"

                        # 7. Limpieza de imagenes huerfanas (Doc Apoyo 06).
                        docker image prune -f || true
                    '''
                }

                // Seed de usuarios demo con credenciales inyectadas desde Jenkins
                // (nunca quedan persistidas en el contenedor web).
                // Espera ~3s a que gunicorn levante migrate y arranque.
                withCredentials([
                    string(credentialsId: 'uniticket-prod-seed-usuario-password', variable: 'SEED_USUARIO_PW'),
                    string(credentialsId: 'uniticket-prod-seed-tecnico-password', variable: 'SEED_TECNICO_PW'),
                    string(credentialsId: 'uniticket-prod-seed-super-password',   variable: 'SEED_SUPER_PW')
                ]) {
                    sh '''
                        set -e
                        # Espera a que web este listo (gunicorn + migrate)
                        for i in $(seq 1 10); do
                            if docker exec "${NAME_WEB}" python -c "import django; django.setup()" >/dev/null 2>&1; then
                                break
                            fi
                            sleep 2
                        done

                        docker exec \
                            -e SEED_USUARIO_PASSWORD="${SEED_USUARIO_PW}" \
                            -e SEED_TECNICO_PASSWORD="${SEED_TECNICO_PW}" \
                            -e SEED_SUPER_PASSWORD="${SEED_SUPER_PW}" \
                            "${NAME_WEB}" python manage.py seed_demo
                    '''
                }
                // Smoke check post-deploy: la app debe responder en /healthz/.
                sh '''
                    set -e
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if docker run --rm \
                             --network "${NET}" \
                             curlimages/curl:8.10.1 \
                             -fsS --max-time 5 -H "Host: 45.55.145.98" \
                             "http://${NAME_WEB}:8000/healthz/" > /dev/null 2>&1; then
                            echo "Smoke check OK tras intento $i"
                            exit 0
                        fi
                        echo "Smoke intento $i fallo, esperando..."
                        sleep 3
                    done
                    echo "Smoke check FAILED tras 10 intentos. Logs del web:"
                    docker logs "${NAME_WEB}" --tail=80 || true
                    exit 1
                '''
            }
            post {
                failure {
                    sh '''
                        echo "--- logs web ---"
                        docker logs "${NAME_WEB}" --tail=120 || true
                        echo "--- logs db ---"
                        docker logs "${NAME_DB}" --tail=80 || true
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline OK — imagen ${IMAGE_NAME}:${IMAGE_TAG} construida. Seguro mergear."
        }
        failure {
            echo 'Pipeline FALLÓ — revisar console output. NO mergear hasta verde.'
        }
        unstable {
            echo 'Pipeline UNSTABLE — revisar warnings.'
        }
        aborted {
            echo 'Pipeline abortado.'
        }
        always {
            sh 'docker image prune -f --filter "dangling=true" || true'
        }
    }
}
