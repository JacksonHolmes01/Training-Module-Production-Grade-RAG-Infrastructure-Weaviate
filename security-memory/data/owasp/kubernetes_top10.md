

---
# K01-insecure-workload-configurations.md

---

layout: col-sidebar
title: "K01: Insecure Workload Configurations"
---

## Overview

The security context of a workload in Kubernetes is highly configurable which
can lead to serious security misconfigurations propagating across an
organization’s workloads and clusters. The [Kubernetes adoption, security, and
market trends report
2022](https://www.redhat.com/en/resources/kubernetes-adoption-security-market-trends-overview)
from Redhat stated that nearly 53% of respondents have experienced a
misconfiguration incident in their Kubernetes environments in the last 12
months.

![Insecure Workload Configuration -
Illustration](../../../assets/images/K01-2022.gif)

## Description

Kubernetes manifests contain many different configurations that can affect the
reliability, security, and scalability of a given workload. These configurations
should be audited and remediated continuously. Some examples of high-impact
manifest configurations are below:

**Application processes should not run as root:** Running the process inside of
a container as the `root` user is a common misconfiguration in many clusters.
While `root` may be an absolute requirement for some workloads, it should be
avoided when possible. If the container were to be compromised, the attacker
would have root-level privileges that allow actions such as starting a malicious
process that otherwise wouldn’t be permitted with other users on the system.

```yaml
apiVersion: v1  
kind: Pod  
metadata:  
  name: root-user
spec:  
  containers:
  ...
  securityContext:  
    #root user:
    runAsUser: 0
    #non-root user:
    runAsUser: 5554
```

**Read-only filesystems should be used:** In order to limit the impact of a
compromised container on a Kubernetes node, it is recommended to utilize
read-only filesystems when possible. This prevents a malicious process or
application from writing back to the host system. Read-only filesystems are a
key component to preventing container breakout.

```yaml
apiVersion: v1  
kind: Pod  
metadata:  
  name: read-only-fs
spec:  
  containers:  
  ...
  securityContext:  
    #read-only fs explicitly defined
    readOnlyRootFilesystem: true
```

**Privileged containers should be disallowed**: When setting a container to
`privileged` within Kubernetes, the container can access additional resources
and kernel capabilities of the host. Workloads running as root combined with
privileged containers can be devastating as the user can get complete access to
the host. This is, however, limited when running as a non-root user. Privileged
containers are dangerous as they remove many of the built-in container isolation
mechanisms entirely.

```yaml
apiVersion: v1  
kind: Pod  
metadata:  
  name: privileged-pod
spec:  
  containers:  
  ...
  securityContext:  
    #priviliged 
    privileged: true
    #non-privileged 
    privileged: false
```

**Resource constraints should be enforced**: By default, containers run with
unbounded compute resources on a Kubernetes cluster. CPU requests and limits
can be attributed to individual containers within a pod. If you don't specify
a CPU limit for a container, it means there's no upper bound on the CPU
resources it can consume. While this flexibility can be advantageous, it also
poses a risk for potential resource abuse, such as crypto-mining, as the
container could potentially utilize all available CPU resources on the
hosting node.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-limit-pod
spec:
  containers:
  ...
    resources:
      limits:
        cpu: "0.5" # 0.5 CPU cores
        memory: "512Mi" # 512 Megabytes of memory
      requests:
        cpu: "0.2" # 0.2 CPU cores
        memory: "256Mi" # 256 Megabytes of memory
```

## How to Prevent

Maintaining secure configurations throughout a large, distributed Kubernetes
environment can be a difficult task. While many security configurations are
often set in the `securityContext` of the manifest itself there are a number of
other misconfigurations that can be detected elsewhere. In order to prevent
misconfigurations, they must first be detected in both runtime and in code. We
can enforce that applications:

1. Run as non-root user
2. Run as non-privileged mode
3. Set AllowPrivilegeEscalation: False to disallow child process from
getting more privileges than its parents.
4. Set a LimitRange to constrain the resource allocations for each applicable
object kind in a namespace.

Tools such as Open Policy Agent can be used as a policy engine to detect these
common misconfigurations. The CIS Benchmark for Kubernetes can also be used as a
starting point for discovering misconfigurations.

![Insecure Workload Configuration -
Mitigations](../../../assets/images/K01-2022-mitigation.gif)

## Example Attack Scenarios

TODO

## References

CIS Benchmarks for Kubernetes:
[https://www.cisecurity.org/benchmark/kubernetes](https://www.cisecurity.org/benchmark/kubernetes)

Open Policy Agent:
[https://github.com/open-policy-agent/opa](https://github.com/open-policy-agent/opa)

Pod Security Standards:
[https://kubernetes.io/docs/concepts/security/pod-security-standards/](https://kubernetes.io/docs/concepts/security/pod-security-standards/)


---
# K02-supply-chain-vulnerabilities.md

---

layout: col-sidebar
title: "K02: Supply Chain Vulnerabilities"
---

## Overview

Containers take on many forms at different phases of the development lifecycle
supply chain; each of them presenting unique security challenges. A single
container alone can rely on hundreds of third-party components and dependencies
making trust of origin at each phase extremely difficult. These challenges
include but are not limited to image integrity, image composition, and known
software vulnerabilities.

![Supply Chain Vulnerabilities -
Illustration](../../../assets/images/K02-2022.gif)

## Description

**Image Integrity:** Software provenance has recently attracted significant
attention in the media due to events such as the [Solarwinds
breach](https://www.businessinsider.com/solarwinds-hack-explained-government-agencies-cyber-security-2020-12)
and a variety of [tainted third-party
packages](https://therecord.media/malware-found-in-npm-package-with-millions-of-weekly-downloads/).
These supply chain risks can surface in various states of the container build
cycle as well as at runtime inside of Kubernetes. When systems of record do not
exist regarding the contents of a container image it is possible that an
unexpected container may run in a cluster.

**Image Composition:** A container image consists of layers, each of which can
present security implications. A properly constructed container image not only
reduces attack surface, but can also increase deployment efficiency. Images with
extraneous software can be leveraged to elevate privileges or exploit known
vulnerabilities.

**Known Software Vulnerabilities**: Due to their extensive use of third-party
packages, many container images are inherently dangerous to pull into a trusted
environment and run. For example, if a given layer in an image contains a
version of OpenSSL that is susceptible to a known exploit it may be propagated
to several workloads and unknowingly put an entire cluster at risk.

## How to Prevent

**Image Integrity:** Container images can be thought of as a series of software
artifacts and metadata passed from a producer to a consumer. The handoff can be
as simple as a developer’s IDE directly to a Kubernetes cluster or as complex as
a multi-step dedicated CI/CD workflow. The integrity of the software should be
validated through each phase using [in-toto](https://in-toto.io/)
[attestations](https://github.com/in-toto/attestation). This also increases the
[SLSA](https://slsa.dev) level of the build pipeline, with a higher SLSA level
indicating a more resilient build pipeline.

**Software Bill of Materials (SBOM)**: An SBOM provides a list of software
packages, licenses, and libraries a given software artifact contains and should
be used as a starting point for other security checks. Two of the most popular
open standards for SBOM generation include [CycloneDX](https://cyclonedx.org/)
and [SPDX](https://spdx.dev/).

**Image Signing**: Each of the steps throughout a DevOps workflow can introduce
attacks or unexpected consequences. Producers and consumers use cryptographic
key-pairs to sign and verify the artifact at each step of the supply chain to
detect tampering with the artifacts themselves. The open-source
[Cosign](https://github.com/sigstore/cosign) project is an open source project
aimed at verifying container images.

**Image Composition:** Container images should be created using minimal OS
packages and dependencies to reduce the attack surface if the workload should be
compromised. Consider utilizing alternative base images such as
[Distroless](https://github.com/GoogleContainerTools/distroless) or
[Scratch](https://hub.docker.com/_/scratch) to not only improve security posture
but also drastically reduce the noise generated by vulnerability scanners. Using
distroless images also reduces the image size which ultimately helps in faster
CI/CD build.  It is also important to ensure your base images are up-to-date
with the latest security patches. Tools such as [Docker
Slim](https://github.com/docker-slim/docker-slim) are available to optimize your
image footprint for performance and security reasons.

**Known Software Vulnerabilities:** Image vulnerability scanning aims to
enumerate known security issues in container images and should be used as a
first line of defense. ****You can identify all upstream software with
vulnerabilities simply by looking for images built with a specific layer. Images
should be patched quickly by simply replacing the layer containing the
vulnerability and rebuilding the container to use up-to-date, fixed packages.
Open source tools such as [Clair](https://github.com/coreos/clair) and
[trivy](https://github.com/aquasecurity/trivy) will statically analyze container
images for known vulnerabilities such as CVEs and should be used as early in the
development cycle as reasonably possible.

**Enforcing Policy:** Prevent unapproved images from being used with the
Kubernetes [admission
controls](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
and policy engines such as [Open Policy Agent](https://www.openpolicyagent.org/)
and [Kyverno](https://kyverno.io) to reject workloads images which:

- haven’t been scanned for vulnerabilities
- use a base image that’s not explicitly allowed
- don’t include an approved SBOM
- originated from untrusted registries

![Supply Chain Vulnerabilities -
Mitigations](../../../assets/images/K02-2022-mitigation.gif)

## Example Attack Scenarios

Example #1: Compromised CI/CD Pipeline

Most teams use some form of automation to build and push container images to a
central registry. The image is then pulled from Kubernetes as defined in the
object manifest. If that build tool were to be compromised and a malicious
package was injected as part of the build Kubernetes would pull the image into
the cluster and run it. Malware may be executed, cryptocurrency miners may be
installed, or a backdoor planted.

## References

Admission Controllers:
[https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)

Co-Sign:
[https://github.com/sigstore/cosign](https://github.com/sigstore/cosign)

CycloneDX:
[https://owasp.org/www-project-cyclonedx/](https://owasp.org/www-project-cyclonedx/)

Docker Slim:
[https://github.com/docker-slim/docker-slim](https://github.com/docker-slim/docker-slim)

Open Policy Agent:
[https://www.openpolicyagent.org/](https://www.openpolicyagent.org/)

in-toto: [https://in-toto.io](https://in-toto.io)

SLSA: [https://slsa.dev](https://slsa.dev)


---
# K03-overly-permissive-rbac.md

---

layout: col-sidebar
title: "K03: Overly Permissive RBAC"
---

## Overview

[Role-Based Access
Control](https://kubernetes.io/docs/reference/access-authn-authz/rbac/) (RBAC)
is the primary authorization mechanism in Kubernetes and is responsible for
permissions over resources. These permissions combine verbs (get, create,
delete, etc.) with resources (pods, services, nodes, etc.) and can be namespace
or cluster scoped. A set of out of the box roles are provided that offer
reasonable default separation of responsibility depending on what actions a
client might want to perform. Configuring RBAC with least privilege enforcement
is a challenge for reasons we will explore below.

![Overly Permissive RBAC - Illustration](../../../assets/images/K03-2022.gif)

## Description

RBAC is an extremely powerful security enforcement mechanism in Kubernetes when
appropriately configured but can quickly become a massive risk to the cluster
and increase the blast radius in the event of a compromise.  Below are a few
examples of misconfigured RBAC:

## Unnecessary use of `cluster-admin`

When a subject such as a Service Account, User, or Group has access to the
built-in Kubernetes “superuser” called `cluster-admin` they are able to perform
any action on any resource within a cluster. This level of permission is
especially dangerous when used in a `ClusterRoleBinding` which grants full
control over every resource across the entire cluster. `cluster-admin` can also
be used as a `RoleBinding` which may also pose significant risk.

Below you will find the RBAC configuration of a popular OSS Kubernetes
development platform. It showcases a very dangerous `ClusterRoleBinding` which
is bound to the `default` service account. Why is this dangerous? It grants the
all-powerful `cluster-admin` privilege to every single Pod in the `default`
namespace. If a pod in the default namespace is compromised (think, Remote Code
Execution) then it is trivial for the attacker to compromise the entire cluster
by impersonating the service

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: redacted-rbac
subjects:
- kind: ServiceAccount
  name: default
  namespace: default
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
```

### How to Prevent

To reduce the risk of an attacker abusing RBAC configurations, it is important
to analyze your configurations continuously and ensure the principle of least
privilege is always enforced. Some recommendations are below:

- Reduce direct cluster access by end users when possible
- Don’t use Service Account Tokens outside of the cluster
- Avoid automatically mounting the default service account token
- Audit RBAC included with installed third-party components
- Deploy centralized polices to detect and block risky RBAC permissions
- Utilize `RoleBindings` to limit scope of permissions to particular namespaces
  vs. cluster-wide RBAC policies
- Follow the official [RBAC Good
  Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
  in the Kubernetes docs

### Example Attack Scenarios

An OSS cluster observability tool is installed inside of a private Kubernetes
cluster by the platform engineering team. This tool has an included web UI for
debugging and analyzing traffic. The UI is accidentally exposed to the internet
through it’s included Service manifest - it uses type: LoadBalancer which spins
up an AWS ALB load balancer with a **public** IP address.

This hypothetical tool uses the following RBAC configuration:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: default-sa-namespace-admin
  namespace: prd
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: admin
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: User
  name: system:serviceaccount:prd:default
```

An attacker finds the open web UI and is able to get a shell on the running
container in the cluster. The default service account token in the `prd`
namespace is used by the web UI and the attacker is able to impersonate it to
call the Kubernetes API and perform elevated actions such as `describe secrets`
in the `kube-system` namespace. This is due to the `roleRef` which gives that
service account the built-in privilege `admin` in the entire cluster.

### References

Kubernetes RBAC: <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>

RBAC Police Scanner: <https://github.com/PaloAltoNetworks/rbac-police>

Kubernetes RBAC Good Practices:
<https://kubernetes.io/docs/concepts/security/rbac-good-practices/>

## Unnecessary use of `LIST` permission

The list response contains all items in full, not just their name. Accounts with
`LIST` permission cannot get a specific item from the API, but will get all of
them in full when they list.

kubectl hides this by default by choosing to only show you the object names, but
it has all attributes of those objects.

### How to Prevent

Only grant `LIST` permission if you are also allowing that account to `GET` all
of that resource  

### Example Attack Scenario

```bash

# Create example A, which can only list secrets in the default namespace
# It does not have the GET permission
kubectl create serviceaccount only-list-secrets-sa
kubectl create role only-list-secrets-role --verb=list --resource=secrets
kubectl create rolebinding only-list-secrets-default-ns \
  --role=only-list-secrets-role --serviceaccount=default:only-list-secrets-sa
# Now to impersonate that service account
kubectl proxy &
# Create a secret to get
kubectl create secret generic abc --from-literal=secretAuthToken=verySecure123
# Prove we cannot get that secret
curl http://127.0.0.1:8001/api/v1/namespaces/default/secrets/abc \
  -H "Authorization: Bearer $(kubectl -n default get secrets -ojson | jq '.items[]| select(.metadata.annotations."kubernetes.io/service-account.name"=="only-list-secrets-sa")| \
  .data.token' | tr -d '"' | base64 -d)"
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {
  },
  "status": "Failure",
  "message": "secrets \"abc\" is forbidden: User \"system:serviceaccount:default:only-list-secrets-sa\" cannot get resource \"secrets\" in API group \"\" in the namespace \"default\"",
  "reason": "Forbidden",
  "details": {
    "name": "abc",
    "kind": "secrets"
  },
  "code": 403
}
# Now to get all secrets in the default namespace, despite not having "get" permission
curl http://127.0.0.1:8001/api/v1/namespaces/default/secrets?limit=500 -H \
  "Authorization: Bearer $(kubectl -n default get secrets -ojson | jq '.items[]| select(.metadata.annotations."kubernetes.io/service-account.name"=="only-list-secrets-sa")| \
  .data.token' | tr -d '"' | base64 -d)"
{
  "kind": "SecretList",
  "apiVersion": "v1",
  "metadata": {
    "selfLink": "/api/v1/namespaces/default/secrets",
    "resourceVersion": "17718246"
  },
  "items": [
  REDACTED : REDACTED
  ]
}
# Cleanup
kubectl delete serviceaccount only-list-secrets-sa
kubectl delete role only-list-secrets-role 
kubectl delete rolebinding only-list-secrets-default-ns 
kubectl delete secret abc
# Kill backgrounded kubectl proxy
kill "%$(jobs | grep "kubectl proxy" | cut -d [ -f 2| cut -d ] -f 1)"
```

### References

Why list is a scary permission on k8s:
<https://tales.fromprod.com/2022/202/Why-Listing-Is-Scary_On-K8s.html>
Kubernetes security recommendations for developers:
<https://kubernetes.io/docs/concepts/configuration/secret/#security-recommendations-for-developers>

## Unnecessary use of `WATCH` permission

The watch response contains all items in full, not just their name when they're
updated. Accounts with `WATCH` permission cannot get a specific item or list all
items from the API, but will get all of them in full when during the watch call,
and get all new items if the watch isn't interrupted.

### How to Prevent

Only grant `WATCH` permission if you are also allowing that account to `GET` and
`LIST` all of that resource  

![Overly Permissive RBAC -
Mitigations](../../../assets/images/K03-2022-mitigation.gif)

### Example Attack Scenarios

```bash

# Create example A, which can only watch secrets in the default namespace
# It does not have the GET permission
kubectl create serviceaccount only-watch-secrets-sa
kubectl create role only-watch-secrets-role --verb=watch --resource=secrets
kubectl create rolebinding only-watch-secrets-default-ns --role=only-watch-secrets-role --serviceaccount=default:only-watch-secrets-sa
# Now to impersonate that service account
kubectl proxy &
# Create a secret to get
kubectl create secret generic  abcd  --from-literal=secretPassword=verySecure
# Prove we cannot get that secret
curl http://127.0.0.1:8001/api/v1/namespaces/default/secrets/abcd \
  -H "Authorization: Bearer $(kubectl -n default get secrets -ojson | jq '.items[]| select(.metadata.annotations."kubernetes.io/service-account.name"=="only-watch-secrets-sa")| \
  .data.token' | tr -d '"' | base64 -d)"
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {
  },
  "status": "Failure",
  "message": "secrets \"abc\" is forbidden: User \"system:serviceaccount:default:only-watch-secrets-sa\" cannot get resource \"secrets\" in API group \"\" in the namespace \"default\"",
  "reason": "Forbidden",
  "details": {
    "name": "abcd",
    "kind": "secrets"
  },
  "code": 403
}

