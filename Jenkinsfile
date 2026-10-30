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
    }
    
    triggers {
        pollSCM('H/2 * * * *')
    }
}