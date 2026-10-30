// Run pipeline stages on the dedicated build agent.
pipeline {
    agent {
        label 'finsecure-agent'
    }

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }
    

        stage('Build') {
            steps {
                sh 'docker build -f jenkins/Dockerfile.test -t finsecure-pay-test:$BUILD_NUMBER .'
            }
        }

        stage('Test') {
            steps {
                sh 'docker run --rm finsecure-pay-test:$BUILD_NUMBER'
            }
        }
        
        stage('Package') {
            steps {
                sh '''
                    mkdir -p dist
                    git archive \
                    --format=tar.gz \
                    --output=dist/finsecure-pay-${BUILD_NUMBER}.tar.gz \
                    HEAD \
                    app.py transaction.py requirements.txt Dockerfile k8s README.md
                '''

                archiveArtifacts(
                    artifacts: "dist/finsecure-pay-${env.BUILD_NUMBER}.tar.gz",
                    fingerprint: true
                )
            }
        }

        stage('Security Checks') {
            steps {
                sh '''
                    docker run --rm finsecure-pay-test:$BUILD_NUMBER \
                    python -m bandit app.py transaction.py
                '''
            }
        }
    }

    triggers {
        pollSCM('H/2 * * * *')
    }
}