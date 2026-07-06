# Jetson Firmware Builder

Jetson Firmware Builder is a Dockerized Python toolchain for building and flashing custom NVIDIA Jetson Xavier NX and Orin NX firmware for JetPack 5.1 / L4T R35.2.1.

## Prerequisites

- Docker on the host
- Linux host recommended for USB flashing passthrough

## Install

```bash
pip install -e .
```

## Quickstart

Validate the example configs on the host:

```bash
jetson-fw validate configs/xavier-nx.yaml --schema-out configs/schema.json
jetson-fw validate configs/orin-nx.yaml
```

Build or pull the container image:

```bash
jetson-fw image configs/xavier-nx.yaml
```

Preview the Docker invocation and inner L4T commands:

```bash
jetson-fw build configs/xavier-nx.yaml --dry-run
```

Flash a board with USB passthrough:

```bash
jetson-fw flash configs/xavier-nx.yaml --target xavier-nx
```

## Logging modes

- Default mode prints stage progress, command output, warnings, and success/error summaries.
- `--verbose` adds debug metadata for stage orchestration, Docker/image context, command cwd/env override keys, and command timing/exit summaries.
- `--quiet` suppresses non-error output.

## YAML Reference

### `version`
- `1` (required): schema version.

### `docker`
- `image` (required): builder image tag.
- `dockerfile` (default `docker/Dockerfile`): Dockerfile path when `build: true`.
- `build` (default `true`): build locally instead of `docker pull`.
- `registry` (default empty): optional registry prefix.
- `privileged_for_flash` (default `true`): use `--privileged` for flash containers.
- `devices` (default `[/dev/bus/usb]`): device paths for flashing.
- `volumes` (default `./build:/workspace/build`): extra bind mounts using `host:container[:mode]`.
- `environment` (default `JOBS=8`): extra container environment variables.

### `l4t`
- `release` (default `35.2.1`): supported JetPack/L4T release.
- `bsp_url` / `sample_rootfs_url` (required): download URLs.
- `bsp_sha256` / `sample_rootfs_sha256` (required): 64-character SHA256 digests.

### `toolchain`
- `name` (default `bootlin-gcc-9.3`)
- `url` (required)
- `sha256` (required)
- `cross_compile_prefix` (default `aarch64-buildroot-linux-gnu-`)

### `workspace`
- `root` (default `/workspace/build`): build path inside the container.
- `keep_intermediate` (default `true`)

### `kernel`
- `source_tag` (default `jetson_35.2.1`): used for the kernel/device-tree source sync that the build runs before compiling.
- `defconfig` (default `tegra_defconfig`)
- `config_fragments` (default empty)
- `extra_dts` (default empty)

### `rootfs`
- `install_modules` (default `true`)
- `extra_packages` (default empty)
- `overlays` (default empty)

### `bsp`
- `overlays` (default empty): files or directories copied into the extracted `Linux_for_Tegra` tree after `fetch_bsp` and before `source_sync`, kernel build, and flash. Use this for bootloader DTB/BCT replacements that affect early boot device initialization.

### `targets`
- `name` (required)
- `module` (required enum: `p3668`, `p3767`)
- `flash_config` (required enum: `jetson-xavier-nx-devkit-emmc`, `jetson-orin-nano-devkit`)
- `root_device` (required enum: `mmcblk0p1`, `internal`)
- `enabled` (default `true`)

## Docker execution model

- `validate` runs on the host and does not require Docker.
- `image` runs `docker build` or `docker pull` using the YAML `docker` section.
- `build`, `flash`, and `all` run inside the builder image and bind-mount the repository plus configured volumes.
- `bsp.overlays` are applied inside `Linux_for_Tegra` before source sync and flashing, so they can override NVIDIA bootloader config files such as MB1 BCTs or bootloader DTBs.
- Flashing adds `--privileged` or USB device passthrough mounts.
- Download archives in `/workspace/build/downloads` are treated as a reusable cache for BSP, sample rootfs, and toolchain artifacts.

## Troubleshooting

- If `flash.sh` cannot see the Jetson in recovery mode, confirm `/dev/bus/usb` is exposed and retry with `privileged_for_flash: true`.
- If a config path is rejected, ensure relative paths are relative to the YAML file.
- If downloads fail verification, refresh the SHA256 values in the YAML instead of editing code.
- If recovery boot fails before Linux starts with messages such as `DEVICE_PROD`, `tegrabl_tca9539_init`, or `Failed to initialize device 1-3`, make sure the required bootloader DT/BCT files are provided via `bsp.overlays`; kernel DTS changes alone are too late for those failures.
- Cached archives are still checksum-verified on every run; YAML checksum values remain authoritative even when archives are pre-seeded in `/workspace/build/downloads`.
- If `assemble_rootfs` fails partway through `apply_binaries.sh`, rerunning the stage now scrubs stale `/dev/random` and `/dev/urandom` nodes left behind by the interrupted NVIDIA script before retrying.
- If you use a custom builder image and enable `rootfs.install_modules`, make sure the image includes `depmod` (provided by the `kmod` package) so `make modules_install` can generate module dependency metadata without warnings.
- If you want compose wrappers, use `docker compose run --rm validate`, `build`, or `flash`.