# Prove we cannot list the secrets either
curl http://127.0.0.1:8001/api/v1/namespaces/default/secrets?limit=500 \
  -H "Authorization: Bearer $(kubectl -n default get secrets -ojson | jq '.items[]| select(.metadata.annotations."kubernetes.io/service-account.name"=="only-watch-secrets-sa")| \
  .data.token' | tr -d '"' | base64 -d)"
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {
    
  },
  "status": "Failure",
  "message": "secrets is forbidden: User \"system:serviceaccount:default:only-watch-secrets-sa\" cannot list resource \"secrets\" in API group \"\" in the namespace \"default\"",
  "reason": "Forbidden",
  "details": {
    "kind": "secrets"
  },
  "code": 403
}

# Now to get all secrets in the default namespace, despite not having "get" permission
curl http://127.0.0.1:8001/api/v1/namespaces/default/secrets?watch=true \
  -H "Authorization: Bearer $(kubectl -n default get secrets -ojson | jq '.items[]| select(.metadata.annotations."kubernetes.io/service-account.name"=="only-watch-secrets-sa")| \
  .data.token' | tr -d '"' | base64 -d)"

{
  "type": "ADDED",
  "object": {
    "kind": "Secret",
    "apiVersion": "v1",
    "metadata": {
      "name": "abcd",
      "namespace": "default",
      "selfLink": "/api/v1/namespaces/default/secrets/abcd",
      "uid": "725c84ee-8dc7-41ef-a03e-193225e228b2",
      "resourceVersion": "1903164",
      "creationTimestamp": "2022-09-09T13:39:43Z",
      "managedFields": [
        {
          "manager": "kubectl-create",
          "operation": "Update",
          "apiVersion": "v1",
          "time": "2022-09-09T13:39:43Z",
          "fieldsType": "FieldsV1",
          "fieldsV1": {
            "f:data": {
              ".": {},
              "f:secretPassword": {}
            },
            "f:type": {}
          }
        }
      ]
    },
    "data": {
      "secretPassword": "dmVyeVNlY3VyZQ=="
    },
    "type": "Opaque"
  }
}
REDACTED OTHER SECRETS
# crtl+c to stop curl as this http request will continue

