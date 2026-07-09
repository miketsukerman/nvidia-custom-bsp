# Jetson Firmware Builder

Jetson Firmware Builder is a Dockerized Python toolchain for building and flashing custom NVIDIA Jetson firmware across JetPack/L4T releases, including multi-target workflows from a single YAML.

## Prerequisites

- Docker on the host
- Linux host recommended for USB flashing passthrough

## Install

```bash
pip install -e .
```

## Quickstart

Validate the example config on the host:

```bash
jetson-fw validate configs/jetpack51.yaml --schema-out configs/schema.json
```

Build or pull the container image:

```bash
jetson-fw image configs/jetpack51.yaml
```

Preview the Docker invocation and inner L4T commands:

```bash
jetson-fw build configs/jetpack51.yaml --dry-run
```

Flash a board with USB passthrough:

```bash
jetson-fw flash configs/jetpack51.yaml --target xavier-nx
```

## Logging modes

- Default mode prints stage progress, command output, warnings, and success/error summaries.
- `--verbose` adds debug metadata for stage orchestration, Docker/image context, command cwd/env override keys, and command timing/exit summaries.
- `--quiet` suppresses non-error output.

## YAML Reference

For the full per-field configuration reference, annotated examples, and merge semantics for
per-target overrides, see [docs/configuration.md](docs/configuration.md).

The top-level sections are: `version`, `docker`, `l4t`, `toolchain`, `workspace`, `kernel`,
`rootfs`, `bsp`, and `targets`.  All sections except `docker`, `l4t`, `toolchain`, and `targets`
are optional and carry sensible defaults.  Per-target `kernel`, `rootfs`, and `bsp` sub-sections
are merged with their top-level counterparts: scalar fields override, list fields append.

A working multi-target example is in [`configs/jetpack51.yaml`](configs/jetpack51.yaml).

## Docker execution model

- `validate` runs on the host and does not require Docker.
- `image` runs `docker build` or `docker pull` using the YAML `docker` section.
- `build`, `flash`, and `all` run inside the builder image and bind-mount the repository plus configured volumes.
- Shared download/toolchain stages are reused, while target-scoped stages (`customize_bsp`, `source_sync`, `build_kernel`, `assemble_rootfs`, `flash`) keep per-target stage markers.
- `bsp.overlays` are applied inside `Linux_for_Tegra` before source sync and flashing, so they can override NVIDIA bootloader config files such as MB1 BCTs or bootloader DTBs.
- Flashing adds `--privileged` or USB device passthrough mounts.
- Download archives in `/workspace/build/downloads` are treated as a reusable cache for BSP, sample rootfs, and toolchain artifacts.

## Sudo-less flashing

By default, `flash.sh` needs root to access the Jetson USB recovery device
(VID `0x0955`).  A udev rule can grant a normal user in the **plugdev** group
direct USB access, eliminating the need for sudo during the flashing step.

### 1. Install the udev rule

```bash
sudo jetson-fw install-udev-rules
```

This copies `99-tegra-devices.rules` to `/etc/udev/rules.d/` and runs
`udevadm control --reload-rules && udevadm trigger`.  You can preview what it
would do with `--dry-run`:

```bash
jetson-fw install-udev-rules --dry-run
```

To install to a custom directory (e.g. for testing):

```bash
sudo jetson-fw install-udev-rules --dest-dir /run/udev/rules.d
```

### 2. Add your user to the plugdev group

```bash
sudo usermod -aG plugdev $USER
```

Log out and back in (or run `newgrp plugdev` in the current shell) for the
group change to take effect.

### 3. Plug the board in Force Recovery Mode

Connect the Jetson via USB and boot it into Force Recovery Mode.  Verify the
device appears without sudo:

```bash
lsusb | grep 0955
```

You should now be able to run `jetson-fw flash` without root.

### Remaining privilege need

Even with the udev rule in place, the `assemble_rootfs` stage uses `losetup`,
`mount`, and `umount` (via NVIDIA's `apply_binaries.sh`) to build
`system.img`.  Those operations still require root or the appropriate Linux
capabilities.  The udev rule only removes the need for root during the USB
flashing step.

The `flash` command automatically runs a preflight check and emits warnings if
the rule is missing or the user is not in `plugdev`.

## Troubleshooting

- If `flash.sh` cannot see the Jetson in recovery mode, confirm `/dev/bus/usb` is exposed and retry with `privileged_for_flash: true`.
- If a config path is rejected, ensure relative paths are relative to the YAML file.
- If downloads fail verification, refresh the SHA256 values in the YAML instead of editing code.
- If recovery boot fails before Linux starts with messages such as `DEVICE_PROD`, `tegrabl_tca9539_init`, or `Failed to initialize device 1-3`, make sure the required bootloader DT/BCT files are provided via `bsp.overlays`; kernel DTS changes alone are too late for those failures.
- Cached archives are still checksum-verified on every run; YAML checksum values remain authoritative even when archives are pre-seeded in `/workspace/build/downloads`.
- If `assemble_rootfs` fails partway through `apply_binaries.sh`, rerunning the stage now scrubs stale `/dev/random` and `/dev/urandom` nodes left behind by the interrupted NVIDIA script before retrying.
- If you use a custom builder image and enable `rootfs.install_modules`, make sure the image includes `depmod` (provided by the `kmod` package) so `make modules_install` can generate module dependency metadata without warnings.
- If you want compose wrappers, use `docker compose run --rm validate`, `build`, or `flash`.
