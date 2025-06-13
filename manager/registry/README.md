# Device Registry

The contents of this folder will deploy the device registry.  mDNS is a standardized protocol for identifying devices
and their services on a local network.

Individual acquisition devices are configured to broadcast their availability and connection information (see 
[device installation README](../../device/README.md)).  This service runs on a single device (typically the device
chosen to be the central management server) and observes the broadcasts from each device.  This consolidated device
listing is published by this service for the management console dashboard or any other client.

### Requirements

The following instructions assume deployment on a Linux host machine.  The service itself is cross-platform and may be
run on any host.  The specifics of installing node.js and making it automatically start on other platforms will vary.  On
Windows and macOS you can generally assume mDNS is running (final step).

* A user and group both named `autotrainer`.
    * A different user can be used, but `auto-trainer-management-registry.service` will need to be updated accordingly.
* node.js (v22 or later) installed for the user that will be assigned to run the service in `auto-trainer-management-registry.service`.
    * [NVM](https://github.com/nvm-sh/nvm) is a convenient method to install node.js.
* The `auto-trainer-deployment` repository cloned to `/autotrainer/auto-trainer-deployment/`
    * `/autotrainer` must at a minimum have rwx permissions for the `autotrainer` user and group.
    * A different location can be used, but `auto-trainer-management-registry.service` will need to be updated accordingly.

Although the default for many Linux distributions, you may want to verify mDNS is running:

```bash
avahi-browse -d local _autotrainer._tcp --resolve -t
```

Depending on whether any autotrainer device nodes are currently configured to advertise on your network, this may not return
any results/instances, however it should execute cleanly without errors.

This is typically done under the `autotrainer` user.  If so, and the user is not yet created, it can be added with

```bash
sudo useradd -m -s /bin/bash -G sudo autotrainer
sudo passwd autotrainer
```

The second command will require entering the desired password twice.

### Installation

1. Clone the `auto-trainer-deployment` repository to `/autotrainer/auto-trainer-deployment/`:
   ```bash
   sudo mkdir -p /autotrainer
   sudo chown autotrainer:autotrainer /autotrainer
   cd /autotrainer
   git clone https://github.com/Mouse-GYM/auto-trainer-deployment.git
   ```
2. Install the dependencies:
   ```bash
   cd /autotrainer/auto-trainer-deployment/management/registry
   npm install
   ```
3. Copy the service file to the systemd directory:
   ```bash
   sudo cp auto-trainer-management-registry.service /etc/systemd/system/
   ```
4. Enable and start the service:
   ```bash
   sudo systemctl enable auto-trainer-management-registry.service
   sudo systemctl start auto-trainer-management-registry.service
    ```
   
