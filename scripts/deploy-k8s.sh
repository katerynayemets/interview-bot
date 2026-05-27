#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*" >&2; }
step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }

NAMESPACE="interview-bot"
IMAGE_TAG="interview-bot:k8s"
MANIFESTS_DIR="k8s"
EXPECTED_CONTEXT="${EXPECTED_CONTEXT:-docker-desktop}"
SKIP_BUILD="${SKIP_BUILD:-0}"

# ---------------------------------------------------------------------------
# 1. Pre-flight: docker, kubectl, context
# ---------------------------------------------------------------------------
step "1/7 Pre-flight checks"

if ! command -v docker >/dev/null 2>&1; then
  error "Docker CLI not found"; exit 1
fi
if ! docker info >/dev/null 2>&1; then
  error "Docker daemon is not running"; exit 1
fi
info "Docker is available."

if ! command -v kubectl >/dev/null 2>&1; then
  error "kubectl not found"; exit 1
fi
info "kubectl found: $(kubectl version --client --output=yaml 2>/dev/null | grep gitVersion | head -1 | awk '{print $2}')"

current_ctx="$(kubectl config current-context 2>/dev/null || echo none)"
if [ "$current_ctx" != "$EXPECTED_CONTEXT" ]; then
  warn "Current kubectl context is '$current_ctx', expected '$EXPECTED_CONTEXT'."
  warn "Trying to switch: kubectl config use-context $EXPECTED_CONTEXT"
  kubectl config use-context "$EXPECTED_CONTEXT" || {
    error "Could not switch context. Set EXPECTED_CONTEXT=$current_ctx to skip this check."
    exit 1
  }
fi
info "kubectl context: $(kubectl config current-context)"

if ! kubectl get nodes >/dev/null 2>&1; then
  error "Cluster is not reachable. Make sure Kubernetes is enabled in Docker Desktop."
  exit 1
fi
info "Cluster reachable: $(kubectl get nodes --no-headers | wc -l | tr -d ' ') node(s)."

# ---------------------------------------------------------------------------
# 2. Secret (copy template if missing)
# ---------------------------------------------------------------------------
step "2/7 Verifying Secret manifest"

if [ ! -f "${MANIFESTS_DIR}/02-secret.yaml" ]; then
  if [ -f "${MANIFESTS_DIR}/02-secret.yaml.example" ]; then
    warn "k8s/02-secret.yaml not found. Copying from .example."
    warn "Edit k8s/02-secret.yaml (put real BOT_TOKEN) and re-run."
    cp "${MANIFESTS_DIR}/02-secret.yaml.example" "${MANIFESTS_DIR}/02-secret.yaml"
    exit 1
  else
    error "Neither k8s/02-secret.yaml nor .example present."
    exit 1
  fi
fi
info "Secret manifest present."

# ---------------------------------------------------------------------------
# 3. Build image (Docker Desktop's k8s sees local docker images directly)
# ---------------------------------------------------------------------------
step "3/7 Building application image: ${IMAGE_TAG}"

if [ "$SKIP_BUILD" = "1" ]; then
  warn "SKIP_BUILD=1 → skipping docker build (using existing image)."
else
  docker build --target production -t "${IMAGE_TAG}" .
  info "Image built: ${IMAGE_TAG}"
fi

# ---------------------------------------------------------------------------
# 4. Apply manifests (alphabetic order via the numeric prefixes)
# ---------------------------------------------------------------------------
step "4/7 Applying manifests from ${MANIFESTS_DIR}/"
kubectl apply -f "${MANIFESTS_DIR}/"
info "Manifests applied."

# ---------------------------------------------------------------------------
# 5. Wait for stateful services first, then deployments
# ---------------------------------------------------------------------------
step "5/7 Waiting for Deployments to become Available (up to 5 min each)"

deployments=("postgres" "redis" "api" "worker" "pgadmin")
for d in "${deployments[@]}"; do
  info "Waiting: deployment/$d"
  kubectl -n "${NAMESPACE}" rollout status "deployment/$d" --timeout=300s
done

step "5b/7 Waiting for hostPath demo pods to become Ready"
for p in "hostpath-writer" "hostpath-reader"; do
  info "Waiting: pod/$p"
  kubectl -n "${NAMESPACE}" wait --for=condition=Ready "pod/$p" --timeout=120s
done

# ---------------------------------------------------------------------------
# 6. Smoke test
# ---------------------------------------------------------------------------
step "6/7 Smoke test on api NodePort (http://localhost:30080/health)"

attempts=0
max_attempts=20
sleep_secs=3
ok=0
while [ "$attempts" -lt "$max_attempts" ]; do
  if curl -fsS "http://localhost:30080/health" >/dev/null 2>&1; then
    info "Smoke test passed: /health returned 200."
    ok=1
    break
  fi
  attempts=$((attempts + 1))
  sleep "$sleep_secs"
done

if [ "$ok" -ne 1 ]; then
  warn "Smoke test did not succeed within $((max_attempts * sleep_secs))s."
  warn "Diagnose with:  kubectl -n ${NAMESPACE} logs deploy/api -c api --tail=50"
fi

# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------
step "7/7 Cluster summary"
echo
kubectl -n "${NAMESPACE}" get pods,svc,pvc,configmap,secret

echo
info "Stack deployed to namespace '${NAMESPACE}'."
echo "  API:        http://localhost:30080"
echo "  Health:     http://localhost:30080/health"
echo "  pgAdmin:    http://localhost:30050"
echo
info "Useful commands:"
echo "  kubectl -n ${NAMESPACE} get pods -o wide"
echo "  kubectl -n ${NAMESPACE} top pods                       # resource usage"
echo "  kubectl -n ${NAMESPACE} logs deploy/api -c api -f"
echo "  kubectl -n ${NAMESPACE} logs deploy/api -c log-sidecar -f   # emptyDir sidecar"
echo "  kubectl -n ${NAMESPACE} logs pod/hostpath-reader -f         # hostPath cross-pod"
echo "  kubectl -n ${NAMESPACE} delete all,pvc,configmap,secret --all   # full cleanup"
