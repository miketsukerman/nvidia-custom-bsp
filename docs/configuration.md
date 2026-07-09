# YAML Configuration Reference

This document describes every field in the Jetson Firmware Builder YAML configuration file, along with annotated examples.

A configuration file is validated against the JSON Schema at [`configs/schema.json`](../configs/schema.json).

---

## Top-level structure

```yaml
version: 1        # required

docker:   { … }   # required
l4t:      { … }   # required
toolchain: { … }  # required
workspace: { … }  # optional
kernel:   { … }   # optional
rootfs:   { … }   # optional
bsp:      { … }   # optional
targets:  [ … ]   # required – at least one entry
```

---

## `version`

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `version` | integer (const `1`) | yes | `1` |

Schema version sentinel.  Currently only `1` is supported.

```yaml
version: 1
```

---

## `docker`

Docker execution settings for the builder container.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `image` | string | **yes** | – |
| `dockerfile` | path | no | `docker/Dockerfile` |
| `build` | boolean | no | `true` |
| `registry` | string | no | `""` |
| `privileged_for_flash` | boolean | no | `true` |
| `devices` | list of paths | no | `[/dev/bus/usb]` |
| `volumes` | list of `host:container[:mode]` strings | no | `[../build:/workspace/build]` |
| `environment` | map of string→string | no | `{JOBS: "8"}` |

**`image`** — Docker image tag for the builder.  The image is either built locally (when `build: true`) or pulled from the `registry`.

**`dockerfile`** — Path to the `Dockerfile` used when `build: true`.  Relative paths are resolved from the directory containing the YAML file.

**`build`** — When `true` the toolchain runs `docker build` before every build/flash invocation.  Set to `false` to always pull instead.

**`registry`** — Optional registry prefix prepended to `image` for both pulls and pushes (e.g. `ghcr.io/myorg`).

**`privileged_for_flash`** — Passes `--privileged` to the flash container.  Disable only when USB access is granted via udev rules and no other privileged operation is needed.

**`devices`** — List of host device nodes made available inside the flash container.  `/dev/bus/usb` is required for USB recovery flashing.

**`volumes`** — Additional bind mounts in Docker `host:container[:mode]` format.  At minimum the build output directory should be mounted here.

**`environment`** — Extra environment variables injected into the container.  `JOBS` controls the parallelism level for `make`.

```yaml
docker:
  image: "jetson-firmware-builder:35.2.1"
  dockerfile: "../docker/Dockerfile"
  build: true
  registry: ""
  privileged_for_flash: true
  devices:
    - "/dev/bus/usb"
  volumes:
    - "../build:/workspace/build"
  environment:
    JOBS: "8"
```

---

## `l4t`

Jetson Linux (L4T) archive inputs.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `release` | string | no | `"35.2.1"` |
| `bsp_url` | URI | **yes** | – |
| `bsp_sha256` | string | **yes** | – |
| `sample_rootfs_url` | URI | **yes** | – |
| `sample_rootfs_sha256` | string | **yes** | – |

**`release`** — L4T release string used for informational and compatibility checks (e.g. `"35.2.1"` corresponds to JetPack 5.1).

**`bsp_url`** / **`sample_rootfs_url`** — Direct download URLs for the Jetson Linux BSP archive and sample root filesystem archive from the NVIDIA developer site.

**`bsp_sha256`** / **`sample_rootfs_sha256`** — SHA-256 digests (64 hex characters) used to verify the downloaded archives.  These values are authoritative even when archives are pre-seeded in the download cache.

```yaml
l4t:
  release: "35.2.1"
  bsp_url: "https://developer.nvidia.com/downloads/jetson-linux-r3521-aarch64tbz2"
  bsp_sha256: "9959bcd3de79de231a8fb54119f9cdb57a753542d44d994e346664028142d40d"
  sample_rootfs_url: "https://developer.nvidia.com/downloads/linux-sample-root-filesystem-r3521aarch64tbz2"
  sample_rootfs_sha256: "aad1ba13dbae2c8657123d39b23dc836ea46f7d7a2da24a8adb4c0e58da501d6"
```

---

## `toolchain`

Cross-compilation toolchain metadata.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `name` | string | no | `"bootlin-gcc-9.3"` |
| `url` | URI | **yes** | – |
| `sha256` | string | **yes** | – |
| `cross_compile_prefix` | string | no | `"aarch64-buildroot-linux-gnu-"` |

