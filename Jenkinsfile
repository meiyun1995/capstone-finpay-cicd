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
    }

    triggers {
        pollSCM('H/2 * * * *')
    }
}