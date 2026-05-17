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
                sh """
                    docker run --rm \
                      -v "${env.WORKSPACE}/reports":/reports \
                      --workdir /app \
                      ${IMAGE_NAME}:${IMAGE_TAG} \
                      bandit -r . \
                        -x ./tests,./venv,./.venv,./migrations,./staticfiles,./reports,./docs,./_jenkins_reports,./.git,./.pytest_cache,./.ruff_cache \
                        -f xml -o /reports/bandit.xml \
                        -v
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
                    docker run --rm \
                      -v "${env.WORKSPACE}/reports":/reports \
                      -e DJANGO_SETTINGS_MODULE=uniticket.settings \
                      -e SECRET_KEY=ci-test-only \
                      -e DEBUG=False \
                      -e ALLOWED_HOSTS='*' \
                      -e DATABASE_URL='sqlite:////tmp/test_uniticket.sqlite3' \
                      --workdir /app \
                      ${IMAGE_NAME}:${IMAGE_TAG} \
                      sh -c 'coverage run -m pytest --junitxml=/reports/junit.xml -v && coverage xml -o /reports/coverage.xml && coverage report'
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
                        # Despliegue del Documento de Apoyo 06:
                        docker compose -p uniticket-grupo-7 down || true
                        docker compose -p uniticket-grupo-7 up -d --build
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
                             --network uniticket-grupo-7_uniticket_net \
                             curlimages/curl:8.10.1 \
                             -fsS --max-time 5 -H "Host: 45.55.145.98" \
                             http://web:8000/healthz/ > /dev/null 2>&1; then
                            echo "Smoke check OK tras intento $i"
                            exit 0
                        fi
                        echo "Smoke intento $i fallo, esperando..."
                        sleep 3
                    done
                    echo "Smoke check FAILED tras 10 intentos. Logs:"
                    docker compose -p uniticket-grupo-7 logs web --tail=80 || true
                    exit 1
                '''
            }
            post {
                failure {
                    sh 'docker compose -p uniticket-grupo-7 logs --tail=120 || true'
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
