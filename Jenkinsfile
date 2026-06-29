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
                sh 'python3 -m pip install -r requirements-ci.txt'
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
