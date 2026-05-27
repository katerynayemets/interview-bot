#!/usr/bin/env bash
# scripts/deploy-mlops.sh
#
# End-to-end deployment of the LR3 MLOps stack on a local Kubernetes cluster
# (tested on Docker Desktop Kubernetes v1.34, kubeadm provisioner).
#
# What it does:
#   1. Pre-flight checks (docker, kubectl, cluster, context).
#   2. Installs Kubeflow Pipelines standalone (cluster-scoped + env/dev).
#   3. Patches broken/removed upstream images:
#        - gcr.io/ml-pipeline/minio:...  ->  minio/minio (Docker Hub fallback)
#        - gcr.io/ml-pipeline/mysql:8.0.26 -> mysql:5.7 (native_password auth)
#      and recreates the MySQL PVC if MySQL 8 data is sitting there.
#   4. Scales proxy-agent to 0 (it's GCP-only, useless on a laptop).
#   5. Installs metrics-server with --kubelet-insecure-tls (Docker Desktop fix).
#   6. Installs ArgoCD.
#   7. Applies the ArgoCD Application manifest (GitOps demo).
#   8. Prints URLs + useful follow-up commands.
#
# Idempotent: safe to re-run.
#
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*" >&2; }
step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }

PIPELINE_VERSION="${PIPELINE_VERSION:-2.5.0}"
EXPECTED_CONTEXT="${EXPECTED_CONTEXT:-docker-desktop}"
MINIO_IMAGE="${MINIO_IMAGE:-minio/minio:RELEASE.2019-08-14T20-37-41Z}"
MYSQL_IMAGE="${MYSQL_IMAGE:-mysql:5.7}"

KFP_BASE="github.com/kubeflow/pipelines/manifests/kustomize"
ARGOCD_INSTALL_URL="https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
METRICS_URL="https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"

# ---------------------------------------------------------------------------
step "1/8 Pre-flight checks"
# ---------------------------------------------------------------------------
command -v docker  >/dev/null 2>&1 || { error "docker not in PATH";  exit 1; }
command -v kubectl >/dev/null 2>&1 || { error "kubectl not in PATH"; exit 1; }
docker info >/dev/null 2>&1        || { error "docker daemon not running"; exit 1; }
info "Docker + kubectl available."

current_ctx="$(kubectl config current-context 2>/dev/null || echo none)"
if [ "$current_ctx" != "$EXPECTED_CONTEXT" ]; then
  warn "kubectl context is '$current_ctx' (expected '$EXPECTED_CONTEXT'). Trying to switch."
  kubectl config use-context "$EXPECTED_CONTEXT" || {
    error "Could not switch context. Override via EXPECTED_CONTEXT=<your>."
    exit 1
  }
fi
info "Cluster context: $(kubectl config current-context)"
kubectl get nodes >/dev/null 2>&1 || { error "Cluster not reachable"; exit 1; }

# ---------------------------------------------------------------------------
step "2/8 Install Kubeflow Pipelines (v$PIPELINE_VERSION)"
# ---------------------------------------------------------------------------
info "Applying cluster-scoped resources..."
kubectl apply -k "${KFP_BASE}/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io

info "Applying env/dev (this brings up the kubeflow namespace)..."
# Retry loop — first apply often fails on CRD races
for i in 1 2 3; do
  if kubectl apply -k "${KFP_BASE}/env/dev?ref=$PIPELINE_VERSION"; then
    break
  fi
  warn "kubectl apply -k failed (attempt $i/3); sleeping 15s and retrying."
  sleep 15
done

# ---------------------------------------------------------------------------
step "3/8 Patch broken upstream images + recreate mysql PVC if needed"
# ---------------------------------------------------------------------------
info "Patching minio image -> ${MINIO_IMAGE}"
kubectl -n kubeflow set image deployment/minio "minio=${MINIO_IMAGE}"

