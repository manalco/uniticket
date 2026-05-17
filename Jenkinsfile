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
                // Project name vía env var en vez de -p (mas compatible con
                // distintas versiones del CLI compose en el VPS).
                COMPOSE_PROJECT_NAME = 'uniticket-grupo-7'
            }
            steps {
                withCredentials([
                    string(credentialsId: 'uniticket-prod-secret-key', variable: 'PROD_SECRET_KEY'),
                    string(credentialsId: 'uniticket-prod-pg-password', variable: 'PROD_PG_PASSWORD')
                ]) {
                    sh '''
                        # Genera .env transitorio para compose con valores de prod.
                        # Se borra al final del stage (no debe persistir en workspace).
                        cat > .env <<EOF
SECRET_KEY=${PROD_SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=45.55.145.98,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://45.55.145.98:7007
POSTGRES_DB=uniticket_g7_prod
POSTGRES_USER=uniticket_g7
POSTGRES_PASSWORD=${PROD_PG_PASSWORD}
EOF
                        # Diagnostico + seleccion del binario compose
                        # (v2 plugin moderno o v1 standalone).
                        if docker compose version > /dev/null 2>&1; then
                            COMPOSE="docker compose"
                        elif docker-compose --version > /dev/null 2>&1; then
                            COMPOSE="docker-compose"
                        else
                            echo "ERROR: ni 'docker compose' ni 'docker-compose' disponibles en el agente"
                            exit 1
                        fi
                        echo "Usando: $COMPOSE (project=$COMPOSE_PROJECT_NAME)"

                        # Despliegue (Doc Apoyo 06). Project name via env var.
                        $COMPOSE down || true
                        $COMPOSE up -d --build
                        docker image prune -f

                        # No dejar secretos en workspace de Jenkins.
                        rm -f .env
                    '''
                }
                // Smoke check post-deploy: la app debe responder en /healthz/.
                sh '''
                    set -e
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if docker run --rm \
                             --network ${COMPOSE_PROJECT_NAME}_uniticket_net \
                             curlimages/curl:8.10.1 \
                             -fsS --max-time 5 -H "Host: 45.55.145.98" \
                             http://web:8000/healthz/ > /dev/null 2>&1; then
                            echo "Smoke check OK tras intento $i"
                            exit 0
                        fi
                        echo "Smoke intento $i fallo, esperando..."
                        sleep 3
                    done
                    echo "Smoke check FAILED tras 10 intentos. Logs del web:"
                    if docker compose version > /dev/null 2>&1; then
                        docker compose logs web --tail=80 || true
                    else
                        docker-compose logs web --tail=80 || true
                    fi
                    exit 1
                '''
            }
            post {
                failure {
                    sh '''
                        if docker compose version > /dev/null 2>&1; then
                            docker compose logs --tail=120 || true
                        else
                            docker-compose logs --tail=120 || true
                        fi
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
