##  Device Deployment
Installation of the core AutoTrainer application is described in the [AutoTrainer Repository itself](https://github.com/Mouse-GYM/auto-trainer).
In addition, the following supporting services are required for the node to participate in centralized system management.

The majority of device setup is performed by the `prepare_autotrainer_unit.sh` script. This is followed by a manual, device-specific
configuration step.

## Prerequisites

#### 1.SSD & Jetson Linux/Jetpack
The installation requires an SSD.  The default drive can accept the installation, but the applications will
perform as required for default capture rates.

The software currently requires JetPack 5.1.x.  There are a number of tutorials for physical SSD installation
as well as using the NVidia SDK Manager to install Jetson Linux and Jetpack 5, including [this one](https://www.youtube.com/watch?v=DKI1k_aP0Qk).

#### 2. User
Although the acquisition application and many services can be made to run under any user, many services 
default to the assumption, and some do require, that the user be `autotrainer`.  These instructions
assume they being performed under this user.

## Required

### 1. Automated Preparation
Run `prepare_autotrainer_unit.sh` with the name of the unit as an argument.
The name will be used as the hostname for the computer as well as the identifier in remote views,
emergency notifications, and similar.
It should be unique for all units in the system.

```bash
./prepare_autotrainer_unit.sh <DEVICE_HOST_NAME>
```

where `<DEVICE_HOST_NAME>` must be replaced with the device-specific name. Such as _agx327_.
The script, during execution, is sometimes making use of `sudo`.
You will be prompted to enter the account password if you have not already authenticated for an earlier `sudo` command.

### 2. Configure Docker Compose Variables

Copy the environment template:

```shell
cp .env-template .env
```

Edit the newly created .env and populate the required values.
Typical values are provided in the comments of the template file.
The device name should be the same value you used as an argument to `prepare_autotrainer_unit.sh`.

The Cognito user pool and app client values are required for the dashboard to make changes to the device; the AWS credential and SNS values are optional and will be based on your deployment.

### 3. Start Docker Containers
```shell
./up.sh
```

After the first manual start, the services will restart after any reboot or other reason for exit automatically.

### 4. Manual Changes

#### Power Mode
When logged in, use the NVidia Power Mode item in the upper right of the Desktop to ensure that Power Mode is
set to 50W (typically defaults to 30W after a fresh installation).

## Details of Automated Preparation
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
sudo mkdir -p /var/autotrainer/logs
chmod ug+w /var/autotrainer/logs
```

#### Nightly Maintenance

`autotrainer_maintenance.timer` starts `autotrainer_maintenance.service` every day at 01:00. The service runs
`/usr/local/sbin/auto_trainer_nightly_maintenance.sh` as the `autotrainer` user, with the settings in
`/etc/default/autotrainer_nightly_maintenance` (sync target, maintenance venv, `delete_older_days`).

For each `YYYYMMDD` folder in `~/Documents/RawDataLocal` older than today, a run:

1. converts every `*_web_images` folder into `*_web_video.mp4` plus `*_web_images_timestamps.txt` (one
   `<frame index>\t<HHMMSS_mmm>` line per frame), deleting only the PNG files that went into the video;
2. rsyncs the folder to the Isilon share;
3. deletes the local folder once it is synced and older than `delete_older_days`.

It needs `ffmpeg` from apt (installed by `prepare_autotrainer_unit.sh`) and the venv from
`install_maintenance_venv.sh`.

The result of the latest run is written to `~/.config/Colorado/nightly_maintenance_status.json` for other
services to poll. Set `AUTOTRAINER_NIGHTLY_MAINTENANCE_STATUS_FILE`, or pass `--status-file`, to use another path.

```json
{
  "schema_version": 1,
  "result": "failure",
  "exit_code": 1,
  "started_at": "2026-11-28T01:00:02-07:00",
  "finished_at": "2026-11-28T01:07:41-07:00",
  "errors": [
    {"kind": "sync-failed", "path": "/home/autotrainer/Documents/RawDataLocal/20261120", "message": "rsync exited with status 23"}
  ],
  "warnings": [
    {"kind": "unreadable-image", "path": "/home/autotrainer/Documents/RawDataLocal/20261126/agx003/20261126_agx003_h14_web_images",
     "message": "2 PNG files are empty or cannot be decoded; left in place and synced", "count": 2,
     "files": ["20261126_agx003_h14_web_20261126_141502_118.png", "20261126_agx003_h14_web_20261126_141503_120.png"]}
  ]
}
```

- `result` is `running`, `success` or `failure`, and `exit_code` is `null` while running. A `running` result
  whose `started_at` is more than a day old means the run died before finishing.
- Times are ISO 8601 local time. Paths are absolute, and `path` is `null` when no single path applies.
- Every entry in `errors` made the run fail. Its `kind` is one of `target-unavailable`, `ffmpeg-missing`,
  `opencv-missing`, `encode-failed`, `validation-failed`, `publish-failed`, `unverified-video`, `folder-failed`,
  `sync-failed`, `delete-failed`, `unexpected-exception`, `invalid-arguments`, `wrapper-failed` or
  `status-write-failed`.
- `warnings` list PNG files left out of a video, which stay in place and are synced; they never fail the run.
  The kinds are `bad-filename` (no `_HHMMSS_mmm.png` timestamp in the name), `unreadable-image` (empty or
  undecodable) and `not-in-video` (arrived after the folder's video was made). `count` is the number of files and
  `files` lists at most the first 20 names.