# MySQL 8 data in PVC is incompatible with MySQL 5.7 (innodb crash).
# Wipe the PVC so 5.7 starts fresh.
if kubectl -n kubeflow get pvc mysql-pv-claim >/dev/null 2>&1; then
  current_mysql_img="$(kubectl -n kubeflow get deploy mysql -o jsonpath='{.spec.template.spec.containers[0].image}' || echo none)"
  if [ "$current_mysql_img" != "$MYSQL_IMAGE" ]; then
    info "Recreating mysql PVC (data layout changes from $current_mysql_img to $MYSQL_IMAGE)"
    kubectl -n kubeflow scale deploy/mysql --replicas=0
    sleep 5
    kubectl -n kubeflow delete pvc mysql-pv-claim --wait=false || true
    sleep 5
    kubectl apply -k "${KFP_BASE}/env/dev?ref=$PIPELINE_VERSION" >/dev/null
  fi
fi

info "Patching mysql image -> ${MYSQL_IMAGE}"
kubectl -n kubeflow set image deployment/mysql "mysql=${MYSQL_IMAGE}"
kubectl -n kubeflow scale deploy/mysql --replicas=1

# ---------------------------------------------------------------------------
step "4/8 Scale proxy-agent to 0 (GCP-only component, unused locally)"
# ---------------------------------------------------------------------------
kubectl -n kubeflow scale deploy/proxy-agent --replicas=0 || true

# ---------------------------------------------------------------------------
step "5/8 Wait for Kubeflow Pipelines core to become Ready"
# ---------------------------------------------------------------------------
core_deploys=(
  mysql
  minio
  ml-pipeline
  ml-pipeline-ui
  metadata-grpc-deployment
  workflow-controller
)
for d in "${core_deploys[@]}"; do
  info "rollout status: deploy/$d"
  kubectl -n kubeflow rollout status "deploy/$d" --timeout=600s || warn "  $d not Ready in 10m — continuing"
done

# After mysql is fresh, ml-pipeline + clients must reconnect to create their dbs
info "Restarting mysql-clients so they (re)create their databases"
for d in ml-pipeline metadata-grpc-deployment metadata-writer \
         cache-server cache-deployer-deployment \
         ml-pipeline-persistenceagent ml-pipeline-scheduledworkflow; do
  kubectl -n kubeflow rollout restart "deploy/$d" >/dev/null
done
for d in ml-pipeline metadata-grpc-deployment metadata-writer ml-pipeline-persistenceagent; do
  kubectl -n kubeflow rollout status "deploy/$d" --timeout=180s || warn "  $d slow to roll out"
done

# ---------------------------------------------------------------------------
step "6/8 Install metrics-server (with Docker Desktop kubelet TLS fix)"
# ---------------------------------------------------------------------------
kubectl apply -f "$METRICS_URL"
kubectl -n kube-system patch deployment metrics-server \
  --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' \
  2>/dev/null || info "  (metrics-server already patched)"

# ---------------------------------------------------------------------------
step "7/8 Install ArgoCD + apply Application manifest"
# ---------------------------------------------------------------------------
kubectl get ns argocd >/dev/null 2>&1 || kubectl create namespace argocd
kubectl apply -n argocd -f "$ARGOCD_INSTALL_URL" || warn "  (one CRD may fail with 'Too long' on client-side; harmless)"
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=300s

info "Applying ArgoCD Application: mlops/argocd/application.yaml"
kubectl apply -f mlops/argocd/application.yaml

# ---------------------------------------------------------------------------
step "8/8 Summary"
# ---------------------------------------------------------------------------
echo
info "Stack deployed."
echo
echo "  Kubeflow Pipelines UI:"
echo "    kubectl -n kubeflow port-forward svc/ml-pipeline-ui 8080:80"
echo "    open http://localhost:8080"
echo
echo "  ArgoCD UI:"
echo "    kubectl -n argocd port-forward svc/argocd-server 8081:443"
echo "    open https://localhost:8081  (admin / \$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d))"
echo
echo "  ArgoCD demo app (NodePort, after first sync):"
echo "    open http://localhost:30090"
echo
echo "  Useful diagnostics:"
echo "    kubectl -n kubeflow get pods"
echo "    kubectl -n argocd get pods,applications.argoproj.io"
echo "    kubectl top pods -A"
echo "    kubectl -n kubeflow logs deploy/ml-pipeline --tail=20"
echo
echo "  Upload the example pipeline through the Kubeflow UI:"
echo "    file: mlops/pipelines/iris_pipeline.yaml"
