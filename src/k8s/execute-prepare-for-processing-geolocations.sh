#!/bin/sh

set -e

K8S_ROOT="$(cd `dirname "${BASH_SOURCE}"`; pwd)"

envsubst < ${K8S_ROOT}/prepare-for-processing-geolocations.yaml | kubectl -n ${APP_NAMESPACE} apply -f -
JOB_SUCCEEDED_STATUS=0

while [ "$JOB_SUCCEEDED_STATUS" != "1" ]; do
    echo "Waiting for kubernetes job 'prepare-for-processing-geolocation-job' to finish!"
    sleep 30
    JOB_SUCCEEDED_STATUS=$(kubectl -n vision get job prepare-for-processing-geolocation-job -o json | jq '.status.succeeded')
    if [ "$JOB_SUCCEEDED_STATUS" == "null" ]; then
        IS_JOB_ACTIVE=$(kubectl -n vision get job prepare-for-processing-geolocation-job -o json | jq '.status.active')
        if [ "$IS_JOB_ACTIVE" == null ]; then
            echo "Job status could not be found"
            exit 1
        fi
    fi
done