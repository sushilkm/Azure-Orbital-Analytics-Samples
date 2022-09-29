#!/bin/sh

set -e

K8S_ROOT="$(cd `dirname "${BASH_SOURCE}"`; pwd)"

date
source params.source

usage() {
  echo "$@"
  exit 1
}

[ -z "$STORAGE_ACCOUNT_RG_NAME" ] && usage "Storage Account Resource Group Name not provided not supplied"
[ -z "$STORAGE_ACCOUNT_NAME" ] && usage "Storage Account Name not provided not supplied"
[ -z "$STORAGE_ACCOUNT_CONTAINER_NAME" ] && usage "Storage Account Container Name not provided not supplied"

# Create persistent volument and persistent volume claim
envsubst < ${K8S_ROOT}/create-pv.yaml | kubectl -n ${APP_NAMESPACE} apply -f -
envsubst < ${K8S_ROOT}/create-pvc.yaml | kubectl -n ${APP_NAMESPACE} apply -f -

echo "Files will be processed in directory ${PROCESSING_DIR} in storage account!"
${K8S_ROOT}/execute-job.sh image-transform
${K8S_ROOT}/execute-job.sh prepare-for-ai-model
${K8S_ROOT}/execute-job.sh ai-model
${K8S_ROOT}/execute-job.sh prepare-for-processing-geolocations
${K8S_ROOT}/execute-job.sh process-geolocations
date
