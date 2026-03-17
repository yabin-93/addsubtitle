pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    triggers {
        cron('H 3 * * *')
    }

    parameters {
        string(name: 'ADD_SUBTITLE_BASE_URL', defaultValue: 'https://staging.addsubtitle.ai', description: 'API base URL')
        string(name: 'ADD_SUBTITLE_LOGIN_EMAIL', defaultValue: '1020817070@qq.com', description: 'Login email')
        booleanParam(name: 'RUN_ALL_CASES', defaultValue: false, description: 'Run all cases')
        string(name: 'PYTEST_MARK_EXPRESSION', defaultValue: 'P0', description: 'Used only when RUN_ALL_CASES=false')
    }

    environment {
        JUNIT_XML_PATH = 'junit.xml'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PYTHONUTF8 = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Set Up Python') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m venv .venv-jenkins'
                        sh '.venv-jenkins/bin/python -m pip install --upgrade pip'
                        sh '.venv-jenkins/bin/python -m pip install -r requirements.txt'
                    } else {
                        bat 'python -m venv .venv-jenkins'
                        bat '.\\.venv-jenkins\\Scripts\\python.exe -m pip install --upgrade pip'
                        bat '.\\.venv-jenkins\\Scripts\\python.exe -m pip install -r requirements.txt'
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                script {
                    if (isUnix()) {
                        sh '.venv-jenkins/bin/python run.py'
                    } else {
                        bat '.\\.venv-jenkins\\Scripts\\python.exe run.py'
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'allure-results/**/*,reports/**/*,common/Logs/**/*,extract.yaml,junit.xml', allowEmptyArchive: true
            junit testResults: 'junit.xml', allowEmptyResults: true
            // If the Allure Jenkins plugin is installed, you can add:
            // allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        }
    }
}