**`name`** — Human-readable toolchain identifier used in log output.

**`url`** — Download URL for the toolchain tarball.

**`sha256`** — SHA-256 digest for the toolchain archive.

**`cross_compile_prefix`** — Prefix passed to `CROSS_COMPILE` during kernel compilation (e.g. `aarch64-buildroot-linux-gnu-`).

```yaml
toolchain:
  name: "bootlin-gcc-9.3"
  url: "https://developer.nvidia.com/embedded/jetson-linux/bootlin-toolchain-gcc-93"
  sha256: "7725b4603193a9d3751d2715ef242bd16ded46b4e0610c83e76d8891cf580975"
  cross_compile_prefix: "aarch64-buildroot-linux-gnu-"
```

---

## `workspace`

Workspace options inside the builder container.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `root` | path | no | `"/workspace/build"` |
| `keep_intermediate` | boolean | no | `true` |

**`root`** — Absolute path inside the container where all build artifacts, downloaded archives, and stage markers are stored.

**`keep_intermediate`** — When `true`, intermediate artifacts (source trees, compiled objects) are retained between runs to speed up incremental builds.

```yaml
workspace:
  root: "/workspace/build"
  keep_intermediate: true
```

---

## `kernel`

Global kernel build options shared by all targets (unless overridden per-target).

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `source_tag` | string | no | `"jetson_35.2.1"` |
| `defconfig` | string | no | `"tegra_defconfig"` |
| `config_fragments` | list of paths | no | `[]` |
| `extra_dts` | list of paths | no | `[]` |

**`source_tag`** — Git tag used to check out the kernel and device-tree sources during `source_sync`.  Must correspond to a tag in the Jetson kernel repository (e.g. `jetson_35.2.1`).

**`defconfig`** — Kernel defconfig target passed to `make` (e.g. `tegra_defconfig`).

**`config_fragments`** — Optional list of kernel config fragment files (`.config` snippets) merged into the final kernel configuration after applying the defconfig.  Paths are relative to the YAML file.

**`extra_dts`** — Optional list of custom DTS source files included in the kernel device-tree build.  Paths are relative to the YAML file.

```yaml
kernel:
  source_tag: "jetson_35.2.1"
  defconfig: "tegra_defconfig"
  config_fragments:
    - "../fixtures/configs/enable-can.config"
  extra_dts:
    - "../fixtures/dts/my-carrier.dts"
```

---

## `rootfs`

