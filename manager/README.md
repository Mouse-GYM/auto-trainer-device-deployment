# Central Service Deployment
The central services are run on a single device, which can be a separate server or one of the nodes in the system.

## Management Registry
The management registry is a node.js application. See the requirements and installation instructions in
the [Readme](registry/README.md).

## Management Dashboard
The management dashboard is deployed as a Docker container.  If installed on a device node, Docker will already be
installed.  For other devices, see the [Docker Installation Instructions](https://docs.docker.com/engine/install/) for your
platform, if needed.

The following also assumes that the `auto-trainer-deployment` repository has been cloned to `/autotrainer/auto-trainer-deployment/`
as described in the [Management Registry Readme](registry/README.md).

With docker installed:
```bash
cd /autotrainer/auto-trainer-deployment/manager

./up.sh
```
The service will start automatically on restarts moving forward.
