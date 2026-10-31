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

        stage('Container Build') {
            steps {
                sh '''
                    docker build \
                    --platform linux/amd64 \
                    -t cmyaa/finsecure-pay:build-${BUILD_NUMBER} \
                    .

                    docker image inspect \
                    cmyaa/finsecure-pay:build-${BUILD_NUMBER} \
                    --format '{{.Os}}/{{.Architecture}}'
                '''
            }
        }    

        stage('Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKERHUB_USERNAME',
                        passwordVariable: 'DOCKERHUB_TOKEN'
                    )
                ]) {
                    sh '''
                        set +x
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT

                        printf '%s' "$DOCKERHUB_TOKEN" |
                        docker login \
                            --username "$DOCKERHUB_USERNAME" \
                            --password-stdin

                        docker push cmyaa/finsecure-pay:build-${BUILD_NUMBER}
                    '''
                }
            }
        }

    stage('Deploy') {
        steps {
            withCredentials([
                file(
                    credentialsId: 'aks-kubeconfig',
                    variable: 'KUBECONFIG'
                )
            ]) {
                sh '''
                    set -eu

                    kubectl --namespace default apply \
                    -f k8s/configmap.yaml \
                    -f k8s/service.yaml

                    DEPLOY_MANIFEST="$(mktemp)"
                    trap 'rm -f "$DEPLOY_MANIFEST"' EXIT

                    kubectl set image \
                    --local \
                    -f k8s/deployment.yaml \
                    finsecure-pay=cmyaa/finsecure-pay:build-${BUILD_NUMBER} \
                    -o yaml > "$DEPLOY_MANIFEST"

                    kubectl --namespace default apply -f "$DEPLOY_MANIFEST"

                    kubectl --namespace default rollout status \
                    deployment/finsecure-pay --timeout=180s

                    kubectl --namespace default get deployment finsecure-pay -o wide
                    kubectl --namespace default get pods -l app=finsecure-pay -o wide
                '''
            }
        }
    }
}

    triggers {
        pollSCM('H/2 * * * *')
    }
}