# Proving that we got the full secret
echo "dmVyeVNlY3VyZQ==" | base64 -d
verySecure

# Cleanup
kubectl delete serviceaccount only-watch-secrets-sa
kubectl delete role only-watch-secrets-role 
kubectl delete rolebinding only-watch-secrets-default-ns --role=only-list-secrets-role --serviceaccount=default:only-list-secrets-sa
kubectl delete secret abcd
# Kill backgrounded kubectl proxy
kill "%$(jobs | grep "kubectl proxy" | cut -d [ -f 2| cut -d ] -f 1)"
```

### References

Kubernetes security recommendations for developers:
<https://kubernetes.io/docs/concepts/configuration/secret/#security-recommendations-for-developers>


---
# K05-inadequate-logging.md

---

layout: col-sidebar
title: "K05: Inadequate Logging"
---

## Overview

A Kubernetes environment has the ability to generate logs at a variety of levels
from many different components. When logs are not captured, stored, or actively
monitored attackers have the ability to exploit vulnerabilities while going
largely undetected. The lack of logging and monitoring also presents challenges
during incident investigation and response efforts.

![Inadequate Logging - Illustration](../../../assets/images/K05-2022.gif)

## Description

Inadequate logging in the context of Kubernetes occurs any time:

- Relevant events such as failed authentication attempts, access to sensitive
  resources, manual deletion or modification of Kubernetes resources are not
  logged.
- Logs and traces of running workloads are not monitored for suspicious
  activity.
- Alerting thresholds are not in place or escalated appropriately.
- Logs are not centrally stored and protected against tampering.
- Logging infrastructure is disabled completely.

## How to Prevent

The following logging sources should be enabled and configured appropriately:

**Kubernetes Audit Logs: [Audit
logging](https://kubernetes.io/docs/tasks/debug-application-cluster/audit/)** is
a Kubernetes feature that records actions taken by the API for later analysis.
Audit logs help answer questions pertaining to events occurring on the API
server itself.

Ensure logs are monitoring for anomalous or unwanted API calls, especially any
authorization failures (these log entries will have a status message
“Forbidden”). Authorization failures could mean that an attacker is trying to
abuse stolen credentials.

Managed Kubernetes providers, including AWS, Azure, and GCP provide optional
access to this data in their cloud console and may allow you to set up alerts on
authorization failures.

**Kubernetes Events:** Kubernetes events can indicate any Kubernetes resource
state changes and errors, such as exceeded resource quota or pending pods, as
well as any informational messages.

**Application & Container Logs:** Applications running inside of Kubernetes
generate useful logs from a security perspective. The easiest method for
capturing these logs is to ensure the output is written to standard output
`stdout` and standard error `stderr` streams. Persisting these logs can be
carried out in a number of ways. It is common for operators to configure
applications to write logs to a log file which is then consumed by a sidecar
container to be shipped and processed centrally.

**Operating System Logs**: Depending on the OS running the Kubernetes nodes,
additional logs may be available for processing. Logs from programs such as
`systemd` are available using the `journalctl -u` command.

**Cloud Provider Logs:** If you are operating Kubernetes in a managed
environment such as AWS EKS, Azure AKS, or GCP GKE you can find a number of
additional logging streams available for consumption. One example, is within
[Amazon EKS](https://aws.amazon.com/eks/) there exists a log stream specifically
for the
[Authenticator](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
component. These logs represent the control plane component that EKS uses for
RBAC authentication using AWS IAM credentials and can be a rich source of data
for security operations teams.

**Network Logs:** Network logs can be captured within Kubernetes at a number of
layers. If you are working with traditional proxy or ingress components such as
nginx or apache, you should use the standard out `stdout` and standard error
`stderr` pattern to capture and ship these logs for further investigation. Other
projects such as [eBPF](https://ebpf.io/) aim to provide consumable network and
kernel logs to greater enhance security observability within the cluster.

As outlined above, there is no shortage of logging mechanisms available within
the Kubernetes ecosystem. A robust security logging architecture should not only
capture relevant security events, but also be centralized in a way that is
queryable, long term, and maintains integrity.

![Inadequate Logging -
Mitigations](../../../assets/images/K05-2022-mitigation.gif)

## Example Attack Scenarios

Scenario #1: Rouge Insider (anomalous number of “delete” events)

Scenario #2: Service Account Token Compromise

## References

[https://developer.squareup.com/blog/threat-hunting-with-kubernetes-audit-logs/](https://developer.squareup.com/blog/threat-hunting-with-kubernetes-audit-logs/)

[https://kubernetes.io/docs/concepts/cluster-administration/logging/](https://kubernetes.io/docs/concepts/cluster-administration/logging/)

[https://www.cncf.io/blog/2021/12/21/extracting-value-from-the-kubernetes-events-feed/](https://www.cncf.io/blog/2021/12/21/extracting-value-from-the-kubernetes-events-feed/)


---
# K06-broken-authentication.md

---

layout: col-sidebar
title: "K06: Broken Authentication"
---

## Overview

Authentication in Kubernetes takes on my many forms and is extremely flexible.
This emphasis on being highly configurable makes Kubernetes work in a number of
different environments but also presents challenges when it comes to cluster and
cloud security posture.

![Broken Authentication - Illustration](../../../assets/images/K06-2022.gif)

## Description

Several entities need to access the Kubernetes API. Authentication is the first
hurdle for these requests. Authentication to the Kubernetes API is via HTTP
request and the authentication method can vary from cluster to cluster. If a
request cannot be authenticated, it is rejected with an HTTP status of 401.

![Kubernetes Authentication](../../../assets/images/kubernetes-auth.png)

Source:
[https://kubernetes.io/docs/concepts/security/controlling-access/](https://kubernetes.io/docs/concepts/security/controlling-access/)

Let’s dive into the different types of subjects who need to authenticate to the
Kubernetes API.

### Human Authentication

People need to interact with Kubernetes for a number of reasons. Developers
debugging their running application in a staging cluster, platform engineers
building and testing new infra, and more. There are several methods available to
authenticate to a cluster as a human such as OpenID Connect (OIDC),
Certificates, cloud IAM, and even ServiceAccount tokens. Some of these offer
much more robust security than others as we will explore in the prevention
section below.

### Service Account Authentication

Service account (SA) tokens can be presented to the Kubernetes API as an
authentication mechanism when configured with RBAC appropriately. A SA is a
simple authentication mechanism typically reserved for container-to-api
authentication from *inside* the cluster.

## How to Prevent

### Avoid using certificates for end user authentication

Certificates are convenient to use for authenticating to the Kubernetes API but
should be used with extreme caution. At this time, the API has no way to revoke
certificates making for a scramble to re-key the cluster in the event of a
compromise or leak of private key material. Certificates are also more
cumbersome to configure, sign, and distribute. A certificate may be used as a
“Break Glass” authentication mechanism but not for primary auth.

### Never roll your own authentication

Just like crypto, you should not build something novel when it isn’t necessary.
Use what is supported and widely adopted.

### Enforce MFA when possible

No matter the auth mechanism chosen, force humans to provide a second method of
authentication (typically part of OIDC).

### Don’t use Service Account tokens from outside of the cluster

For use inside the cluster, Kubernetes Service Account tokens are
obtained directly using the TokenRequest API, and are mounted into Pods
using a projected volume. For use outside the cluster, these tokens must be
manually provisioned via a [Kubernetes Secret](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#manually-create-a-long-lived-api-token-for-a-serviceaccount)
and have no expiration. Using long-lived SA tokens from outside of the cluster
opens your cluster up to significant risk.

If a token based approach is required, short-lived tokens can be provisioned
by the [TokenRequest API](https://kubernetes.io/docs/reference/kubernetes-api/authentication-resources/token-request-v1/)
or using [`kubectl create token` with the `--duration`
flag](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/).

### Authenticate users and external services using short-lived tokens

All authentication tokens should be as short-lived as tolerable. This way if
(and when) a credential is leaked, it is possible that it may not be replayed in
the time necessary to compromise the account.

![Broken Authentication -
Mitigations](../../../assets/images/K06-2022-mitigation.gif)

## Example Attack Scenarios

***Accidental Git Leak:*** A developer accidentally checks their `.kubeconfig`
file from their laptop which holds Kubernetes authentication credentials for
their clusters at work. Someone scanning GitHub finds the credentials and
replays them to the target API (unfortunately, sitting on the internet) and
because the cluster is configured to authenticate using certificates, the leaked
file has all of the information needed to successfully authenticate to the
target cluster.

## References

Tremlo Blog Post:
[https://www.tremolosecurity.com/post/what-the-nsa-and-cisa-left-out-of-their-kubernetes-hardening-guide](https://www.tremolosecurity.com/post/what-the-nsa-and-cisa-left-out-of-their-kubernetes-hardening-guide)

Kubernetes Authentication:
[https://kubernetes.io/docs/concepts/security/controlling-access/](https://kubernetes.io/docs/concepts/security/controlling-access/)


---
# K09-misconfigured-cluster-components.md

---

layout: col-sidebar
title: "K09: Misconfigured Cluster Components"
---

## Overview

A Kubernetes cluster is compromised of many different components ranging from
key-value storage within etcd, the kube-apiserver, the kubelet, and more. Each
of these components are highly configurable have important security
responsibilities.

![Misconfigured Cluster Components -
Illustration](../../../assets/images/K09-2022.gif)

## Description

Misconfigurations in core Kubernetes components can lead to complete cluster
compromise or worse. In this section we will explore some of the components that
exist on the Kubernetes control plane and nodes which can easily be
misconfigured:

**kubelet:** Agent that runs on each node in the cluster and ensures that
containers run as expected and are healthy. Some dangerous configurations to
watch out for on the kubelet itself are as follows:

Anonymous authentication allows non-authenticated requests to the Kubelet. Check
your Kubelet configuration and ensure the flag below is set to **false**:

```bash
#bad
--anonymous-auth=true
#good
--anonymous-auth=false
```

Authorization checks should always be performed when communicating with the
Kubelets. It is possible to set the Authorization mode to explicitally allow
unauthorized requests. Inspect the following to ensure this is not the case in
your Kubelet config. The mode should be set to anything other than
**AlwaysAllow**:

```bash
#bad
--authorization-mode=AlwaysAllow
#good
--authorization-mode=Webhook
```

**etcd:** A highly available key-value store that Kubernetes uses to centrally
house all cluster data. It is important to keep etcd safe as it stores config
data as well as secrets.

**kube-apiserver:** The API server is a component of the Kubernetes [control
 plane](https://kubernetes.io/docs/reference/glossary/?all=true#term-control-plane)
 that exposes the Kubernetes API. The API server is the front end for the
 Kubernetes control plane.

A simple security check you can perform is to inspect the internet accessibility
of the API server itself. It is recommended to keep the Kubernetes API off of
public network as seen in recent
[news](https://www.bleepingcomputer.com/news/security/over-900-000-kubernetes-instances-found-exposed-online/).

![Misconfigured Cluster Components -
Mitigations](../../../assets/images/K09-2022-mitigation.gif)

## How to Prevent

A good start is to perform regular CIS Benchmark scans and audits focused on
component misconfigurations. A strong culture of Infrastructure-as-Code can also
help centralize Kubernetes configuration and remediation giving security teams
visibility into how clusters are created and maintained. Using managed
Kubernetes such as EKS or GKE can also help limit some of the options for
component configuration as well as guide operators into more secure defaults.

## References

CIS Benchmark:
[https://www.cisecurity.org/benchmark/kubernetes](https://www.cisecurity.org/benchmark/kubernetes)

Kubernetes Cluster Components:
[https://kubernetes.io/docs/concepts/overview/components/](https://kubernetes.io/docs/concepts/overview/components/)
