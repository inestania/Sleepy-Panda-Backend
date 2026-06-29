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
                    py -3.10 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
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