Global rootfs customization options shared by all targets (unless overridden per-target).

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `install_modules` | boolean | no | `true` |
| `extra_packages` | list of strings | no | `[]` |
| `overlays` | list of [RootfsOverlay](#rootfsoverlay) | no | `[]` |

**`install_modules`** — When `true`, the compiled kernel modules are installed into the rootfs via `make modules_install`.  Requires `depmod` (from the `kmod` package) in the builder image.

**`extra_packages`** — Additional Debian/Ubuntu package names to install into the rootfs via `apt`.

**`overlays`** — List of overlay entries that copy files or directories from the host into the rootfs.  See [RootfsOverlay](#rootfsoverlay).

### RootfsOverlay

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `src` | path | **yes** | Source file or directory on the host (relative to the YAML file) |
| `dest` | string | **yes** | Absolute destination path within the rootfs |

```yaml
rootfs:
  install_modules: true
  extra_packages:
    - "curl"
    - "htop"
  overlays:
    - src: "../fixtures/overlays/etc"
      dest: "/etc"
```

---

## `bsp`

Global Linux_for_Tegra (BSP) customization options.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `overlays` | list of [BspOverlay](#bspoverlay) | no | `[]` |

**`overlays`** — Files or directories copied into the extracted `Linux_for_Tegra` tree after `fetch_bsp` and before `source_sync`, kernel build, and flash.  Use this for bootloader files such as MB1 BCTs or bootloader DTBs that must be present before early-boot device initialization.

> **Note**: BSP overlay changes take effect before the kernel DTS is processed, so they are the correct mechanism to fix early-boot failures (e.g. `DEVICE_PROD`, `tegrabl_tca9539_init`).

### BspOverlay

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `src` | path | **yes** | Source file or directory on the host (relative to the YAML file) |
| `dest` | string | **yes** | Absolute destination path within `Linux_for_Tegra` |

```yaml
bsp:
  overlays:
    - src: "../fixtures/bootloader/my-board"
      dest: "/bootloader"
```

---

## `targets`

List of Jetson targets that share the same kernel and rootfs build.  At least one target is required.

Each entry is a **TargetConfig**:

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `name` | string | **yes** | – |
| `module` | enum | **yes** | – |
| `flash_config` | string | **yes** | – |
| `root_device` | enum | **yes** | – |
| `enabled` | boolean | no | `true` |
| `kernel` | [TargetKernelConfig](#targetkernelconfig) | no | `null` |
| `rootfs` | [TargetRootfsConfig](#targetrootfsconfig) | no | `null` |
| `bsp` | [TargetBspConfig](#targetbspconfig) | no | `null` |

**`name`** — Unique identifier for this target, used with the `--target` CLI flag.

**`module`** — Jetson module hardware identifier.

| Value | Module |
|-------|--------|
| `p3668` | Jetson Xavier NX |
| `p3767` | Jetson Orin NX / Orin Nano |

**`flash_config`** — Board configuration name passed to `flash.sh` (e.g. `jetson-xavier-nx-devkit-emmc`, `jetson-orin-nano-devkit`, or a custom value for production boards).

**`root_device`** — Root device argument passed to `flash.sh`.

| Value | Device |
|-------|--------|
| `mmcblk0p1` | eMMC partition 1 (Xavier NX eMMC modules) |
| `internal` | Internal storage (Orin modules, NVMe, or SD) |

**`enabled`** — When `false`, the target is skipped by the `build` and `all` commands.

### TargetKernelConfig

Per-target kernel overrides merged with the top-level `kernel` section.

| Field | Type | Default | Merge behavior |
|-------|------|---------|----------------|
| `source_tag` | string or null | `null` | Overrides shared value when set |
| `defconfig` | string or null | `null` | Overrides shared value when set |
| `config_fragments` | list of paths or null | `null` | **Appended** to shared list when set |
| `extra_dts` | list of paths or null | `null` | **Appended** to shared list when set |

### TargetRootfsConfig

Per-target rootfs overrides merged with the top-level `rootfs` section.

| Field | Type | Default | Merge behavior |
|-------|------|---------|----------------|
| `install_modules` | boolean or null | `null` | Overrides shared value when set |
| `extra_packages` | list of strings or null | `null` | **Appended** to shared list when set |
| `overlays` | list of RootfsOverlay or null | `null` | **Appended** to shared list when set |

### TargetBspConfig

Per-target Linux_for_Tegra overrides merged with the top-level `bsp` section.

| Field | Type | Default | Merge behavior |
|-------|------|---------|----------------|
| `overlays` | list of BspOverlay or null | `null` | **Appended** to shared list when set |

```yaml
targets:
  - name: "xavier-nx"
    module: "p3668"
    flash_config: "jetson-xavier-nx-devkit-emmc"
    root_device: "mmcblk0p1"
    enabled: true
    kernel:
      extra_dts:
        - "../fixtures/dts/xavier-carrier.dts"
    bsp:
      overlays:
        - src: "../fixtures/bootloader/xavier-bct"
          dest: "/bootloader"
```

---

## Examples

### Single target – Orin NX

A minimal configuration for a single Jetson Orin NX target with a custom DTS and CAN kernel fragment.

```yaml
# configs/orin-nx.yaml
version: 1

docker:
  image: "jetson-firmware-builder:35.2.1"
  dockerfile: "../docker/Dockerfile"
  build: true
  registry: ""
  privileged_for_flash: true
  devices:
    - "/dev/bus/usb"
  volumes:
    - "../build:/workspace/build"
  environment:
    JOBS: "8"

l4t:
  release: "35.2.1"
  bsp_url: "https://developer.nvidia.com/downloads/jetson-linux-r3521-aarch64tbz2"
  bsp_sha256: "9959bcd3de79de231a8fb54119f9cdb57a753542d44d994e346664028142d40d"
  sample_rootfs_url: "https://developer.nvidia.com/downloads/linux-sample-root-filesystem-r3521aarch64tbz2"
  sample_rootfs_sha256: "aad1ba13dbae2c8657123d39b23dc836ea46f7d7a2da24a8adb4c0e58da501d6"

toolchain:
  name: "bootlin-gcc-9.3"
  url: "https://developer.nvidia.com/embedded/jetson-linux/bootlin-toolchain-gcc-93"
  sha256: "7725b4603193a9d3751d2715ef242bd16ded46b4e0610c83e76d8891cf580975"
  cross_compile_prefix: "aarch64-buildroot-linux-gnu-"

workspace:
  root: "/workspace/build"
  keep_intermediate: true

kernel:
  source_tag: "jetson_35.2.1"
  defconfig: "tegra_defconfig"
  config_fragments:
    - "../fixtures/configs/enable-can.config"   # enables CAN bus support
  extra_dts:
    - "../fixtures/dts/orin-carrier.dts"         # custom carrier board DT

rootfs:
  install_modules: true
  extra_packages: []
  overlays:
    - src: "../fixtures/overlays/etc"
      dest: "/etc"

bsp:
  overlays: []

targets:
  - name: "orin-nx"
    module: "p3767"
    flash_config: "jetson-orin-nano-devkit"
    root_device: "internal"
    enabled: true
```

---

### Single target – Xavier NX (eMMC)

```yaml
# configs/xavier-nx.yaml
version: 1

docker:
  image: "jetson-firmware-builder:35.2.1"
  dockerfile: "../docker/Dockerfile"
  build: true
  registry: ""
  privileged_for_flash: true
  devices:
    - "/dev/bus/usb"
  volumes:
    - "../build:/workspace/build"
  environment:
    JOBS: "8"

l4t:
  release: "35.2.1"
  bsp_url: "https://developer.nvidia.com/downloads/jetson-linux-r3521-aarch64tbz2"
  bsp_sha256: "9959bcd3de79de231a8fb54119f9cdb57a753542d44d994e346664028142d40d"
  sample_rootfs_url: "https://developer.nvidia.com/downloads/linux-sample-root-filesystem-r3521aarch64tbz2"
  sample_rootfs_sha256: "aad1ba13dbae2c8657123d39b23dc836ea46f7d7a2da24a8adb4c0e58da501d6"

toolchain:
  name: "bootlin-gcc-9.3"
  url: "https://developer.nvidia.com/embedded/jetson-linux/bootlin-toolchain-gcc-93"
  sha256: "7725b4603193a9d3751d2715ef242bd16ded46b4e0610c83e76d8891cf580975"
  cross_compile_prefix: "aarch64-buildroot-linux-gnu-"

workspace:
  root: "/workspace/build"
  keep_intermediate: true

kernel:
  source_tag: "jetson_35.2.1"
  defconfig: "tegra_defconfig"
  config_fragments:
    - "../fixtures/configs/enable-can.config"
  extra_dts:
    - "../fixtures/dts/xavier-carrier.dts"

rootfs:
  install_modules: true
  extra_packages: []
  overlays:
    - src: "../fixtures/overlays/etc"
      dest: "/etc"

bsp:
  overlays: []

targets:
  - name: "xavier-nx"
    module: "p3668"
    flash_config: "jetson-xavier-nx-devkit-emmc"
    root_device: "mmcblk0p1"  # eMMC root partition
    enabled: true
```

---

### Multi-target – Xavier NX + Orin NX

Shared kernel and rootfs build with per-target DTS overrides.  Both targets are built with a single `jetson-fw build` invocation.

```yaml
# configs/xavier-orin-multi.yaml
version: 1

docker:
  image: "jetson-firmware-builder:35.2.1"
  dockerfile: "../docker/Dockerfile"
  build: true
  registry: ""
  privileged_for_flash: true
  devices:
    - "/dev/bus/usb"
  volumes:
    - "../build:/workspace/build"
  environment:
    JOBS: "8"

l4t:
  release: "35.2.1"
  bsp_url: "https://developer.nvidia.com/downloads/jetson-linux-r3521-aarch64tbz2"
  bsp_sha256: "9959bcd3de79de231a8fb54119f9cdb57a753542d44d994e346664028142d40d"
  sample_rootfs_url: "https://developer.nvidia.com/downloads/linux-sample-root-filesystem-r3521aarch64tbz2"
  sample_rootfs_sha256: "aad1ba13dbae2c8657123d39b23dc836ea46f7d7a2da24a8adb4c0e58da501d6"

toolchain:
  name: "bootlin-gcc-9.3"
  url: "https://developer.nvidia.com/embedded/jetson-linux/bootlin-toolchain-gcc-93"
  sha256: "7725b4603193a9d3751d2715ef242bd16ded46b4e0610c83e76d8891cf580975"
  cross_compile_prefix: "aarch64-buildroot-linux-gnu-"

workspace:
  root: "/workspace/build"
  keep_intermediate: true

kernel:
  source_tag: "jetson_35.2.1"
  defconfig: "tegra_defconfig"
  # No global extra_dts – each target supplies its own

rootfs:
  install_modules: true
  extra_packages: []
  overlays:
    - src: "../fixtures/overlays/etc"
      dest: "/etc"

bsp:
  overlays: []

targets:
  - name: "xavier-nx"
    module: "p3668"
    flash_config: "jetson-xavier-nx-devkit-emmc"
    root_device: "mmcblk0p1"
    enabled: true
    kernel:
      extra_dts:                                      # appended to global kernel.extra_dts
        - "../fixtures/dts/xavier-carrier.dts"

  - name: "orin-nx"
    module: "p3767"
    flash_config: "jetson-orin-nano-devkit"
    root_device: "internal"
    enabled: true
    kernel:
      extra_dts:
        - "../fixtures/dts/orin-carrier.dts"
```

---

### Multi-target – Production boards with BSP bootloader overlays

Two production variants that share a common kernel/rootfs but each supply different bootloader files via `bsp.overlays`.

```yaml
# configs/air-020-air-021.yaml
version: 1

docker:
  image: "jetson-firmware-builder:35.2.1"
  dockerfile: "../docker/Dockerfile"
  build: true
  registry: ""
  privileged_for_flash: true
  devices:
    - "/dev/bus/usb"
  volumes:
    - "../build:/workspace/build"
  environment:
    JOBS: "8"

l4t:
  release: "35.2.1"
  bsp_url: "https://developer.nvidia.com/downloads/jetson-linux-r3521-aarch64tbz2"
  bsp_sha256: "9959bcd3de79de231a8fb54119f9cdb57a753542d44d994e346664028142d40d"
  sample_rootfs_url: "https://developer.nvidia.com/downloads/linux-sample-root-filesystem-r3521aarch64tbz2"
  sample_rootfs_sha256: "aad1ba13dbae2c8657123d39b23dc836ea46f7d7a2da24a8adb4c0e58da501d6"

toolchain:
  name: "bootlin-gcc-9.3"
  url: "https://developer.nvidia.com/embedded/jetson-linux/bootlin-toolchain-gcc-93"
  sha256: "7725b4603193a9d3751d2715ef242bd16ded46b4e0610c83e76d8891cf580975"
  cross_compile_prefix: "aarch64-buildroot-linux-gnu-"

workspace:
  root: "/workspace/build"
  keep_intermediate: true

kernel:
  source_tag: "jetson_35.2.1"
  defconfig: "tegra_defconfig"

rootfs:
  install_modules: true
  extra_packages: []
  overlays:
    - src: "../fixtures/overlays/etc"
      dest: "/etc"

bsp:
  overlays: []   # no shared BSP overlays

targets:
  - name: "air-020"
    module: "p3767"
    flash_config: "air-020-production"   # custom flash.sh config for this board
    root_device: "internal"
    enabled: true
    kernel:
      extra_dts:
        - "../fixtures/dts/air-020-carrier.dts"
    bsp:
      overlays:                                 # board-specific bootloader files
        - src: "../fixtures/bootloader/air-020"
          dest: "/bootloader"

  - name: "air-021"
    module: "p3767"
    flash_config: "air-021-production"
    root_device: "internal"
    enabled: true
    kernel:
      extra_dts:
        - "../fixtures/dts/air-021-carrier.dts"
    bsp:
      overlays:
        - src: "../fixtures/bootloader/air-021"
          dest: "/bootloader"
```

---

## Merge semantics for per-target overrides

When a target defines a `kernel`, `rootfs`, or `bsp` sub-section, the fields are merged with the corresponding top-level section according to the following rules:

| Field type | Merge rule |
|------------|------------|
| Scalar (string, boolean) | Target value **replaces** the shared value |
| List (`config_fragments`, `extra_dts`, `extra_packages`, `overlays`) | Target list is **appended** to the shared list |
| `null` (field absent or explicitly `null`) | Shared value is used unchanged |

This means, for example, that a shared `config_fragments` list applies to every target, and each target can add further fragments without removing the shared ones.

---

## Validation

Validate a configuration file against the JSON schema without starting Docker:

```bash
jetson-fw validate configs/my-board.yaml
```

Export the current schema alongside validation:

```bash
jetson-fw validate configs/my-board.yaml --schema-out configs/schema.json
```
