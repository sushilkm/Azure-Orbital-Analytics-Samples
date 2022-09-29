#!/bin/sh

set -e

K8S_ROOT="$(cd `dirname "${BASH_SOURCE}"`; pwd)"
ACTIVITY=$1

usage() {
  echo "$@"
  exit 1
}

[ -z "$ACTIVITY" ] && usage "Activity name not supplied"

export SCRIPT_NAME=${ACTIVITY}.yaml
export JOB_NAME=${ACTIVITY}-job

envsubst < ${K8S_ROOT}/${SCRIPT_NAME} | kubectl -n ${APP_NAMESPACE} apply -f -
JOB_SUCCEEDED_STATUS=0

while [ "$JOB_SUCCEEDED_STATUS" != "1" ]; do
    echo "Waiting for kubernetes job '${JOB_NAME}' to finish!"
    sleep 30
    JOB_SUCCEEDED_STATUS=$(kubectl -n ${APP_NAMESPACE} get job ${JOB_NAME} -o json | jq '.status.succeeded')
    if [ -z "$JOB_SUCCEEDED_STATUS" ]; then
        echo "Job status could not be found"
        exit 1
    fi
    if [ "$JOB_SUCCEEDED_STATUS" == "null" ]; then
        IS_JOB_ACTIVE=$(kubectl -n ${APP_NAMESPACE} get job ${JOB_NAME} -o json | jq '.status.active')
        if [ "$IS_JOB_ACTIVE" == null ]; then
            echo "Job status could not be found"
            exit 1
        fi
    fi
done