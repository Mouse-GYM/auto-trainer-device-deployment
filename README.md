##  Device Deployment
Installation of the core AutoTrainer application is described in the [AutoTrainer Repository itself](https://github.com/Mouse-GYM/auto-trainer).
In addition, the following supporting services are required for the node to participate in centralized system management.

The majority of device setup is performed by the `prepare_autotrainer_unit.sh` script. This is followed by a manual, device-specific
configuration step.

### Typical Installation

#### 1. Automated Preparation
Run `prepare_autotrainer_unit.sh` with the name of the unit as an argument.
The name will be used as the hostname for the computer as well as the identifier in remote views,
emergency notifications, and similar.
It should be unique for all units in the system.

```bash
./prepare_autotrainer_unit.sh <DEVICE_HOST_NAME>
```

where `<DEVICE_HOST_NAME>` must be replaced with the device-specific name. Such as _agx327_.
The script requires the use of `sudo`.
You will be prompted to enter the account password if you have already authenticated for an earlier `sudo` command.

#### 2. Configure Docker Compose Variables

Copy the environment template:

```shell
cp .env-template .env
```

Edit the newly created .env and populate the required values.
Typical values are provided in the comments of the template file.
The device name should be the same value you used as an argument to `prepare_autotrainer_unit.sh`.

Values for the AWS SNS notifications are found elsewhere.

#### 3. Authenticate for Docker Images
Installing the per-device management console services requires access to the Mouse-GYM GitHub organization.

Log into the GitHub docker registry

```shell
docker login ghcr.io -u <username>
```

You will be prompted for a personal access token associated with `<username>`.

Note: For Colorado devices at the time of this writing, a username and access token is sometimes found in a file
`startup_steps.txt` or similar on the Desktop.

#### 4. Start Docker Containers
```shell
./up.sh
```

After the first manual start, the services will restart after any reboot or other reason for exit automatically.

### Details of Automated Preparation
The following provides details of some of the actions performed in the `prepare_autotrainer_unit.sh` script.
These should not need to be done manually, but may be useful if some portion of the configuration needs to be updated,
or the script requires troubleshooting.

#### Set the Hostname
The hostname of the device should be set to a unique name.
This can be done via Settings->About->Device Name on the device, or via the command line with:

```bash
sudo hostnamectl set-hostname <unique-name>
```

Replace `<unique-name>` with a unique name for the device, such as `agx201`.

#### mDNS

The autotrainer mDNS service entry allows the node to be discovered by the system management services.

It this repository has been cloned to the device, the file can be copied directly:

```bash
sudo mkdir -p /etc/avahi/services
sudo cp auto-trainer-deployment/device/autotrainer.service /etc/avahi/services/
```

Alternatively, manually add and edit the file `/etc/avahi/services/autotrainer.service` with the following contents:

```xml
<service-group>

  <name replace-wildcards="yes">%h</name>

  <service>
    <type>_autotrainer._tcp</type>
    <port>5555</port>
    <txt-record>Subscriber=5556</txt-record>
    <txt-record>Command=5557</txt-record>
  </service>

</service-group>
```

Restart the mDNS service to pick up the new service entry:

```bash
sudo service avahi-daemon restart
```

Verify it is running

```bash
avahi-browse -d local _autotrainer._tcp --resolve -t
```

The output will vary based on the number of nodes in the system and nature of the network interfaces on the device,
however there should be an entry with a hostname and IP that matches the device, e.g. in the case above with the
hostname `agx201`:

```
=  wlan0 IPv4 agx201                                    _autotrainer._tcp    local
   hostname = [agx201.local]            # Should match the device hostname (with .local)
   address = [192.168.1.100]            # Should match the device IP
   port = [5555]
   txt = ["Command=5557" "Subscriber=5556"]
```

#### Logging for Docker Containers

Create a log file location for the services:

```shell
sudo mkdir -p /autotrainer/logs
chmod uog+w /autotrainer/logs
```
