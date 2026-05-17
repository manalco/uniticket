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
