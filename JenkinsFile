pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements-ci.txt
                '''
            }
        }

        stage('Success') {
            steps {
                echo 'Build berhasil'
            }
        }

    }

    post {
        success {
            echo 'Pipeline berhasil.'
        }

        failure {
            echo 'Pipeline gagal.'
        }
    }
}
