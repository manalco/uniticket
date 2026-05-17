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
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --pretty=format:"%h %s%n%an <%ae>"'
            }
        }

        stage('Build Image') {
            steps {
                script {
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

    post {
        success {
            echo "Pipeline OK — imagen ${IMAGE_NAME}:${IMAGE_TAG} construida."
        }
        failure {
            echo 'Pipeline FALLÓ — revisar console output antes de reintentar.'
        }
        always {
            sh 'docker image prune -f --filter "dangling=true" || true'
        }
    }
}
